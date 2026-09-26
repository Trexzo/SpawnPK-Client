from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile


class NamespaceCollisionProofError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _class_names(jar: Path) -> set[str]:
    names: set[str] = set()
    with zipfile.ZipFile(jar) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.endswith(".class"):
                continue
            if info.filename.startswith("META-INF/versions/"):
                continue
            names.add(info.filename[:-6])
    return names


def _candidate_names(private_plan: dict[str, Any]) -> list[tuple[str, str]]:
    if (
        private_plan.get("schema_version") != 1
        or private_plan.get("kind")
        != "javac_missing_class_recovery_plan"
        or private_plan.get("identifiers_included") is not True
    ):
        raise NamespaceCollisionProofError(
            "requires private identifier-bearing class recovery plan"
        )

    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for row in private_plan.get("candidates", []):
        candidate_id = row.get("candidate_id")
        internal = row.get("candidate_internal_name")
        if (
            not isinstance(candidate_id, str)
            or not candidate_id
            or not isinstance(internal, str)
            or not internal
        ):
            raise NamespaceCollisionProofError(
                "private plan candidate lacks exact identity"
            )
        if internal in seen:
            raise NamespaceCollisionProofError(
                "duplicate candidate internal name"
            )
        seen.add(internal)
        rows.append((candidate_id, internal))
    return rows


def _proper_package_prefixes(internal: str) -> list[str]:
    parts = internal.split("/")
    return [
        "/".join(parts[:index])
        for index in range(1, len(parts))
    ]


def _rename_family(
    classes: set[str],
    owner: str,
    destination: str,
) -> dict[str, str]:
    family: dict[str, str] = {}
    prefix = owner + "$"
    for internal in sorted(classes):
        if internal == owner:
            family[internal] = destination
        elif internal.startswith(prefix):
            suffix = internal[len(owner):]
            family[internal] = destination + suffix
    return family


def _collision_nodes_for_classes(
    classes: set[str],
) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for internal in classes:
        for prefix in _proper_package_prefixes(internal):
            if prefix in classes:
                out[prefix].add(internal)
    return out


def _apply_rename_map(
    classes: set[str],
    rename_map: dict[str, str],
) -> set[str]:
    remapped = {
        rename_map.get(internal, internal)
        for internal in classes
    }
    if len(remapped) != len(classes):
        raise NamespaceCollisionProofError(
            "rename plan collapses distinct class identities"
        )
    return remapped


