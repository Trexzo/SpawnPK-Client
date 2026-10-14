"""R140: exact-SHA-pinned private v309 R138+R139 compiler error delta.

Measure the same whole-Java source candidate twice against R138-normalized,
R136-filtered, *uncertified* original-derived non-rs binaries, before and
after R139's conservative AST import overlay. This is strictly diagnostic.
No original project binary can be accepted as a verified dependency here.
No source or original JAR is returned in report or committed to GitHub.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file
from .private_v309_compiler_frontier_r137 import private_source_compile_frontier
from .private_v309_import_overlay_r139 import private_import_overlay


class PrivateCompilerDeltaR140Error(ValueError):
    pass


def require(value, code):
    if not value:
        raise PrivateCompilerDeltaR140Error(code)


def _private_zip(entries, dest):
    """Deterministic, fresh, all-Java temporary archive; not a release."""
    require(not dest.exists(), "TEMP_CLIENT_JAVA_ZIP_NOT_FRESH")
    with ZipFile(dest, "w", compression=ZIP_DEFLATED) as archive:
        for rel, data in entries:
            require(rel.endswith(".java") and not rel.startswith("/") and
                    "\\" not in rel and ".." not in rel.split("/") and
                    all(part not in ("", ".", "..") for part in rel.split("/")),
                    "OVERLAY_CONTAINS_UNSAFE_SOURCE_PATH")
            member = ZipInfo("src/main/java/" + rel,
                             date_time=(1980, 1, 1, 0, 0, 0))
            member.compress_type = ZIP_DEFLATED
            archive.writestr(member, data)


def _categories(report):
    return {key: report["error_categories"][key]
            for key in ("unresolved_symbol_errors", "missing_package_errors",
                        "other_compiler_errors")}


def compare_private_original_source_javac(source_zip, original_jar, *,
                                         source_sha256,
                                         original_sha256=CANONICAL_V309,
                                         maximum_diagnostics=3000):
    """Two true compilations, zero rs-class direct fallback, no certification."""
    require(sha_file(source_zip) == source_sha256 and
            sha_file(original_jar) == original_sha256,
            "R140_PRIVATE_SOURCE_ORIGINAL_SHA_MISMATCH")
    require(type(maximum_diagnostics) is int and
            100 <= maximum_diagnostics <= 3000,
            "R140_COMPILER_DIAGNOSTIC_LIMIT_INVALID")

    # Reuse the same R136 partition / R125 namespace plan as R138, not an
    # independently guessed "external" classpath.
    overlay, rewrite = private_import_overlay(
        source_zip, original_jar, source_sha256=source_sha256,
        original_sha256=original_sha256)
    require(rewrite["source_archive_sha256"] == source_sha256 and
            rewrite["original_client_sha256"] == original_sha256 and
            rewrite["source_java_file_count"] == len(overlay),
            "R139_INPUTS_OR_SOURCE_COVERAGE_DRIFTED")
    with tempfile.TemporaryDirectory(prefix="spk-r140-private-") as tmp:
        temporary = Path(tmp) / "PRIVATE_OVERLAY_NOT_FOR_PUBLICATION.zip"
        _private_zip(overlay, temporary)
        after_sha256 = sha_file(temporary)
        before = private_source_compile_frontier(
            source_zip, original_jar, source_sha256=source_sha256,
            original_sha256=original_sha256,
            maximum_diagnostics=maximum_diagnostics,
            normalize_diagnostic_classpath=True)
        after = private_source_compile_frontier(
            temporary, original_jar, source_sha256=after_sha256,
            original_sha256=original_sha256,
            maximum_diagnostics=maximum_diagnostics,
            normalize_diagnostic_classpath=True)

    require(before["source_java_file_count"] ==
            after["source_java_file_count"] ==
            rewrite["source_java_file_count"] and
            before["source_zip_sha256"] == source_sha256 and
            after["source_zip_sha256"] == after_sha256,
            "R140_PRE_POST_SOURCE_COVERAGE_DRIFTED")
    for field in ("original_client_sha256", "javac_release",
                  "private_diagnostic_classpath_sha256",
                  "provisional_non_rs_classpath_classfiles",
                  "original_rs_classfiles_excluded",
                  "non_rs_game_bound_classfiles_excluded"):
        require(before[field] == after[field],
                "R140_COMPILER_AUTHORITY_OR_CLASSPATH_CHANGED_" + field)
    require(before["diagnostic_classpath_collision_normalized"] and
            after["diagnostic_classpath_collision_normalized"] and
            not before["original_rs_classes_directly_on_classpath"] and
            not after["original_rs_classes_directly_on_classpath"] and
            not before["complete_original_client_source_build_accepted"] and
            not after["complete_original_client_source_build_accepted"] and
            not before["non_rs_original_binary_capsule_certified_third_party"] and
            not after["non_rs_original_binary_capsule_certified_third_party"],
            "R140_DIAGNOSTIC_NOT_CERTIFYING_OR_RS_BINARY_LEAK")

    pre_count = before["observed_error_diagnostic_count"]
    post_count = after["observed_error_diagnostic_count"]
    diff = post_count - pre_count
    truncated = (before["diagnostics_may_be_truncated"] or
                 after["diagnostics_may_be_truncated"])
    classification = ("truncated_uninterpretable" if truncated
                      else "decrease" if diff < 0
                      else "increase" if diff > 0
                      else "unchanged")
    result = {
        "schema_version": 1,
        "kind": "private_v309_noncertifying_r138_r139_javac_delta_r140",
        "source_archive_sha256": source_sha256,
        "original_client_sha256": original_sha256,
        "original_jar_executed": False,
        "private_client_runtime_executed": False,
        "input_source_java_file_count": rewrite["source_java_file_count"],
        "r139_edited_source_java_file_count":
            rewrite["changed_java_file_count"],
        "r139_ast_verified_explicit_import_edits":
            rewrite["ast_verified_explicit_import_edits"],
        "r139_deferred_source_java_file_count":
            rewrite["whole_java_files_withheld_for_unresolved_imports"],
        "r139_deferred_unsafe_import_count":
            rewrite["withheld_unsafe_import_count"],
        "source_manifest_before_sha256":
            rewrite["source_manifest_before_sha256"],
        "source_manifest_after_sha256":
            rewrite["source_manifest_after_sha256"],
        "private_r125_mapping_sha256":
            rewrite["private_r125_provisional_mapping_sha256"],
        "private_r138_normalized_diagnostic_classpath_sha256":
            before["private_diagnostic_classpath_sha256"],
        "original_rs_classfiles_excluded":
            before["original_rs_classfiles_excluded"],
        "game_linked_nonrs_original_classfiles_excluded":
            before["non_rs_game_bound_classfiles_excluded"],
        "provisional_nonrs_binary_classfile_count":
            before["provisional_non_rs_classpath_classfiles"],
        "javac_release": before["javac_release"],
        "baseline_compiler_exit_code": before["compiler_exit_code"],
        "overlay_compiler_exit_code": after["compiler_exit_code"],
        "baseline_observed_errors": pre_count,
        "overlay_observed_errors": post_count,
        "overlay_minus_baseline_observed_errors": diff,
        "observed_error_classification": classification,
        "diagnostics_may_be_truncated": bool(truncated),
        "baseline_error_categories": _categories(before),
        "overlay_error_categories": _categories(after),
        "both_passes_used_same_normalized_classpath": True,
        "original_game_class_binary_fallback_accepted": False,
        "remaining_original_nonrs_binary_dependency_certified": False,
        "compiler_success_proves_original_client_source_identity": False,
        "complete_original_client_source_build_accepted": False,
        "canonical_recovered_source_tree_published": False,
    }
    require(sha_file(source_zip) == source_sha256 and
            sha_file(original_jar) == original_sha256,
            "R140_PRIVATE_INPUT_CHANGED_DURING_REPLAY")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_original_derived_client_source_zip")
    p.add_argument("private_exact_original_v309_jar")
    p.add_argument("fresh_private_report_json")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    p.add_argument("--maximum-diagnostics", type=int, default=3000)
    opts = p.parse_args(argv)
    output = Path(opts.fresh_private_report_json)
    try:
        require(not output.exists() and not output.is_symlink() and
                output.parent.is_dir() and not output.parent.is_symlink(),
                "R140_PRIVATE_REPORT_MUST_BE_FRESH")
        result = compare_private_original_source_javac(
            opts.private_original_derived_client_source_zip,
            opts.private_exact_original_v309_jar,
            source_sha256=opts.source_sha256,
            original_sha256=opts.original_sha256,
            maximum_diagnostics=opts.maximum_diagnostics)
        output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        print("R140_PRIVATE_JAVAC_DELTA_RECORDED_NONCERTIFYING")
        print("private_report_sha256=" + sha_file(output))
    except Exception:
        p.error("R140_PRIVATE_COMPILE_DELTA_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
