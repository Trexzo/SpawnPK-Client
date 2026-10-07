from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from .boundary_field_block_evidence import (
    BoundaryFieldBlockEvidenceError,
    build_boundary_field_block_evidence,
)
from .lineage import LineageValidationError, load_lineage
from .member_lineage import (
    MemberLineageError,
    load_member_lineage,
)


class BoundaryFieldReviewSpecError(MemberLineageError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BoundaryFieldReviewSpecError(
            f"JSON root must be object: {path}"
        )
    return value


def _candidate_coord(
    row: dict[str, Any],
    *,
    side: str,
) -> tuple[str, str, str]:
    owner = str(row.get(f"{side}_owner", "")).removesuffix(".class")
    coord = row.get(side)
    if not isinstance(coord, dict):
        raise BoundaryFieldReviewSpecError(
            f"candidate {side} coordinate must be an object"
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
        raise BoundaryFieldReviewSpecError(
            f"candidate {side} coordinate is invalid"
        )
    return owner, name, descriptor


def build_boundary_field_review_spec(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
    boundary_report: dict[str, Any],
) -> dict[str, Any]:
    if (
        boundary_report.get("schema_version") != 1
        or boundary_report.get("kind")
        != "boundary_field_block_identity_candidates"
        or boundary_report.get("canonical") is not False
    ):
        raise BoundaryFieldReviewSpecError(
            "unsupported boundary-field report"
        )

    recomputed = build_boundary_field_block_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
    )
    if _stable_digest(recomputed) != _stable_digest(boundary_report):
        raise BoundaryFieldReviewSpecError(
            "boundary-field report does not equal exact-JAR recomputation"
        )

    report_id = boundary_report.get("report_id")
    old_build_id = boundary_report.get("old_build_id")
    new_build_id = boundary_report.get("new_build_id")
    old_sha = str(boundary_report.get("old_sha256", "")).lower()
    new_sha = str(boundary_report.get("new_sha256", "")).lower()
    member_digest = boundary_report.get("member_lineage_digest")
    global_report_id = boundary_report.get("global_usage_report_id")
    base_report_id = boundary_report.get("base_declaration_report_id")
    base_report_digest = boundary_report.get(
        "base_declaration_report_digest"
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
        or not isinstance(global_report_id, str)
        or not global_report_id
        or not isinstance(base_report_id, str)
        or not base_report_id
        or not isinstance(base_report_digest, str)
        or len(base_report_digest) != 64
    ):
        raise BoundaryFieldReviewSpecError(
            "boundary-field report identity/binding is invalid"
        )

    summary = boundary_report.get("summary")
    candidates = boundary_report.get("candidates")
    rejected = boundary_report.get("rejected")
    if (
        not isinstance(summary, dict)
        or not isinstance(candidates, list)
        or not isinstance(rejected, list)
    ):
        raise BoundaryFieldReviewSpecError(
            "boundary-field report summary/detail shape is invalid"
        )

    input_count = summary.get("input_missing_anchor_reviews")
    candidate_count = summary.get("candidate_fields")
    remaining_count = summary.get(
        "remaining_without_boundary_block_proof"
    )
    mode_keys = (
        "prefix_block_exact",
        "suffix_block_exact",
        "whole_class_exact",
    )
    rejection_keys = (
        "boundary_symmetry_mismatch",
        "single_anchor_identity_mismatch",
        "block_length_mismatch",
        "block_shape_mismatch",
        "target_offset_mismatch",
        "target_signature_not_unique",
    )
    mode_counts = [summary.get(key) for key in mode_keys]
    rejection_counts = [summary.get(key) for key in rejection_keys]
    values = [
        input_count,
        candidate_count,
        remaining_count,
        *mode_counts,
        *rejection_counts,
    ]
    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        for value in values
    ):
        raise BoundaryFieldReviewSpecError(
            "boundary-field summary accounting is invalid"
        )
    if candidate_count + remaining_count != input_count:
        raise BoundaryFieldReviewSpecError(
            "candidate+remaining boundary accounting mismatch"
        )
    if sum(mode_counts) != candidate_count:
        raise BoundaryFieldReviewSpecError(
            "candidate mode accounting mismatch"
        )
    if sum(rejection_counts) != remaining_count:
        raise BoundaryFieldReviewSpecError(
            "boundary rejection reason accounting mismatch"
        )
    if len(candidates) != candidate_count:
        raise BoundaryFieldReviewSpecError(
            "candidate detail count mismatch"
        )
    if len(rejected) != remaining_count:
        raise BoundaryFieldReviewSpecError(
            "rejected detail count mismatch"
        )

    rejected_tally = {key: 0 for key in rejection_keys}
    rejected_ids: set[str] = set()
    for i, row in enumerate(rejected):
        label = f"rejected[{i}]"
        if not isinstance(row, dict):
            raise BoundaryFieldReviewSpecError(
                f"{label} must be an object"
            )
        relationship_id = row.get("relationship_id")
        reason = row.get("reason")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in rejected_ids
            or reason not in rejected_tally
        ):
            raise BoundaryFieldReviewSpecError(
                f"{label} has invalid id/reason"
            )
        rejected_ids.add(relationship_id)
        rejected_tally[reason] += 1
    for key in rejection_keys:
        if rejected_tally[key] != summary[key]:
            raise BoundaryFieldReviewSpecError(
                f"rejected detail accounting mismatch for {key}"
            )

    seen_ids: set[str] = set()
    seen_old: set[tuple[str, str, str]] = set()
    seen_new: set[tuple[str, str, str]] = set()
    relationship_ids: list[str] = []
    mode_tally = {key: 0 for key in mode_keys}

    for i, row in enumerate(candidates):
        label = f"candidates[{i}]"
        if not isinstance(row, dict):
            raise BoundaryFieldReviewSpecError(
                f"{label} must be an object"
            )
        if (
            row.get("strategy")
            != "canonical_boundary_block_declaration_exact"
            or row.get("supports_existing_review") is not True
            or row.get("confidence") != "INFERRED_HIGH"
            or float(row.get("score", 0.0)) != 0.995
        ):
            raise BoundaryFieldReviewSpecError(
                f"{label} is not trusted boundary-block review evidence"
            )

        relationship_id = row.get("relationship_id")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in seen_ids
            or relationship_id in rejected_ids
        ):
            raise BoundaryFieldReviewSpecError(
                f"{label} has invalid/duplicate/overlapping relationship_id"
            )
        seen_ids.add(relationship_id)

        old_coord = _candidate_coord(row, side="old")
        new_coord = _candidate_coord(row, side="new")
        if old_coord in seen_old:
            raise BoundaryFieldReviewSpecError(
                f"{relationship_id}: duplicate old coordinate"
            )
        if new_coord in seen_new:
            raise BoundaryFieldReviewSpecError(
                f"{relationship_id}: duplicate new coordinate"
            )
        seen_old.add(old_coord)
        seen_new.add(new_coord)

        block_kind = row.get("block_kind")
        if block_kind not in mode_tally:
            raise BoundaryFieldReviewSpecError(
                f"{relationship_id}: unsupported block kind"
            )
        mode_tally[block_kind] += 1

        anchor_member_id = row.get("anchor_member_id")
        if block_kind == "whole_class_exact":
            if anchor_member_id is not None:
                raise BoundaryFieldReviewSpecError(
                    f"{relationship_id}: whole-class proof must not have anchor"
                )
        else:
            if (
                not isinstance(anchor_member_id, str)
                or not anchor_member_id
            ):
                raise BoundaryFieldReviewSpecError(
                    f"{relationship_id}: boundary block lacks canonical anchor"
                )

        block_length = row.get("block_length")
        target_offset = row.get("target_offset")
        block_digest = row.get("block_digest")
        target_digest = row.get("target_signature_digest")
        if (
            not isinstance(block_length, int)
            or isinstance(block_length, bool)
            or block_length <= 0
            or not isinstance(target_offset, int)
            or isinstance(target_offset, bool)
            or target_offset < 0
            or target_offset >= block_length
            or not isinstance(block_digest, str)
            or len(block_digest) != 64
            or not isinstance(target_digest, str)
            or len(target_digest) != 64
        ):
            raise BoundaryFieldReviewSpecError(
                f"{relationship_id}: boundary block evidence is invalid"
            )

        if row.get("base_declaration_report_id") != base_report_id:
            raise BoundaryFieldReviewSpecError(
                f"{relationship_id}: base declaration report drift"
            )

        relationship_ids.append(relationship_id)

    for key in mode_keys:
        if mode_tally[key] != summary[key]:
            raise BoundaryFieldReviewSpecError(
                f"candidate detail accounting mismatch for {key}"
            )

    if not relationship_ids:
        raise BoundaryFieldReviewSpecError(
            "boundary-field report contains no reviewable candidates"
        )

    report_digest = _stable_digest(boundary_report)
    global_report_digest = _stable_digest(global_usage_report)

    return {
        "schema_version": 1,
        "kind": "reviewed_member_identity_acceptance_spec",
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "note": (
            f"Explicitly reviewed from {report_id}: exact-JAR boundary-block "
            "declaration bijection with canonical descriptor identities, "
            "matching full block length/order, exact target offset, unique "
            "target declaration signature, and exact canonical anchor "
            "identity where applicable. Every rejected boundary row remains "
            "unresolved."
        ),
        "evidence": [
            f"report_id={report_id}",
            f"report_digest_sha256={report_digest}",
            f"global_usage_report_id={global_report_id}",
            f"global_usage_report_digest_sha256={global_report_digest}",
            f"base_declaration_report_id={base_report_id}",
            f"base_declaration_report_digest_sha256={base_report_digest}",
            f"member_lineage_digest_sha256={member_digest}",
            "strategy=canonical_boundary_block_declaration_exact",
            f"reviewed_candidates={len(relationship_ids)}",
            f"remaining_without_boundary_block_proof={remaining_count}",
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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-boundary-field-review-spec"
    )
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("old_index", type=Path)
    p.add_argument("new_index", type=Path)
    p.add_argument("old_jar", type=Path)
    p.add_argument("new_jar", type=Path)
    p.add_argument("global_usage_report", type=Path)
    p.add_argument("boundary_report", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        spec = build_boundary_field_review_spec(
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.old_index),
            _load(args.new_index),
            args.old_jar,
            args.new_jar,
            _load(args.global_usage_report),
            _load(args.boundary_report),
        )
        write_spec(spec, args.out)
    except (
        BoundaryFieldReviewSpecError,
        BoundaryFieldBlockEvidenceError,
        LineageValidationError,
        MemberLineageError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_BOUNDARY_FIELD_REVIEW_SPEC_PASS")
    print(f"relationship_ids={len(spec['relationship_ids'])}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
