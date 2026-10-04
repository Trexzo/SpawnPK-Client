from __future__ import annotations

import binascii
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
import zipfile

from .classfile import ClassFormatError, parse_class
from .collision_bytecode_remap import (
    CollisionBytecodeRemapError,
    _class_names_from_jar,
    _expanded_mappings,
    _load_plan,
    remap_class_bytes,
    transform_collision_jar,
)
from .javac_diagnostics import (
    classify_javac_diagnostics,
    write_javac_diagnostic_report,
)
from .java9_macos_eawt_bridge import (
    Java9MacosEawtBridgeError,
    build_java9_macos_eawt_compile_bridge,
)
from .source_digest import source_tree_digest


class CollisionDerivedCompileError(ValueError):
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


def _arg(value: str) -> str:
    return '"' + value.replace("\\", "/").replace('"', '\\"') + '"'


def _stage_explicit_javac_sources(
    source_files: list[Path],
    source_root: Path,
    staging_root: Path,
) -> tuple[list[Path], dict[str, str]]:
    """Stage explicit javac inputs under case-unique physical parents.

    Windows javac/file-manager paths can case-fold even when the underlying
    NTFS directory is case-sensitive.  Keep package/type declarations
    untouched, but give each explicit compilation unit a unique physical
    parent so source-path transport cannot collapse case-distinct identities.
    """
    staging_root.mkdir(parents=True, exist_ok=True)

    staged: list[Path] = []
    diagnostic_map: dict[str, str] = {}

    for index, source in enumerate(source_files):
        source.relative_to(source_root)
        target = staging_root / f"{index:06d}" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())

        staged.append(target)
        diagnostic_map[str(target)] = str(source)
        diagnostic_map[target.as_posix()] = source.as_posix()

    if len(staged) != len(source_files):
        raise CollisionDerivedCompileError(
            "javac source staging count drifted"
        )

    casefolded = {
        str(path).casefold()
        for path in staged
    }
    if len(casefolded) != len(staged):
        raise CollisionDerivedCompileError(
            "javac source staging did not eliminate casefold collisions"
        )

    return staged, diagnostic_map


def _remap_staged_diagnostics(
    text: str,
    diagnostic_map: dict[str, str],
) -> str:
    value = text
    for staged in sorted(
        diagnostic_map,
        key=len,
        reverse=True,
    ):
        value = value.replace(staged, diagnostic_map[staged])
    return value


def _require_executable(command: str) -> str:
    candidate = Path(command)
    if candidate.is_absolute():
        if not candidate.is_file():
            raise CollisionDerivedCompileError(
                "javac executable does not exist"
            )
        return str(candidate)
    found = shutil.which(command)
    if found is None:
        raise CollisionDerivedCompileError(
            "javac executable not found on PATH"
        )
    return found


