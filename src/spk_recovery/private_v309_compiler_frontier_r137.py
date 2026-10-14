"""R137: private, reproducible v309 source javac error frontier, NOT acceptance.

Builds a temporary diagnostic-only subset of the SHA-pinned ORIGINAL v309
non-rs classfiles, excluding every direct/transitive dependency on game rs/
code according to R136. A remaining class being "non-rs" is never taken as
independent third-party provenance. Compiler inputs/outputs stay private.
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

from .private_v309_dependency_closure_r136 import audit_pinned_original_jar
from .private_client_source_ast_census_r126 import source_members, sha_file
from .private_client_namespace_legalizer_r125 import CANONICAL_V309


class PrivateCompilerFrontierR137Error(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise PrivateCompilerFrontierR137Error(reason)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _write_provisional_original_nonrs_capsule(original_jar, allowed, target):
    """Private diagnostic only. Never call this capsule certified third-party."""
    need(type(allowed) is set and bool(allowed)
         and all(type(n) is str and not n.startswith("rs/") for n in allowed),
         "NON_RS_CAPSULE_ALLOWLIST_INVALID")
    with ZipFile(original_jar) as original, ZipFile(
            target, "w", compression=ZIP_DEFLATED) as out:
        present = set()
        original_members = set(original.namelist())
        for name in sorted(allowed):
            entry = name + ".class"
            need(entry in original_members,
                 "ORIGINAL_CAPSULE_MEMBER_MISSING")
            data = original.read(entry)
            member = ZipInfo(entry, date_time=(1980, 1, 1, 0, 0, 0))
            member.compress_type = ZIP_DEFLATED
            out.writestr(member, data)
            present.add(name)
    need(present == allowed, "ORIGINAL_CAPSULE_CLASS_COUNT_MISMATCH")
    with ZipFile(target) as verify:
        listed = {x[:-6] for x in verify.namelist()
                  if x.endswith(".class")}
        need(listed == allowed and all(not x.startswith("rs/")
                                      for x in listed),
             "ORIGINAL_RS_BINARY_LEAK_IN_DIAGNOSTIC_CAPSULE")
    return _sha256(target.read_bytes())


def _normalize_private_provisional_capsule(input_jar, output_jar, scratch):
    """Use existing R125 solver + R8R constant-pool remapper, private only.

    This does not certify original-derived dependency ownership or source
    identity. The whole original rs/ namespace was already excluded by R136.
    """
    from .private_client_namespace_legalizer_r125 import (
        plan_client_namespaces,
    )
    from .namespace_collision import analyze_namespace_collisions
    from .collision_bytecode_remap import transform_collision_jar

    with ZipFile(input_jar) as data:
        names = {n[:-6] for n in data.namelist()
                 if n.endswith(".class")}
    need(bool(names) and all(not n.startswith("rs/") for n in names),
         "R138_GAME_CLASS_IN_PROVISIONAL_CAPSULE")
    original_sha = sha_file(input_jar)
    proof = plan_client_namespaces(
        names, include_identifiers=True,
        original_jar_sha256=original_sha)
    pre = analyze_namespace_collisions(input_jar)
    plan = {
        "schema_version": 1,
        "kind": "class_package_namespace_collision_plan",
        "identifiers_included": True,
        "plan_id": "R138_DIAGNOSTIC_" + original_sha[:20].upper(),
        "collision_report_id": pre["report_id"],
        "readable_jar_sha256": original_sha,
        "remaps": [
            {"old_internal_name": row["old_internal_name"],
             "new_internal_name": row["new_internal_name"]}
            for row in proof["remaps"]
        ],
    }
    plan_path = scratch / "private-original-namespace-plan.json"
    plan_path.write_text(
        json.dumps(plan, sort_keys=True) + "\n", encoding="utf-8")
    transform = transform_collision_jar(
        input_jar, plan_path, output_jar)
    need(transform["summary"]["post_collision_edge_count"] == 0
         and transform["summary"]["input_class_count"] == len(names),
         "R138_REMAP_DID_NOT_PRESERVE_ORIGINAL_CLASS_COVERAGE")
    with ZipFile(output_jar) as mapped:
        entries = [n for n in mapped.namelist() if n.endswith(".class")]
    need(len(entries) == len(names)
         and all(not n.startswith("rs/") for n in entries),
         "R138_ORIGINAL_GAME_BINARY_REINTRODUCED")
    return {
        "pre_collision_edges": transform["summary"][
            "pre_collision_edge_count"],
        "post_collision_edges": 0,
        "classfile_remap_count": transform["summary"][
            "expanded_remap_count"],
        "changed_original_classfile_count": transform["summary"][
            "rewritten_class_count"],
        "private_mapping_digest_sha256": proof["private_mapping_sha256"],
        "private_normalized_capsule_sha256": sha_file(output_jar),
    }


def private_source_compile_frontier(source_zip, original_jar, *,
                                    source_sha256,
                                    original_sha256=CANONICAL_V309,
                                    maximum_diagnostics=3000,
                                    normalize_diagnostic_classpath=False):
    need(type(maximum_diagnostics) is int
         and 100 <= maximum_diagnostics <= 3000,
         "COMPILER_ERROR_LIMIT_INVALID")
    need(sha_file(source_zip) == source_sha256
         and sha_file(original_jar) == original_sha256,
         "PRIVATE_COMPILER_INPUT_SHA256_MISMATCH")
    sources = source_members(source_zip, source_sha256)
    graph = audit_pinned_original_jar(
        original_jar, original_sha256=original_sha256,
        include_private_names=True)
    allowed = set(graph["private_dependency_partition"][
        "provisional_non_rs_untainted"])
    need(graph["non_rs_without_known_rs_dependency_chain"] == len(allowed),
         "R136_ALLOWED_CLASS_COUNT_MISMATCH")
    javac = shutil.which("javac")
    need(javac is not None, "JDK_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r137-private-javac-") as temp:
        root = Path(temp)
        capsule = root / "DIAGNOSTIC_ORIGINAL_NONRS_UNVERIFIED.jar"
        capsule_sha = _write_provisional_original_nonrs_capsule(
            original_jar, allowed, capsule)
        normalized_evidence = None
        selected_capsule = capsule
        if normalize_diagnostic_classpath:
            selected_capsule = root / "normalized-original-nonrs-private.jar"
            normalized_evidence = _normalize_private_provisional_capsule(
                capsule, selected_capsule, root)
        srcroot = root / "client-java"
        output = root / "compiled-preview"
        empty = root / "empty-external-sourcepath"
        srcroot.mkdir()
        output.mkdir()
        empty.mkdir()
        paths = []
        for name, data in sources:
            file = srcroot / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
            paths.append(str(file))
        env = os.environ.copy()
        for k in ("CLASSPATH", "JAVA_TOOL_OPTIONS",
                  "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS"):
            env.pop(k, None)
        cmd = [
            javac, "--release", "11", "-proc:none", "-implicit:none",
            "-encoding", "UTF-8", "-Xmaxerrs", str(maximum_diagnostics),
            "-classpath", str(selected_capsule),
            "-sourcepath", str(empty),
            "-d", str(output),
        ] + paths
        try:
            proc = subprocess.run(
                cmd, cwd=root, env=env, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=180, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PrivateCompilerFrontierR137Error(
                "PRIVATE_SOURCE_JAVAC_NOT_COMPLETED") from exc
        need(len(proc.stderr) <= 20_000_000 and
             len(proc.stdout) <= 1_000_000,
             "PRIVATE_JAVAC_DIAGNOSTICS_UNBOUNDED")
        stderr = proc.stderr.decode("utf-8", errors="replace")
        errors = [line for line in stderr.splitlines()
                  if re.search(r":\s*error:", line)]
        counts = {
            "unresolved_symbol_errors": sum(
                "cannot find symbol" in line for line in errors),
            "missing_package_errors": sum(
                "does not exist" in line for line in errors),
            "other_compiler_errors": sum(
                "cannot find symbol" not in line
                and "does not exist" not in line for line in errors),
        }
        if proc.returncode != 0:
            need(bool(errors), "JAVAC_FAILED_WITHOUT_CLASSIFIED_ERRORS")
        compiled_classes = [
            file for file in output.rglob("*.class") if file.is_file()]
        result = {
            "schema_version": 1,
            "kind": "private_v309_diagnostic_source_javac_frontier_r137",
            "original_client_sha256": original_sha256,
            "source_zip_sha256": source_sha256,
            "source_java_file_count": len(sources),
            "original_rs_classfiles_excluded": graph[
                "original_rs_game_classes"],
            "non_rs_game_bound_classfiles_excluded": graph[
                "non_rs_with_any_rs_dependency_chain"],
            "provisional_non_rs_classpath_classfiles": len(allowed),
            "private_unmapped_capsule_sha256": capsule_sha,
            "private_diagnostic_classpath_sha256": sha_file(
                selected_capsule),
            "diagnostic_classpath_collision_normalized":
                bool(normalize_diagnostic_classpath),
            "diagnostic_namespace_remap_evidence":
                normalized_evidence if normalized_evidence is not None
                else {"not_applied": True},
            "javac_release": 11,
            "annotation_processing_disabled": True,
            "implicit_class_compilation_disabled": True,
            "ambient_java_options_and_classpath_disabled": True,
            "original_rs_classes_directly_on_classpath": False,
            "compiler_exit_code": proc.returncode,
            "observed_error_diagnostic_count": len(errors),
            "diagnostics_may_be_truncated": len(errors) >= maximum_diagnostics,
            "error_categories": counts,
            "private_full_stderr_sha256": _sha256(proc.stderr),
            "private_compiled_preview_classfiles_count":
                len(compiled_classes),
            "source_and_original_client_executed": False,
            "candidate_source_compiled_with_independently_owned_deps": False,
            "non_rs_original_binary_capsule_certified_third_party": False,
            "original_project_binary_fallback_fully_ruled_out": False,
            "complete_original_client_source_build_accepted": False,
        }
        need(sha_file(source_zip) == source_sha256
             and sha_file(original_jar) == original_sha256,
             "PRIVATE_COMPILER_INPUT_CHANGED_DURING_BUILD")
        return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_decompiled_java_zip")
    p.add_argument("private_original_v309_jar")
    p.add_argument("fresh_private_javac_report")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    p.add_argument("--maximum-diagnostics", type=int, default=3000)
    p.add_argument("--collision-normalize-provisional-classpath",
                   action="store_true")
    args = p.parse_args(argv)
    output = Path(args.fresh_private_javac_report)
    try:
        need(not output.exists() and not output.is_symlink()
             and output.parent.is_dir() and not output.parent.is_symlink(),
             "FRESH_PRIVATE_COMPILER_REPORT_REQUIRED")
        report = private_source_compile_frontier(
            args.private_decompiled_java_zip,
            args.private_original_v309_jar,
            source_sha256=args.source_sha256,
            original_sha256=args.original_sha256,
            maximum_diagnostics=args.maximum_diagnostics,
            normalize_diagnostic_classpath=
                args.collision_normalize_provisional_classpath)
        output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        print("PRIVATE_R137_COMPILER_FRONTIER_COLLECTED")
        print("private_report_sha256=" + sha_file(output))
    except Exception:
        p.error("PRIVATE_R137_COMPILER_FRONTIER_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
