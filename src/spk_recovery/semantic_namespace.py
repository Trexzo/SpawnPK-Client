from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .lineage import validate_lineage
from .member_lineage import validate_member_lineage
from .member_remap_plan import (
    MemberRemapPlanError,
    build_member_remap_plan,
)
from .remap_plan import RemapPlanError, build_remap_plan


class SemanticNamespaceError(ValueError):
    pass


_IDENTIFIER = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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
        raise SemanticNamespaceError(
            f"expected one canonical build {build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _has_build_entry(
    record: dict[str, Any],
    build_id: str,
) -> bool:
    return any(
        entry.get("build_id") == build_id
        for entry in record.get("lineage", [])
    )


def _entry_for_build(record: dict[str, Any], build_id: str) -> dict[str, Any]:
    hits = [
        entry
        for entry in record.get("lineage", [])
        if entry.get("build_id") == build_id
    ]
    if len(hits) != 1:
        raise SemanticNamespaceError(
            f"{record.get('logical_id')}: expected one lineage entry for "
            f"{build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _class_package_collision_roots(names: dict[str, str]) -> dict[str, list[str]]:
    """Return logical IDs whose effective class name is also a package prefix."""
    by_name = {name: logical_id for logical_id, name in names.items()}
    roots: dict[str, set[str]] = {}
    for descendant_id, descendant in names.items():
        parts = descendant.split("/")
        for i in range(1, len(parts)):
            prefix = "/".join(parts[:i])
            root_id = by_name.get(prefix)
            if root_id is not None and root_id != descendant_id:
                roots.setdefault(root_id, set()).add(descendant)
    return {
        logical_id: sorted(descendants)
        for logical_id, descendants in sorted(roots.items())
    }


def _accepted_class_spec(
    class_lineage: dict[str, Any],
    *,
    build_id: str,
    source_sha256: str,
    target_package: str,
    source_safe_fallback: bool,
    fallback_package: str,
) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    requested: dict[str, Any] = {}
    accepted_ids: list[str] = []

    for record in class_lineage.get("classes", []):
        if not _has_build_entry(record, build_id):
            continue
        if record.get("semantic_status") != "ACCEPTED":
            continue

        logical_id = str(record.get("logical_id"))
        name = record.get("semantic_name")
        if not isinstance(name, str) or not _IDENTIFIER.fullmatch(name):
            raise SemanticNamespaceError(
                f"{logical_id}: accepted class semantic name is not one Java identifier"
            )
        confidence = record.get("semantic_confidence")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= float(confidence) <= 1.0
        ):
            raise SemanticNamespaceError(
                f"{logical_id}: accepted class semantic confidence is invalid"
            )
        provenance = record.get("semantic_provenance")
        if not isinstance(provenance, list) or not provenance:
            raise SemanticNamespaceError(
                f"{logical_id}: accepted class semantic name lacks provenance"
            )

        requested[logical_id] = {
            "target_internal_name": (
                target_package.rstrip("/") + "/" + name
            ),
            "confidence": float(confidence),
            "provenance": provenance,
        }
        accepted_ids.append(logical_id)

    fallback_rows: list[dict[str, Any]] = []
    if source_safe_fallback:
        effective_names: dict[str, str] = {}
        records_by_id: dict[str, dict[str, Any]] = {}
        for record in class_lineage.get("classes", []):
            if not _has_build_entry(record, build_id):
                continue
            logical_id = str(record.get("logical_id"))
            records_by_id[logical_id] = record
            entry = _entry_for_build(record, build_id)
            cfg = requested.get(logical_id)
            effective_names[logical_id] = (
                str(cfg["target_internal_name"])
                if cfg is not None
                else str(entry["internal_name"])
            )

        collisions = _class_package_collision_roots(effective_names)
        for logical_id, descendants in collisions.items():
            if logical_id in requested:
                raise SemanticNamespaceError(
                    f"{logical_id}: accepted semantic target still creates a "
                    "Java class/package collision; source-safety fallback cannot "
                    "override ACCEPTED semantics"
                )
            record = records_by_id[logical_id]
            if record.get("semantic_status") == "ACCEPTED":
                raise SemanticNamespaceError(
                    f"{logical_id}: ACCEPTED semantic class remained at a "
                    "class/package collision root"
                )
            target = (
                fallback_package.rstrip("/")
                + "/"
                + logical_id
            )
            requested[logical_id] = {
                "target_internal_name": target,
                "confidence": 1.0,
                "provenance": [
                    {
                        "kind": "source_safety",
                        "reason": "java_class_package_collision",
                        "conflicting_descendants": descendants,
                    }
                ],
            }
            fallback_rows.append(
                {
                    "logical_id": logical_id,
                    "source_internal_name": effective_names[logical_id],
                    "target_internal_name": target,
                    "reason": "java_class_package_collision",
                    "conflicting_descendants": descendants,
                }
            )

    spec = {
        "schema_version": 1,
        "kind": "remap_spec",
        "build_id": build_id,
        "source_sha256": source_sha256,
        "classes": requested,
    }
    return spec, sorted(accepted_ids), fallback_rows


