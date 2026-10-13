"""R130: one SHA-pinned source class Java AST rename, private-only output.

Requires a single fully analyzable private Java source file. Uses JDK semantic
symbol attribution to rename its declaration, constructors and type uses.
Does not alter strings/comments, rewrite packages, accept guessed lineage or
publish original-derived source to GitHub. Follow with R129 for bytecode proof.
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

from .private_client_namespace_legalizer_r125 import _JAVA_RESERVED


class PrivateSingleClassRenameR130Error(ValueError):
    pass


def need(value, code):
    if not value:
        raise PrivateSingleClassRenameR130Error(code)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _java_owner(internal):
    need(type(internal) is str and internal.startswith("rs/")
         and len(internal) <= 300 and
         all(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", item)
             and item not in _JAVA_RESERVED
             for item in internal.split("/")),
         "JAVA_SOURCE_LEGAL_RS_OWNER_REQUIRED")
    return internal.rsplit("/", 1)



def _verified_helper_replacements(stdout):
    """Line-ending independent; require one exact Java-helper pass/counter."""
    try:
        lines = stdout.decode("utf-8", errors="strict").splitlines()
    except UnicodeDecodeError as exc:
        raise PrivateSingleClassRenameR130Error(
            "TRUSTED_JAVA_HELPER_OUTPUT_INVALID_UTF8") from exc
    need(lines.count("R130_AST_SOURCE_CLASS_REWRITE_PASS") == 1,
         "TRUSTED_JAVA_HELPER_NO_SUCCESS_MARKER")
    values = [line.partition("=")[2] for line in lines
              if line.startswith("source_symbol_replacements=")]
    need(len(values) == 1 and values[0].isascii() and values[0].isdecimal()
         and 2 <= int(values[0]) <= 5000,
         "CLASS_DECLARATION_OR_CONSTRUCTOR_NOT_REWRITTEN")
    return int(values[0])


def rename_private_single_source_class(source_root, fresh_private_output, *,
                                       original_java_owner, intended_jvm_owner,
                                       source_sha256, javac="javac", java="java"):
    first_package, before = _java_owner(original_java_owner)
    second_package, after = _java_owner(intended_jvm_owner)
    need(first_package == second_package and before != after,
         "R130_DIFFERENT_PACKAGE_OR_IDENTITY_REMAP_NOT_SUPPORTED")
    source = Path(source_root)
    output = Path(fresh_private_output)
    need(source.is_dir() and not source.is_symlink(),
         "PRIVATE_RESTORED_JAVA_DIRECTORY_REQUIRED")
    need(not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink()
         and output.resolve() != source.resolve()
         and source.resolve() not in output.resolve().parents,
         "FRESH_PRIVATE_OUTPUT_OUTSIDE_SOURCE_REQUIRED")
    files = list(source.rglob("*"))
    need(len(files) <= 64 and not any(p.is_symlink() for p in files),
         "SOURCE_PATH_COUNT_OR_SYMLINK_REJECTED")
    non_dirs = [p for p in files if not p.is_dir()]
    need(len(non_dirs) == 1 and
         non_dirs[0].relative_to(source).as_posix() ==
         original_java_owner + ".java",
         "EXACT_ONE_SOURCE_MATCHING_DECLARED_CLASS_REQUIRED")
    original = non_dirs[0]
    need(original.stat().st_size <= 2_000_000,
         "SOURCE_BYTES_OUTSIDE_BOUND")
    need(isinstance(source_sha256, str)
         and re.fullmatch(r"[a-f0-9]{64}", source_sha256)
         and sha256(original) == source_sha256,
         "SOURCE_JAVA_SHA256_PIN_MISMATCH")
    javac_path, java_path = shutil.which(javac), shutil.which(java)
    need(javac_path is not None and java_path is not None,
         "JDK_JAVA_AND_JAVAC_REQUIRED")
    helper = (Path(__file__).resolve().parent / "java" /
              "ClientSingleClassRenameR130.java")
    need(helper.is_file(), "R130_TRUSTED_JAVA_HELPER_UNAVAILABLE")
    with tempfile.TemporaryDirectory(
            prefix="v309-r130-class-ast-private-",
            dir=output.parent) as temp:
        root = Path(temp)
        staged = root / "staged"
        stage_source = staged / (original_java_owner + ".java")
        stage_source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, stage_source)
        classes = root / "trusted-helper"
        classes.mkdir()
        empty = root / "empty-dependencies"
        empty.mkdir()
        commands = [
            [javac_path, "-encoding", "UTF-8",
             "-d", str(classes), str(helper)],
            [java_path, "-cp", str(classes),
             "ClientSingleClassRenameR130", str(staged),
             original_java_owner, intended_jvm_owner, str(empty)],
        ]
        result = None
        for command in commands:
            try:
                result = subprocess.run(
                    command, cwd=root, capture_output=True,
                    stdin=subprocess.DEVNULL, timeout=180)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise PrivateSingleClassRenameR130Error(
                    "PRIVATE_AST_SOURCE_REWRITE_NOT_COMPLETED") from exc
            need(result.returncode == 0,
                 "PRIVATE_AST_SOURCE_SYMBOL_REWRITE_REJECTED")
        replacement_count = _verified_helper_replacements(result.stdout)
        target = staged / (intended_jvm_owner + ".java")
        need(target.is_file() and not stage_source.exists(),
             "REWRITTEN_SOURCE_FILE_IDENTITY_MISMATCH")
        need(sha256(original) == source_sha256,
             "PRIVATE_ORIGINAL_SOURCE_MUTATED_DURING_REWRITE")
        # Verify the rewrite actually compiles with no original project
        # classes or binary stubs. These classfiles are then discarded.
        compiled = root / "verified-java9"
        compiled.mkdir()
        compile_command = [
            javac_path, "--release", "9", "-g:none", "-proc:none",
            "-implicit:none", "-encoding", "UTF-8",
            "-classpath", str(empty), "-sourcepath", str(empty),
            "-d", str(compiled), str(target),
        ]
        try:
            comp = subprocess.run(
                compile_command, cwd=root, capture_output=True,
                stdin=subprocess.DEVNULL, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PrivateSingleClassRenameR130Error(
                "RENAMED_SOURCE_COMPILATION_NOT_COMPLETED") from exc
        need(comp.returncode == 0 and
             (compiled / (intended_jvm_owner + ".class")).is_file(),
             "RENAMED_SOURCE_NOT_STANDALONE_JAVA9_COMPILABLE")
        posthash = sha256(target)
        proof = {
            "schema_version": 1,
            "kind": "private_v309_single_java_ast_class_rename_r130",
            "source_java_original_sha256": source_sha256,
            "independently_renamed_java_source_sha256": posthash,
            "source_symbol_replacements": replacement_count,
            "jvm_source_compiler_release": 9,
            "project_binary_fallback_used": False,
            "private_original_source_unchanged": True,
            "renamed_source_java9_compiled": True,
            "original_client_binary_executed": False,
            "candidate_class_identity_original_proven": False,
            "original_binary_method_parity_proven": False,
            "whole_client_source_tree_accepted": False,
            "runtime_equivalence_proven": False,
        }
        published = root / "private-rewritten-source"
        (published / "src").mkdir(parents=True)
        rewritten = published / "src" / (intended_jvm_owner + ".java")
        rewritten.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(target, rewritten)
        need(sha256(rewritten) == posthash,
             "PRIVATE_OUTPUT_SOURCE_COPY_CHANGED")
        (published / "source-rewrite.aggregate.json").write_text(
            json.dumps(proof, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        need(not output.exists(), "PRIVATE_REWRITE_OUTPUT_BECAME_OCCUPIED")
        os.rename(published, output)
    return proof


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_one_class_source_root")
    p.add_argument("fresh_private_rewritten_source")
    p.add_argument("--old-java-owner", required=True)
    p.add_argument("--new-original-owner", required=True)
    p.add_argument("--source-sha256", required=True)
    a = p.parse_args(argv)
    try:
        report = rename_private_single_source_class(
            a.private_one_class_source_root, a.fresh_private_rewritten_source,
            original_java_owner=a.old_java_owner,
            intended_jvm_owner=a.new_original_owner,
            source_sha256=a.source_sha256)
        print("PRIVATE_SOURCE_AST_RENAME_R130_PASS")
        print("aggregate_report_sha256=" + sha256(
            Path(a.fresh_private_rewritten_source) /
            "source-rewrite.aggregate.json"))
        print("source_symbol_replacements=" +
              str(report["source_symbol_replacements"]))
    except Exception:
        p.error("PRIVATE_V309_CLASS_AST_RENAME_R130_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
