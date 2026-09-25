from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any
import zipfile

from .decompiler import DecompilerError, run_decompiler, sha256_file
from .source_digest import source_tree_digest
from .source_normalization import (
    SourceNormalizationError,
    normalize_procyon_source,
)


class SourceWorkspaceError(ValueError):
    pass


def _write_json(doc: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _source_tree_digest(root: Path) -> tuple[str, int, int]:
    digest, files, total_bytes = source_tree_digest(root)
    return digest, len(files), total_bytes



def _project_prefixes(readable_manifest: dict[str, Any]) -> list[str]:
    values = readable_manifest.get("project_source_prefixes")
    if not isinstance(values, list) or not values:
        raise SourceWorkspaceError(
            "project-only source workspace requires non-empty "
            "readable manifest project_source_prefixes"
        )
    out: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise SourceWorkspaceError(
                "readable manifest project_source_prefixes must contain "
                "non-empty strings"
            )
        normalized = value.replace("\\", "/").lstrip("/")
        if not normalized:
            raise SourceWorkspaceError(
                "readable manifest project_source_prefixes must not normalize "
                "to the archive root"
            )
        parts = [part for part in normalized.rstrip("/").split("/") if part]
        if (
            not parts
            or any(part in {".", ".."} for part in parts)
            or normalized.startswith("META-INF/")
        ):
            raise SourceWorkspaceError(
                "readable manifest project_source_prefixes contains an unsafe "
                f"or unsupported prefix: {value!r}"
            )
        normalized = "/".join(parts) + "/"
        out.append(normalized)
    return sorted(set(out))


def _is_project_class(entry: str, prefixes: list[str]) -> bool:
    if not entry.endswith(".class"):
        return False
    if entry.startswith("META-INF/versions/"):
        parts = entry.split("/", 3)
        if len(parts) == 4:
            return any(parts[3].startswith(prefix) for prefix in prefixes)
    return any(entry.startswith(prefix) for prefix in prefixes)


def _is_project_source_target(entry: str, prefixes: list[str]) -> bool:
    """Select Java source units, not nested/inner classfiles.

    Procyon reconstructs $-named inner classes from the outer class when they
    remain available as resolver context. Targeting them independently produces
    invalid duplicate source units such as Outer$Inner.java declaring public
    class Inner.
    """
    if not _is_project_class(entry, prefixes):
        return False
    return "$" not in Path(entry).name


def _selection_digest(entries: list[str]) -> str:
    h = hashlib.sha256()
    for entry in entries:
        raw = entry.encode("utf-8")
        h.update(len(raw).to_bytes(4, "big"))
        h.update(raw)
    return h.hexdigest()


def _casefold_collision_groups(values: list[str]) -> list[list[str]]:
    groups: dict[str, list[str]] = {}
    for value in values:
        groups.setdefault(value.casefold(), []).append(value)
    return [
        sorted(group)
        for group in groups.values()
        if len(set(group)) > 1
    ]


def _filesystem_supports_case_distinct_names(root: Path) -> bool:
    """Probe whether one directory can hold names differing only by case."""
    root.mkdir(parents=True, exist_ok=True)
    upper = root / ".spk-case-probe-A"
    lower = root / ".spk-case-probe-a"
    try:
        upper.write_bytes(b"UPPER")
        lower.write_bytes(b"lower")
        if upper.read_bytes() != b"UPPER":
            return False
        if lower.read_bytes() != b"lower":
            return False
        try:
            return not os.path.samefile(str(upper), str(lower))
        except OSError:
            return False
    finally:
        for path in (upper, lower):
            try:
                os.unlink(str(path))
            except FileNotFoundError:
                pass


def _extract_class_context(
    readable_jar: Path,
    root: Path,
    prefixes: list[str],
) -> tuple[list[Path], list[str]]:
    selected: list[str] = []
    with zipfile.ZipFile(readable_jar) as z:
        infos = sorted(z.infolist(), key=lambda info: info.filename)
        class_entries = [
            info.filename
            for info in infos
            if not info.is_dir() and info.filename.endswith(".class")
        ]
        collisions = _casefold_collision_groups(class_entries)
        if collisions and not _filesystem_supports_case_distinct_names(root):
            raise SourceWorkspaceError(
                "project-only Procyon resolver context contains "
                "case-distinct class paths, but the staging filesystem is "
                "case-insensitive. Use a case-sensitive output directory. "
                f"collision_groups={len(collisions)} "
                f"sample={collisions[:3]!r}"
            )
        for info in infos:
            name = info.filename
            if info.is_dir() or not name.endswith(".class"):
                continue
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                raise SourceWorkspaceError(
                    f"unsafe class entry in readable JAR: {name!r}"
                )
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(info))
            if _is_project_source_target(name, prefixes):
                if name.startswith("META-INF/versions/"):
                    raise SourceWorkspaceError(
                        "project-only source workspace does not support "
                        f"multi-release project class {name!r}"
                    )
                selected.append(name)
    if not selected:
        raise SourceWorkspaceError(
            "project-only source workspace selected no project classes"
        )
    return [root / Path(name) for name in selected], selected

