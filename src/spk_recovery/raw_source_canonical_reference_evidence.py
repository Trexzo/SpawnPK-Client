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
from .member_lineage import MemberLineageError
from .raw_source_exact_declaration_evidence import (
    _topology,
)
from .raw_source_structural_topology_evidence import (
    RawSourceStructuralTopologyEvidenceError,
    _normalize_topology,
    _normalized_rows,
    build_raw_source_structural_topology_evidence,
)


class RawSourceCanonicalReferenceEvidenceError(MemberLineageError):
    pass


def _paired_class_aliases(
    class_lineage: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
) -> tuple[dict[str, str], dict[str, str]]:
    old: dict[str, str] = {}
    new: dict[str, str] = {}

    for record in class_lineage.get("classes", []):
        if not isinstance(record, dict):
            continue
        logical_id = record.get("logical_id")
        if not isinstance(logical_id, str) or not logical_id:
            continue

        old_hits = [
            row
            for row in record.get("lineage", [])
            if isinstance(row, dict)
            and row.get("build_id") == old_build_id
        ]
        new_hits = [
            row
            for row in record.get("lineage", [])
            if isinstance(row, dict)
            and row.get("build_id") == new_build_id
        ]
        if len(old_hits) > 1 or len(new_hits) > 1:
            raise RawSourceCanonicalReferenceEvidenceError(
                f"{logical_id}: duplicate old/new class relation"
            )
        if not old_hits or not new_hits:
            continue

        old_name = old_hits[0].get("internal_name")
        new_name = new_hits[0].get("internal_name")
        if (
            not isinstance(old_name, str)
            or not old_name
            or not isinstance(new_name, str)
            or not new_name
        ):
            raise RawSourceCanonicalReferenceEvidenceError(
                f"{logical_id}: invalid paired class relation"
            )
        if old_name in old or new_name in new:
            raise RawSourceCanonicalReferenceEvidenceError(
                f"{logical_id}: duplicate paired class coordinate"
            )
        old[old_name] = logical_id
        new[new_name] = logical_id

    return old, new


def _paired_member_maps(
    member_lineage: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
) -> tuple[
    dict[tuple[str, str, str, str], str],
    dict[tuple[str, str, str, str], str],
]:
    old: dict[tuple[str, str, str, str], str] = {}
    new: dict[tuple[str, str, str, str], str] = {}

    for record in member_lineage.get("members", []):
        if not isinstance(record, dict):
            continue
        kind = record.get("kind")
        if kind not in {"field", "method"}:
            continue
        member_id = record.get("member_id")
        if not isinstance(member_id, str) or not member_id:
            raise RawSourceCanonicalReferenceEvidenceError(
                "paired member lacks member_id"
            )

        old_hits = [
            row
            for row in record.get("lineage", [])
            if isinstance(row, dict)
            and row.get("build_id") == old_build_id
        ]
        new_hits = [
            row
            for row in record.get("lineage", [])
            if isinstance(row, dict)
            and row.get("build_id") == new_build_id
        ]
        if len(old_hits) > 1 or len(new_hits) > 1:
            raise RawSourceCanonicalReferenceEvidenceError(
                f"{member_id}: duplicate old/new member relation"
            )
        if not old_hits or not new_hits:
            continue

        def key(row: dict[str, Any]) -> tuple[str, str, str, str]:
            owner = row.get("owner_internal_name")
            name = row.get("name")
            descriptor = row.get("descriptor")
            if (
                not isinstance(owner, str)
                or not owner
                or not isinstance(name, str)
                or not name
                or not isinstance(descriptor, str)
                or not descriptor
            ):
                raise RawSourceCanonicalReferenceEvidenceError(
                    f"{member_id}: invalid paired member coordinate"
                )
            return kind, owner, name, descriptor

        old_key = key(old_hits[0])
        new_key = key(new_hits[0])
        if old_key in old or new_key in new:
            raise RawSourceCanonicalReferenceEvidenceError(
                f"{member_id}: duplicate paired member coordinate"
            )
        old[old_key] = member_id
        new[new_key] = member_id

    return old, new


