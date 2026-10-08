from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .canonical_method_boundary_block_evidence import (
    CanonicalMethodBoundaryBlockEvidenceError,
    _witness_stats,
    build_canonical_method_boundary_block_evidence,
)
from .member_lineage import MemberLineageError


class CanonicalMethodBoundaryBlockReviewSpecError(MemberLineageError):
    pass


_REASONS = (
    "boundary_symmetry_mismatch",
    "single_anchor_identity_mismatch",
    "block_length_mismatch",
    "block_shape_mismatch",
    "target_offset_mismatch",
    "target_signature_not_unique",
)
_MODES = {
    "prefix_block_exact",
    "suffix_block_exact",
    "whole_class_exact",
}


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _hex_digest(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            f"{label} must be a 64-character digest"
        )
    try:
        int(value, 16)
    except ValueError as exc:
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            f"{label} is not hex"
        ) from exc
    return value


def _candidate_coord(
    row: dict[str, Any],
    side: str,
) -> tuple[str, str, str]:
    owner = row.get(f"{side}_owner")
    coord = row.get(side)
    if (
        not isinstance(owner, str)
        or not owner
        or not isinstance(coord, dict)
        or not isinstance(coord.get("name"), str)
        or not coord.get("name")
        or not isinstance(coord.get("descriptor"), str)
        or not coord.get("descriptor")
    ):
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            f"invalid {side} candidate coordinate"
        )
    return owner, coord["name"], coord["descriptor"]


