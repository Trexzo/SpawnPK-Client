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
from .javac_diagnostics import classify_javac_diagnostics
from .progressive_compile import (
    ProgressiveCompileError,
    _verify_authority,
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
