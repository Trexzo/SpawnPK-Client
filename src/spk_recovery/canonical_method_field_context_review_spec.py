from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .canonical_method_field_context_evidence import (
    CanonicalMethodFieldContextEvidenceError,
    build_canonical_method_field_context_evidence,
)
from .member_lineage import MemberLineageError


class CanonicalMethodFieldContextReviewSpecError(MemberLineageError):
    pass


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _candidate_coord(
    row: dict[str, Any],
    side: str,
) -> tuple[str, str, str]:
    owner = str(row.get(f"{side}_owner", "")).removesuffix(".class")
    coord = row.get(side)
    if not isinstance(coord, dict):
        raise CanonicalMethodFieldContextReviewSpecError(
            f"{side} coordinate must be object"
        )
    name = coord.get("name")
    descriptor = coord.get("descriptor")
    if (
        not owner
        or not isinstance(name, str)
        or not name
        or not isinstance(descriptor, str)
        or not descriptor
    ):
        raise CanonicalMethodFieldContextReviewSpecError(
            f"invalid {side} coordinate"
        )
    return owner, name, descriptor


def _validate_method_witnesses(
    relationship_id: str,
    value: Any,
) -> tuple[int, int, int]:
    if not isinstance(value, list) or not value:
        raise CanonicalMethodFieldContextReviewSpecError(
            f"{relationship_id}: missing method witnesses"
        )

    method_ids: set[str] = set()
    context_digests: set[str] = set()
    observations = 0
    seen_method_op: set[tuple[str, str]] = set()

    for i, witness in enumerate(value):
        if not isinstance(witness, dict):
            raise CanonicalMethodFieldContextReviewSpecError(
                f"{relationship_id}: witness[{i}] must be object"
            )
        method_id = witness.get("method_id")
        operation = witness.get("operation")
        count = witness.get("count")
        contexts = witness.get("contexts")
        if (
            not isinstance(method_id, str)
            or not method_id
            or operation not in {
                "getstatic",
                "putstatic",
                "getfield",
                "putfield",
            }
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count <= 0
            or not isinstance(contexts, list)
            or not contexts
        ):
            raise CanonicalMethodFieldContextReviewSpecError(
                f"{relationship_id}: invalid witness[{i}]"
            )
        key = (method_id, operation)
        if key in seen_method_op:
            raise CanonicalMethodFieldContextReviewSpecError(
                f"{relationship_id}: duplicate method/operation witness"
            )
        seen_method_op.add(key)
        method_ids.add(method_id)

        context_count = 0
        seen_context: set[str] = set()
        for j, row in enumerate(contexts):
            if not isinstance(row, list) or len(row) != 2:
                raise CanonicalMethodFieldContextReviewSpecError(
                    f"{relationship_id}: witness[{i}].contexts[{j}] invalid"
                )
            digest, occurrences = row
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or digest in seen_context
                or not isinstance(occurrences, int)
                or isinstance(occurrences, bool)
                or occurrences <= 0
            ):
                raise CanonicalMethodFieldContextReviewSpecError(
                    f"{relationship_id}: witness[{i}].contexts[{j}] invalid"
                )
            try:
                int(digest, 16)
            except ValueError as exc:
                raise CanonicalMethodFieldContextReviewSpecError(
                    f"{relationship_id}: context digest is not hex"
                ) from exc
            seen_context.add(digest)
            context_digests.add(digest)
            context_count += occurrences

        if context_count != count:
            raise CanonicalMethodFieldContextReviewSpecError(
                f"{relationship_id}: witness context count drift"
            )
        observations += count

    return len(method_ids), observations, len(context_digests)


