from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any
import zipfile

from .classfile import ClassFormatError, parse_class
from .decompiler import DecompilerError, run_decompiler, sha256_file
from .source_digest import source_tree_digest
from .source_normalization import (
    SourceNormalizationError,
    normalize_procyon_source,
)
from .source_readiness import _PACKAGE_RE, _top_level_type_names


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


def _selected_case_collision_report(
    readable_jar: Path,
    selected_entries: list[str],
    source_dir: Path | None = None,
    *,
    phase: str = "bytecode_preflight",
) -> dict[str, Any]:
    """Classify casefold-colliding source targets against exact class identity.

    The report binds every colliding archive entry to its exact classfile
    SHA-256 and parsed JVM this_class internal name.  When source_dir is
    supplied, it also verifies whether Procyon materialized distinct source
    bytes at each exact internal-name-derived Java path.
    """
    groups = _casefold_collision_groups(selected_entries)
    rows: list[dict[str, Any]] = []

    with zipfile.ZipFile(readable_jar) as z:
        for group in groups:
            entries: list[dict[str, Any]] = []
            parse_failed = False

            for entry in group:
                data = z.read(entry)
                class_sha = hashlib.sha256(data).hexdigest()
                internal_name: str | None = None
                parse_error: str | None = None

                try:
                    parsed = parse_class(data)
                    internal_name = parsed.name
                except (ClassFormatError, ValueError, IndexError) as exc:
                    parse_failed = True
                    parse_error = f"{type(exc).__name__}: {exc}"

                entry_internal_name = entry[:-6]
                expected_source = (
                    f"{internal_name}.java"
                    if internal_name
                    else None
                )
                source_exists = False
                source_sha: str | None = None
                source_bytes: int | None = None
                declared_package: str | None = None
                top_level_types: list[str] = []
                source_identity_matches_internal_name: bool | None = None

                if source_dir is not None and expected_source is not None:
                    source_path = source_dir / Path(expected_source)
                    source_exists = source_path.is_file()
                    if source_exists:
                        source_data = source_path.read_bytes()
                        source_sha = hashlib.sha256(source_data).hexdigest()
                        source_bytes = len(source_data)
                        source_text = source_data.decode(
                            "utf-8",
                            errors="replace",
                        )
                        package_match = _PACKAGE_RE.search(source_text)
                        declared_package = (
                            package_match.group(1)
                            if package_match
                            else None
                        )
                        top_level_types = _top_level_type_names(
                            source_text,
                            public_only=False,
                        )
                        expected_package = (
                            internal_name.rpartition("/")[0].replace("/", ".")
                            if internal_name
                            else ""
                        )
                        expected_simple_name = (
                            internal_name.rpartition("/")[2]
                            if internal_name
                            else ""
                        )
                        source_identity_matches_internal_name = (
                            (declared_package or "") == expected_package
                            and expected_simple_name in top_level_types
                        )

                entries.append(
                    {
                        "entry": entry,
                        "entry_sha256": class_sha,
                        "entry_internal_name": entry_internal_name,
                        "internal_name": internal_name,
                        "entry_matches_internal_name": (
                            internal_name == entry_internal_name
                        ),
                        "parse_error": parse_error,
                        "expected_source_path": expected_source,
                        "source_exists": source_exists,
                        "source_sha256": source_sha,
                        "source_bytes": source_bytes,
                        "declared_package": declared_package,
                        "top_level_types": top_level_types,
                        "source_identity_matches_internal_name": (
                            source_identity_matches_internal_name
                        ),
                    }
                )

            class_shas = {
                str(row["entry_sha256"])
                for row in entries
            }
            internal_names = {
                str(row["internal_name"])
                for row in entries
                if row["internal_name"] is not None
            }
            source_shas = {
                str(row["source_sha256"])
                for row in entries
                if row["source_sha256"] is not None
            }

            exact_entry_identity = (
                not parse_failed
                and all(
                    row["entry_matches_internal_name"]
                    for row in entries
                )
            )
            distinct_case_types = (
                exact_entry_identity
                and len(internal_names) == len(entries)
                and len(
                    {
                        name.casefold()
                        for name in internal_names
                    }
                ) == 1
            )
            exact_alias = (
                not parse_failed
                and len(class_shas) == 1
                and len(internal_names) == 1
            )

            if parse_failed:
                classification = "class_parse_failure"
            elif exact_alias:
                classification = "exact_alias_entries"
            elif not exact_entry_identity:
                classification = "entry_internal_identity_mismatch"
            elif distinct_case_types:
                if source_dir is None:
                    classification = "distinct_case_types"
                elif not all(row["source_exists"] for row in entries):
                    classification = "distinct_case_types_missing_source"
                elif not all(
                    row["source_identity_matches_internal_name"] is True
                    for row in entries
                ):
                    classification = (
                        "distinct_case_types_source_identity_mismatch"
                    )
                elif len(source_shas) != len(entries):
                    classification = "distinct_case_types_source_conflated"
                else:
                    classification = (
                        "distinct_case_types_source_identity_preserved"
                    )
            else:
                classification = "mixed_case_collision_identity"

            rows.append(
                {
                    "casefold_key": group[0].casefold(),
                    "entry_count": len(entries),
                    "unique_class_sha256_count": len(class_shas),
                    "unique_internal_name_count": len(internal_names),
                    "unique_source_sha256_count": len(source_shas),
                    "classification": classification,
                    "entries": entries,
                }
            )

    counts: dict[str, int] = {}
    for row in rows:
        key = str(row["classification"])
        counts[key] = counts.get(key, 0) + 1

    material = {
        "phase": phase,
        "selected_class_count": len(selected_entries),
        "collision_group_count": len(rows),
        "classification_counts": dict(sorted(counts.items())),
        "groups": rows,
    }
    report_id = (
        "SRCCASE_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )
    return {
        "schema_version": 1,
        "kind": "project_source_case_collision_report",
        "report_id": report_id,
        **material,
    }


def _case_collision_report_passes(report: dict[str, Any]) -> bool:
    allowed = {
        "distinct_case_types_source_identity_preserved",
    }
    return all(
        row.get("classification") in allowed
        for row in report.get("groups", [])
    )


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
                pre_case_report = _selected_case_collision_report(
                    readable_jar,
                    selected_entries,
                    phase="bytecode_preflight",
                )
                _write_json(
                    pre_case_report,
                    out_dir / "case-collision-preflight.json",
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
                _write_json(result, out_dir / "decompiler-result.json")

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

                raw_case_report = _selected_case_collision_report(
                    readable_jar,
                    selected_entries,
                    source_dir,
                    phase="raw_procyon",
                )
                _write_json(
                    raw_case_report,
                    out_dir / "case-collision-raw-procyon.json",
                )
                if not _case_collision_report_passes(raw_case_report):
                    counts = raw_case_report.get(
                        "classification_counts",
                        {},
                    )
                    raise SourceWorkspaceError(
                        "project-only Procyon raw source identity gate "
                        "failed; inspect case-collision-raw-procyon.json. "
                        f"collision_groups={raw_case_report.get('collision_group_count')} "
                        f"classifications={counts}"
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
        if project_only and selected_entries:
            normalized_case_report = _selected_case_collision_report(
                readable_jar,
                selected_entries,
                source_dir,
                phase="post_normalization",
            )
            _write_json(
                normalized_case_report,
                out_dir / "case-collision-post-normalization.json",
            )
            if not _case_collision_report_passes(
                normalized_case_report
            ):
                counts = normalized_case_report.get(
                    "classification_counts",
                    {},
                )
                raise SourceWorkspaceError(
                    "project-only normalized source identity gate failed; "
                    "inspect case-collision-post-normalization.json. "
                    f"collision_groups={normalized_case_report.get('collision_group_count')} "
                    f"classifications={counts}"
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
