"""R139: private Java source import overlay for verified R125/R138 package moves.

Only explicit non-static imports to R136-provisionally-unlinked classes are
eligible. A same-simple-name R125 relocation is required; changed type names,
wildcards, static imports, qualified usages, and source declarations remain
unresolved. Java AST positions, not regular expressions, authorize edits.
No private source, original binary, or staged output is published to GitHub.
This is NOT an accepted original client reconstruction or licensed classpath.
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
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .private_client_namespace_legalizer_r125 import (
    CANONICAL_V309, plan_client_namespaces,
)
from .private_client_source_ast_census_r126 import source_members, sha_file
from .private_v309_dependency_closure_r136 import audit_pinned_original_jar


class PrivateImportOverlayR139Error(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise PrivateImportOverlayR139Error(reason)


def _sha(contents):
    return hashlib.sha256(contents).hexdigest()


def _manifest(entries):
    digest = hashlib.sha256()
    for rel, data in entries:
        digest.update(rel.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


def safe_package_only_imports(names, *, namespace_sha256=None):
    """Generate eligible mapping from a real R125 plan; never semantic labels."""
    require(type(names) is set and names and
            all(isinstance(x, str) and not x.startswith("rs/")
                for x in names), "ONLY_R136_PROVISIONAL_NON_RS_NAMES")
    proof = plan_client_namespaces(
        names, include_identifiers=True, original_jar_sha256=namespace_sha256)
    allowed = {}
    withheld = {}
    for row in proof["remaps"]:
        old, new = row["old_internal_name"], row["new_internal_name"]
        if ("$" in old or "$" in new or
                old.rsplit("/", 1)[-1] != new.rsplit("/", 1)[-1]):
            withheld[old.replace("/", ".")] = new.replace("/", ".")
        else:
            allowed[old.replace("/", ".")] = new.replace("/", ".")
    require(len(set(allowed.values())) == len(allowed),
            "REMAP_FQN_MUST_BE_INJECTIVE")
    return allowed, withheld, proof["private_mapping_sha256"]


def _ast_imports(source, file, java, helper_classes, empty):
    """Run a fixed locally compiled helper in parse-only mode."""
    text = source.decode("utf-8", errors="strict")
    require("\r" not in text and all(ord(c) <= 0xffff for c in text),
            "JAVA_AST_UTF16_SOURCE_OFFSET_AMBIGUOUS")
    file.write_bytes(source)
    env = os.environ.copy()
    for setting in ("CLASSPATH", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS",
                    "_JAVA_OPTIONS"):
        env.pop(setting, None)
    try:
        proc = subprocess.run(
            [java, "-cp", str(helper_classes), "PrivateSingleImportSpansR139",
             str(file), str(empty)],
            cwd=file.parent, env=env, stdin=subprocess.DEVNULL,
            capture_output=True, timeout=40, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PrivateImportOverlayR139Error("JAVA_IMPORT_AST_NOT_COMPLETED") from exc
    require(proc.returncode == 0 and len(proc.stdout) <= 200000,
            "JAVA_IMPORT_AST_PARSE_FAILED")
    found = []
    for line in proc.stdout.decode("utf-8", errors="strict").splitlines():
        cells = line.split("\t")
        require(len(cells) == 3 and cells[0].isdigit() and
                cells[1].isdigit(), "JAVA_AST_IMPORT_PROTOCOL_BAD")
        start, end = int(cells[0]), int(cells[1])
        name = cells[2]
        require(0 <= start < end <= len(text) and
                text[start:end] == name, "AST_OFFSET_IMPORT_CONTENT_MISMATCH")
        found.append((start, end, name))
    require(len({(a, b) for a, b, _ in found}) == len(found),
            "DUPLICATE_AST_IMPORT_SPAN")
    return found


def import_overlay_entries(entries, eligible, withheld, *,
                           java_helper=None):
    """Return unchanged+edited source bytes with fail-closed AST authority.

    A whole-qualified use of a relocated type outside the import is left
    untouched and the entire containing file is withheld from the overlay.
    """
    require(type(eligible) is dict and type(withheld) is dict and
            not (set(eligible) & set(withheld)), "INVALID_IMPORT_MAPS")
    java, javac = shutil.which("java"), shutil.which("javac")
    require(java and javac, "JDK_REQUIRED_FOR_AST_REWRITE")
    helper = (Path(java_helper) if java_helper else
              Path(__file__).resolve().parent / "java" /
              "PrivateSingleImportSpansR139.java")
    require(helper.is_file() and not helper.is_symlink(),
            "TRUSTED_R139_AST_HELPER_REQUIRED")
    changed = []
    blocked_files = 0
    edited_imports = 0
    withheld_imports = 0
    with tempfile.TemporaryDirectory(prefix="spk-r139-import-") as td:
        root = Path(td)
        classes = root / "trusted-helper"
        empty = root / "empty"
        classes.mkdir()
        empty.mkdir()
        env = os.environ.copy()
        for key in ("CLASSPATH", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS",
                    "_JAVA_OPTIONS"):
            env.pop(key, None)
        command = [javac, "-encoding", "UTF-8", "-proc:none",
                   "-classpath", str(empty), "-sourcepath", str(empty),
                   "-d", str(classes), str(helper)]
        try:
            proc = subprocess.run(
                command, cwd=root, env=env, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PrivateImportOverlayR139Error(
                "TRUSTED_R139_HELPER_COMPILE_NOT_COMPLETED") from exc
        require(proc.returncode == 0, "TRUSTED_R139_HELPER_DID_NOT_COMPILE")
        for index, (rel, raw) in enumerate(entries):
            text = raw.decode("utf-8", errors="strict")
            # This regex ONLY selects candidate files for AST inspection.
            # Never use these regex matches to locate or authorize patches.
            names = set(re.findall(
                r"(?m)^[ \t]*import[ \t]+(?!static\b)([\w.$]+)[ \t]*;",
                text))
            relevant = names & (set(eligible) | set(withheld))
            if not relevant:
                changed.append((rel, raw))
                continue
            file = root / ("candidate-" + str(index) + ".java")
            spans = _ast_imports(raw, file, java, classes, empty)
            seen = [name for _, _, name in spans if name in relevant]
            require(set(seen) == relevant, "PRESCAN_AST_IMPORT_DISAGREEMENT")
            blocked = 0
            patches = []
            for start, end, old in spans:
                if old in withheld:
                    blocked += 1
                    withheld_imports += 1
                    continue
                if old not in eligible:
                    continue
                # A qualified use outside its sole import would require
                # independent AST symbol-resolution; defer the whole file.
                if text.count(old) != 1:
                    blocked += 1
                    withheld_imports += 1
                    continue
                target = eligible[old]
                if target.rsplit(".", 1)[-1] != old.rsplit(".", 1)[-1]:
                    blocked += 1
                    withheld_imports += 1
                    continue
                patches.append((start, end, target))
            if blocked:
                blocked_files += 1
                changed.append((rel, raw))
                continue
            replacement = text
            for start, end, target in sorted(patches, reverse=True):
                replacement = replacement[:start] + target + replacement[end:]
            if replacement != text:
                edited_imports += len(patches)
            changed.append((rel, replacement.encode("utf-8")))
    require([p for p, _ in changed] == [p for p, _ in entries],
            "CLIENT_SOURCE_FILES_CHANGED_OR_REORDERED")
    return changed, {
        "changed_java_file_count": sum(x[1] != y[1]
                                       for x, y in zip(entries, changed)),
        "unchanged_java_file_count": sum(x[1] == y[1]
                                         for x, y in zip(entries, changed)),
        "ast_verified_explicit_import_edits": edited_imports,
        "whole_java_files_withheld_for_unresolved_imports": blocked_files,
        "withheld_unsafe_import_count": withheld_imports,
    }


def private_import_overlay(source_zip, original_jar, *,
                           source_sha256, original_sha256=CANONICAL_V309):
    require(sha_file(source_zip) == source_sha256 and
            sha_file(original_jar) == original_sha256,
            "PRIVATE_R139_INPUT_HASH_MISMATCH")
    entries = source_members(source_zip, source_sha256)
    graph = audit_pinned_original_jar(
        original_jar, original_sha256=original_sha256,
        include_private_names=True)
    names = set(graph["private_dependency_partition"][
        "provisional_non_rs_untainted"])
    require(len(names) == graph["non_rs_without_known_rs_dependency_chain"],
            "R136_CLASS_SET_HASH_OR_COUNT_MISMATCH")
    eligible, withheld, mapping_sha = safe_package_only_imports(
        names, namespace_sha256=original_sha256)
    updated, stats = import_overlay_entries(entries, eligible, withheld)
    report = {
        "schema_version": 1,
        "kind": "private_v309_provisional_dependency_import_overlay_r139",
        "source_archive_sha256": source_sha256,
        "original_client_sha256": original_sha256,
        "private_r125_provisional_mapping_sha256": mapping_sha,
        "source_java_file_count": len(entries),
        "provisional_non_rs_binary_class_count": len(names),
        "eligible_same_simple_name_class_mapping_count": len(eligible),
        "deferred_nontrivial_type_mapping_count": len(withheld),
        "source_manifest_before_sha256": _manifest(entries),
        "source_manifest_after_sha256": _manifest(updated),
        "original_binary_executed": False,
        "candidate_client_executed": False,
        "original_project_binary_fallback_fully_ruled_out": False,
        "non_rs_original_binaries_independently_certified": False,
        "class_and_member_semantic_lineage_accepted": False,
        "complete_v309_client_compilation_accepted": False,
        **stats,
    }
    require(sha_file(source_zip) == source_sha256 and
            sha_file(original_jar) == original_sha256,
            "R139_PRIVATE_INPUT_CHANGED_DURING_REWRITE")
    return updated, report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_client_java_source_zip")
    p.add_argument("private_original_v309_jar")
    p.add_argument("fresh_private_overlay_zip")
    p.add_argument("fresh_private_report_json")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    args = p.parse_args(argv)
    out = Path(args.fresh_private_overlay_zip)
    report_path = Path(args.fresh_private_report_json)
    try:
        require(out != report_path and not out.exists() and
                not report_path.exists() and out.parent.is_dir() and
                report_path.parent.is_dir() and
                not out.is_symlink() and not report_path.is_symlink(),
                "R139_OUTPUT_PATHS_MUST_BE_FRESH")
        files, report = private_import_overlay(
            args.private_client_java_source_zip, args.private_original_v309_jar,
            source_sha256=args.source_sha256,
            original_sha256=args.original_sha256)
        with tempfile.TemporaryDirectory(
                prefix="spk-r139-stage-", dir=out.parent) as td:
            zip_tmp, report_tmp = (
                Path(td) / "private-overlay.zip",
                Path(td) / "private-report.json")
            with ZipFile(zip_tmp, "w", ZIP_DEFLATED) as archive:
                for rel, raw in files:
                    name = "src/main/java/" + rel
                    item = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                    item.compress_type = ZIP_DEFLATED
                    archive.writestr(item, raw)
            report["private_preview_zip_sha256"] = sha_file(zip_tmp)
            report_tmp.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n",
                encoding="utf-8")
            zip_tmp.replace(out)
            report_tmp.replace(report_path)
        print("PRIVATE_R139_IMPORT_OVERLAY_REVIEW_COMPLETE")
        print("private_report_sha256=" + sha_file(report_path))
    except Exception:
        p.error("PRIVATE_R139_IMPORT_OVERLAY_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
