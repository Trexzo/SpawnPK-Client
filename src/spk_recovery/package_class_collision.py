from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any
import zipfile

from .bytecode_profile import (
    BytecodeProfileError,
    profile_class_constant_pool_references,
)
from .classfile import ClassFormatError, parse_class


class PackageClassCollisionError(ValueError):
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
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _proper_package_prefixes(internal_name: str) -> list[str]:
    parts = internal_name.split("/")
    return [
        "/".join(parts[:index])
        for index in range(1, len(parts))
    ]


_OBJECT_DESCRIPTOR_RE = re.compile(r"L([^;]+);")


def _descriptor_references(descriptor: str) -> set[str]:
    return {
        match.group(1)
        for match in _OBJECT_DESCRIPTOR_RE.finditer(descriptor)
    }


def _declared_type_references(data: bytes) -> set[str]:
    try:
        parsed = parse_class(data)
    except ClassFormatError as exc:
        raise PackageClassCollisionError(
            f"class parse failed: {exc}"
        ) from exc

    refs: set[str] = set(parsed.interfaces)
    if parsed.super_name is not None:
        refs.add(parsed.super_name)

    for field in parsed.fields:
        refs.update(
            _descriptor_references(str(field["descriptor"]))
        )

    for method in parsed.methods:
        refs.update(
            _descriptor_references(str(method["descriptor"]))
        )

    return refs


def _jar_profiles(
    jar_path: Path,
) -> tuple[set[str], dict[str, dict[str, Any]]]:
    names: set[str] = set()
    profiles: dict[str, dict[str, Any]] = {}

    try:
        with zipfile.ZipFile(jar_path) as archive:
            entries = sorted(
                name
                for name in archive.namelist()
                if name.endswith(".class")
                and name != "module-info.class"
                and not name.startswith("META-INF/versions/")
            )
            for entry in entries:
                internal = entry[:-6]
                data = archive.read(entry)
                try:
                    profile = profile_class_constant_pool_references(data)
                    profile["declared_type_references"] = sorted(
                        _declared_type_references(data)
                    )
                except (
                    BytecodeProfileError,
                    PackageClassCollisionError,
                ) as exc:
                    raise PackageClassCollisionError(
                        f"{entry}: class reference profile failed: {exc}"
                    ) from exc

                if profile.get("internal_name") != internal:
                    raise PackageClassCollisionError(
                        f"{entry}: class identity mismatch"
                    )
                names.add(internal)
                profiles[internal] = profile
    except zipfile.BadZipFile as exc:
        raise PackageClassCollisionError(
            f"invalid JAR/ZIP: {jar_path}"
        ) from exc

    return names, profiles