def _class_tree(root: Path) -> tuple[str, list[Path], int]:
    files = sorted(
        root.rglob("*.class"),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    h = hashlib.sha256()
    total = 0
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
        total += len(data)
    return h.hexdigest(), files, total


def _normalize_prefixes(prefixes: list[str]) -> list[str]:
    out: list[str] = []
    for value in prefixes:
        if not isinstance(value, str) or not value:
            raise CollisionDerivedCompileError(
                "project prefixes must be non-empty strings"
            )
        normalized = value.replace("\\", "/").lstrip("/")
        if normalized and not normalized.endswith("/"):
            normalized += "/"
        out.append(normalized)
    if not out:
        raise CollisionDerivedCompileError(
            "project prefixes must not be empty"
        )
    return sorted(set(out))


def _is_project_class(
    internal: str,
    prefixes: list[str],
) -> bool:
    entry = internal + ".class"
    return any(entry.startswith(prefix) for prefix in prefixes)


def _write_stored_zip(
    path: Path,
    entries: dict[str, bytes],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        path,
        "w",
        compression=zipfile.ZIP_STORED,
    ) as archive:
        for name in sorted(entries):
            data = entries[name]
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_STORED
            info.file_size = len(data)
            info.CRC = binascii.crc32(data) & 0xFFFFFFFF
            archive.writestr(info, data)


def _dependency_capsule(
    readable_jar: Path,
    prefixes: list[str],
    out: Path,
) -> tuple[str, int]:
    entries: dict[str, bytes] = {}
    with zipfile.ZipFile(readable_jar) as archive:
        for info in archive.infolist():
            name = info.filename
            if info.is_dir() or not name.endswith(".class"):
                continue
            internal = name[:-6]
            if _is_project_class(internal, prefixes):
                continue
            entries[name] = archive.read(name)
    if not entries:
        raise CollisionDerivedCompileError(
            "transformed dependency capsule would be empty"
        )
    _write_stored_zip(out, entries)
    return _sha256_file(out), len(entries)


def _remap_diagnostic_root(
    text: str,
    *,
    source_root: Path,
    diagnostic_root: Path,
) -> str:
    value = text.replace("\r\n", "\n").replace("\r", "\n")
    if source_root == diagnostic_root:
        return value
    replacements = [
        (str(source_root), str(diagnostic_root)),
        (source_root.as_posix(), diagnostic_root.as_posix()),
    ]
    for old, new in sorted(
        replacements,
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        value = value.replace(old, new)
    return value


def _public_diagnostic_summary(
    report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "report_id": report["report_id"],
        "frontier_id": report["frontier_id"],
        "input_sha256": report["input_sha256"],
        "summary": report["summary"],
        "identifiers_included": False,
    }


def _validate_derivation(
    recovered_manifest: dict[str, Any],
    transform: dict[str, Any],
) -> None:
    expected = {
        "collision_transform_id": transform["transform_id"],
        "collision_plan_id": transform["plan_id"],
        "collision_report_id": transform["collision_report_id"],
        "collision_mapping_sha256": transform[
            "private_mapping_sha256"
        ],
        "base_readable_jar_sha256": transform["input_jar_sha256"],
        "readable_jar_sha256": transform["output_jar_sha256"],
    }
    for key, value in expected.items():
        actual = recovered_manifest.get(key)
        if actual != value:
            raise CollisionDerivedCompileError(
                "collision-derived source authority mismatch for "
                + key
            )


def compile_collision_derived_source(
    recovered_manifest: dict[str, Any],
    source_root: Path,
    base_readable_jar: Path,
    private_collision_plan_path: Path,
    project_prefixes: list[str],
    out_dir: Path,
    *,
    javac_command: str = "javac",
    release: int | None = 9,
    java9_macos_eawt_compile_bridge: bool = False,
    report_compile_failure: bool = False,
    private_diagnostic_report_out: Path | None = None,
    diagnostic_source_root: Path | None = None,
    canonical_source_root: Path | None = None,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    base_readable_jar = base_readable_jar.resolve()
    private_collision_plan_path = (
        private_collision_plan_path.resolve()
    )
    out_dir = out_dir.resolve()
    diagnostic_root = (
        diagnostic_source_root.resolve()
        if diagnostic_source_root is not None
        else source_root
    )
    canonical_root = (
        canonical_source_root.resolve()
        if canonical_source_root is not None
        else source_root
    )

    if not source_root.is_dir():
        raise CollisionDerivedCompileError(
            "source root does not exist"
        )
    if not base_readable_jar.is_file():
        raise CollisionDerivedCompileError(
            "base readable JAR does not exist"
        )
    if not private_collision_plan_path.is_file():
        raise CollisionDerivedCompileError(
            "private collision plan does not exist"
        )
    if not diagnostic_root.is_dir():
        raise CollisionDerivedCompileError(
            "diagnostic source root does not exist"
        )
    if not canonical_root.is_dir():
        raise CollisionDerivedCompileError(
            "canonical source root does not exist"
        )
    if out_dir.exists() and any(out_dir.iterdir()):
        raise CollisionDerivedCompileError(
            "compile output directory must be empty"
        )
    if release is not None and (
        not isinstance(release, int)
        or isinstance(release, bool)
        or release < 1
    ):
        raise CollisionDerivedCompileError(
            "invalid target release"
        )

    prefixes = _normalize_prefixes(project_prefixes)
    javac = _require_executable(javac_command)
    canonical_before_sha, canonical_files, canonical_bytes = (
        source_tree_digest(canonical_root)
    )
    if canonical_before_sha != recovered_manifest.get(
        "source_tree_sha256"
    ):
        raise CollisionDerivedCompileError(
            "source tree does not match recovered manifest"
        )

    try:
        plan = _load_plan(private_collision_plan_path)
        base_classes = _class_names_from_jar(base_readable_jar)
        expanded_mapping, nested_added = _expanded_mappings(
            base_classes,
            plan,
        )
    except CollisionBytecodeRemapError as exc:
        raise CollisionDerivedCompileError(str(exc)) from exc

    for old, new in expanded_mapping.items():
        if _is_project_class(old, prefixes):
            raise CollisionDerivedCompileError(
                "collision mapping touches project class identity"
            )
        if _is_project_class(new, prefixes):
            raise CollisionDerivedCompileError(
                "collision mapping target enters project namespace"
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    transformed_readable = out_dir / "compile-transformed-readable.jar"
    transformed_dependency = (
        out_dir / "compile-transformed-dependency.jar"
    )
    generated_dir = out_dir / "generated-transformed"
    restored_dir = out_dir / "restored-classes"
    argfile = out_dir / "javac.args"

    try:
        transform = transform_collision_jar(
            base_readable_jar,
            private_collision_plan_path,
            transformed_readable,
        )
    except CollisionBytecodeRemapError as exc:
        raise CollisionDerivedCompileError(str(exc)) from exc

    _validate_derivation(recovered_manifest, transform)

    dependency_sha, dependency_class_count = _dependency_capsule(
        transformed_readable,
        prefixes,
        transformed_dependency,
    )

    compile_classpath = [str(transformed_dependency)]
    platform_bridges: list[dict[str, Any]] = []
    if java9_macos_eawt_compile_bridge:
        try:
            bridge_classes, bridge_report = (
                build_java9_macos_eawt_compile_bridge(
                    out_dir / "java9-macos-eawt-bridge",
                    javac_command=javac,
                    release=release,
                )
            )
        except Java9MacosEawtBridgeError as exc:
            raise CollisionDerivedCompileError(str(exc)) from exc
        compile_classpath.append(str(bridge_classes))
        platform_bridges.append(bridge_report)

    sources = sorted(
        source_root.rglob("*.java"),
        key=lambda path: path.relative_to(source_root).as_posix(),
    )
    if not sources:
        raise CollisionDerivedCompileError(
            "collision-derived source root contains no Java files"
        )

    staged_sources, staged_diagnostic_map = (
        _stage_explicit_javac_sources(
            sources,
            source_root,
            out_dir / "source-inputs",
        )
    )
    empty_sourcepath = out_dir / "empty-sourcepath"
    empty_sourcepath.mkdir(parents=True)

    generated_dir.mkdir(parents=True)
    args = [
        "-proc:none",
        "-encoding",
        "UTF-8",
        "-Xlint:none",
        "-Xmaxerrs",
        "10000",
        "-sourcepath",
        str(empty_sourcepath),
        "-classpath",
        os.pathsep.join(compile_classpath),
        "-d",
        str(generated_dir),
    ]
    if release is not None:
        args.extend(["--release", str(release)])
    args.extend(str(path) for path in staged_sources)
    argfile.write_text(
        "\n".join(_arg(value) for value in args) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    proc = subprocess.run(
        [javac, "@" + str(argfile)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if proc.returncode != 0:
        if not report_compile_failure:
            raise CollisionDerivedCompileError(
                "collision-derived javac failed:\n"
                + proc.stdout
                + proc.stderr
            )

        staged_remapped = _remap_staged_diagnostics(
            proc.stdout + proc.stderr,
            staged_diagnostic_map,
        )
        remapped = _remap_diagnostic_root(
            staged_remapped,
            source_root=source_root,
            diagnostic_root=diagnostic_root,
        )
        public_diagnostic = classify_javac_diagnostics(remapped)
        if private_diagnostic_report_out is not None:
            private_diagnostic = classify_javac_diagnostics(
                remapped,
                include_identifiers=True,
            )
            if (
                private_diagnostic["report_id"]
                != public_diagnostic["report_id"]
                or private_diagnostic["frontier_id"]
                != public_diagnostic["frontier_id"]
            ):
                raise CollisionDerivedCompileError(
                    "private/public javac diagnostic authority drifted"
                )
            write_javac_diagnostic_report(
                private_diagnostic,
                private_diagnostic_report_out,
            )

        canonical_after_sha, after_files, after_bytes = (
            source_tree_digest(canonical_root)
        )
        if (
            canonical_after_sha != canonical_before_sha
            or len(after_files) != len(canonical_files)
            or after_bytes != canonical_bytes
        ):
            raise CollisionDerivedCompileError(
                "canonical source changed during failed derived compile"
            )

        material = {
            "collision_transform_id": transform["transform_id"],
            "collision_plan_id": transform["plan_id"],
            "canonical_source_tree_sha256": canonical_before_sha,
            "compile_dependency_sha256": dependency_sha,
            "compile_only_platform_bridge_ids": [
                row["bridge_id"]
                for row in platform_bridges
            ],
            "release": release,
            "source_count": len(sources),
            "source_transport": "case_unique_explicit_inputs",
            "status": "compile_failed",
            "javac_frontier_id": public_diagnostic["frontier_id"],
        }
        compile_id = (
            "COLLDERIVEDCOMPILE_"
            + _stable_digest(material)[:20].upper()
        )
        report = {
            "schema_version": 1,
            "kind": "collision_derived_compile",
            "compile_id": compile_id,
            "status": "compile_failed",
            "collision_transform_id": transform["transform_id"],
            "collision_plan_id": transform["plan_id"],
            "collision_report_id": transform[
                "collision_report_id"
            ],
            "canonical_source_tree_sha256": canonical_before_sha,
            "canonical_source_tree_sha256_after": canonical_after_sha,
            "canonical_source_modified": False,
            "compile_only_transformed_readable": {
                "sha256": transform["output_jar_sha256"],
                "runtime_allowed": False,
            },
            "compile_only_transformed_dependency": {
                "sha256": dependency_sha,
                "class_count": dependency_class_count,
                "runtime_allowed": False,
            },
            "compile_only_platform_bridges": platform_bridges,
            "mapping": {
                "explicit_count": int(
                    transform["summary"]["explicit_remap_count"]
                ),
                "expanded_count": len(expanded_mapping),
                "nested_family_added_count": nested_added,
            },
            "compiler": {
                "target_release": release,
                "source_count": len(sources),
                "staged_source_count": len(staged_sources),
                "source_transport": "case_unique_explicit_inputs",
                "classpath_entry_count": len(compile_classpath),
                "exit_code": proc.returncode,
                "diagnostic_classification": (
                    _public_diagnostic_summary(
                        public_diagnostic
                    )
                ),
            },
            "generated_transformed_classes": {
                "class_count": 0,
                "tree_sha256": None,
                "total_bytes": 0,
            },
            "restored_classes": {
                "class_count": 0,
                "tree_sha256": None,
                "total_bytes": 0,
                "restore_replacement_count": 0,
                "transformed_reference_count": 0,
            },
            "runtime_transformed_dependency_allowed": False,
            "runtime_platform_bridges_allowed": False,
        }
        (out_dir / "collision-derived-compile.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return report

    generated_sha, generated_files, generated_bytes = _class_tree(
        generated_dir
    )
    if not generated_files:
        raise CollisionDerivedCompileError(
            "javac produced no project classfiles"
        )

    reverse = {
        new: old
        for old, new in expanded_mapping.items()
    }
    transformed_names = sorted(reverse)

    restored_dir.mkdir(parents=True)
    replacement_count = 0
    for path in generated_files:
        rel = path.relative_to(generated_dir)
        internal = rel.as_posix()[:-6]
        if internal in reverse or any(
            internal.startswith(name + "$")
            for name in transformed_names
        ):
            raise CollisionDerivedCompileError(
                "generated project class identity occupies transformed "
                "dependency namespace"
            )

        try:
            original = path.read_bytes()
            restored, changed = remap_class_bytes(
                original,
                reverse,
            )
            replacement_count += changed
            parsed = parse_class(restored)
        except (
            CollisionBytecodeRemapError,
            ClassFormatError,
        ) as exc:
            raise CollisionDerivedCompileError(str(exc)) from exc

        if parsed.name != internal:
            raise CollisionDerivedCompileError(
                "restored project class identity/path mismatch"
            )

        # A second reverse pass must be a no-op.  This proves all exact
        # transformed type tokens handled by the remapper are gone.
        try:
            second, second_changes = remap_class_bytes(
                restored,
                reverse,
            )
        except CollisionBytecodeRemapError as exc:
            raise CollisionDerivedCompileError(str(exc)) from exc
        if second_changes != 0 or second != restored:
            raise CollisionDerivedCompileError(
                "restored class retains transformed dependency references"
            )

        target = restored_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(restored)

    restored_sha, restored_files, restored_bytes = _class_tree(
        restored_dir
    )

    canonical_after_sha, after_files, after_bytes = source_tree_digest(
        canonical_root
    )
    if (
        canonical_after_sha != canonical_before_sha
        or len(after_files) != len(canonical_files)
        or after_bytes != canonical_bytes
    ):
        raise CollisionDerivedCompileError(
            "canonical source changed during derived compile"
        )

    material = {
        "collision_transform_id": transform["transform_id"],
        "collision_plan_id": transform["plan_id"],
        "canonical_source_tree_sha256": canonical_before_sha,
        "compile_dependency_sha256": dependency_sha,
        "compile_only_platform_bridge_ids": [
            row["bridge_id"]
            for row in platform_bridges
        ],
        "release": release,
        "source_count": len(sources),
        "source_transport": "case_unique_explicit_inputs",
        "generated_class_tree_sha256": generated_sha,
        "restored_class_tree_sha256": restored_sha,
        "restore_replacement_count": replacement_count,
    }
    compile_id = (
        "COLLDERIVEDCOMPILE_"
        + _stable_digest(material)[:20].upper()
    )

    report = {
        "schema_version": 1,
        "kind": "collision_derived_compile",
        "compile_id": compile_id,
        "status": "complete",
        "collision_transform_id": transform["transform_id"],
        "collision_plan_id": transform["plan_id"],
        "collision_report_id": transform["collision_report_id"],
        "canonical_source_tree_sha256": canonical_before_sha,
        "canonical_source_tree_sha256_after": canonical_after_sha,
        "canonical_source_modified": False,
        "compile_only_transformed_readable": {
            "sha256": transform["output_jar_sha256"],
            "runtime_allowed": False,
        },
        "compile_only_transformed_dependency": {
            "sha256": dependency_sha,
            "class_count": dependency_class_count,
            "runtime_allowed": False,
        },
        "compile_only_platform_bridges": platform_bridges,
        "mapping": {
            "explicit_count": int(
                transform["summary"]["explicit_remap_count"]
            ),
            "expanded_count": len(expanded_mapping),
            "nested_family_added_count": nested_added,
        },
        "compiler": {
            "target_release": release,
            "source_count": len(sources),
            "staged_source_count": len(staged_sources),
            "source_transport": "case_unique_explicit_inputs",
            "classpath_entry_count": len(compile_classpath),
            "exit_code": 0,
            "diagnostic_classification": None,
        },
        "generated_transformed_classes": {
            "class_count": len(generated_files),
            "tree_sha256": generated_sha,
            "total_bytes": generated_bytes,
        },
        "restored_classes": {
            "class_count": len(restored_files),
            "tree_sha256": restored_sha,
            "total_bytes": restored_bytes,
            "restore_replacement_count": replacement_count,
            "transformed_reference_count": 0,
        },
        "runtime_transformed_dependency_allowed": False,
        "runtime_platform_bridges_allowed": False,
    }

    (out_dir / "collision-derived-compile.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
