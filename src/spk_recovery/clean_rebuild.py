from __future__ import annotations

import binascii
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any
import zipfile

from .indexer import index_jar
from .javac_diagnostics import (
    classify_javac_diagnostics,
    write_javac_diagnostic_report,
)
from .progressive_compile import (
    ProgressiveCompileError,
    _verify_authority,
    _workspace_readable_derivation,
)
from .namespace_virtualized_compile import (
    NamespaceVirtualizedCompileError,
    compile_with_namespace_virtualization,
)
from .namespace_alias_plan import (
    NamespaceAliasPlanError,
    build_namespace_alias_plan,
)
from .collision_derived_compile import (
    CollisionDerivedCompileError,
    compile_collision_derived_source,
)
from .source_digest import source_tree_digest
from .dependency_official_derived_compile import (
    DependencyOfficialDerivedCompileError,
    compile_official_overlay_and_restore,
)


class CleanRebuildError(ValueError):
    pass


_SIGNATURE_SUFFIXES = (".SF", ".RSA", ".DSA", ".EC")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _normalize_prefixes(
    readable_manifest: dict[str, Any],
    source_prefixes: list[str] | None,
) -> list[str]:
    if source_prefixes is None:
        manifest_prefixes = readable_manifest.get(
            "project_source_prefixes"
        )
        if manifest_prefixes is not None:
            if (
                not isinstance(manifest_prefixes, list)
                or not manifest_prefixes
            ):
                raise CleanRebuildError(
                    "readable manifest project_source_prefixes must be "
                    "a non-empty array"
                )
            values = manifest_prefixes
        else:
            fallback_count = int(
                readable_manifest.get("semantic_summary", {}).get(
                    "source_safety_fallbacks",
                    0,
                )
            )
            if fallback_count:
                raise CleanRebuildError(
                    "readable manifest contains source-safety fallback "
                    "classes but lacks project_source_prefixes; rebuild "
                    "the readable client with current tooling or supply "
                    "explicit source prefixes"
                )
            target_package = str(
                readable_manifest.get("target_package", "")
            ).strip("/")
            values = ["rs/"]
            if target_package:
                values.append(target_package + "/")
    else:
        values = source_prefixes

    out: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise CleanRebuildError(
                "source prefixes must be non-empty strings"
            )
        normalized = value.replace("\\", "/").lstrip("/")
        if normalized and not normalized.endswith("/"):
            normalized += "/"
        out.append(normalized)
    return sorted(set(out))


def _is_project_class(
    entry: str,
    prefixes: list[str],
) -> bool:
    if not entry.endswith(".class"):
        return False
    if entry.startswith("META-INF/versions/"):
        parts = entry.split("/", 3)
        if len(parts) == 4:
            return any(
                parts[3].startswith(prefix)
                for prefix in prefixes
            )
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
    ) as z:
        for name in sorted(entries):
            data = entries[name]
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_STORED
            info.file_size = len(data)
            info.CRC = binascii.crc32(data) & 0xFFFFFFFF
            z.writestr(info, data)


def _dependency_capsule(
    readable_jar: Path,
    prefixes: list[str],
    out: Path,
) -> tuple[str, int]:
    entries: dict[str, bytes] = {}
    with zipfile.ZipFile(readable_jar) as z:
        for info in z.infolist():
            name = info.filename
            if info.is_dir() or not name.endswith(".class"):
                continue
            if _is_project_class(name, prefixes):
                continue
            entries[name] = z.read(name)
    if not entries:
        raise CleanRebuildError(
            "dependency capsule would contain no external class entries"
        )
    _write_stored_zip(out, entries)
    return _sha256_file(out), len(entries)


def _arg(value: str) -> str:
    # javac argfiles accept quoted forward-slash paths on Windows and POSIX.
    return '"' + value.replace("\\", "/").replace('"', '\\"') + '"'


def _diagnostic(
    text: str,
    *,
    source_root: Path,
    work_root: Path,
    limit: int = 50000,
) -> str:
    value = text.replace("\r\n", "\n").replace("\r", "\n")
    for old, new in (
        (str(source_root), "<SOURCE>"),
        (source_root.as_posix(), "<SOURCE>"),
        (str(work_root), "<WORK>"),
        (work_root.as_posix(), "<WORK>"),
    ):
        value = value.replace(old, new)
    if len(value) > limit:
        value = value[:limit] + "\n<TRUNCATED>\n"
    return value


def _project_source_files(
    all_files: list[Path],
    source_root: Path,
    prefixes: list[str],
) -> list[Path]:
    return [
        path
        for path in all_files
        if any(
            path.relative_to(source_root)
            .as_posix()
            .startswith(prefix)
            for prefix in prefixes
        )
    ]


def _generated_classes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(
            root.rglob("*.class"),
            key=lambda path: path.relative_to(root).as_posix(),
        )
    }


def _expected_project_classes(
    readable_jar: Path,
    prefixes: list[str],
) -> set[str]:
    with zipfile.ZipFile(readable_jar) as z:
        names = {
            info.filename
            for info in z.infolist()
            if not info.is_dir()
            and _is_project_class(info.filename, prefixes)
        }
    versioned = [
        name
        for name in names
        if name.startswith("META-INF/versions/")
    ]
    if versioned:
        raise CleanRebuildError(
            "multi-release project classes are not supported by R5D: "
            + repr(sorted(versioned)[:10])
        )
    return names


def _rebuild_jar(
    readable_jar: Path,
    project_classes: dict[str, bytes],
    prefixes: list[str],
    out: Path,
) -> None:
    entries: dict[str, bytes] = {}
    with zipfile.ZipFile(readable_jar) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = info.filename
            upper = name.upper()
            if (
                name.startswith("META-INF/")
                and upper.endswith(_SIGNATURE_SUFFIXES)
            ):
                raise CleanRebuildError(
                    f"signed archive metadata cannot survive rebuild: {name}"
                )
            if _is_project_class(name, prefixes):
                continue
            entries[name] = z.read(name)

    for name, data in project_classes.items():
        if name in entries:
            raise CleanRebuildError(
                f"rebuilt project class collides with retained entry: {name}"
            )
        entries[name] = data

    _write_stored_zip(out, entries)


