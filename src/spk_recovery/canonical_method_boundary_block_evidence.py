from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .boundary_field_block_evidence import _block_signatures
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
    _stable_digest,
    _unresolved_reviews,
)
from .member_lineage import MemberLineageError


class CanonicalMethodBoundaryBlockEvidenceError(MemberLineageError):
    pass


_FIELD_OPS = {"getstatic", "putstatic", "getfield", "putfield"}


def _witness_stats(
    relationship_id: str,
    value: Any,
) -> tuple[int, int, int]:
    if not isinstance(value, list) or not value:
        raise CanonicalMethodBoundaryBlockEvidenceError(
            f"{relationship_id}: method_witnesses must be a non-empty list"
        )

    method_ids: set[str] = set()
    context_ids: set[str] = set()
    observations = 0

    for i, row in enumerate(value):
        if not isinstance(row, dict):
            raise CanonicalMethodBoundaryBlockEvidenceError(
                f"{relationship_id}: method_witnesses[{i}] must be object"
            )
        method_id = row.get("method_id")
        operation = row.get("operation")
        count = row.get("count")
        contexts = row.get("contexts")
        if (
            not isinstance(method_id, str)
            or not method_id
            or operation not in _FIELD_OPS
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count <= 0
            or not isinstance(contexts, list)
            or not contexts
        ):
            raise CanonicalMethodBoundaryBlockEvidenceError(
                f"{relationship_id}: invalid method witness"
            )

        context_total = 0
        for j, item in enumerate(contexts):
            if (
                not isinstance(item, list)
                or len(item) != 2
                or not isinstance(item[0], str)
                or len(item[0]) != 64
                or not isinstance(item[1], int)
                or isinstance(item[1], bool)
                or item[1] <= 0
            ):
                raise CanonicalMethodBoundaryBlockEvidenceError(
                    f"{relationship_id}: invalid context row {i}:{j}"
                )
            context_ids.add(item[0])
            context_total += item[1]

        if context_total != count:
            raise CanonicalMethodBoundaryBlockEvidenceError(
                f"{relationship_id}: witness context/count mismatch"
            )

        method_ids.add(method_id)
        observations += count

    return len(method_ids), observations, len(context_ids)


def _prove_boundary_block(
    *,
    old_fields: list[dict[str, Any]],
    new_fields: list[dict[str, Any]],
    old_paired: dict[tuple[str, str, str], str],
    new_paired: dict[tuple[str, str, str], str],
    old_aliases: dict[str, str],
    new_aliases: dict[str, str],
    old_owner: str,
    new_owner: str,
    old_index_pos: int,
    new_index_pos: int,
) -> tuple[bool, dict[str, Any]]:
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
            return False, {
                "reason": "single_anchor_identity_mismatch",
                "boundary": "class_start",
                "old_anchor": old_right,
                "new_anchor": new_right,
            }
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
            return False, {
                "reason": "single_anchor_identity_mismatch",
                "boundary": "class_end",
                "old_anchor": old_left,
                "new_anchor": new_left,
            }
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
        return False, {
            "reason": "boundary_symmetry_mismatch",
            "old_left": old_left,
            "old_right": old_right,
            "new_left": new_left,
            "new_right": new_right,
        }

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
        return False, {
            "reason": "block_length_mismatch",
            "block_kind": mode,
            "old_length": len(old_block),
            "new_length": len(new_block),
            "anchor_member_id": anchor_member_id,
        }

    if old_block != new_block:
        return False, {
            "reason": "block_shape_mismatch",
            "block_kind": mode,
            "old_block_digest": _stable_digest(old_block),
            "new_block_digest": _stable_digest(new_block),
            "block_length": len(old_block),
            "anchor_member_id": anchor_member_id,
        }

    old_offset = old_index_pos - old_start
    new_offset = new_index_pos - new_start
    if old_offset != new_offset:
        return False, {
            "reason": "target_offset_mismatch",
            "block_kind": mode,
            "old_offset": old_offset,
            "new_offset": new_offset,
            "block_length": len(old_block),
            "anchor_member_id": anchor_member_id,
        }

    if (
        old_offset < 0
        or old_offset >= len(old_block)
        or new_offset < 0
        or new_offset >= len(new_block)
    ):
        raise CanonicalMethodBoundaryBlockEvidenceError(
            "target lies outside matched boundary block"
        )

    target_signature = old_block[old_offset]
    old_occurrences = old_block.count(target_signature)
    new_occurrences = new_block.count(target_signature)
    if (
        new_block[new_offset] != target_signature
        or old_occurrences != 1
        or new_occurrences != 1
    ):
        return False, {
            "reason": "target_signature_not_unique",
            "block_kind": mode,
            "target_offset": old_offset,
            "target_signature_digest": _stable_digest(target_signature),
            "old_occurrences": old_occurrences,
            "new_occurrences": new_occurrences,
            "anchor_member_id": anchor_member_id,
        }

    return True, {
        "block_kind": mode,
        "anchor_member_id": anchor_member_id,
        "block_length": len(old_block),
        "target_offset": old_offset,
        "block_digest": _stable_digest(old_block),
        "target_signature_digest": _stable_digest(target_signature),
    }