def prove_namespace_collisions(
    private_plan: dict[str, Any],
    readable_jar: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    readable_jar = readable_jar.resolve()
    if not readable_jar.is_file():
        raise NamespaceCollisionProofError(
            "readable JAR does not exist"
        )

    candidates = _candidate_names(private_plan)
    classes = _class_names(readable_jar)

    collision_descendants = _collision_nodes_for_classes(
        classes
    )
    collision_nodes = set(collision_descendants)
    candidate_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []

    candidate_collision_nodes: set[str] = set()
    collision_node_to_candidates: dict[str, set[str]] = defaultdict(set)

    for candidate_id, internal in candidates:
        if internal not in classes:
            raise NamespaceCollisionProofError(
                "candidate missing from readable JAR"
            )

        chain = [
            prefix
            for prefix in _proper_package_prefixes(internal)
            if prefix in collision_nodes
        ]
        candidate_collision_nodes.update(chain)
        for node in chain:
            collision_node_to_candidates[node].add(candidate_id)

        public = {
            "candidate_id": candidate_id,
            "collision_count": len(chain),
            "collision_depths": [
                node.count("/") + 1
                for node in chain
            ],
            "collision_proven": bool(chain),
            "deepest_collision_depth": (
                max((node.count("/") + 1 for node in chain), default=0)
            ),
        }
        candidate_rows.append(public)

        private_rows.append(
            {
                **public,
                "candidate_internal_name": internal,
                "collision_nodes": chain,
            }
        )

    impacted_descendant_count = sum(
        len(collision_descendants[node])
        for node in candidate_collision_nodes
    )

    collision_plan_rows: list[dict[str, Any]] = []
    private_plan_rows: list[dict[str, Any]] = []
    aggregate_rename_map: dict[str, str] = {}

    for index, node in enumerate(
        sorted(
            candidate_collision_nodes,
            key=lambda value: (value.count("/"), value),
        ),
        start=1,
    ):
        remap_id = f"JCOLLISION_{index:03d}"
        descendant_count = len(collision_descendants[node])
        affected_candidates = sorted(
            collision_node_to_candidates[node]
        )
        proposed = (
            node
            + "__spk_type_"
            + hashlib.sha256(node.encode("utf-8")).hexdigest()[:8]
        )
        family = _rename_family(
            classes,
            node,
            proposed,
        )
        if node not in family:
            raise NamespaceCollisionProofError(
                "colliding owner missing from rename family"
            )
        for old_name, new_name in family.items():
            existing = aggregate_rename_map.get(old_name)
            if existing is not None and existing != new_name:
                raise NamespaceCollisionProofError(
                    "overlapping collision rename families disagree"
                )
            aggregate_rename_map[old_name] = new_name

        public = {
            "collision_id": remap_id,
            "package_depth": node.count("/") + 1,
            "descendant_class_count": descendant_count,
            "affected_candidate_count": len(affected_candidates),
            "affected_candidate_ids": affected_candidates,
            "repair_strategy": "rename_colliding_class_node",
            "rename_family_class_count": len(family),
            "nested_binary_class_count": max(0, len(family) - 1),
            "requires_classfile_reference_rewrite": True,
            "requires_source_reference_rewrite": True,
        }
        collision_plan_rows.append(public)
        private_plan_rows.append(
            {
                **public,
                "colliding_class_internal_name": node,
                "proposed_internal_name": proposed,
                "rename_family": [
                    {
                        "from": old_name,
                        "to": new_name,
                    }
                    for old_name, new_name in sorted(
                        family.items()
                    )
                ],
                "descendant_classes": sorted(
                    collision_descendants[node]
                ),
            }
        )

    proposed_names = set(aggregate_rename_map.values())
    untouched_names = classes - set(aggregate_rename_map)
    destination_conflicts = sorted(
        proposed_names & untouched_names
    )
    if destination_conflicts:
        raise NamespaceCollisionProofError(
            "rename destination already exists in readable JAR"
        )

    simulated_classes = _apply_rename_map(
        classes,
        aggregate_rename_map,
    )
    simulated_collisions = _collision_nodes_for_classes(
        simulated_classes
    )

    simulated_candidate_collision_count = 0
    for _candidate_id, internal in candidates:
        remaining = [
            prefix
            for prefix in _proper_package_prefixes(internal)
            if prefix in simulated_collisions
        ]
        if remaining:
            simulated_candidate_collision_count += 1

    newly_created_collision_nodes = sorted(
        set(simulated_collisions)
        - (
            set(collision_nodes)
            - set(candidate_collision_nodes)
        )
    )

    candidate_proven_count = sum(
        row["collision_proven"] for row in candidate_rows
    )
    collision_depths = Counter(
        depth
        for row in candidate_rows
        for depth in row["collision_depths"]
    )

    material = {
        "class_recovery_plan_id": private_plan.get("plan_id"),
        "readable_jar_sha256": _sha256_file(readable_jar),
        "candidate_rows": candidate_rows,
        "collision_plan": collision_plan_rows,
    }
    report: dict[str, Any] = {
        "schema_version": 1,
        "kind": "dependency_namespace_collision_proof",
        "proof_id": (
            "NSCOLLISION_"
            + _stable_digest(material)[:20].upper()
        ),
        "class_recovery_plan_id": private_plan.get("plan_id"),
        "readable_jar_sha256": material["readable_jar_sha256"],
        "summary": {
            "readable_class_count": len(classes),
            "global_collision_node_count": len(collision_nodes),
            "candidate_count": len(candidate_rows),
            "collision_proven_candidate_count": candidate_proven_count,
            "collision_unproven_candidate_count": (
                len(candidate_rows) - candidate_proven_count
            ),
            "candidate_collision_node_count": len(
                candidate_collision_nodes
            ),
            "candidate_collision_depths": {
                str(key): value
                for key, value in sorted(collision_depths.items())
            },
            "candidate_collision_impacted_descendant_sum": (
                impacted_descendant_count
            ),
            "planned_colliding_class_rename_count": len(
                collision_plan_rows
            ),
            "planned_binary_class_rename_count": len(
                aggregate_rename_map
            ),
            "planned_nested_binary_class_rename_count": sum(
                max(0, row["rename_family_class_count"] - 1)
                for row in collision_plan_rows
            ),
            "rename_destination_conflict_count": len(
                destination_conflicts
            ),
            "simulated_candidate_collision_count": (
                simulated_candidate_collision_count
            ),
            "simulated_new_collision_node_count": len(
                newly_created_collision_nodes
            ),
            "remap_plan_topology_safe": (
                not destination_conflicts
                and simulated_candidate_collision_count == 0
                and not newly_created_collision_nodes
            ),
        },
        "candidates": candidate_rows,
        "collision_plan": collision_plan_rows,
        "identifiers_included": include_identifiers,
    }

    if include_identifiers:
        report["candidates"] = private_rows
        report["collision_plan"] = private_plan_rows

    return report


def write_namespace_collision_proof(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
