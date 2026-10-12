"""R86: compile a PRIVATE full Java 9 candidate, then demand R66 + R81 parity.

Inputs are already reconstructed source files supplied by the user. This
does not invent owner dependencies or turn bounded fragments into classes.
The original exact client remains read-only and outside the repository.
No generated candidate or compiler diagnostics are uploaded to GitHub.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

from .clinit_store_order_witness import _verified_class
from .mutable_scalar_initializer_source import _digest
from .whole_method_operand_parity import (
    WholeMethodOperandError, compare_all_method_operands,
)


class PrivateJava9AcceptanceError(ValueError):
    """Whole compiled original/candidate JVM parity not certified."""


def require(ok, error):
    if not ok:
        raise PrivateJava9AcceptanceError(error)


def _input_sources(root: Path) -> tuple[list[Path], str]:
    require(root.is_dir() and not root.is_symlink(), "PRIVATE_SOURCE_ROOT_NOT_DIRECTORY")
    root_abs = root.resolve()
    files = sorted(root.rglob("*.java"))
    require(0 < len(files) <= 256, "PRIVATE_JAVA_SOURCE_COUNT_OUTSIDE_BOUNDS")
    digest = hashlib.sha256()
    size = 0
    for file in files:
        require(file.is_file() and not file.is_symlink()
                and file.resolve().is_relative_to(root_abs)
                and not any(parent.is_symlink()
                            for parent in file.parents if parent != root_abs
                            and root_abs in parent.parents),
                "PRIVATE_JAVA_SOURCE_PATH_NOT_SAFE")
        raw = file.read_bytes()
        size += len(raw)
        require(size <= 16 * 1024 * 1024,
                "PRIVATE_JAVA_SOURCE_BYTES_EXCEED_LIMIT")
        relative = file.relative_to(root).as_posix()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative.encode("utf-8"))
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return files, digest.hexdigest()


def _private_class_entry(entry: str) -> str:
    require(isinstance(entry, str) and entry.endswith(".class")
            and not entry.startswith("/") and "\\" not in entry
            and all(part not in ("", ".", "..") and ":" not in part
                    for part in entry.split("/")),
            "PRIVATE_JVM_CLASS_ENTRY_INVALID")
    return entry


def compile_and_accept_private_java9(
    original_jar: Path, original_entry: str, original_method: str,
    original_descriptor: str, source_root: Path, candidate_entry: str,
    candidate_method: str, candidate_descriptor: str, alias_json: Path,
    new_private_output: Path, *, original_sha256: str, javac: str = "javac",
    compile_classpath: Path | None = None,
) -> dict:
    original_jar, source_root, alias_json, new_private_output = map(
        Path, (original_jar, source_root, alias_json, new_private_output))
    require(not new_private_output.exists() and not new_private_output.is_symlink(),
            "OUTPUT_ALREADY_EXISTS")
    require(isinstance(original_sha256, str)
            and len(original_sha256) == 64
            and all(c in "0123456789abcdefABCDEF" for c in original_sha256),
            "ORIGINAL_COMPLETE_JAR_SHA256_INVALID")
    require(original_jar.is_file() and not original_jar.is_symlink()
            and _digest(original_jar) == original_sha256.lower(),
            "ORIGINAL_COMPLETE_JAR_PIN_MISMATCH")
    require(alias_json.is_file() and not alias_json.is_symlink()
            and alias_json.stat().st_size <= 1024*1024,
            "PRIVATE_ALIASES_FILE_MISSING_OR_UNSAFE")
    try:
        aliases = json.loads(alias_json.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PrivateJava9AcceptanceError("PRIVATE_ALIAS_JSON_INVALID") from exc
    require(isinstance(aliases, dict) and aliases.get("schema_version") == 1
            and isinstance(aliases.get("aliases"), list)
            and isinstance(aliases.get("read_only_field_aliases", []), list)
            and isinstance(aliases.get("method_aliases", []), list),
            "PRIVATE_ALIASES_SCHEMA_INVALID")
    original_entry = _private_class_entry(original_entry)
    candidate_entry = _private_class_entry(candidate_entry)
    files, source_digest = _input_sources(source_root)
    if compile_classpath is not None:
        compile_classpath = Path(compile_classpath)
        require((compile_classpath.is_file() or compile_classpath.is_dir())
                and not compile_classpath.is_symlink(),
                "COMPILE_CLASSPATH_NOT_AVAILABLE")
    require(isinstance(javac, str) and javac.strip(),
            "JAVAC_EXECUTABLE_NOT_SET")
    javac_exe = shutil.which(javac)
    require(javac_exe is not None, "JAVAC_UNAVAILABLE")
    try:
        original = _verified_class(
            original_jar, original_entry, original_sha256)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        raise PrivateJava9AcceptanceError(
            "ORIGINAL_PINNED_CLASS_NOT_VERIFIABLE") from exc
    with tempfile.TemporaryDirectory(prefix="v309-java9-private-") as tmp:
        tmp_root = Path(tmp)
        classes = tmp_root / "classes"
        classes.mkdir()
        argv = [
            javac_exe, "--release", "9", "-g:none", "-proc:none",
            "-encoding", "UTF-8", "-d", str(classes)
        ]
        if compile_classpath is not None:
            argv += ["-classpath", str(compile_classpath)]
        argv += [str(file.resolve()) for file in files]
        try:
            result = subprocess.run(
                argv, capture_output=True, text=True, timeout=180,
                check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PrivateJava9AcceptanceError(
                "PRIVATE_JAVA9_COMPILER_UNAVAILABLE_OR_TIMEOUT") from exc
        # javac diagnostics can contain original field names, literal keys,
        # source lines or local paths. Do not return or persist them here.
        require(result.returncode == 0,
                "PRIVATE_JAVA9_COMPILE_FAILED_NO_OUTPUT_PUBLISHED")
        class_files = sorted(classes.rglob("*.class"))
        require(class_files and len(class_files) <= 1024,
                "PRIVATE_COMPILED_CLASS_COUNT_INVALID")
        candidate_file = classes / candidate_entry
        require(candidate_file.is_file() and not candidate_file.is_symlink(),
                "PRIVATE_CANDIDATE_OWNER_CLASS_MISSING")
        temporary_candidate_jar = tmp_root / "candidate.private.jar"
        with ZipFile(temporary_candidate_jar, "w", ZIP_DEFLATED) as archive:
            for file in class_files:
                relative = file.relative_to(classes).as_posix()
                require(file.is_file() and not file.is_symlink()
                        and file.resolve().is_relative_to(classes.resolve()),
                        "PRIVATE_COMPILED_CLASS_PATH_UNSAFE")
                archive.write(file, arcname=relative)
        candidate_sha = _digest(temporary_candidate_jar)
        try:
            candidate = _verified_class(
                temporary_candidate_jar, candidate_entry, candidate_sha)
            proof = compare_all_method_operands(
                original, original_method, original_descriptor,
                candidate, candidate_method, candidate_descriptor,
                aliases["aliases"], aliases.get("read_only_field_aliases", []),
                aliases.get("method_aliases", []),
            )
        except (WholeMethodOperandError, OSError, ValueError,
                KeyError, TypeError, IndexError) as exc:
            raise PrivateJava9AcceptanceError(
                "R66_R81_COMPILED_ORIGINAL_METHOD_PARITY_NOT_ACCEPTED") from exc
        require(_digest(original_jar) == original_sha256.lower()
                and _digest(temporary_candidate_jar) == candidate_sha,
                "PINNED_INPUT_OR_COMPILED_CANDIDATE_CHANGED")
        report = {
            "schema_version": 1,
            "kind": "private_compiled_java9_R66_R81_method_gate",
            "research_only": True,
            "original_complete_jar_sha256": original_sha256.lower(),
            "candidate_compiled_jar_sha256": candidate_sha,
            "private_source_tree_sha256": source_digest,
            "private_java_source_file_count": len(files),
            "private_compiled_class_count": len(class_files),
            "java_release": 9,
            "R66_original_candidate_structural_parity": True,
            "R81_every_parsed_JVM_operand_parity": True,
            **proof,
            "original_helper_methods_and_dependency_implementations_proven": False,
            "original_entire_owner_class_metadata_and_initializer_proven": False,
            "runtime_and_filesystem_side_effects_equivalent": False,
        }
        new_private_output.mkdir(parents=True, exist_ok=False)
        with (new_private_output / "candidate.private.jar").open("xb") as stream:
            stream.write(temporary_candidate_jar.read_bytes())
        with (new_private_output / "java9-parity.aggregate.json").open(
                "x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("original_jar", "original_class_entry",
                "original_method_name", "original_method_descriptor",
                "private_java_source_root", "candidate_class_entry",
                "candidate_method_name", "candidate_method_descriptor",
                "private_alias_json", "new_private_output"):
        parser.add_argument(arg)
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--javac", default="javac")
    parser.add_argument("--compile-classpath", type=Path)
    a = parser.parse_args(argv)
    try:
        proof = compile_and_accept_private_java9(
            Path(a.original_jar), a.original_class_entry,
            a.original_method_name, a.original_method_descriptor,
            Path(a.private_java_source_root), a.candidate_class_entry,
            a.candidate_method_name, a.candidate_method_descriptor,
            Path(a.private_alias_json), Path(a.new_private_output),
            original_sha256=a.original_sha256, javac=a.javac,
            compile_classpath=a.compile_classpath)
        print(json.dumps(proof, sort_keys=True))
    except PrivateJava9AcceptanceError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
