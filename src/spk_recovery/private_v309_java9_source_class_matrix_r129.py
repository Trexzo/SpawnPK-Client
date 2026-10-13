"""R129: private source-first, no-game-binary-fallback Java9 class replay.

Compiles an explicit private Java source tree using only the JDK and the
explicitly enumerated source files; original client JAR is used ONLY for a
subsequent read-only parity comparison, never as a compiler dependency.
A positive method matrix is not original authorial source or runtime proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .source_class_method_matrix import build_class_method_matrix


class PrivateSourceJavacClassReplayR129Error(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise PrivateSourceJavacClassReplayR129Error(code)


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def _sources(root):
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(),
            "PRIVATE_SOURCE_ROOT_MUST_BE_REAL_DIRECTORY")
    selected = []
    total = 0
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(),
                "PRIVATE_SOURCE_TREE_SYMLINK_FORBIDDEN")
        if path.is_dir():
            continue
        require(path.is_file(), "PRIVATE_SOURCE_SPECIAL_FILE_FORBIDDEN")
        if path.suffix != ".java":
            continue
        rel = path.relative_to(root).as_posix()
        require(len(rel) <= 500 and len(rel.split("/")) <= 32,
                "PRIVATE_SOURCE_NAME_BOUND_EXCEEDED")
        stat = path.stat()
        require(stat.st_size <= 2_000_000,
                "PRIVATE_SOURCE_FILE_TOO_LARGE")
        total += stat.st_size
        require(total <= 30_000_000, "PRIVATE_SOURCE_TOTAL_TOO_LARGE")
        selected.append((rel, path))
    require(1 <= len(selected) <= 256,
            "PRIVATE_SOURCE_FILE_COUNT_OUTSIDE_BOUND")
    require(len({name.casefold() for name, _ in selected}) == len(selected),
            "WINDOWS_SOURCE_PATH_CASEFOLD_COLLISION")
    return selected


def _zip_compiled_classfiles(classes, jar):
    entries = []
    for path in sorted(classes.rglob("*")):
        require(not path.is_symlink(),
                "COMPILED_CLASS_SYMLINK_NOT_ALLOWED")
        if path.is_dir():
            continue
        require(path.suffix == ".class" and path.is_file(),
                "UNEXPECTED_COMPILER_OUTPUT_FILE")
        rel = path.relative_to(classes).as_posix()
        body = path.read_bytes()
        require(len(body) >= 8 and body[:4] == b"\xca\xfe\xba\xbe"
                and int.from_bytes(body[6:8], "big") == 53,
                "NON_JAVA9_OR_INVALID_COMPILED_CLASSFILE")
        entries.append((rel, body))
    require(1 <= len(entries) <= 1024,
            "COMPILED_JAVA9_CLASS_COUNT_OUTSIDE_BOUND")
    require(len({name.casefold() for name, _ in entries}) == len(entries),
            "WINDOWS_COMPILED_CLASSFILE_CASEFOLD_COLLISION")
    with ZipFile(jar, "w") as archive:
        for rel, body in entries:
            info = ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, body)
    return entries


def compile_and_compare_private_class(source_root, original_jar,
                                      fresh_private_output, *,
                                      original_sha256=CANONICAL_V309,
                                      class_entry, javac="javac"):
    source_root = Path(source_root)
    original_jar = Path(original_jar)
    output = Path(fresh_private_output)
    require(not output.exists() and not output.is_symlink()
            and output.parent.is_dir() and not output.parent.is_symlink(),
            "FRESH_PRIVATE_OUTPUT_DIRECTORY_REQUIRED")
    require(output.resolve() != source_root.resolve()
            and source_root.resolve() not in output.resolve().parents,
            "OUTPUT_INSIDE_SOURCE_TREE_FORBIDDEN")
    require(type(class_entry) is str and
            class_entry.startswith("rs/") and
            class_entry.endswith(".class") and "\\" not in class_entry
            and all(x not in ("", ".", "..") for x in class_entry.split("/")),
            "PRIVATE_RS_CLASS_ENTRY_REQUIRED")
    require(original_jar.is_file() and not original_jar.is_symlink()
            and isinstance(original_sha256, str) and
            re.fullmatch(r"[a-fA-F0-9]{64}", original_sha256) and
            file_digest(original_jar).lower() == original_sha256.lower(),
            "PINNED_ORIGINAL_CLIENT_JAR_REQUIRED")
    listed = _sources(source_root)
    compiler = shutil.which(javac)
    require(compiler is not None, "JDK_JAVAC_REQUIRED")
    manifest = [
        {"source_path": name, "sha256": file_digest(path)}
        for name, path in listed
    ]
    manifest_digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    with tempfile.TemporaryDirectory(
            prefix="spk-r129-source-compile-", dir=output.parent) as td:
        scratch = Path(td)
        compiled = scratch / "classes"
        isolated = scratch / "empty-classpath-and-sourcepath"
        compiled.mkdir()
        isolated.mkdir()
        argv = [
            compiler, "--release", "9", "-g:none", "-proc:none",
            "-encoding", "UTF-8", "-implicit:none",
            "-classpath", str(isolated), "-sourcepath", str(isolated),
            "-d", str(compiled),
            *[str(path.resolve()) for _, path in listed],
        ]
        try:
            proc = subprocess.run(
                argv, cwd=scratch, capture_output=True,
                stdin=subprocess.DEVNULL, check=False, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PrivateSourceJavacClassReplayR129Error(
                "PRIVATE_JAVA9_COMPILATION_NOT_COMPLETED") from exc
        require(proc.returncode == 0,
                "PRIVATE_JAVA9_SOURCE_COMPILATION_FAILED")
        require(all(file_digest(path) == item["sha256"]
                    for (_, path), item in zip(listed, manifest)),
                "PRIVATE_JAVA_SOURCE_INPUT_CHANGED_DURING_COMPILE")
        candidate = scratch / "source-built.private.jar"
        classes = _zip_compiled_classfiles(compiled, candidate)
        require(sum(name == class_entry for name, _ in classes) == 1,
                "REQUESTED_PRIVATE_ORIGINAL_CLASS_NOT_SOURCE_COMPILED")
        candidate_sha = file_digest(candidate)
        try:
            matrix = build_class_method_matrix(
                original_jar, candidate,
                original_sha256=original_sha256,
                candidate_sha256=candidate_sha,
                class_entry=class_entry,
            )
        except Exception as exc:
            raise PrivateSourceJavacClassReplayR129Error(
                "PINNED_ORIGINAL_JVM_CLASS_MATRIX_UNAVAILABLE") from exc

        head = matrix.get("class_header", {})
        evidence = {
            "schema_version": 1,
            "kind": "private_v309_javac9_source_vs_original_class_matrix_r129",
            "original_client_sha256": original_sha256,
            "independently_source_compiled_candidate_sha256": candidate_sha,
            "private_source_manifest_sha256": manifest_digest,
            "private_java_source_file_count": len(listed),
            "compiled_java9_classfile_count": len(classes),
            "javac_release": 9,
            "original_rs_classfile_used_in_compiler": False,
            "project_binary_dependency_fallback_used": False,
            "original_client_executed": False,
            "source_compile_succeeded": True,
            "class_header_exact": head.get("class_header_exact") is True,
            "class_signature_exact": matrix.get("class_signature_exact") is True,
            "field_inventory_exact": matrix.get("field_inventory_exact") is True,
            "all_method_bodies_instruction_parity":
                matrix.get("all_method_bodies_instruction_parity") is True,
            "original_declared_method_count":
                matrix.get("original_declared_method_count"),
            "candidate_declared_method_count":
                matrix.get("candidate_declared_method_count"),
            "original_declared_field_count":
                matrix.get("original_declared_field_count"),
            "candidate_declared_field_count":
                matrix.get("candidate_declared_field_count"),
            "method_classification_counts": matrix.get("counts"),
            "field_classification_counts": matrix.get("field_counts"),
            "class_research_matrix_id": matrix.get("report_id"),
            "all_matrix_checks_exact": bool(
                head.get("class_header_exact") is True
                and matrix.get("class_signature_exact") is True
                and matrix.get("field_inventory_exact") is True
                and matrix.get("all_method_bodies_instruction_parity") is True
            ),
            "source_authorial_identity_proven": False,
            "whole_client_source_tree_complete": False,
            "whole_client_runtime_equivalent": False,
            "original_game_class_parity_accepted": False,
            "unverified_other_code_attributes_and_dependencies": True,
        }
        accepted = scratch / "published-private-research"
        accepted.mkdir()
        shutil.copyfile(candidate, accepted / "source-built.private.jar")
        require(file_digest(accepted / "source-built.private.jar") ==
                candidate_sha,
                "COPIED_PRIVATE_JAVA9_CANDIDATE_HASH_CHANGED")
        (accepted / "source-built.aggregate.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        # Destination must not already exist, even across a long compilation.
        require(not output.exists(), "PRIVATE_OUTPUT_DIRECTORY_ALREADY_EXISTS")
        os.rename(accepted, output)
    return evidence


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_java_source_root")
    p.add_argument("original_v309_jar")
    p.add_argument("fresh_private_output_dir")
    p.add_argument("--class-entry", required=True)
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    p.add_argument("--javac", default="javac")
    a = p.parse_args(argv)
    try:
        report = compile_and_compare_private_class(
            a.private_java_source_root, a.original_v309_jar,
            a.fresh_private_output_dir,
            class_entry=a.class_entry,
            original_sha256=a.original_sha256, javac=a.javac)
        print("R129_JAVA9_SOURCE_CLASS_MATRIX_RESEARCH_COMPLETE")
        print("sanitized_report_sha256=" +
              file_digest(Path(a.fresh_private_output_dir) /
                          "source-built.aggregate.json"))
        print("all_matrix_checks_exact=" +
              str(report["all_matrix_checks_exact"]).lower())
    except Exception:
        p.error("PRIVATE_V309_JAVA9_SOURCE_CLASS_GATE_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
