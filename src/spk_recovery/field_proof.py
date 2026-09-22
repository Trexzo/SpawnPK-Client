from __future__ import annotations

from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from .bytecode_profile import profile_jar_class
from .indexer import sha256_file
from .lineage import LineageValidationError, validate_lineage
from .member_lineage import (
    MemberLineageError,
    validate_member_lineage,
)


class FieldProofError(MemberLineageError):
    pass


def _descriptor_identity(
    descriptor: str,
    aliases: dict[str, str],
) -> str:
    out: list[str] = []
    i = 0
    while i < len(descriptor):
        ch = descriptor[i]
        if ch != "L":
            out.append(ch)
            i += 1
            continue
        semi = descriptor.find(";", i)
        if semi < 0:
            return descriptor
        internal = descriptor[i + 1 : semi]
        if internal in aliases:
            token = "@" + aliases[internal]
        elif internal.startswith("rs/"):
            token = "rs/?"
        else:
            token = internal
        out.append("L" + token + ";")
        i = semi + 1
    return "".join(out)


def _build(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, Any]:
    hits = [
        row
        for row in class_lineage.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(hits) != 1:
        raise FieldProofError(
            f"expected one canonical build {build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _class_entries(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, tuple[str, dict[str, Any]]]:
    out: dict[str, tuple[str, dict[str, Any]]] = {}
    for record in class_lineage.get("classes", []):
        logical_id = str(record.get("logical_id"))
        hits = [
            entry
            for entry in record.get("lineage", [])
            if entry.get("build_id") == build_id
        ]
        if len(hits) > 1:
            raise FieldProofError(
                f"{logical_id} has duplicate {build_id!r} class entries"
            )
        if not hits:
            continue
        entry = hits[0]
        internal = entry.get("internal_name")
        if not isinstance(internal, str) or not internal:
            raise FieldProofError(
                f"{logical_id}.{build_id}: invalid internal class name"
            )
        out[logical_id] = (internal, entry)
    return out


def _aliases(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, str]:
    return {
        internal: logical_id
        for logical_id, (internal, _entry) in _class_entries(
            class_lineage,
            build_id,
        ).items()
    }


def _canonical_methods(
    member_lineage: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
) -> tuple[
    dict[str, dict[tuple[str, str], str]],
    dict[str, dict[tuple[str, str], str]],
]:
    old: dict[str, dict[tuple[str, str], str]] = defaultdict(dict)
    new: dict[str, dict[tuple[str, str], str]] = defaultdict(dict)

    for record in member_lineage.get("members", []):
        if record.get("kind") != "method":
            continue
        member_id = str(record.get("member_id"))
        old_hits = [
            entry
            for entry in record.get("lineage", [])
            if entry.get("build_id") == old_build_id
        ]
        new_hits = [
            entry
            for entry in record.get("lineage", [])
            if entry.get("build_id") == new_build_id
        ]
        if len(old_hits) > 1 or len(new_hits) > 1:
            raise FieldProofError(
                f"{member_id}: duplicate old/new method lineage relation"
            )
        if not old_hits or not new_hits:
            continue

        old_entry, new_entry = old_hits[0], new_hits[0]
        old_owner = str(old_entry.get("owner_internal_name"))
        new_owner = str(new_entry.get("owner_internal_name"))
        old_key = (
            str(old_entry.get("name")),
            str(old_entry.get("descriptor")),
        )
        new_key = (
            str(new_entry.get("name")),
            str(new_entry.get("descriptor")),
        )
        if old_key in old[old_owner]:
            raise FieldProofError(
                f"duplicate canonical old method coordinate {old_owner}.{old_key}"
            )
        if new_key in new[new_owner]:
            raise FieldProofError(
                f"duplicate canonical new method coordinate {new_owner}.{new_key}"
            )
        old[old_owner][old_key] = member_id
        new[new_owner][new_key] = member_id

    return dict(old), dict(new)


def _field_signatures(
    profile: dict[str, Any],
    methods: dict[tuple[str, str], str],
    aliases: dict[str, str],
) -> dict[
    tuple[int, str, tuple[tuple[str, str, int, int], ...]],
    list[tuple[str, str]],
]:
    owner = profile.get("internal_name")
    if not isinstance(owner, str) or not owner:
        raise FieldProofError("profile missing internal_name")

    declared: dict[tuple[str, str], dict[str, Any]] = {
        (
            str(field.get("name")),
            str(field.get("descriptor")),
        ): field
        for field in profile.get("fields", [])
        if isinstance(field, dict)
    }

    observations: dict[
        tuple[str, str],
        Counter[tuple[str, str, int, int]],
    ] = defaultdict(Counter)

    for method in profile.get("methods", []):
        if not isinstance(method, dict):
            continue
        method_id = methods.get(
            (
                str(method.get("name")),
                str(method.get("descriptor")),
            )
        )
        if method_id is None:
            continue

        own_ordinal = 0
        for access in method.get("field_accesses", []):
            if not isinstance(access, dict):
                continue
            if access.get("owner") != owner:
                continue
            coord = (
                str(access.get("name")),
                str(access.get("descriptor")),
            )
            if coord not in declared:
                continue
            offset = access.get("offset")
            if isinstance(offset, int):
                observations[coord][
                    (
                        method_id,
                        str(access.get("operation")),
                        own_ordinal,
                        offset,
                    )
                ] += 1
            own_ordinal += 1

    groups: dict[
        tuple[int, str, tuple[tuple[str, str, int, int], ...]],
        list[tuple[str, str]],
    ] = defaultdict(list)

    for coord, field in declared.items():
        context = observations.get(coord)
        if not context:
            continue
        signature = (
            int(field.get("access", 0)),
            _descriptor_identity(
                str(field.get("descriptor", "")),
                aliases,
            ),
            tuple(
                sorted(
                    (
                        method_id,
                        operation,
                        ordinal,
                        offset,
                    )
                    for (
                        method_id,
                        operation,
                        ordinal,
                        offset,
                    ), count in context.items()
                    for _ in range(count)
                )
            ),
        )
        groups[signature].append(coord)
    return dict(groups)


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_field_position_proof(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    *,
    old_build_id: str,
    new_build_id: str,
    min_observations: int = 2,
) -> dict[str, Any]:
    """Re-prove field identities from exact JAR bytecode and canonical methods."""
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )
    if min_observations < 2:
        raise FieldProofError(
            "min_observations must be >= 2 for canonical field proof"
        )
    if old_build_id == new_build_id:
        raise FieldProofError("old/new build IDs must differ")

    old_build = _build(class_lineage, old_build_id)
    new_build = _build(class_lineage, new_build_id)
    old_sha = sha256_file(old_jar.resolve())
    new_sha = sha256_file(new_jar.resolve())

    if old_sha.lower() != str(old_index.get("sha256", "")).lower():
        raise FieldProofError("old JAR SHA-256 does not match old index")
    if new_sha.lower() != str(new_index.get("sha256", "")).lower():
        raise FieldProofError("new JAR SHA-256 does not match new index")
    if old_sha.lower() != str(old_build.get("sha256", "")).lower():
        raise FieldProofError(
            "old JAR SHA-256 does not match canonical old build"
        )
    if new_sha.lower() != str(new_build.get("sha256", "")).lower():
        raise FieldProofError(
            "new JAR SHA-256 does not match canonical new build"
        )

    old_classes = _class_entries(class_lineage, old_build_id)
    new_classes = _class_entries(class_lineage, new_build_id)
    old_aliases = _aliases(class_lineage, old_build_id)
    new_aliases = _aliases(class_lineage, new_build_id)
    old_methods, new_methods = _canonical_methods(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )

    proofs: list[dict[str, Any]] = []
    audited_classes = 0

    for logical_id in sorted(set(old_classes) & set(new_classes)):
        old_owner, _old_entry = old_classes[logical_id]
        new_owner, _new_entry = new_classes[logical_id]
        old_method_map = old_methods.get(old_owner, {})
        new_method_map = new_methods.get(new_owner, {})
        common_method_ids = set(old_method_map.values()) & set(
            new_method_map.values()
        )
        if not common_method_ids:
            continue

        old_profile = profile_jar_class(
            old_jar,
            old_owner + ".class",
        )
        new_profile = profile_jar_class(
            new_jar,
            new_owner + ".class",
        )
        old_groups = _field_signatures(
            old_profile,
            old_method_map,
            old_aliases,
        )
        new_groups = _field_signatures(
            new_profile,
            new_method_map,
            new_aliases,
        )
        audited_classes += 1

        for signature in set(old_groups) & set(new_groups):
            old_rows = old_groups[signature]
            new_rows = new_groups[signature]
            if len(old_rows) != 1 or len(new_rows) != 1:
                continue
            observations = len(signature[2])
            if observations < min_observations:
                continue
            old_coord = old_rows[0]
            new_coord = new_rows[0]
            evidence = [
                {
                    "method_id": method_id,
                    "operation": operation,
                    "own_field_ordinal": ordinal,
                    "bytecode_offset": offset,
                }
                for method_id, operation, ordinal, offset in signature[2]
            ]
            material = {
                "old_sha256": old_sha,
                "new_sha256": new_sha,
                "logical_class_id": logical_id,
                "old_owner": old_owner,
                "new_owner": new_owner,
                "old": {
                    "name": old_coord[0],
                    "descriptor": old_coord[1],
                },
                "new": {
                    "name": new_coord[0],
                    "descriptor": new_coord[1],
                },
                "evidence": evidence,
            }
            proofs.append(
                {
                    **material,
                    "proof_id": (
                        "FIELDPROOF_"
                        + _stable_digest(material)[:20].upper()
                    ),
                    "observations": observations,
                    "confidence": 0.9995,
                }
            )

    proofs.sort(
        key=lambda row: (
            row["logical_class_id"],
            row["old_owner"],
            row["old"]["name"],
            row["old"]["descriptor"],
            row["new"]["name"],
            row["new"]["descriptor"],
        )
    )
    report_material = {
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "min_observations": min_observations,
        "proofs": proofs,
    }
    return {
        "schema_version": 1,
        "kind": "jar_bound_field_position_proof",
        "canonical": False,
        "report_id": (
            "FIELDPROOFSET_"
            + _stable_digest(report_material)[:20].upper()
        ),
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "min_observations": min_observations,
        "audited_classes": audited_classes,
        "proof_count": len(proofs),
        "proofs": proofs,
    }


def _old_field_records(
    member_lineage: dict[str, Any],
    build_id: str,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    out: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in member_lineage.get("members", []):
        if record.get("kind") != "field":
            continue
        for entry in record.get("lineage", []):
            if entry.get("build_id") != build_id:
                continue
            key = (
                str(entry.get("owner_internal_name")),
                str(entry.get("name")),
                str(entry.get("descriptor")),
            )
            if key in out:
                raise FieldProofError(
                    f"duplicate canonical old field coordinate {key!r}"
                )
            out[key] = record
    return out


def _target_field(
    index: dict[str, Any],
    owner: str,
    name: str,
    descriptor: str,
) -> dict[str, Any]:
    cls = index.get("classes", {}).get(owner + ".class")
    if not isinstance(cls, dict):
        raise FieldProofError(f"new index missing owner {owner!r}")
    hits = [
        row
        for row in cls.get("fields", [])
        if row.get("name") == name
        and row.get("descriptor") == descriptor
    ]
    if len(hits) != 1:
        raise FieldProofError(
            f"expected one target field {owner}.{name}:{descriptor}, "
            f"found {len(hits)}"
        )
    return hits[0]


def _unresolved_matches_proof(
    item: dict[str, Any],
    proof: dict[str, Any],
    new_build_id: str,
) -> bool:
    if item.get("new_build_id") != new_build_id:
        return False
    if item.get("kind") != "member_identity_review":
        return False
    if item.get("member_kind") != "field":
        return False
    candidate = item.get("candidate")
    if not isinstance(candidate, dict):
        return False
    old = candidate.get("old", {})
    new = candidate.get("new", {})
    if not isinstance(old, dict) or not isinstance(new, dict):
        return False
    return (
        str(candidate.get("old_owner", "")).removesuffix(".class")
        == proof["old_owner"]
        and str(candidate.get("new_owner", "")).removesuffix(".class")
        == proof["new_owner"]
        and old.get("name") == proof["old"]["name"]
        and old.get("descriptor") == proof["old"]["descriptor"]
        and new.get("name") == proof["new"]["name"]
        and new.get("descriptor") == proof["new"]["descriptor"]
    )


def apply_field_position_proof(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    new_index: dict[str, Any],
    proof_report: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Apply only already JAR-bound exact-position proofs to canonical fields."""
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )
    if (
        proof_report.get("schema_version") != 1
        or proof_report.get("kind")
        != "jar_bound_field_position_proof"
        or proof_report.get("canonical") is not False
    ):
        raise FieldProofError("unsupported field proof report")
    if (
        proof_report.get("old_build_id") != old_build_id
        or proof_report.get("new_build_id") != new_build_id
    ):
        raise FieldProofError("field proof build IDs do not match request")
    if str(proof_report.get("new_sha256", "")).lower() != str(
        new_index.get("sha256", "")
    ).lower():
        raise FieldProofError(
            "field proof new SHA-256 does not match exact new index"
        )

    old_classes = _class_entries(class_lineage, old_build_id)
    new_classes = _class_entries(class_lineage, new_build_id)
    old_fields = _old_field_records(member_lineage, old_build_id)
    out = copy.deepcopy(member_lineage)
    by_id = {
        row["member_id"]: row
        for row in out.get("members", [])
    }

    target_owner: dict[tuple[str, str, str], str] = {}
    for record in out.get("members", []):
        for entry in record.get("lineage", []):
            if entry.get("build_id") != new_build_id:
                continue
            key = (
                str(entry.get("owner_internal_name")),
                str(entry.get("name")),
                str(entry.get("descriptor")),
            )
            target_owner[key] = record["member_id"]

    applied = 0
    already_present = 0
    unresolved_removed = 0

    for proof in proof_report.get("proofs", []):
        logical_id = proof.get("logical_class_id")
        if logical_id not in old_classes or logical_id not in new_classes:
            raise FieldProofError(
                f"proof references non-canonical class {logical_id!r}"
            )
        if old_classes[logical_id][0] != proof.get("old_owner"):
            raise FieldProofError("proof old owner does not match class lineage")
        if new_classes[logical_id][0] != proof.get("new_owner"):
            raise FieldProofError("proof new owner does not match class lineage")

        old_key = (
            proof["old_owner"],
            proof["old"]["name"],
            proof["old"]["descriptor"],
        )
        record = old_fields.get(old_key)
        if record is None:
            raise FieldProofError(
                f"proof old field is not canonical: {old_key!r}"
            )
        if record.get("owner_logical_id") != logical_id:
            raise FieldProofError(
                "proof field canonical owner logical ID mismatch"
            )

        target = _target_field(
            new_index,
            proof["new_owner"],
            proof["new"]["name"],
            proof["new"]["descriptor"],
        )
        target_key = (
            proof["new_owner"],
            proof["new"]["name"],
            proof["new"]["descriptor"],
        )
        member_id = record["member_id"]
        occupied = target_owner.get(target_key)
        if occupied is not None and occupied != member_id:
            raise FieldProofError(
                f"proven target field already belongs to {occupied}"
            )

        target_record = by_id[member_id]
        existing = [
            entry
            for entry in target_record.get("lineage", [])
            if entry.get("build_id") == new_build_id
        ]
        if len(existing) > 1:
            raise FieldProofError(
                f"{member_id} has duplicate target-build relations"
            )
        if existing:
            entry = existing[0]
            if (
                entry.get("owner_internal_name") != target_key[0]
                or entry.get("name") != target_key[1]
                or entry.get("descriptor") != target_key[2]
            ):
                raise FieldProofError(
                    f"{member_id} existing target relation contradicts "
                    f"JAR-bound proof {proof['proof_id']}"
                )
            already_present += 1
        else:
            target_record["lineage"].append(
                {
                    "build_id": new_build_id,
                    "owner_internal_name": target_key[0],
                    "name": target_key[1],
                    "descriptor": target_key[2],
                    "access": int(target.get("access", 0)),
                    "relation": "STRUCTURAL",
                    "confidence": float(proof["confidence"]),
                    "provenance": [
                        {
                            "authority": "CROSS_BUILD",
                            "source": proof["proof_id"],
                            "note": (
                                "JAR-bound unique exact matched-method "
                                "field-access-position proof."
                            ),
                        }
                    ],
                }
            )
            target_owner[target_key] = member_id
            applied += 1

        before = len(out.get("unresolved", []))
        out["unresolved"] = [
            item
            for item in out.get("unresolved", [])
            if not (
                isinstance(item, dict)
                and _unresolved_matches_proof(
                    item,
                    proof,
                    new_build_id,
                )
            )
        ]
        unresolved_removed += before - len(out["unresolved"])

    validate_member_lineage(out, class_lineage=class_lineage)
    return out, {
        "proofs": int(proof_report.get("proof_count", 0)),
        "applied_fields": applied,
        "already_present": already_present,
        "unresolved_removed": unresolved_removed,
        "remaining_unresolved": len(out.get("unresolved", [])),
    }


def prove_and_apply_fields(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    *,
    old_build_id: str,
    new_build_id: str,
    min_observations: int = 2,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    proof = build_field_position_proof(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
        min_observations=min_observations,
    )
    out, summary = apply_field_position_proof(
        class_lineage,
        member_lineage,
        new_index,
        proof,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    return out, proof, summary


def write_json(doc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            doc,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
