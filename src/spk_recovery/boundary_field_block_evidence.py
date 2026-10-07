from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from .empty_field_declaration_evidence import (
    EmptyFieldDeclarationEvidenceError,
    _aliases,
    _coord,
    _declaration_signature,
    _field_index,
    _jar_field_table,
    _paired_anchor_id,
    _paired_field_maps,
    _stable_digest,
    _unresolved_reviews,
    build_empty_field_declaration_evidence,
)
from .lineage import LineageValidationError, load_lineage
from .member_lineage import (
    MemberLineageError,
    load_member_lineage,
)


class BoundaryFieldBlockEvidenceError(MemberLineageError):
    pass


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BoundaryFieldBlockEvidenceError(
            f"JSON root must be object: {path}"
        )
    return value


def _json_coord(value: Any, *, label: str) -> dict[str, Any]:
    name, descriptor, access = _coord(value, label=label)
    return {
        "name": name,
        "descriptor": descriptor,
        "access": access,
    }


def _block_signatures(
    fields: list[dict[str, Any]],
    aliases: dict[str, str],
    *,
    start: int,
    stop: int,
) -> list[tuple[Any, ...]]:
    if start < 0 or stop < start or stop > len(fields):
        raise BoundaryFieldBlockEvidenceError(
            f"invalid declaration block [{start}:{stop}]"
        )
    return [
        _declaration_signature(row, aliases)
        for row in fields[start:stop]
    ]