def build_canonical_method_field_context_review_spec(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
    context_report: dict[str, Any],
) -> dict[str, Any]:
    if (
        context_report.get("schema_version") != 1
        or context_report.get("kind")
        != "canonical_method_field_context_identity_candidates"
        or context_report.get("canonical") is not False
    ):
        raise CanonicalMethodFieldContextReviewSpecError(
            "unsupported canonical-method context report"
        )

    recomputed = build_canonical_method_field_context_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
    )
    if _digest(recomputed) != _digest(context_report):
        raise CanonicalMethodFieldContextReviewSpecError(
            "canonical-method context report does not equal exact-JAR recomputation"
        )

    report_id = context_report.get("report_id")
    old_build_id = context_report.get("old_build_id")
    new_build_id = context_report.get("new_build_id")
    old_sha = str(context_report.get("old_sha256", "")).lower()
    new_sha = str(context_report.get("new_sha256", "")).lower()
    member_digest = context_report.get("member_lineage_digest")
    base_global_id = context_report.get("base_global_usage_report_id")
    base_global_digest = context_report.get(
        "base_global_usage_report_digest"
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
        or not isinstance(member_digest, str)
        or len(member_digest) != 64
        or not isinstance(base_global_id, str)
        or not base_global_id
        or not isinstance(base_global_digest, str)
        or len(base_global_digest) != 64
    ):
        raise CanonicalMethodFieldContextReviewSpecError(
            "canonical-method context report binding is invalid"
        )

    summary = context_report.get("summary")
    candidates = context_report.get("candidates")
    rejected = context_report.get("rejected")
    if (
        not isinstance(summary, dict)
        or not isinstance(candidates, list)
        or not isinstance(rejected, list)
    ):
        raise CanonicalMethodFieldContextReviewSpecError(
            "canonical-method context detail shape is invalid"
        )

    rejection_keys = (
        "canonical_method_context_missing",
        "canonical_method_context_mismatch",
        "canonical_method_context_nonunique",
        "insufficient_independent_context_witness",
        "missing_two_sided_canonical_anchor",
        "canonical_anchor_identity_mismatch",
        "declaration_interval_length_mismatch",
        "declaration_interval_shape_mismatch",
        "target_interval_offset_mismatch",
        "target_declaration_signature_not_unique",
    )
    input_count = summary.get(
        "input_global_class_topology_guard_rejected"
    )
    candidate_count = summary.get("candidate_fields")
    remaining = summary.get("remaining_without_context_proof")
    rejection_counts = [summary.get(key) for key in rejection_keys]
    values = [input_count, candidate_count, remaining, *rejection_counts]
    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        for value in values
    ):
        raise CanonicalMethodFieldContextReviewSpecError(
            "canonical-method context summary accounting is invalid"
        )
    if candidate_count + remaining != input_count:
        raise CanonicalMethodFieldContextReviewSpecError(
            "candidate+remaining context accounting mismatch"
        )
    if len(candidates) != candidate_count or len(rejected) != remaining:
        raise CanonicalMethodFieldContextReviewSpecError(
            "canonical-method context detail count mismatch"
        )
    if sum(rejection_counts) != remaining:
        raise CanonicalMethodFieldContextReviewSpecError(
            "canonical-method context rejection accounting mismatch"
        )

    rejected_ids: set[str] = set()
    reason_tally = {key: 0 for key in rejection_keys}
    for i, row in enumerate(rejected):
        if not isinstance(row, dict):
            raise CanonicalMethodFieldContextReviewSpecError(
                f"rejected[{i}] must be object"
            )
        relationship_id = row.get("relationship_id")
        reason = row.get("reason")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in rejected_ids
            or reason not in reason_tally
        ):
            raise CanonicalMethodFieldContextReviewSpecError(
                f"rejected[{i}] has invalid id/reason"
            )
        if (
            row.get("base_global_usage_outcome")
            != "global_class_topology_guard_rejected"
        ):
            raise CanonicalMethodFieldContextReviewSpecError(
                f"{relationship_id}: rejected row lost base global veto"
            )
        rejected_ids.add(relationship_id)
        reason_tally[reason] += 1

    for key in rejection_keys:
        if reason_tally[key] != summary[key]:
            raise CanonicalMethodFieldContextReviewSpecError(
                f"rejected detail accounting mismatch for {key}"
            )

    relationship_ids: list[str] = []
    seen_ids: set[str] = set()
    seen_old: set[tuple[str, str, str]] = set()
    seen_new: set[tuple[str, str, str]] = set()

    for i, row in enumerate(candidates):
        label = f"candidates[{i}]"
        if not isinstance(row, dict):
            raise CanonicalMethodFieldContextReviewSpecError(
                f"{label} must be object"
            )
        if (
            row.get("strategy")
            != (
                "canonical_method_unique_local_context_and_"
                "canonical_anchor_declaration_interval_exact"
            )
            or row.get("supports_existing_review") is not True
            or row.get("confidence") != "INFERRED_HIGH"
            or float(row.get("score", 0.0)) != 0.9994
            or row.get("base_global_usage_outcome")
            != "global_class_topology_guard_rejected"
            or row.get("base_global_usage_report_id") != base_global_id
        ):
            raise CanonicalMethodFieldContextReviewSpecError(
                f"{label} is not trusted method-context evidence"
            )

        relationship_id = row.get("relationship_id")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in seen_ids
            or relationship_id in rejected_ids
        ):
            raise CanonicalMethodFieldContextReviewSpecError(
                f"{label} has invalid/duplicate/overlapping relationship_id"
            )
        seen_ids.add(relationship_id)

        old_coord = _candidate_coord(row, "old")
        new_coord = _candidate_coord(row, "new")
        if old_coord in seen_old or new_coord in seen_new:
            raise CanonicalMethodFieldContextReviewSpecError(
                f"{relationship_id}: duplicate candidate coordinate"
            )
        seen_old.add(old_coord)
        seen_new.add(new_coord)

        method_count, observations, distinct_contexts = (
            _validate_method_witnesses(
                relationship_id,
                row.get("method_witnesses"),
            )
        )
        if (
            row.get("canonical_methods") != method_count
            or row.get("observations") != observations
            or row.get("distinct_contexts") != distinct_contexts
        ):
            raise CanonicalMethodFieldContextReviewSpecError(
                f"{relationship_id}: witness summary drift"
            )
        if not (
            method_count >= 2
            or (observations >= 2 and distinct_contexts >= 2)
        ):
            raise CanonicalMethodFieldContextReviewSpecError(
                f"{relationship_id}: insufficient independent witness"
            )

        left = row.get("left_anchor_member_id")
        right = row.get("right_anchor_member_id")
        digest = row.get("interval_digest")
        length = row.get("interval_length")
        offset = row.get("interval_offset")
        old_ordinal = row.get("old_field_ordinal")
        new_ordinal = row.get("new_field_ordinal")
        if (
            not isinstance(left, str)
            or not left
            or not isinstance(right, str)
            or not right
            or left == right
            or not isinstance(digest, str)
            or len(digest) != 64
            or not isinstance(length, int)
            or isinstance(length, bool)
            or length <= 0
            or not isinstance(offset, int)
            or isinstance(offset, bool)
            or offset < 0
            or offset >= length
            or not isinstance(old_ordinal, int)
            or isinstance(old_ordinal, bool)
            or old_ordinal < 0
            or not isinstance(new_ordinal, int)
            or isinstance(new_ordinal, bool)
            or new_ordinal < 0
        ):
            raise CanonicalMethodFieldContextReviewSpecError(
                f"{relationship_id}: invalid anchor/interval evidence"
            )

        relationship_ids.append(relationship_id)

    if not relationship_ids:
        raise CanonicalMethodFieldContextReviewSpecError(
            "canonical-method context report contains no reviewable candidates"
        )

    return {
        "schema_version": 1,
        "kind": "reviewed_member_identity_acceptance_spec",
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "note": (
            f"Explicitly reviewed from {report_id}: the prior complete global "
            "source-class topology veto remains recorded, while field continuity "
            "is independently re-proven inside paired canonical methods by exact "
            "name-insensitive local JVM context multisets that are unique against "
            "same-shape competitor fields in both builds. The unchanged two-sided "
            "canonical declaration interval proof was recomputed exactly. Rejected "
            "rows remain unresolved."
        ),
        "evidence": [
            f"report_id={report_id}",
            f"report_digest_sha256={_digest(context_report)}",
            f"base_global_usage_report_id={base_global_id}",
            f"base_global_usage_report_digest_sha256={base_global_digest}",
            f"member_lineage_digest_sha256={member_digest}",
            (
                "strategy=canonical_method_unique_local_context_and_"
                "canonical_anchor_declaration_interval_exact"
            ),
            f"reviewed_candidates={len(relationship_ids)}",
            f"remaining_without_context_proof={remaining}",
        ],
        "relationship_ids": sorted(relationship_ids),
    }


def write_spec(spec: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            spec,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
