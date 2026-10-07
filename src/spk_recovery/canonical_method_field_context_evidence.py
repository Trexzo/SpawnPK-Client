from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .bytecode_profile import BytecodeProfileError, profile_class_field_accesses
from .classfile import _descriptor_shape
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
from .global_field_usage_evidence import (
    GlobalFieldUsageEvidenceError,
    _paired_method_maps,
    build_global_field_usage_evidence,
)
from .member_lineage import MemberLineageError
from .raw_source_canonical_reference_evidence import (
    _paired_class_aliases,
    _paired_member_maps,
)


class CanonicalMethodFieldContextEvidenceError(MemberLineageError):
    pass


_FIELD_OPS = {"getstatic", "putstatic", "getfield", "putfield"}
_INVOKE_OPS = {
    "invokevirtual",
    "invokespecial",
    "invokestatic",
    "invokeinterface",
}


def _reverse_methods(
    maps: dict[str, dict[tuple[str, str], str]],
) -> dict[str, tuple[str, str, str]]:
    out: dict[str, tuple[str, str, str]] = {}
    for owner, rows in maps.items():
        for (name, descriptor), member_id in rows.items():
            if member_id in out:
                raise CanonicalMethodFieldContextEvidenceError(
                    f"duplicate canonical method ID {member_id!r}"
                )
            out[member_id] = (owner, name, descriptor)
    return out


class _ProfileCache:
    def __init__(self, jar_path: Path):
        self.jar_path = jar_path
        self._archive = zipfile.ZipFile(jar_path, "r")
        self._cache: dict[str, dict[str, Any]] = {}

    def close(self) -> None:
        self._archive.close()

    def class_profile(self, owner: str) -> dict[str, Any]:
        if owner not in self._cache:
            entry = owner + ".class"
            try:
                data = self._archive.read(entry)
            except KeyError as exc:
                raise CanonicalMethodFieldContextEvidenceError(
                    f"class entry missing from exact JAR: {entry}"
                ) from exc
            profile = profile_class_field_accesses(data)
            if profile.get("internal_name") != owner:
                raise CanonicalMethodFieldContextEvidenceError(
                    f"class entry/internal-name mismatch: {entry}"
                )
            self._cache[owner] = profile
        return self._cache[owner]

    def method(
        self,
        coord: tuple[str, str, str],
    ) -> dict[str, Any]:
        owner, name, descriptor = coord
        matches = [
            row
            for row in self.class_profile(owner).get("methods", [])
            if isinstance(row, dict)
            and row.get("name") == name
            and row.get("descriptor") == descriptor
        ]
        if len(matches) != 1:
            raise CanonicalMethodFieldContextEvidenceError(
                f"canonical method coordinate is not unique: {coord!r}"
            )
        return matches[0]


def _member_identity(
    member_map: dict[tuple[str, str, str, str], str],
    *,
    kind: str,
    owner: str,
    name: str,
    descriptor: str,
) -> str | None:
    return member_map.get((kind, owner, name, descriptor))