def build_boundary_field_block_evidence(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
) -> dict[str, Any]:
    base = build_empty_field_declaration_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
    )

    old_build_id = base.get("old_build_id")
    new_build_id = base.get("new_build_id")
    if (
        not isinstance(old_build_id, str)
        or not old_build_id
        or not isinstance(new_build_id, str)
        or not new_build_id
    ):
        raise BoundaryFieldBlockEvidenceError(
            "base declaration report lacks build binding"
        )

    missing_rows = [
        row
        for row in base.get("rejected", [])
        if isinstance(row, dict)
        and row.get("reason") == "missing_two_sided_canonical_anchor"
    ]

    unresolved = _unresolved_reviews(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_paired, new_paired = _paired_field_maps(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_aliases = _aliases(class_lineage, old_build_id)
    new_aliases = _aliases(class_lineage, new_build_id)

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    reason_counts = {
        "boundary_symmetry_mismatch": 0,
        "single_anchor_identity_mismatch": 0,
        "block_length_mismatch": 0,
        "block_shape_mismatch": 0,
        "target_offset_mismatch": 0,
        "target_signature_not_unique": 0,
    }
    mode_counts = {
        "prefix_block_exact": 0,
        "suffix_block_exact": 0,
        "whole_class_exact": 0,
    }

    seen_ids: set[str] = set()
    seen_old: set[tuple[str, str, str]] = set()
    seen_new: set[tuple[str, str, str]] = set()

    for i, row in enumerate(missing_rows):
        relationship_id = row.get("relationship_id")
        logical_class_id = row.get("logical_class_id")
        old_owner = str(row.get("old_owner", "")).removesuffix(".class")
        new_owner = str(row.get("new_owner", "")).removesuffix(".class")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in seen_ids
            or not isinstance(logical_class_id, str)
            or not logical_class_id
            or not old_owner
            or not new_owner
        ):
            raise BoundaryFieldBlockEvidenceError(
                f"base missing-anchor row {i} is invalid/duplicate"
            )
        seen_ids.add(relationship_id)

        original = unresolved.get(relationship_id)
        if original is None:
            raise BoundaryFieldBlockEvidenceError(
                f"{relationship_id}: missing from exact unresolved frontier"
            )
        if original.get("strategy") != "stable_symbol":
            raise BoundaryFieldBlockEvidenceError(
                f"{relationship_id}: unresolved source is not stable_symbol"
            )

        old_coord = _json_coord(
            original.get("old"),
            label=f"{relationship_id}.old",
        )
        new_coord = _json_coord(
            original.get("new"),
            label=f"{relationship_id}.new",
        )
        original_old_owner = str(
            original.get("old_owner", "")
        ).removesuffix(".class")
        original_new_owner = str(
            original.get("new_owner", "")
        ).removesuffix(".class")
        if (
            old_owner != original_old_owner
            or new_owner != original_new_owner
        ):
            raise BoundaryFieldBlockEvidenceError(
                f"{relationship_id}: base owner differs from unresolved review"
            )

        old_key = (
            old_owner,
            old_coord["name"],
            old_coord["descriptor"],
        )
        new_key = (
            new_owner,
            new_coord["name"],
            new_coord["descriptor"],
        )
        if old_key in seen_old:
            raise BoundaryFieldBlockEvidenceError(
                f"{relationship_id}: duplicate old residual coordinate"
            )
        if new_key in seen_new:
            raise BoundaryFieldBlockEvidenceError(
                f"{relationship_id}: duplicate new residual coordinate"
            )
        seen_old.add(old_key)
        seen_new.add(new_key)

        old_fields = _jar_field_table(old_jar, owner=old_owner)
        new_fields = _jar_field_table(new_jar, owner=new_owner)
        old_index_pos = _field_index(
            old_fields,
            (
                old_coord["name"],
                old_coord["descriptor"],
                old_coord["access"],
            ),
            label=f"{relationship_id}.old",
        )
        new_index_pos = _field_index(
            new_fields,
            (
                new_coord["name"],
                new_coord["descriptor"],
                new_coord["access"],
            ),
            label=f"{relationship_id}.new",
        )

        old_left = _paired_anchor_id(
            old_fields,
            old_paired,
            owner=old_owner,
            target_index=old_index_pos,
            direction=-1,
        )
        old_right = _paired_anchor_id(
            old_fields,
            old_paired,
            owner=old_owner,
            target_index=old_index_pos,
            direction=1,
        )
        new_left = _paired_anchor_id(
            new_fields,
            new_paired,
            owner=new_owner,
            target_index=new_index_pos,
            direction=-1,
        )
        new_right = _paired_anchor_id(
            new_fields,
            new_paired,
            owner=new_owner,
            target_index=new_index_pos,
            direction=1,
        )

        def reject(reason: str, **evidence: Any) -> None:
            reason_counts[reason] += 1
            rejected.append(
                {
                    "relationship_id": relationship_id,
                    "logical_class_id": logical_class_id,
                    "old_owner": old_owner,
                    "new_owner": new_owner,
                    "reason": reason,
                    **evidence,
                }
            )

        mode: str
        anchor_member_id: str | None
        old_start: int
        old_stop: int
        new_start: int
        new_stop: int

        if (
            old_left is None
            and new_left is None
            and old_right is not None
            and new_right is not None
        ):
            if old_right[0] != new_right[0]:
                reject(
                    "single_anchor_identity_mismatch",
                    boundary="class_start",
                    old_anchor=old_right,
                    new_anchor=new_right,
                )
                continue
            mode = "prefix_block_exact"
            anchor_member_id = old_right[0]
            old_start = 0
            old_stop = old_right[1]
            new_start = 0
            new_stop = new_right[1]
        elif (
            old_right is None
            and new_right is None
            and old_left is not None
            and new_left is not None
        ):
            if old_left[0] != new_left[0]:
                reject(
                    "single_anchor_identity_mismatch",
                    boundary="class_end",
                    old_anchor=old_left,
                    new_anchor=new_left,
                )
                continue
            mode = "suffix_block_exact"
            anchor_member_id = old_left[0]
            old_start = old_left[1] + 1
            old_stop = len(old_fields)
            new_start = new_left[1] + 1
            new_stop = len(new_fields)
        elif (
            old_left is None
            and old_right is None
            and new_left is None
            and new_right is None
        ):
            mode = "whole_class_exact"
            anchor_member_id = None
            old_start = 0
            old_stop = len(old_fields)
            new_start = 0
            new_stop = len(new_fields)
        else:
            reject(
                "boundary_symmetry_mismatch",
                old_left=old_left,
                old_right=old_right,
                new_left=new_left,
                new_right=new_right,
            )
            continue

        old_block = _block_signatures(
            old_fields,
            old_aliases,
            start=old_start,
            stop=old_stop,
        )
        new_block = _block_signatures(
            new_fields,
            new_aliases,
            start=new_start,
            stop=new_stop,
        )
        if len(old_block) != len(new_block):
            reject(
                "block_length_mismatch",
                block_kind=mode,
                old_length=len(old_block),
                new_length=len(new_block),
                anchor_member_id=anchor_member_id,
            )
            continue
        if old_block != new_block:
            reject(
                "block_shape_mismatch",
                block_kind=mode,
                old_block_digest=_stable_digest(old_block),
                new_block_digest=_stable_digest(new_block),
                block_length=len(old_block),
                anchor_member_id=anchor_member_id,
            )
            continue

        old_offset = old_index_pos - old_start
        new_offset = new_index_pos - new_start
        if old_offset != new_offset:
            reject(
                "target_offset_mismatch",
                block_kind=mode,
                old_offset=old_offset,
                new_offset=new_offset,
                block_length=len(old_block),
                anchor_member_id=anchor_member_id,
            )
            continue
        if (
            old_offset < 0
            or old_offset >= len(old_block)
            or new_offset < 0
            or new_offset >= len(new_block)
        ):
            raise BoundaryFieldBlockEvidenceError(
                f"{relationship_id}: target lies outside matched block"
            )

        target_signature = old_block[old_offset]
        if (
            new_block[new_offset] != target_signature
            or old_block.count(target_signature) != 1
            or new_block.count(target_signature) != 1
        ):
            reject(
                "target_signature_not_unique",
                block_kind=mode,
                target_offset=old_offset,
                target_signature_digest=_stable_digest(target_signature),
                old_occurrences=old_block.count(target_signature),
                new_occurrences=new_block.count(target_signature),
                anchor_member_id=anchor_member_id,
            )
            continue

        mode_counts[mode] += 1
        block_digest = _stable_digest(old_block)
        candidates.append(
            {
                "relationship_id": relationship_id,
                "logical_class_id": logical_class_id,
                "old_owner": old_owner,
                "new_owner": new_owner,
                "old": old_coord,
                "new": new_coord,
                "strategy": "canonical_boundary_block_declaration_exact",
                "confidence": "INFERRED_HIGH",
                "score": 0.995,
                "supports_existing_review": True,
                "block_kind": mode,
                "anchor_member_id": anchor_member_id,
                "block_length": len(old_block),
                "target_offset": old_offset,
                "block_digest": block_digest,
                "target_signature_digest": _stable_digest(
                    target_signature
                ),
                "base_declaration_report_id": base.get("report_id"),
            }
        )

    if len(candidates) + len(rejected) != len(missing_rows):
        raise BoundaryFieldBlockEvidenceError(
            "boundary block outcome accounting mismatch"
        )

    summary = {
        "input_missing_anchor_reviews": len(missing_rows),
        "candidate_fields": len(candidates),
        "remaining_without_boundary_block_proof": len(rejected),
        **mode_counts,
        **reason_counts,
    }

    body = {
        "schema_version": 1,
        "kind": "boundary_field_block_identity_candidates",
        "canonical": False,
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": base.get("old_sha256"),
        "new_sha256": base.get("new_sha256"),
        "member_lineage_digest": base.get("member_lineage_digest"),
        "global_usage_report_id": base.get("global_usage_report_id"),
        "base_declaration_report_id": base.get("report_id"),
        "base_declaration_report_digest": _stable_digest(base),
        "summary": summary,
        "candidates": candidates,
        "rejected": rejected,
        "note": (
            "Research-only exact-JAR boundary-block declaration evidence. "
            "A class boundary is never accepted as a standalone anchor: "
            "the complete prefix/suffix block, or the complete class field "
            "table when no paired anchors exist, must be bijective and "
            "declaration-identical under canonical descriptor identities; "
            "the target offset must match and its declaration signature must "
            "be unique inside that exact block. No lineage mutation occurs."
        ),
    }
    return {
        "report_id": (
            "BOUNDARYFIELDBLOCK_"
            + hashlib.sha256(
                json.dumps(
                    body,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()[:20].upper()
        ),
        **body,
    }


def write_report(report: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-boundary-field-block-evidence"
    )
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("old_index", type=Path)
    p.add_argument("new_index", type=Path)
    p.add_argument("old_jar", type=Path)
    p.add_argument("new_jar", type=Path)
    p.add_argument("global_usage_report", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = build_boundary_field_block_evidence(
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.old_index),
            _load(args.new_index),
            args.old_jar,
            args.new_jar,
            _load(args.global_usage_report),
        )
        write_report(report, args.out)
    except (
        BoundaryFieldBlockEvidenceError,
        EmptyFieldDeclarationEvidenceError,
        LineageValidationError,
        MemberLineageError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_BOUNDARY_FIELD_BLOCK_EVIDENCE_PASS")
    print(f"report_id={report['report_id']}")
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
