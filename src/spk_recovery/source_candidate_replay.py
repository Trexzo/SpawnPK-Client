"""Compile a private Java source candidate without original-client dependencies.

Read-only pinned inputs; no public source, original JAR, or canonical writes.
Generated classfiles, candidate JAR and detailed report remain local/private.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any
from zipfile import ZipFile, ZipInfo, ZIP_STORED

from .source_class_method_matrix import build_class_method_matrix, ClassMethodMatrixError
from .source_tree_fingerprint import SourceTreeError, fingerprint_java_source_tree


class SourceCandidateReplayError(ValueError):
    """Unsafe or unsupported private Java compilation/evidence."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise SourceCandidateReplayError(reason)


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _pin(path: Path, expected: str, kind: str) -> str:
    _require(type(expected) is str and re.fullmatch(r"[0-9a-fA-F]{64}", expected) is not None,
             f"{kind}_INVALID_SHA256_PIN")
    _require(path.is_file() and not path.is_symlink(), f"{kind}_MISSING_OR_SYMLINK")
    digest = _hash(path)
    _require(digest.lower() == expected.lower(), f"{kind}_SHA256_MISMATCH")
    return digest


def _build_jar(class_root: Path, target: Path) -> tuple[str, int]:
    paths = sorted(class_root.rglob("*.class"), key=lambda p: p.relative_to(class_root).as_posix())
    _require(bool(paths), "NO_COMPILED_CLASSES")
    with target.open("xb") as stream:
        with ZipFile(stream, "w", compression=ZIP_STORED) as archive:
            for path in paths:
                _require(path.is_file() and not path.is_symlink(), "UNSAFE_COMPILED_CLASS_PATH")
                relative = path.relative_to(class_root).as_posix()
                _require(relative and all(part not in (".", "..") for part in relative.split("/")),
                         "INVALID_COMPILED_CLASS_PATH")
                info = ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_STORED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
    return _hash(target), len(paths)


