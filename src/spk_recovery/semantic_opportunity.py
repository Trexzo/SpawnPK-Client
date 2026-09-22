from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from .coverage import build_coverage_report
from .lineage import validate_lineage
from .member_lineage import validate_member_lineage


class SemanticOpportunityError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _has_build(record: dict[str, Any], build_id: str) -> bool:
    return any(
        entry.get("build_id") == build_id
        for entry in record.get("lineage", [])
    )


def _percent(part: int, whole: int) -> float:
    return round((100.0 * part / whole), 4) if whole else 0.0


def _validate_review(
    review: dict[str, Any],
    *,
    build_id: str,
    source_sha256: str,
) -> None:
    if review.get("schema_version") != 1:
        raise SemanticOpportunityError(
            "semantic review schema_version must be 1"
        )
    if review.get("kind") != "semantic_review_set":
        raise SemanticOpportunityError(
            "expected semantic_review_set"
        )
    if review.get("canonical") is not False:
        raise SemanticOpportunityError(
            "semantic review must be explicitly non-canonical"
        )
    if review.get("source_build") != build_id:
        raise SemanticOpportunityError(
            "semantic review build does not match requested build"
        )
    if str(review.get("source_sha256", "")).lower() != source_sha256:
        raise SemanticOpportunityError(
            "semantic review SHA-256 does not match canonical build"
        )
    proposals = review.get("proposals")
    if not isinstance(proposals, list):
        raise SemanticOpportunityError(
            "semantic review proposals must be an array"
        )
    if review.get("proposal_count") != len(proposals):
        raise SemanticOpportunityError(
            "semantic review proposal_count mismatch"
        )
    if not isinstance(review.get("unresolved"), list):
        raise SemanticOpportunityError(
            "semantic review unresolved must be an array"
        )