def build_source_workspace(
    readable_manifest: dict[str, Any],
    readable_jar: Path,
    decompiler_jar: Path,
    *,
    expected_decompiler_sha256: str,
    engine: str,
    out_dir: Path,
    project_only: bool = False,
) -> dict[str, Any]:
    if (
        readable_manifest.get("schema_version") != 1
        or readable_manifest.get("kind")
        != "readable_client_build_manifest"
    ):
        raise SourceWorkspaceError("unsupported readable-client manifest")

    if readable_manifest.get("status") != "complete":
        raise SourceWorkspaceError(
            "source workspace requires a complete readable-client build"
        )
    if readable_manifest.get("verification_pass") is not True:
        raise SourceWorkspaceError(
            "readable-client manifest is not independently verified"
        )

    readable_jar = readable_jar.resolve()
    if not readable_jar.is_file():
        raise SourceWorkspaceError(
            f"readable client JAR does not exist: {readable_jar}"
        )

    expected_input_sha = str(
        readable_manifest.get("output_sha256", "")
    ).lower()
    actual_input_sha = sha256_file(readable_jar)
    if actual_input_sha.lower() != expected_input_sha:
        raise SourceWorkspaceError(
            "readable client SHA-256 does not match build manifest: "
            f"{actual_input_sha} != {expected_input_sha}"
        )

    namespace_id = readable_manifest.get("namespace_id")
    class_plan_digest = readable_manifest.get("class_plan_digest")
    member_plan_digest = readable_manifest.get("member_plan_digest")
    if not all(
        isinstance(value, str) and value
        for value in (
            namespace_id,
            class_plan_digest,
            member_plan_digest,
        )
    ):
        raise SourceWorkspaceError(
            "readable-client manifest lacks namespace/plan digest pins"
        )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SourceWorkspaceError(
            "source workspace output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    source_dir = out_dir / "src"

    project_prefixes: list[str] = []
    selected_entries: list[str] = []
    selection_sha: str | None = None
    try:
        if project_only:
            if engine.lower() != "procyon":
                raise SourceWorkspaceError(
                    "project-only source workspace is currently supported "
                    "only with Procyon"
                )
            project_prefixes = _project_prefixes(readable_manifest)
            with tempfile.TemporaryDirectory(
                prefix=".spk-project-decompile-",
                dir=out_dir,
            ) as td:
                class_files, selected_entries = _extract_class_context(
                    readable_jar,
                    Path(td),
                    project_prefixes,
                )
                selection_sha = _selection_digest(selected_entries)
                selected_collisions = _casefold_collision_groups(
                    [
                        str(Path(name).with_suffix(".java")).replace("\\", "/")
                        for name in selected_entries
                    ]
                )
                if (
                    selected_collisions
                    and not _filesystem_supports_case_distinct_names(source_dir)
                ):
                    raise SourceWorkspaceError(
                        "project-only Procyon output contains case-distinct "
                        "Java source paths, but the source filesystem is "
                        "case-insensitive. Use a case-sensitive output "
                        "directory. "
                        f"collision_groups={len(selected_collisions)} "
                        f"sample={selected_collisions[:3]!r}"
                    )
                result = run_decompiler(
                    readable_jar,
                    decompiler_jar,
                    expected_decompiler_sha256=expected_decompiler_sha256,
                    engine=engine,
                    out_dir=source_dir,
                    clean_out=False,
                    input_class_files=class_files,
                )
                expected_count = len(selected_entries)
                actual_inputs = int(
                    result.get("selected_class_file_count", -1)
                )
                if actual_inputs != expected_count:
                    raise SourceWorkspaceError(
                        "project-only Procyon selected input count drifted: "
                        f"{actual_inputs} != {expected_count}"
                    )
                actual_sources = int(result.get("java_file_count", -1))
                if actual_sources != expected_count:
                    raise SourceWorkspaceError(
                        "project-only Procyon did not materialize one Java "
                        "source unit per selected top-level class: "
                        f"{actual_sources} != {expected_count}"
                    )
        else:
            result = run_decompiler(
                readable_jar,
                decompiler_jar,
                expected_decompiler_sha256=expected_decompiler_sha256,
                engine=engine,
                out_dir=source_dir,
                clean_out=False,
            )
    except DecompilerError as exc:
        raise SourceWorkspaceError(str(exc)) from exc

    normalization_report: dict[str, Any] | None = None
    if str(result.get("engine", "")).lower() == "procyon":
        try:
            normalization_report = normalize_procyon_source(
                source_dir,
                readable_jar,
            )
        except SourceNormalizationError as exc:
            raise SourceWorkspaceError(str(exc)) from exc
        _write_json(
            normalization_report,
            out_dir / "source-normalization.json",
        )

    tree_sha, java_count, source_bytes = _source_tree_digest(source_dir)
    if java_count != int(result.get("java_file_count", -1)):
        raise SourceWorkspaceError(
            "decompiler result java_file_count disagrees with source tree"
        )

    material = {
        "source_sha256": readable_manifest["source_sha256"],
        "readable_jar_sha256": actual_input_sha,
        "namespace_id": namespace_id,
        "class_plan_digest": class_plan_digest,
        "member_plan_digest": member_plan_digest,
        "engine": result["engine"],
        "decompiler_sha256": result["decompiler_sha256"],
        "source_tree_sha256": tree_sha,
        "source_scope": "project_classes" if project_only else "whole_archive",
        "project_source_prefixes": project_prefixes,
        "selected_class_count": len(selected_entries) if project_only else None,
        "selected_class_digest": selection_sha,
    }
    if normalization_report is not None:
        material["normalization_id"] = normalization_report[
            "normalization_id"
        ]
    raw = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    workspace_id = (
        "SRCWS_" + hashlib.sha256(raw).hexdigest()[:20].upper()
    )

    manifest = {
        "schema_version": 1,
        "kind": "recovered_source_workspace_manifest",
        "workspace_id": workspace_id,
        "build_id": readable_manifest["build_id"],
        "source_authority_sha256": readable_manifest["source_sha256"],
        "readable_jar_sha256": actual_input_sha,
        "namespace_id": namespace_id,
        "class_plan_digest": class_plan_digest,
        "member_plan_digest": member_plan_digest,
        "engine": result["engine"],
        "decompiler_sha256": result["decompiler_sha256"],
        "source_tree_sha256": tree_sha,
        "java_file_count": java_count,
        "source_bytes": source_bytes,
        "source_directory": "src",
        "source_scope": "project_classes" if project_only else "whole_archive",
        "project_source_prefixes": project_prefixes,
        "selected_class_count": len(selected_entries) if project_only else None,
        "selected_class_digest": selection_sha,
        "normalization_id": (
            normalization_report["normalization_id"]
            if normalization_report is not None
            else None
        ),
        "normalization_summary": (
            normalization_report["summary"]
            if normalization_report is not None
            else None
        ),
    }
    _write_json(result, out_dir / "decompiler-result.json")
    _write_json(
        manifest,
        out_dir / "recovered-source-manifest.json",
    )
    return manifest
