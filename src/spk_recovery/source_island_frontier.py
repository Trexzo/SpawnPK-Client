"""Read-only source-island frontier against one exact original Java client JAR.

Reports explicitly dependency-closed original project classes adjacent to the
selected, independently rebuilt classes. It does not copy game code, assume
identity across releases, decompile, or label a candidate source-recovered.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any
import zipfile

from .source_dependency_closure import (
    SourceClosureError, explicit_class_references,
)


class SourceFrontierError(ValueError):
    pass


_CLASS = re.compile(r"rs/(?:[A-Za-z_$][A-Za-z_$0-9]*/)*[A-Za-z_$][A-Za-z_$0-9]*\.class\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for part in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(part)
    return hasher.hexdigest()


def _source_name_collision(candidate: str, selected: set[str]) -> bool:
    symbol = candidate[:-6]
    return any(
        old[:-6].startswith(symbol + "/") or
        symbol.startswith(old[:-6] + "/")
        for old in selected
    )


def _dependency_closed_groups(
    edges: dict[str, set[str]],
    selected: set[str],
    metadata: dict[str, tuple[str, int]],
    *,
    max_group_size: int,
    max_candidates: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Discover bounded multi-class additions, including mutual dependencies.

    A seed's entire explicit transitive project-class closure must fit inside
    the proposed batch plus the attested selection. This also finds cycles
    that a single-class direct-dependency frontier necessarily overlooks.
    """
    unique: dict[tuple[str, ...], dict[str, Any]] = {}
    for seed in sorted(edges):
        if seed in selected:
            continue
        pending = [seed]
        additional: set[str] = set()
        rejected = False
        while pending:
            name = pending.pop()
            if name in selected or name in additional:
                continue
            if name not in edges:  # Referenced original project class absent.
                rejected = True
                break
            additional.add(name)
            if len(additional) > max_group_size:
                rejected = True
                break
            pending.extend(sorted(edges[name] - selected - additional, reverse=True))
        if rejected or len(additional) < 2:
            continue
        key = tuple(sorted(additional))
        if key in unique:
            continue
        anchored = sorted({
            dependency for name in additional for dependency in edges[name] & selected
        })
        unique[key] = {
            "original_class_paths": list(key),
            "original_class_sha256": {
                name: metadata[name][0] for name in key
            },
            "additional_class_count": len(key),
            "additional_original_class_bytes": sum(metadata[name][1] for name in key),
            "internal_explicit_dependency_edges": sum(
                len(edges[name] & additional) for name in key
            ),
            "dependencies_to_selected": anchored,
            "connected_to_selected": bool(anchored),
            "class_package_collision_with_selection_or_batch": any(
                _source_name_collision(name, selected | (additional - {name}))
                for name in additional
            ),
            "source_reconstructed": False,
            "compile_or_runtime_parity_proven": False,
        }
    candidates = sorted(
        unique.values(),
        key=lambda item: (
            item["class_package_collision_with_selection_or_batch"],
            not item["connected_to_selected"],
            item["additional_class_count"],
            item["additional_original_class_bytes"],
            item["original_class_paths"],
        ),
    )
    return len(candidates), candidates[:max_candidates]


