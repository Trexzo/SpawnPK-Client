from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .canonicalize import CandidateApplicationError, apply_lineage_candidates
from .lineage import LineageValidationError, validate_lineage, write_lineage
from .lineage_candidates import build_lineage_candidates
from .matcher import match_classes


class UpdateTransferError(LineageValidationError):
    pass


_TRUSTED_AUTO_STRATEGIES = {"exact_sha256", "structural_unique"}


def _validate_intake_binding(
    intake_report: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
) -> None:
    if (
        intake_report.get("schema_version") != 1
        or intake_report.get("kind") != "update_intake_report"
    ):
        raise UpdateTransferError("unsupported intake report schema/kind")
    if intake_report.get("old_build_id") != old_build_id:
        raise UpdateTransferError("intake old_build_id mismatch")
    if intake_report.get("new_build_id") != new_build_id:
        raise UpdateTransferError("intake new_build_id mismatch")
    if (
        str(intake_report.get("old_sha256", "")).lower()
        != str(old_index.get("sha256", "")).lower()
    ):
        raise UpdateTransferError("intake old SHA does not match old index")
    if (
        str(intake_report.get("new_sha256", "")).lower()
        != str(new_index.get("sha256", "")).lower()
    ):
        raise UpdateTransferError("intake new SHA does not match new index")


def _trusted_match_report(
    matcher_report: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    trusted: list[dict[str, Any]] = []
    review_only: list[dict[str, Any]] = []

    for match in matcher_report.get("matches", []):
        if match.get("strategy") in _TRUSTED_AUTO_STRATEGIES:
            trusted.append(copy.deepcopy(match))
        else:
            review_only.append(
                {
                    "old": match.get("old"),
                    "proposed_new": match.get("new"),
                    "strategy": match.get("strategy"),
                    "score": match.get("score"),
                    "confidence": match.get("confidence"),
                    "reason": "identity_requires_explicit_review_before_canonical_transfer",
                    "evidence": copy.deepcopy(match.get("evidence", {})),
                }
            )

    ambiguous = list(copy.deepcopy(matcher_report.get("ambiguous", [])))
    ambiguous.extend(review_only)

    filtered = {
        "schema_version": matcher_report.get("schema_version", 1),
        "old_sha256": matcher_report.get("old_sha256"),
        "new_sha256": matcher_report.get("new_sha256"),
        "scope_prefix": matcher_report.get("scope_prefix"),
        "thresholds": copy.deepcopy(matcher_report.get("thresholds", {})),
        "package_anchors": copy.deepcopy(matcher_report.get("package_anchors", {})),
        "summary": copy.deepcopy(matcher_report.get("summary", {})),
        "matches": trusted,
        "ambiguous": ambiguous,
        "unmatched_old": copy.deepcopy(matcher_report.get("unmatched_old", [])),
        "unmatched_new": copy.deepcopy(matcher_report.get("unmatched_new", [])),
    }
    return filtered, {
        "trusted_exact": sum(
            1 for row in trusted if row.get("strategy") == "exact_sha256"
        ),
        "trusted_structural": sum(
            1 for row in trusted if row.get("strategy") == "structural_unique"
        ),
        "review_only_matches": len(review_only),
    }


def transfer_trusted_class_lineage(
    lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    intake_report: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
    new_build_number: int | None,
    new_authority: str = "CROSS_BUILD",
) -> tuple[dict[str, Any], dict[str, Any]]:
    validate_lineage(lineage)
    _validate_intake_binding(
        intake_report,
        old_index,
        new_index,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )

    scope_prefix = intake_report.get("scope_prefix", "rs/")
    if not isinstance(scope_prefix, str):
        raise UpdateTransferError("intake scope_prefix must be a string")

    matcher_report = match_classes(
        old_index,
        new_index,
        prefix=scope_prefix,
    )
    filtered, trust_summary = _trusted_match_report(matcher_report)
    candidates = build_lineage_candidates(
        old_index,
        new_index,
        filtered,
        old_build=old_build_id,
        new_build=new_build_id,
    )

    try:
        out, canonical_summary = apply_lineage_candidates(
            lineage,
            old_index,
            new_index,
            candidates,
            old_build_id=old_build_id,
            new_build_id=new_build_id,
            new_build_number=new_build_number,
            new_authority=new_authority,
        )
    except CandidateApplicationError as exc:
        raise UpdateTransferError(str(exc)) from exc

    summary = {
        "migration_id": intake_report.get("migration_id"),
        "new_build_id": new_build_id,
        **trust_summary,
        "trusted_applied": canonical_summary["applied_relationships"],
        "unresolved_added": canonical_summary["unresolved_added"],
        "canonical_logical_classes": canonical_summary["logical_classes"],
        "canonical_builds": canonical_summary["builds"],
    }
    return out, summary


def write_transfer_result(
    lineage: dict[str, Any],
    summary: dict[str, Any],
    *,
    lineage_out: Path,
    summary_out: Path | None = None,
) -> None:
    import json

    write_lineage(lineage, lineage_out)
    if summary_out is not None:
        summary_out.parent.mkdir(parents=True, exist_ok=True)
        summary_out.write_text(
            json.dumps(
                summary,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
