from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .canonical_method_field_context_evidence import (
    CanonicalMethodFieldContextEvidenceError,
    _ProfileCache,
    _context_multiset,
    _context_unique_in_method,
    _counter_rows,
    _reverse_methods,
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
from .global_field_usage_evidence import _paired_method_maps
from .lineage import LineageValidationError, load_lineage
from .member_lineage import MemberLineageError, load_member_lineage
from .raw_source_canonical_reference_evidence import (
    _paired_class_aliases,
    _paired_member_maps,
)


class CanonicalMethodPartialMultimethodContextEvidenceError(MemberLineageError):
    pass


_FIELD_OPS = {"getstatic", "putstatic", "getfield", "putfield"}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CanonicalMethodPartialMultimethodContextEvidenceError(
            f"JSON root must be object: {path}"
        )
    return value


def _global_rows(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in report.get("review_outcomes", []):
        if (
            isinstance(row, dict)
            and row.get("outcome") == "global_class_topology_guard_rejected"
        ):
            relationship_id = row.get("relationship_id")
            if not isinstance(relationship_id, str) or not relationship_id:
                raise CanonicalMethodPartialMultimethodContextEvidenceError(
                    "global topology row lacks relationship_id"
                )
            if relationship_id in out:
                raise CanonicalMethodPartialMultimethodContextEvidenceError(
                    f"duplicate global relationship_id {relationship_id!r}"
                )
            out[relationship_id] = row
    return out


def build_canonical_method_partial_multimethod_context_evidence(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
    context_report: dict[str, Any],
) -> dict[str, Any]:
    recomputed_context = build_canonical_method_field_context_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
    )
    if _stable_digest(recomputed_context) != _stable_digest(context_report):
        raise CanonicalMethodPartialMultimethodContextEvidenceError(
            "canonical-method context report does not equal exact-JAR recomputation"
        )

    old_build_id = str(recomputed_context.get("old_build_id", ""))
    new_build_id = str(recomputed_context.get("new_build_id", ""))
    if not old_build_id or not new_build_id or old_build_id == new_build_id:
        raise CanonicalMethodPartialMultimethodContextEvidenceError(
            "canonical-method context build binding is invalid"
        )

    rows = [
        row
        for row in recomputed_context.get("rejected", [])
        if isinstance(row, dict)
        and row.get("reason") == "canonical_method_context_missing"
    ]
    global_rows = _global_rows(global_usage_report)

    unresolved = _unresolved_reviews(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_method_maps, new_method_maps, _ = _paired_method_maps(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_reverse = _reverse_methods(old_method_maps)
    new_reverse = _reverse_methods(new_method_maps)
    old_member_map, new_member_map = _paired_member_maps(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_class_aliases, new_class_aliases = _paired_class_aliases(
        class_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_decl_aliases = _aliases(class_lineage, old_build_id)
    new_decl_aliases = _aliases(class_lineage, new_build_id)
    old_paired_fields, new_paired_fields = _paired_field_maps(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    counts = {
        "no_symmetric_unavailable_context": 0,
        "partial_context_observation_count_mismatch": 0,
        "partial_context_mismatch": 0,
        "partial_context_nonunique": 0,
        "insufficient_surviving_context_witness": 0,
        "missing_two_sided_canonical_anchor": 0,
        "canonical_anchor_identity_mismatch": 0,
        "declaration_interval_length_mismatch": 0,
        "declaration_interval_shape_mismatch": 0,
        "target_interval_offset_mismatch": 0,
        "target_declaration_signature_not_unique": 0,
    }

    old_cache = _ProfileCache(old_jar)
    new_cache = _ProfileCache(new_jar)
    try:
        for i, row in enumerate(rows):
            relationship_id = row.get("relationship_id")
            logical_class_id = row.get("logical_class_id")
            old_owner = str(row.get("old_owner", "")).removesuffix(".class")
            new_owner = str(row.get("new_owner", "")).removesuffix(".class")
            if (
                not isinstance(relationship_id, str)
                or not relationship_id
                or not isinstance(logical_class_id, str)
                or not logical_class_id
                or not old_owner
                or not new_owner
            ):
                raise CanonicalMethodPartialMultimethodContextEvidenceError(
                    f"missing-context row {i} is invalid"
                )

            original = unresolved.get(relationship_id)
            global_row = global_rows.get(relationship_id)
            if (
                original is None
                or original.get("strategy") != "stable_symbol"
                or global_row is None
            ):
                raise CanonicalMethodPartialMultimethodContextEvidenceError(
                    f"{relationship_id}: missing exact frontier binding"
                )

            old_coord = _coord(original.get("old"), label=f"{relationship_id}.old")
            new_coord = _coord(original.get("new"), label=f"{relationship_id}.new")
            old_target = (old_owner, old_coord[0], old_coord[1])
            new_target = (new_owner, new_coord[0], new_coord[1])
            topology = global_row.get("canonical_method_topology")
            if not isinstance(topology, list) or not topology:
                raise CanonicalMethodPartialMultimethodContextEvidenceError(
                    f"{relationship_id}: missing canonical method topology"
                )

            def reject(reason: str, **extra: Any) -> None:
                counts[reason] += 1
                rejected.append(
                    {
                        "relationship_id": relationship_id,
                        "logical_class_id": logical_class_id,
                        "old_owner": old_owner,
                        "new_owner": new_owner,
                        "reason": reason,
                        "base_context_reason": "canonical_method_context_missing",
                        **extra,
                    }
                )

            method_witnesses: list[dict[str, Any]] = []
            unavailable_methods: list[dict[str, Any]] = []
            all_contexts: set[str] = set()
            observations = 0
            failed = False

            for topo in topology:
                if not isinstance(topo, dict):
                    raise CanonicalMethodPartialMultimethodContextEvidenceError(
                        f"{relationship_id}: malformed method topology"
                    )
                method_id = topo.get("member_id")
                operation = topo.get("operation")
                expected_count = topo.get("count")
                if (
                    not isinstance(method_id, str)
                    or not method_id
                    or operation not in _FIELD_OPS
                    or not isinstance(expected_count, int)
                    or isinstance(expected_count, bool)
                    or expected_count <= 0
                    or method_id not in old_reverse
                    or method_id not in new_reverse
                ):
                    raise CanonicalMethodPartialMultimethodContextEvidenceError(
                        f"{relationship_id}: invalid method topology row"
                    )

                old_method = old_cache.method(old_reverse[method_id])
                new_method = new_cache.method(new_reverse[method_id])
                old_ctx = _context_multiset(
                    old_method,
                    target=old_target,
                    operation=operation,
                    member_map=old_member_map,
                    class_aliases=old_class_aliases,
                )
                new_ctx = _context_multiset(
                    new_method,
                    target=new_target,
                    operation=operation,
                    member_map=new_member_map,
                    class_aliases=new_class_aliases,
                )

                if not old_ctx and not new_ctx:
                    unavailable_methods.append(
                        {
                            "method_id": method_id,
                            "operation": operation,
                            "expected_count": expected_count,
                            "old_context_count": 0,
                            "new_context_count": 0,
                        }
                    )
                    continue

                if (
                    sum(old_ctx.values()) != expected_count
                    or sum(new_ctx.values()) != expected_count
                ):
                    reject(
                        "partial_context_observation_count_mismatch",
                        method_id=method_id,
                        operation=operation,
                        expected_count=expected_count,
                        old_context_count=sum(old_ctx.values()),
                        new_context_count=sum(new_ctx.values()),
                    )
                    failed = True
                    break

                if old_ctx != new_ctx:
                    reject(
                        "partial_context_mismatch",
                        method_id=method_id,
                        operation=operation,
                        old_contexts=_counter_rows(old_ctx),
                        new_contexts=_counter_rows(new_ctx),
                    )
                    failed = True
                    break

                old_unique = _context_unique_in_method(
                    old_method,
                    target=old_target,
                    operation=operation,
                    target_context=old_ctx,
                    member_map=old_member_map,
                    class_aliases=old_class_aliases,
                )
                new_unique = _context_unique_in_method(
                    new_method,
                    target=new_target,
                    operation=operation,
                    target_context=new_ctx,
                    member_map=new_member_map,
                    class_aliases=new_class_aliases,
                )
                if not old_unique or not new_unique:
                    reject(
                        "partial_context_nonunique",
                        method_id=method_id,
                        operation=operation,
                        old_unique=old_unique,
                        new_unique=new_unique,
                        contexts=_counter_rows(old_ctx),
                    )
                    failed = True
                    break

                method_witnesses.append(
                    {
                        "method_id": method_id,
                        "operation": operation,
                        "count": expected_count,
                        "contexts": _counter_rows(old_ctx),
                    }
                )
                all_contexts.update(old_ctx)
                observations += expected_count

            if failed:
                continue

            if not unavailable_methods:
                reject(
                    "no_symmetric_unavailable_context",
                    method_witnesses=method_witnesses,
                )
                continue

            method_ids = {value["method_id"] for value in method_witnesses}
            strong = (
                len(method_ids) >= 2
                or (observations >= 2 and len(all_contexts) >= 2)
            )
            if not strong:
                reject(
                    "insufficient_surviving_context_witness",
                    canonical_methods=len(method_ids),
                    observations=observations,
                    distinct_contexts=len(all_contexts),
                    method_witnesses=method_witnesses,
                    unavailable_methods=unavailable_methods,
                )
                continue

            old_fields = _jar_field_table(old_jar, owner=old_owner)
            new_fields = _jar_field_table(new_jar, owner=new_owner)
            old_pos = _field_index(old_fields, old_coord, label=f"{relationship_id}.old")
            new_pos = _field_index(new_fields, new_coord, label=f"{relationship_id}.new")

            old_left = _paired_anchor_id(
                old_fields, old_paired_fields, owner=old_owner,
                target_index=old_pos, direction=-1,
            )
            old_right = _paired_anchor_id(
                old_fields, old_paired_fields, owner=old_owner,
                target_index=old_pos, direction=1,
            )
            new_left = _paired_anchor_id(
                new_fields, new_paired_fields, owner=new_owner,
                target_index=new_pos, direction=-1,
            )
            new_right = _paired_anchor_id(
                new_fields, new_paired_fields, owner=new_owner,
                target_index=new_pos, direction=1,
            )

            if any(value is None for value in (old_left, old_right, new_left, new_right)):
                reject(
                    "missing_two_sided_canonical_anchor",
                    method_witnesses=method_witnesses,
                    unavailable_methods=unavailable_methods,
                )
                continue

            assert old_left is not None
            assert old_right is not None
            assert new_left is not None
            assert new_right is not None

            if old_left[0] != new_left[0] or old_right[0] != new_right[0]:
                reject(
                    "canonical_anchor_identity_mismatch",
                    method_witnesses=method_witnesses,
                    unavailable_methods=unavailable_methods,
                    old_left_member_id=old_left[0],
                    new_left_member_id=new_left[0],
                    old_right_member_id=old_right[0],
                    new_right_member_id=new_right[0],
                )
                continue

            old_segment = _segment_signatures(
                old_fields, old_decl_aliases,
                left_index=old_left[1], right_index=old_right[1],
            )
            new_segment = _segment_signatures(
                new_fields, new_decl_aliases,
                left_index=new_left[1], right_index=new_right[1],
            )
            if len(old_segment) != len(new_segment):
                reject(
                    "declaration_interval_length_mismatch",
                    old_interval_length=len(old_segment),
                    new_interval_length=len(new_segment),
                )
                continue
            if old_segment != new_segment:
                reject(
                    "declaration_interval_shape_mismatch",
                    old_interval_digest=_stable_digest(old_segment),
                    new_interval_digest=_stable_digest(new_segment),
                )
                continue

            old_offset = old_pos - old_left[1] - 1
            new_offset = new_pos - new_left[1] - 1
            if old_offset != new_offset:
                reject(
                    "target_interval_offset_mismatch",
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
                raise CanonicalMethodPartialMultimethodContextEvidenceError(
                    f"{relationship_id}: target lies outside declaration interval"
                )

            target_signature = old_segment[old_offset]
            old_occurrences = sum(1 for value in old_segment if value == target_signature)
            new_occurrences = sum(1 for value in new_segment if value == target_signature)
            if (
                new_segment[new_offset] != target_signature
                or old_occurrences != 1
                or new_occurrences != 1
            ):
                reject(
                    "target_declaration_signature_not_unique",
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
                        "canonical_method_partial_multimethod_unique_context_and_"
                        "canonical_anchor_declaration_interval_exact"
                    ),
                    "confidence": "INFERRED_HIGH",
                    "score": 0.9993,
                    "supports_existing_review": True,
                    "canonical_methods": len(method_ids),
                    "observations": observations,
                    "distinct_contexts": len(all_contexts),
                    "method_witnesses": method_witnesses,
                    "symmetric_unavailable_methods": unavailable_methods,
                    "left_anchor_member_id": old_left[0],
                    "right_anchor_member_id": old_right[0],
                    "old_field_ordinal": old_pos,
                    "new_field_ordinal": new_pos,
                    "interval_offset": old_offset,
                    "interval_length": len(old_segment),
                    "interval_digest": _stable_digest(old_segment),
                    "target_signature_digest": _stable_digest(target_signature),
                    "base_context_report_id": recomputed_context["report_id"],
                    "base_context_report_digest": _stable_digest(recomputed_context),
                    "base_context_reason": "canonical_method_context_missing",
                    "base_global_usage_report_id": recomputed_context[
                        "base_global_usage_report_id"
                    ],
                }
            )
    finally:
        old_cache.close()
        new_cache.close()

    candidates.sort(key=lambda value: value["relationship_id"])
    rejected.sort(key=lambda value: value["relationship_id"])
    if len(candidates) + len(rejected) != len(rows):
        raise CanonicalMethodPartialMultimethodContextEvidenceError(
            "partial multimethod context outcome accounting mismatch"
        )

    summary = {
        "input_missing_context_reviews": len(rows),
        "candidate_fields": len(candidates),
        "remaining_without_partial_context_proof": len(rejected),
        **counts,
    }
    body = {
        "schema_version": 1,
        "kind": "canonical_method_partial_multimethod_context_identity_candidates",
        "canonical": False,
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": recomputed_context.get("old_sha256"),
        "new_sha256": recomputed_context.get("new_sha256"),
        "member_lineage_digest": recomputed_context.get("member_lineage_digest"),
        "base_global_usage_report_id": recomputed_context.get(
            "base_global_usage_report_id"
        ),
        "base_global_usage_report_digest": recomputed_context.get(
            "base_global_usage_report_digest"
        ),
        "base_context_report_id": recomputed_context.get("report_id"),
        "base_context_report_digest": _stable_digest(recomputed_context),
        "summary": summary,
        "candidates": candidates,
        "rejected": rejected,
        "note": (
            "Research-only continuation for rows rejected by the base context "
            "lane because at least one canonical method produced no usable local "
            "window. Only symmetric old/new unavailability may be skipped. "
            "One-sided or partial observation loss, context mismatch, or context "
            "nonuniqueness fails closed. The surviving contexts must still meet "
            "the existing independent-witness threshold, followed by exact "
            "two-sided canonical declaration continuity. canonical=false; no "
            "lineage mutation."
        ),
    }
    return {
        "report_id": (
            "PARTIALMETHODCTX_"
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
        prog="spk-canonical-method-partial-multimethod-context-evidence"
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
        report = build_canonical_method_partial_multimethod_context_evidence(
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
        CanonicalMethodPartialMultimethodContextEvidenceError,
        CanonicalMethodFieldContextEvidenceError,
        LineageValidationError,
        MemberLineageError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(
            "SPK_CANONICAL_METHOD_PARTIAL_MULTIMETHOD_CONTEXT_EVIDENCE_FAIL",
            file=__import__("sys").stderr,
        )
        print(str(exc), file=__import__("sys").stderr)
        return 1

    print("SPK_CANONICAL_METHOD_PARTIAL_MULTIMETHOD_CONTEXT_EVIDENCE_PASS")
    print(f"report_id={report['report_id']}")
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