def discover_original_source_frontier(
    original_jar: Path,
    manifest: dict[str, Any],
    *,
    max_candidates: int = 30,
    max_group_size: int = 8,
) -> dict[str, Any]:
    """Return a small reproducible queue, refusing unverifiable authority.

    Dependencies are JVM constant-pool Class and type-descriptor references.
    This does not establish reflection/ServiceLoader/resource/native closure.
    """
    if not 1 <= max_candidates <= 100:
        raise SourceFrontierError("SOURCE_FRONTIER_INVALID_LIMIT")
    if not 2 <= max_group_size <= 32:
        raise SourceFrontierError("SOURCE_FRONTIER_INVALID_GROUP_SIZE")
    expected_jar = manifest.get("original_jar_sha256")
    selected_hashes = manifest.get("original_class_sha256")
    if not isinstance(expected_jar, str) or not _SHA.fullmatch(expected_jar):
        raise SourceFrontierError("SOURCE_FRONTIER_INVALID_ORIGINAL_SHA")
    if not isinstance(selected_hashes, dict) or not 1 <= len(selected_hashes) <= 1000:
        raise SourceFrontierError("SOURCE_FRONTIER_INVALID_SELECTED_CLASSES")
    for path, sha in selected_hashes.items():
        if (
            not isinstance(path, str) or not _CLASS.fullmatch(path) or
            not isinstance(sha, str) or not _SHA.fullmatch(sha)
        ):
            raise SourceFrontierError("SOURCE_FRONTIER_INVALID_SELECTED_CLASS_PIN")
    if not original_jar.is_file() or original_jar.is_symlink():
        raise SourceFrontierError("SOURCE_FRONTIER_ORIGINAL_JAR_MISSING")
    if _digest(original_jar) != expected_jar:
        raise SourceFrontierError("SOURCE_FRONTIER_ORIGINAL_JAR_SHA_MISMATCH")

    selected = set(selected_hashes)
    try:
        with zipfile.ZipFile(original_jar) as archive:
            members = archive.namelist()
            if len(members) != len(set(members)):
                raise SourceFrontierError("SOURCE_FRONTIER_DUPLICATE_ZIP_ENTRY")
            project = {
                name for name in members
                if _CLASS.fullmatch(name)
            }
            if not project or not selected <= project:
                raise SourceFrontierError("SOURCE_FRONTIER_SELECTED_CLASS_MISSING")
            for name, expected in selected_hashes.items():
                if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                    raise SourceFrontierError("SOURCE_FRONTIER_ORIGINAL_CLASS_SHA_MISMATCH")

            # Verify selected source closure as well; an arbitrary hash list
            # must not be mistaken for an already independent source island.
            edges: dict[str, set[str]] = {}
            metadata: dict[str, tuple[str, int]] = {}
            for name in sorted(project):
                class_bytes = archive.read(name)
                edges[name] = explicit_class_references(class_bytes) - {name}
                metadata[name] = (hashlib.sha256(class_bytes).hexdigest(), len(class_bytes))
            for name in selected:
                if edges[name] - selected:
                    raise SourceFrontierError("SOURCE_FRONTIER_BASE_SELECTION_NOT_CLOSED")

            proposed = []
            for name in sorted(project - selected):
                dependencies = edges[name]
                if not dependencies or not dependencies <= selected:
                    continue
                # Dependency *adjacent*, not merely JDK-only standalone.
                proposed.append({
                    "original_class_path": name,
                    "original_class_sha256": metadata[name][0],
                    "original_class_bytes": metadata[name][1],
                    "direct_original_project_dependencies": sorted(dependencies),
                    "additional_explicit_project_dependencies_needed": 0,
                    "class_package_collision_with_selected": _source_name_collision(
                        name, selected
                    ),
                    "source_reconstructed": False,
                    "compile_or_runtime_parity_proven": False,
                })
    except (zipfile.BadZipFile, OSError, EOFError, SourceClosureError) as exc:
        raise SourceFrontierError("SOURCE_FRONTIER_ARCHIVE_OR_CLASS_PARSE_ERROR") from exc

    group_count, groups = _dependency_closed_groups(
        edges, selected, metadata,
        max_group_size=max_group_size, max_candidates=max_candidates,
    )
    proposed.sort(key=lambda item: (
        item["class_package_collision_with_selected"],
        item["original_class_bytes"],
        item["original_class_path"],
    ))
    return {
        "schema_version": 1,
        "kind": "original_source_island_dependency_frontier",
        "original_jar_sha256": expected_jar,
        "selected_classes_attested": len(selected),
        "explicit_source_island_closure_verified": True,
        "original_project_classes": len(project),
        "direct_dependency_closed_candidate_count": len(proposed),
        "candidates": proposed[:max_candidates],
        "dependency_closed_group_candidate_count": group_count,
        "max_additional_classes_per_group": max_group_size,
        "dependency_closed_group_candidates": groups,
        "all_selected_source_files_compiled": "NOT_EVALUATED",
        "dynamic_or_resource_dependency_closure": "NOT_PROVEN",
        "original_class_bytecode_published": False,
    }


def write_source_frontier(
    original_jar: Path, manifest_path: Path, output_path: Path,
    *, max_candidates: int = 30, max_group_size: int = 8,
) -> dict[str, Any]:
    if output_path.exists() or output_path.is_symlink():
        raise SourceFrontierError("SOURCE_FRONTIER_REFUSE_OVERWRITE")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SourceFrontierError("SOURCE_FRONTIER_MANIFEST_READ_FAILED") from exc
    if not isinstance(manifest, dict):
        raise SourceFrontierError("SOURCE_FRONTIER_MANIFEST_NOT_OBJECT")
    report = discover_original_source_frontier(
        original_jar, manifest, max_candidates=max_candidates,
        max_group_size=max_group_size,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except FileExistsError as exc:
        raise SourceFrontierError("SOURCE_FRONTIER_REFUSE_OVERWRITE") from exc
    return report
