"""R126: SHA-pinned private Java AST census versus original v309 class identities.

Parses candidate Java with JDK compiler AST; never executes source or original
client. A matching *spelling* is NOT proven original binary semantic lineage.
Private report contains aggregates unless explicit identifier output requested.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .private_client_namespace_legalizer_r125 import (
    CANONICAL_V309, original_class_inventory,
)


class PrivateClientSourceAstR126Error(ValueError):
    pass


def need(value, reason):
    if not value:
        raise PrivateClientSourceAstR126Error(reason)


def sha_file(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _decode(token):
    return base64.urlsafe_b64decode(
        token + "=" * ((-len(token)) % 4)
    ).decode("utf-8")


def source_members(archive_path, expected_sha):
    archive_path = Path(archive_path)
    need(archive_path.is_file() and not archive_path.is_symlink(),
         "PRIVATE_SOURCE_ARCHIVE_REQUIRED")
    need(type(expected_sha) is str and
         re.fullmatch(r"[a-f0-9]{64}", expected_sha) and
         sha_file(archive_path) == expected_sha,
         "PRIVATE_SOURCE_ARCHIVE_SHA256_MISMATCH")
    with ZipFile(archive_path) as archive:
        infos = archive.infolist()
        need(1 <= len(infos) <= 50000,
             "SOURCE_ZIP_ENTRY_COUNT_OUTSIDE_LIMIT")
        paths = [i.filename for i in infos]
        need(len(paths) == len(set(paths)), "SOURCE_ZIP_DUPLICATE_PATH")
        selected = []
        cumulative = 0
        for entry in infos:
            path = entry.filename
            need(not path.startswith("/") and "\\" not in path and
                 all(seg not in ("", ".", "..")
                     for seg in path.rstrip("/").split("/")),
                 "UNSAFE_SOURCE_ARCHIVE_PATH")
            need(((entry.external_attr >> 16) & 0o170000) != 0o120000,
                 "SOURCE_ARCHIVE_SYMLINK_REJECTED")
            if not path.endswith(".java") or entry.is_dir():
                continue
            prefix = "/client/src/main/java/"
            if prefix in path:
                rel = path.split(prefix, 1)[1]
            elif path.startswith("client/src/main/java/"):
                rel = path[len("client/src/main/java/"):]
            elif path.startswith("src/main/java/"):
                rel = path[len("src/main/java/"):]
            else:
                continue
            need(rel and len(rel) <= 300 and
                 all(seg not in ("", ".", "..") for seg in rel.split("/")),
                 "UNSAFE_JAVA_SOURCE_PATH")
            need(entry.file_size <= 2_000_000,
                 "JAVA_SOURCE_TOO_LARGE")
            cumulative += entry.file_size
            need(cumulative <= 40_000_000,
                 "JAVA_SOURCE_TOTAL_EXCEEDS_BOUND")
            selected.append((rel, path))
        need(1 <= len(selected) <= 5000,
             "JAVA_SOURCE_FILE_COUNT_OUTSIDE_BOUND")
        rels = [r for r, _ in selected]
        need(len(rels) == len(set(rels)),
             "JAVA_SOURCE_DUPLICATE_RELATIVE_PATH")
        need(len({r.casefold() for r in rels}) == len(rels),
             "WINDOWS_SOURCE_FILENAME_CASEFOLD_COLLISION")
        entries = [(rel, archive.read(member))
                   for rel, member in sorted(selected)]
        for _, content in entries:
            try:
                content.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise PrivateClientSourceAstR126Error(
                    "SOURCE_UTF8_REQUIRED") from exc
        return entries


def _java_ast_declarations(entries, root):
    helper = (Path(__file__).resolve().parent /
              "java" / "ClientAstDeclarationCensusR126.java")
    need(helper.is_file(), "PACKAGED_TRUSTED_JAVA_AST_HELPER_REQUIRED")
    javac = shutil.which("javac")
    java = shutil.which("java")
    need(javac is not None and java is not None,
         "JDK_COMPILER_AND_RUNTIME_REQUIRED")
    source_root = root / "private-input-java"
    classes = root / "trusted-helper"
    source_root.mkdir()
    classes.mkdir()
    for rel, body in entries:
        path = source_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    commands = [
        ([javac, "-encoding", "UTF-8", "-d", str(classes), str(helper)], root),
        ([java, "-cp", str(classes),
          "ClientAstDeclarationCensusR126", str(source_root)], root),
    ]
    collected = None
    for argv, cwd in commands:
        try:
            result = subprocess.run(
                argv, cwd=cwd, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=180, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PrivateClientSourceAstR126Error(
                "JAVA_AST_EXECUTION_NOT_COMPLETED") from exc
        need(result.returncode == 0, "JAVA_AST_PARSE_OR_HELPER_FAILED")
        collected = result.stdout
    need(collected is not None and len(collected) <= 4_000_000,
         "JAVA_AST_DECLARATION_OUTPUT_INVALID")
    declarations = []
    for line in collected.decode("utf-8").splitlines():
        parts = line.split("\t")
        need(len(parts) == 2,
             "AST_DECLARATION_PROTOCOL_INVALID")
        source, internal = map(_decode, parts)
        need(source in {rel for rel, _ in entries} and internal
             and not internal.startswith("/") and ".." not in internal,
             "AST_DECLARATION_OUTSIDE_STAGED_INPUT")
        declarations.append((source, internal))
    need(len({item[1] for item in declarations}) == len(declarations),
         "AST_DUPLICATE_JAVA_TYPE_DECLARATION")
    return sorted(declarations)


def census_private_client_source(source_zip, original_jar, *,
                                 source_sha256, original_sha256=CANONICAL_V309,
                                 include_identifiers=False):
    entries = source_members(source_zip, source_sha256)
    original = original_class_inventory(original_jar, original_sha256)
    manifest = hashlib.sha256()
    for rel, body in entries:
        manifest.update(rel.encode("utf-8") + b"\0")
        manifest.update(hashlib.sha256(body).digest())
    with tempfile.TemporaryDirectory(prefix="spk-r126-private-") as td:
        rows = _java_ast_declarations(entries, Path(td))
    declared = {name for _, name in rows}
    original_rs = {name for name in original if name.startswith("rs/")}
    declared_rs = {name for name in declared if name.startswith("rs/")}
    matched = declared_rs & original_rs
    report = {
        "schema_version": 1,
        "kind": "private_client_source_ast_original_identity_census_r126",
        "source_archive_sha256": source_sha256,
        "original_client_sha256": original_sha256,
        "source_content_manifest_sha256": manifest.hexdigest(),
        "source_java_file_count": len(entries),
        "rs_source_file_count": sum(rel.startswith("rs/")
                                    for rel, _ in entries),
        "ast_named_type_declaration_count": len(rows),
        "ast_named_rs_type_declaration_count": len(declared_rs),
        "original_rs_classfile_count": len(original_rs),
        "exact_spelling_original_rs_type_matches": len(matched),
        "rs_ast_types_not_matching_original_name": len(declared_rs-matched),
        "original_rs_classfile_names_not_ast_declared":
            len(original_rs-matched),
        "parse_only_no_java_source_compiled": True,
        "original_binary_not_executed": True,
        "matched_spelling_is_proven_binary_lineage": False,
        "complete_deobfuscated_client_source_accepted": False,
        "zero_project_binary_fallback_build_passed": False,
        "source_files_edited": False,
        "source_identifiers_included": bool(include_identifiers),
    }
    if include_identifiers:
        report["private_ast_declarations"] = [
            {"source_path": rel, "java_internal_name": name,
             "same_named_original_rs_classfile":
                name in original_rs if name.startswith("rs/") else False}
            for rel, name in rows
        ]
        report["private_unmatched_original_rs_names"] = sorted(
            original_rs - matched)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_decompiled_source_zip")
    p.add_argument("private_original_v309_jar")
    p.add_argument("new_private_report")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    p.add_argument("--private-identifiers", action="store_true")
    a = p.parse_args(argv)
    target = Path(a.new_private_report)
    try:
        need(not target.exists() and not target.is_symlink()
             and target.parent.is_dir() and not target.parent.is_symlink(),
             "FRESH_PRIVATE_REPORT_PATH_REQUIRED")
        result = census_private_client_source(
            a.private_decompiled_source_zip,
            a.private_original_v309_jar,
            source_sha256=a.source_sha256,
            original_sha256=a.original_sha256,
            include_identifiers=a.private_identifiers)
        target.write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        print("V309_SOURCE_AST_IDENTITY_CENSUS_R126_COMPLETE")
        print("private_report_sha256=" + sha_file(target))
    except Exception:
        p.error("PRIVATE_V309_SOURCE_AST_CENSUS_R126_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
