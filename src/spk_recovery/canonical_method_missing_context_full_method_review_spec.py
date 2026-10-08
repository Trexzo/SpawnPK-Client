from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .canonical_method_missing_context_full_method_evidence import (
    CanonicalMethodMissingContextFullMethodEvidenceError,
    build_canonical_method_missing_context_full_method_evidence,
)
from .lineage import LineageValidationError, load_lineage
from .member_lineage import MemberLineageError, load_member_lineage


class CanonicalMethodMissingContextFullMethodReviewSpecError(MemberLineageError):
    pass


_FIELD_OPS = {"getstatic", "putstatic", "getfield", "putfield"}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
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
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
            f"{label} must be 64-char hex digest"
        )
    try:
        int(value, 16)
    except ValueError as exc:
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
            f"{label} is not hex"
        ) from exc
    return value


def _coord(row: dict[str, Any], side: str) -> tuple[str, str, str]:
    owner = str(row.get(f"{side}_owner", "")).removesuffix(".class")
    value = row.get(side)
    if not isinstance(value, dict):
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
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
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
            f"invalid {side} coordinate"
        )
    return owner, name, descriptor


def build_canonical_method_missing_context_full_method_review_spec(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
    context_report: dict[str, Any],
    full_method_report: dict[str, Any],
) -> dict[str, Any]:
    if (
        full_method_report.get("schema_version") != 1
        or full_method_report.get("kind")
        != "canonical_method_missing_context_full_method_identity_candidates"
        or full_method_report.get("canonical") is not False
    ):
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
            "unsupported missing-context full-method report"
        )

    recomputed = build_canonical_method_missing_context_full_method_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
        context_report,
    )
    if _digest(recomputed) != _digest(full_method_report):
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
            "missing-context full-method report does not equal exact-JAR recomputation"
        )

    report_id = full_method_report.get("report_id")
    old_build_id = full_method_report.get("old_build_id")
    new_build_id = full_method_report.get("new_build_id")
    old_sha = str(full_method_report.get("old_sha256", "")).lower()
    new_sha = str(full_method_report.get("new_sha256", "")).lower()
    member_digest = full_method_report.get("member_lineage_digest")
    base_global_id = full_method_report.get("base_global_usage_report_id")
    base_global_digest = full_method_report.get("base_global_usage_report_digest")
    base_context_id = full_method_report.get("base_context_report_id")
    base_context_digest = full_method_report.get("base_context_report_digest")
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
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
            "missing-context full-method report binding is invalid"
        )

    summary = full_method_report.get("summary")
    candidates = full_method_report.get("candidates")
    rejected = full_method_report.get("rejected")
    if (
        not isinstance(summary, dict)
        or not isinstance(candidates, list)
        or not isinstance(rejected, list)
    ):
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
            "missing-context full-method detail shape is invalid"
        )

    rejection_keys = (
        "missing_context_shape_mismatch",
        "full_method_target_access_mismatch",
        "full_method_fingerprint_mismatch",
        "full_method_fingerprint_nonunique",
        "missing_two_sided_canonical_anchor",
        "canonical_anchor_identity_mismatch",
        "declaration_interval_length_mismatch",
        "declaration_interval_shape_mismatch",
        "target_interval_offset_mismatch",
        "target_declaration_signature_not_unique",
    )
    input_count = summary.get("input_context_missing_reviews")
    candidate_count = summary.get("candidate_fields")
    remaining = summary.get("remaining_without_full_method_proof")
    rejection_counts = [summary.get(key) for key in rejection_keys]
    values = [input_count, candidate_count, remaining, *rejection_counts]
    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        for value in values
    ):
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
            "missing-context full-method summary accounting is invalid"
        )
    if candidate_count + remaining != input_count:
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
            "candidate+remaining accounting mismatch"
        )
    if len(candidates) != candidate_count or len(rejected) != remaining:
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
            "missing-context full-method detail count mismatch"
        )
    if sum(rejection_counts) != remaining:
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
            "missing-context full-method rejection accounting mismatch"
        )

    reason_tally = {key: 0 for key in rejection_keys}
    rejected_ids: set[str] = set()
    for i, row in enumerate(rejected):
        if not isinstance(row, dict):
            raise CanonicalMethodMissingContextFullMethodReviewSpecError(
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
            raise CanonicalMethodMissingContextFullMethodReviewSpecError(
                f"rejected[{i}] has invalid id/reason/base binding"
            )
        rejected_ids.add(relationship_id)
        reason_tally[reason] += 1
    for key in rejection_keys:
        if reason_tally[key] != summary[key]:
            raise CanonicalMethodMissingContextFullMethodReviewSpecError(
                f"rejected detail accounting mismatch for {key}"
            )

    relationship_ids: list[str] = []
    seen_ids: set[str] = set()
    seen_old: set[tuple[str, str, str]] = set()
    seen_new: set[tuple[str, str, str]] = set()

    for i, row in enumerate(candidates):
        label = f"candidates[{i}]"
        if not isinstance(row, dict):
            raise CanonicalMethodMissingContextFullMethodReviewSpecError(
                f"{label} must be object"
            )
        if (
            row.get("strategy")
            != (
                "canonical_method_full_normalized_fingerprint_and_"
                "canonical_anchor_declaration_interval_exact"
            )
            or row.get("supports_existing_review") is not True
            or row.get("confidence") != "INFERRED_HIGH"
            or float(row.get("score", 0.0)) != 0.9993
            or row.get("base_context_reason")
            != "canonical_method_context_missing"
            or row.get("base_context_report_id") != base_context_id
            or row.get("base_global_usage_report_id") != base_global_id
            or row.get("operation") not in _FIELD_OPS
            or not isinstance(row.get("method_id"), str)
            or not row.get("method_id")
            or not isinstance(row.get("expected_count"), int)
            or isinstance(row.get("expected_count"), bool)
            or row.get("expected_count") <= 0
            or not isinstance(row.get("full_method_instruction_count"), int)
            or isinstance(row.get("full_method_instruction_count"), bool)
            or row.get("full_method_instruction_count") <= 0
        ):
            raise CanonicalMethodMissingContextFullMethodReviewSpecError(
                f"{label} is not trusted full-method evidence"
            )

        relationship_id = row.get("relationship_id")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in seen_ids
            or relationship_id in rejected_ids
        ):
            raise CanonicalMethodMissingContextFullMethodReviewSpecError(
                f"{label} has invalid/duplicate/overlapping relationship_id"
            )
        seen_ids.add(relationship_id)

        old_coord = _coord(row, "old")
        new_coord = _coord(row, "new")
        if old_coord in seen_old or new_coord in seen_new:
            raise CanonicalMethodMissingContextFullMethodReviewSpecError(
                f"{relationship_id}: duplicate candidate coordinate"
            )
        seen_old.add(old_coord)
        seen_new.add(new_coord)

        _hex(
            row.get("full_method_fingerprint_digest"),
            label="full_method_fingerprint_digest",
        )
        _hex(row.get("interval_digest"), label="interval_digest")
        _hex(
            row.get("target_signature_digest"),
            label="target_signature_digest",
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
            raise CanonicalMethodMissingContextFullMethodReviewSpecError(
                f"{relationship_id}: invalid declaration interval evidence"
            )
        relationship_ids.append(relationship_id)

    if not relationship_ids:
        raise CanonicalMethodMissingContextFullMethodReviewSpecError(
            "missing-context full-method report contains no reviewable candidates"
        )

    return {
        "schema_version": 1,
        "kind": "reviewed_member_identity_acceptance_spec",
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "note": (
            f"Explicitly reviewed from {report_id}: the radius-4 missing-context "
            "outcome remains recorded. Continuity is independently re-proven by "
            "an exact normalized full canonical-method fingerprint that matches "
            "old/new and is unique against same-shape competitors in both builds, "
            "plus exact two-sided canonical declaration continuity. Rejected rows "
            "remain unresolved."
        ),
        "evidence": [
            f"report_id={report_id}",
            f"report_digest_sha256={_digest(full_method_report)}",
            f"base_context_report_id={base_context_id}",
            f"base_context_report_digest_sha256={base_context_digest}",
            f"base_global_usage_report_id={base_global_id}",
            f"base_global_usage_report_digest_sha256={base_global_digest}",
            f"member_lineage_digest_sha256={member_digest}",
            (
                "strategy=canonical_method_full_normalized_fingerprint_and_"
                "canonical_anchor_declaration_interval_exact"
            ),
            f"reviewed_candidates={len(relationship_ids)}",
            f"remaining_without_full_method_proof={remaining}",
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
        prog="spk-canonical-method-missing-context-full-method-review-spec"
    )
    for name in (
        "class_lineage", "member_lineage", "old_index", "new_index",
        "old_jar", "new_jar", "global_usage_report", "context_report",
        "full_method_report",
    ):
        p.add_argument(name, type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        spec = build_canonical_method_missing_context_full_method_review_spec(
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.old_index),
            _load(args.new_index),
            args.old_jar,
            args.new_jar,
            _load(args.global_usage_report),
            _load(args.context_report),
            _load(args.full_method_report),
        )
        write_spec(spec, args.out)
    except (
        CanonicalMethodMissingContextFullMethodReviewSpecError,
        CanonicalMethodMissingContextFullMethodEvidenceError,
        LineageValidationError,
        MemberLineageError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print("SPK_CANONICAL_METHOD_MISSING_CONTEXT_FULL_METHOD_REVIEW_SPEC_FAIL")
        print(str(exc))
        return 1

    print("SPK_CANONICAL_METHOD_MISSING_CONTEXT_FULL_METHOD_REVIEW_SPEC_PASS")
    print(f"relationship_ids={len(spec['relationship_ids'])}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