def _reference_profile(
    data: bytes,
    *,
    class_aliases: dict[str, str],
    member_map: dict[tuple[str, str, str, str], str],
) -> dict[str, Any]:
    cp = profile_class_constant_pool_references(data)
    internal_name = cp.get("internal_name")
    if not isinstance(internal_name, str) or not internal_name:
        raise RawSourceCanonicalReferenceEvidenceError(
            "constant-pool profile lacks internal name"
        )

    class_tokens = sorted(
        {
            logical_id
            for ref in cp.get("class_references", [])
            if isinstance(ref, str)
            for logical_id in [class_aliases.get(ref)]
            if isinstance(logical_id, str) and logical_id
        }
    )

    member_counts: Counter[str] = Counter()
    for row in cp.get("member_references", []):
        if not isinstance(row, dict):
            continue
        kind = row.get("kind")
        owner = row.get("owner")
        name = row.get("name")
        descriptor = row.get("descriptor")
        if (
            kind not in {"field", "method"}
            or not isinstance(owner, str)
            or not isinstance(name, str)
            or not isinstance(descriptor, str)
        ):
            continue
        member_id = member_map.get(
            (kind, owner, name, descriptor)
        )
        if member_id is not None:
            member_counts[f"{kind}:{member_id}"] += 1

    member_rows = [
        [token, count]
        for token, count in sorted(member_counts.items())
    ]
    return {
        "internal_name": internal_name,
        "canonical_class_ids": class_tokens,
        "canonical_member_refs": member_rows,
        "canonical_class_count": len(class_tokens),
        "canonical_member_distinct": len(member_rows),
        "canonical_member_observations": sum(member_counts.values()),
    }


def _profile_key(
    profile: dict[str, Any],
    *,
    mode: str,
) -> tuple[Any, ...] | None:
    classes = tuple(profile.get("canonical_class_ids", []))
    members = tuple(
        (str(row[0]), int(row[1]))
        for row in profile.get("canonical_member_refs", [])
        if isinstance(row, list) and len(row) == 2
    )

    if mode == "canonical_member_reference_topology":
        if len(members) < 2:
            return None
        return members

    if mode == "canonical_class_member_reference_topology":
        if len(members) < 1:
            return None
        if len(classes) + len(members) < 3:
            return None
        return classes, members

    raise RawSourceCanonicalReferenceEvidenceError(
        f"unsupported reference profile mode {mode!r}"
    )


def _scan_profiles(
    jar_path: Path,
    *,
    class_aliases: dict[str, str],
    member_map: dict[tuple[str, str, str, str], str],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    try:
        with zipfile.ZipFile(jar_path, "r") as archive:
            for entry in sorted(
                name
                for name in archive.namelist()
                if name.endswith(".class")
            ):
                profile = _reference_profile(
                    archive.read(entry),
                    class_aliases=class_aliases,
                    member_map=member_map,
                )
                internal_name = profile["internal_name"]
                if entry != internal_name + ".class":
                    raise RawSourceCanonicalReferenceEvidenceError(
                        f"class entry/internal-name mismatch: {entry}"
                    )
                if internal_name in out:
                    raise RawSourceCanonicalReferenceEvidenceError(
                        f"duplicate class internal name {internal_name!r}"
                    )
                out[internal_name] = profile
    except (zipfile.BadZipFile, BytecodeProfileError) as exc:
        raise RawSourceCanonicalReferenceEvidenceError(
            f"cannot scan exact JAR reference topology: {jar_path}"
        ) from exc
    return out


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


def _global_reference_identity_proofs(
    old_jar: Path,
    new_jar: Path,
    *,
    old_class_aliases: dict[str, str],
    new_class_aliases: dict[str, str],
    old_member_map: dict[tuple[str, str, str, str], str],
    new_member_map: dict[tuple[str, str, str, str], str],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, int],
]:
    old_profiles = _scan_profiles(
        old_jar,
        class_aliases=old_class_aliases,
        member_map=old_member_map,
    )
    new_profiles = _scan_profiles(
        new_jar,
        class_aliases=new_class_aliases,
        member_map=new_member_map,
    )

    old_proofs: dict[str, dict[str, Any]] = {}
    new_proofs: dict[str, dict[str, Any]] = {}
    strategy_counts = {
        "canonical_member_reference_topology_unique_global": 0,
        "canonical_class_member_reference_topology_unique_global": 0,
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
            "reference_topology": key,
        }
        digest = _stable_digest(material)
        token = f"{strategy}:{digest}"
        proof = {
            "identity_token": token,
            "strategy": strategy,
            "old_source_class": "RAW:" + old_name,
            "new_source_class": "RAW:" + new_name,
            "reference_topology_digest": digest,
            "old_profile": old_profiles[old_name],
            "new_profile": new_profiles[new_name],
        }
        old_proofs[old_name] = proof
        new_proofs[new_name] = proof
        strategy_counts[strategy] += 1

    modes = [
        (
            "canonical_member_reference_topology",
            "canonical_member_reference_topology_unique_global",
        ),
        (
            "canonical_class_member_reference_topology",
            "canonical_class_member_reference_topology_unique_global",
        ),
    ]
    for mode, strategy in modes:
        old_unique = _unique_keys(old_profiles, mode=mode)
        new_unique = _unique_keys(new_profiles, mode=mode)
        for key in sorted(
            set(old_unique) & set(new_unique),
            key=lambda value: repr(value),
        ):
            install(
                old_unique[key],
                new_unique[key],
                strategy=strategy,
                key=key,
            )

    return old_proofs, new_proofs, strategy_counts


