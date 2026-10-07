from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .bytecode_profile import (
    BytecodeProfileError,
    profile_class_constant_pool_references,
    profile_class_field_accesses,
)
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
from .global_field_usage_evidence import _paired_method_maps
from .member_lineage import MemberLineageError
from .raw_source_canonical_reference_evidence import (
    RawSourceCanonicalReferenceEvidenceError,
    _paired_class_aliases,
    build_raw_source_canonical_reference_evidence,
)
from .raw_source_exact_declaration_evidence import _topology
from .raw_source_structural_topology_evidence import (
    RawSourceStructuralTopologyEvidenceError,
    _normalize_topology,
    _normalized_rows,
    _topology_rows,
    build_raw_source_structural_topology_evidence,
)


class RawSourceInboundCanonicalEvidenceError(MemberLineageError):
    pass


def _normalize_type_name(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    while value.startswith("["):
        value = value[1:]
    if value.startswith("L") and value.endswith(";"):
        return value[1:-1]
    if not value or len(value) == 1:
        return None
    return value


def _scan_inbound_profiles(
    jar_path: Path,
    *,
    class_aliases: dict[str, str],
    method_maps: dict[str, dict[tuple[str, str], str]],
) -> dict[str, dict[str, Any]]:
    class_sources: dict[str, Counter[str]] = defaultdict(Counter)
    method_events: dict[
        str,
        Counter[tuple[str, str]],
    ] = defaultdict(Counter)

    try:
        with zipfile.ZipFile(jar_path, "r") as archive:
            names = set(archive.namelist())

            for source_owner in sorted(class_aliases):
                entry = source_owner + ".class"
                if entry not in names:
                    raise RawSourceInboundCanonicalEvidenceError(
                        f"canonical source class missing from JAR: {entry}"
                    )

                data = archive.read(entry)
                source_class_id = class_aliases[source_owner]

                cp = profile_class_constant_pool_references(data)
                if cp.get("internal_name") != source_owner:
                    raise RawSourceInboundCanonicalEvidenceError(
                        f"class entry/internal-name mismatch: {entry}"
                    )
                for target in cp.get("class_references", []):
                    target_name = _normalize_type_name(target)
                    if target_name is None or target_name == source_owner:
                        continue
                    class_sources[target_name][source_class_id] += 1

                method_map = method_maps.get(source_owner, {})
                if not method_map:
                    continue

                profile = profile_class_field_accesses(data)
                if profile.get("internal_name") != source_owner:
                    raise RawSourceInboundCanonicalEvidenceError(
                        f"bytecode profile owner mismatch: {entry}"
                    )

                for method in profile.get("methods", []):
                    if not isinstance(method, dict):
                        continue
                    method_id = method_map.get(
                        (
                            str(method.get("name", "")),
                            str(method.get("descriptor", "")),
                        )
                    )
                    if method_id is None:
                        continue

                    for instruction in method.get("instructions", []):
                        if not isinstance(instruction, dict):
                            continue
                        target_name = _normalize_type_name(
                            instruction.get("type")
                        )
                        if target_name is None:
                            continue
                        mnemonic = str(
                            instruction.get("mnemonic", "")
                        )
                        if mnemonic not in {
                            "new",
                            "anewarray",
                            "checkcast",
                            "instanceof",
                        }:
                            continue
                        method_events[target_name][
                            (method_id, f"type:{mnemonic}")
                        ] += 1

                    for access in method.get("field_accesses", []):
                        if not isinstance(access, dict):
                            continue
                        target_name = _normalize_type_name(
                            access.get("owner")
                        )
                        if target_name is None:
                            continue
                        operation = str(access.get("operation", ""))
                        if operation not in {
                            "getstatic",
                            "putstatic",
                            "getfield",
                            "putfield",
                        }:
                            continue
                        shape = _descriptor_shape(
                            str(access.get("descriptor", ""))
                        )
                        method_events[target_name][
                            (
                                method_id,
                                f"field:{operation}:{shape}",
                            )
                        ] += 1

                    for invocation in method.get(
                        "method_invocations",
                        [],
                    ):
                        if not isinstance(invocation, dict):
                            continue
                        target_name = _normalize_type_name(
                            invocation.get("owner")
                        )
                        if target_name is None:
                            continue
                        operation = str(
                            invocation.get("operation", "")
                        )
                        if operation not in {
                            "invokevirtual",
                            "invokespecial",
                            "invokestatic",
                            "invokeinterface",
                        }:
                            continue
                        shape = _descriptor_shape(
                            str(invocation.get("descriptor", ""))
                        )
                        method_events[target_name][
                            (
                                method_id,
                                f"invoke:{operation}:{shape}",
                            )
                        ] += 1

    except (zipfile.BadZipFile, BytecodeProfileError) as exc:
        raise RawSourceInboundCanonicalEvidenceError(
            f"cannot scan inbound canonical topology: {jar_path}"
        ) from exc

    targets = set(class_sources) | set(method_events)
    out: dict[str, dict[str, Any]] = {}
    for target in sorted(targets):
        class_rows = [
            [source_class_id, count]
            for source_class_id, count in sorted(
                class_sources.get(target, {}).items()
            )
        ]
        event_rows = [
            [method_id, signal, count]
            for (method_id, signal), count in sorted(
                method_events.get(target, {}).items()
            )
        ]
        out[target] = {
            "canonical_source_classes": class_rows,
            "canonical_source_method_events": event_rows,
            "canonical_source_class_ids": sorted(
                {row[0] for row in class_rows}
            ),
            "canonical_source_method_ids": sorted(
                {row[0] for row in event_rows}
            ),
            "method_event_count": sum(
                int(row[2]) for row in event_rows
            ),
        }
    return out


def _profile_key(
    profile: dict[str, Any],
    *,
    mode: str,
) -> tuple[Any, ...] | None:
    class_rows = tuple(
        (str(row[0]), int(row[1]))
        for row in profile.get(
            "canonical_source_classes",
            [],
        )
        if isinstance(row, list) and len(row) == 2
    )
    event_rows = tuple(
        (str(row[0]), str(row[1]), int(row[2]))
        for row in profile.get(
            "canonical_source_method_events",
            [],
        )
        if isinstance(row, list) and len(row) == 3
    )
    method_ids = {
        str(row[0])
        for row in profile.get(
            "canonical_source_method_events",
            [],
        )
        if isinstance(row, list) and len(row) == 3
    }
    class_ids = {
        str(row[0])
        for row in profile.get(
            "canonical_source_classes",
            [],
        )
        if isinstance(row, list) and len(row) == 2
    }

    if mode == "canonical_method_inbound_topology":
        if len(method_ids) < 2:
            return None
        return event_rows

    if mode == "canonical_class_method_inbound_topology":
        if not method_ids:
            return None
        if len(method_ids) + len(class_ids) < 3:
            return None
        return class_rows, event_rows

    raise RawSourceInboundCanonicalEvidenceError(
        f"unsupported inbound profile mode {mode!r}"
    )


def _unique_keys(
    profiles: dict[str, dict[str, Any]],
    *,
    mode: str,
) -> dict[tuple[Any, ...], str]:
    buckets: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    for internal_name, profile in profiles.items():
        key = _profile_key(profile, mode=mode)
        if key is not None:
            buckets[key].append(internal_name)
    return {
        key: names[0]
        for key, names in buckets.items()
        if len(names) == 1
    }


def _global_inbound_identity_proofs(
    old_jar: Path,
    new_jar: Path,
    *,
    old_aliases: dict[str, str],
    new_aliases: dict[str, str],
    old_method_maps: dict[str, dict[tuple[str, str], str]],
    new_method_maps: dict[str, dict[tuple[str, str], str]],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, int],
]:
    old_profiles = _scan_inbound_profiles(
        old_jar,
        class_aliases=old_aliases,
        method_maps=old_method_maps,
    )
    new_profiles = _scan_inbound_profiles(
        new_jar,
        class_aliases=new_aliases,
        method_maps=new_method_maps,
    )

    old_proofs: dict[str, dict[str, Any]] = {}
    new_proofs: dict[str, dict[str, Any]] = {}
    counts = {
        "canonical_method_inbound_topology_unique_global": 0,
        "canonical_class_method_inbound_topology_unique_global": 0,
    }

    def install(
        old_name: str,
        new_name: str,
        *,
        strategy: str,
        key: tuple[Any, ...],
    ) -> None:
        if old_name in old_proofs or new_name in new_proofs:
            return
        material = {
            "strategy": strategy,
            "inbound_topology": key,
        }
        digest = _stable_digest(material)
        token = f"{strategy}:{digest}"
        proof = {
            "identity_token": token,
            "strategy": strategy,
            "old_source_class": "RAW:" + old_name,
            "new_source_class": "RAW:" + new_name,
            "inbound_topology_digest": digest,
            "old_profile": old_profiles[old_name],
            "new_profile": new_profiles[new_name],
        }
        old_proofs[old_name] = proof
        new_proofs[new_name] = proof
        counts[strategy] += 1

    modes = [
        (
            "canonical_method_inbound_topology",
            "canonical_method_inbound_topology_unique_global",
        ),
        (
            "canonical_class_method_inbound_topology",
            "canonical_class_method_inbound_topology_unique_global",
        ),
    ]
    for mode, strategy in modes:
        old_unique = _unique_keys(old_profiles, mode=mode)
        new_unique = _unique_keys(new_profiles, mode=mode)
        for key in sorted(
            set(old_unique) & set(new_unique),
            key=repr,
        ):
            install(
                old_unique[key],
                new_unique[key],
                strategy=strategy,
                key=key,
            )

    return old_proofs, new_proofs, counts


