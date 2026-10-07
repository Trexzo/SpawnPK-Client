from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

from .empty_field_declaration_evidence import (
    EmptyFieldDeclarationEvidenceError,
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
from .lineage import LineageValidationError
from .member_lineage import MemberLineageError
from .raw_source_exact_declaration_evidence import (
    RawSourceExactDeclarationEvidenceError,
    _topology,
    _topology_rows,
    build_raw_source_exact_declaration_evidence,
)


class RawSourceStructuralTopologyEvidenceError(MemberLineageError):
    pass


def _class_paths_by(
    index: dict[str, Any],
    *,
    value_key: str,
    entry_key: bool = False,
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    classes = index.get("classes", {})
    entries = index.get("entries", {})
    if not isinstance(classes, dict) or not isinstance(entries, dict):
        raise RawSourceStructuralTopologyEvidenceError(
            "exact index lacks classes/entries objects"
        )

    for path, cls in classes.items():
        if not isinstance(path, str) or not path.endswith(".class"):
            continue
        if not isinstance(cls, dict):
            raise RawSourceStructuralTopologyEvidenceError(
                f"invalid class index row {path!r}"
            )
        value = (
            entries.get(path, {}).get(value_key)
            if entry_key
            else cls.get(value_key)
        )
        if isinstance(value, str) and value:
            out[value].append(path)
    return dict(out)


def _global_identity_proofs(
    old_index: dict[str, Any],
    new_index: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    old_classes = old_index.get("classes", {})
    new_classes = new_index.get("classes", {})
    old_entries = old_index.get("entries", {})
    new_entries = new_index.get("entries", {})
    if not all(
        isinstance(value, dict)
        for value in (
            old_classes,
            new_classes,
            old_entries,
            new_entries,
        )
    ):
        raise RawSourceStructuralTopologyEvidenceError(
            "exact indexes lack classes/entries objects"
        )

    old_sha = _class_paths_by(
        old_index,
        value_key="sha256",
        entry_key=True,
    )
    new_sha = _class_paths_by(
        new_index,
        value_key="sha256",
        entry_key=True,
    )
    old_struct = _class_paths_by(
        old_index,
        value_key="structural_sha256",
    )
    new_struct = _class_paths_by(
        new_index,
        value_key="structural_sha256",
    )

    old: dict[str, dict[str, Any]] = {}
    new: dict[str, dict[str, Any]] = {}

    def install(
        old_path: str,
        new_path: str,
        *,
        strategy: str,
        proof_value: str,
    ) -> None:
        old_cls = old_classes.get(old_path, {})
        new_cls = new_classes.get(new_path, {})
        old_internal = old_cls.get("internal_name")
        new_internal = new_cls.get("internal_name")
        if (
            not isinstance(old_internal, str)
            or not old_internal
            or not isinstance(new_internal, str)
            or not new_internal
        ):
            raise RawSourceStructuralTopologyEvidenceError(
                "class identity proof lacks internal name"
            )
        if old_path != old_internal + ".class":
            raise RawSourceStructuralTopologyEvidenceError(
                f"old index path/internal-name mismatch: {old_path}"
            )
        if new_path != new_internal + ".class":
            raise RawSourceStructuralTopologyEvidenceError(
                f"new index path/internal-name mismatch: {new_path}"
            )

        token = f"{strategy}:{proof_value}"
        proof = {
            "identity_token": token,
            "strategy": strategy,
            "old_source_class": "RAW:" + old_internal,
            "new_source_class": "RAW:" + new_internal,
            "old_entry": old_path,
            "new_entry": new_path,
            "old_entry_sha256": old_entries.get(old_path, {}).get("sha256"),
            "new_entry_sha256": new_entries.get(new_path, {}).get("sha256"),
            "old_structural_sha256": old_cls.get("structural_sha256"),
            "new_structural_sha256": new_cls.get("structural_sha256"),
        }
        old[old_internal] = proof
        new[new_internal] = proof

    for value in sorted(set(old_sha) & set(new_sha)):
        old_paths = old_sha[value]
        new_paths = new_sha[value]
        if len(old_paths) != 1 or len(new_paths) != 1:
            continue
        install(
            old_paths[0],
            new_paths[0],
            strategy="exact_sha256_unique_global",
            proof_value=value,
        )

    for value in sorted(set(old_struct) & set(new_struct)):
        old_paths = old_struct[value]
        new_paths = new_struct[value]
        if len(old_paths) != 1 or len(new_paths) != 1:
            continue
        old_path, new_path = old_paths[0], new_paths[0]
        old_internal = old_classes.get(old_path, {}).get("internal_name")
        new_internal = new_classes.get(new_path, {}).get("internal_name")
        if (
            isinstance(old_internal, str)
            and old_internal in old
        ) or (
            isinstance(new_internal, str)
            and new_internal in new
        ):
            continue
        install(
            old_path,
            new_path,
            strategy="structural_sha256_unique_global",
            proof_value=value,
        )

    return old, new


def _normalize_topology(
    topology: Counter[tuple[str, str]],
    *,
    raw_proofs: dict[str, dict[str, Any]],
) -> tuple[
    Counter[tuple[str, str]],
    list[str],
    dict[str, dict[str, Any]],
]:
    normalized: Counter[tuple[str, str]] = Counter()
    unproven: list[str] = []
    used: dict[str, dict[str, Any]] = {}

    for (source_class, operation), count in sorted(topology.items()):
        if source_class.startswith("RAW:"):
            internal = source_class[4:]
            proof = raw_proofs.get(internal)
            if proof is None:
                unproven.append(source_class)
                continue
            token = str(proof["identity_token"])
            used[token] = proof
        else:
            token = "CANON:" + source_class
        normalized[(token, operation)] += count

    return normalized, sorted(set(unproven)), used


def _normalized_rows(
    topology: Counter[tuple[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "source_identity": source_identity,
            "operation": operation,
            "count": count,
        }
        for (source_identity, operation), count in sorted(topology.items())
    ]


def build_raw_source_structural_topology_evidence(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
) -> dict[str, Any]:
    base = build_raw_source_exact_declaration_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
    )
    if base.get("canonical") is not False:
        raise RawSourceStructuralTopologyEvidenceError(
            "base RAW-source declaration report unexpectedly canonical"
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
        raise RawSourceStructuralTopologyEvidenceError(
            "base RAW-source declaration report binding is invalid"
        )

    rows = [
        row
        for row in base.get("rejected", [])
        if isinstance(row, dict)
        and row.get("reason") == "raw_source_topology_mismatch"
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
    old_raw_proofs, new_raw_proofs = _global_identity_proofs(
        old_index,
        new_index,
    )

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    reason_counts = {
        "raw_source_identity_unproven": 0,
        "normalized_source_topology_mismatch": 0,
        "missing_two_sided_canonical_anchor": 0,
        "canonical_anchor_identity_mismatch": 0,
        "declaration_interval_length_mismatch": 0,
        "declaration_interval_shape_mismatch": 0,
        "target_interval_offset_mismatch": 0,
        "target_declaration_signature_not_unique": 0,
    }

    exact_tokens: set[str] = set()
    structural_tokens: set[str] = set()
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
            raise RawSourceStructuralTopologyEvidenceError(
                f"base topology row {i} is invalid/duplicate"
            )
        seen_ids.add(relationship_id)

        original = unresolved.get(relationship_id)
        if original is None:
            raise RawSourceStructuralTopologyEvidenceError(
                f"{relationship_id}: missing from exact unresolved frontier"
            )
        if original.get("strategy") != "stable_symbol":
            raise RawSourceStructuralTopologyEvidenceError(
                f"{relationship_id}: unresolved source is not stable_symbol"
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
            raise RawSourceStructuralTopologyEvidenceError(
                f"{relationship_id}: base owner differs from unresolved review"
            )

        old_key = (old_owner, old_coord[0], old_coord[1])
        new_key = (new_owner, new_coord[0], new_coord[1])
        if old_key in seen_old or new_key in seen_new:
            raise RawSourceStructuralTopologyEvidenceError(
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

        raw_sources = sorted(
            {
                source_class
                for source_class, _operation in (
                    set(old_topology) | set(new_topology)
                )
                if source_class.startswith("RAW:")
            }
        )
        if not raw_sources:
            raise RawSourceStructuralTopologyEvidenceError(
                f"{relationship_id}: topology mismatch contains no RAW source"
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
            raw_proofs=old_raw_proofs,
        )
        new_normalized, new_unproven, new_used = _normalize_topology(
            new_topology,
            raw_proofs=new_raw_proofs,
        )
        if old_unproven or new_unproven:
            reject(
                "raw_source_identity_unproven",
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
            if strategy == "exact_sha256_unique_global":
                exact_tokens.add(token)
            elif strategy == "structural_sha256_unique_global":
                structural_tokens.add(token)
            else:
                raise RawSourceStructuralTopologyEvidenceError(
                    f"{relationship_id}: unsupported RAW proof strategy"
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
                old_left=old_left,
                old_right=old_right,
                new_left=new_left,
                new_right=new_right,
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
                    "globally_unique_raw_source_identity_and_"
                    "canonical_anchor_declaration_interval_exact"
                ),
                "confidence": "INFERRED_HIGH",
                "score": 0.999,
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
                "base_raw_source_report_id": base_report_id,
            }
        )

    candidates.sort(key=lambda row: row["relationship_id"])
    rejected.sort(key=lambda row: row["relationship_id"])
    if len(candidates) + len(rejected) != len(rows):
        raise RawSourceStructuralTopologyEvidenceError(
            "RAW-source structural-topology outcome accounting mismatch"
        )

    summary = {
        "input_raw_source_topology_mismatches": len(rows),
        "candidate_fields": len(candidates),
        "remaining_without_structural_topology_proof": len(rejected),
        "unique_exact_sha_source_identities_used": len(exact_tokens),
        "unique_structural_source_identities_used": len(structural_tokens),
        **reason_counts,
    }
    body = {
        "schema_version": 1,
        "kind": "raw_source_structural_topology_declaration_identity_candidates",
        "canonical": False,
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "member_lineage_digest": member_digest,
        "global_usage_report_id": global_report_id,
        "base_raw_source_report_id": base_report_id,
        "base_raw_source_report_digest": _stable_digest(base),
        "summary": summary,
        "candidates": candidates,
        "rejected": rejected,
        "note": (
            "Research-only RAW-source topology normalization. Only #845 rows "
            "rejected at raw_source_topology_mismatch are considered. RAW "
            "source identity is never paired from the target field topology, "
            "names, or weighted matcher evidence. A RAW source may receive a "
            "stable proof token only from a class-entry SHA-256 that is unique "
            "in both exact JAR indexes, or from a name-insensitive structural "
            "SHA-256 that is unique in both exact JAR indexes. After replacing "
            "only those independently proven RAW identities, the complete "
            "source-class/read-write/count topology must match exactly, then "
            "the same two-sided canonical field-anchor and ordered declaration "
            "interval proof is required. canonical=false; no lineage mutation."
        ),
    }
    return {
        "report_id": (
            "RAWSOURCETOPO_"
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
