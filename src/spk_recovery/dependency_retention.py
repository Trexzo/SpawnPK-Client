from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .bytecode_profile import (
    BytecodeProfileError,
    profile_class_constant_pool_references,
)
from .decompiler import sha256_file
from .dependency_artifact_proof import (
    DependencyArtifactProofError,
    _artifact_index,
)
from .dependency_remap_proof import (
    DependencyRemapProofError,
    _bundled_index,
    _class_mappings,
)


class DependencyRetentionError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_json(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRetentionError(
            f"invalid JSON authority: {path}"
        ) from exc
    if data.get("kind") != kind:
        raise DependencyRetentionError(
            f"{path}: expected kind {kind!r}, got {data.get('kind')!r}"
        )
    return data


def _normalized_prefixes(
    project_prefixes: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        prefix if prefix.endswith("/") else prefix + "/"
        for prefix in project_prefixes
    )


def _is_project(
    internal_name: str,
    project_prefixes: tuple[str, ...],
) -> bool:
    return any(
        internal_name.startswith(prefix)
        for prefix in project_prefixes
    )


def _class_profiles(
    jar_path: Path,
    class_names: set[str],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    try:
        with zipfile.ZipFile(jar_path) as archive:
            for name in sorted(class_names):
                entry = name + ".class"
                try:
                    data = archive.read(entry)
                except KeyError as exc:
                    raise DependencyRetentionError(
                        f"bundled class missing from exact JAR: {entry}"
                    ) from exc
                try:
                    result[name] = (
                        profile_class_constant_pool_references(data)
                    )
                except BytecodeProfileError as exc:
                    raise DependencyRetentionError(
                        f"{entry}: constant-pool profile failed: {exc}"
                    ) from exc
    except zipfile.BadZipFile as exc:
        raise DependencyRetentionError(
            f"invalid bundled JAR: {jar_path}"
        ) from exc
    return result


def _referenced_targets(
    profile: dict[str, Any],
) -> set[str]:
    targets = {
        str(name)
        for name in profile.get("class_references", [])
    }
    targets.update(
        str(row["owner"])
        for row in profile.get("member_references", [])
    )
    return targets


def _project_targets(
    profile: dict[str, Any],
    project_prefixes: tuple[str, ...],
) -> set[str]:
    return {
        target
        for target in _referenced_targets(profile)
        if _is_project(target, project_prefixes)
    }


def _artifact_sha_rows(
    artifacts: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    return sorted(
        (
            str(row["artifact"]),
            str(row["sha256"]),
        )
        for row in artifacts
    )


def _verify_remap_binding(
    *,
    remap: dict[str, Any],
    reference_surface: dict[str, Any],
    bundled_jar: Path,
    java_release: int,
    official_artifacts: list[dict[str, Any]],
) -> None:
    if remap.get("reference_surface_id") != reference_surface.get(
        "reference_surface_id"
    ):
        raise DependencyRetentionError(
            "dependency remap report is bound to a different DEPREF"
        )
    if remap.get("bundled_jar_sha256") != sha256_file(bundled_jar):
        raise DependencyRetentionError(
            "dependency remap report is bound to a different bundled JAR"
        )
    if int(remap.get("java_release", -1)) != java_release:
        raise DependencyRetentionError(
            "dependency remap report is bound to a different Java release"
        )
    if _artifact_sha_rows(
        list(remap.get("official_artifacts", []))
    ) != _artifact_sha_rows(official_artifacts):
        raise DependencyRetentionError(
            "dependency remap report official artifact SHA set disagrees"
        )


def classify_project_coupled_retention(
    reference_surface_path: Path,
    dependency_remap_report_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    java_release: int,
    project_prefixes: tuple[str, ...] = ("rs/", "tools/"),
    lineage_jar: Path | None = None,
) -> dict[str, Any]:
    reference_surface_path = reference_surface_path.resolve()
    dependency_remap_report_path = (
        dependency_remap_report_path.resolve()
    )
    bundled_jar = bundled_jar.resolve()
    lineage_jar = lineage_jar.resolve() if lineage_jar else None

    prefixes = _normalized_prefixes(project_prefixes)
    surface = _load_json(
        reference_surface_path,
        kind="project_non_project_reference_surface",
    )
    remap = _load_json(
        dependency_remap_report_path,
        kind="dependency_structural_remap_proof",
    )

    try:
        official, artifact_by_class, artifact_rows = _artifact_index(
            official_artifacts,
            java_release=java_release,
        )
        bundled = _bundled_index(
            bundled_jar,
            project_prefixes=prefixes,
        )
        accepted_mappings, _ = _class_mappings(
            bundled,
            official,
            artifact_by_class,
        )
    except (
        DependencyArtifactProofError,
        DependencyRemapProofError,
    ) as exc:
        raise DependencyRetentionError(str(exc)) from exc

    _verify_remap_binding(
        remap=remap,
        reference_surface=surface,
        bundled_jar=bundled_jar,
        java_release=java_release,
        official_artifacts=artifact_rows,
    )

    remap_by_key = {
        (
            str(row["kind"]),
            str(row["old_owner"]),
            str(row["old_name"]),
            str(row["old_descriptor"]),
        ): row
        for row in remap.get("member_results", [])
    }

    unresolved_owner_rows: dict[str, list[dict[str, Any]]] = {}
    for row in surface.get("member_references", []):
        key = (
            str(row["kind"]),
            str(row["owner"]),
            str(row["name"]),
            str(row["descriptor"]),
        )
        remap_row = remap_by_key.get(key)
        if remap_row is None:
            raise DependencyRetentionError(
                f"DEPREF row absent from DEPREMAP: {key!r}"
            )
        if remap_row.get("status") != "bundled_unresolved_class":
            continue
        owner = str(row["owner"])
        if owner in accepted_mappings:
            raise DependencyRetentionError(
                f"unresolved remap row has accepted official mapping: {owner}"
            )
        unresolved_owner_rows.setdefault(owner, []).append(row)

    profile_names = set(bundled)
    profiles = _class_profiles(bundled_jar, profile_names)

    coupled_seeds: set[str] = set()
    consumed_only: set[str] = set()
    reverse_project_targets: dict[str, list[str]] = {}
    for owner in sorted(unresolved_owner_rows):
        targets = sorted(
            _project_targets(profiles[owner], prefixes)
        )
        reverse_project_targets[owner] = targets
        if targets:
            coupled_seeds.add(owner)
        else:
            consumed_only.add(owner)

    retained: set[str] = set(coupled_seeds)
    closure_parent: dict[str, str] = {}
    queue = sorted(coupled_seeds)
    while queue:
        current = queue.pop(0)
        for target in sorted(_referenced_targets(profiles[current])):
            if _is_project(target, prefixes):
                continue
            if target not in bundled:
                continue
            if target in accepted_mappings:
                continue
            if target in retained:
                continue
            retained.add(target)
            closure_parent[target] = current
            queue.append(target)

    closure_only = retained - coupled_seeds
    classifications: dict[str, str] = {}
    for owner in sorted(coupled_seeds):
        classifications[owner] = "project_coupled_non_pom"
    for owner in sorted(consumed_only):
        if owner not in retained:
            classifications[owner] = "project_consumed_non_pom"
    for owner in sorted(closure_only):
        classifications[owner] = "source_retention_closure"

    lineage_equal: dict[str, bool] = {}
    lineage_sha = None
    if lineage_jar is not None:
        lineage_sha = sha256_file(lineage_jar)
        try:
            with zipfile.ZipFile(bundled_jar) as current_zip, zipfile.ZipFile(
                lineage_jar
            ) as lineage_zip:
                for owner in sorted(retained):
                    entry = owner + ".class"
                    try:
                        current_bytes = current_zip.read(entry)
                        lineage_bytes = lineage_zip.read(entry)
                    except KeyError:
                        lineage_equal[owner] = False
                    else:
                        lineage_equal[owner] = (
                            current_bytes == lineage_bytes
                        )
        except zipfile.BadZipFile as exc:
            raise DependencyRetentionError(
                f"invalid lineage JAR: {lineage_jar}"
            ) from exc

    class_rows: list[dict[str, Any]] = []
    for owner, status in sorted(classifications.items()):
        rows = unresolved_owner_rows.get(owner, [])
        class_rows.append(
            {
                "class": owner,
                "status": status,
                "project_to_class_unique_member_rows": len(rows),
                "project_to_class_weighted_references": sum(
                    int(row.get("reference_count", 0))
                    for row in rows
                ),
                "reverse_project_targets": (
                    reverse_project_targets.get(owner, [])
                ),
                "closure_parent": closure_parent.get(owner),
                "lineage_byte_identical": (
                    lineage_equal.get(owner)
                    if lineage_jar is not None
                    else None
                ),
                "proof": {
                    "official_mapping_absent": owner
                    not in accepted_mappings,
                    "strategy": (
                        "bidirectional_exact_jvm_reference"
                        if status == "project_coupled_non_pom"
                        else (
                            "exact_project_consumption_without_official_mapping"
                            if status == "project_consumed_non_pom"
                            else "exact_unmapped_retention_closure_edge"
                        )
                    ),
                },
            }
        )

    member_rows: list[dict[str, Any]] = []
    for owner, rows in sorted(unresolved_owner_rows.items()):
        status = classifications.get(owner)
        if status is None:
            continue
        for row in rows:
            member_rows.append(
                {
                    "kind": str(row["kind"]),
                    "owner": owner,
                    "name": str(row["name"]),
                    "descriptor": str(row["descriptor"]),
                    "reference_count": int(
                        row.get("reference_count", 0)
                    ),
                    "retention_status": status,
                }
            )

    retained_weighted = sum(
        int(row["reference_count"])
        for row in member_rows
        if row["retention_status"]
        in {
            "project_coupled_non_pom",
            "source_retention_closure",
        }
    )
    consumed_weighted = sum(
        int(row["reference_count"])
        for row in member_rows
        if row["retention_status"] == "project_consumed_non_pom"
    )
    prior_unresolved_weighted = sum(
        int(row.get("reference_count", 0))
        for row in remap.get("member_results", [])
        if row.get("status") == "bundled_unresolved_class"
    )

    material = {
        "bundled_jar_sha256": sha256_file(bundled_jar),
        "reference_surface_id": surface["reference_surface_id"],
        "dependency_remap_proof_id": remap[
            "dependency_remap_proof_id"
        ],
        "java_release": java_release,
        "project_prefixes": list(prefixes),
        "official_artifacts": artifact_rows,
        "lineage_jar_sha256": lineage_sha,
        "classifications": class_rows,
        "member_reclassifications": member_rows,
    }
    return {
        "schema_version": 1,
        "kind": "dependency_source_retention_classification",
        "retention_report_id": (
            "DEPRETAIN_" + _stable_digest(material)[:20].upper()
        ),
        **material,
        "summary": {
            "project_coupled_class_count": sum(
                row["status"] == "project_coupled_non_pom"
                for row in class_rows
            ),
            "project_consumed_class_count": sum(
                row["status"] == "project_consumed_non_pom"
                for row in class_rows
            ),
            "source_retention_closure_class_count": sum(
                row["status"] == "source_retention_closure"
                for row in class_rows
            ),
            "retained_weighted_reference_count": retained_weighted,
            "project_consumed_weighted_reference_count": consumed_weighted,
            "prior_bundled_unresolved_weighted_reference_count": (
                prior_unresolved_weighted
            ),
            "remaining_dependency_uncertainty_weighted_reference_count": (
                prior_unresolved_weighted
                - retained_weighted
                - consumed_weighted
            ),
            "lineage_byte_identical_retained_class_count": (
                sum(lineage_equal.values())
                if lineage_jar is not None
                else None
            ),
        },
        "classifications": class_rows,
        "member_reclassifications": member_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify unresolved bundled dependency owners that must be "
            "retained/recovered with the project rather than substituted."
        )
    )
    parser.add_argument("reference_surface", type=Path)
    parser.add_argument("dependency_remap_report", type=Path)
    parser.add_argument("bundled_jar", type=Path)
    parser.add_argument("artifact", type=Path, nargs="+")
    parser.add_argument("--java-release", type=int, required=True)
    parser.add_argument("--lineage-jar", type=Path)
    parser.add_argument(
        "--project-prefix",
        action="append",
        default=None,
    )
    args = parser.parse_args()

    report = classify_project_coupled_retention(
        args.reference_surface,
        args.dependency_remap_report,
        args.bundled_jar,
        args.artifact,
        java_release=args.java_release,
        project_prefixes=tuple(
            args.project_prefix or ["rs/", "tools/"]
        ),
        lineage_jar=args.lineage_jar,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
