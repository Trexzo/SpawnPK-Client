"""R141/R143: provisional v309 class-casefold and class/package-shadow type repair.

R125 may rename original binary class leaf identities to resolve Windows case
collisions. A Java source import then names an alias that was NOT present in the
original decompiler candidate; its uses must change together. Only a trusted
JDK parse-only AST can authorize supported type positions. Expression/static
uses, source class shadowing, multiple imported aliases, or any uncertain
case leave the ENTIRE affected source file unchanged. Never invent names.
No original game classfile or private Java source is published to GitHub.
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

from .private_client_namespace_legalizer_r125 import (
    CANONICAL_V309, plan_client_namespaces,
)
from .private_client_source_ast_census_r126 import source_members, sha_file
from .private_v309_dependency_closure_r136 import audit_pinned_original_jar


class PrivateImportedTypeAliasR141Error(ValueError):
    pass


def need(value, error):
    if not value:
        raise PrivateImportedTypeAliasR141Error(error)


def manifest(entries):
    digest = hashlib.sha256()
    for path, data in entries:
        digest.update(path.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


def _exact_casefold_type_aliases(nonrs_names, original_sha256):
    """Only independently justified class-casefold/shadow leaf aliases from R125."""
    proof = plan_client_namespaces(
        nonrs_names, include_identifiers=True,
        original_jar_sha256=original_sha256)
    eligible = {}
    case_count = 0
    shadow_count = 0
    for row in proof["remaps"]:
        old, new = row["old_internal_name"], row["new_internal_name"]
        oldpath, _, oldleaf = old.rpartition("/")
        newpath, _, newleaf = new.rpartition("/")
        if (oldpath != newpath or oldleaf == newleaf
                or "$" in old or "$" in new):
            continue
        reasons = set(row["reasons"])
        is_case = "windows_class_case" in reasons
        is_shadow = "java_class_package_shadow" in reasons
        if not (is_case or is_shadow):
            continue
        # These are disjoint actual R125 class-leaf legality operations.
        # Never rewrite a source import using an unrelated guessed alias.
        need(not (is_case and is_shadow),
             "R125_AMBIGUOUS_CASE_AND_CLASS_PACKAGE_SHADOW_ALIAS")
        if is_case:
            need(newleaf.startswith(oldleaf + "__Case_"),
                 "UNEXPECTED_R125_CLASS_CASE_ALIAS")
            case_count += 1
        else:
            need(newleaf.startswith(oldleaf + "__Type_"),
                 "UNEXPECTED_R125_CLASS_PACKAGE_SHADOW_ALIAS")
            shadow_count += 1
        eligible[old.replace("/", ".")] = new.replace("/", ".")
    need(len(set(eligible.values())) == len(eligible),
         "R125_IMPORTED_LEAF_ALIAS_TARGET_COLLISION")
    return eligible, proof["private_mapping_sha256"], case_count, shadow_count


def _ast_type_alias_spans(source, original_import, *,
                          helper_classes, empty, java, work):
    content = source.decode("utf-8", errors="strict")
    need("\r" not in content and all(ord(c) <= 0xffff for c in content),
         "AST_SOURCE_UTF16_OFFSET_AMBIGUITY")
    path = work / "TypeOverlay.java"
    path.write_bytes(source)
    environ = os.environ.copy()
    for key in ("CLASSPATH", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS",
                "_JAVA_OPTIONS"):
        environ.pop(key, None)
    try:
        proc = subprocess.run(
            [java, "-cp", str(helper_classes),
             "PrivateImportedTypeAliasSpansR141",
             str(path), str(empty), original_import],
            cwd=work, env=environ, stdin=subprocess.DEVNULL,
            capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PrivateImportedTypeAliasR141Error(
            "TRUSTED_AST_SOURCE_SCAN_NOT_COMPLETED") from exc
    need(proc.returncode == 0 and len(proc.stdout) <= 200000,
         "TRUSTED_AST_TYPE_ALIAS_SCAN_FAILED")
    spans = []
    for item in proc.stdout.decode("utf-8", errors="strict").splitlines():
        parts = item.split("\t")
        need(len(parts) == 4 and
             parts[0] in ("IMPORT", "TYPE", "UNSUPPORTED"),
             "R141_AST_SPAN_PROTOCOL_INVALID")
        start, end = int(parts[1]), int(parts[2])
        token = parts[3]
        if parts[0] == "UNSUPPORTED":
            spans.append(("UNSUPPORTED", 0, 0, token))
            continue
        need(0 <= start < end <= len(content) and
             content[start:end] == token,
             "R141_AST_SPAN_SOURCE_MISMATCH")
        spans.append((parts[0], start, end, token))
    need(sum(kind == "IMPORT" for kind, *_ in spans) == 1,
         "R141_SOURCE_IMPORT_NOT_UNIQUE")
    return spans


def rewrite_private_candidate(entries, eligible, *, java_helper=None):
    """Guarded complete client Java preview (no original runtime class fallback).

    Uncertain source file cases remain bit-identical and counted; no partial
    method/source-file patches. A full source file is never accepted solely
    because an original type name happens to share its spelling.
    """
    need(type(eligible) is dict and all(
        type(old) is str and type(new) is str and old != new and
        old.rsplit(".", 1)[0] == new.rsplit(".", 1)[0]
        for old, new in eligible.items()),
        "R141_UNREVIEWED_IMPORT_ALIAS_SET")
    java, javac = shutil.which("java"), shutil.which("javac")
    need(java and javac, "R141_JDK_REQUIRED")
    helper = (Path(java_helper) if java_helper else
              Path(__file__).resolve().parent /
              "java" / "PrivateImportedTypeAliasSpansR141.java")
    need(helper.is_file() and not helper.is_symlink(),
         "R141_TRUSTED_AST_HELPER_REQUIRED")
    edited = []
    affected_files = 0
    changed_files = 0
    changed_imports = 0
    changed_type_occurrences = 0
    withheld_files = 0
    with tempfile.TemporaryDirectory(prefix="spk-r141-types-") as td:
        work = Path(td)
        classes = work / "trusted-helper"
        empty = work / "empty"
        classes.mkdir()
        empty.mkdir()
        environ = os.environ.copy()
        for key in ("CLASSPATH", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS",
                    "_JAVA_OPTIONS"):
            environ.pop(key, None)
        try:
            proc = subprocess.run(
                [javac, "-encoding", "UTF-8", "-proc:none",
                 "-classpath", str(empty), "-sourcepath", str(empty),
                 "-d", str(classes), str(helper)],
                cwd=work, env=environ, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PrivateImportedTypeAliasR141Error(
                "TRUSTED_AST_HELPER_COMPILE_NOT_COMPLETED") from exc
        need(proc.returncode == 0, "R141_TRUSTED_AST_HELPER_COMPILE_FAILED")
        for rel, body in entries:
            before = body.decode("utf-8", errors="strict")
            imports = re.findall(
                r"(?m)^[ \t]*import[ \t]+(?!static\b)([A-Za-z_$][\w.$]*)[ \t]*;",
                before)
            affected = [name for name in imports if name in eligible]
            if not affected:
                edited.append((rel, body))
                continue
            affected_files += 1
            # Multiple independent aliases are safe only as ONE atomic
            # source-file transaction. No best-effort subset is permitted.
            # The per-import JDK AST scan sees the same unmodified source.
            if (len(affected) > 8 or len(set(affected)) != len(affected)
                    or len(set(imports)) != len(imports)):
                withheld_files += 1
                edited.append((rel, body))
                continue
            oldsimples = [old.rsplit(".", 1)[-1] for old in affected]
            newsimples = [eligible[old].rsplit(".", 1)[-1]
                          for old in affected]
            # An old or new simple name must never collide with ANY other
            # imported type or with another alias being concurrently patched.
            all_old_and_new = oldsimples + newsimples
            imported_other_simples = [
                name.rsplit(".", 1)[-1]
                for name in imports if name not in affected
            ]
            if (len(set(all_old_and_new)) != len(all_old_and_new)
                    or any(s in imported_other_simples
                           for s in all_old_and_new)):
                withheld_files += 1
                edited.append((rel, body))
                continue
            changes = []
            all_types = 0
            blocked = False
            for old in affected:
                alias = eligible[old]
                oldsimple = old.rsplit(".", 1)[-1]
                newsimple = alias.rsplit(".", 1)[-1]
                # Includes the qualification-prefix ambiguity: e.g. a.b
                # and a.b.C in a single source. No implicit guess is safe.
                if before.count(old) != 1:
                    blocked = True
                    break
                spans = _ast_type_alias_spans(
                    body, old, helper_classes=classes, empty=empty,
                    java=java, work=work)
                if any(kind == "UNSUPPORTED" for kind, *_ in spans):
                    blocked = True
                    break
                for kind, start, end, source in spans:
                    if kind == "IMPORT":
                        need(source == old,
                             "R144_ORIGINAL_IMPORT_AST_MISMATCH")
                        changes.append((start, end, alias))
                    else:
                        need(source == oldsimple,
                             "R144_TYPE_IDENTIFIER_AST_MISMATCH")
                        changes.append((start, end, newsimple))
                        all_types += 1
            if blocked:
                withheld_files += 1
                edited.append((rel, body))
                continue
            ordered = sorted(changes, key=lambda x: x[0])
            need(len([1 for _, _, _ in changes]) >= len(affected) and
                 all(ordered[i][1] <= ordered[i+1][0]
                     for i in range(len(ordered)-1)),
                 "R144_ATOMIC_AST_PATCH_SPANS_OVERLAP")
            candidate = before
            for start, end, target in reversed(ordered):
                candidate = candidate[:start] + target + candidate[end:]
            final_imports = re.findall(
                r"(?m)^[ \t]*import[ \t]+([\w.$]+)[ \t]*;", candidate)
            need(candidate != before and
                 all(candidate.count("import " + eligible[old] + ";") == 1
                     and old not in final_imports for old in affected),
                 "R144_ATOMIC_IMPORTS_NOT_ALL_REWRITTEN")
            edited.append((rel, candidate.encode("utf-8")))
            changed_files += 1
            changed_imports += len(affected)
            changed_type_occurrences += all_types
    need([path for path, _ in entries] == [path for path, _ in edited],
         "R141_SOURCE_COVERAGE_OR_ORDER_CHANGED")
    return edited, {
        "candidate_files_with_eligible_alias_imports": affected_files,
        "changed_java_source_file_count": changed_files,
        "reviewed_rewritten_import_count": changed_imports,
        "reviewed_rewritten_type_identifier_count": changed_type_occurrences,
        "withheld_ambiguous_java_file_count": withheld_files,
        "unchanged_java_source_file_count": len(entries) - changed_files,
    }


def patch_private_casefold_source(source_zip, original_jar, *,
                                  source_sha256,
                                  original_sha256=CANONICAL_V309):
    need(sha_file(source_zip) == source_sha256 and
         sha_file(original_jar) == original_sha256,
         "R141_PRIVATE_SOURCE_ORIGINAL_SHA_MISMATCH")
    original_sources = source_members(source_zip, source_sha256)
    graph = audit_pinned_original_jar(
        original_jar, original_sha256=original_sha256,
        include_private_names=True)
    nonrs = set(graph["private_dependency_partition"][
        "provisional_non_rs_untainted"])
    need(len(nonrs) == graph["non_rs_without_known_rs_dependency_chain"],
         "R141_PROVISIONAL_CLASSPATH_CHANGED")
    aliases, mapping_digest, case_count, shadow_count = _exact_casefold_type_aliases(
        nonrs, original_sha256)
    rewritten, proof = rewrite_private_candidate(original_sources, aliases)
    result = {
        "schema_version": 1,
        "kind": "private_v309_casefold_java_import_type_alias_repair_r141",
        "original_client_sha256": original_sha256,
        "source_archive_sha256": source_sha256,
        "source_java_file_count": len(original_sources),
        "eligible_original_nonrs_casefold_type_count": case_count,
        "eligible_original_nonrs_shadow_type_count": shadow_count,
        "eligible_original_nonrs_all_rewritable_leaf_aliases": len(aliases),
        "private_r125_mapping_sha256": mapping_digest,
        "source_manifest_before_sha256": manifest(original_sources),
        "source_manifest_after_sha256": manifest(rewritten),
        "original_binary_executed": False,
        "decompiled_client_executed": False,
        "accepted_original_client_class_or_member_lineage": False,
        "provisional_nonrs_classpath_certified_third_party": False,
        "whole_client_source_build_verified": False,
        "original_project_binary_fallback_fully_ruled_out": False,
        "public_source_tree_release_authorized": False,
        **proof,
    }
    need(sha_file(source_zip) == source_sha256 and
         sha_file(original_jar) == original_sha256,
         "R141_PRIVATE_INPUT_CHANGED_DURING_PATCH")
    return rewritten, result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_decompiled_client_source_zip")
    p.add_argument("private_original_v309_jar")
    p.add_argument("fresh_private_repaired_java_zip")
    p.add_argument("fresh_private_report_json")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    opts = p.parse_args(argv)
    archive_out = Path(opts.fresh_private_repaired_java_zip)
    report_out = Path(opts.fresh_private_report_json)
    try:
        need(archive_out != report_out and
             not archive_out.exists() and not report_out.exists() and
             archive_out.parent.is_dir() and report_out.parent.is_dir() and
             not archive_out.is_symlink() and not report_out.is_symlink(),
             "R141_PRIVATE_OUTPUTS_MUST_BE_FRESH")
        entries, proof = patch_private_casefold_source(
            opts.private_decompiled_client_source_zip,
            opts.private_original_v309_jar,
            source_sha256=opts.source_sha256,
            original_sha256=opts.original_sha256)
        with tempfile.TemporaryDirectory(
                prefix="spk-r141-private-stage-",
                dir=archive_out.parent) as td:
            tmp = Path(td)
            archive = tmp / "private-preview.zip"
            report = tmp / "sanitized.json"
            with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zip_:
                for rel, data in entries:
                    member = ZipInfo("src/main/java/" + rel,
                                     (1980, 1, 1, 0, 0, 0))
                    member.compress_type = ZIP_DEFLATED
                    zip_.writestr(member, data)
            proof["private_preview_java_zip_sha256"] = sha_file(archive)
            report.write_text(
                json.dumps(proof, indent=2, sort_keys=True) + "\n",
                encoding="utf-8")
            archive.replace(archive_out)
            report.replace(report_out)
        print("R141_PROVISIONAL_PRIVATE_AST_CASEFOLD_SOURCE_REPAIR_RECORDED")
        print("private_report_sha256=" + sha_file(report_out))
    except Exception:
        p.error("R141_PRIVATE_CASEFOLD_SOURCE_REPAIR_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
