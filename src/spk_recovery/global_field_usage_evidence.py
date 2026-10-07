from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import zipfile

from .bytecode_profile import (
    BytecodeProfileError,
    profile_class_constant_pool_references,
    profile_class_field_accesses,
)
from .indexer import sha256_file
from .lineage import (
    LineageValidationError,
    load_lineage,
    validate_lineage,
)
from .member_identity import _descriptor_identity_shape
from .member_lineage import (
    MemberLineageError,
    load_member_lineage,
    validate_member_lineage,
)


class GlobalFieldUsageEvidenceError(MemberLineageError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GlobalFieldUsageEvidenceError(
            f"JSON root must be object: {path}"
        )
    return value


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
        raise GlobalFieldUsageEvidenceError(
            f"expected one canonical build {build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _aliases(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for record in class_lineage.get("classes", []):
        logical_id = record.get("logical_id")
        if not isinstance(logical_id, str) or not logical_id:
            continue
        hits = [
            row
            for row in record.get("lineage", [])
            if row.get("build_id") == build_id
        ]
        if len(hits) > 1:
            raise GlobalFieldUsageEvidenceError(
                f"{logical_id}: duplicate class relation for {build_id!r}"
            )
        if not hits:
            continue
        internal = hits[0].get("internal_name")
        if not isinstance(internal, str) or not internal:
            raise GlobalFieldUsageEvidenceError(
                f"{logical_id}: invalid class owner for {build_id!r}"
            )
        if internal in out:
            raise GlobalFieldUsageEvidenceError(
                f"duplicate canonical class owner {internal!r}"
            )
        out[internal] = logical_id
    return out


def _paired_method_maps(
    member_lineage: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
) -> tuple[
    dict[str, dict[tuple[str, str], str]],
    dict[str, dict[tuple[str, str], str]],
    int,
]:
    old: dict[str, dict[tuple[str, str], str]] = defaultdict(dict)
    new: dict[str, dict[tuple[str, str], str]] = defaultdict(dict)
    paired_ids: set[str] = set()

    for record in member_lineage.get("members", []):
        if record.get("kind") != "method":
            continue
        member_id = record.get("member_id")
        if not isinstance(member_id, str) or not member_id:
            raise GlobalFieldUsageEvidenceError(
                "canonical method record lacks member_id"
            )
        old_hits = [
            row
            for row in record.get("lineage", [])
            if row.get("build_id") == old_build_id
        ]
        new_hits = [
            row
            for row in record.get("lineage", [])
            if row.get("build_id") == new_build_id
        ]
        if len(old_hits) > 1 or len(new_hits) > 1:
            raise GlobalFieldUsageEvidenceError(
                f"{member_id}: duplicate old/new method relation"
            )
        if not old_hits or not new_hits:
            continue

        old_entry, new_entry = old_hits[0], new_hits[0]
        old_owner = old_entry.get("owner_internal_name")
        new_owner = new_entry.get("owner_internal_name")
        if (
            not isinstance(old_owner, str)
            or not old_owner
            or not isinstance(new_owner, str)
            or not new_owner
        ):
            raise GlobalFieldUsageEvidenceError(
                f"{member_id}: invalid method owner"
            )

        old_key = (
            str(old_entry.get("name", "")),
            str(old_entry.get("descriptor", "")),
        )
        new_key = (
            str(new_entry.get("name", "")),
            str(new_entry.get("descriptor", "")),
        )
        if not all(old_key) or not all(new_key):
            raise GlobalFieldUsageEvidenceError(
                f"{member_id}: invalid method coordinate"
            )
        if old_key in old[old_owner]:
            raise GlobalFieldUsageEvidenceError(
                f"duplicate canonical old method coordinate "
                f"{old_owner}.{old_key}"
            )
        if new_key in new[new_owner]:
            raise GlobalFieldUsageEvidenceError(
                f"duplicate canonical new method coordinate "
                f"{new_owner}.{new_key}"
            )
        old[old_owner][old_key] = member_id
        new[new_owner][new_key] = member_id
        paired_ids.add(member_id)

    return dict(old), dict(new), len(paired_ids)


def _owner(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise GlobalFieldUsageEvidenceError(
            f"{label} must be a non-empty owner string"
        )
    return value[:-6] if value.endswith(".class") else value


def _coord(
    value: Any,
    *,
    label: str,
) -> tuple[str, str, int | None]:
    if not isinstance(value, dict):
        raise GlobalFieldUsageEvidenceError(
            f"{label} must be an object"
        )
    name = value.get("name")
    descriptor = value.get("descriptor")
    access = value.get("access")
    if not isinstance(name, str) or not name:
        raise GlobalFieldUsageEvidenceError(
            f"{label}.name must be non-empty"
        )
    if not isinstance(descriptor, str) or not descriptor:
        raise GlobalFieldUsageEvidenceError(
            f"{label}.descriptor must be non-empty"
        )
    if access is not None and (
        not isinstance(access, int) or isinstance(access, bool)
    ):
        raise GlobalFieldUsageEvidenceError(
            f"{label}.access must be an integer when present"
        )
    return name, descriptor, access


def _exact_field(
    index: dict[str, Any],
    *,
    owner: str,
    name: str,
    descriptor: str,
) -> dict[str, Any]:
    cls = index.get("classes", {}).get(owner + ".class")
    if not isinstance(cls, dict):
        raise GlobalFieldUsageEvidenceError(
            f"exact index missing owner {owner!r}"
        )
    hits = [
        row
        for row in cls.get("fields", [])
        if row.get("name") == name
        and row.get("descriptor") == descriptor
    ]
    if len(hits) != 1:
        raise GlobalFieldUsageEvidenceError(
            f"expected one exact field {owner}.{name}:{descriptor}, "
            f"found {len(hits)}"
        )
    return hits[0]


def _stable_reviews(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
    descriptor_identity_rejections: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    old_aliases = _aliases(class_lineage, old_build_id)
    new_aliases = _aliases(class_lineage, new_build_id)
    old_owners = old_aliases
    new_owners = new_aliases
    seen_relationships: set[str] = set()
    seen_old_coords: set[tuple[str, str, str]] = set()
    seen_new_coords: set[tuple[str, str, str]] = set()
    reviews: list[dict[str, Any]] = []

    for item in member_lineage.get("unresolved", []):
        if not isinstance(item, dict):
            continue
        if (
            item.get("kind") != "member_identity_review"
            or item.get("member_kind") != "field"
            or item.get("source") != "member_identity_candidates"
            or item.get("old_build_id") != old_build_id
            or item.get("new_build_id") != new_build_id
        ):
            continue
        candidate = item.get("candidate")
        if not isinstance(candidate, dict):
            continue
        if candidate.get("strategy") != "stable_symbol":
            continue

        relationship_id = candidate.get("relationship_id")
        if not isinstance(relationship_id, str) or not relationship_id:
            raise GlobalFieldUsageEvidenceError(
                "stable-symbol review lacks relationship_id"
            )
        if relationship_id in seen_relationships:
            raise GlobalFieldUsageEvidenceError(
                f"duplicate relationship_id {relationship_id!r}"
            )
        seen_relationships.add(relationship_id)

        old_owner = _owner(
            candidate.get("old_owner"),
            label=f"{relationship_id}.old_owner",
        )
        new_owner = _owner(
            candidate.get("new_owner"),
            label=f"{relationship_id}.new_owner",
        )
        old_logical = old_owners.get(old_owner)
        new_logical = new_owners.get(new_owner)
        if old_logical is None or new_logical is None:
            raise GlobalFieldUsageEvidenceError(
                f"{relationship_id}: owner is not canonical in both builds"
            )
        if old_logical != new_logical:
            raise GlobalFieldUsageEvidenceError(
                f"{relationship_id}: owner logical class differs"
            )

        old_name, old_desc, old_access = _coord(
            candidate.get("old"),
            label=f"{relationship_id}.old",
        )
        new_name, new_desc, new_access = _coord(
            candidate.get("new"),
            label=f"{relationship_id}.new",
        )
        old_decl = _exact_field(
            old_index,
            owner=old_owner,
            name=old_name,
            descriptor=old_desc,
        )
        new_decl = _exact_field(
            new_index,
            owner=new_owner,
            name=new_name,
            descriptor=new_desc,
        )
        old_decl_access = int(old_decl.get("access", 0))
        new_decl_access = int(new_decl.get("access", 0))
        if old_access is not None and old_access != old_decl_access:
            raise GlobalFieldUsageEvidenceError(
                f"{relationship_id}: old access disagrees with exact index"
            )
        if new_access is not None and new_access != new_decl_access:
            raise GlobalFieldUsageEvidenceError(
                f"{relationship_id}: new access disagrees with exact index"
            )
        if old_name != new_name:
            raise GlobalFieldUsageEvidenceError(
                f"{relationship_id}: stable_symbol field name changed"
            )
        if old_decl_access != new_decl_access:
            raise GlobalFieldUsageEvidenceError(
                f"{relationship_id}: stable_symbol field access changed"
            )
        old_shape = _descriptor_identity_shape(old_desc, old_aliases)
        new_shape = _descriptor_identity_shape(new_desc, new_aliases)
        if old_shape != new_shape:
            if descriptor_identity_rejections is None:
                raise GlobalFieldUsageEvidenceError(
                    f"{relationship_id}: stable_symbol descriptor identity changed"
                )
            descriptor_identity_rejections.append(
                {
                    "relationship_id": relationship_id,
                    "old_owner": old_owner,
                    "new_owner": new_owner,
                    "old_descriptor": old_desc,
                    "new_descriptor": new_desc,
                    "old_descriptor_identity": old_shape,
                    "new_descriptor_identity": new_shape,
                    "reason": "canonical_descriptor_identity_changed",
                }
            )
            continue

        old_key = (old_owner, old_name, old_desc)
        new_key = (new_owner, new_name, new_desc)
        if old_key in seen_old_coords:
            raise GlobalFieldUsageEvidenceError(
                f"{relationship_id}: duplicate old review coordinate {old_key!r}"
            )
        if new_key in seen_new_coords:
            raise GlobalFieldUsageEvidenceError(
                f"{relationship_id}: duplicate new review coordinate {new_key!r}"
            )
        seen_old_coords.add(old_key)
        seen_new_coords.add(new_key)

        reviews.append(
            {
                "relationship_id": relationship_id,
                "logical_class_id": old_logical,
                "old_owner": old_owner,
                "new_owner": new_owner,
                "old": {
                    "name": old_name,
                    "descriptor": old_desc,
                    "access": old_decl_access,
                },
                "new": {
                    "name": new_name,
                    "descriptor": new_desc,
                    "access": new_decl_access,
                },
            }
        )

    reviews.sort(key=lambda row: row["relationship_id"])
    return reviews


def _target_key(
    owner: str,
    coord: dict[str, Any],
) -> tuple[str, str, str]:
    return (
        owner,
        str(coord["name"]),
        str(coord["descriptor"]),
    )


def _scan_usage(
    jar_path: Path,
    method_maps: dict[str, dict[tuple[str, str], str]],
    targets: set[tuple[str, str, str]],
) -> tuple[
    dict[
        tuple[str, str, str],
        Counter[tuple[str, str]],
    ],
    dict[str, int],
]:
    usage: dict[
        tuple[str, str, str],
        Counter[tuple[str, str]],
    ] = defaultdict(Counter)
    source_classes_scanned = 0
    source_classes_relevant = 0
    canonical_methods_scanned = 0
    observations = 0

    try:
        with zipfile.ZipFile(jar_path, "r") as archive:
            names = set(archive.namelist())
            for owner in sorted(method_maps):
                entry = owner + ".class"
                if entry not in names:
                    raise GlobalFieldUsageEvidenceError(
                        f"canonical method owner missing from JAR: {entry}"
                    )
                data = archive.read(entry)
                source_classes_scanned += 1

                cp_profile = profile_class_constant_pool_references(data)
                if cp_profile.get("internal_name") != owner:
                    raise GlobalFieldUsageEvidenceError(
                        f"class entry/internal-name mismatch: {entry}"
                    )
                possible = {
                    (
                        str(row.get("owner")),
                        str(row.get("name")),
                        str(row.get("descriptor")),
                    )
                    for row in cp_profile.get("member_references", [])
                    if isinstance(row, dict)
                    and row.get("kind") == "field"
                }
                if not (possible & targets):
                    continue

                source_classes_relevant += 1
                profile = profile_class_field_accesses(data)
                if profile.get("internal_name") != owner:
                    raise GlobalFieldUsageEvidenceError(
                        f"profile owner mismatch: {entry}"
                    )
                method_map = method_maps[owner]
                for method in profile.get("methods", []):
                    if not isinstance(method, dict):
                        continue
                    member_id = method_map.get(
                        (
                            str(method.get("name", "")),
                            str(method.get("descriptor", "")),
                        )
                    )
                    if member_id is None:
                        continue
                    canonical_methods_scanned += 1
                    for access in method.get("field_accesses", []):
                        if not isinstance(access, dict):
                            continue
                        key = (
                            str(access.get("owner")),
                            str(access.get("name")),
                            str(access.get("descriptor")),
                        )
                        if key not in targets:
                            continue
                        operation = str(access.get("operation", ""))
                        if operation not in {
                            "getstatic",
                            "putstatic",
                            "getfield",
                            "putfield",
                        }:
                            raise GlobalFieldUsageEvidenceError(
                                f"unexpected field operation {operation!r}"
                            )
                        usage[key][(member_id, operation)] += 1
                        observations += 1
    except zipfile.BadZipFile as exc:
        raise GlobalFieldUsageEvidenceError(
            f"invalid JAR: {jar_path}"
        ) from exc

    return dict(usage), {
        "source_classes_scanned": source_classes_scanned,
        "source_classes_relevant": source_classes_relevant,
        "canonical_methods_scanned": canonical_methods_scanned,
        "field_access_observations": observations,
    }


def _scan_source_class_usage(
    jar_path: Path,
    aliases: dict[str, str],
    targets: set[tuple[str, str, str]],
) -> tuple[
    dict[
        tuple[str, str, str],
        Counter[tuple[str, str]],
    ],
    dict[str, int],
]:
    usage: dict[
        tuple[str, str, str],
        Counter[tuple[str, str]],
    ] = defaultdict(Counter)
    classes_scanned = 0
    classes_relevant = 0
    observations = 0

    try:
        with zipfile.ZipFile(jar_path, "r") as archive:
            entries = sorted(
                name
                for name in archive.namelist()
                if name.endswith(".class")
            )
            for entry in entries:
                data = archive.read(entry)
                classes_scanned += 1
                cp_profile = profile_class_constant_pool_references(data)
                internal_name = cp_profile.get("internal_name")
                if not isinstance(internal_name, str) or not internal_name:
                    raise GlobalFieldUsageEvidenceError(
                        f"class profile missing internal name: {entry}"
                    )
                possible = {
                    (
                        str(row.get("owner")),
                        str(row.get("name")),
                        str(row.get("descriptor")),
                    )
                    for row in cp_profile.get("member_references", [])
                    if isinstance(row, dict)
                    and row.get("kind") == "field"
                }
                if not (possible & targets):
                    continue

                classes_relevant += 1
                profile = profile_class_field_accesses(data)
                if profile.get("internal_name") != internal_name:
                    raise GlobalFieldUsageEvidenceError(
                        f"profile owner mismatch: {entry}"
                    )
                source_identity = aliases.get(
                    internal_name,
                    "RAW:" + internal_name,
                )
                for method in profile.get("methods", []):
                    if not isinstance(method, dict):
                        continue
                    for access in method.get("field_accesses", []):
                        if not isinstance(access, dict):
                            continue
                        key = (
                            str(access.get("owner")),
                            str(access.get("name")),
                            str(access.get("descriptor")),
                        )
                        if key not in targets:
                            continue
                        operation = str(access.get("operation", ""))
                        if operation not in {
                            "getstatic",
                            "putstatic",
                            "getfield",
                            "putfield",
                        }:
                            raise GlobalFieldUsageEvidenceError(
                                f"unexpected field operation {operation!r}"
                            )
                        usage[key][(source_identity, operation)] += 1
                        observations += 1
    except zipfile.BadZipFile as exc:
        raise GlobalFieldUsageEvidenceError(
            f"invalid JAR: {jar_path}"
        ) from exc

    return dict(usage), {
        "classes_scanned": classes_scanned,
        "classes_relevant": classes_relevant,
        "field_access_observations": observations,
    }


def _topology_rows(
    topology: Counter[tuple[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "member_id": member_id,
            "operation": operation,
            "count": count,
        }
        for (member_id, operation), count in sorted(topology.items())
    ]


def _source_class_topology_rows(
    topology: Counter[tuple[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "source_class": source_class,
            "operation": operation,
            "count": count,
        }
        for (source_class, operation), count in sorted(topology.items())
    ]


def build_global_field_usage_evidence(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    *,
    old_build_id: str,
    new_build_id: str,
) -> dict[str, Any]:
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )
    if old_build_id == new_build_id:
        raise GlobalFieldUsageEvidenceError(
            "old/new build IDs must differ"
        )

    old_jar = old_jar.resolve()
    new_jar = new_jar.resolve()
    old_sha = sha256_file(old_jar)
    new_sha = sha256_file(new_jar)
    old_build = _build(class_lineage, old_build_id)
    new_build = _build(class_lineage, new_build_id)

    if old_sha.lower() != str(old_index.get("sha256", "")).lower():
        raise GlobalFieldUsageEvidenceError(
            "old JAR SHA does not match exact old index"
        )
    if new_sha.lower() != str(new_index.get("sha256", "")).lower():
        raise GlobalFieldUsageEvidenceError(
            "new JAR SHA does not match exact new index"
        )
    if old_sha.lower() != str(old_build.get("sha256", "")).lower():
        raise GlobalFieldUsageEvidenceError(
            "old JAR SHA does not match canonical old build"
        )
    if new_sha.lower() != str(new_build.get("sha256", "")).lower():
        raise GlobalFieldUsageEvidenceError(
            "new JAR SHA does not match canonical new build"
        )

    descriptor_identity_rejections: list[dict[str, Any]] = []
    reviews = _stable_reviews(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
        descriptor_identity_rejections=descriptor_identity_rejections,
    )
    input_stable_symbol_reviews = (
        len(reviews) + len(descriptor_identity_rejections)
    )
    old_methods, new_methods, paired_method_count = _paired_method_maps(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )

    old_targets = {
        _target_key(row["old_owner"], row["old"])
        for row in reviews
    }
    new_targets = {
        _target_key(row["new_owner"], row["new"])
        for row in reviews
    }
    old_usage, old_scan = _scan_usage(
        old_jar,
        old_methods,
        old_targets,
    )
    new_usage, new_scan = _scan_usage(
        new_jar,
        new_methods,
        new_targets,
    )
    old_class_usage, old_class_scan = _scan_source_class_usage(
        old_jar,
        _aliases(class_lineage, old_build_id),
        old_targets,
    )
    new_class_usage, new_class_scan = _scan_source_class_usage(
        new_jar,
        _aliases(class_lineage, new_build_id),
        new_targets,
    )

    candidates: list[dict[str, Any]] = []
    review_outcomes: list[dict[str, Any]] = [
        {
            **row,
            "outcome": "descriptor_identity_guard_rejected",
        }
        for row in descriptor_identity_rejections
    ]
    empty_both = 0
    changed_or_one_sided = 0
    canonical_method_topology_matches = 0
    global_class_topology_guard_rejected = 0
    raw_source_guard_rejected = 0

    for review in reviews:
        old_key = _target_key(review["old_owner"], review["old"])
        new_key = _target_key(review["new_owner"], review["new"])
        old_topology = old_usage.get(old_key, Counter())
        new_topology = new_usage.get(new_key, Counter())

        if not old_topology and not new_topology:
            empty_both += 1
            review_outcomes.append(
                {
                    **review,
                    "outcome": "empty_both",
                    "canonical_method_topology": [],
                    "global_source_class_topology": [],
                }
            )
            continue
        if not old_topology or old_topology != new_topology:
            changed_or_one_sided += 1
            review_outcomes.append(
                {
                    **review,
                    "outcome": "changed_or_one_sided",
                    "old_canonical_method_topology": _topology_rows(
                        old_topology
                    ),
                    "new_canonical_method_topology": _topology_rows(
                        new_topology
                    ),
                }
            )
            continue

        canonical_method_topology_matches += 1
        old_class_topology = old_class_usage.get(
            old_key,
            Counter(),
        )
        new_class_topology = new_class_usage.get(
            new_key,
            Counter(),
        )
        if (
            not old_class_topology
            or old_class_topology != new_class_topology
        ):
            global_class_topology_guard_rejected += 1
            review_outcomes.append(
                {
                    **review,
                    "outcome": "global_class_topology_guard_rejected",
                    "canonical_method_topology": _topology_rows(
                        old_topology
                    ),
                    "old_global_source_class_topology": (
                        _source_class_topology_rows(
                            old_class_topology
                        )
                    ),
                    "new_global_source_class_topology": (
                        _source_class_topology_rows(
                            new_class_topology
                        )
                    ),
                }
            )
            continue
        if any(
            source_class.startswith("RAW:")
            for source_class, _operation in old_class_topology
        ):
            raw_source_guard_rejected += 1
            review_outcomes.append(
                {
                    **review,
                    "outcome": "raw_source_guard_rejected",
                    "canonical_method_topology": _topology_rows(
                        old_topology
                    ),
                    "global_source_class_topology": (
                        _source_class_topology_rows(
                            old_class_topology
                        )
                    ),
                }
            )
            continue

        method_rows = _topology_rows(old_topology)
        class_rows = _source_class_topology_rows(
            old_class_topology
        )
        candidate = {
            **review,
            "strategy": (
                "canonical_method_and_global_class_usage_"
                "topology_exact"
            ),
            "confidence": "INFERRED_HIGH",
            "supports_existing_review": True,
            "observations": sum(old_topology.values()),
            "canonical_methods": len(
                {member_id for member_id, _operation in old_topology}
            ),
            "canonical_method_topology": method_rows,
            "global_source_class_topology": class_rows,
        }
        candidates.append(candidate)
        review_outcomes.append(
            {
                **review,
                "outcome": "candidate",
                "canonical_method_topology": method_rows,
                "global_source_class_topology": class_rows,
            }
        )

    candidates.sort(key=lambda row: row["relationship_id"])
    review_outcomes.sort(key=lambda row: row["relationship_id"])
    if len(review_outcomes) != input_stable_symbol_reviews:
        raise GlobalFieldUsageEvidenceError(
            "review outcome ledger does not cover the exact input frontier"
        )
    outcome_ids = [row["relationship_id"] for row in review_outcomes]
    if len(set(outcome_ids)) != len(outcome_ids):
        raise GlobalFieldUsageEvidenceError(
            "review outcome ledger contains duplicate relationship_id"
        )
    material = {
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "member_lineage_digest": _stable_digest(member_lineage),
        "candidates": candidates,
        "review_outcomes": review_outcomes,
    }
    report = {
        "schema_version": 1,
        "kind": "global_field_usage_identity_candidates",
        "canonical": False,
        "report_id": (
            "GLOBALFIELDUSE_"
            + _stable_digest(material)[:20].upper()
        ),
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "member_lineage_digest": material["member_lineage_digest"],
        "summary": {
            "input_stable_symbol_reviews": input_stable_symbol_reviews,
            "eligible_stable_symbol_reviews": len(reviews),
            "descriptor_identity_guard_rejected": (
                len(descriptor_identity_rejections)
            ),
            "paired_canonical_methods": paired_method_count,
            "candidate_fields": len(candidates),
            "review_outcomes": len(review_outcomes),
            "empty_both": empty_both,
            "changed_or_one_sided": changed_or_one_sided,
            "canonical_method_topology_matches": (
                canonical_method_topology_matches
            ),
            "global_class_topology_guard_rejected": (
                global_class_topology_guard_rejected
            ),
            "raw_source_guard_rejected": raw_source_guard_rejected,
            "remaining_without_global_topology_proof": (
                input_stable_symbol_reviews - len(candidates)
            ),
            "old_source_classes_scanned": old_scan[
                "source_classes_scanned"
            ],
            "new_source_classes_scanned": new_scan[
                "source_classes_scanned"
            ],
            "old_source_classes_relevant": old_scan[
                "source_classes_relevant"
            ],
            "new_source_classes_relevant": new_scan[
                "source_classes_relevant"
            ],
            "old_field_access_observations": old_scan[
                "field_access_observations"
            ],
            "new_field_access_observations": new_scan[
                "field_access_observations"
            ],
            "old_global_classes_scanned": old_class_scan[
                "classes_scanned"
            ],
            "new_global_classes_scanned": new_class_scan[
                "classes_scanned"
            ],
            "old_global_classes_relevant": old_class_scan[
                "classes_relevant"
            ],
            "new_global_classes_relevant": new_class_scan[
                "classes_relevant"
            ],
            "old_global_field_access_observations": old_class_scan[
                "field_access_observations"
            ],
            "new_global_field_access_observations": new_class_scan[
                "field_access_observations"
            ],
        },
        "candidates": candidates,
        "review_outcomes": review_outcomes,
        "descriptor_identity_rejections": descriptor_identity_rejections,
        "note": (
            "Research-only evidence. canonical=false. A candidate is emitted "
            "only when an existing stable_symbol field review has both the "
            "same non-empty multiset of canonical method IDs/read-write "
            "operations and the same complete canonical source-class/read-write "
            "topology across the exact old/new client JARs. Any supporting "
            "source class that is not canonical is refused. These guards detect "
            "contradictory accesses in unpaired methods. No member lineage "
            "relation is appended by this report. Stable-symbol reviews whose "
            "descriptor identity is contradicted by stronger canonical class "
            "lineage are recorded as rejected evidence and never considered "
            "candidates. review_outcomes is an exhaustive one-row-per-relationship "
            "ledger over the exact stable-symbol input frontier."
        ),
    }
    return report


def write_report(
    report: dict[str, Any],
    out: Path,
) -> None:
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
        prog="spk-global-field-usage-evidence"
    )
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("old_index", type=Path)
    p.add_argument("new_index", type=Path)
    p.add_argument("old_jar", type=Path)
    p.add_argument("new_jar", type=Path)
    p.add_argument("--old-build-id", required=True)
    p.add_argument("--new-build-id", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = build_global_field_usage_evidence(
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.old_index),
            _load(args.new_index),
            args.old_jar,
            args.new_jar,
            old_build_id=args.old_build_id,
            new_build_id=args.new_build_id,
        )
        write_report(report, args.out)
    except (
        GlobalFieldUsageEvidenceError,
        BytecodeProfileError,
        LineageValidationError,
        MemberLineageError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_GLOBAL_FIELD_USAGE_EVIDENCE_PASS")
    print(f"report_id={report['report_id']}")
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