def build_canonical_method_boundary_block_review_spec(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
    context_report: dict[str, Any],
    boundary_report: dict[str, Any],
) -> dict[str, Any]:
    recomputed = build_canonical_method_boundary_block_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
        context_report,
    )
    if _digest(recomputed) != _digest(boundary_report):
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "method-context boundary report does not equal exact-JAR recomputation"
        )

    if (
        boundary_report.get("schema_version") != 1
        or boundary_report.get("kind")
        != "canonical_method_boundary_block_identity_candidates"
        or boundary_report.get("canonical") is not False
    ):
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "unsupported method-context boundary report"
        )

    report_id = boundary_report.get("report_id")
    old_build_id = boundary_report.get("old_build_id")
    new_build_id = boundary_report.get("new_build_id")
    old_sha = str(boundary_report.get("old_sha256", "")).lower()
    new_sha = str(boundary_report.get("new_sha256", "")).lower()
    member_digest = boundary_report.get("member_lineage_digest")
    base_global_id = boundary_report.get("base_global_usage_report_id")
    base_global_digest = boundary_report.get(
        "base_global_usage_report_digest"
    )
    base_context_id = boundary_report.get("base_context_report_id")
    base_context_digest = boundary_report.get(
        "base_context_report_digest"
    )

    if (
        not isinstance(report_id, str)
        or not report_id
        or not isinstance(old_build_id, str)
        or not old_build_id
        or not isinstance(new_build_id, str)
        or not new_build_id
        or old_build_id == new_build_id
        or len(old_sha) != 64
        or len(new_sha) != 64
        or not isinstance(base_global_id, str)
        or not base_global_id
        or not isinstance(base_context_id, str)
        or not base_context_id
    ):
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "method-context boundary binding is invalid"
        )

    _hex_digest(old_sha, label="old_sha256")
    _hex_digest(new_sha, label="new_sha256")
    _hex_digest(member_digest, label="member_lineage_digest")
    _hex_digest(
        base_global_digest,
        label="base_global_usage_report_digest",
    )
    _hex_digest(
        base_context_digest,
        label="base_context_report_digest",
    )

    if global_usage_report.get("report_id") != base_global_id:
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "base global usage report ID drift"
        )
    if _digest(global_usage_report) != base_global_digest:
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "base global usage report digest drift"
        )
    if context_report.get("report_id") != base_context_id:
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "base context report ID drift"
        )
    if _digest(context_report) != base_context_digest:
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "base context report digest drift"
        )

    summary = boundary_report.get("summary")
    candidates = boundary_report.get("candidates")
    rejected = boundary_report.get("rejected")
    if (
        not isinstance(summary, dict)
        or not isinstance(candidates, list)
        or not isinstance(rejected, list)
    ):
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "method-context boundary detail shape is invalid"
        )

    input_count = summary.get("input_context_missing_anchor_reviews")
    candidate_count = summary.get("candidate_fields")
    remaining = summary.get("remaining_without_boundary_block_proof")
    mode_counts = [summary.get(mode) for mode in sorted(_MODES)]
    rejection_counts = [summary.get(reason) for reason in _REASONS]
    values = [
        input_count,
        candidate_count,
        remaining,
        *mode_counts,
        *rejection_counts,
    ]
    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        for value in values
    ):
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "method-context boundary summary accounting is invalid"
        )
    if candidate_count + remaining != input_count:
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "candidate+remaining boundary accounting mismatch"
        )
    if len(candidates) != candidate_count or len(rejected) != remaining:
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "boundary detail count mismatch"
        )
    if sum(mode_counts) != candidate_count:
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "boundary mode accounting mismatch"
        )
    if sum(rejection_counts) != remaining:
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "boundary rejection accounting mismatch"
        )

    rejected_ids: set[str] = set()
    reason_tally = {reason: 0 for reason in _REASONS}
    for i, row in enumerate(rejected):
        if not isinstance(row, dict):
            raise CanonicalMethodBoundaryBlockReviewSpecError(
                f"rejected[{i}] must be object"
            )
        relationship_id = row.get("relationship_id")
        reason = row.get("reason")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in rejected_ids
            or reason not in reason_tally
            or row.get("base_context_reason")
            != "missing_two_sided_canonical_anchor"
        ):
            raise CanonicalMethodBoundaryBlockReviewSpecError(
                f"rejected[{i}] has invalid identity/reason binding"
            )
        rejected_ids.add(relationship_id)
        reason_tally[reason] += 1

    for reason in _REASONS:
        if reason_tally[reason] != summary[reason]:
            raise CanonicalMethodBoundaryBlockReviewSpecError(
                f"rejected detail accounting mismatch for {reason}"
            )

    relationship_ids: list[str] = []
    seen_ids: set[str] = set()
    seen_old: set[tuple[str, str, str]] = set()
    seen_new: set[tuple[str, str, str]] = set()
    candidate_mode_tally = {mode: 0 for mode in _MODES}

    for i, row in enumerate(candidates):
        label = f"candidates[{i}]"
        if not isinstance(row, dict):
            raise CanonicalMethodBoundaryBlockReviewSpecError(
                f"{label} must be object"
            )

        if (
            row.get("strategy")
            != (
                "canonical_method_unique_local_context_and_"
                "boundary_block_declaration_exact"
            )
            or row.get("supports_existing_review") is not True
            or row.get("confidence") != "INFERRED_HIGH"
            or float(row.get("score", 0.0)) != 0.9995
            or row.get("base_context_report_id") != base_context_id
            or row.get("base_context_report_digest") != base_context_digest
            or row.get("base_context_reason")
            != "missing_two_sided_canonical_anchor"
            or row.get("base_global_usage_report_id") != base_global_id
        ):
            raise CanonicalMethodBoundaryBlockReviewSpecError(
                f"{label} is not trusted method-context boundary evidence"
            )

        relationship_id = row.get("relationship_id")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in seen_ids
            or relationship_id in rejected_ids
        ):
            raise CanonicalMethodBoundaryBlockReviewSpecError(
                f"{label} has invalid/duplicate/overlapping relationship_id"
            )
        seen_ids.add(relationship_id)

        old_coord = _candidate_coord(row, "old")
        new_coord = _candidate_coord(row, "new")
        if old_coord in seen_old or new_coord in seen_new:
            raise CanonicalMethodBoundaryBlockReviewSpecError(
                f"{relationship_id}: duplicate candidate coordinate"
            )
        seen_old.add(old_coord)
        seen_new.add(new_coord)

        method_count, observations, distinct_contexts = _witness_stats(
            relationship_id,
            row.get("method_witnesses"),
        )
        if (
            row.get("canonical_methods") != method_count
            or row.get("observations") != observations
            or row.get("distinct_contexts") != distinct_contexts
        ):
            raise CanonicalMethodBoundaryBlockReviewSpecError(
                f"{relationship_id}: witness summary drift"
            )
        if not (
            method_count >= 2
            or (observations >= 2 and distinct_contexts >= 2)
        ):
            raise CanonicalMethodBoundaryBlockReviewSpecError(
                f"{relationship_id}: insufficient independent witness"
            )

        mode = row.get("block_kind")
        anchor = row.get("anchor_member_id")
        block_length = row.get("block_length")
        target_offset = row.get("target_offset")
        if (
            mode not in _MODES
            or not isinstance(block_length, int)
            or isinstance(block_length, bool)
            or block_length <= 0
            or not isinstance(target_offset, int)
            or isinstance(target_offset, bool)
            or target_offset < 0
            or target_offset >= block_length
        ):
            raise CanonicalMethodBoundaryBlockReviewSpecError(
                f"{relationship_id}: invalid boundary block evidence"
            )
        if mode == "whole_class_exact":
            if anchor is not None:
                raise CanonicalMethodBoundaryBlockReviewSpecError(
                    f"{relationship_id}: whole-class proof cannot carry anchor"
                )
        elif not isinstance(anchor, str) or not anchor:
            raise CanonicalMethodBoundaryBlockReviewSpecError(
                f"{relationship_id}: boundary proof requires canonical anchor"
            )

        _hex_digest(row.get("block_digest"), label="block_digest")
        _hex_digest(
            row.get("target_signature_digest"),
            label="target_signature_digest",
        )
        candidate_mode_tally[mode] += 1
        relationship_ids.append(relationship_id)

    for mode in _MODES:
        if candidate_mode_tally[mode] != summary[mode]:
            raise CanonicalMethodBoundaryBlockReviewSpecError(
                f"candidate mode accounting mismatch for {mode}"
            )

    if not relationship_ids:
        raise CanonicalMethodBoundaryBlockReviewSpecError(
            "method-context boundary report contains no reviewable candidates"
        )

    return {
        "schema_version": 1,
        "kind": "reviewed_member_identity_acceptance_spec",
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "note": (
            f"Explicitly reviewed from {report_id}: field continuity was "
            "already independently proven by the strong exact paired "
            "canonical-method local-context witness. The missing two-sided "
            "declaration anchor was replaced only by an exact symmetric "
            "prefix/suffix/whole-class boundary block with matching canonical "
            "single-anchor identity where present, identical block shape and "
            "target offset, and a unique target declaration signature. "
            "Rejected rows remain unresolved."
        ),
        "evidence": [
            f"report_id={report_id}",
            f"report_digest_sha256={_digest(boundary_report)}",
            f"base_context_report_id={base_context_id}",
            f"base_context_report_digest_sha256={base_context_digest}",
            f"base_global_usage_report_id={base_global_id}",
            f"base_global_usage_report_digest_sha256={base_global_digest}",
            f"member_lineage_digest_sha256={member_digest}",
            (
                "strategy=canonical_method_unique_local_context_and_"
                "boundary_block_declaration_exact"
            ),
            f"reviewed_candidates={len(relationship_ids)}",
            f"remaining_without_boundary_block_proof={remaining}",
        ],
        "relationship_ids": sorted(relationship_ids),
    }


def write_spec(spec: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