def _normalize_constant(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", value]
    if isinstance(value, float):
        return ["float", repr(value)]
    if isinstance(value, str):
        # Deliberately avoid literal strings/class names as identity evidence.
        return ["string"]
    return ["other", type(value).__name__]


def _instruction_token(
    row: dict[str, Any],
    *,
    target: tuple[str, str, str],
    member_map: dict[tuple[str, str, str, str], str],
    class_aliases: dict[str, str],
) -> list[Any]:
    mnemonic = str(row.get("mnemonic", row.get("opcode", "")))
    owner = row.get("owner")
    name = row.get("name")
    descriptor = row.get("descriptor")

    if (
        mnemonic in _FIELD_OPS
        and isinstance(owner, str)
        and isinstance(name, str)
        and isinstance(descriptor, str)
    ):
        coord = (owner, name, descriptor)
        if coord == target:
            return [
                "TARGET_FIELD",
                mnemonic,
                _descriptor_shape(descriptor),
            ]
        member_id = _member_identity(
            member_map,
            kind="field",
            owner=owner,
            name=name,
            descriptor=descriptor,
        )
        if member_id is not None:
            return ["FIELD_CANON", mnemonic, member_id]
        return [
            "FIELD_SHAPE",
            mnemonic,
            _descriptor_shape(descriptor),
        ]

    if (
        mnemonic in _INVOKE_OPS
        and isinstance(owner, str)
        and isinstance(name, str)
        and isinstance(descriptor, str)
    ):
        member_id = _member_identity(
            member_map,
            kind="method",
            owner=owner,
            name=name,
            descriptor=descriptor,
        )
        if member_id is not None:
            return ["METHOD_CANON", mnemonic, member_id]
        return [
            "METHOD_SHAPE",
            mnemonic,
            _descriptor_shape(descriptor),
        ]

    if mnemonic == "invokedynamic":
        return [
            "INVOKEDYNAMIC",
            _descriptor_shape(str(row.get("descriptor", ""))),
        ]

    if mnemonic in {"new", "anewarray", "checkcast", "instanceof"}:
        raw_type = row.get("type")
        if isinstance(raw_type, str):
            logical_id = class_aliases.get(raw_type)
            if logical_id is not None:
                return ["TYPE_CANON", mnemonic, logical_id]
        return ["TYPE_SHAPE", mnemonic]

    token: list[Any] = ["OP", mnemonic]
    if "local_index" in row:
        token.extend(["local", int(row["local_index"])])
    if "increment" in row:
        token.extend(["increment", int(row["increment"])])
    if "int_constant" in row:
        token.extend(["int", int(row["int_constant"])])
    if "constant" in row:
        token.extend(["constant", _normalize_constant(row.get("constant"))])
    if "wide_mnemonic" in row:
        token.extend(["wide", str(row["wide_mnemonic"])])
    # Absolute branch targets, bytecode offsets and CP indices are excluded.
    return token


def _target_access_indices(
    method: dict[str, Any],
    *,
    target: tuple[str, str, str],
    operation: str | None = None,
) -> list[int]:
    instructions = method.get("instructions", [])
    result: list[int] = []
    for i, row in enumerate(instructions):
        if not isinstance(row, dict):
            continue
        if row.get("mnemonic") not in _FIELD_OPS:
            continue
        coord = (
            str(row.get("owner", "")),
            str(row.get("name", "")),
            str(row.get("descriptor", "")),
        )
        if coord != target:
            continue
        if operation is not None and row.get("mnemonic") != operation:
            continue
        result.append(i)
    return result


def _context_multiset(
    method: dict[str, Any],
    *,
    target: tuple[str, str, str],
    operation: str,
    member_map: dict[tuple[str, str, str, str], str],
    class_aliases: dict[str, str],
    radius: int = 4,
) -> Counter[str]:
    instructions = method.get("instructions", [])
    if not isinstance(instructions, list):
        raise CanonicalMethodFieldContextEvidenceError(
            "method instructions must be list"
        )
    result: Counter[str] = Counter()
    for index in _target_access_indices(
        method,
        target=target,
        operation=operation,
    ):
        left = max(0, index - radius)
        right = min(len(instructions), index + radius + 1)
        if right - left < 3:
            continue
        window = [
            _instruction_token(
                row,
                target=target,
                member_map=member_map,
                class_aliases=class_aliases,
            )
            for row in instructions[left:right]
            if isinstance(row, dict)
        ]
        material = {
            "radius": radius,
            "target_index": index - left,
            "window": window,
        }
        result[_stable_digest(material)] += 1
    return result


def _same_shape_field_coords(
    method: dict[str, Any],
    target: tuple[str, str, str],
) -> set[tuple[str, str, str]]:
    target_shape = _descriptor_shape(target[2])
    coords: set[tuple[str, str, str]] = set()
    for row in method.get("field_accesses", []):
        if not isinstance(row, dict):
            continue
        owner = str(row.get("owner", ""))
        name = str(row.get("name", ""))
        descriptor = str(row.get("descriptor", ""))
        if not owner or not name or not descriptor:
            continue
        if _descriptor_shape(descriptor) == target_shape:
            coords.add((owner, name, descriptor))
    return coords


def _context_unique_in_method(
    method: dict[str, Any],
    *,
    target: tuple[str, str, str],
    operation: str,
    target_context: Counter[str],
    member_map: dict[tuple[str, str, str, str], str],
    class_aliases: dict[str, str],
) -> bool:
    if not target_context:
        return False
    for competitor in sorted(_same_shape_field_coords(method, target)):
        if competitor == target:
            continue
        other = _context_multiset(
            method,
            target=competitor,
            operation=operation,
            member_map=member_map,
            class_aliases=class_aliases,
        )
        if other and other == target_context:
            return False
    return True


def _counter_rows(value: Counter[str]) -> list[list[Any]]:
    return [[digest, count] for digest, count in sorted(value.items())]


def _base_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in report.get("review_outcomes", [])
        if isinstance(row, dict)
        and row.get("outcome") == "global_class_topology_guard_rejected"
    ]
    rows.sort(key=lambda row: str(row.get("relationship_id", "")))
    return rows


