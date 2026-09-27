from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .namespace_collision import (
    NamespaceCollisionError,
    _class_names,
    _collisions_for_class,
    _package_prefixes,
    analyze_namespace_collisions,
)


class NamespaceCollisionPlanError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _all_package_prefixes(class_names: set[str]) -> set[str]:
    prefixes: set[str] = set()
    for name in class_names:
        prefixes.update(_package_prefixes(name))
    return prefixes


def _safe_replacement_name(
    blocker: str,
    blocker_id: str,
    *,
    occupied_classes: set[str],
    occupied_packages: set[str],
) -> str:
    if "/" in blocker:
        parent = blocker.rsplit("/", 1)[0]
        base = parent + "/Recovered_" + blocker_id
    else:
        base = "Recovered_" + blocker_id

    candidate = base
    suffix = 1
    while (
        candidate in occupied_classes
        or candidate in occupied_packages
    ):
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def _simulate_remap(
    class_names: set[str],
    remaps: dict[str, str],
) -> set[str]:
    return {
        remaps.get(name, name)
        for name in class_names
    }


def build_namespace_collision_plan(
    readable_jar: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    readable_jar = readable_jar.resolve()
    try:
        collision = analyze_namespace_collisions(
            readable_jar,
            include_identifiers=True,
        )
    except NamespaceCollisionError as exc:
        raise NamespaceCollisionPlanError(str(exc)) from exc

    class_names = _class_names(readable_jar)
    package_prefixes = _all_package_prefixes(class_names)

    private_blockers = collision["blockers"]
    blocker_by_name = {
        row["blocker_internal_name"]: row
        for row in private_blockers
    }

    remaps: dict[str, str] = {}
    occupied_classes = set(class_names)
    occupied_packages = set(package_prefixes)

    for blocker, row in sorted(
        blocker_by_name.items(),
        key=lambda item: item[1]["blocker_id"],
    ):
        replacement = _safe_replacement_name(
            blocker,
            row["blocker_id"],
            occupied_classes=occupied_classes,
            occupied_packages=occupied_packages,
        )
        remaps[blocker] = replacement
        occupied_classes.add(replacement)

    simulated = _simulate_remap(class_names, remaps)
    remaining_collisions = {
        name: _collisions_for_class(name, simulated)
        for name in sorted(simulated)
    }
    remaining_collisions = {
        name: blockers
        for name, blockers in remaining_collisions.items()
        if blockers
    }

    if remaining_collisions:
        raise NamespaceCollisionPlanError(
            "candidate remap plan does not eliminate all namespace collisions"
        )

    public_rows: list[dict[str, Any]] = []
    for blocker, row in sorted(
        blocker_by_name.items(),
        key=lambda item: item[1]["blocker_id"],
    ):
        replacement = remaps[blocker]
        same_parent = (
            blocker.rsplit("/", 1)[0]
            if "/" in blocker
            else ""
        ) == (
            replacement.rsplit("/", 1)[0]
            if "/" in replacement
            else ""
        )
        plan_row = {
            "blocker_id": row["blocker_id"],
            "component_id": row["component_id"],
            "affected_target_count": row[
                "affected_target_count"
            ],
            "blocker_depth": row["blocker_depth"],
            "replacement_strategy": (
                "rename_class_preserve_parent_package"
                if same_parent
                else "rename_class_rehome_package"
            ),
            "replacement_parent_preserved": same_parent,
        }
        if include_identifiers:
            plan_row.update(
                {
                    "old_internal_name": blocker,
                    "new_internal_name": replacement,
                }
            )
        public_rows.append(plan_row)

    public_material = {
        "collision_report_id": collision["report_id"],
        "readable_jar_sha256": collision[
            "readable_jar_sha256"
        ],
        "remaps": [
            {
                key: row[key]
                for key in (
                    "blocker_id",
                    "component_id",
                    "affected_target_count",
                    "blocker_depth",
                    "replacement_strategy",
                    "replacement_parent_preserved",
                )
            }
            for row in public_rows
        ],
    }

    report = {
        "schema_version": 1,
        "kind": "class_package_namespace_collision_plan",
        "plan_id": (
            "JNSPLAN_"
            + _stable_digest(public_material)[:20].upper()
        ),
        "collision_report_id": collision["report_id"],
        "readable_jar_sha256": collision[
            "readable_jar_sha256"
        ],
        "summary": {
            "blocker_remap_count": len(public_rows),
            "affected_target_count": collision["summary"][
                "affected_class_count"
            ],
            "collision_component_count": collision["summary"][
                "collision_component_count"
            ],
            "pre_collision_edge_count": collision["summary"][
                "collision_edge_count"
            ],
            "post_collision_edge_count": 0,
            "parent_package_preserved_count": sum(
                bool(row["replacement_parent_preserved"])
                for row in public_rows
            ),
            "plan_eliminates_all_collisions": True,
        },
        "remaps": public_rows,
        "identifiers_included": include_identifiers,
    }
    return report


def write_namespace_collision_plan(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
