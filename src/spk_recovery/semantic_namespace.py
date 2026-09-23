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


def _accepted_nested_class_closure(
    class_lineage: dict[str, Any],
    index: dict[str, Any],
    *,
    build_id: str,
    requested: dict[str, Any],
    accepted_ids: list[str],
) -> list[dict[str, Any]]:
    """Keep binary nested-class names coupled to ACCEPTED outer remaps."""
    records_by_id: dict[str, dict[str, Any]] = {}
    records_by_source: dict[str, dict[str, Any]] = {}
    for record in class_lineage.get("classes", []):
        if not _has_build_entry(record, build_id):
            continue
        logical_id = str(record.get("logical_id"))
        source = str(_entry_for_build(record, build_id)["internal_name"])
        records_by_id[logical_id] = record
        records_by_source[source] = record

    indexed_by_name = {
        str(row.get("internal_name")): row
        for row in index.get("classes", {}).values()
        if isinstance(row, dict) and row.get("internal_name")
    }

    def structural_root(source: str) -> str | None:
        seen: set[str] = set()
        current = source
        while current not in seen:
            seen.add(current)
            meta = indexed_by_name.get(current)
            if not isinstance(meta, dict):
                return None
            owner = meta.get("inner_outer_name") or meta.get("enclosing_class_name")
            if not isinstance(owner, str) or not owner:
                return current if current != source else None
            current = owner
        return None

    rows: list[dict[str, Any]] = []
    for outer_id in sorted(accepted_ids):
        outer = records_by_id[outer_id]
        outer_source = str(_entry_for_build(outer, build_id)["internal_name"])
        outer_target = str(requested[outer_id]["target_internal_name"])
        prefix = outer_source + "$"

        for nested_source in sorted(
            name
            for name in records_by_source
            if name.startswith(prefix)
            and structural_root(name) == outer_source
        ):
            nested = records_by_source[nested_source]
            nested_id = str(nested.get("logical_id"))
            suffix = nested_source[len(outer_source):]
            required_target = outer_target + suffix
            existing = requested.get(nested_id)

            if existing is not None:
                existing_target = str(existing["target_internal_name"])
                if existing_target != required_target:
                    if nested.get("semantic_status") == "ACCEPTED":
                        raise SemanticNamespaceError(
                            f"{nested_id}: accepted nested semantic target "
                            f"{existing_target!r} conflicts with required binary "
                            f"nesting target {required_target!r} from {outer_id}"
                        )
                    raise SemanticNamespaceError(
                        f"{nested_id}: nested class already has incompatible "
                        f"target {existing_target!r}"
                    )
                continue

            requested[nested_id] = {
                "target_internal_name": required_target,
                "confidence": 1.0,
                "provenance": [
                    {
                        "kind": "source_safety",
                        "reason": "semantic_outer_nested_class_closure",
                        "strategy": "preserve_outer_inner_binary_name",
                        "accepted_outer_logical_id": outer_id,
                        "accepted_outer_source": outer_source,
                        "accepted_outer_target": outer_target,
                    }
                ],
            }
            rows.append(
                {
                    "logical_id": nested_id,
                    "source_internal_name": nested_source,
                    "target_internal_name": required_target,
                    "reason": "semantic_outer_nested_class_closure",
                    "strategy": "preserve_outer_inner_binary_name",
                    "accepted_outer_logical_id": outer_id,
                }
            )
    return rows


