from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile


class NamespaceCollisionError(ValueError):
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


def _class_identities(jar: Path) -> set[str]:
    with zipfile.ZipFile(jar) as z:
        return {
            info.filename[:-6]
            for info in z.infolist()
            if (
                not info.is_dir()
                and info.filename.endswith(".class")
                and not info.filename.startswith("META-INF/")
                and info.filename != "module-info.class"
            )
        }


def _package_prefixes(name: str) -> list[str]:
    parts = name.split("/")
    return [
        "/".join(parts[:i])
        for i in range(1, len(parts))
    ]


def _package_prefix_index(
    classes: set[str],
) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for name in classes:
        for prefix in _package_prefixes(name):
            out.setdefault(prefix, set()).add(name)
    return out


def build_namespace_collision_graph(
    private_plan: dict[str, Any],
    readable_jar: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    if (
        private_plan.get("schema_version") != 1
        or private_plan.get("kind")
        != "javac_missing_class_recovery_plan"
        or private_plan.get("identifiers_included") is not True
    ):
        raise NamespaceCollisionError(
            "requires private identifier-bearing recovery plan"
        )

    readable_jar = readable_jar.resolve()
    if not readable_jar.is_file():
        raise NamespaceCollisionError("readable JAR missing")

    classes = _class_identities(readable_jar)
    package_index = _package_prefix_index(classes)
    collision_nodes = sorted(
        name
        for name in classes
        if name in package_index
    )

    rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []

    for candidate in private_plan.get("candidates", []):
        candidate_id = candidate.get("candidate_id")
        internal = candidate.get("candidate_internal_name")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise NamespaceCollisionError(
                "candidate lacks stable candidate_id"
            )
        if not isinstance(internal, str) or not internal:
            raise NamespaceCollisionError(
                "candidate lacks internal name"
            )
        if internal not in classes:
            raise NamespaceCollisionError(
                "candidate absent from readable class set"
            )

        ancestors = _package_prefixes(internal)
        ancestor_collisions = [
            prefix
            for prefix in ancestors
            if prefix in classes
        ]
        descendant_classes = sorted(
            package_index.get(internal, set())
        )

        if ancestor_collisions and descendant_classes:
            relation = "ancestor_and_descendant_collision"
        elif ancestor_collisions:
            relation = "ancestor_class_blocks_package"
        elif descendant_classes:
            relation = "candidate_class_is_package_prefix"
        else:
            relation = "no_namespace_collision"

        collision_depths = [
            len(name.split("/"))
            for name in ancestor_collisions
        ]

        public = {
            "candidate_id": candidate_id,
            "relation": relation,
            "package_depth": len(internal.split("/")) - 1,
            "ancestor_collision_count": len(
                ancestor_collisions
            ),
            "ancestor_collision_depths": collision_depths,
            "nearest_ancestor_distance": (
                len(internal.split("/"))
                - len(ancestor_collisions[-1].split("/"))
                if ancestor_collisions
                else None
            ),
            "descendant_class_count": len(
                descendant_classes
            ),
            "direct_collision_node": (
                internal in package_index
            ),
            "remap_boundaries": {
                "colliding_class_identity_count": (
                    len(ancestor_collisions)
                ),
                "candidate_package_descendant_count": (
                    len(descendant_classes)
                ),
            },
        }
        rows.append(public)

        if include_identifiers:
            private_rows.append(
                {
                    **public,
                    "candidate_internal_name": internal,
                    "ancestor_collision_internal_names": (
                        ancestor_collisions
                    ),
                    "descendant_internal_names": (
                        descendant_classes
                    ),
                }
            )

    relation_counts = Counter(
        row["relation"]
        for row in rows
    )
    candidate_collision_count = sum(
        1
        for row in rows
        if row["relation"] != "no_namespace_collision"
    )
    candidate_ancestor_collision_count = sum(
        1
        for row in rows
        if row["ancestor_collision_count"] > 0
    )
    candidate_descendant_collision_count = sum(
        1
        for row in rows
        if row["descendant_class_count"] > 0
    )

    public_material = {
        "class_recovery_plan_id": private_plan.get("plan_id"),
        "readable_jar_sha256": _sha256_file(readable_jar),
        "class_count": len(classes),
        "collision_node_count": len(collision_nodes),
        "candidates": rows,
    }

    report = {
        "schema_version": 1,
        "kind": "namespace_collision_graph",
        "graph_id": (
            "NSCOLLISION_"
            + _stable_digest(public_material)[:20].upper()
        ),
        "class_recovery_plan_id": private_plan.get("plan_id"),
        "readable_jar_sha256": public_material[
            "readable_jar_sha256"
        ],
        "summary": {
            "readable_class_count": len(classes),
            "global_collision_node_count": len(
                collision_nodes
            ),
            "candidate_count": len(rows),
            "candidate_collision_count": (
                candidate_collision_count
            ),
            "candidate_ancestor_collision_count": (
                candidate_ancestor_collision_count
            ),
            "candidate_descendant_collision_count": (
                candidate_descendant_collision_count
            ),
            "relation_counts": dict(
                sorted(relation_counts.items())
            ),
        },
        "candidates": (
            private_rows
            if include_identifiers
            else rows
        ),
        "identifiers_included": include_identifiers,
    }
    return report


def write_namespace_collision_graph(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
