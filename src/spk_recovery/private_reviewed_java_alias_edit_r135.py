"""R135: one reviewed v309 class/package alias source edit, private only.

Do not upload original-derived Java or candidate output ZIP to public GitHub.
The alias is a *provisional* source-linkage repair, not an accepted original
source tree or a confirmed full-client compile. No project code is executed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import (
    CANONICAL_V309, original_class_inventory, plan_client_namespaces,
)
from .private_client_source_ast_census_r126 import source_members, sha_file


class ReviewedImportAliasR135Error(ValueError):
    pass


def need(condition, code):
    if not condition:
        raise ReviewedImportAliasR135Error(code)


TARGET = "rs/plugins/configs/ConfigPanel.java"
ORIGINAL_OWNER = "org/apache/commons/a/d"
ORIGINAL_IMPORT = "org.apache.commons.a.d_"
ORIGINAL_TOKEN = "d_"
ORIGINAL_METHOD = "a"
ORIGINAL_DESCRIPTOR = "([Ljava/lang/Object;Ljava/lang/Object;)I"
CANONICAL_TARGET_SHA256 = "c828c1e2b9735504bdd86d18ebe8fb6699e916f13b1bd9a9c3a4f536ca719297"


def _source_hash(contents):
    return hashlib.sha256(contents).hexdigest()


def _compiled_original_method_guard(jar):
    originals = original_class_inventory(jar, sha_file(jar))
    need(ORIGINAL_OWNER in originals
         and any(name.startswith(ORIGINAL_OWNER + "/") for name in originals),
         "EXPECTED_EXACT_ORIGINAL_CLASS_PACKAGE_SHADOW_REQUIRED")
    with zipfile.ZipFile(jar) as archive:
        raw = archive.read(ORIGINAL_OWNER + ".class")
    cls = parse_class(raw)
    need(cls.name == ORIGINAL_OWNER, "ORIGINAL_CLASS_IDENTITY_WRONG")
    matches = [method for method in cls.methods
               if method["name"] == ORIGINAL_METHOD
               and method["descriptor"] == ORIGINAL_DESCRIPTOR
               and method["access"] & 0x0008]
    need(len(matches) == 1,
         "ORIGINAL_STATIC_METHOD_DESCRIPTOR_NOT_PROVEN")
    return originals


def _ast_spans(source_bytes, *, helper_path=None):
    content = source_bytes.decode("utf-8", errors="strict")
    need("\r" not in content and
         all(ord(char) <= 0xFFFF for char in content),
         "SOURCE_OFFSETS_NOT_SAFE_AS_JAVA_UTF16")
    java = shutil.which("java")
    javac = shutil.which("javac")
    need(java is not None and javac is not None,
         "JDK_COMPILER_REQUIRED")
    helper = helper_path or (Path(__file__).resolve().parent /
                              "java" / "ReviewedImportAliasSpansR135.java")
    need(helper.is_file() and not helper.is_symlink(),
         "TRUSTED_AST_HELPER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r135-ast-") as tmp:
        root = Path(tmp)
        source = root / "ConfigPanel.java"
        source.write_bytes(source_bytes)
        compiled = root / "helper"
        compiled.mkdir()
        cmds = [
            [javac, "-encoding", "UTF-8", "-classpath", str(compiled),
             "-sourcepath", str(compiled), "-d", str(compiled), str(helper)],
            [java, "-cp", str(compiled), "ReviewedImportAliasSpansR135",
             str(source), ORIGINAL_IMPORT, ORIGINAL_TOKEN]
        ]
        result = None
        for cmd in cmds:
            try:
                result = subprocess.run(cmd, cwd=root,
                                        stdin=subprocess.DEVNULL,
                                        capture_output=True, timeout=90,
                                        check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ReviewedImportAliasR135Error(
                    "TRUSTED_AST_HELPER_DID_NOT_COMPLETE") from exc
            need(result.returncode == 0,
                 "REVIEWED_AST_IMPORT_OR_CALL_NOT_PROVEN")
    need(result is not None and len(result.stdout) < 1024,
         "INVALID_TRUSTED_AST_SPANS")
    spans = {}
    for line in result.stdout.decode("utf-8", errors="strict").splitlines():
        parts = line.split("\t")
        need(len(parts) == 3 and parts[0] in ("CALL", "IMPORT")
             and parts[0] not in spans,
             "AST_SPAN_FORMAT_INVALID")
        try:
            start, end = int(parts[1]), int(parts[2])
        except ValueError as exc:
            raise ReviewedImportAliasR135Error(
                "AST_SPAN_NUMBER_INVALID") from exc
        need(0 <= start < end <= len(content), "AST_SPAN_OUT_OF_RANGE")
        spans[parts[0]] = (start, end)
    need(set(spans) == {"CALL", "IMPORT"}, "EXACT_AST_SPANS_MISSING")
    need(content[slice(*spans["IMPORT"])] == ORIGINAL_IMPORT
         and content[slice(*spans["CALL"])] == ORIGINAL_TOKEN,
         "AST_SOURCE_TEXT_DOES_NOT_MATCH_EXPECTATION")
    # Two occurrences only: one import segment and one call receiver.
    need(len(re.findall(r"\bd_\b", content)) == 2,
         "ADDITIONAL_UNREVIEWED_ALIAS_REFERENCES")
    return spans


def patch_private_candidate(source_zip, original_jar, *,
                            source_sha256, original_sha256=CANONICAL_V309,
                            target_sha256=CANONICAL_TARGET_SHA256):
    need(sha_file(source_zip) == source_sha256
         and sha_file(original_jar) == original_sha256,
         "PINNED_PRIVATE_INPUT_SHA256_MISMATCH")
    entries = source_members(source_zip, source_sha256)
    source_by_path = dict(entries)
    need(TARGET in source_by_path, "ORIGINAL_CLIENT_SOURCE_FILE_MISSING")
    before = source_by_path[TARGET]
    need(_source_hash(before) == target_sha256,
         "UNREVIEWED_CONFIG_PANEL_PREIMAGE_SHA256")
    originals = _compiled_original_method_guard(original_jar)
    solution = plan_client_namespaces(originals, include_identifiers=True,
                                      original_jar_sha256=original_sha256)
    remaps = {row["old_internal_name"]: row["new_internal_name"]
              for row in solution["remaps"]}
    need(ORIGINAL_OWNER in remaps,
         "ORIGINAL_SHADOW_ALIAS_MAPPING_NOT_PRESENT")
    mapped = remaps[ORIGINAL_OWNER]
    need(mapped.startswith("org/apache/commons/a/d__Type_")
         and "/" not in mapped[len("org/apache/commons/a/"):],
         "REMAP_NOT_A_REVIEWABLE_TYPE_ALIAS")
    mapped_import = mapped.replace("/", ".")
    mapped_name = mapped.rsplit("/", 1)[-1]
    spans = _ast_spans(before)
    original_text = before.decode("utf-8")
    replacements = [
        (*spans["IMPORT"], mapped_import),
        (*spans["CALL"], mapped_name),
    ]
    result = original_text
    for start, end, new in sorted(replacements, reverse=True):
        result = result[:start] + new + result[end:]
    new_bytes = result.encode("utf-8")
    need(new_bytes != before
         and ORIGINAL_IMPORT not in result
         and len(re.findall(r"\bd_\b", result)) == 0
         and result.count(mapped_import) == 1
         and len(re.findall(r"\b" + re.escape(mapped_name) + r"\b", result)) == 2,
         "PATCHED_SOURCE_IMPORT_OR_RECEIVER_NOT_UNIQUE")
    changed = [(path, new_bytes if path == TARGET else bytes_)
               for path, bytes_ in entries]
    manifest = hashlib.sha256()
    for rel, contents in changed:
        manifest.update(rel.encode("utf-8") + b"\0")
        manifest.update(hashlib.sha256(contents).digest())
    report = {
        "schema_version": 1,
        "kind": "private_v309_provisional_original_class_shadow_java_source_edit_r135",
        "source_archive_sha256": source_sha256,
        "original_client_sha256": original_sha256,
        "source_file_count": len(entries),
        "changed_java_source_file_count": 1,
        "unmodified_java_source_file_count": len(entries) - 1,
        "original_target_file_sha256": target_sha256,
        "provisional_patched_file_sha256": _source_hash(new_bytes),
        "patched_source_manifest_sha256": manifest.hexdigest(),
        "r125_original_namespace_mapping_sha256":
            solution["private_mapping_sha256"],
        "original_static_method_descriptor_verified": True,
        "ast_import_and_call_spans_verified": True,
        "no_regex_only_source_rewrite": True,
        "original_client_executed": False,
        "candidate_source_compiled": False,
        "alias_proven_same_semantic_class": False,
        "original_deobfuscated_source_tree_complete": False,
    }
    need(sha_file(source_zip) == source_sha256
         and sha_file(original_jar) == original_sha256,
         "PRIVATE_INPUT_CHANGED_DURING_PATCH")
    return changed, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_decompiled_zip")
    parser.add_argument("private_original_v309_jar")
    parser.add_argument("fresh_private_client_java_zip")
    parser.add_argument("fresh_private_report_json")
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--original-sha256", default=CANONICAL_V309)
    parser.add_argument("--target-sha256", default=CANONICAL_TARGET_SHA256)
    opts = parser.parse_args(argv)
    dest = Path(opts.fresh_private_client_java_zip)
    report_path = Path(opts.fresh_private_report_json)
    try:
        need(dest != report_path
             and not dest.exists() and not report_path.exists()
             and dest.parent.is_dir() and report_path.parent.is_dir()
             and not dest.is_symlink() and not report_path.is_symlink(),
             "PRIVATE_OUTPUTS_MUST_BE_FRESH")
        files, proof = patch_private_candidate(
            opts.private_decompiled_zip, opts.private_original_v309_jar,
            source_sha256=opts.source_sha256,
            original_sha256=opts.original_sha256,
            target_sha256=opts.target_sha256)
        # Write to fresh private temp files; only client .java files are staged.
        with tempfile.TemporaryDirectory(
                prefix="spk-r135-stage-", dir=dest.parent) as stage:
            archive_tmp = Path(stage) / "candidate.zip"
            report_tmp = Path(stage) / "proof.json"
            with zipfile.ZipFile(archive_tmp, "w",
                                 compression=zipfile.ZIP_DEFLATED) as out:
                for rel, data in files:
                    entry = zipfile.ZipInfo("src/main/java/" + rel,
                                            (1980, 1, 1, 0, 0, 0))
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    out.writestr(entry, data)
            proof["private_client_java_preview_zip_sha256"] = sha_file(archive_tmp)
            report_tmp.write_text(
                json.dumps(proof, indent=2, sort_keys=True) + "\n",
                encoding="utf-8")
            archive_tmp.replace(dest)
            report_tmp.replace(report_path)
        print("PRIVATE_R135_SOURCE_ALIAS_EDIT_COMPLETE")
        print("private_report_sha256=" + sha_file(report_path))
    except Exception:
        parser.error("PRIVATE_R135_REVIEWED_ALIAS_PATCH_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
