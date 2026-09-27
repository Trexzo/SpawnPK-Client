from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .package_class_collision import (
    PackageClassCollisionError,
    analyze_package_class_collisions,
)


class PackageClassRemapPlanError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _target_for(blocker: str) -> str:
    if "/" in blocker:
        package, _simple = blocker.rsplit("/", 1)
        prefix = package + "/"
    else:
        prefix = ""
    suffix = hashlib.sha256(
        blocker.encode("utf-8")
    ).hexdigest()[:12].upper()
    return prefix + "RecoveredCollision_" + suffix


def build_package_class_remap_plan(
    private_plan_path: Path,
    jar_path: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    topology = analyze_package_class_collisions(
        private_plan_path,
        jar_path,
        include_identifiers=True,
    )

    if topology["summary"]["colliding_candidate_count"] == 0:
        raise PackageClassRemapPlanError(
            "collision topology contains no colliding candidates"
        )

    existing_names = {
        str(row["candidate_internal_name"])
        for row in topology["candidates"]
    }
    existing_names.update(
        str(row["blocker_internal_name"])
        for row in topology["blockers"]
    )
    for row in topology["blockers"]:
        existing_names.update(
            str(name)
            for name in row.get("reference_holders", [])
        )

    private_rows: list[dict[str, Any]] = []
    public_rows: list[dict[str, Any]] = []

    for index, blocker in enumerate(
        topology["blockers"],
        start=1,
    ):
        old_name = str(blocker["blocker_internal_name"])
        new_name = _target_for(old_name)

        if new_name == old_name:
            raise PackageClassRemapPlanError(
                "remap target equals blocker identity"
            )
        if new_name in existing_names:
            raise PackageClassRemapPlanError(
                "deterministic remap target collides with known class"
            )

        old_package = (
            old_name.rsplit("/", 1)[0]
            if "/" in old_name
            else ""
        )
        new_package = (
            new_name.rsplit("/", 1)[0]
            if "/" in new_name
            else ""
        )
        same_package = old_package == new_package
        if not same_package:
            raise PackageClassRemapPlanError(
                "remap target must remain in blocker package"
            )

        public = {
            "remap_id": f"JCOLLISION_REMAP_{index:03d}",
            "blocker_id": blocker["blocker_id"],
            "affected_candidate_count": blocker[
                "affected_candidate_count"
            ],
            "bytecode_reference_holder_count": blocker[
                "direct_reference_holder_count"
            ],
            "same_package": same_package,
            "target_collision_free": True,
            "requires_class_identity_rewrite": True,
            "requires_reference_rewrite": (
                blocker["direct_reference_holder_count"] > 0
            ),
        }
        public_rows.append(public)

        private_rows.append(
            {
                **public,
                "old_internal_name": old_name,
                "new_internal_name": new_name,
                "affected_candidates": list(
                    blocker.get("affected_candidates", [])
                ),
                "bytecode_reference_holders": list(
                    blocker.get("reference_holders", [])
                ),
            }
        )

    holder_union = {
        holder
        for row in private_rows
        for holder in row["bytecode_reference_holders"]
    }

    material = {
        "collision_topology_id": topology[
            "collision_topology_id"
        ],
        "jar_sha256": topology["jar_sha256"],
        "remaps": public_rows,
    }

    report: dict[str, Any] = {
        "schema_version": 1,
        "kind": "package_class_collision_remap_plan",
        "remap_plan_id": (
            "JCOLLISIONREMAP_"
            + _stable_digest(material)[:20].upper()
        ),
        "collision_topology_id": topology[
            "collision_topology_id"
        ],
        "class_recovery_plan_id": topology[
            "class_recovery_plan_id"
        ],
        "jar_sha256": topology["jar_sha256"],
        "summary": {
            "remap_count": len(public_rows),
            "affected_candidate_count": topology[
                "summary"
            ]["colliding_candidate_count"],
            "bytecode_reference_holder_count": len(holder_union),
            "same_package_remap_count": sum(
                bool(row["same_package"])
                for row in public_rows
            ),
            "collision_free_target_count": sum(
                bool(row["target_collision_free"])
                for row in public_rows
            ),
            "reference_rewrite_remap_count": sum(
                bool(row["requires_reference_rewrite"])
                for row in public_rows
            ),
        },
        "remaps": (
            private_rows
            if include_identifiers
            else public_rows
        ),
        "identifiers_included": include_identifiers,
    }
    return report


def write_package_class_remap_plan(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