def compile_private_source_candidate(
    original_jar: Path, source_root: Path, main_java: Path, output_root: Path, *,
    original_sha256: str, source_sha256: str, source_tree_sha256: str,
    class_entry: str, javac_command: str = "javac", timeout_seconds: int = 180,
) -> dict[str, Any]:
    """Compile one entry Java file plus source-path dependencies with JDK-only classpath.

    The original JAR is never passed to javac. No processors, external JARs,
    implicit user CLASSPATH or binary fallback are allowed in the compile.
    """
    _require(type(timeout_seconds) is int and 1 <= timeout_seconds <= 3600,
             "INVALID_COMPILER_TIMEOUT")
    _require(type(class_entry) is str and class_entry.endswith(".class")
             and not class_entry.startswith("/") and "\\" not in class_entry
             and all(part and part not in (".", "..") and ":" not in part
                     for part in class_entry.split("/")), "INVALID_TARGET_CLASS_ENTRY")
    _require(not Path(source_root).is_symlink(), "SOURCE_ROOT_SYMLINK_NOT_ALLOWED")
    original_jar, source_root, main_java, output_root = map(
        lambda p: Path(p).resolve(), (original_jar, source_root, main_java, output_root),
    )
    _require(source_root.is_dir(), "SOURCE_ROOT_MISSING")
    _require(main_java.suffix == ".java" and main_java.is_relative_to(source_root),
             "JAVA_OUTSIDE_SOURCE_ROOT")
    input_pin = _pin(original_jar, original_sha256, "ORIGINAL_JAR")
    source_pin = _pin(main_java, source_sha256, "JAVA_SOURCE")
    _require(
        type(source_tree_sha256) is str
        and re.fullmatch(r"[0-9a-fA-F]{64}", source_tree_sha256) is not None,
        "SOURCE_TREE_INVALID_SHA256_PIN",
    )
    try:
        tree_before = fingerprint_java_source_tree(source_root)
    except (SourceTreeError, OSError):
        raise SourceCandidateReplayError("SOURCE_TREE_PREFLIGHT_FAILED") from None
    _require(
        tree_before["source_tree_sha256"] == source_tree_sha256.lower(),
        "SOURCE_TREE_SHA256_MISMATCH",
    )
    _require(not output_root.exists(), "OUTPUT_ROOT_ALREADY_EXISTS")
    java = shutil.which(javac_command)
    _require(java is not None, "JAVAC_EXECUTABLE_MISSING")
    output_root.mkdir(parents=True)
    class_output = output_root / "compiled"
    empty_deps = output_root / "empty-classpath"
    class_output.mkdir()
    empty_deps.mkdir()
    cmd = [java, "--release", "9", "-g:none", "-proc:none", "-encoding", "UTF-8",
           "-classpath", str(empty_deps), "-sourcepath", str(source_root),
           "-d", str(class_output), str(main_java)]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, timeout=timeout_seconds,
                              cwd=output_root, check=False)
    except subprocess.TimeoutExpired:
        raise SourceCandidateReplayError("SOURCE_COMPILATION_TIMEOUT") from None
    except OSError:
        raise SourceCandidateReplayError("SOURCE_COMPILER_LAUNCH_FAILED") from None
    _require(proc.returncode == 0, "SOURCE_COMPILATION_FAILED")
    _require((class_output / class_entry).is_file(), "TARGET_CLASS_NOT_COMPILED")
    candidate_jar = output_root / "private-candidate.jar"
    candidate_sha, class_count = _build_jar(class_output, candidate_jar)
    try:
        matrix = build_class_method_matrix(
            original_jar, candidate_jar, original_sha256=input_pin,
            candidate_sha256=candidate_sha, class_entry=class_entry,
        )
    except ClassMethodMatrixError:
        raise SourceCandidateReplayError("METHOD_MATRIX_REJECTED") from None
    _require(_hash(original_jar) == input_pin and _hash(main_java) == source_pin,
             "ORIGINAL_OR_SOURCE_CHANGED_DURING_REPLAY")
    try:
        tree_after = fingerprint_java_source_tree(source_root)
    except (SourceTreeError, OSError):
        raise SourceCandidateReplayError("SOURCE_TREE_CHANGED_DURING_REPLAY") from None
    _require(tree_after == tree_before, "SOURCE_TREE_CHANGED_DURING_REPLAY")
    _require(_hash(candidate_jar) == candidate_sha,
             "COMPILED_CANDIDATE_CHANGED_DURING_REPLAY")
    result = {
        "schema_version": 1,
        "kind": "private_source_candidate_compile_replay",
        "research_only": True,
        "canonical_identity_accepted": False,
        "source_equivalence_certified": False,
        "original_sha256": input_pin,
        "source_sha256": source_pin,
        "source_tree_sha256": tree_before["source_tree_sha256"],
        "source_java_file_count": tree_before["source_java_file_count"],
        "complete_staged_java_tree_pre_and_postflight_verified": True,
        "compiled_candidate_sha256": candidate_sha,
        "compiled_class_count": class_count,
        "compiler_release": 9,
        "annotation_processors_disabled": True,
        "original_client_binary_classpath_disabled": True,
        "compiler_timeout_seconds": timeout_seconds,
        "class_method_matrix": matrix,
    }
    with (output_root / "private-candidate-report.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument("main_java", type=Path)
    p.add_argument("target_class")
    p.add_argument("output_root", type=Path)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--source-tree-sha256", required=True)
    p.add_argument("--javac", default="javac")
    p.add_argument("--timeout-seconds", type=int, default=180)
    args = p.parse_args(argv)
    try:
        result = compile_private_source_candidate(
            args.original_jar, args.source_root, args.main_java, args.output_root,
            original_sha256=args.original_sha256,
            source_sha256=args.source_sha256,
            source_tree_sha256=args.source_tree_sha256,
            class_entry=args.target_class,
            javac_command=args.javac, timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps({
            "compiler_release": result["compiler_release"],
            "compiled_class_count": result["compiled_class_count"],
            "counts": result["class_method_matrix"]["counts"],
            "source_equivalence_certified": False,
        }, sort_keys=True))
        return 0
    except (SourceCandidateReplayError, OSError, ValueError) as exc:
        p.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
