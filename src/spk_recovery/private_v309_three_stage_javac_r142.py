"""R142: measure the *real private* v309 Java source frontier in three stages.

Stage 0: original decompiled Java source with R138 normalized, provisional
non-rs original-derived diagnostic dependencies.
Stage 1: R139 Java-AST package import overlay.
Stage 2: R141 Java-AST original class-casefold import + type overlay.

All source/JAR inputs must be SHA-pinned. Original game rs/ classfiles are
excluded from the provisional compiler classpath. The surviving original-
derived non-rs capsule is NOT accepted or licensed third-party source.
No client or original binary is executed. No private source is published.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file
from .private_v309_import_overlay_r139 import private_import_overlay
from .private_v309_casefold_type_rewrite_r141 import patch_private_casefold_source
from .private_v309_compiler_frontier_r137 import private_source_compile_frontier


class PrivateCombinedJavacR142Error(ValueError):
    pass


def check(ok, reason):
    if not ok:
        raise PrivateCombinedJavacR142Error(reason)


def _temp_java_zip(entries, target):
    check(not target.exists(), "R142_PRIVATE_TEMP_OUTPUT_MUST_BE_NEW")
    paths = [p for p, _ in entries]
    check(len(paths) == len(set(paths)) == len(set(p.casefold() for p in paths)),
          "R142_DUPLICATE_OR_WINDOWS_COLLIDING_SOURCE")
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        for path, data in entries:
            check(path.endswith(".java") and not path.startswith("/") and
                  "\\" not in path and all(seg not in ("", ".", "..")
                  for seg in path.split("/")), "R142_UNSAFE_SOURCE_PATH")
            name = ZipInfo("src/main/java/" + path, (1980, 1, 1, 0, 0, 0))
            name.compress_type = ZIP_DEFLATED
            archive.writestr(name, data)
    return sha_file(target)


def _frontier(zip_path, original, source_sha, original_sha, error_limit):
    return private_source_compile_frontier(
        zip_path, original, source_sha256=source_sha,
        original_sha256=original_sha, maximum_diagnostics=error_limit,
        normalize_diagnostic_classpath=True)


def _summarize(report):
    keys = ("unresolved_symbol_errors", "missing_package_errors",
            "other_compiler_errors")
    categories = report["error_categories"]
    return {
        "compiler_exit_code": report["compiler_exit_code"],
        "observed_errors": report["observed_error_diagnostic_count"],
        "diagnostics_may_be_truncated": report["diagnostics_may_be_truncated"],
        "error_categories": {key: categories[key] for key in keys},
        "private_full_stderr_sha256": report["private_full_stderr_sha256"],
    }


def compare_private_three_stage_source(source_zip, original_jar, *,
                                       source_sha256,
                                       original_sha256=CANONICAL_V309,
                                       maximum_diagnostics=3000):
    check(sha_file(source_zip) == source_sha256 and
          sha_file(original_jar) == original_sha256,
          "R142_INPUT_HASH_MISMATCH")
    check(type(maximum_diagnostics) is int and
          100 <= maximum_diagnostics <= 3000,
          "R142_COMPILER_ERROR_BOUND_INVALID")

    import_java, import_evidence = private_import_overlay(
        source_zip, original_jar, source_sha256=source_sha256,
        original_sha256=original_sha256)

    with tempfile.TemporaryDirectory(prefix="spk-r142-private-") as temp:
        root = Path(temp)
        imports_zip = root / "PRIVATE_R139_SOURCE.zip"
        type_zip = root / "PRIVATE_R141_SOURCE.zip"
        imports_sha = _temp_java_zip(import_java, imports_zip)
        type_java, type_evidence = patch_private_casefold_source(
            imports_zip, original_jar, source_sha256=imports_sha,
            original_sha256=original_sha256)
        type_sha = _temp_java_zip(type_java, type_zip)

        check(import_evidence["source_java_file_count"] ==
              type_evidence["source_java_file_count"] ==
              len(import_java) == len(type_java),
              "R142_CLIENT_SOURCE_COVERAGE_CHANGED")
        check(type_evidence["source_archive_sha256"] == imports_sha and
              import_evidence["source_archive_sha256"] == source_sha256 and
              import_evidence["private_r125_provisional_mapping_sha256"] ==
              type_evidence["private_r125_mapping_sha256"],
              "R142_R125_R136_AUTHORITIES_NOT_IDENTICAL")
        check(type_evidence["source_manifest_before_sha256"] ==
              import_evidence["source_manifest_after_sha256"],
              "R142_R139_TO_R141_JAVA_MANIFEST_CHANGED")

        original = _frontier(source_zip, original_jar,
                            source_sha256, original_sha256,
                            maximum_diagnostics)
        imports = _frontier(imports_zip, original_jar,
                           imports_sha, original_sha256,
                           maximum_diagnostics)
        types = _frontier(type_zip, original_jar,
                         type_sha, original_sha256,
                         maximum_diagnostics)

    authorities = (
        "original_client_sha256", "javac_release",
        "private_diagnostic_classpath_sha256",
        "provisional_non_rs_classpath_classfiles",
        "original_rs_classfiles_excluded",
        "non_rs_game_bound_classfiles_excluded",
        "source_java_file_count",
    )
    for key in authorities:
        check(original[key] == imports[key] == types[key],
              "R142_COMPILE_AUTHORITY_DRIFT_" + key)
    for row in (original, imports, types):
        check(row["diagnostic_classpath_collision_normalized"] is True and
              row["original_rs_classes_directly_on_classpath"] is False and
              row["complete_original_client_source_build_accepted"] is False and
              row["non_rs_original_binary_capsule_certified_third_party"] is False,
              "R142_FALSE_DEPENDENCY_OR_COMPILE_CERTIFICATION")
    truncated = any(row["diagnostics_may_be_truncated"]
                    for row in (original, imports, types))
    before = original["observed_error_diagnostic_count"]
    middle = imports["observed_error_diagnostic_count"]
    after = types["observed_error_diagnostic_count"]
    def label(change):
        return ("uninterpretable_truncated" if truncated else
                "improved" if change < 0 else
                "regressed" if change > 0 else "unchanged")
    result = {
        "schema_version": 1,
        "kind": "v309_private_combined_r138_r139_r141_source_javac_r142",
        "original_client_sha256": original_sha256,
        "original_decompiled_source_archive_sha256": source_sha256,
        "private_r139_java_zip_sha256": imports_sha,
        "private_r141_java_zip_sha256": type_sha,
        "source_java_file_count": original["source_java_file_count"],
        "r139_package_imports_rewritten":
            import_evidence["ast_verified_explicit_import_edits"],
        "r139_changed_java_files":
            import_evidence["changed_java_file_count"],
        "r141_class_imports_rewritten":
            type_evidence["reviewed_rewritten_import_count"],
        "r141_java_type_identifiers_rewritten":
            type_evidence["reviewed_rewritten_type_identifier_count"],
        "r141_changed_java_files":
            type_evidence["changed_java_source_file_count"],
        "r141_ambiguous_java_files_withheld":
            type_evidence["withheld_ambiguous_java_file_count"],
        "source_manifest_original":
            import_evidence["source_manifest_before_sha256"],
        "source_manifest_after_r139":
            import_evidence["source_manifest_after_sha256"],
        "source_manifest_after_r141":
            type_evidence["source_manifest_after_sha256"],
        "private_r125_source_to_diagnostic_namespace_mapping_sha256":
            type_evidence["private_r125_mapping_sha256"],
        "private_original_derived_normalized_nonrs_capsule_sha256":
            original["private_diagnostic_classpath_sha256"],
        "original_rs_classfiles_excluded":
            original["original_rs_classfiles_excluded"],
        "original_linked_nonrs_binary_classfiles_excluded":
            original["non_rs_game_bound_classfiles_excluded"],
        "stages": {
            "unmodified_source": _summarize(original),
            "after_r139_imports": _summarize(imports),
            "after_r141_type_aliases": _summarize(types),
        },
        "delta_r139_minus_original": middle - before,
        "delta_r141_minus_r139": after - middle,
        "delta_final_minus_original": after - before,
        "overall_delta_classification": label(after - before),
        "stage_deltas_interpretable": not truncated,
        "all_stages_same_normalized_classpath_sha256": True,
        "original_client_executed": False,
        "candidate_client_executed": False,
        "original_game_rs_binary_fallback_accepted": False,
        "original_nonrs_capsule_proven_external_third_party": False,
        "complete_original_client_source_build_accepted": False,
        "accepted_original_semantic_class_or_member_lineage": False,
        "whole_client_runtime_equivalence_verified": False,
        "public_recovered_source_release_authorized": False,
    }
    check(sha_file(source_zip) == source_sha256 and
          sha_file(original_jar) == original_sha256,
          "R142_INPUT_HASH_CHANGED_DURING_DIAGNOSTIC")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_original_decompiled_java_zip")
    parser.add_argument("private_original_v309_jar")
    parser.add_argument("fresh_private_sanitized_report_json")
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--original-sha256", default=CANONICAL_V309)
    parser.add_argument("--maximum-diagnostics", type=int, default=3000)
    args = parser.parse_args(argv)
    dest = Path(args.fresh_private_sanitized_report_json)
    try:
        check(not dest.exists() and not dest.is_symlink()
              and dest.parent.is_dir() and not dest.parent.is_symlink(),
              "R142_PRIVATE_REPORT_MUST_BE_FRESH")
        result = compare_private_three_stage_source(
            args.private_original_decompiled_java_zip,
            args.private_original_v309_jar,
            source_sha256=args.source_sha256,
            original_sha256=args.original_sha256,
            maximum_diagnostics=args.maximum_diagnostics)
        dest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        print("R142_PRIVATE_CLIENT_SOURCE_JAVAC_DELTA_RECORDED_NONCERTIFYING")
        print("private_report_sha256=" + sha_file(dest))
    except Exception:
        parser.error("R142_PRIVATE_V309_SOURCE_REPLAY_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
