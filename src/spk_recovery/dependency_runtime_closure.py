from __future__ import annotations

from collections import Counter, deque
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
from .dependency_artifact_proof import (
    DependencyArtifactProofError,
    _artifact_index,
)
from .dependency_runtime_frontier import (
    DependencyRuntimeFrontierError,
    _artifact_rows_key,
    _load_private_plan,
    _normalize_prefixes,
)


class DependencyRuntimeClosureError(ValueError):
    pass


_DESCRIPTOR_OBJECT_RE = re.compile(r"L([^;]+);")
_NATIVE_SUFFIXES = (
    ".dll",
    ".so",
    ".dylib",
    ".jnilib",
)
_PLATFORM_PREFIXES = (
    "java/",
    "jdk/",
    "sun/",
)


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_frontier(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRuntimeClosureError(
            "invalid runtime frontier authority"
        ) from exc
    if data.get("kind") != "dependency_runtime_frontier":
        raise DependencyRuntimeClosureError(
            "unexpected runtime frontier kind"
        )
    return data


def _descriptor_types(descriptor: str) -> set[str]:
    return set(_DESCRIPTOR_OBJECT_RE.findall(descriptor))


def _profile_references(data: bytes) -> set[str]:
    try:
        profile = profile_class_constant_pool_references(data)
    except BytecodeProfileError as exc:
        raise DependencyRuntimeClosureError(
            f"dependency bytecode profile failed: {exc}"
        ) from exc

    refs = {
        str(value)
        for value in profile.get("class_references", [])
        if isinstance(value, str) and value
    }
    for row in profile.get("member_references", []):
        if not isinstance(row, dict):
            continue
        owner = row.get("owner")
        if isinstance(owner, str) and owner and not owner.startswith("["):
            refs.add(owner)
        descriptor = row.get("descriptor")
        if isinstance(descriptor, str):
            refs.update(_descriptor_types(descriptor))
    refs.discard(str(profile.get("internal_name", "")))
    return refs


def _official_authority(
    plan: dict[str, Any],
    official_artifacts: list[Path],
) -> tuple[
    dict[str, str],
    dict[str, Path],
    list[dict[str, Any]],
]:
    release = plan.get("java_release")
    if (
        not isinstance(release, int)
        or isinstance(release, bool)
        or release < 1
    ):
        raise DependencyRuntimeClosureError(
            "private DEPREPLACE has invalid java_release"
        )

    resolved = [path.resolve() for path in official_artifacts]
    try:
        _classes, owner_artifact, rows = _artifact_index(
            resolved,
            java_release=release,
        )
    except DependencyArtifactProofError as exc:
        raise DependencyRuntimeClosureError(str(exc)) from exc

    expected = plan.get("official_artifacts")
    if not isinstance(expected, list):
        raise DependencyRuntimeClosureError(
            "private DEPREPLACE lacks official artifact authority"
        )
    if _artifact_rows_key(expected) != _artifact_rows_key(rows):
        raise DependencyRuntimeClosureError(
            "official artifact authority differs from DEPREPLACE"
        )

    by_name: dict[str, Path] = {}
    for path in resolved:
        if path.name in by_name:
            raise DependencyRuntimeClosureError(
                f"duplicate official artifact basename: {path.name}"
            )
        by_name[path.name] = path
    return owner_artifact, by_name, rows


def _resource_inventory(
    artifact_names: set[str],
    artifact_paths: dict[str, Path],
    *,
    include_identifiers: bool,
) -> dict[str, Any]:
    artifact_rows: list[dict[str, Any]] = []
    total_resource_count = 0
    total_resource_bytes = 0
    service_count = 0
    native_count = 0

    for artifact_id, name in enumerate(
        sorted(artifact_names),
        start=1,
    ):
        path = artifact_paths.get(name)
        if path is None:
            raise DependencyRuntimeClosureError(
                f"used official artifact was not supplied: {name}"
            )

        resources: list[dict[str, Any]] = []
        try:
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    if info.is_dir() or info.filename.endswith(".class"):
                        continue
                    entry = info.filename
                    is_service = entry.startswith("META-INF/services/")
                    lowered = entry.lower()
                    is_native = (
                        lowered.endswith(_NATIVE_SUFFIXES)
                        or "/natives/" in lowered
                        or lowered.startswith("natives/")
                        or lowered.startswith("meta-inf/native/")
                    )
                    resources.append(
                        {
                            "entry": entry,
                            "bytes": info.file_size,
                            "service": is_service,
                            "native": is_native,
                        }
                    )
        except zipfile.BadZipFile as exc:
            raise DependencyRuntimeClosureError(
                f"invalid official artifact JAR: {path}"
            ) from exc

        resource_bytes = sum(int(row["bytes"]) for row in resources)
        services = sum(1 for row in resources if row["service"])
        natives = sum(1 for row in resources if row["native"])
        total_resource_count += len(resources)
        total_resource_bytes += resource_bytes
        service_count += services
        native_count += natives

        public = {
            "artifact_id": f"DEPCLOSUREARTIFACT_{artifact_id:04d}",
            "resource_entry_count": len(resources),
            "resource_bytes": resource_bytes,
            "service_entry_count": services,
            "native_entry_count": natives,
        }
        if include_identifiers:
            public["artifact"] = name
            public["resource_entries"] = resources
        artifact_rows.append(public)

    return {
        "artifact_count": len(artifact_rows),
        "resource_entry_count": total_resource_count,
        "resource_bytes": total_resource_bytes,
        "service_entry_count": service_count,
        "native_entry_count": native_count,
        "artifacts": artifact_rows,
    }


def build_dependency_runtime_closure(
    private_replacement_plan_path: Path,
    runtime_frontier_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    private_replacement_plan_path = (
        private_replacement_plan_path.resolve()
    )
    runtime_frontier_path = runtime_frontier_path.resolve()
    bundled_jar = bundled_jar.resolve()

    try:
        plan = _load_private_plan(private_replacement_plan_path)
    except DependencyRuntimeFrontierError as exc:
        raise DependencyRuntimeClosureError(str(exc)) from exc
    frontier = _load_frontier(runtime_frontier_path)
    prefixes = _normalize_prefixes(plan.get("project_prefixes"))

    bundled_sha = _sha256_file(bundled_jar)
    if str(plan.get("bundled_jar_sha256", "")).lower() != bundled_sha:
        raise DependencyRuntimeClosureError(
            "bundled/readable JAR SHA differs from DEPREPLACE"
        )
    if frontier.get("bundled_jar_sha256") != bundled_sha:
        raise DependencyRuntimeClosureError(
            "runtime frontier is bound to a different bundled JAR"
        )
    if frontier.get("replacement_plan_id") != plan.get(
        "replacement_plan_id"
    ):
        raise DependencyRuntimeClosureError(
            "runtime frontier is bound to a different DEPREPLACE"
        )

    owner_artifact, artifact_paths, artifact_rows = _official_authority(
        plan,
        official_artifacts,
    )
    artifact_sha = sorted(str(row["sha256"]).lower() for row in artifact_rows)
    if sorted(frontier.get("official_artifact_sha256", [])) != artifact_sha:
        raise DependencyRuntimeClosureError(
            "runtime frontier official artifact authority drifted"
        )

    owner_rows_raw = plan.get("owners")
    if not isinstance(owner_rows_raw, list):
        raise DependencyRuntimeClosureError(
            "private DEPREPLACE lacks owner rows"
        )
    owner_rows = {
        str(row["old_owner"]): row
        for row in owner_rows_raw
        if isinstance(row, dict)
        and isinstance(row.get("old_owner"), str)
    }

    frontier_rows = frontier.get("owners")
    if not isinstance(frontier_rows, list):
        raise DependencyRuntimeClosureError(
            "runtime frontier lacks owner rows"
        )
    frontier_by_id = {
        str(row["owner_id"]): row
        for row in frontier_rows
        if isinstance(row, dict)
        and isinstance(row.get("owner_id"), str)
    }

    roots: list[str] = []
    for old_owner, row in owner_rows.items():
        if row.get("classification") != "official_replaceable":
            continue
        owner_id = row.get("owner_id")
        public = frontier_by_id.get(str(owner_id))
        if public is None:
            raise DependencyRuntimeClosureError(
                "DEPREPLACE owner missing from runtime frontier"
            )
        if public.get("classification") != "official_replaceable":
            raise DependencyRuntimeClosureError(
                "runtime frontier classification drifted"
            )
        if public.get("bundled_class_entry_present") is True:
            roots.append(old_owner)

    try:
        with zipfile.ZipFile(bundled_jar) as archive:
            class_entries = {
                info.filename[:-6]: info.filename
                for info in archive.infolist()
                if not info.is_dir()
                and info.filename.endswith(".class")
                and not info.filename.startswith("META-INF/versions/")
            }

            queue = deque(sorted(set(roots)))
            visited: set[str] = set()
            edge_rows: list[dict[str, Any]] = []
            reachable: set[str] = set(roots)

            while queue:
                source = queue.popleft()
                if source in visited:
                    continue
                visited.add(source)
                entry = class_entries.get(source)
                if entry is None:
                    raise DependencyRuntimeClosureError(
                        f"closure source missing bundled class entry: {source}"
                    )
                refs = _profile_references(archive.read(entry))
                for target in sorted(refs):
                    reachable.add(target)
                    edge_rows.append(
                        {"source": source, "target": target}
                    )
                    target_plan_row = owner_rows.get(target)
                    if (
                        target in class_entries
                        and target not in visited
                        and not any(
                            target.startswith(prefix)
                            for prefix in prefixes
                        )
                        and target_plan_row is not None
                        and target_plan_row.get("classification")
                        == "official_replaceable"
                    ):
                        queue.append(target)
    except zipfile.BadZipFile as exc:
        raise DependencyRuntimeClosureError(
            "invalid bundled/readable JAR"
        ) from exc

    status_rows: list[dict[str, Any]] = []
    used_artifacts: set[str] = set()
    blocker_count = 0

    for owner in sorted(reachable):
        plan_row = owner_rows.get(owner)
        official_target: str | None = None
        artifact_name: str | None = None

        if any(owner.startswith(prefix) for prefix in prefixes):
            status = "project_retained"
            reason = "project_prefix"
        elif plan_row is not None:
            classification = plan_row.get("classification")
            if classification == "official_replaceable":
                status = "official_closure_mapped"
                reason = "accepted_depreplace"
                official_target = plan_row.get("new_owner")
                artifact_name = plan_row.get("artifact")
                if (
                    not isinstance(official_target, str)
                    or not official_target
                    or not isinstance(artifact_name, str)
                    or owner_artifact.get(official_target)
                    != artifact_name
                ):
                    raise DependencyRuntimeClosureError(
                        "official closure target disagrees with artifact authority"
                    )
                used_artifacts.add(artifact_name)
            elif classification == "residual_bundled":
                status = "residual_bundled"
                reason = "accepted_depreplace"
            elif classification == "project_retained":
                status = "project_retained"
                reason = "accepted_depreplace"
            elif classification == "platform_runtime":
                status = "platform_runtime"
                reason = "accepted_depreplace"
            else:
                status = "unresolved"
                reason = "unsupported_depreplace_classification"
        elif owner in class_entries:
            status = "unresolved"
            reason = "bundled_owner_without_depreplace_authority"
        elif owner.startswith(_PLATFORM_PREFIXES):
            status = "platform_runtime"
            reason = "platform_namespace"
        else:
            status = "unresolved"
            reason = "non_bundled_owner_without_depreplace_authority"

        if status in {
            "residual_bundled",
            "project_retained",
            "unresolved",
        }:
            blocker_count += 1

        row = {
            "closure_owner_id": (
                "DEPCLOSUREOWNER_"
                + hashlib.sha256(owner.encode("utf-8")).hexdigest()[:16].upper()
            ),
            "status": status,
            "reason": reason,
            "bundled_class_present": owner in class_entries,
            "official_target_present": (
                owner_artifact.get(official_target) == artifact_name
                if official_target is not None
                and artifact_name is not None
                else None
            ),
        }
        if include_identifiers:
            row["owner"] = owner
            row["official_target"] = official_target
            row["artifact"] = artifact_name
        status_rows.append(row)

    status_counts = Counter(row["status"] for row in status_rows)
    resources = _resource_inventory(
        used_artifacts,
        artifact_paths,
        include_identifiers=include_identifiers,
    )

    edge_public = [
        {
            "source_id": (
                "DEPCLOSUREOWNER_"
                + hashlib.sha256(row["source"].encode("utf-8"))
                .hexdigest()[:16].upper()
            ),
            "target_id": (
                "DEPCLOSUREOWNER_"
                + hashlib.sha256(row["target"].encode("utf-8"))
                .hexdigest()[:16].upper()
            ),
            **(
                {
                    "source": row["source"],
                    "target": row["target"],
                }
                if include_identifiers
                else {}
            ),
        }
        for row in sorted(
            edge_rows,
            key=lambda value: (value["source"], value["target"]),
        )
    ]

    resource_or_native_blocker = (
        resources["service_entry_count"] > 0
        or resources["native_entry_count"] > 0
        or resources["resource_entry_count"] > 0
    )
    reflection_dynamic_loading_unproven = True
    runtime_ready = (
        blocker_count == 0
        and not resource_or_native_blocker
        and not reflection_dynamic_loading_unproven
    )

    material_owners = [
        {
            key: value
            for key, value in row.items()
            if key not in {"owner", "official_target", "artifact"}
        }
        for row in status_rows
    ]
    material_edges = [
        {
            key: value
            for key, value in row.items()
            if key not in {"source", "target"}
        }
        for row in edge_public
    ]
    material_resources = {
        **{
            key: value
            for key, value in resources.items()
            if key != "artifacts"
        },
        "artifacts": [
            {
                key: value
                for key, value in row.items()
                if key not in {"artifact", "resource_entries"}
            }
            for row in resources["artifacts"]
        ],
    }

    material = {
        "runtime_frontier_id": frontier.get("runtime_frontier_id"),
        "replacement_plan_id": plan.get("replacement_plan_id"),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": artifact_sha,
        "roots": sorted(
            hashlib.sha256(root.encode("utf-8")).hexdigest()
            for root in roots
        ),
        "owners": material_owners,
        "edges": material_edges,
        "resources": material_resources,
        "runtime_capsule_mutation_ready": runtime_ready,
        "reflection_dynamic_loading_unproven": (
            reflection_dynamic_loading_unproven
        ),
    }
    closure_id = (
        "DEPRUNTIMECLOSURE_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "dependency_runtime_closure",
        "runtime_closure_id": closure_id,
        "runtime_frontier_id": frontier.get("runtime_frontier_id"),
        "replacement_plan_id": plan.get("replacement_plan_id"),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": artifact_sha,
        "summary": {
            "root_count": len(set(roots)),
            "reachable_owner_count": len(status_rows),
            "edge_count": len(edge_public),
            "status_counts": dict(sorted(status_counts.items())),
            "class_closure_blocker_count": blocker_count,
            "used_official_artifact_count": len(used_artifacts),
            "resource_entry_count": resources["resource_entry_count"],
            "service_entry_count": resources["service_entry_count"],
            "native_entry_count": resources["native_entry_count"],
            "resource_equivalence_unproven": (
                resources["resource_entry_count"] > 0
            ),
            "reflection_dynamic_loading_unproven": True,
            "runtime_capsule_mutation_ready": runtime_ready,
        },
        "owners": status_rows,
        "edges": edge_public,
        "resources": resources,
        "identifiers_included": include_identifiers,
        "note": (
            "Bytecode closure is necessary but not sufficient for runtime "
            "dependency replacement. Resource/native equivalence and dynamic "
            "loading remain explicit fail-closed boundaries."
        ),
    }


def write_dependency_runtime_closure(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