def _stage_javac_sources(
    source_files: list[Path],
    source_root: Path,
    staging_root: Path,
) -> tuple[list[Path], dict[str, str]]:
    """Stage explicit javac inputs under case-unique physical parents.

    Windows javac/file-manager paths can still fold case even when the
    underlying NTFS directory is case-sensitive.  Distinct authoritative
    sources such as rs/A.java and rs/a.java are therefore staged under
    unique ordinal parents while preserving the original filename and bytes.

    The Java package/type declarations remain untouched.  All sources are
    still passed explicitly to javac, so package semantics come from source
    declarations rather than the physical staging directory.
    """
    staging_root.mkdir(parents=True, exist_ok=True)

    staged: list[Path] = []
    diagnostic_map: dict[str, str] = {}

    for index, source in enumerate(source_files):
        rel = source.relative_to(source_root).as_posix()
        target = (
            staging_root
            / f"{index:06d}"
            / source.name
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())

        staged.append(target)

        original = str(source)
        diagnostic_map[str(target)] = original
        diagnostic_map[target.as_posix()] = original

    if len(staged) != len(source_files):
        raise CleanRebuildError(
            "javac source staging count drifted"
        )

    casefolded = {
        str(path).casefold()
        for path in staged
    }
    if len(casefolded) != len(staged):
        raise CleanRebuildError(
            "javac source staging did not eliminate casefold collisions"
        )

    return staged, diagnostic_map


def _remap_javac_diagnostics(
    text: str,
    diagnostic_map: dict[str, str],
) -> str:
    value = text
    for staged in sorted(
        diagnostic_map,
        key=len,
        reverse=True,
    ):
        value = value.replace(
            staged,
            diagnostic_map[staged],
        )
    return value


