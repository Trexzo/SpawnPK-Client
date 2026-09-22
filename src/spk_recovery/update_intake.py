from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .diffing import diff_indexes
from .delta_classify import classify_class_deltas
from .indexer import index_jar, write_index
from .matcher import match_classes


class UpdateIntakeError(ValueError):
    pass


_REVIEW_STRATEGIES = {"package_anchor", "weighted_mutual_best"}


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _classification(match: dict[str, Any]) -> str:
    strategy = match.get("strategy")
    old_path = match.get("old")
    new_path = match.get("new")

    if strategy == "exact_sha256":
        return (
            "byte_identical_same_path"
            if old_path == new_path
            else "byte_identical_moved"
        )
    if strategy == "structural_unique":
        return (
            "structurally_equivalent_same_path"
            if old_path == new_path
            else "structurally_equivalent_moved"
        )
    if strategy == "package_anchor":
        return "package_anchor_identity_candidate"
    if strategy == "weighted_mutual_best":
        return "weighted_identity_candidate"
    return "unknown_match_strategy"


def build_update_intake(
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
    scope_prefix: str = "rs/",
) -> dict[str, Any]:
    if not isinstance(old_build_id, str) or not old_build_id:
        raise UpdateIntakeError("old_build_id must be non-empty")
    if not isinstance(new_build_id, str) or not new_build_id:
        raise UpdateIntakeError("new_build_id must be non-empty")
    if old_build_id == new_build_id:
        raise UpdateIntakeError("old_build_id and new_build_id must differ")

    old_sha = str(old_index.get("sha256", "")).lower()
    new_sha = str(new_index.get("sha256", "")).lower()
    if len(old_sha) != 64 or len(new_sha) != 64:
        raise UpdateIntakeError("both indexes require SHA-256 authority")

    diff = diff_indexes(old_index, new_index)
    matcher = match_classes(
        old_index,
        new_index,
        prefix=scope_prefix,
    )
    class_delta_report = classify_class_deltas(
        old_index,
        new_index,
        matcher,
    )

    matched_rows: list[dict[str, Any]] = []
    class_counts: dict[str, int] = {}
    review_queue: list[dict[str, Any]] = []

    for match in matcher.get("matches", []):
        classification = _classification(match)
        class_counts[classification] = (
            class_counts.get(classification, 0) + 1
        )
        row = {
            "old": match["old"],
            "new": match["new"],
            "strategy": match["strategy"],
            "classification": classification,
            "score": match["score"],
            "confidence": match["confidence"],
        }
        matched_rows.append(row)

        if match.get("strategy") in _REVIEW_STRATEGIES:
            review_queue.append(
                {
                    "kind": "class_identity_review",
                    "priority": (
                        "high"
                        if match.get("strategy")
                        == "weighted_mutual_best"
                        else "medium"
                    ),
                    "old": match["old"],
                    "new": match["new"],
                    "strategy": match["strategy"],
                    "score": match["score"],
                    "reason": (
                        "Identity is not proven by exact bytes or a unique "
                        "name-insensitive structural fingerprint."
                    ),
                }
            )

    for ambiguous in matcher.get("ambiguous", []):
        review_queue.append(
            {
                "kind": "ambiguous_class_identity",
                "priority": "high",
                "old": ambiguous.get("old"),
                "reason": ambiguous.get(
                    "reason",
                    "matcher reported ambiguity",
                ),
                "candidates": ambiguous.get("candidates", []),
            }
        )

    for path in matcher.get("unmatched_old", []):
        review_queue.append(
            {
                "kind": "unmatched_old_class",
                "priority": "medium",
                "old": path,
                "reason": (
                    "Could be removed code or a matcher miss; do not "
                    "classify as removed automatically."
                ),
            }
        )

    for path in matcher.get("unmatched_new", []):
        review_queue.append(
            {
                "kind": "unmatched_new_class",
                "priority": "medium",
                "new": path,
                "reason": (
                    "Could be genuinely new code or a matcher miss; do not "
                    "promote a new logical ID automatically."
                ),
            }
        )

    changed_same_path_classes = sorted(
        path
        for path in diff.get("changed_same_path", [])
        if path.endswith(".class")
        and (
            scope_prefix is None
            or path.startswith(scope_prefix)
        )
    )

    queue_order = {"high": 0, "medium": 1, "low": 2}
    review_queue.sort(
        key=lambda row: (
            queue_order.get(str(row.get("priority")), 99),
            str(row.get("old", "")),
            str(row.get("new", "")),
            str(row.get("kind", "")),
        )
    )
    matched_rows.sort(
        key=lambda row: (
            row["old"],
            row["new"],
        )
    )

    old_scope = int(
        matcher.get("summary", {}).get("old_class_count", 0)
    )
    matched = int(
        matcher.get("summary", {}).get("matched", 0)
    )
    reuse_percent = (
        round((matched / old_scope) * 100.0, 4)
        if old_scope
        else 0.0
    )

    report_material = {
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "scope_prefix": scope_prefix,
        "diff_summary": diff["summary"],
        "matcher_summary": matcher["summary"],
        "classifications": class_counts,
        "analysis_queue_count": len(review_queue),
    }
    migration_id = (
        "MIGRATION_"
        + hashlib.sha256(_stable_json(report_material))
        .hexdigest()[:20]
        .upper()
    )

    return {
        "schema_version": 1,
        "kind": "update_intake_report",
        "migration_id": migration_id,
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "scope_prefix": scope_prefix,
        "summary": {
            "old_scope_classes": old_scope,
            "new_scope_classes": int(
                matcher.get("summary", {}).get(
                    "new_class_count",
                    0,
                )
            ),
            "matched_classes": matched,
            "class_identity_reuse_percent": reuse_percent,
            "changed_same_path_classes": len(
                changed_same_path_classes
            ),
            "analysis_queue_items": len(review_queue),
            "ambiguous_classes": int(
                matcher.get("summary", {}).get(
                    "ambiguous",
                    0,
                )
            ),
            "unmatched_old_classes": int(
                matcher.get("summary", {}).get(
                    "unmatched_old",
                    0,
                )
            ),
            "unmatched_new_classes": int(
                matcher.get("summary", {}).get(
                    "unmatched_new",
                    0,
                )
            ),
        },
        "classifications": dict(sorted(class_counts.items())),
        "changed_same_path_classes": changed_same_path_classes,
        "matched_classes": matched_rows,
        "analysis_queue": review_queue,
        "diff_summary": diff["summary"],
        "matcher_summary": matcher["summary"],
        "package_anchors": matcher.get("package_anchors", {}),
        "class_delta_report": class_delta_report,
    }


def intake_new_jar(
    old_index: dict[str, Any],
    new_jar: Path,
    *,
    old_build_id: str,
    new_build_id: str,
    scope_prefix: str = "rs/",
) -> tuple[dict[str, Any], dict[str, Any]]:
    new_index = index_jar(new_jar)
    if new_index["summary"]["class_parse_error_count"] != 0:
        raise UpdateIntakeError(
            "new JAR index contains class parse errors; refusing intake"
        )
    report = build_update_intake(
        old_index,
        new_index,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
        scope_prefix=scope_prefix,
    )
    return new_index, report


def write_update_workspace(
    out_dir: Path,
    *,
    new_index: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "new-index.json"
    report_path = out_dir / "migration-report.json"
    queue_path = out_dir / "analysis-queue.json"

    write_index(new_index, index_path)
    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    queue_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "update_analysis_queue",
                "migration_id": report["migration_id"],
                "old_sha256": report["old_sha256"],
                "new_sha256": report["new_sha256"],
                "items": report["analysis_queue"],
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "index": str(index_path),
        "report": str(report_path),
        "queue": str(queue_path),
    }