def _load_private_plan(path: Path) -> dict[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageClassCollisionError(
            f"invalid private plan: {path}"
        ) from exc

    if (
        plan.get("kind") != "javac_missing_class_recovery_plan"
        or plan.get("identifiers_included") is not True
    ):
        raise PackageClassCollisionError(
            "requires identifier-bearing javac class recovery plan"
        )
    return plan


def _candidate_names(plan: dict[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for row in plan.get("candidates", []):
        candidate_id = row.get("candidate_id")
        internal = row.get("candidate_internal_name")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise PackageClassCollisionError(
                "private candidate lacks candidate_id"
            )
        if not isinstance(internal, str) or not internal:
            raise PackageClassCollisionError(
                "private candidate lacks internal name"
            )
        rows.append((candidate_id, internal))
    return rows


def analyze_package_class_collisions(
    private_plan_path: Path,
    jar_path: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    private_plan_path = private_plan_path.resolve()
    jar_path = jar_path.resolve()

    plan = _load_private_plan(private_plan_path)
    names, profiles = _jar_profiles(jar_path)
    candidates = _candidate_names(plan)

    missing = sorted(
        internal
        for _candidate_id, internal in candidates
        if internal not in names
    )
    if missing:
        raise PackageClassCollisionError(
            "candidate classes missing from JAR"
        )

    collisions: list[dict[str, Any]] = []
    blocker_to_candidates: dict[str, set[str]] = defaultdict(set)

    for candidate_id, internal in candidates:
        blockers = [
            prefix
            for prefix in _proper_package_prefixes(internal)
            if prefix in names
        ]

        for blocker in blockers:
            blocker_to_candidates[blocker].add(internal)

        collisions.append(
            {
                "candidate_id": candidate_id,
                "package_depth": internal.count("/"),
                "blocking_prefix_count": len(blockers),
                "collision_depths": [
                    blocker.count("/") + 1
                    for blocker in blockers
                ],
                "_candidate_internal_name": internal,
                "_blockers": blockers,
            }
        )

    referenced_by: dict[str, set[str]] = defaultdict(set)
    for holder, profile in profiles.items():
        targets = {
            str(name)
            for name in profile.get("class_references", [])
        }
        targets.update(
            str(row["owner"])
            for row in profile.get("member_references", [])
        )
        targets.update(
            str(name)
            for name in profile.get(
                "declared_type_references",
                [],
            )
        )
        for target in targets:
            if holder == target:
                continue
            referenced_by[target].add(holder)

    blocker_rows: list[dict[str, Any]] = []
    for blocker, affected in sorted(blocker_to_candidates.items()):
        holders = referenced_by.get(blocker, set())
        blocker_rows.append(
            {
                "affected_candidate_count": len(affected),
                "direct_reference_holder_count": len(holders),
                "self_referenced": blocker in holders,
                "_blocker_internal_name": blocker,
                "_affected_candidates": sorted(affected),
                "_reference_holders": sorted(holders),
            }
        )

    # Connected components are defined by shared blockers/candidates.
    candidate_to_blockers = {
        row["_candidate_internal_name"]: set(row["_blockers"])
        for row in collisions
        if row["_blockers"]
    }
    components: list[dict[str, Any]] = []
    unseen = set(candidate_to_blockers)

    while unseen:
        seed = min(unseen)
        component_candidates: set[str] = set()
        component_blockers: set[str] = set()
        frontier = {seed}

        while frontier:
            current = frontier.pop()
            if current in component_candidates:
                continue
            component_candidates.add(current)
            unseen.discard(current)

            for blocker in candidate_to_blockers.get(current, set()):
                if blocker in component_blockers:
                    continue
                component_blockers.add(blocker)
                frontier.update(blocker_to_candidates.get(blocker, set()))

        holders: set[str] = set()
        for blocker in component_blockers:
            holders.update(referenced_by.get(blocker, set()))

        components.append(
            {
                "candidate_count": len(component_candidates),
                "blocker_count": len(component_blockers),
                "direct_reference_holder_count": len(holders),
                "_candidates": sorted(component_candidates),
                "_blockers": sorted(component_blockers),
                "_holders": sorted(holders),
            }
        )

    components.sort(
        key=lambda row: (
            -row["candidate_count"],
            -row["blocker_count"],
            row["_candidates"],
        )
    )

    public_components = []
    for index, row in enumerate(components, start=1):
        public_components.append(
            {
                "component_id": f"JCOLLISION_{index:03d}",
                "candidate_count": row["candidate_count"],
                "blocker_count": row["blocker_count"],
                "direct_reference_holder_count": row[
                    "direct_reference_holder_count"
                ],
            }
        )

    public_blockers = []
    for index, row in enumerate(
        sorted(
            blocker_rows,
            key=lambda item: (
                -item["affected_candidate_count"],
                item["_blocker_internal_name"],
            ),
        ),
        start=1,
    ):
        public_blockers.append(
            {
                "blocker_id": f"JCOLLISION_BLOCKER_{index:03d}",
                "affected_candidate_count": row[
                    "affected_candidate_count"
                ],
                "direct_reference_holder_count": row[
                    "direct_reference_holder_count"
                ],
                "self_referenced": row["self_referenced"],
            }
        )

    collision_count = sum(
        row["blocking_prefix_count"] > 0
        for row in collisions
    )
    collision_edge_count = sum(
        row["blocking_prefix_count"]
        for row in collisions
    )
    package_depths = Counter(
        str(row["package_depth"]) for row in collisions
    )
    blocker_counts = Counter(
        str(row["blocking_prefix_count"]) for row in collisions
    )

    public_candidates = [
        {
            key: row[key]
            for key in (
                "candidate_id",
                "package_depth",
                "blocking_prefix_count",
                "collision_depths",
            )
        }
        for row in collisions
    ]

    material = {
        "class_recovery_plan_id": plan.get("plan_id"),
        "jar_sha256": _sha256_file(jar_path),
        "candidates": public_candidates,
        "blockers": public_blockers,
        "components": public_components,
    }

    report: dict[str, Any] = {
        "schema_version": 1,
        "kind": "package_class_collision_topology",
        "collision_topology_id": (
            "JCOLLISION_"
            + _stable_digest(material)[:20].upper()
        ),
        "class_recovery_plan_id": plan.get("plan_id"),
        "jar_sha256": material["jar_sha256"],
        "summary": {
            "candidate_count": len(collisions),
            "colliding_candidate_count": collision_count,
            "non_colliding_candidate_count": (
                len(collisions) - collision_count
            ),
            "collision_edge_count": collision_edge_count,
            "unique_blocker_count": len(blocker_to_candidates),
            "component_count": len(components),
            "package_depths": dict(sorted(package_depths.items())),
            "blocking_prefix_counts": dict(
                sorted(blocker_counts.items())
            ),
            "direct_reference_holder_count": len(
                {
                    holder
                    for row in blocker_rows
                    for holder in row["_reference_holders"]
                }
            ),
        },
        "candidates": public_candidates,
        "blockers": public_blockers,
        "components": public_components,
        "identifiers_included": include_identifiers,
    }

    if include_identifiers:
        blocker_id_by_name = {
            row["_blocker_internal_name"]: public["blocker_id"]
            for row, public in zip(
                sorted(
                    blocker_rows,
                    key=lambda item: (
                        -item["affected_candidate_count"],
                        item["_blocker_internal_name"],
                    ),
                ),
                public_blockers,
            )
        }
        component_id_by_candidate: dict[str, str] = {}
        for public, private in zip(public_components, components):
            for candidate in private["_candidates"]:
                component_id_by_candidate[candidate] = public[
                    "component_id"
                ]

        report["candidates"] = [
            {
                **public,
                "candidate_internal_name": private[
                    "_candidate_internal_name"
                ],
                "blocking_prefixes": private["_blockers"],
                "component_id": component_id_by_candidate.get(
                    private["_candidate_internal_name"]
                ),
            }
            for public, private in zip(
                public_candidates,
                collisions,
            )
        ]

        ordered_blockers = sorted(
            blocker_rows,
            key=lambda item: (
                -item["affected_candidate_count"],
                item["_blocker_internal_name"],
            ),
        )
        report["blockers"] = [
            {
                **public,
                "blocker_internal_name": private[
                    "_blocker_internal_name"
                ],
                "affected_candidates": private[
                    "_affected_candidates"
                ],
                "reference_holders": private[
                    "_reference_holders"
                ],
            }
            for public, private in zip(
                public_blockers,
                ordered_blockers,
            )
        ]

        report["components"] = [
            {
                **public,
                "candidates": private["_candidates"],
                "blockers": private["_blockers"],
                "reference_holders": private["_holders"],
            }
            for public, private in zip(
                public_components,
                components,
            )
        ]

    return report


def write_package_class_collision_report(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
