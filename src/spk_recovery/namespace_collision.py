from __future__ import annotations

from collections import Counter, defaultdict
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


def _class_names(readable_jar: Path) -> set[str]:
    names: set[str] = set()
    with zipfile.ZipFile(readable_jar) as z:
        for info in z.infolist():
            if info.is_dir() or not info.filename.endswith(".class"):
                continue
            internal = info.filename[:-6]
            if internal == "module-info":
                continue
            names.add(internal)
    return names


def _package_prefixes(internal: str) -> list[str]:
    parts = internal.split("/")
    if len(parts) <= 1:
        return []
    package_parts = parts[:-1]
    return [
        "/".join(package_parts[:index])
        for index in range(1, len(package_parts) + 1)
    ]


def _collisions_for_class(
    internal: str,
    class_names: set[str],
) -> list[str]:
    return [
        prefix
        for prefix in _package_prefixes(internal)
        if prefix in class_names
    ]


def analyze_namespace_collisions(
    readable_jar: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    readable_jar = readable_jar.resolve()
    if not readable_jar.is_file():
        raise NamespaceCollisionError(
            "readable JAR does not exist"
        )

    class_names = _class_names(readable_jar)

    affected: dict[str, list[str]] = {}
    reverse: dict[str, set[str]] = defaultdict(set)

    for internal in sorted(class_names):
        blockers = _collisions_for_class(internal, class_names)
        if not blockers:
            continue
        affected[internal] = blockers
        for blocker in blockers:
            reverse[blocker].add(internal)

    # Connected components across target classes and blocker classes.
    adjacency: dict[str, set[str]] = defaultdict(set)
    for target, blockers in affected.items():
        for blocker in blockers:
            adjacency[target].add(blocker)
            adjacency[blocker].add(target)

    components: list[list[str]] = []
    seen: set[str] = set()
    for node in sorted(adjacency):
        if node in seen:
            continue
        stack = [node]
        component: set[str] = set()
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component.add(current)
            stack.extend(
                sorted(adjacency.get(current, set()) - seen)
            )
        components.append(sorted(component))

    component_id_by_node: dict[str, str] = {}
    component_rows: list[dict[str, Any]] = []
    for index, component in enumerate(
        sorted(components, key=lambda row: (len(row), row)),
        start=1,
    ):
        component_id = f"JNSCOLLISION_{index:03d}"
        for node in component:
            component_id_by_node[node] = component_id

        target_count = sum(1 for node in component if node in affected)
        blocker_count = sum(1 for node in component if node in reverse)
        edge_count = sum(
            1
            for node in component
            for blocker in affected.get(node, [])
            if blocker in component
        )
        component_rows.append(
            {
                "component_id": component_id,
                "node_count": len(component),
                "target_count": target_count,
                "blocker_count": blocker_count,
                "edge_count": edge_count,
            }
        )

    depth_counts = Counter()
    blocker_frequency = Counter()
    public_targets: list[dict[str, Any]] = []

    ordered_targets = sorted(
        affected.items(),
        key=lambda item: (
            -len(item[1]),
            item[0],
        ),
    )
    for index, (target, blockers) in enumerate(
        ordered_targets,
        start=1,
    ):
        depths = [
            blocker.count("/") + 1
            for blocker in blockers
        ]
        for depth in depths:
            depth_counts[str(depth)] += 1
        for blocker in blockers:
            blocker_frequency[blocker] += 1

        row = {
            "target_id": f"JNSTARGET_{index:04d}",
            "component_id": component_id_by_node[target],
            "blocking_prefix_count": len(blockers),
            "shallowest_blocking_depth": min(depths),
            "deepest_blocking_depth": max(depths),
            "source_addressability": (
                "blocked_by_class_package_prefix"
            ),
        }
        if include_identifiers:
            row.update(
                {
                    "target_internal_name": target,
                    "blocking_class_prefixes": blockers,
                }
            )
        public_targets.append(row)

    blocker_rows: list[dict[str, Any]] = []
    for index, (blocker, count) in enumerate(
        sorted(
            blocker_frequency.items(),
            key=lambda item: (-item[1], item[0]),
        ),
        start=1,
    ):
        row = {
            "blocker_id": f"JNSBLOCKER_{index:04d}",
            "affected_target_count": count,
            "component_id": component_id_by_node[blocker],
            "blocker_depth": blocker.count("/") + 1,
        }
        if include_identifiers:
            row["blocker_internal_name"] = blocker
        blocker_rows.append(row)

    public_material = {
        "readable_jar_sha256": hashlib.sha256(
            readable_jar.read_bytes()
        ).hexdigest(),
        "class_count": len(class_names),
        "components": component_rows,
        "targets": [
            {
                key: row[key]
                for key in (
                    "target_id",
                    "component_id",
                    "blocking_prefix_count",
                    "shallowest_blocking_depth",
                    "deepest_blocking_depth",
                    "source_addressability",
                )
            }
            for row in public_targets
        ],
        "blockers": [
            {
                key: row[key]
                for key in (
                    "blocker_id",
                    "affected_target_count",
                    "component_id",
                    "blocker_depth",
                )
            }
            for row in blocker_rows
        ],
    }

    report: dict[str, Any] = {
        "schema_version": 1,
        "kind": "class_package_namespace_collision",
        "report_id": (
            "JNSCOLLISION_"
            + _stable_digest(public_material)[:20].upper()
        ),
        "readable_jar_sha256": public_material[
            "readable_jar_sha256"
        ],
        "summary": {
            "class_count": len(class_names),
            "affected_class_count": len(affected),
            "blocking_class_count": len(reverse),
            "collision_component_count": len(component_rows),
            "collision_edge_count": sum(
                len(blockers)
                for blockers in affected.values()
            ),
            "blocking_depth_counts": dict(
                sorted(depth_counts.items())
            ),
            "max_blocking_prefixes_per_target": max(
                (len(blockers) for blockers in affected.values()),
                default=0,
            ),
        },
        "components": component_rows,
        "targets": public_targets,
        "blockers": blocker_rows,
        "identifiers_included": include_identifiers,
    }
    return report


def write_namespace_collision_report(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
