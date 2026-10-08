from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .canonical_method_field_context_evidence import (
    CanonicalMethodFieldContextEvidenceError,
    _ProfileCache,
    _instruction_token,
    _reverse_methods,
    _same_shape_field_coords,
    _target_access_indices,
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


class CanonicalMethodMissingContextFullMethodEvidenceError(MemberLineageError):
    pass


_FIELD_OPS = {"getstatic", "putstatic", "getfield", "putfield"}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CanonicalMethodMissingContextFullMethodEvidenceError(
            f"JSON root must be object: {path}"
        )
    return value


def _full_method_tokens(
    method: dict[str, Any],
    *,
    target: tuple[str, str, str],
    operation: str,
    expected_count: int,
    member_map: dict[tuple[str, str, str, str], str],
    class_aliases: dict[str, str],
) -> list[list[Any]] | None:
    if len(_target_access_indices(method, target=target, operation=operation)) != expected_count:
        return None
    instructions = method.get("instructions")
    if not isinstance(instructions, list) or not instructions:
        return None
    return [
        _instruction_token(
            row,
            target=target,
            member_map=member_map,
            class_aliases=class_aliases,
        )
        for row in instructions
        if isinstance(row, dict)
    ]


def _full_method_unique(
    method: dict[str, Any],
    *,
    target: tuple[str, str, str],
    operation: str,
    expected_count: int,
    target_tokens: list[list[Any]],
    member_map: dict[tuple[str, str, str, str], str],
    class_aliases: dict[str, str],
) -> bool:
    for competitor in sorted(_same_shape_field_coords(method, target)):
        if competitor == target:
            continue
        if not _target_access_indices(
            method,
            target=competitor,
            operation=operation,
        ):
            continue
        other = _full_method_tokens(
            method,
            target=competitor,
            operation=operation,
            expected_count=len(
                _target_access_indices(
                    method,
                    target=competitor,
                    operation=operation,
                )
            ),
            member_map=member_map,
            class_aliases=class_aliases,
        )
        if other is not None and other == target_tokens:
            return False
    return True


def build_canonical_method_missing_context_full_method_evidence(
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
        raise CanonicalMethodMissingContextFullMethodEvidenceError(
            "canonical-method context report does not equal exact-JAR recomputation"
        )

    old_build_id = str(recomputed.get("old_build_id", ""))
    new_build_id = str(recomputed.get("new_build_id", ""))
    if not old_build_id or not new_build_id or old_build_id == new_build_id:
        raise CanonicalMethodMissingContextFullMethodEvidenceError(
            "canonical-method context build binding is invalid"
        )

    rows = [
        row for row in recomputed.get("rejected", [])
        if isinstance(row, dict)
        and row.get("reason") == "canonical_method_context_missing"
    ]

    old_methods, new_methods, _ = _paired_method_maps(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_reverse = _reverse_methods(old_methods)
    new_reverse = _reverse_methods(new_methods)
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
    old_paired, new_paired = _paired_field_maps(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    unresolved = _unresolved_reviews(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    counts = {
        "missing_context_shape_mismatch": 0,
        "full_method_target_access_mismatch": 0,
        "full_method_fingerprint_mismatch": 0,
        "full_method_fingerprint_nonunique": 0,
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
                raise CanonicalMethodMissingContextFullMethodEvidenceError(
                    f"missing-context row {i} is invalid"
                )

            original = unresolved.get(relationship_id)
            if original is None or original.get("strategy") != "stable_symbol":
                raise CanonicalMethodMissingContextFullMethodEvidenceError(
                    f"{relationship_id}: missing from exact stable-symbol frontier"
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

            method_id = row.get("method_id")
            operation = row.get("operation")
            expected_count = row.get("expected_count")
            if (
                not isinstance(method_id, str)
                or not method_id
                or method_id not in old_reverse
                or method_id not in new_reverse
                or operation not in _FIELD_OPS
                or not isinstance(expected_count, int)
                or isinstance(expected_count, bool)
                or expected_count <= 0
                or row.get("old_context_count") != 0
                or row.get("new_context_count") != 0
            ):
                reject("missing_context_shape_mismatch")
                continue

            old_coord = _coord(original.get("old"), label=f"{relationship_id}.old")
            new_coord = _coord(original.get("new"), label=f"{relationship_id}.new")
            old_target = (old_owner, old_coord[0], old_coord[1])
            new_target = (new_owner, new_coord[0], new_coord[1])
            old_method = old_cache.method(old_reverse[method_id])
            new_method = new_cache.method(new_reverse[method_id])

            old_tokens = _full_method_tokens(
                old_method,
                target=old_target,
                operation=operation,
                expected_count=expected_count,
                member_map=old_member_map,
                class_aliases=old_class_aliases,
            )
            new_tokens = _full_method_tokens(
                new_method,
                target=new_target,
                operation=operation,
                expected_count=expected_count,
                member_map=new_member_map,
                class_aliases=new_class_aliases,
            )
            if old_tokens is None or new_tokens is None:
                reject(
                    "full_method_target_access_mismatch",
                    method_id=method_id,
                    operation=operation,
                    expected_count=expected_count,
                )
                continue
            if old_tokens != new_tokens:
                reject(
                    "full_method_fingerprint_mismatch",
                    method_id=method_id,
                    operation=operation,
                    old_digest=_stable_digest(old_tokens),
                    new_digest=_stable_digest(new_tokens),
                )
                continue

            old_unique = _full_method_unique(
                old_method,
                target=old_target,
                operation=operation,
                expected_count=expected_count,
                target_tokens=old_tokens,
                member_map=old_member_map,
                class_aliases=old_class_aliases,
            )
            new_unique = _full_method_unique(
                new_method,
                target=new_target,
                operation=operation,
                expected_count=expected_count,
                target_tokens=new_tokens,
                member_map=new_member_map,
                class_aliases=new_class_aliases,
            )
            if not old_unique or not new_unique:
                reject(
                    "full_method_fingerprint_nonunique",
                    method_id=method_id,
                    operation=operation,
                    old_unique=old_unique,
                    new_unique=new_unique,
                    fingerprint_digest=_stable_digest(old_tokens),
                )
                continue

            old_fields = _jar_field_table(old_jar, owner=old_owner)
            new_fields = _jar_field_table(new_jar, owner=new_owner)
            old_pos = _field_index(old_fields, old_coord, label=f"{relationship_id}.old")
            new_pos = _field_index(new_fields, new_coord, label=f"{relationship_id}.new")
            old_left = _paired_anchor_id(
                old_fields, old_paired, owner=old_owner,
                target_index=old_pos, direction=-1,
            )
            old_right = _paired_anchor_id(
                old_fields, old_paired, owner=old_owner,
                target_index=old_pos, direction=1,
            )
            new_left = _paired_anchor_id(
                new_fields, new_paired, owner=new_owner,
                target_index=new_pos, direction=-1,
            )
            new_right = _paired_anchor_id(
                new_fields, new_paired, owner=new_owner,
                target_index=new_pos, direction=1,
            )
            if any(v is None for v in (old_left, old_right, new_left, new_right)):
                reject("missing_two_sided_canonical_anchor")
                continue
            assert old_left and old_right and new_left and new_right

            if old_left[0] != new_left[0] or old_right[0] != new_right[0]:
                reject(
                    "canonical_anchor_identity_mismatch",
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
            target_signature = old_segment[old_offset]
            old_occurrences = sum(v == target_signature for v in old_segment)
            new_occurrences = sum(v == target_signature for v in new_segment)
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
                        "canonical_method_full_normalized_fingerprint_and_"
                        "canonical_anchor_declaration_interval_exact"
                    ),
                    "confidence": "INFERRED_HIGH",
                    "score": 0.9993,
                    "supports_existing_review": True,
                    "method_id": method_id,
                    "operation": operation,
                    "expected_count": expected_count,
                    "full_method_instruction_count": len(old_tokens),
                    "full_method_fingerprint_digest": _stable_digest(old_tokens),
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
                    "base_context_reason": "canonical_method_context_missing",
                    "base_global_usage_report_id": recomputed[
                        "base_global_usage_report_id"
                    ],
                }
            )
    finally:
        old_cache.close()
        new_cache.close()

    candidates.sort(key=lambda row: row["relationship_id"])
    rejected.sort(key=lambda row: row["relationship_id"])
    if len(candidates) + len(rejected) != len(rows):
        raise CanonicalMethodMissingContextFullMethodEvidenceError(
            "missing-context full-method outcome accounting mismatch"
        )

    summary = {
        "input_context_missing_reviews": len(rows),
        "candidate_fields": len(candidates),
        "remaining_without_full_method_proof": len(rejected),
        **counts,
    }
    body = {
        "schema_version": 1,
        "kind": "canonical_method_missing_context_full_method_identity_candidates",
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
            "Research-only continuation of the exact canonical-method context "
            "frontier. Only rows rejected because the radius-4 context extractor "
            "produced zero usable contexts in both builds are considered. The "
            "existing context rule is not weakened. Instead the entire paired "
            "canonical method is normalized with the target operand masked, raw "
            "names/absolute offsets excluded by the certified token normalizer, "
            "and the resulting full-method fingerprint must match old/new and be "
            "unique against same-shape field competitors in both methods. An "
            "independent exact two-sided canonical declaration interval proof is "
            "then required. canonical=false; no lineage mutation."
        ),
    }
    return {
        "report_id": "MISSINGCTXFULL_"
        + hashlib.sha256(
            json.dumps(
                body,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper(),
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
        prog="spk-canonical-method-missing-context-full-method-evidence"
    )
    for name in (
        "class_lineage", "member_lineage", "old_index", "new_index",
        "old_jar", "new_jar", "global_usage_report", "context_report",
    ):
        p.add_argument(name, type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        report = build_canonical_method_missing_context_full_method_evidence(
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
        CanonicalMethodMissingContextFullMethodEvidenceError,
        CanonicalMethodFieldContextEvidenceError,
        LineageValidationError,
        MemberLineageError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print("SPK_CANONICAL_METHOD_MISSING_CONTEXT_FULL_METHOD_EVIDENCE_FAIL")
        print(str(exc))
        return 1

    print("SPK_CANONICAL_METHOD_MISSING_CONTEXT_FULL_METHOD_EVIDENCE_PASS")
    print(f"report_id={report['report_id']}")
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
