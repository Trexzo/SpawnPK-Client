from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .canonical_method_partial_multimethod_context_evidence import (
    CanonicalMethodPartialMultimethodContextEvidenceError,
    build_canonical_method_partial_multimethod_context_evidence,
)
from .lineage import LineageValidationError, load_lineage
from .member_lineage import MemberLineageError, load_member_lineage


class CanonicalMethodPartialMultimethodContextReviewSpecError(MemberLineageError):
    pass


_FIELD_OPS = {"getstatic", "putstatic", "getfield", "putfield"}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            f"JSON root must be object: {path}"
        )
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _hex(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            f"{label} must be 64-char hex"
        )
    try:
        int(value, 16)
    except ValueError as exc:
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            f"{label} is not hex"
        ) from exc
    return value


def _coord(row: dict[str, Any], side: str) -> tuple[str, str, str]:
    owner = str(row.get(f"{side}_owner", "")).removesuffix(".class")
    value = row.get(side)
    if not isinstance(value, dict):
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            f"{side} coordinate must be object"
        )
    name = value.get("name")
    descriptor = value.get("descriptor")
    if (
        not owner
        or not isinstance(name, str)
        or not name
        or not isinstance(descriptor, str)
        or not descriptor
    ):
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            f"invalid {side} coordinate"
        )
    return owner, name, descriptor


def _validate_contexts(value: Any) -> tuple[int, set[str]]:
    if not isinstance(value, list) or not value:
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            "missing witness contexts"
        )
    observations = 0
    digests: set[str] = set()
    for i, row in enumerate(value):
        if not isinstance(row, list) or len(row) != 2:
            raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                f"contexts[{i}] invalid"
            )
        digest, count = row
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or digest in digests
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count <= 0
        ):
            raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                f"contexts[{i}] invalid"
            )
        _hex(digest, label=f"contexts[{i}].digest")
        digests.add(digest)
        observations += count
    return observations, digests


