from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any


class ProgressiveCompileError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_tree_digest(root: Path) -> tuple[str, list[Path]]:
    files = sorted(\n        root.rglob("*.java"),\n        key=lambda path: path.relative_to(root).as_posix(),\n    )
    h = hashlib.sha256()
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest(), files


def _probe_javac(command: str) -> dict[str, Any]:
    found = shutil.which(command)
    if found is None:
        raise ProgressiveCompileError(
            f"javac executable not found on PATH: {command}"
        )
    path = Path(found).resolve()
    proc = subprocess.run(
        [str(path), "-version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise ProgressiveCompileError(
            "javac -version failed: " + proc.stdout + proc.stderr
        )
    return {
        "resolved_path": str(path),
        "binary_sha256": (
            _sha256_file(path)
            if path.is_file()
            else None
        ),
        "version_output": (proc.stdout + proc.stderr).strip(),
    }


def _normalize_diagnostic(
    text: str,
    *,
    source_root: Path,
    work_root: Path,
    limit: int = 20000,
) -> str:
    value = text.replace("\r\n", "\n").replace("\r", "\n")
    replacements = [
        (str(source_root), "<SOURCE>"),
        (source_root.as_posix(), "<SOURCE>"),
        (str(work_root), "<WORK>"),
        (work_root.as_posix(), "<WORK>"),
    ]
    for old, new in replacements:
        value = value.replace(old, new)
    if len(value) > limit:
        value = value[:limit] + "\n<TRUNCATED>\n"
    return value


def _copy_tree_unique(
    src: Path,
    dst: Path,
) -> int:
    count = 0
    for path in sorted(\n        src.rglob("*.class"),\n        key=lambda path: path.relative_to(src).as_posix(),\n    ):
        rel = path.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        data = path.read_bytes()
        if target.exists():
            if target.read_bytes() != data:
                raise ProgressiveCompileError(
                    f"compiled class collision with different bytes: {rel.as_posix()}"
                )
        else:
            target.write_bytes(data)
            count += 1
    return count


def _verify_authority(
    recovered_manifest: dict[str, Any],
    source_readiness: dict[str, Any],
    readable_manifest: dict[str, Any],
    readable_jar: Path,
    build_authority: dict[str, Any],
    source_root: Path,
    javac_command: str,
) -> tuple[list[Path], dict[str, Any], int | None]:
    if (
        recovered_manifest.get("schema_version") != 1
        or recovered_manifest.get("kind")
        != "recovered_source_workspace_manifest"
    ):
        raise ProgressiveCompileError(
            "unsupported recovered-source manifest"
        )
    if (
        source_readiness.get("schema_version") != 1
        or source_readiness.get("kind")
        != "source_readiness_report"
    ):
        raise ProgressiveCompileError(
            "unsupported source-readiness report"
        )
    if (
        readable_manifest.get("schema_version") != 1
        or readable_manifest.get("kind")
        != "readable_client_build_manifest"
        or readable_manifest.get("status") != "complete"
        or readable_manifest.get("verification_pass") is not True
    ):
        raise ProgressiveCompileError(
            "progressive compilation requires a complete verified readable build"
        )
    if (
        build_authority.get("schema_version") != 1
        or build_authority.get("kind")
        != "build_authority_manifest"
    ):
        raise ProgressiveCompileError(
            "unsupported build-authority manifest"
        )

    tree_sha, files = _source_tree_digest(source_root)
    expected_tree = str(
        recovered_manifest.get("source_tree_sha256", "")
    ).lower()
    if tree_sha.lower() != expected_tree:
        raise ProgressiveCompileError(
            "source tree SHA-256 does not match recovered-source manifest"
        )
    if (
        str(source_readiness.get("source_tree_sha256", "")).lower()
        != tree_sha.lower()
    ):
        raise ProgressiveCompileError(
            "source-readiness report is stale for this source tree"
        )

    readable_jar = readable_jar.resolve()
    if not readable_jar.is_file():
        raise ProgressiveCompileError(
            f"readable fallback JAR does not exist: {readable_jar}"
        )
    readable_sha = _sha256_file(readable_jar)
    if (
        readable_sha.lower()
        != str(readable_manifest.get("output_sha256", "")).lower()
    ):
        raise ProgressiveCompileError(
            "readable fallback JAR SHA-256 does not match readable manifest"
        )

    authority_sha = str(
        recovered_manifest.get("source_authority_sha256", "")
    ).lower()
    if (
        str(build_authority.get("source_sha256", "")).lower()
        != authority_sha
    ):
        raise ProgressiveCompileError(
            "build authority is for a different source authority"
        )

    probe = _probe_javac(javac_command)
    expected_probe = (
        build_authority.get("compiler_runtime", {})
        .get("javac", {})
    )
    expected_version = expected_probe.get("version_output")
    if (
        isinstance(expected_version, str)
        and expected_version
        and probe["version_output"] != expected_version
    ):
        raise ProgressiveCompileError(
            "current javac version does not match build-authority probe"
        )
    expected_binary = expected_probe.get("binary_sha256")
    if (
        isinstance(expected_binary, str)
        and expected_binary
        and probe["binary_sha256"] != expected_binary
    ):
        raise ProgressiveCompileError(
            "current javac binary SHA-256 does not match build authority"
        )

    release = build_authority.get("bytecode", {}).get(
        "dominant_java_release"
    )
    if release is not None and (
        not isinstance(release, int)
        or isinstance(release, bool)
        or release < 1
    ):
        raise ProgressiveCompileError(
            "invalid dominant Java release in build authority"
        )
    return files, probe, release


def progressive_compile(
    recovered_manifest: dict[str, Any],
    source_readiness: dict[str, Any],
    readable_manifest: dict[str, Any],
    readable_jar: Path,
    build_authority: dict[str, Any],
    source_root: Path,
    *,
    out_dir: Path,
    javac_command: str = "javac",
    batch_size: int = 64,
    source_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise ProgressiveCompileError(
            f"source root does not exist: {source_root}"
        )
    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or batch_size < 1
    ):
        raise ProgressiveCompileError(
            "batch_size must be a positive integer"
        )

    files, javac_probe, release = _verify_authority(
        recovered_manifest,
        source_readiness,
        readable_manifest,
        readable_jar,
        build_authority,
        source_root,
        javac_command,
    )
    if not files:
        raise ProgressiveCompileError(
            "source workspace contains no Java files"
        )

    if source_prefixes is None:
        target_package = str(
            readable_manifest.get("target_package", "")
        ).strip("/")
        source_prefixes = ["rs/"]
        if target_package:
            source_prefixes.append(target_package + "/")
    normalized_prefixes: list[str] = []
    for prefix in source_prefixes:
        if not isinstance(prefix, str) or not prefix:
            raise ProgressiveCompileError(
                "source prefixes must be non-empty strings"
            )
        normalized = prefix.replace("\\", "/").lstrip("/")
        if normalized and not normalized.endswith("/"):
            normalized += "/"
        normalized_prefixes.append(normalized)
    normalized_prefixes = sorted(set(normalized_prefixes))

    all_files = files
    files = [
        path
        for path in all_files
        if any(
            path.relative_to(source_root).as_posix().startswith(prefix)
            for prefix in normalized_prefixes
        )
    ]
    if not files:
        raise ProgressiveCompileError(
            "no Java source files matched project source prefixes "
            + repr(normalized_prefixes)
        )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ProgressiveCompileError(
            "progressive compile output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    final_classes = out_dir / "classes"
    final_classes.mkdir()

    passed: set[Path] = set()
    failed: dict[Path, str] = {}
    invocation_count = 0
    generated_class_count = 0

    with tempfile.TemporaryDirectory(
        prefix="spk-progressive-compile-"
    ) as td:
        work_root = Path(td)
        empty_sourcepath = work_root / "empty-sourcepath"
        empty_sourcepath.mkdir()

        def compile_group(group: list[Path]) -> None:
            nonlocal invocation_count, generated_class_count
            invocation_count += 1
            attempt = work_root / f"attempt-{invocation_count:06d}"
            classes = attempt / "classes"
            classes.mkdir(parents=True)

            javac_path = javac_probe["resolved_path"]
            cmd = [
                javac_path,
                "-proc:none",
                "-encoding",
                "UTF-8",
                "-Xlint:none",
                "-sourcepath",
                str(empty_sourcepath),
                "-classpath",
                str(readable_jar.resolve()),
                "-d",
                str(classes),
            ]
            if release is not None:
                cmd.extend(["--release", str(release)])
            cmd.extend(str(path) for path in group)

            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if proc.returncode == 0:
                generated_class_count += _copy_tree_unique(
                    classes,
                    final_classes,
                )
                passed.update(group)
                return

            if len(group) > 1:
                midpoint = len(group) // 2
                compile_group(group[:midpoint])
                compile_group(group[midpoint:])
                return

            diagnostic = _normalize_diagnostic(
                proc.stdout + proc.stderr,
                source_root=source_root,
                work_root=work_root,
            )
            failed[group[0]] = diagnostic

        for start in range(0, len(files), batch_size):
            compile_group(files[start : start + batch_size])

    rows: list[dict[str, Any]] = []
    for path in files:
        rel = path.relative_to(source_root).as_posix()
        if path in passed:
            rows.append(
                {
                    "path": rel,
                    "status": "compiled_with_readable_fallback",
                    "diagnostic": None,
                }
            )
        else:
            rows.append(
                {
                    "path": rel,
                    "status": "compile_failed",
                    "diagnostic": failed.get(
                        path,
                        "compiler group failed without isolated diagnostic",
                    ),
                }
            )

    compiled_count = len(passed)
    failed_count = len(files) - compiled_count
    percent = round(
        100.0 * compiled_count / len(files),
        4,
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
        "compiled_count": compiled_count,
        "failed_count": failed_count,
        "batch_size": batch_size,
        "source_prefixes": normalized_prefixes,
        "javac_version": javac_probe["version_output"],
    }
    run_id = (
        "PROGCOMPILE_"
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
        "kind": "progressive_compile_report",
        "run_id": run_id,
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
        "javac": javac_probe,
        "target_release": release,
        "source_scope": {
            "prefixes": normalized_prefixes,
            "all_workspace_java_files": len(all_files),
            "scoped_project_java_files": len(files),
        },
        "fallback_classpath": {
            "kind": "verified_readable_client_jar",
            "sha256": readable_manifest.get("output_sha256"),
            "clean_build": False,
        },
        "summary": {
            "java_file_count": len(files),
            "compiled_file_count": compiled_count,
            "failed_file_count": failed_count,
            "compile_percent": percent,
            "compiler_invocations": invocation_count,
            "generated_class_count": generated_class_count,
            "full_source_compile_ready": failed_count == 0,
            "clean_build": False,
        },
        "files": rows,
    }

    (out_dir / "progressive-compile.json").write_text(
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
