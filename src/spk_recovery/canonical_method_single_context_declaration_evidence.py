from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .canonical_method_field_context_evidence import (
    CanonicalMethodFieldContextEvidenceError,
    build_canonical_method_field_context_evidence,
)
from .empty_field_declaration_evidence import (
    _aliases,
    _coord,
    _field_index,
    _jar_field_table,
    _paired_anchor_id,
    _paired_field_maps,
    _segment_signatures,
    _stable_digest,
    _unresolved_reviews,
)
from .lineage import LineageValidationError, load_lineage
from .member_lineage import (
    MemberLineageError,
    load_member_lineage,
)


class CanonicalMethodSingleContextDeclarationEvidenceError(MemberLineageError):
    pass


_FIELD_OPS = {"getstatic", "putstatic", "getfield", "putfield"}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CanonicalMethodSingleContextDeclarationEvidenceError(
            f"JSON root must be object: {path}"
        )
    return value


def _single_witness(
    row: dict[str, Any],
) -> tuple[str, str, str, int] | None:
    observations = row.get("observations")
    if (
        row.get("canonical_methods") != 1
        or not isinstance(observations, int)
        or isinstance(observations, bool)
        or observations <= 0
        or row.get("distinct_contexts") != 1
    ):
        return None
    witnesses = row.get("method_witnesses")
    if not isinstance(witnesses, list) or len(witnesses) != 1:
        return None
    witness = witnesses[0]
    if not isinstance(witness, dict):
        return None
    method_id = witness.get("method_id")
    operation = witness.get("operation")
    count = witness.get("count")
    contexts = witness.get("contexts")
    if (
        not isinstance(method_id, str)
        or not method_id
        or operation not in _FIELD_OPS
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count <= 0
        or count != observations
        or not isinstance(contexts, list)
        or len(contexts) != 1
    ):
        return None
    context = contexts[0]
    if (
        not isinstance(context, list)
        or len(context) != 2
        or not isinstance(context[0], str)
        or len(context[0]) != 64
        or context[1] != observations
    ):
        return None
    try:
        int(context[0], 16)
    except ValueError:
        return None
    return method_id, operation, context[0], observations