def build_raw_source_canonical_reference_evidence(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
) -> dict[str, Any]:
    base = build_raw_source_structural_topology_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
    )
    if base.get("canonical") is not False:
        raise RawSourceCanonicalReferenceEvidenceError(
            "base RAW structural-topology report unexpectedly canonical"
        )

    old_build_id = base.get("old_build_id")
    new_build_id = base.get("new_build_id")
    old_sha = str(base.get("old_sha256", ""))
    new_sha = str(base.get("new_sha256", ""))
    member_digest = base.get("member_lineage_digest")
    global_report_id = base.get("global_usage_report_id")
    base_report_id = base.get("report_id")
    if (
        not isinstance(old_build_id, str)
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
    ):
        raise RawSourceCanonicalReferenceEvidenceError(
            "base RAW structural-topology report binding is invalid"
        )

    rows = [
        row
        for row in base.get("rejected", [])
        if isinstance(row, dict)
        and row.get("reason") == "raw_source_identity_unproven"
    ]

    old_class_aliases, new_class_aliases = _paired_class_aliases(
        class_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_member_map, new_member_map = _paired_member_maps(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_proofs, new_proofs, global_proof_counts = (
        _global_reference_identity_proofs(
            old_jar,
            new_jar,
            old_class_aliases=old_class_aliases,
            new_class_aliases=new_class_aliases,
            old_member_map=old_member_map,
            new_member_map=new_member_map,
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
    old_aliases = _aliases(class_lineage, old_build_id)
    new_aliases = _aliases(class_lineage, new_build_id)

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    reason_counts = {
        "canonical_reference_identity_unproven": 0,
        "normalized_source_topology_mismatch": 0,
        "missing_two_sided_canonical_anchor": 0,
        "canonical_anchor_identity_mismatch": 0,
        "declaration_interval_length_mismatch": 0,
        "declaration_interval_shape_mismatch": 0,
        "target_interval_offset_mismatch": 0,
        "target_declaration_signature_not_unique": 0,
    }
    used_member_tokens: set[str] = set()
    used_combined_tokens: set[str] = set()
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
            raise RawSourceCanonicalReferenceEvidenceError(
                f"base canonical-reference row {i} is invalid/duplicate"
            )
        seen_ids.add(relationship_id)

        original = unresolved.get(relationship_id)
        if original is None or original.get("strategy") != "stable_symbol":
            raise RawSourceCanonicalReferenceEvidenceError(
                f"{relationship_id}: missing stable-symbol unresolved source"
            )

        old_coord = _coord(
            original.get("old"),
            label=f"{relationship_id}.old",
        )
        new_coord = _coord(
            original.get("new"),
            label=f"{relationship_id}.new",
        )
        if (
            old_owner
            != str(original.get("old_owner", "")).removesuffix(".class")
            or new_owner
            != str(original.get("new_owner", "")).removesuffix(".class")
        ):
            raise RawSourceCanonicalReferenceEvidenceError(
                f"{relationship_id}: base owner differs from unresolved review"
            )

        old_key = (old_owner, old_coord[0], old_coord[1])
        new_key = (new_owner, new_coord[0], new_coord[1])
        if old_key in seen_old or new_key in seen_new:
            raise RawSourceCanonicalReferenceEvidenceError(
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
                "canonical_reference_identity_unproven",
                old_unproven_raw_sources=old_unproven,
                new_unproven_raw_sources=new_unproven,
            )
            continue

        used = dict(old_used)
        used.update(new_used)
        proofs = [used[token] for token in sorted(used)]
        for proof in proofs:
            strategy = proof.get("strategy")
            token = str(proof.get("identity_token", ""))
            if strategy == (
                "canonical_member_reference_topology_unique_global"
            ):
                used_member_tokens.add(token)
            elif strategy == (
                "canonical_class_member_reference_topology_unique_global"
            ):
                used_combined_tokens.add(token)
            else:
                raise RawSourceCanonicalReferenceEvidenceError(
                    f"{relationship_id}: unsupported canonical-reference proof"
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
        old_index_pos = _field_index(
            old_fields,
            old_coord,
            label=f"{relationship_id}.old",
        )
        new_index_pos = _field_index(
            new_fields,
            new_coord,
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

        old_offset = old_index_pos - old_left[1] - 1
        new_offset = new_index_pos - new_left[1] - 1
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
                    "globally_unique_canonical_reference_identity_and_"
                    "canonical_anchor_declaration_interval_exact"
                ),
                "confidence": "INFERRED_HIGH",
                "score": 0.9992,
                "supports_existing_review": True,
                "raw_source_identity_proofs": proofs,
                "normalized_global_source_class_topology": (
                    _normalized_rows(old_normalized)
                ),
                "left_anchor_member_id": old_left[0],
                "right_anchor_member_id": old_right[0],
                "old_field_ordinal": old_index_pos,
                "new_field_ordinal": new_index_pos,
                "interval_offset": old_offset,
                "interval_length": len(old_segment),
                "interval_digest": _stable_digest(old_segment),
                "base_structural_topology_report_id": base_report_id,
            }
        )

    candidates.sort(key=lambda row: row["relationship_id"])
    rejected.sort(key=lambda row: row["relationship_id"])
    if len(candidates) + len(rejected) != len(rows):
        raise RawSourceCanonicalReferenceEvidenceError(
            "canonical-reference outcome accounting mismatch"
        )

    summary = {
        "input_raw_source_identity_unproven": len(rows),
        "candidate_fields": len(candidates),
        "remaining_without_canonical_reference_proof": len(rejected),
        "global_unique_member_reference_identities": (
            global_proof_counts[
                "canonical_member_reference_topology_unique_global"
            ]
        ),
        "global_unique_class_member_reference_identities": (
            global_proof_counts[
                "canonical_class_member_reference_topology_unique_global"
            ]
        ),
        "used_member_reference_identities": len(used_member_tokens),
        "used_class_member_reference_identities": len(
            used_combined_tokens
        ),
        **reason_counts,
    }

    body = {
        "schema_version": 1,
        "kind": (
            "raw_source_canonical_reference_topology_"
            "declaration_identity_candidates"
        ),
        "canonical": False,
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "member_lineage_digest": member_digest,
        "global_usage_report_id": global_report_id,
        "base_structural_topology_report_id": base_report_id,
        "base_structural_topology_report_digest": _stable_digest(base),
        "summary": summary,
        "candidates": candidates,
        "rejected": rejected,
        "note": (
            "Research-only RAW source identity recovery after exact/structural "
            "class identity was exhausted. A RAW source class can be paired "
            "only by a globally unique exact topology of already-canonical "
            "class/member references. Member references contribute only when "
            "the member is canonical in both builds, so unresolved target "
            "fields cannot participate in source-class identity. No RAW class "
            "name equality, weighted matcher score, target-field access "
            "similarity, or field-specific source pairing is used. Once RAW "
            "identity is independently proven, complete source operation/count "
            "topology and the existing two-sided canonical declaration proof "
            "must still match exactly. canonical=false; no lineage mutation."
        ),
    }

    return {
        "report_id": (
            "RAWREFTOPO_"
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