def _clean_project_rebuild_legacy(
    recovered_manifest: dict[str, Any],
    source_readiness: dict[str, Any],
    readable_manifest: dict[str, Any],
    readable_jar: Path,
    build_authority: dict[str, Any],
    source_root: Path,
    *,
    out_dir: Path,
    javac_command: str = "javac",
    source_prefixes: list[str] | None = None,
    private_diagnostic_report_out: Path | None = None,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    readable_jar = readable_jar.resolve()

    try:
        all_files, javac_probe, release = _verify_authority(
            recovered_manifest,
            source_readiness,
            readable_manifest,
            readable_jar,
            build_authority,
            source_root,
            javac_command,
        )
    except ProgressiveCompileError as exc:
        raise CleanRebuildError(str(exc)) from exc

    try:
        source_derivation = _workspace_readable_derivation(
            recovered_manifest,
            readable_manifest,
        )
    except ProgressiveCompileError as exc:
        raise CleanRebuildError(str(exc)) from exc

    try:
        source_derivation = _workspace_readable_derivation(
            recovered_manifest,
            readable_manifest,
        )
    except ProgressiveCompileError as exc:
        raise CleanRebuildError(str(exc)) from exc

    prefixes = _normalize_prefixes(
        readable_manifest,
        source_prefixes,
    )
    source_files = _project_source_files(
        all_files,
        source_root,
        prefixes,
    )
    if not source_files:
        raise CleanRebuildError(
            "no project Java source matched the clean-build prefixes"
        )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise CleanRebuildError(
            "clean rebuild output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    dependency_jar = out_dir / "dependency-capsule.jar"
    dependency_sha, dependency_class_count = _dependency_capsule(
        readable_jar,
        prefixes,
        dependency_jar,
    )

    expected = _expected_project_classes(
        readable_jar,
        prefixes,
    )

    status = "compile_failed"
    diagnostic = ""
    javac_diagnostic_classification: dict[str, Any] | None = None
    missing: list[str] = []
    unexpected: list[str] = []
    rebuilt_sha: str | None = None
    rebuilt_index_summary: dict[str, Any] | None = None

    with tempfile.TemporaryDirectory(
        prefix=".spk-clean-rebuild-",
        dir=out_dir,
    ) as td:
        work_root = Path(td)
        classes = work_root / "classes"
        classes.mkdir()
        empty_sourcepath = work_root / "empty-sourcepath"
        empty_sourcepath.mkdir()
        args_path = work_root / "javac.args"

        staged_source_files, diagnostic_map = _stage_javac_sources(
            source_files,
            source_root,
            work_root / "source-inputs",
        )

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
            str(dependency_jar),
            "-d",
            str(classes),
        ]
        if release is not None:
            args.extend(["--release", str(release)])
        args.extend(
            str(path)
            for path in staged_source_files
        )
        args_path.write_text(
            "\n".join(_arg(value) for value in args) + "\n",
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                javac_probe["resolved_path"],
                "@" + str(args_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        raw_diagnostic = proc.stdout + proc.stderr
        remapped_diagnostic = _remap_javac_diagnostics(
            raw_diagnostic,
            diagnostic_map,
        )
        javac_diagnostic_classification = (
            classify_javac_diagnostics(remapped_diagnostic)
        )
        if private_diagnostic_report_out is not None:
            private_classification = classify_javac_diagnostics(
                remapped_diagnostic,
                include_identifiers=True,
            )
            if (
                private_classification["report_id"]
                != javac_diagnostic_classification["report_id"]
                or private_classification["frontier_id"]
                != javac_diagnostic_classification["frontier_id"]
            ):
                raise CleanRebuildError(
                    "private/public javac diagnostic authority drifted"
                )
            write_javac_diagnostic_report(
                private_classification,
                private_diagnostic_report_out,
            )
        diagnostic = _diagnostic(
            remapped_diagnostic,
            source_root=source_root,
            work_root=work_root,
        )

        if proc.returncode == 0:
            generated = _generated_classes(classes)
            generated_set = set(generated)
            missing = sorted(expected - generated_set)
            unexpected = sorted(generated_set - expected)
            if not missing and not unexpected:
                rebuilt_jar = out_dir / "rebuilt-client.jar"
                _rebuild_jar(
                    readable_jar,
                    generated,
                    prefixes,
                    rebuilt_jar,
                )
                rebuilt_sha = _sha256_file(rebuilt_jar)
                rebuilt_index = index_jar(rebuilt_jar)
                rebuilt_index_summary = rebuilt_index["summary"]
                if (
                    rebuilt_index["summary"][
                        "class_parse_error_count"
                    ]
                    != 0
                ):
                    raise CleanRebuildError(
                        "rebuilt client contains class parse errors"
                    )
                status = "complete"
            else:
                status = "class_set_mismatch"

    material = {
        "workspace_id": recovered_manifest.get("workspace_id"),
        "build_authority_id": build_authority.get("authority_id"),
        "readable_jar_sha256": readable_manifest.get(
            "output_sha256"
        ),
        "source_tree_sha256": recovered_manifest.get(
            "source_tree_sha256"
        ),
        "prefixes": prefixes,
        "status": status,
        "dependency_capsule_sha256": dependency_sha,
        "rebuilt_jar_sha256": rebuilt_sha,
    }
    if source_derivation is not None:
        material["source_derivation"] = source_derivation

    if source_derivation is not None:
        material["source_derivation"] = source_derivation

    rebuild_id = (
        "CLEANBUILD_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )

    report = {
        "schema_version": 1,
        "kind": "clean_project_rebuild_report",
        "rebuild_id": rebuild_id,
        "status": status,
        "workspace_id": recovered_manifest.get("workspace_id"),
        "build_id": recovered_manifest.get("build_id"),
        "source_authority_sha256": recovered_manifest.get(
            "source_authority_sha256"
        ),
        "readable_jar_sha256": readable_manifest.get(
            "output_sha256"
        ),
        "namespace_id": recovered_manifest.get("namespace_id"),
        "source_tree_sha256": recovered_manifest.get(
            "source_tree_sha256"
        ),
        "build_authority_id": build_authority.get("authority_id"),
        "source_scope": {
            "prefixes": prefixes,
            "project_source_files": len(source_files),
            "all_workspace_java_files": len(all_files),
            "javac_input_transport": (
                "case_unique_staged_explicit_sources"
            ),
        },
        "compiler": {
            "javac": javac_probe,
            "target_release": release,
            "diagnostic_classification": (
                {
                    "report_id": javac_diagnostic_classification[
                        "report_id"
                    ],
                    "frontier_id": javac_diagnostic_classification[
                        "frontier_id"
                    ],
                    "input_sha256": javac_diagnostic_classification[
                        "input_sha256"
                    ],
                    "summary": javac_diagnostic_classification[
                        "summary"
                    ],
                    "identifiers_included": False,
                }
                if javac_diagnostic_classification is not None
                else None
            ),
        },
        "dependency_capsule": {
            "path": "dependency-capsule.jar",
            "sha256": dependency_sha,
            "class_count": dependency_class_count,
            "contains_project_classes": False,
            "source": "verified_readable_client_non_project_classes",
        },
        "project_classes": {
            "expected_count": len(expected),
            "generated_count": (
                len(expected) - len(missing) + len(unexpected)
                if status != "compile_failed"
                else 0
            ),
            "missing": missing,
            "unexpected": unexpected,
            "binary_fallback_count": 0,
        },
        "diagnostic": diagnostic,
        "rebuilt_client": {
            "path": (
                "rebuilt-client.jar"
                if rebuilt_sha is not None
                else None
            ),
            "sha256": rebuilt_sha,
            "index_summary": rebuilt_index_summary,
        },
        "clean_project_build": status == "complete",
        "all_dependencies_rebuilt_from_source": False,
        "note": (
            "Project classes are rebuilt from recovered source with zero "
            "project-binary fallback. Bundled non-project dependency classes "
            "remain exact binary dependencies from the readable authority."
        ),
    }
    if source_derivation is not None:
        report["source_derivation"] = source_derivation

    if source_derivation is not None:
        report["source_derivation"] = source_derivation

    (out_dir / "clean-rebuild.json").write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def _copy_project_source_scope(
    source_files: list[Path],
    source_root: Path,
    scoped_root: Path,
) -> None:
    for source in source_files:
        rel = source.relative_to(source_root)
        target = scoped_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())


def _clean_project_rebuild_collision_derived(
    recovered_manifest: dict[str, Any],
    source_readiness: dict[str, Any],
    readable_manifest: dict[str, Any],
    readable_jar: Path,
    build_authority: dict[str, Any],
    source_root: Path,
    private_collision_plan_path: Path,
    *,
    out_dir: Path,
    javac_command: str = "javac",
    source_prefixes: list[str] | None = None,
    private_diagnostic_report_out: Path | None = None,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    readable_jar = readable_jar.resolve()
    private_collision_plan_path = (
        private_collision_plan_path.resolve()
    )
    if not private_collision_plan_path.is_file():
        raise CleanRebuildError(
            "private collision plan does not exist"
        )
    collision_plan_sha256 = _sha256_file(
        private_collision_plan_path
    )

    try:
        all_files, javac_probe, release = _verify_authority(
            recovered_manifest,
            source_readiness,
            readable_manifest,
            readable_jar,
            build_authority,
            source_root,
            javac_command,
        )
        source_derivation = _workspace_readable_derivation(
            recovered_manifest,
            readable_manifest,
        )
    except ProgressiveCompileError as exc:
        raise CleanRebuildError(str(exc)) from exc

    if source_derivation is None:
        raise CleanRebuildError(
            "collision-derived compile requires derived source authority"
        )

    prefixes = _normalize_prefixes(
        readable_manifest,
        source_prefixes,
    )
    source_files = _project_source_files(
        all_files,
        source_root,
        prefixes,
    )
    if not source_files:
        raise CleanRebuildError(
            "no project Java source matched the clean-build prefixes"
        )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise CleanRebuildError(
            "clean rebuild output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    canonical_before = source_tree_digest(source_root)[0]
    if canonical_before != recovered_manifest.get(
        "source_tree_sha256"
    ):
        raise CleanRebuildError(
            "canonical source tree authority drifted before "
            "collision-derived compile"
        )

    # Runtime dependency authority always comes from the original readable
    # JAR.  The transformed dependency emitted by the compile transport is
    # compile-only and is never packaged into the rebuilt client.
    dependency_jar = out_dir / "dependency-capsule.jar"
    dependency_sha, dependency_class_count = _dependency_capsule(
        readable_jar,
        prefixes,
        dependency_jar,
    )

    expected = _expected_project_classes(
        readable_jar,
        prefixes,
    )

    compile_root = out_dir / "collision-derived-compile"

    try:
        with tempfile.TemporaryDirectory(
            prefix=".spk-clean-collision-derived-source-",
            dir=out_dir,
        ) as td:
            scoped_source_root = Path(td) / "project-source"
            scoped_source_root.mkdir(parents=True)
            _copy_project_source_scope(
                source_files,
                source_root,
                scoped_source_root,
            )

            derived = compile_collision_derived_source(
                recovered_manifest,
                scoped_source_root,
                readable_jar,
                private_collision_plan_path,
                prefixes,
                compile_root,
                javac_command=javac_probe["resolved_path"],
                release=release,
                report_compile_failure=True,
                private_diagnostic_report_out=(
                    private_diagnostic_report_out
                ),
                diagnostic_source_root=source_root,
                canonical_source_root=source_root,
            )
    except CollisionDerivedCompileError as exc:
        raise CleanRebuildError(str(exc)) from exc

    derived_status = derived.get("status", "complete")
    generated: dict[str, bytes] = {}
    missing: list[str] = []
    unexpected: list[str] = []
    rebuilt_sha: str | None = None
    rebuilt_index_summary: dict[str, Any] | None = None

    if derived_status == "compile_failed":
        status = "compile_failed"
    elif derived_status == "complete":
        restored_root = compile_root / "restored-classes"
        generated = _generated_classes(restored_root)
        generated_set = set(generated)
        missing = sorted(expected - generated_set)
        unexpected = sorted(generated_set - expected)

        status = "class_set_mismatch"
        if not missing and not unexpected:
            rebuilt_jar = out_dir / "rebuilt-client.jar"
            _rebuild_jar(
                readable_jar,
                generated,
                prefixes,
                rebuilt_jar,
            )
            rebuilt_sha = _sha256_file(rebuilt_jar)
            rebuilt_index = index_jar(rebuilt_jar)
            rebuilt_index_summary = rebuilt_index["summary"]
            if (
                rebuilt_index["summary"][
                    "class_parse_error_count"
                ]
                != 0
            ):
                raise CleanRebuildError(
                    "rebuilt client contains class parse errors"
                )
            status = "complete"
    else:
        raise CleanRebuildError(
            "unsupported collision-derived compile status: "
            + repr(derived_status)
        )

    canonical_after = source_tree_digest(source_root)[0]
    if canonical_after != canonical_before:
        raise CleanRebuildError(
            "canonical recovered source changed during "
            "collision-derived rebuild"
        )

    material = {
        "workspace_id": recovered_manifest.get("workspace_id"),
        "build_authority_id": build_authority.get("authority_id"),
        "readable_jar_sha256": readable_manifest.get(
            "output_sha256"
        ),
        "source_tree_sha256": recovered_manifest.get(
            "source_tree_sha256"
        ),
        "prefixes": prefixes,
        "status": status,
        "dependency_capsule_sha256": dependency_sha,
        "rebuilt_jar_sha256": rebuilt_sha,
        "compile_transport": "collision_derived_remap",
        "collision_compile_id": derived["compile_id"],
        "collision_transform_id": derived[
            "collision_transform_id"
        ],
        "collision_plan_id": derived["collision_plan_id"],
        "collision_plan_sha256": collision_plan_sha256,
        "source_derivation": source_derivation,
    }
    rebuild_id = (
        "CLEANBUILD_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )

    report = {
        "schema_version": 1,
        "kind": "clean_project_rebuild_report",
        "rebuild_id": rebuild_id,
        "status": status,
        "workspace_id": recovered_manifest.get("workspace_id"),
        "build_id": recovered_manifest.get("build_id"),
        "source_authority_sha256": recovered_manifest.get(
            "source_authority_sha256"
        ),
        "readable_jar_sha256": readable_manifest.get(
            "output_sha256"
        ),
        "namespace_id": recovered_manifest.get("namespace_id"),
        "source_tree_sha256": recovered_manifest.get(
            "source_tree_sha256"
        ),
        "build_authority_id": build_authority.get("authority_id"),
        "source_derivation": source_derivation,
        "source_scope": {
            "prefixes": prefixes,
            "project_source_files": len(source_files),
            "all_workspace_java_files": len(all_files),
            "javac_input_transport": (
                "collision_derived_remap_argfile"
            ),
        },
        "compiler": {
            "javac": javac_probe,
            "target_release": release,
            "diagnostic_classification": derived[
                "compiler"
            ].get("diagnostic_classification"),
        },
        "dependency_capsule": {
            "path": "dependency-capsule.jar",
            "sha256": dependency_sha,
            "class_count": dependency_class_count,
            "contains_project_classes": False,
            "source": "verified_base_readable_non_project_classes",
        },
        "project_classes": {
            "expected_count": len(expected),
            "generated_count": len(generated),
            "missing": missing,
            "unexpected": unexpected,
            "binary_fallback_count": 0,
        },
        "diagnostic": "",
        "rebuilt_client": {
            "path": (
                "rebuilt-client.jar"
                if rebuilt_sha is not None
                else None
            ),
            "sha256": rebuilt_sha,
            "index_summary": rebuilt_index_summary,
        },
        "compile_transport": {
            "mode": "collision_derived_remap",
            "opt_in": True,
            "status": derived_status,
            "collision_compile_id": derived["compile_id"],
            "collision_transform_id": derived[
                "collision_transform_id"
            ],
            "collision_plan_id": derived["collision_plan_id"],
            "collision_plan_sha256": collision_plan_sha256,
            "collision_report_id": derived[
                "collision_report_id"
            ],
            "compiler": derived["compiler"],
            "compile_only_transformed_readable": derived[
                "compile_only_transformed_readable"
            ],
            "compile_only_transformed_dependency": derived[
                "compile_only_transformed_dependency"
            ],
            "mapping": derived["mapping"],
            "generated_transformed_classes": derived[
                "generated_transformed_classes"
            ],
            "restored_classes": derived[
                "restored_classes"
            ],
            "runtime_transformed_dependency_allowed": False,
            "runtime_dependency_source": (
                "original_verified_dependency_capsule"
            ),
            "canonical_source_tree_sha256_before": canonical_before,
            "canonical_source_tree_sha256_after": canonical_after,
            "canonical_source_modified": False,
        },
        "clean_project_build": status == "complete",
        "all_dependencies_rebuilt_from_source": False,
        "note": (
            (
                "Collision-derived source compiled against the exact "
                "matching transformed dependency namespace. Generated "
                "project references were restored to original JVM "
                "dependency identities; runtime dependency bytes remain "
                "the original verified readable authority."
            )
            if status == "complete"
            else (
                "Collision-derived compile preserved its redacted javac "
                "frontier. No transformed dependency bytes are runtime "
                "eligible, and no rebuilt runtime JAR is emitted until "
                "compilation completes."
            )
        ),
    }

    (out_dir / "clean-rebuild.json").write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def _clean_project_rebuild_virtualized(
    recovered_manifest: dict[str, Any],
    source_readiness: dict[str, Any],
    readable_manifest: dict[str, Any],
    readable_jar: Path,
    build_authority: dict[str, Any],
    source_root: Path,
    private_namespace_alias_plan: dict[str, Any] | None,
    *,
    out_dir: Path,
    javac_command: str = "javac",
    source_prefixes: list[str] | None = None,
    private_diagnostic_report_out: Path | None = None,
    auto_namespace_alias: bool = False,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    readable_jar = readable_jar.resolve()

    try:
        all_files, javac_probe, release = _verify_authority(
            recovered_manifest,
            source_readiness,
            readable_manifest,
            readable_jar,
            build_authority,
            source_root,
            javac_command,
        )
    except ProgressiveCompileError as exc:
        raise CleanRebuildError(str(exc)) from exc

    if release is None:
        raise CleanRebuildError(
            "namespace virtualization requires an explicit target release"
        )

    prefixes = _normalize_prefixes(
        readable_manifest,
        source_prefixes,
    )
    source_files = _project_source_files(
        all_files,
        source_root,
        prefixes,
    )
    if not source_files:
        raise CleanRebuildError(
            "no project Java source matched the clean-build prefixes"
        )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise CleanRebuildError(
            "clean rebuild output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    canonical_before = source_tree_digest(source_root)[0]
    if canonical_before != recovered_manifest.get(
        "source_tree_sha256"
    ):
        raise CleanRebuildError(
            "canonical source tree authority drifted before virtualized compile"
        )

    dependency_jar = out_dir / "dependency-capsule.jar"
    dependency_sha, dependency_class_count = _dependency_capsule(
        readable_jar,
        prefixes,
        dependency_jar,
    )

    alias_plan_source = "explicit"
    if private_namespace_alias_plan is None:
        if not auto_namespace_alias:
            raise CleanRebuildError(
                "namespace virtualization requires an explicit alias plan "
                "or auto namespace alias mode"
            )
        try:
            private_namespace_alias_plan = build_namespace_alias_plan(
                dependency_jar,
                include_identifiers=True,
            )
        except NamespaceAliasPlanError as exc:
            raise CleanRebuildError(str(exc)) from exc

        mapped = int(
            private_namespace_alias_plan.get("summary", {}).get(
                "mapped_class_identity_count",
                0,
            )
        )
        if mapped <= 0:
            raise CleanRebuildError(
                "auto namespace alias mode found no class/package collisions"
            )
        alias_plan_source = "auto_dependency_capsule"

    expected = _expected_project_classes(
        readable_jar,
        prefixes,
    )

    compile_root = out_dir / "namespace-virtualized-compile"

    try:
        with tempfile.TemporaryDirectory(
            prefix=".spk-clean-virtualized-source-",
            dir=out_dir,
        ) as td:
            scoped_source_root = Path(td) / "project-source"
            scoped_source_root.mkdir(parents=True)
            _copy_project_source_scope(
                source_files,
                source_root,
                scoped_source_root,
            )

            virtualized = compile_with_namespace_virtualization(
                private_namespace_alias_plan,
                scoped_source_root,
                dependency_jar,
                compile_root,
                javac_command=javac_probe["resolved_path"],
                release=int(release),
                report_compile_failure=True,
                private_diagnostic_report_out=(
                    private_diagnostic_report_out
                ),
                diagnostic_source_root=source_root,
            )
    except NamespaceVirtualizedCompileError as exc:
        raise CleanRebuildError(str(exc)) from exc

    virtualized_status = virtualized.get("status", "complete")
    generated: dict[str, bytes] = {}
    missing: list[str] = []
    unexpected: list[str] = []
    rebuilt_sha: str | None = None
    rebuilt_index_summary: dict[str, Any] | None = None

    if virtualized_status == "compile_failed":
        status = "compile_failed"
    elif virtualized_status == "complete":
        restored_root = compile_root / "restored-classes"
        generated = _generated_classes(restored_root)
        generated_set = set(generated)
        missing = sorted(expected - generated_set)
        unexpected = sorted(generated_set - expected)

        status = "class_set_mismatch"
        if not missing and not unexpected:
            rebuilt_jar = out_dir / "rebuilt-client.jar"
            _rebuild_jar(
                readable_jar,
                generated,
                prefixes,
                rebuilt_jar,
            )
            rebuilt_sha = _sha256_file(rebuilt_jar)
            rebuilt_index = index_jar(rebuilt_jar)
            rebuilt_index_summary = rebuilt_index["summary"]
            if (
                rebuilt_index["summary"][
                    "class_parse_error_count"
                ]
                != 0
            ):
                raise CleanRebuildError(
                    "rebuilt client contains class parse errors"
                )
            status = "complete"
    else:
        raise CleanRebuildError(
            "unsupported namespace-virtualized compile status: "
            + repr(virtualized_status)
        )

    canonical_after = source_tree_digest(source_root)[0]
    if canonical_after != canonical_before:
        raise CleanRebuildError(
            "canonical recovered source changed during virtualized rebuild"
        )

    material = {
        "workspace_id": recovered_manifest.get("workspace_id"),
        "build_authority_id": build_authority.get("authority_id"),
        "readable_jar_sha256": readable_manifest.get(
            "output_sha256"
        ),
        "source_tree_sha256": recovered_manifest.get(
            "source_tree_sha256"
        ),
        "prefixes": prefixes,
        "status": status,
        "dependency_capsule_sha256": dependency_sha,
        "rebuilt_jar_sha256": rebuilt_sha,
        "compile_transport": "namespace_virtualized",
        "namespace_compile_id": virtualized["compile_id"],
        "alias_plan_id": virtualized["alias_plan_id"],
    }
    rebuild_id = (
        "CLEANBUILD_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )

    report = {
        "schema_version": 1,
        "kind": "clean_project_rebuild_report",
        "rebuild_id": rebuild_id,
        "status": status,
        "workspace_id": recovered_manifest.get("workspace_id"),
        "build_id": recovered_manifest.get("build_id"),
        "source_authority_sha256": recovered_manifest.get(
            "source_authority_sha256"
        ),
        "readable_jar_sha256": readable_manifest.get(
            "output_sha256"
        ),
        "namespace_id": recovered_manifest.get("namespace_id"),
        "source_tree_sha256": recovered_manifest.get(
            "source_tree_sha256"
        ),
        "build_authority_id": build_authority.get("authority_id"),
        "source_scope": {
            "prefixes": prefixes,
            "project_source_files": len(source_files),
            "all_workspace_java_files": len(all_files),
            "javac_input_transport": (
                "namespace_virtualized_overlay_argfile"
            ),
        },
        "compiler": {
            "javac": javac_probe,
            "target_release": release,
            "diagnostic_classification": virtualized[
                "compiler"
            ].get("diagnostic_classification"),
        },
        "dependency_capsule": {
            "path": "dependency-capsule.jar",
            "sha256": dependency_sha,
            "class_count": dependency_class_count,
            "contains_project_classes": False,
            "source": "verified_readable_client_non_project_classes",
        },
        "project_classes": {
            "expected_count": len(expected),
            "generated_count": len(generated),
            "missing": missing,
            "unexpected": unexpected,
            "binary_fallback_count": 0,
        },
        "diagnostic": "",
        "rebuilt_client": {
            "path": (
                "rebuilt-client.jar"
                if rebuilt_sha is not None
                else None
            ),
            "sha256": rebuilt_sha,
            "index_summary": rebuilt_index_summary,
        },
        "compile_transport": {
            "mode": "namespace_virtualized",
            "opt_in": True,
            "status": virtualized_status,
            "namespace_compile_id": virtualized["compile_id"],
            "alias_plan_id": virtualized["alias_plan_id"],
            "alias_plan_source": alias_plan_source,
            "compiler": virtualized["compiler"],
            "compile_only_alias_dependency": virtualized[
                "compile_only_alias_dependency"
            ],
            "overlay": virtualized["overlay"],
            "restored_classes": virtualized["restored_classes"],
            "runtime_alias_dependency_allowed": False,
            "runtime_dependency_source": (
                "original_verified_dependency_capsule"
            ),
            "canonical_source_tree_sha256_before": canonical_before,
            "canonical_source_tree_sha256_after": canonical_after,
            "canonical_source_modified": False,
        },
        "clean_project_build": status == "complete",
        "all_dependencies_rebuilt_from_source": False,
        "note": (
            (
                "Namespace virtualization completed compilation. Project "
                "classes are rebuilt with zero project-binary fallback; "
                "the runtime JAR retains original dependency bytes and "
                "restored original JVM identities."
            )
            if status == "complete"
            else (
                "Namespace virtualization preserved the redacted javac "
                "frontier without publishing alias runtime classes. No "
                "rebuilt runtime JAR is emitted until compilation completes."
            )
        ),
    }
    (out_dir / "clean-rebuild.json").write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def _project_classes_from_jar(
    path: Path,
    prefixes: list[str],
) -> dict[str, bytes]:
    rows: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.is_dir() or not info.filename.endswith(".class"):
                    continue
                if not _is_project_class(info.filename, prefixes):
                    raise CleanRebuildError(
                        "restored project JAR contains a class outside "
                        "the clean-build project scope: "
                        + info.filename
                    )
                rows[info.filename] = archive.read(info)
    except (OSError, zipfile.BadZipFile) as exc:
        raise CleanRebuildError(
            "invalid restored project JAR"
        ) from exc

    if not rows:
        raise CleanRebuildError(
            "restored project JAR contains no project classes"
        )
    return rows


def _clean_project_rebuild_official_first(
    recovered_manifest: dict[str, Any],
    source_readiness: dict[str, Any],
    readable_manifest: dict[str, Any],
    readable_jar: Path,
    build_authority: dict[str, Any],
    source_root: Path,
    overlay_manifest_path: Path,
    overlay_source_root: Path,
    private_replacement_plan_path: Path,
    private_reverse_plan_path: Path,
    official_artifacts: list[Path],
    *,
    out_dir: Path,
    java_command: str = "java",
    javac_command: str = "javac",
    source_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    readable_jar = readable_jar.resolve()

    try:
        all_files, javac_probe, authority_release = _verify_authority(
            recovered_manifest,
            source_readiness,
            readable_manifest,
            readable_jar,
            build_authority,
            source_root,
            javac_command,
        )
    except ProgressiveCompileError as exc:
        raise CleanRebuildError(str(exc)) from exc

    try:
        source_derivation = _workspace_readable_derivation(
            recovered_manifest,
            readable_manifest,
        )
    except ProgressiveCompileError as exc:
        raise CleanRebuildError(str(exc)) from exc
    if source_derivation is not None:
        raise CleanRebuildError(
            "official-first restored clean rebuild does not compose "
            "with collision-derived source authority"
        )

    prefixes = _normalize_prefixes(
        readable_manifest,
        source_prefixes,
    )
    source_files = _project_source_files(
        all_files,
        source_root,
        prefixes,
    )
    if not source_files:
        raise CleanRebuildError(
            "no project Java source matched the clean-build prefixes"
        )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise CleanRebuildError(
            "clean rebuild output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    expected = _expected_project_classes(
        readable_jar,
        prefixes,
    )

    runtime_dependency_jar = out_dir / "dependency-capsule.jar"
    runtime_dependency_sha, runtime_dependency_count = (
        _dependency_capsule(
            readable_jar,
            prefixes,
            runtime_dependency_jar,
        )
    )

    derived_dir = out_dir / "official-first-derived"
    try:
        derived = compile_official_overlay_and_restore(
            overlay_manifest_path,
            overlay_source_root,
            source_root,
            private_replacement_plan_path,
            private_reverse_plan_path,
            readable_jar,
            official_artifacts,
            derived_dir,
            project_prefixes=tuple(prefixes),
            java_command=java_command,
            javac_command=javac_command,
        )
    except DependencyOfficialDerivedCompileError as exc:
        raise CleanRebuildError(str(exc)) from exc

    if derived.get("status") != "complete":
        raise CleanRebuildError(
            "official-first derived compile did not complete"
        )

    summary = derived.get("summary", {})
    required_true = (
        "reverse_reference_surface_match",
        "restored_project_bytecode_ready_for_runtime_assembly",
    )
    for key in required_true:
        if summary.get(key) is not True:
            raise CleanRebuildError(
                "official-first derived compile lacks required proof: "
                + key
            )

    required_false = (
        "compile_dependency_contains_project_classes",
        "canonical_source_modified",
        "bundled_runtime_dependency_modified",
        "official_compile_artifacts_modified",
        "official_dependencies_runtime_allowed",
    )
    for key in required_false:
        if summary.get(key) is not False:
            raise CleanRebuildError(
                "official-first derived compile violates runtime boundary: "
                + key
            )

    if int(summary.get("project_binary_fallback_count", -1)) != 0:
        raise CleanRebuildError(
            "official-first derived compile used project binary fallback"
        )

    if (
        authority_release is not None
        and int(derived.get("release", -1)) != authority_release
    ):
        raise CleanRebuildError(
            "official-first Java release differs from build authority"
        )

    restored_path = (
        derived_dir / "restored-bundled-project.jar"
    )
    restored_classes = _project_classes_from_jar(
        restored_path,
        prefixes,
    )
    restored_set = set(restored_classes)
    missing = sorted(expected - restored_set)
    unexpected = sorted(restored_set - expected)

    status = (
        "complete"
        if not missing and not unexpected
        else "class_set_mismatch"
    )

    rebuilt_sha: str | None = None
    rebuilt_index_summary: dict[str, Any] | None = None
    if status == "complete":
        rebuilt_jar = out_dir / "rebuilt-client.jar"
        _rebuild_jar(
            readable_jar,
            restored_classes,
            prefixes,
            rebuilt_jar,
        )
        rebuilt_sha = _sha256_file(rebuilt_jar)
        rebuilt_index = index_jar(rebuilt_jar)
        rebuilt_index_summary = rebuilt_index["summary"]
        if rebuilt_index_summary["class_parse_error_count"] != 0:
            raise CleanRebuildError(
                "official-first rebuilt client contains class parse errors"
            )

    material = {
        "workspace_id": recovered_manifest.get("workspace_id"),
        "build_authority_id": build_authority.get("authority_id"),
        "readable_jar_sha256": readable_manifest.get(
            "output_sha256"
        ),
        "source_tree_sha256": recovered_manifest.get(
            "source_tree_sha256"
        ),
        "prefixes": prefixes,
        "status": status,
        "compile_id": derived.get("compile_id"),
        "overlay_id": derived.get("overlay_id"),
        "replacement_plan_id": derived.get("replacement_plan_id"),
        "reverse_plan_id": derived.get("reverse_plan_id"),
        "reverse_application_id": derived.get(
            "reverse_application_id"
        ),
        "runtime_dependency_capsule_sha256": runtime_dependency_sha,
        "restored_project_jar_sha256": derived.get(
            "restored_project_jar_sha256"
        ),
        "rebuilt_jar_sha256": rebuilt_sha,
    }
    rebuild_id = (
        "CLEANBUILD_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )

    report = {
        "schema_version": 1,
        "kind": "clean_project_rebuild_report",
        "rebuild_id": rebuild_id,
        "status": status,
        "workspace_id": recovered_manifest.get("workspace_id"),
        "build_id": recovered_manifest.get("build_id"),
        "source_authority_sha256": recovered_manifest.get(
            "source_authority_sha256"
        ),
        "readable_jar_sha256": readable_manifest.get(
            "output_sha256"
        ),
        "namespace_id": recovered_manifest.get("namespace_id"),
        "source_tree_sha256": recovered_manifest.get(
            "source_tree_sha256"
        ),
        "build_authority_id": build_authority.get("authority_id"),
        "source_scope": {
            "prefixes": prefixes,
            "project_source_files": len(source_files),
            "all_workspace_java_files": len(all_files),
            "javac_input_transport": (
                "official_api_overlay_then_bundled_bytecode_restore"
            ),
        },
        "compiler": {
            "javac": javac_probe,
            "target_release": derived.get("release"),
            "diagnostic_classification": None,
        },
        "dependency_capsule": {
            "path": "dependency-capsule.jar",
            "sha256": runtime_dependency_sha,
            "class_count": runtime_dependency_count,
            "contains_project_classes": False,
            "source": "verified_readable_client_non_project_classes",
        },
        "project_classes": {
            "expected_count": len(expected),
            "generated_count": len(restored_classes),
            "missing": missing,
            "unexpected": unexpected,
            "binary_fallback_count": 0,
        },
        "diagnostic": "",
        "rebuilt_client": {
            "path": (
                "rebuilt-client.jar"
                if rebuilt_sha is not None
                else None
            ),
            "sha256": rebuilt_sha,
            "index_summary": rebuilt_index_summary,
        },
        "compile_transport": {
            "mode": "official_first_restored",
            "opt_in": True,
            "status": derived["status"],
            "official_compile_id": derived["compile_id"],
            "overlay_id": derived["overlay_id"],
            "replacement_plan_id": derived["replacement_plan_id"],
            "reverse_plan_id": derived["reverse_plan_id"],
            "reverse_application_id": derived[
                "reverse_application_id"
            ],
            "official_artifact_sha256": derived[
                "official_artifact_sha256"
            ],
            "compile_dependency_capsule_sha256": derived[
                "compile_dependency_capsule_sha256"
            ],
            "compile_dependency_capsule_class_count": derived[
                "compile_dependency_capsule_class_count"
            ],
            "generated_project_jar_sha256": derived[
                "generated_project_jar_sha256"
            ],
            "restored_project_jar_sha256": derived[
                "restored_project_jar_sha256"
            ],
            "project_binary_fallback_count": 0,
            "runtime_official_dependencies_allowed": False,
            "runtime_dependency_source": (
                "original_verified_readable_non_project_bytes"
            ),
            "canonical_source_modified": False,
            "bundled_runtime_dependency_modified": False,
            "restored_project_bytecode_ready_for_runtime_assembly": True,
        },
        "clean_project_build": status == "complete",
        "all_dependencies_rebuilt_from_source": False,
        "note": (
            "Official dependency APIs are compile-only inputs. Generated "
            "project bytecode is restored to bundled dependency identities, "
            "and the runtime JAR retains the original verified non-project "
            "dependency bytes."
        ),
    }

    (out_dir / "clean-rebuild.json").write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def clean_project_rebuild(
    recovered_manifest: dict[str, Any],
    source_readiness: dict[str, Any],
    readable_manifest: dict[str, Any],
    readable_jar: Path,
    build_authority: dict[str, Any],
    source_root: Path,
    *,
    out_dir: Path,
    javac_command: str = "javac",
    source_prefixes: list[str] | None = None,
    private_diagnostic_report_out: Path | None = None,
    private_namespace_alias_plan: dict[str, Any] | None = None,
    auto_namespace_alias: bool = False,
    private_collision_plan_path: Path | None = None,
    official_first_restored: bool = False,
    official_overlay_manifest_path: Path | None = None,
    official_overlay_source_root: Path | None = None,
    private_dependency_replacement_plan_path: Path | None = None,
    private_dependency_reverse_plan_path: Path | None = None,
    official_artifacts: list[Path] | None = None,
    java_command: str = "java",
) -> dict[str, Any]:
    try:
        source_derivation = _workspace_readable_derivation(
            recovered_manifest,
            readable_manifest,
        )
    except ProgressiveCompileError as exc:
        raise CleanRebuildError(str(exc)) from exc

    official_inputs_supplied = any(
        value is not None
        for value in (
            official_overlay_manifest_path,
            official_overlay_source_root,
            private_dependency_replacement_plan_path,
            private_dependency_reverse_plan_path,
            official_artifacts,
        )
    )

    if official_first_restored:
        if source_derivation is not None:
            raise CleanRebuildError(
                "official-first restored transport does not compose with "
                "collision-derived source authority"
            )
        if (
            private_namespace_alias_plan is not None
            or auto_namespace_alias
            or private_collision_plan_path is not None
        ):
            raise CleanRebuildError(
                "official-first restored transport is mutually exclusive "
                "with namespace/collision compile transports"
            )
        if (
            official_overlay_manifest_path is None
            or official_overlay_source_root is None
            or private_dependency_replacement_plan_path is None
            or private_dependency_reverse_plan_path is None
            or not official_artifacts
        ):
            raise CleanRebuildError(
                "official-first restored transport requires overlay "
                "manifest/source, private replacement/reverse plans, and "
                "at least one official artifact"
            )
        return _clean_project_rebuild_official_first(
            recovered_manifest,
            source_readiness,
            readable_manifest,
            readable_jar,
            build_authority,
            source_root,
            official_overlay_manifest_path,
            official_overlay_source_root,
            private_dependency_replacement_plan_path,
            private_dependency_reverse_plan_path,
            list(official_artifacts),
            out_dir=out_dir,
            java_command=java_command,
            javac_command=javac_command,
            source_prefixes=source_prefixes,
        )

    if official_inputs_supplied:
        raise CleanRebuildError(
            "official-first inputs require explicit "
            "official_first_restored opt-in"
        )

    if source_derivation is not None:
        if (
            private_namespace_alias_plan is not None
            or auto_namespace_alias
        ):
            raise CleanRebuildError(
                "collision-derived source requires the matching "
                "blocker-remap compile transport; namespace alias "
                "virtualization is not valid for this source authority"
            )
        if private_collision_plan_path is None:
            raise CleanRebuildError(
                "collision-derived source requires an explicit private "
                "collision plan path"
            )
        return _clean_project_rebuild_collision_derived(
            recovered_manifest,
            source_readiness,
            readable_manifest,
            readable_jar,
            build_authority,
            source_root,
            private_collision_plan_path,
            out_dir=out_dir,
            javac_command=javac_command,
            source_prefixes=source_prefixes,
            private_diagnostic_report_out=private_diagnostic_report_out,
        )

    if private_collision_plan_path is not None:
        raise CleanRebuildError(
            "collision plan transport was supplied for a non-derived "
            "source workspace"
        )

    if (
        private_namespace_alias_plan is not None
        and auto_namespace_alias
    ):
        raise CleanRebuildError(
            "explicit namespace alias plan and auto namespace alias "
            "mode are mutually exclusive"
        )

    if (
        private_namespace_alias_plan is None
        and not auto_namespace_alias
    ):
        return _clean_project_rebuild_legacy(
            recovered_manifest,
            source_readiness,
            readable_manifest,
            readable_jar,
            build_authority,
            source_root,
            out_dir=out_dir,
            javac_command=javac_command,
            source_prefixes=source_prefixes,
            private_diagnostic_report_out=private_diagnostic_report_out,
        )

    return _clean_project_rebuild_virtualized(
        recovered_manifest,
        source_readiness,
        readable_manifest,
        readable_jar,
        build_authority,
        source_root,
        private_namespace_alias_plan,
        out_dir=out_dir,
        javac_command=javac_command,
        source_prefixes=source_prefixes,
        private_diagnostic_report_out=private_diagnostic_report_out,
        auto_namespace_alias=auto_namespace_alias,
    )