def _same_simple_nested_source_safety(
    class_lineage: dict[str, Any],
    index: dict[str, Any],
    *,
    build_id: str,
    requested: dict[str, Any],
    fallback_name_prefix: str,
) -> list[dict[str, Any]]:
    """Rename structurally nested classes that Java cannot declare safely.

    The JVM permits a member class whose InnerClasses simple name equals the
    direct enclosing type's simple name. Java source does not. This is a
    source-safety rename only; semantic state is never promoted.
    """
    records_by_source: dict[str, dict[str, Any]] = {}
    for record in class_lineage.get("classes", []):
        if not _has_build_entry(record, build_id):
            continue
        source = str(_entry_for_build(record, build_id)["internal_name"])
        records_by_source[source] = record

    indexed_by_name = {
        str(row.get("internal_name")): row
        for row in index.get("classes", {}).values()
        if isinstance(row, dict) and row.get("internal_name")
    }

    rows: list[dict[str, Any]] = []
    for nested_source in sorted(records_by_source):
        meta = indexed_by_name.get(nested_source)
        if not isinstance(meta, dict):
            continue
        outer_source = meta.get("inner_outer_name")
        inner_simple = meta.get("inner_simple_name")
        if (
            not isinstance(outer_source, str)
            or not outer_source
            or not isinstance(inner_simple, str)
            or not inner_simple
        ):
            continue
        outer_record = records_by_source.get(outer_source)
        if outer_record is None:
            continue

        outer_effective = (
            str(requested[str(outer_record["logical_id"])]["target_internal_name"])
            if str(outer_record["logical_id"]) in requested
            else outer_source
        )
        outer_simple = outer_effective.rsplit("$", 1)[-1].rsplit("/", 1)[-1]
        if inner_simple != outer_simple:
            continue

        nested = records_by_source[nested_source]
        nested_id = str(nested.get("logical_id"))
        existing = requested.get(nested_id)
        if existing is not None:
            existing_target = str(existing["target_internal_name"])
            existing_simple = existing_target.rsplit("$", 1)[-1].rsplit("/", 1)[-1]
            if existing_simple != outer_simple:
                continue
            if nested.get("semantic_status") == "ACCEPTED":
                raise SemanticNamespaceError(
                    f"{nested_id}: ACCEPTED semantic nested target "
                    f"{existing_target!r} still conflicts with enclosing "
                    f"simple name {outer_simple!r}"
                )

        target = (
            outer_effective
            + "$"
            + fallback_name_prefix
            + nested_id
        )
        requested[nested_id] = {
            "target_internal_name": target,
            "confidence": 1.0,
            "provenance": [
                {
                    "kind": "source_safety",
                    "reason": "java_enclosing_nested_simple_name_collision",
                    "strategy": "preserve_outer_binary_nested_class_rename",
                    "outer_source_internal_name": outer_source,
                    "outer_target_internal_name": outer_effective,
                    "inner_simple_name": inner_simple,
                }
            ],
        }
        rows.append(
            {
                "logical_id": nested_id,
                "source_internal_name": nested_source,
                "target_internal_name": target,
                "reason": "java_enclosing_nested_simple_name_collision",
                "strategy": "preserve_outer_binary_nested_class_rename",
                "outer_source_internal_name": outer_source,
                "outer_target_internal_name": outer_effective,
                "inner_simple_name": inner_simple,
            }
        )
    return rows