def build_semantic_namespace(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    index: dict[str, Any],
    *,
    build_id: str,
    target_package: str = "recovered/spawnpk/client",
    source_safe_fallback: bool = False,
    fallback_package: str = "recovered/spawnpk/fallback",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build semantic remaps plus optional non-semantic Java source-safety remaps."""
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )
    build = _build(class_lineage, build_id)
    source_sha = str(build.get("sha256", "")).lower()
    if str(index.get("sha256", "")).lower() != source_sha:
        raise SemanticNamespaceError(
            "semantic namespace index SHA-256 does not match canonical build"
        )

    package = target_package.rstrip("/")
    parts = package.split("/")
    if (
        not package
        or any(not _IDENTIFIER.fullmatch(part) for part in parts)
        or package.startswith(("java/", "javax/", "jdk/", "sun/"))
    ):
        raise SemanticNamespaceError(
            f"invalid or reserved target package {target_package!r}"
        )

    fallback = fallback_package.rstrip("/")
    fallback_parts = fallback.split("/")
    if (
        not fallback
        or any(not _IDENTIFIER.fullmatch(part) for part in fallback_parts)
        or fallback.startswith(("java/", "javax/", "jdk/", "sun/"))
    ):
        raise SemanticNamespaceError(
            f"invalid or reserved fallback package {fallback_package!r}"
        )

    class_spec, accepted_class_ids, fallback_rows = _accepted_class_spec(
        class_lineage,
        build_id=build_id,
        source_sha256=source_sha,
        target_package=package,
        source_safe_fallback=source_safe_fallback,
        fallback_package=fallback,
    )
    if class_spec["classes"]:
        try:
            class_plan = build_remap_plan(
                class_lineage,
                class_spec,
            )
        except RemapPlanError as exc:
            raise SemanticNamespaceError(str(exc)) from exc
    else:
        class_plan = {
            "schema_version": 1,
            "kind": "remap_plan",
            "build_id": build_id,
            "source_sha256": source_sha,
            "class_count": 0,
            "classes": [],
        }

    try:
        member_plan = build_member_remap_plan(
            class_lineage,
            member_lineage,
            index,
            build_id=build_id,
        )
    except MemberRemapPlanError as exc:
        raise SemanticNamespaceError(str(exc)) from exc

    build_classes = [
        row
        for row in class_lineage.get("classes", [])
        if _has_build_entry(row, build_id)
    ]
    build_members = [
        row
        for row in member_lineage.get("members", [])
        if _has_build_entry(row, build_id)
    ]
    fields = [
        row for row in build_members
        if row.get("kind") == "field"
    ]
    methods = [
        row for row in build_members
        if row.get("kind") == "method"
    ]

    accepted_classes = sum(
        1
        for row in build_classes
        if row.get("semantic_status") == "ACCEPTED"
    )
    accepted_fields = sum(
        1
        for row in fields
        if row.get("semantic_status") == "ACCEPTED"
    )
    accepted_methods = sum(
        1
        for row in methods
        if row.get("semantic_status") == "ACCEPTED"
    )

    class_plan_digest = _stable_digest(class_plan)
    member_plan_digest = _stable_digest(member_plan)
    material = {
        "build_id": build_id,
        "source_sha256": source_sha,
        "target_package": package,
        "source_safe_fallback": source_safe_fallback,
        "fallback_package": fallback,
        "fallback_remaps": fallback_rows,
        "class_plan_digest": class_plan_digest,
        "member_plan_digest": member_plan_digest,
        "accepted_class_ids": accepted_class_ids,
        "fallback_remaps": fallback_rows,
    }

    manifest = {
        "schema_version": 1,
        "kind": "semantic_namespace_manifest",
        "namespace_id": (
            "SEMNS_" + _stable_digest(material)[:20].upper()
        ),
        "build_id": build_id,
        "source_sha256": source_sha,
        "target_package": package,
        "source_safe_fallback": source_safe_fallback,
        "fallback_package": fallback,
        "class_plan_digest": class_plan_digest,
        "member_plan_digest": member_plan_digest,
        "summary": {
            "source_safety_fallbacks": len(fallback_rows),
            "classes_total": len(build_classes),
            "classes_accepted": accepted_classes,
            "classes_remapped": class_plan["class_count"],
            "fields_total": len(fields),
            "fields_accepted": accepted_fields,
            "fields_remapped": member_plan["field_count"],
            "methods_total": len(methods),
            "methods_accepted": accepted_methods,
            "methods_remapped": member_plan["method_count"],
            "members_total": len(build_members),
            "members_accepted": accepted_fields + accepted_methods,
            "members_remapped": member_plan["member_count"],
        },
        "accepted_class_ids": accepted_class_ids,
        "fallback_remaps": fallback_rows,
    }
    return manifest, class_plan, member_plan


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