def _record_maps(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    *,
    build_id: str,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    classes = {
        str(row.get("logical_id")): row
        for row in class_lineage.get("classes", [])
        if _has_build(row, build_id)
    }
    members = {
        str(row.get("member_id")): row
        for row in member_lineage.get("members", [])
        if _has_build(row, build_id)
    }
    return classes, members


def _evidence_families(
    proposals: list[dict[str, Any]],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for proposal in proposals:
        for item in proposal.get("evidence", []):
            if not isinstance(item, dict):
                continue
            family = item.get("family")
            if isinstance(family, str) and family:
                counts[family] += 1
    return dict(sorted(counts.items()))


def build_semantic_opportunity_report(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    review: dict[str, Any],
    *,
    build_id: str,
) -> dict[str, Any]:
    """Overlay reviewed semantic proposals on canonical coverage without mutation.

    This report never changes semantic status and never implies acceptance. It
    answers only which canonical UNKNOWN/CANDIDATE/ACCEPTED records have reviewed
    semantic proposals available for a later explicit decision.
    """
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    builds = [
        row
        for row in class_lineage.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(builds) != 1:
        raise SemanticOpportunityError(
            f"expected exactly one canonical build {build_id!r}"
        )
    build = builds[0]
    source_sha = str(build.get("sha256", "")).lower()
    _validate_review(
        review,
        build_id=build_id,
        source_sha256=source_sha,
    )

    baseline = build_coverage_report(
        class_lineage,
        member_lineage,
        build_id=build_id,
    )
    class_map, member_map = _record_maps(
        class_lineage,
        member_lineage,
        build_id=build_id,
    )

    rows: list[dict[str, Any]] = []
    seen_targets: set[tuple[str, str]] = set()
    duplicate_targets: list[dict[str, Any]] = []
    missing_targets: list[dict[str, Any]] = []

    for proposal in review.get("proposals", []):
        if not isinstance(proposal, dict):
            raise SemanticOpportunityError(
                "semantic review proposal must be an object"
            )
        kind = proposal.get("target_kind")
        stable_id = proposal.get("stable_id")
        if kind not in {"class", "field", "method"}:
            raise SemanticOpportunityError(
                f"unsupported semantic proposal kind {kind!r}"
            )
        if not isinstance(stable_id, str) or not stable_id:
            raise SemanticOpportunityError(
                "semantic proposal stable_id must be non-empty"
            )

        key = (str(kind), stable_id)
        if key in seen_targets:
            duplicate_targets.append(
                {
                    "target_kind": kind,
                    "stable_id": stable_id,
                    "proposal_id": proposal.get("proposal_id"),
                }
            )
            continue
        seen_targets.add(key)

        record = (
            class_map.get(stable_id)
            if kind == "class"
            else member_map.get(stable_id)
        )
        if record is None:
            missing_targets.append(
                {
                    "target_kind": kind,
                    "stable_id": stable_id,
                    "proposal_id": proposal.get("proposal_id"),
                }
            )
            continue

        if kind != "class" and record.get("kind") != kind:
            raise SemanticOpportunityError(
                f"{stable_id}: proposal/member kind mismatch"
            )

        current_status = str(
            record.get("semantic_status", "UNKNOWN")
        )
        current_name = record.get("semantic_name")
        proposed_name = proposal.get("proposed_name")

        if current_status == "ACCEPTED":
            state = (
                "ALREADY_ACCEPTED_SAME_NAME"
                if current_name == proposed_name
                else "CONFLICTS_WITH_ACCEPTED_NAME"
            )
        elif current_status == "CANDIDATE":
            state = (
                "ALREADY_CANDIDATE_SAME_NAME"
                if current_name == proposed_name
                else "ALTERNATE_TO_CANONICAL_CANDIDATE"
            )
        else:
            state = "REVIEWED_UNKNOWN_TARGET"

        rows.append(
            {
                "proposal_id": proposal.get("proposal_id"),
                "target_kind": kind,
                "stable_id": stable_id,
                "owner_logical_id": proposal.get(
                    "owner_logical_id"
                ),
                "proposed_name": proposed_name,
                "confidence": proposal.get("confidence"),
                "current_semantic_status": current_status,
                "current_semantic_name": current_name,
                "opportunity_state": state,
                "evidence_families": sorted(
                    {
                        str(item.get("family"))
                        for item in proposal.get("evidence", [])
                        if (
                            isinstance(item, dict)
                            and isinstance(
                                item.get("family"),
                                str,
                            )
                            and item.get("family")
                        )
                    }
                ),
            }
        )

    state_counts = Counter(
        row["opportunity_state"] for row in rows
    )
    by_kind: dict[str, dict[str, Any]] = {}
    for kind in ("class", "field", "method"):
        kind_rows = [
            row for row in rows
            if row["target_kind"] == kind
        ]
        reviewed_unknown = sum(
            row["opportunity_state"]
            == "REVIEWED_UNKNOWN_TARGET"
            for row in kind_rows
        )
        canonical = baseline["summary"][
            "classes" if kind == "class" else kind + "s"
        ]
        accepted = int(canonical["accepted"])
        candidate = int(canonical["candidate"])
        total = int(canonical["total"])
        known_or_reviewed = min(
            total,
            accepted + candidate + reviewed_unknown,
        )
        by_kind[kind] = {
            "canonical_total": total,
            "canonical_accepted": accepted,
            "canonical_candidate": candidate,
            "canonical_unknown": int(canonical["unknown"]),
            "reviewed_proposals": len(kind_rows),
            "reviewed_unknown_targets": reviewed_unknown,
            "already_accepted_same_name": sum(
                row["opportunity_state"]
                == "ALREADY_ACCEPTED_SAME_NAME"
                for row in kind_rows
            ),
            "accepted_name_conflicts": sum(
                row["opportunity_state"]
                == "CONFLICTS_WITH_ACCEPTED_NAME"
                for row in kind_rows
            ),
            "reviewed_or_canonical_known_percent": _percent(
                known_or_reviewed,
                total,
            ),
        }

    reviewable = [
        row
        for row in rows
        if row["opportunity_state"]
        in {
            "REVIEWED_UNKNOWN_TARGET",
            "ALREADY_CANDIDATE_SAME_NAME",
            "ALTERNATE_TO_CANONICAL_CANDIDATE",
        }
    ]
    unknown_reviewable = [
        row
        for row in rows
        if row["opportunity_state"]
        == "REVIEWED_UNKNOWN_TARGET"
    ]

    material = {
        "build_id": build_id,
        "source_sha256": source_sha,
        "review_id": review.get("review_id"),
        "baseline_coverage_id": baseline.get("coverage_id"),
        "proposal_ids": sorted(
            str(row.get("proposal_id"))
            for row in rows
        ),
    }
    report_id = (
        "SEMOPP_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "semantic_opportunity_report",
        "canonical": False,
        "report_id": report_id,
        "build_id": build_id,
        "source_sha256": source_sha,
        "review_id": review.get("review_id"),
        "baseline_coverage_id": baseline.get("coverage_id"),
        "summary": {
            "reviewed_proposals": len(rows),
            "reviewable_unaccepted": len(reviewable),
            "reviewed_unknown_targets": len(
                unknown_reviewable
            ),
            "already_accepted_same_name": int(
                state_counts[
                    "ALREADY_ACCEPTED_SAME_NAME"
                ]
            ),
            "accepted_name_conflicts": int(
                state_counts[
                    "CONFLICTS_WITH_ACCEPTED_NAME"
                ]
            ),
            "duplicate_review_targets": len(
                duplicate_targets
            ),
            "missing_review_targets": len(
                missing_targets
            ),
        },
        "by_kind": by_kind,
        "evidence_families": _evidence_families(
            list(review.get("proposals", []))
        ),
        "baseline_coverage": baseline["overall"],
        "opportunities": sorted(
            rows,
            key=lambda row: (
                row["target_kind"],
                row["stable_id"],
                str(row["proposal_id"]),
            ),
        ),
        "duplicate_review_targets": duplicate_targets,
        "missing_review_targets": missing_targets,
    }


def write_semantic_opportunity_report(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
