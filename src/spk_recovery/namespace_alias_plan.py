from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .namespace_collision_graph import (
    _class_identities,
    _package_prefix_index,
)


class NamespaceAliasPlanError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_namespace_alias_plan(
    readable_jar: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    readable_jar = readable_jar.resolve()
    if not readable_jar.is_file():
        raise NamespaceAliasPlanError(
            "readable JAR missing"
        )

    classes = _class_identities(readable_jar)
    package_index = _package_prefix_index(classes)
    collision_nodes = sorted(
        name
        for name in classes
        if name in package_index
    )

    readable_sha = _sha256_file(readable_jar)
    namespace_token = readable_sha[:12]
    alias_root = (
        "spk_compile_alias/r8s/"
        + namespace_token
    )

    if any(
        name == alias_root
        or name.startswith(alias_root + "/")
        for name in classes
    ):
        raise NamespaceAliasPlanError(
            "reserved compile-alias namespace already exists"
        )

    public_nodes: list[dict[str, Any]] = []
    private_nodes: list[dict[str, Any]] = []
    mapping: dict[str, str] = {}

    for index, old in enumerate(
        collision_nodes,
        start=1,
    ):
        simple = old.rsplit("/", 1)[-1]
        alias = (
            alias_root
            + f"/NODE_{index:04d}/"
            + simple
        )
        if alias in classes or alias in mapping.values():
            raise NamespaceAliasPlanError(
                "generated alias identity collision"
            )
        mapping[old] = alias

        nested = sorted(
            name
            for name in classes
            if name.startswith(old + "$")
        )
        descendants = sorted(
            package_index.get(old, set())
        )

        public = {
            "node_id": f"NSALIAS_NODE_{index:04d}",
            "collision_depth": len(old.split("/")),
            "nested_class_count": len(nested),
            "package_descendant_class_count": len(
                descendants
            ),
            "alias_simple_name_preserved": True,
        }
        public_nodes.append(public)

        if include_identifiers:
            private_nodes.append(
                {
                    **public,
                    "original_internal_name": old,
                    "alias_internal_name": alias,
                    "nested_internal_names": nested,
                    "package_descendant_internal_names": (
                        descendants
                    ),
                }
            )

    material = {
        "readable_jar_sha256": readable_sha,
        "alias_root": alias_root,
        "nodes": public_nodes,
    }
    report = {
        "schema_version": 1,
        "kind": "namespace_alias_plan",
        "plan_id": (
            "NSALIAS_"
            + _stable_digest(material)[:20].upper()
        ),
        "readable_jar_sha256": readable_sha,
        "summary": {
            "readable_class_count": len(classes),
            "collision_node_count": len(
                collision_nodes
            ),
            "mapped_class_identity_count": len(
                mapping
            ),
            "nested_class_count": sum(
                row["nested_class_count"]
                for row in public_nodes
            ),
            "package_descendant_class_count": sum(
                row["package_descendant_class_count"]
                for row in public_nodes
            ),
            "alias_root_depth": len(
                alias_root.split("/")
            ),
        },
        "nodes": (
            private_nodes
            if include_identifiers
            else public_nodes
        ),
        "mapping": (
            mapping
            if include_identifiers
            else None
        ),
        "identifiers_included": include_identifiers,
    }
    return report


def reverse_alias_mapping(
    private_plan: dict[str, Any],
) -> dict[str, str]:
    if (
        private_plan.get("schema_version") != 1
        or private_plan.get("kind") != "namespace_alias_plan"
        or private_plan.get("identifiers_included") is not True
    ):
        raise NamespaceAliasPlanError(
            "requires private namespace alias plan"
        )

    mapping = private_plan.get("mapping")
    if not isinstance(mapping, dict):
        raise NamespaceAliasPlanError(
            "private alias plan lacks mapping"
        )

    reverse: dict[str, str] = {}
    for old, alias in mapping.items():
        if not isinstance(old, str) or not isinstance(alias, str):
            raise NamespaceAliasPlanError(
                "invalid alias mapping entry"
            )
        if alias in reverse:
            raise NamespaceAliasPlanError(
                "alias mapping is not bijective"
            )
        reverse[alias] = old
    return reverse


def write_namespace_alias_plan(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