def build_canonical_method_field_context_evidence(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
) -> dict[str, Any]:
    old_build_id = str(global_usage_report.get("old_build_id", ""))
    new_build_id = str(global_usage_report.get("new_build_id", ""))
    if not old_build_id or not new_build_id or old_build_id == new_build_id:
        raise CanonicalMethodFieldContextEvidenceError(
            "global usage report build binding is invalid"
        )

    recomputed = build_global_field_usage_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    if _stable_digest(recomputed) != _stable_digest(global_usage_report):
        raise CanonicalMethodFieldContextEvidenceError(
            "global usage report does not equal exact-JAR recomputation"
        )

    rows = _base_rows(recomputed)
    old_method_maps, new_method_maps, _paired_count = _paired_method_maps(
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
    unresolved = _unresolved_reviews(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    counts = {
        "canonical_method_context_missing": 0,
        "canonical_method_context_mismatch": 0,
        "canonical_method_context_nonunique": 0,
        "insufficient_independent_context_witness": 0,
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
        for row in rows:
            relationship_id = str(row.get("relationship_id", ""))
            logical_class_id = str(row.get("logical_class_id", ""))
            original = unresolved.get(relationship_id)
            if (
                not relationship_id
                or not logical_class_id
                or original is None
                or original.get("strategy") != "stable_symbol"
            ):
                raise CanonicalMethodFieldContextEvidenceError(
                    f"invalid global-topology frontier row {relationship_id!r}"
                )

            old_owner = str(row.get("old_owner", "")).removesuffix(".class")
            new_owner = str(row.get("new_owner", "")).removesuffix(".class")
            old_coord = _coord(original.get("old"), label=f"{relationship_id}.old")
            new_coord = _coord(original.get("new"), label=f"{relationship_id}.new")
            old_target = (old_owner, old_coord[0], old_coord[1])
            new_target = (new_owner, new_coord[0], new_coord[1])

            method_topology = row.get("canonical_method_topology")
            if not isinstance(method_topology, list) or not method_topology:
                raise CanonicalMethodFieldContextEvidenceError(
                    f"{relationship_id}: missing exact canonical method topology"
                )

            method_witnesses: list[dict[str, Any]] = []
            all_contexts: set[str] = set()
            observation_count = 0

            def reject(reason: str, **evidence: Any) -> None:
                counts[reason] += 1
                rejected.append(
                    {
                        "relationship_id": relationship_id,
                        "logical_class_id": logical_class_id,
                        "old_owner": old_owner,
                        "new_owner": new_owner,
                        "reason": reason,
                        "base_global_usage_outcome": (
                            "global_class_topology_guard_rejected"
                        ),
                        **evidence,
                    }
                )

            failed = False
            nonunique = False
            for topo in method_topology:
                if not isinstance(topo, dict):
                    raise CanonicalMethodFieldContextEvidenceError(
                        f"{relationship_id}: malformed method topology row"
                    )
                method_id = str(topo.get("member_id", ""))
                operation = str(topo.get("operation", ""))
                expected_count = int(topo.get("count", 0))
                if (
                    not method_id
                    or operation not in _FIELD_OPS
                    or expected_count <= 0
                    or method_id not in old_reverse
                    or method_id not in new_reverse
                ):
                    raise CanonicalMethodFieldContextEvidenceError(
                        f"{relationship_id}: invalid canonical method topology"
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

                if (
                    sum(old_ctx.values()) != expected_count
                    or sum(new_ctx.values()) != expected_count
                    or not old_ctx
                    or not new_ctx
                ):
                    reject(
                        "canonical_method_context_missing",
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
                        "canonical_method_context_mismatch",
                        method_id=method_id,
                        operation=operation,
                        expected_count=expected_count,
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
                        "canonical_method_context_nonunique",
                        method_id=method_id,
                        operation=operation,
                        old_unique=old_unique,
                        new_unique=new_unique,
                        contexts=_counter_rows(old_ctx),
                    )
                    failed = True
                    nonunique = True
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
                observation_count += expected_count

            if failed:
                continue

            method_ids = {row["method_id"] for row in method_witnesses}
            strong_witness = (
                len(method_ids) >= 2
                or (
                    observation_count >= 2
                    and len(all_contexts) >= 2
                )
            )
            if not strong_witness:
                reject(
                    "insufficient_independent_context_witness",
                    canonical_methods=len(method_ids),
                    observations=observation_count,
                    distinct_contexts=len(all_contexts),
                    method_witnesses=method_witnesses,
                )
                continue

            old_fields = _jar_field_table(old_jar, owner=old_owner)
            new_fields = _jar_field_table(new_jar, owner=new_owner)
            old_pos = _field_index(old_fields, old_coord, label=f"{relationship_id}.old")
            new_pos = _field_index(new_fields, new_coord, label=f"{relationship_id}.new")

            old_left = _paired_anchor_id(
                old_fields,
                old_paired_fields,
                owner=old_owner,
                target_index=old_pos,
                direction=-1,
            )
            old_right = _paired_anchor_id(
                old_fields,
                old_paired_fields,
                owner=old_owner,
                target_index=old_pos,
                direction=1,
            )
            new_left = _paired_anchor_id(
                new_fields,
                new_paired_fields,
                owner=new_owner,
                target_index=new_pos,
                direction=-1,
            )
            new_right = _paired_anchor_id(
                new_fields,
                new_paired_fields,
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
                    method_witnesses=method_witnesses,
                )
                continue

            if old_left[0] != new_left[0] or old_right[0] != new_right[0]:
                reject(
                    "canonical_anchor_identity_mismatch",
                    method_witnesses=method_witnesses,
                    old_left_member_id=old_left[0],
                    new_left_member_id=new_left[0],
                    old_right_member_id=old_right[0],
                    new_right_member_id=new_right[0],
                )
                continue

            old_segment = _segment_signatures(
                old_fields,
                old_decl_aliases,
                left_index=old_left[1],
                right_index=old_right[1],
            )
            new_segment = _segment_signatures(
                new_fields,
                new_decl_aliases,
                left_index=new_left[1],
                right_index=new_right[1],
            )
            if len(old_segment) != len(new_segment):
                reject(
                    "declaration_interval_length_mismatch",
                    method_witnesses=method_witnesses,
                    old_interval_length=len(old_segment),
                    new_interval_length=len(new_segment),
                )
                continue
            if old_segment != new_segment:
                reject(
                    "declaration_interval_shape_mismatch",
                    method_witnesses=method_witnesses,
                    old_interval_digest=_stable_digest(old_segment),
                    new_interval_digest=_stable_digest(new_segment),
                )
                continue

            old_offset = old_pos - old_left[1] - 1
            new_offset = new_pos - new_left[1] - 1
            if old_offset != new_offset:
                reject(
                    "target_interval_offset_mismatch",
                    method_witnesses=method_witnesses,
                    old_offset=old_offset,
                    new_offset=new_offset,
                )
                continue

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
                    method_witnesses=method_witnesses,
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
                        "canonical_method_unique_local_context_and_"
                        "canonical_anchor_declaration_interval_exact"
                    ),
                    "confidence": "INFERRED_HIGH",
                    "score": 0.9994,
                    "supports_existing_review": True,
                    "canonical_methods": len(method_ids),
                    "observations": observation_count,
                    "distinct_contexts": len(all_contexts),
                    "method_witnesses": method_witnesses,
                    "left_anchor_member_id": old_left[0],
                    "right_anchor_member_id": old_right[0],
                    "old_field_ordinal": old_pos,
                    "new_field_ordinal": new_pos,
                    "interval_offset": old_offset,
                    "interval_length": len(old_segment),
                    "interval_digest": _stable_digest(old_segment),
                    "base_global_usage_report_id": recomputed["report_id"],
                    "base_global_usage_outcome": (
                        "global_class_topology_guard_rejected"
                    ),
                }
            )
    finally:
        old_cache.close()
        new_cache.close()

    candidates.sort(key=lambda row: row["relationship_id"])
    rejected.sort(key=lambda row: row["relationship_id"])
    if len(candidates) + len(rejected) != len(rows):
        raise CanonicalMethodFieldContextEvidenceError(
            "canonical-method context outcome accounting mismatch"
        )

    summary = {
        "input_global_class_topology_guard_rejected": len(rows),
        "candidate_fields": len(candidates),
        "remaining_without_context_proof": len(rejected),
        **counts,
    }
    body = {
        "schema_version": 1,
        "kind": "canonical_method_field_context_identity_candidates",
        "canonical": False,
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": recomputed["old_sha256"],
        "new_sha256": recomputed["new_sha256"],
        "member_lineage_digest": recomputed["member_lineage_digest"],
        "base_global_usage_report_id": recomputed["report_id"],
        "base_global_usage_report_digest": _stable_digest(recomputed),
        "summary": summary,
        "candidates": candidates,
        "rejected": rejected,
        "note": (
            "Research-only field identity evidence over rows already rejected "
            "by the complete global source-class topology guard. The guard is "
            "not weakened or reclassified. A new independent candidate requires "
            "the exact paired canonical-method access topology from the base "
            "report plus exact name-insensitive local JVM instruction-context "
            "multisets for every target access in each paired canonical method. "
            "The target field operand is masked. Neighboring paired members and "
            "classes are normalized to canonical IDs; unresolved member names, "
            "RAW type names, literal strings, constant-pool indices, absolute "
            "bytecode offsets and absolute branch targets cannot contribute. "
            "The target context multiset must also be unique against other "
            "same-shape fields in both exact methods. At least two canonical "
            "methods, or two observations with two distinct contexts, are "
            "required before the unchanged two-sided canonical declaration "
            "interval proof is applied. canonical=false; no lineage mutation."
        ),
    }
    return {
        "report_id": (
            "METHODCTX_"
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