def build_canonical_method_partial_multimethod_context_review_spec(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
    context_report: dict[str, Any],
    partial_report: dict[str, Any],
) -> dict[str, Any]:
    if (
        partial_report.get("schema_version") != 1
        or partial_report.get("kind")
        != "canonical_method_partial_multimethod_context_identity_candidates"
        or partial_report.get("canonical") is not False
    ):
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            "unsupported partial multimethod context report"
        )

    recomputed = build_canonical_method_partial_multimethod_context_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
        context_report,
    )
    if _digest(recomputed) != _digest(partial_report):
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            "partial multimethod context report does not equal exact-JAR recomputation"
        )

    report_id = partial_report.get("report_id")
    old_build_id = partial_report.get("old_build_id")
    new_build_id = partial_report.get("new_build_id")
    old_sha = str(partial_report.get("old_sha256", "")).lower()
    new_sha = str(partial_report.get("new_sha256", "")).lower()
    member_digest = partial_report.get("member_lineage_digest")
    base_global_id = partial_report.get("base_global_usage_report_id")
    base_global_digest = partial_report.get("base_global_usage_report_digest")
    base_context_id = partial_report.get("base_context_report_id")
    base_context_digest = partial_report.get("base_context_report_digest")
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
        or not isinstance(base_context_id, str)
        or not base_context_id
        or not isinstance(base_context_digest, str)
        or len(base_context_digest) != 64
    ):
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            "partial multimethod context report binding is invalid"
        )

    summary = partial_report.get("summary")
    candidates = partial_report.get("candidates")
    rejected = partial_report.get("rejected")
    if (
        not isinstance(summary, dict)
        or not isinstance(candidates, list)
        or not isinstance(rejected, list)
    ):
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            "partial multimethod context detail shape is invalid"
        )

    rejection_keys = (
        "no_symmetric_unavailable_context",
        "partial_context_observation_count_mismatch",
        "partial_context_mismatch",
        "partial_context_nonunique",
        "insufficient_surviving_context_witness",
        "missing_two_sided_canonical_anchor",
        "canonical_anchor_identity_mismatch",
        "declaration_interval_length_mismatch",
        "declaration_interval_shape_mismatch",
        "target_interval_offset_mismatch",
        "target_declaration_signature_not_unique",
    )
    input_count = summary.get("input_missing_context_reviews")
    candidate_count = summary.get("candidate_fields")
    remaining = summary.get("remaining_without_partial_context_proof")
    rejection_counts = [summary.get(key) for key in rejection_keys]
    values = [input_count, candidate_count, remaining, *rejection_counts]
    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        for value in values
    ):
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            "partial multimethod context summary accounting is invalid"
        )
    if candidate_count + remaining != input_count:
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            "candidate+remaining accounting mismatch"
        )
    if len(candidates) != candidate_count or len(rejected) != remaining:
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            "partial multimethod context detail count mismatch"
        )
    if sum(rejection_counts) != remaining:
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            "partial multimethod rejection accounting mismatch"
        )

    reason_tally = {key: 0 for key in rejection_keys}
    rejected_ids: set[str] = set()
    for i, row in enumerate(rejected):
        if not isinstance(row, dict):
            raise CanonicalMethodPartialMultimethodContextReviewSpecError(
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
            != "canonical_method_context_missing"
        ):
            raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                f"rejected[{i}] has invalid id/reason/base binding"
            )
        rejected_ids.add(relationship_id)
        reason_tally[reason] += 1
    for key in rejection_keys:
        if reason_tally[key] != summary[key]:
            raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                f"rejected detail accounting mismatch for {key}"
            )

    relationship_ids: list[str] = []
    seen_ids: set[str] = set()
    seen_old: set[tuple[str, str, str]] = set()
    seen_new: set[tuple[str, str, str]] = set()

    for i, row in enumerate(candidates):
        label = f"candidates[{i}]"
        if not isinstance(row, dict):
            raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                f"{label} must be object"
            )
        if (
            row.get("strategy")
            != (
                "canonical_method_partial_multimethod_unique_context_and_"
                "canonical_anchor_declaration_interval_exact"
            )
            or row.get("supports_existing_review") is not True
            or row.get("confidence") != "INFERRED_HIGH"
            or float(row.get("score", 0.0)) != 0.9993
            or row.get("base_context_reason")
            != "canonical_method_context_missing"
            or row.get("base_context_report_id") != base_context_id
            or row.get("base_global_usage_report_id") != base_global_id
        ):
            raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                f"{label} is not trusted partial multimethod context evidence"
            )

        relationship_id = row.get("relationship_id")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in seen_ids
            or relationship_id in rejected_ids
        ):
            raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                f"{label} has invalid/duplicate/overlapping relationship_id"
            )
        seen_ids.add(relationship_id)

        old_coord = _coord(row, "old")
        new_coord = _coord(row, "new")
        if old_coord in seen_old or new_coord in seen_new:
            raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                f"{relationship_id}: duplicate candidate coordinate"
            )
        seen_old.add(old_coord)
        seen_new.add(new_coord)

        witnesses = row.get("method_witnesses")
        unavailable = row.get("symmetric_unavailable_methods")
        if (
            not isinstance(witnesses, list)
            or not witnesses
            or not isinstance(unavailable, list)
            or not unavailable
        ):
            raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                f"{relationship_id}: missing witness/unavailable details"
            )

        method_ids: set[str] = set()
        all_contexts: set[str] = set()
        observations = 0
        for j, witness in enumerate(witnesses):
            if not isinstance(witness, dict):
                raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                    f"{relationship_id}: witness[{j}] invalid"
                )
            method_id = witness.get("method_id")
            operation = witness.get("operation")
            count = witness.get("count")
            if (
                not isinstance(method_id, str)
                or not method_id
                or method_id in method_ids
                or operation not in _FIELD_OPS
                or not isinstance(count, int)
                or isinstance(count, bool)
                or count <= 0
            ):
                raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                    f"{relationship_id}: witness[{j}] invalid"
                )
            context_count, digests = _validate_contexts(witness.get("contexts"))
            if context_count != count:
                raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                    f"{relationship_id}: witness[{j}] context count drift"
                )
            method_ids.add(method_id)
            all_contexts.update(digests)
            observations += count

        unavailable_ids: set[str] = set()
        for j, value in enumerate(unavailable):
            if not isinstance(value, dict):
                raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                    f"{relationship_id}: unavailable[{j}] invalid"
                )
            method_id = value.get("method_id")
            operation = value.get("operation")
            expected = value.get("expected_count")
            if (
                not isinstance(method_id, str)
                or not method_id
                or method_id in unavailable_ids
                or method_id in method_ids
                or operation not in _FIELD_OPS
                or not isinstance(expected, int)
                or isinstance(expected, bool)
                or expected <= 0
                or value.get("old_context_count") != 0
                or value.get("new_context_count") != 0
            ):
                raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                    f"{relationship_id}: unavailable[{j}] invalid"
                )
            unavailable_ids.add(method_id)

        if (
            row.get("canonical_methods") != len(method_ids)
            or row.get("observations") != observations
            or row.get("distinct_contexts") != len(all_contexts)
            or not (
                len(method_ids) >= 2
                or (observations >= 2 and len(all_contexts) >= 2)
            )
        ):
            raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                f"{relationship_id}: surviving witness summary drift"
            )

        left = row.get("left_anchor_member_id")
        right = row.get("right_anchor_member_id")
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
            raise CanonicalMethodPartialMultimethodContextReviewSpecError(
                f"{relationship_id}: invalid declaration interval evidence"
            )
        _hex(row.get("interval_digest"), label="interval_digest")
        _hex(row.get("target_signature_digest"), label="target_signature_digest")
        relationship_ids.append(relationship_id)

    if not relationship_ids:
        raise CanonicalMethodPartialMultimethodContextReviewSpecError(
            "partial multimethod context report contains no reviewable candidates"
        )

    return {
        "schema_version": 1,
        "kind": "reviewed_member_identity_acceptance_spec",
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "note": (
            f"Explicitly reviewed from {report_id}: symmetric old/new context "
            "unavailability remains recorded. One-sided loss, mismatch, and "
            "nonuniqueness are refused. Surviving canonical methods meet the "
            "existing independent-witness threshold and exact two-sided "
            "declaration continuity was recomputed. Rejected rows remain "
            "unresolved."
        ),
        "evidence": [
            f"report_id={report_id}",
            f"report_digest_sha256={_digest(partial_report)}",
            f"base_context_report_id={base_context_id}",
            f"base_context_report_digest_sha256={base_context_digest}",
            f"base_global_usage_report_id={base_global_id}",
            f"base_global_usage_report_digest_sha256={base_global_digest}",
            f"member_lineage_digest_sha256={member_digest}",
            (
                "strategy=canonical_method_partial_multimethod_unique_context_and_"
                "canonical_anchor_declaration_interval_exact"
            ),
            f"reviewed_candidates={len(relationship_ids)}",
            f"remaining_without_partial_context_proof={remaining}",
        ],
        "relationship_ids": sorted(relationship_ids),
    }


