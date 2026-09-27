from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile


class NamespaceRemapBoundaryError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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


def build_namespace_remap_boundary(
    private_graph: dict[str, Any],
    readable_jar: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    if (
        private_graph.get("schema_version") != 1
        or private_graph.get("kind") != "namespace_collision_graph"
        or private_graph.get("identifiers_included") is not True
    ):
        raise NamespaceRemapBoundaryError(
            "requires private identifier-bearing collision graph"
        )

    readable_jar = readable_jar.resolve()
    if not readable_jar.is_file():
        raise NamespaceRemapBoundaryError("readable JAR missing")

    classes = _class_identities(readable_jar)

    node_candidates: dict[str, set[str]] = defaultdict(set)
    node_origins: dict[str, set[str]] = defaultdict(set)

    for row in private_graph.get("candidates", []):
        candidate_id = row.get("candidate_id")
        internal = row.get("candidate_internal_name")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise NamespaceRemapBoundaryError(
                "candidate lacks stable candidate_id"
            )
        if not isinstance(internal, str) or not internal:
            raise NamespaceRemapBoundaryError(
                "candidate lacks internal name"
            )
        if internal not in classes:
            raise NamespaceRemapBoundaryError(
                "candidate absent from readable class set"
            )

        ancestors = row.get(
            "ancestor_collision_internal_names",
            [],
        )
        descendants = row.get(
            "descendant_internal_names",
            [],
        )

        for node in ancestors:
            if node not in classes:
                raise NamespaceRemapBoundaryError(
                    "ancestor collision node absent from readable class set"
                )
            node_candidates[node].add(candidate_id)
            node_origins[node].add("ancestor_class_blocks_package")

        if descendants:
            node_candidates[internal].add(candidate_id)
            node_origins[internal].add(
                "candidate_class_is_package_prefix"
            )

    nodes: list[dict[str, Any]] = []
    private_nodes: list[dict[str, Any]] = []

    for index, node in enumerate(
        sorted(node_candidates),
        start=1,
    ):
        descendants = sorted(
            name
            for name in classes
            if name.startswith(node + "/")
        )
        if not descendants:
            raise NamespaceRemapBoundaryError(
                "collision node has no descendant package classes"
            )

        candidate_ids = sorted(node_candidates[node])
        origins = sorted(node_origins[node])
        node_id = f"NSREMAP_NODE_{index:03d}"

        public = {
            "node_id": node_id,
            "collision_depth": len(node.split("/")),
            "affected_candidate_count": len(candidate_ids),
            "affected_candidate_ids": candidate_ids,
            "collision_origins": origins,
            "package_subtree_class_count": len(descendants),
            "selection_status": "review_required",
            "boundary_options": {
                "rename_colliding_class_identity": {
                    "class_identity_count": 1,
                    "package_subtree_class_count": 0,
                    "requires_classfile_reference_rewrite": True,
                    "requires_source_reference_rewrite": True,
                },
                "rename_descendant_package_subtree": {
                    "class_identity_count": len(descendants),
                    "package_subtree_class_count": len(descendants),
                    "requires_classfile_reference_rewrite": True,
                    "requires_source_reference_rewrite": True,
                },
            },
        }
        nodes.append(public)

        if include_identifiers:
            private_nodes.append(
                {
                    **public,
                    "collision_internal_name": node,
                    "descendant_internal_names": descendants,
                }
            )

    material = {
        "collision_graph_id": private_graph.get("graph_id"),
        "readable_jar_sha256": private_graph.get(
            "readable_jar_sha256"
        ),
        "nodes": nodes,
    }
    report = {
        "schema_version": 1,
        "kind": "namespace_remap_boundary",
        "boundary_id": (
            "NSREMAP_"
            + _stable_digest(material)[:20].upper()
        ),
        "collision_graph_id": private_graph.get("graph_id"),
        "readable_jar_sha256": private_graph.get(
            "readable_jar_sha256"
        ),
        "summary": {
            "collision_node_count": len(nodes),
            "affected_candidate_count": len(
                {
                    candidate_id
                    for row in nodes
                    for candidate_id in row[
                        "affected_candidate_ids"
                    ]
                }
            ),
            "all_nodes_review_required": all(
                row["selection_status"] == "review_required"
                for row in nodes
            ),
            "automatic_strategy_selection_count": 0,
        },
        "nodes": (
            private_nodes
            if include_identifiers
            else nodes
        ),
        "identifiers_included": include_identifiers,
    }
    return report


def write_namespace_remap_boundary(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