def build_canonical_method_single_context_declaration_evidence(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
    context_report: dict[str, Any],
) -> dict[str, Any]:
    recomputed = build_canonical_method_field_context_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
    )
    if _stable_digest(recomputed) != _stable_digest(context_report):
        raise CanonicalMethodSingleContextDeclarationEvidenceError(
            "canonical-method context report does not equal exact-JAR recomputation"
        )

    old_build_id = str(recomputed.get("old_build_id", ""))
    new_build_id = str(recomputed.get("new_build_id", ""))
    if not old_build_id or not new_build_id or old_build_id == new_build_id:
        raise CanonicalMethodSingleContextDeclarationEvidenceError(
            "canonical-method context build binding is invalid"
        )

    rows = [
        row
        for row in recomputed.get("rejected", [])
        if isinstance(row, dict)
        and row.get("reason") == "insufficient_independent_context_witness"
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
    counts = {
        "single_context_shape_mismatch": 0,
        "missing_two_sided_canonical_anchor": 0,
        "canonical_anchor_identity_mismatch": 0,
        "declaration_interval_length_mismatch": 0,
        "declaration_interval_shape_mismatch": 0,
        "target_interval_offset_mismatch": 0,
        "target_declaration_signature_not_unique": 0,
    }

    seen_ids: set[str] = set()
    seen_old: set[tuple[str, str, str]] = set()
    seen_new: set[tuple[str, str, str]] = set()

    for i, row in enumerate(rows):
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
            raise CanonicalMethodSingleContextDeclarationEvidenceError(
                f"insufficient-witness row {i} is invalid/duplicate"
            )
        seen_ids.add(relationship_id)

        original = unresolved.get(relationship_id)
        if original is None or original.get("strategy") != "stable_symbol":
            raise CanonicalMethodSingleContextDeclarationEvidenceError(
                f"{relationship_id}: missing from exact stable-symbol frontier"
            )

        old_coord = _coord(
            original.get("old"),
            label=f"{relationship_id}.old",
        )
        new_coord = _coord(
            original.get("new"),
            label=f"{relationship_id}.new",
        )
        old_key = (old_owner, old_coord[0], old_coord[1])
        new_key = (new_owner, new_coord[0], new_coord[1])
        if old_key in seen_old or new_key in seen_new:
            raise CanonicalMethodSingleContextDeclarationEvidenceError(
                f"{relationship_id}: duplicate unresolved coordinate"
            )
        seen_old.add(old_key)
        seen_new.add(new_key)

        def reject(reason: str, **extra: Any) -> None:
            counts[reason] += 1
            rejected.append(
                {
                    "relationship_id": relationship_id,
                    "logical_class_id": logical_class_id,
                    "old_owner": old_owner,
                    "new_owner": new_owner,
                    "reason": reason,
                    "base_context_reason": (
                        "insufficient_independent_context_witness"
                    ),
                    **extra,
                }
            )

        witness = _single_witness(row)
        if witness is None:
            reject(
                "single_context_shape_mismatch",
                canonical_methods=row.get("canonical_methods"),
                observations=row.get("observations"),
                distinct_contexts=row.get("distinct_contexts"),
                method_witnesses=row.get("method_witnesses"),
            )
            continue
        method_id, operation, context_digest, observations = witness

        old_fields = _jar_field_table(old_jar, owner=old_owner)
        new_fields = _jar_field_table(new_jar, owner=new_owner)
        old_pos = _field_index(
            old_fields,
            old_coord,
            label=f"{relationship_id}.old",
        )
        new_pos = _field_index(
            new_fields,
            new_coord,
            label=f"{relationship_id}.new",
        )

        old_left = _paired_anchor_id(
            old_fields,
            old_paired,
            owner=old_owner,
            target_index=old_pos,
            direction=-1,
        )
        old_right = _paired_anchor_id(
            old_fields,
            old_paired,
            owner=old_owner,
            target_index=old_pos,
            direction=1,
        )
        new_left = _paired_anchor_id(
            new_fields,
            new_paired,
            owner=new_owner,
            target_index=new_pos,
            direction=-1,
        )
        new_right = _paired_anchor_id(
            new_fields,
            new_paired,
            owner=new_owner,
            target_index=new_pos,
            direction=1,
        )

        if (
            old_left is None
            or old_right is None
            or new_left is None
            or new_right is None
        ):
            reject(
                "missing_two_sided_canonical_anchor",
                method_id=method_id,
                operation=operation,
                context_digest=context_digest,
                old_left=old_left,
                old_right=old_right,
                new_left=new_left,
                new_right=new_right,
            )
            continue

        if old_left[0] != new_left[0] or old_right[0] != new_right[0]:
            reject(
                "canonical_anchor_identity_mismatch",
                method_id=method_id,
                operation=operation,
                context_digest=context_digest,
                old_left_member_id=old_left[0],
                new_left_member_id=new_left[0],
                old_right_member_id=old_right[0],
                new_right_member_id=new_right[0],
            )
            continue

        old_segment = _segment_signatures(
            old_fields,
            old_aliases,
            left_index=old_left[1],
            right_index=old_right[1],
        )
        new_segment = _segment_signatures(
            new_fields,
            new_aliases,
            left_index=new_left[1],
            right_index=new_right[1],
        )

        if len(old_segment) != len(new_segment):
            reject(
                "declaration_interval_length_mismatch",
                method_id=method_id,
                operation=operation,
                context_digest=context_digest,
                old_interval_length=len(old_segment),
                new_interval_length=len(new_segment),
            )
            continue

        if old_segment != new_segment:
            reject(
                "declaration_interval_shape_mismatch",
                method_id=method_id,
                operation=operation,
                context_digest=context_digest,
                old_interval_digest=_stable_digest(old_segment),
                new_interval_digest=_stable_digest(new_segment),
            )
            continue

        old_offset = old_pos - old_left[1] - 1
        new_offset = new_pos - new_left[1] - 1
        if old_offset != new_offset:
            reject(
                "target_interval_offset_mismatch",
                method_id=method_id,
                operation=operation,
                context_digest=context_digest,
                old_offset=old_offset,
                new_offset=new_offset,
            )
            continue

        if (
            old_offset < 0
            or old_offset >= len(old_segment)
            or new_offset < 0
            or new_offset >= len(new_segment)
        ):
            raise CanonicalMethodSingleContextDeclarationEvidenceError(
                f"{relationship_id}: target lies outside declaration interval"
            )

        target_signature = old_segment[old_offset]
        old_occurrences = sum(
            1 for value in old_segment if value == target_signature
        )
        new_occurrences = sum(
            1 for value in new_segment if value == target_signature
        )
        if (
            new_segment[new_offset] != target_signature
            or old_occurrences != 1
            or new_occurrences != 1
        ):
            reject(
                "target_declaration_signature_not_unique",
                method_id=method_id,
                operation=operation,
                context_digest=context_digest,
                interval_length=len(old_segment),
                interval_offset=old_offset,
                old_occurrences=old_occurrences,
                new_occurrences=new_occurrences,
            )
            continue

        candidates.append(
            {
                "relationship_id": relationship_id,
                "logical_class_id": logical_class_id,
                "old_owner": old_owner,
                "new_owner": new_owner,
                "old": {
                    "name": old_coord[0],
                    "descriptor": old_coord[1],
                    "access": old_coord[2],
                },
                "new": {
                    "name": new_coord[0],
                    "descriptor": new_coord[1],
                    "access": new_coord[2],
                },
                "strategy": (
                    "canonical_method_single_unique_local_context_and_"
                    "canonical_anchor_declaration_interval_exact"
                ),
                "confidence": "INFERRED_HIGH",
                "score": 0.9992,
                "supports_existing_review": True,
                "canonical_methods": 1,
                "observations": observations,
                "distinct_contexts": 1,
                "method_witnesses": row.get("method_witnesses"),
                "method_id": method_id,
                "operation": operation,
                "context_digest": context_digest,
                "left_anchor_member_id": old_left[0],
                "right_anchor_member_id": old_right[0],
                "old_field_ordinal": old_pos,
                "new_field_ordinal": new_pos,
                "interval_offset": old_offset,
                "interval_length": len(old_segment),
                "interval_digest": _stable_digest(old_segment),
                "target_signature_digest": _stable_digest(target_signature),
                "base_context_report_id": recomputed["report_id"],
                "base_context_report_digest": _stable_digest(recomputed),
                "base_context_reason": (
                    "insufficient_independent_context_witness"
                ),
                "base_global_usage_report_id": recomputed[
                    "base_global_usage_report_id"
                ],
            }
        )

    candidates.sort(key=lambda row: row["relationship_id"])
    rejected.sort(key=lambda row: row["relationship_id"])
    if len(candidates) + len(rejected) != len(rows):
        raise CanonicalMethodSingleContextDeclarationEvidenceError(
            "single-context declaration outcome accounting mismatch"
        )

    summary = {
        "input_insufficient_witness_reviews": len(rows),
        "candidate_fields": len(candidates),
        "remaining_without_declaration_proof": len(rejected),
        **counts,
    }
    body = {
        "schema_version": 1,
        "kind": "canonical_method_single_context_declaration_identity_candidates",
        "canonical": False,
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": recomputed.get("old_sha256"),
        "new_sha256": recomputed.get("new_sha256"),
        "member_lineage_digest": recomputed.get("member_lineage_digest"),
        "base_global_usage_report_id": recomputed.get(
            "base_global_usage_report_id"
        ),
        "base_global_usage_report_digest": recomputed.get(
            "base_global_usage_report_digest"
        ),
        "base_context_report_id": recomputed.get("report_id"),
        "base_context_report_digest": _stable_digest(recomputed),
        "summary": summary,
        "candidates": candidates,
        "rejected": rejected,
        "note": (
            "Research-only continuation of canonical-method field-context "
            "evidence. The existing strong-witness threshold is not weakened. "
            "Only rows already rejected solely at insufficient independent "
            "context witness are considered. A candidate must have exactly one "
            "distinct local context in exactly one paired canonical method; one "
            "or more exact target observations may share that context. The "
            "local name-insensitive context must already be proven equal and unique "
            "against same-shape competitor fields in both exact methods by the "
            "recomputed base context report. That isolated behavioral witness is "
            "then combined with an independent exact two-sided canonical field "
            "declaration proof: matching canonical left/right anchor identities, "
            "identical ordered declaration interval, identical target offset, "
            "and a target declaration signature unique in both intervals. "
            "canonical=false; no lineage mutation."
        ),
    }
    return {
        "report_id": (
            "SINGLECTXDECL_"
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
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-canonical-method-single-context-declaration-evidence"
    )
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("old_index", type=Path)
    p.add_argument("new_index", type=Path)
    p.add_argument("old_jar", type=Path)
    p.add_argument("new_jar", type=Path)
    p.add_argument("global_usage_report", type=Path)
    p.add_argument("context_report", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = build_canonical_method_single_context_declaration_evidence(
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.old_index),
            _load(args.new_index),
            args.old_jar,
            args.new_jar,
            _load(args.global_usage_report),
            _load(args.context_report),
        )
        write_report(report, args.out)
    except (
        CanonicalMethodSingleContextDeclarationEvidenceError,
        CanonicalMethodFieldContextEvidenceError,
        LineageValidationError,
        MemberLineageError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(
            "SPK_CANONICAL_METHOD_SINGLE_CONTEXT_DECLARATION_EVIDENCE_FAIL",
            file=__import__("sys").stderr,
        )
        print(str(exc), file=__import__("sys").stderr)
        return 1

    summary = report["summary"]
    print("SPK_CANONICAL_METHOD_SINGLE_CONTEXT_DECLARATION_EVIDENCE_PASS")
    print(f"report_id={report['report_id']}")
    for key, value in summary.items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