def build_canonical_method_boundary_block_evidence(
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
        raise CanonicalMethodBoundaryBlockEvidenceError(
            "canonical-method context report does not equal exact-JAR recomputation"
        )

    old_build_id = str(recomputed.get("old_build_id", ""))
    new_build_id = str(recomputed.get("new_build_id", ""))
    if not old_build_id or not new_build_id or old_build_id == new_build_id:
        raise CanonicalMethodBoundaryBlockEvidenceError(
            "canonical-method context build binding is invalid"
        )

    rows = [
        row
        for row in recomputed.get("rejected", [])
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
            raise CanonicalMethodBoundaryBlockEvidenceError(
                f"context missing-anchor row {i} is invalid/duplicate"
            )
        seen_ids.add(relationship_id)

        method_witnesses = row.get("method_witnesses")
        method_count, observations, distinct_contexts = _witness_stats(
            relationship_id,
            method_witnesses,
        )
        if not (
            method_count >= 2
            or (observations >= 2 and distinct_contexts >= 2)
        ):
            raise CanonicalMethodBoundaryBlockEvidenceError(
                f"{relationship_id}: missing-anchor row lacks strong context witness"
            )

        original = unresolved.get(relationship_id)
        if original is None or original.get("strategy") != "stable_symbol":
            raise CanonicalMethodBoundaryBlockEvidenceError(
                f"{relationship_id}: missing from exact stable-symbol frontier"
            )

        original_old_owner = str(
            original.get("old_owner", "")
        ).removesuffix(".class")
        original_new_owner = str(
            original.get("new_owner", "")
        ).removesuffix(".class")
        if old_owner != original_old_owner or new_owner != original_new_owner:
            raise CanonicalMethodBoundaryBlockEvidenceError(
                f"{relationship_id}: context owner differs from unresolved review"
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
            raise CanonicalMethodBoundaryBlockEvidenceError(
                f"{relationship_id}: duplicate residual coordinate"
            )
        seen_old.add(old_key)
        seen_new.add(new_key)

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

        proven, proof = _prove_boundary_block(
            old_fields=old_fields,
            new_fields=new_fields,
            old_paired=old_paired,
            new_paired=new_paired,
            old_aliases=old_aliases,
            new_aliases=new_aliases,
            old_owner=old_owner,
            new_owner=new_owner,
            old_index_pos=old_pos,
            new_index_pos=new_pos,
        )

        if not proven:
            reason = str(proof.get("reason", ""))
            if reason not in reason_counts:
                raise CanonicalMethodBoundaryBlockEvidenceError(
                    f"{relationship_id}: unsupported boundary rejection {reason!r}"
                )
            reason_counts[reason] += 1
            rejected.append(
                {
                    "relationship_id": relationship_id,
                    "logical_class_id": logical_class_id,
                    "old_owner": old_owner,
                    "new_owner": new_owner,
                    "reason": reason,
                    "base_context_reason": "missing_two_sided_canonical_anchor",
                    "canonical_methods": method_count,
                    "observations": observations,
                    "distinct_contexts": distinct_contexts,
                    "method_witnesses": method_witnesses,
                    **{k: v for k, v in proof.items() if k != "reason"},
                }
            )
            continue

        mode = str(proof["block_kind"])
        mode_counts[mode] += 1
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
                    "canonical_method_unique_local_context_and_"
                    "boundary_block_declaration_exact"
                ),
                "confidence": "INFERRED_HIGH",
                "score": 0.9995,
                "supports_existing_review": True,
                "canonical_methods": method_count,
                "observations": observations,
                "distinct_contexts": distinct_contexts,
                "method_witnesses": method_witnesses,
                **proof,
                "base_context_report_id": recomputed["report_id"],
                "base_context_report_digest": _stable_digest(recomputed),
                "base_context_reason": "missing_two_sided_canonical_anchor",
                "base_global_usage_report_id": recomputed[
                    "base_global_usage_report_id"
                ],
            }
        )

    candidates.sort(key=lambda row: row["relationship_id"])
    rejected.sort(key=lambda row: row["relationship_id"])
    if len(candidates) + len(rejected) != len(rows):
        raise CanonicalMethodBoundaryBlockEvidenceError(
            "method-context boundary-block outcome accounting mismatch"
        )

    summary = {
        "input_context_missing_anchor_reviews": len(rows),
        "candidate_fields": len(candidates),
        "remaining_without_boundary_block_proof": len(rejected),
        **mode_counts,
        **reason_counts,
    }

    body = {
        "schema_version": 1,
        "kind": "canonical_method_boundary_block_identity_candidates",
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
            "evidence. Only rows that already satisfy the strong exact paired "
            "canonical-method local-context identity proof and fail solely at "
            "missing_two_sided_canonical_anchor are considered. The method "
            "witness is not weakened or recomputed from names. Declaration "
            "continuity may be supplied only by the exact certified boundary "
            "semantics: matching prefix/suffix/whole-class declaration blocks, "
            "matching single canonical anchor identity when present, identical "
            "block shape, identical target offset, and a unique target "
            "declaration signature. canonical=false; no lineage mutation."
        ),
    }
    return {
        "report_id": (
            "METHODBOUNDARY_"
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