def write_spec(spec: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-canonical-method-partial-multimethod-context-review-spec"
    )
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("old_index", type=Path)
    p.add_argument("new_index", type=Path)
    p.add_argument("old_jar", type=Path)
    p.add_argument("new_jar", type=Path)
    p.add_argument("global_usage_report", type=Path)
    p.add_argument("context_report", type=Path)
    p.add_argument("partial_report", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        spec = build_canonical_method_partial_multimethod_context_review_spec(
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.old_index),
            _load(args.new_index),
            args.old_jar,
            args.new_jar,
            _load(args.global_usage_report),
            _load(args.context_report),
            _load(args.partial_report),
        )
        write_spec(spec, args.out)
    except (
        CanonicalMethodPartialMultimethodContextReviewSpecError,
        CanonicalMethodPartialMultimethodContextEvidenceError,
        LineageValidationError,
        MemberLineageError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(
            "SPK_CANONICAL_METHOD_PARTIAL_MULTIMETHOD_CONTEXT_REVIEW_SPEC_FAIL",
            file=__import__("sys").stderr,
        )
        print(str(exc), file=__import__("sys").stderr)
        return 1

    print("SPK_CANONICAL_METHOD_PARTIAL_MULTIMETHOD_CONTEXT_REVIEW_SPEC_PASS")
    print(f"relationship_ids={len(spec['relationship_ids'])}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
