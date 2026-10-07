from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from .empty_field_declaration_evidence import (
    EmptyFieldDeclarationEvidenceError,
    build_empty_field_declaration_evidence,
)
from .lineage import LineageValidationError, load_lineage
from .member_lineage import (
    MemberLineageError,
    load_member_lineage,
)


class EmptyFieldReviewSpecError(MemberLineageError):
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
        raise EmptyFieldReviewSpecError(
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
        raise EmptyFieldReviewSpecError(
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
        raise EmptyFieldReviewSpecError(
            f"candidate {side} coordinate is invalid"
        )
    return owner, name, descriptor


def build_empty_field_review_spec(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
    declaration_report: dict[str, Any],
) -> dict[str, Any]:
    if (
        declaration_report.get("schema_version") != 1
        or declaration_report.get("kind")
        != "empty_field_declaration_identity_candidates"
        or declaration_report.get("canonical") is not False
    ):
        raise EmptyFieldReviewSpecError(
            "unsupported empty-field declaration report"
        )

    recomputed = build_empty_field_declaration_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
    )
    if _stable_digest(recomputed) != _stable_digest(declaration_report):
        raise EmptyFieldReviewSpecError(
            "declaration report does not equal exact-JAR recomputation"
        )

    report_id = declaration_report.get("report_id")
    old_build_id = declaration_report.get("old_build_id")
    new_build_id = declaration_report.get("new_build_id")
    old_sha = str(declaration_report.get("old_sha256", "")).lower()
    new_sha = str(declaration_report.get("new_sha256", "")).lower()
    member_digest = declaration_report.get("member_lineage_digest")
    global_report_id = declaration_report.get("global_usage_report_id")

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
    ):
        raise EmptyFieldReviewSpecError(
            "declaration report identity/binding is invalid"
        )

    summary = declaration_report.get("summary")
    candidates = declaration_report.get("candidates")
    rejected = declaration_report.get("rejected")
    if (
        not isinstance(summary, dict)
        or not isinstance(candidates, list)
        or not isinstance(rejected, list)
    ):
        raise EmptyFieldReviewSpecError(
            "declaration report summary/candidate shape is invalid"
        )

    input_count = summary.get("input_empty_both_reviews")
    candidate_count = summary.get("candidate_fields")
    remaining_count = summary.get("remaining_without_declaration_proof")
    rejection_keys = (
        "raw_source_guard_rejected",
        "global_class_topology_guard_rejected",
        "missing_two_sided_canonical_anchor",
        "canonical_anchor_identity_mismatch",
        "declaration_interval_length_mismatch",
        "declaration_interval_shape_mismatch",
        "target_interval_offset_mismatch",
        "target_declaration_signature_not_unique",
    )
    rejection_counts = [summary.get(key) for key in rejection_keys]

    values = [
        input_count,
        candidate_count,
        remaining_count,
        *rejection_counts,
    ]
    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        for value in values
    ):
        raise EmptyFieldReviewSpecError(
            "declaration report summary accounting is invalid"
        )
    if candidate_count + remaining_count != input_count:
        raise EmptyFieldReviewSpecError(
            "candidate+remaining declaration accounting mismatch"
        )
    if len(candidates) != candidate_count:
        raise EmptyFieldReviewSpecError(
            "candidate detail count mismatch"
        )
    if len(rejected) != remaining_count:
        raise EmptyFieldReviewSpecError(
            "rejected detail count mismatch"
        )
    if sum(rejection_counts) != remaining_count:
        raise EmptyFieldReviewSpecError(
            "declaration rejection reason accounting mismatch"
        )

    seen_ids: set[str] = set()
    seen_old: set[tuple[str, str, str]] = set()
    seen_new: set[tuple[str, str, str]] = set()
    relationship_ids: list[str] = []

    for i, row in enumerate(candidates):
        label = f"candidates[{i}]"
        if not isinstance(row, dict):
            raise EmptyFieldReviewSpecError(
                f"{label} must be an object"
            )
        if (
            row.get("strategy")
            != "canonical_anchor_declaration_interval_exact"
            or row.get("supports_existing_review") is not True
            or row.get("confidence") != "INFERRED_HIGH"
            or float(row.get("score", 0.0)) != 0.99
        ):
            raise EmptyFieldReviewSpecError(
                f"{label} is not trusted declaration review evidence"
            )

        relationship_id = row.get("relationship_id")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in seen_ids
        ):
            raise EmptyFieldReviewSpecError(
                f"{label} has invalid/duplicate relationship_id"
            )
        seen_ids.add(relationship_id)

        old_coord = _candidate_coord(row, side="old")
        new_coord = _candidate_coord(row, side="new")
        if old_coord in seen_old:
            raise EmptyFieldReviewSpecError(
                f"{relationship_id}: duplicate old coordinate"
            )
        if new_coord in seen_new:
            raise EmptyFieldReviewSpecError(
                f"{relationship_id}: duplicate new coordinate"
            )
        seen_old.add(old_coord)
        seen_new.add(new_coord)

        left_anchor = row.get("left_anchor_member_id")
        right_anchor = row.get("right_anchor_member_id")
        interval_digest = row.get("interval_digest")
        interval_length = row.get("interval_length")
        interval_offset = row.get("interval_offset")
        old_ordinal = row.get("old_field_ordinal")
        new_ordinal = row.get("new_field_ordinal")
        if (
            not isinstance(left_anchor, str)
            or not left_anchor
            or not isinstance(right_anchor, str)
            or not right_anchor
            or left_anchor == right_anchor
            or not isinstance(interval_digest, str)
            or len(interval_digest) != 64
            or not isinstance(interval_length, int)
            or isinstance(interval_length, bool)
            or interval_length <= 0
            or not isinstance(interval_offset, int)
            or isinstance(interval_offset, bool)
            or interval_offset < 0
            or interval_offset >= interval_length
            or not isinstance(old_ordinal, int)
            or isinstance(old_ordinal, bool)
            or old_ordinal < 0
            or not isinstance(new_ordinal, int)
            or isinstance(new_ordinal, bool)
            or new_ordinal < 0
        ):
            raise EmptyFieldReviewSpecError(
                f"{relationship_id}: declaration anchor/interval evidence is invalid"
            )

        topology = row.get("global_source_class_topology")
        observations = row.get("global_observations")
        if not isinstance(topology, list):
            raise EmptyFieldReviewSpecError(
                f"{relationship_id}: global topology must be an array"
            )
        if (
            not isinstance(observations, int)
            or isinstance(observations, bool)
            or observations < 0
        ):
            raise EmptyFieldReviewSpecError(
                f"{relationship_id}: global observation count is invalid"
            )
        total = 0
        seen_topology: set[tuple[str, str]] = set()
        for j, topology_row in enumerate(topology):
            if not isinstance(topology_row, dict):
                raise EmptyFieldReviewSpecError(
                    f"{relationship_id}: topology[{j}] must be an object"
                )
            source_class = topology_row.get("source_class")
            operation = topology_row.get("operation")
            count = topology_row.get("count")
            if (
                not isinstance(source_class, str)
                or not source_class
                or source_class.startswith("RAW:")
                or not isinstance(operation, str)
                or operation not in {
                    "getfield",
                    "putfield",
                    "getstatic",
                    "putstatic",
                }
                or not isinstance(count, int)
                or isinstance(count, bool)
                or count <= 0
            ):
                raise EmptyFieldReviewSpecError(
                    f"{relationship_id}: topology[{j}] is invalid"
                )
            key = (source_class, operation)
            if key in seen_topology:
                raise EmptyFieldReviewSpecError(
                    f"{relationship_id}: duplicate topology row {key!r}"
                )
            seen_topology.add(key)
            total += count
        if total != observations:
            raise EmptyFieldReviewSpecError(
                f"{relationship_id}: global observation count does not match topology"
            )

        relationship_ids.append(relationship_id)

    if not relationship_ids:
        raise EmptyFieldReviewSpecError(
            "declaration report contains no reviewable candidates"
        )

    report_digest = _stable_digest(declaration_report)
    global_report_digest = _stable_digest(global_usage_report)

    return {
        "schema_version": 1,
        "kind": "reviewed_member_identity_acceptance_spec",
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "note": (
            f"Explicitly reviewed from {report_id}: exact-JAR two-sided "
            "canonical field anchors, identical declaration interval, "
            "same target offset, unique target signature, independently "
            "rechecked empty canonical-method usage, and identical RAW-free "
            "whole-JAR source-class topology. All rejected declaration rows "
            "remain unresolved."
        ),
        "evidence": [
            f"report_id={report_id}",
            f"report_digest_sha256={report_digest}",
            f"global_usage_report_id={global_report_id}",
            f"global_usage_report_digest_sha256={global_report_digest}",
            f"member_lineage_digest_sha256={member_digest}",
            "strategy=canonical_anchor_declaration_interval_exact",
            f"reviewed_candidates={len(relationship_ids)}",
            f"remaining_without_declaration_proof={remaining_count}",
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
        prog="spk-empty-field-review-spec"
    )
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("old_index", type=Path)
    p.add_argument("new_index", type=Path)
    p.add_argument("old_jar", type=Path)
    p.add_argument("new_jar", type=Path)
    p.add_argument("global_usage_report", type=Path)
    p.add_argument("declaration_report", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        spec = build_empty_field_review_spec(
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.old_index),
            _load(args.new_index),
            args.old_jar,
            args.new_jar,
            _load(args.global_usage_report),
            _load(args.declaration_report),
        )
        write_spec(spec, args.out)
    except (
        EmptyFieldReviewSpecError,
        EmptyFieldDeclarationEvidenceError,
        LineageValidationError,
        MemberLineageError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_EMPTY_FIELD_REVIEW_SPEC_PASS")
    print(f"relationship_ids={len(spec['relationship_ids'])}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