def build_raw_source_inbound_canonical_evidence(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
) -> dict[str, Any]:
    previous = build_raw_source_canonical_reference_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
    )
    structural = build_raw_source_structural_topology_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
    )
    if previous.get("canonical") is not False:
        raise RawSourceInboundCanonicalEvidenceError(
            "base canonical-reference report unexpectedly canonical"
        )
    if structural.get("canonical") is not False:
        raise RawSourceInboundCanonicalEvidenceError(
            "base structural-topology report unexpectedly canonical"
        )

    old_build_id = str(previous.get("old_build_id", ""))
    new_build_id = str(previous.get("new_build_id", ""))
    old_sha = str(previous.get("old_sha256", ""))
    new_sha = str(previous.get("new_sha256", ""))
    member_digest = previous.get("member_lineage_digest")
    global_report_id = previous.get("global_usage_report_id")
    previous_report_id = previous.get("report_id")
    structural_report_id = structural.get("report_id")
    structural_report_digest = _stable_digest(structural)
    if (
        not old_build_id
        or not new_build_id
        or old_build_id == new_build_id
        or len(old_sha) != 64
        or len(new_sha) != 64
        or not isinstance(member_digest, str)
        or len(member_digest) != 64
        or not isinstance(global_report_id, str)
        or not global_report_id
        or not isinstance(previous_report_id, str)
        or not previous_report_id
        or not isinstance(structural_report_id, str)
        or not structural_report_id
    ):
        raise RawSourceInboundCanonicalEvidenceError(
            "base report binding is invalid"
        )

    if (
        str(structural.get("old_build_id", "")) != old_build_id
        or str(structural.get("new_build_id", "")) != new_build_id
        or str(structural.get("old_sha256", "")) != old_sha
        or str(structural.get("new_sha256", "")) != new_sha
        or structural.get("member_lineage_digest") != member_digest
        or structural.get("global_usage_report_id") != global_report_id
        or previous.get("base_structural_topology_report_id")
        != structural_report_id
        or previous.get("base_structural_topology_report_digest")
        != structural_report_digest
    ):
        raise RawSourceInboundCanonicalEvidenceError(
            "canonical-reference/structural report binding mismatch"
        )

    target_ids = {
        str(row.get("relationship_id"))
        for row in previous.get("rejected", [])
        if isinstance(row, dict)
        and row.get("reason")
        == "canonical_reference_identity_unproven"
        and isinstance(row.get("relationship_id"), str)
        and row.get("relationship_id")
    }
    topology_rows = {
        str(row.get("relationship_id")): row
        for row in structural.get("rejected", [])
        if isinstance(row, dict)
        and row.get("reason") == "raw_source_identity_unproven"
        and isinstance(row.get("relationship_id"), str)
        and row.get("relationship_id")
    }
    missing = sorted(target_ids - set(topology_rows))
    if missing:
        raise RawSourceInboundCanonicalEvidenceError(
            f"55-row inbound frontier missing structural rows: {missing[:5]!r}"
        )
    rows = [
        topology_rows[relationship_id]
        for relationship_id in sorted(target_ids)
    ]

    old_source_aliases, new_source_aliases = _paired_class_aliases(
        class_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_aliases = _aliases(class_lineage, old_build_id)
    new_aliases = _aliases(class_lineage, new_build_id)
    old_methods, new_methods, _paired_count = _paired_method_maps(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_proofs, new_proofs, global_counts = (
        _global_inbound_identity_proofs(
            old_jar,
            new_jar,
            old_aliases=old_source_aliases,
            new_aliases=new_source_aliases,
            old_method_maps=old_methods,
            new_method_maps=new_methods,
        )
    )

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

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    reasons = {
        "inbound_canonical_identity_unproven": 0,
        "normalized_source_topology_mismatch": 0,
        "missing_two_sided_canonical_anchor": 0,
        "canonical_anchor_identity_mismatch": 0,
        "declaration_interval_length_mismatch": 0,
        "declaration_interval_shape_mismatch": 0,
        "target_interval_offset_mismatch": 0,
        "target_declaration_signature_not_unique": 0,
    }
    used_method_tokens: set[str] = set()
    used_combined_tokens: set[str] = set()
    seen_old: set[tuple[str, str, str]] = set()
    seen_new: set[tuple[str, str, str]] = set()

    for row in rows:
        relationship_id = str(row["relationship_id"])
        logical_class_id = str(row.get("logical_class_id", ""))
        old_owner = str(row.get("old_owner", "")).removesuffix(".class")
        new_owner = str(row.get("new_owner", "")).removesuffix(".class")
        original = unresolved.get(relationship_id)
        if (
            not logical_class_id
            or not old_owner
            or not new_owner
            or original is None
            or original.get("strategy") != "stable_symbol"
        ):
            raise RawSourceInboundCanonicalEvidenceError(
                f"{relationship_id}: invalid inbound frontier row"
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
            raise RawSourceInboundCanonicalEvidenceError(
                f"{relationship_id}: duplicate residual coordinate"
            )
        seen_old.add(old_key)
        seen_new.add(new_key)

        old_topology = _topology(
            row.get("old_global_source_class_topology"),
            label=f"{relationship_id}.old_global_source_class_topology",
        )
        new_topology = _topology(
            row.get("new_global_source_class_topology"),
            label=f"{relationship_id}.new_global_source_class_topology",
        )

        def reject(reason: str, **evidence: Any) -> None:
            reasons[reason] += 1
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

        old_normalized, old_unproven, old_used = _normalize_topology(
            old_topology,
            raw_proofs=old_proofs,
        )
        new_normalized, new_unproven, new_used = _normalize_topology(
            new_topology,
            raw_proofs=new_proofs,
        )
        if old_unproven or new_unproven:
            reject(
                "inbound_canonical_identity_unproven",
                old_unproven_raw_sources=old_unproven,
                new_unproven_raw_sources=new_unproven,
                old_global_source_class_topology=_topology_rows(
                    old_topology
                ),
                new_global_source_class_topology=_topology_rows(
                    new_topology
                ),
            )
            continue

        used = dict(old_used)
        used.update(new_used)
        proofs = [used[token] for token in sorted(used)]
        for proof in proofs:
            strategy = proof.get("strategy")
            token = str(proof.get("identity_token", ""))
            if strategy == (
                "canonical_method_inbound_topology_unique_global"
            ):
                used_method_tokens.add(token)
            elif strategy == (
                "canonical_class_method_inbound_topology_unique_global"
            ):
                used_combined_tokens.add(token)
            else:
                raise RawSourceInboundCanonicalEvidenceError(
                    f"{relationship_id}: unsupported inbound proof strategy"
                )

        if old_normalized != new_normalized:
            reject(
                "normalized_source_topology_mismatch",
                raw_source_identity_proofs=proofs,
                old_normalized_source_topology=_normalized_rows(
                    old_normalized
                ),
                new_normalized_source_topology=_normalized_rows(
                    new_normalized
                ),
            )
            continue

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
                raw_source_identity_proofs=proofs,
            )
            continue

        if old_left[0] != new_left[0] or old_right[0] != new_right[0]:
            reject(
                "canonical_anchor_identity_mismatch",
                raw_source_identity_proofs=proofs,
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
                raw_source_identity_proofs=proofs,
                old_interval_length=len(old_segment),
                new_interval_length=len(new_segment),
            )
            continue
        if old_segment != new_segment:
            reject(
                "declaration_interval_shape_mismatch",
                raw_source_identity_proofs=proofs,
                old_interval_digest=_stable_digest(old_segment),
                new_interval_digest=_stable_digest(new_segment),
            )
            continue

        old_offset = old_pos - old_left[1] - 1
        new_offset = new_pos - new_left[1] - 1
        if old_offset != new_offset:
            reject(
                "target_interval_offset_mismatch",
                raw_source_identity_proofs=proofs,
                old_offset=old_offset,
                new_offset=new_offset,
            )
            continue

        target_signature = old_segment[old_offset]
        old_occurrences = sum(
            1 for value in old_segment
            if value == target_signature
        )
        new_occurrences = sum(
            1 for value in new_segment
            if value == target_signature
        )
        if (
            new_segment[new_offset] != target_signature
            or old_occurrences != 1
            or new_occurrences != 1
        ):
            reject(
                "target_declaration_signature_not_unique",
                raw_source_identity_proofs=proofs,
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
                    "globally_unique_inbound_canonical_identity_and_"
                    "canonical_anchor_declaration_interval_exact"
                ),
                "confidence": "INFERRED_HIGH",
                "score": 0.9993,
                "supports_existing_review": True,
                "raw_source_identity_proofs": proofs,
                "normalized_global_source_class_topology": (
                    _normalized_rows(old_normalized)
                ),
                "left_anchor_member_id": old_left[0],
                "right_anchor_member_id": old_right[0],
                "old_field_ordinal": old_pos,
                "new_field_ordinal": new_pos,
                "interval_offset": old_offset,
                "interval_length": len(old_segment),
                "interval_digest": _stable_digest(old_segment),
                "base_canonical_reference_report_id": previous_report_id,
            }
        )

    candidates.sort(key=lambda item: item["relationship_id"])
    rejected.sort(key=lambda item: item["relationship_id"])
    if len(candidates) + len(rejected) != len(rows):
        raise RawSourceInboundCanonicalEvidenceError(
            "inbound canonical outcome accounting mismatch"
        )

    summary = {
        "input_canonical_reference_identity_unproven": len(rows),
        "candidate_fields": len(candidates),
        "remaining_without_inbound_canonical_proof": len(rejected),
        "global_unique_method_inbound_identities": global_counts[
            "canonical_method_inbound_topology_unique_global"
        ],
        "global_unique_class_method_inbound_identities": global_counts[
            "canonical_class_method_inbound_topology_unique_global"
        ],
        "used_method_inbound_identities": len(used_method_tokens),
        "used_class_method_inbound_identities": len(
            used_combined_tokens
        ),
        **reasons,
    }

    body = {
        "schema_version": 1,
        "kind": (
            "raw_source_inbound_canonical_topology_"
            "declaration_identity_candidates"
        ),
        "canonical": False,
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "member_lineage_digest": member_digest,
        "global_usage_report_id": global_report_id,
        "base_canonical_reference_report_id": previous_report_id,
        "base_canonical_reference_report_digest": _stable_digest(
            previous
        ),
        "base_structural_topology_report_id": structural_report_id,
        "base_structural_topology_report_digest": (
            structural_report_digest
        ),
        "summary": summary,
        "candidates": candidates,
        "rejected": rejected,
        "note": (
            "Research-only continuation of the exact 55-row #848 identity-"
            "unproven frontier. RAW caller identity may be paired only by a "
            "globally unique exact inbound topology from already-canonical "
            "source classes/methods. Method evidence uses canonical source "
            "method IDs plus JVM type/field/invoke operation and a fully "
            "name-collapsed descriptor shape; referenced RAW member names are "
            "never used. The unresolved target field cannot contribute because "
            "this profile concerns references into the RAW caller rather than "
            "the RAW caller's outbound access to the target field. No RAW name "
            "equality, same-path assumption, weighted matcher, package anchor, "
            "or target-field similarity is used. Complete normalized source "
            "topology and the existing two-sided declaration proof remain exact. "
            "canonical=false; no lineage mutation."
        ),
    }
    return {
        "report_id": (
            "RAWINBOUND_"
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