def _accepted_class_spec(
    class_lineage: dict[str, Any],
    index: dict[str, Any],
    *,
    build_id: str,
    source_sha256: str,
    target_package: str,
    source_safe_fallback: bool,
    fallback_name_prefix: str,
) -> tuple[
    dict[str, Any],
    list[str],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
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

        source_internal_name = str(
            _entry_for_build(record, build_id)["internal_name"]
        )
        source_package = (
            source_internal_name.rsplit("/", 1)[0]
            if "/" in source_internal_name
            else ""
        )
        target_internal_name = (
            (
                source_package + "/" + name
                if source_package
                else name
            )
            if source_safe_fallback
            else target_package.rstrip("/") + "/" + name
        )
        requested[logical_id] = {
            "target_internal_name": target_internal_name,
            "confidence": float(confidence),
            "provenance": provenance,
        }
        accepted_ids.append(logical_id)

    nested_rows = _accepted_nested_class_closure(
        class_lineage,
        index,
        build_id=build_id,
        requested=requested,
        accepted_ids=accepted_ids,
    )

    fallback_rows: list[dict[str, Any]] = []
    same_simple_nested_rows: list[dict[str, Any]] = []
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
            source_name = effective_names[logical_id]
            source_package = (
                source_name.rsplit("/", 1)[0]
                if "/" in source_name
                else ""
            )
            fallback_simple_name = fallback_name_prefix + logical_id
            target = (
                source_package + "/" + fallback_simple_name
                if source_package
                else fallback_simple_name
            )
            requested[logical_id] = {
                "target_internal_name": target,
                "confidence": 1.0,
                "provenance": [
                    {
                        "kind": "source_safety",
                        "reason": "java_class_package_collision",
                        "strategy": "package_preserving_class_rename",
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
                    "strategy": "package_preserving_class_rename",
                    "conflicting_descendants": descendants,
                }
            )

        same_simple_nested_rows = _same_simple_nested_source_safety(
            class_lineage,
            index,
            build_id=build_id,
            requested=requested,
            fallback_name_prefix=fallback_name_prefix,
        )

    spec = {
        "schema_version": 1,
        "kind": "remap_spec",
        "build_id": build_id,
        "source_sha256": source_sha256,
        "classes": requested,
    }
    return (
        spec,
        sorted(accepted_ids),
        fallback_rows,
        nested_rows,
        same_simple_nested_rows,
    )


def build_semantic_namespace(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    index: dict[str, Any],
    *,
    build_id: str,
    target_package: str = "recovered/spawnpk/client",
    source_safe_fallback: bool = False,
    fallback_name_prefix: str = "Recovered_",
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

    semantic_package_strategy = (
        "source_package_preserving"
        if source_safe_fallback
        else "global_target_package"
    )

    if (
        not isinstance(fallback_name_prefix, str)
        or not fallback_name_prefix
        or not _IDENTIFIER.fullmatch(fallback_name_prefix + "X")
    ):
        raise SemanticNamespaceError(
            f"invalid fallback name prefix {fallback_name_prefix!r}"
        )

    (
        class_spec,
        accepted_class_ids,
        fallback_rows,
        nested_rows,
        same_simple_nested_rows,
    ) = _accepted_class_spec(
        class_lineage,
        index,
        build_id=build_id,
        source_sha256=source_sha,
        target_package=package,
        source_safe_fallback=source_safe_fallback,
        fallback_name_prefix=fallback_name_prefix,
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
            source_safe_fallback=source_safe_fallback,
            fallback_name_prefix=fallback_name_prefix,
        )
    except MemberRemapPlanError as exc:
        raise SemanticNamespaceError(str(exc)) from exc

    member_source_safety_rows = [
        row
        for row in member_plan.get("members", [])
        if any(
            isinstance(prov, dict)
            and prov.get("kind") == "source_safety"
            and prov.get("reason") == "java_reserved_member_name"
            for prov in row.get("provenance", [])
        )
    ]

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
        "semantic_package_strategy": semantic_package_strategy,
        "fallback_name_prefix": fallback_name_prefix,
        "fallback_remaps": fallback_rows,
        "member_source_safety_remaps": member_source_safety_rows,
        "nested_class_closure_remaps": nested_rows,
        "same_simple_nested_source_safety_remaps": same_simple_nested_rows,
        "class_plan_digest": class_plan_digest,
        "member_plan_digest": member_plan_digest,
        "accepted_class_ids": accepted_class_ids,
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
        "semantic_package_strategy": semantic_package_strategy,
        "fallback_name_prefix": fallback_name_prefix,
        "class_plan_digest": class_plan_digest,
        "member_plan_digest": member_plan_digest,
        "summary": {
            "source_safety_fallbacks": len(fallback_rows),
            "source_safety_nested_class_remaps": len(nested_rows),
            "source_safety_same_simple_nested_remaps": len(same_simple_nested_rows),
            "source_safety_member_remaps": len(member_source_safety_rows),
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
        "nested_class_closure_remaps": nested_rows,
        "same_simple_nested_source_safety_remaps": same_simple_nested_rows,
        "member_source_safety_remaps": member_source_safety_rows,
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
