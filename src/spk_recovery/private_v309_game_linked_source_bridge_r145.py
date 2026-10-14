"""R145: original-game-linked non-rs Java source bridge, private compiler-only.

R136 excludes original non-rs classfiles that reference the original rs/
game namespace. They cannot silently return as a binary compile fallback.
R145 lets a privately recovered Java-source candidate for such an owner
join the full candidate Java tree *as Java source*, measures the javac delta
against the SAME R138-normalized classpath, and explicitly does NOT confer
semantic or original-bytecode parity, licensing, or release acceptance.

No original binary, donor source, source path, original JVM identifiers,
compiler stderr, or derivative classfile is written to public output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import (
    _java_ast_declarations, source_members, sha_file,
)
from .private_v309_dependency_closure_r136 import audit_pinned_original_jar
from .private_v309_compiler_frontier_r137 import private_source_compile_frontier


class PrivateClientSourceBridgeR145Error(ValueError):
    pass


def require(value, message):
    if not value:
        raise PrivateClientSourceBridgeR145Error(message)


def _manifest(entries):
    output = hashlib.sha256()
    for rel, content in entries:
        output.update(rel.encode("utf-8") + b"\0")
        output.update(hashlib.sha256(content).digest())
    return output.hexdigest()


def _write_private_java_zip(entries, dest):
    require(not dest.exists(), "BRIDGE_PRIVATE_STAGE_NOT_FRESH")
    paths = [rel for rel, _ in entries]
    require(len(paths) == len(set(paths)) ==
            len(set(rel.casefold() for rel in paths)),
            "BRIDGE_DUPLICATE_JAVA_SOURCE_PATH")
    with ZipFile(dest, "w", compression=ZIP_DEFLATED) as archive:
        for rel, source in entries:
            require(rel.endswith(".java") and not rel.startswith("/") and
                    "\\" not in rel and all(x not in ("", ".", "..")
                    for x in rel.split("/")) and type(source) is bytes,
                    "BRIDGE_INVALID_SOURCE_MEMBER")
            entry = ZipInfo("src/main/java/" + rel, (1980, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            archive.writestr(entry, source)
    return sha_file(dest)


def compare_private_linked_owner_source(source_zip, original_jar,
                                        private_donor_java_zip, *,
                                        source_sha256, donor_sha256,
                                        original_sha256=CANONICAL_V309,
                                        maximum_diagnostics=3000):
    """Exactly one owned original linked class, supplied as REAL Java source."""
    require(all(sha_file(path) == digest for path, digest in (
        (source_zip, source_sha256),
        (original_jar, original_sha256),
        (private_donor_java_zip, donor_sha256))),
        "R145_ORIGINAL_SOURCE_OR_DONOR_SHA256_MISMATCH")
    require(type(maximum_diagnostics) is int
            and 100 <= maximum_diagnostics <= 3000,
            "R145_COMPILER_DIAGNOSTIC_BOUND_INVALID")

    existing = source_members(source_zip, source_sha256)
    donated = source_members(private_donor_java_zip, donor_sha256)
    require(len(donated) == 1, "R145_ONE_SOURCE_OWNER_PER_PROOF_REQUIRED")
    original_graph = audit_pinned_original_jar(
        original_jar, original_sha256=original_sha256,
        include_private_names=True)
    original_linked = set(original_graph["private_dependency_partition"][
        "direct_rs_dependent_non_rs"])
    transitive_linked = set(original_graph["private_dependency_partition"][
        "transitively_rs_dependent_non_rs"])
    provisional = set(original_graph["private_dependency_partition"][
        "provisional_non_rs_untainted"])
    require(original_linked and not ((original_linked | transitive_linked) &
                                     provisional),
            "R145_ORIGINAL_BINARY_PARTITION_OVERLAP")

    rel, body = donated[0]
    original_owner = rel[:-5].replace("/", "/")
    require(original_owner in original_linked
            and not original_owner.startswith("rs/")
            and "$" not in original_owner,
            "R145_DONOR_NOT_A_DIRECT_ORIGINAL_RS_LINKED_OWNER")
    require(rel.casefold() not in {path.casefold() for path, _ in existing},
            "R145_OWNER_ALREADY_DEFINED_BY_JAVA_SOURCE")

    with tempfile.TemporaryDirectory(prefix="spk-r145-private-") as scratch:
        temp = Path(scratch)
        # Parse with trusted JDK AST, never execute recovered donor.
        declarations = _java_ast_declarations(donated, temp)
        require(declarations == [(rel, original_owner)],
                "R145_JAVA_DONOR_DECLARES_WRONG_OR_ADDITIONAL_CLASS")
        combined = sorted(existing + donated)
        require(len(combined) == len(existing) + 1,
                "R145_GAME_LINKED_SOURCE_NOT_ADDED_ONCE")
        archive = temp / "private-game-linked-source-preview.zip"
        new_sha = _write_private_java_zip(combined, archive)
        before = private_source_compile_frontier(
            source_zip, original_jar, source_sha256=source_sha256,
            original_sha256=original_sha256,
            maximum_diagnostics=maximum_diagnostics,
            normalize_diagnostic_classpath=True)
        after = private_source_compile_frontier(
            archive, original_jar, source_sha256=new_sha,
            original_sha256=original_sha256,
            maximum_diagnostics=maximum_diagnostics,
            normalize_diagnostic_classpath=True)

    require(before["source_java_file_count"] == len(existing)
            and after["source_java_file_count"] == len(existing)+1
            and before["original_client_sha256"] ==
            after["original_client_sha256"] == original_sha256
            and before["private_diagnostic_classpath_sha256"] ==
            after["private_diagnostic_classpath_sha256"]
            and before["provisional_non_rs_classpath_classfiles"] ==
            after["provisional_non_rs_classpath_classfiles"] ==
            len(provisional)
            and before["non_rs_game_bound_classfiles_excluded"] ==
            after["non_rs_game_bound_classfiles_excluded"] ==
            len(original_linked | transitive_linked)
            and before["original_rs_classfiles_excluded"] ==
            after["original_rs_classfiles_excluded"]
            and before["javac_release"] == after["javac_release"] == 11,
            "R145_DIAGNOSTIC_CLASSPATH_OR_SOURCE_AUTHORITY_DRIFTED")
    for report in (before, after):
        require(report["diagnostic_classpath_collision_normalized"] is True
                and report["original_rs_classes_directly_on_classpath"] is False
                and report["non_rs_original_binary_capsule_certified_third_party"] is False
                and report["complete_original_client_source_build_accepted"] is False,
                "R145_SOURCE_BRIDGE_BYPASSED_ORIGINAL_BINARY_GUARDS")

    before_count = before["observed_error_diagnostic_count"]
    after_count = after["observed_error_diagnostic_count"]
    truncated = (before["diagnostics_may_be_truncated"] or
                 after["diagnostics_may_be_truncated"])
    label = ("uninterpretable_diagnostics_truncated" if truncated
             else "improved" if after_count < before_count
             else "regressed" if after_count > before_count
             else "unchanged")
    result = {
        "schema_version": 1,
        "kind": "private_v309_original_linked_source_bridge_r145",
        "original_client_sha256": original_sha256,
        "original_source_zip_sha256": source_sha256,
        "private_java_donor_zip_sha256": donor_sha256,
        "private_source_preview_zip_sha256": new_sha,
        "original_source_manifest_sha256": _manifest(existing),
        "combined_source_manifest_sha256": _manifest(combined),
        "original_client_source_java_count": len(existing),
        "private_source_bridge_added_java_count": 1,
        "combined_private_java_file_count": len(combined),
        "original_rs_classfiles_excluded":
            before["original_rs_classfiles_excluded"],
        "original_rs_linked_nonrs_classfiles_excluded":
            before["non_rs_game_bound_classfiles_excluded"],
        "provisional_nonrs_binary_count":
            before["provisional_non_rs_classpath_classfiles"],
        "diagnostic_original_derived_capsule_sha256":
            before["private_diagnostic_classpath_sha256"],
        "original_source_observed_errors": before_count,
        "donor_source_observed_errors": after_count,
        "observed_error_delta": after_count - before_count,
        "observed_error_delta_classification": label,
        "diagnostics_may_be_truncated": bool(truncated),
        "baseline_compiler_stderr_sha256":
            before["private_full_stderr_sha256"],
        "donor_compiler_stderr_sha256":
            after["private_full_stderr_sha256"],
        "donor_source_parsed_only_not_executed": True,
        "original_client_binary_executed": False,
        "original_game_binary_fallback_accepted": False,
        "source_to_original_class_abi_verified": False,
        "original_method_bytecode_equivalence_verified": False,
        "original_method_semantics_verified": False,
        "independently_licensed_nonrs_dependencies_proven": False,
        "whole_client_source_compilation_accepted": False,
        "recovered_source_release_authorized": False,
    }
    require(all(sha_file(path) == digest for path, digest in (
        (source_zip, source_sha256),
        (original_jar, original_sha256),
        (private_donor_java_zip, donor_sha256))),
        "R145_ORIGINAL_INPUT_CHANGED_DURING_COMPILATION")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_client_source_zip")
    parser.add_argument("exact_original_v309_jar")
    parser.add_argument("private_recovered_one_class_java_zip")
    parser.add_argument("fresh_private_sanitized_report")
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--donor-sha256", required=True)
    parser.add_argument("--original-sha256", default=CANONICAL_V309)
    parser.add_argument("--maximum-diagnostics", type=int, default=3000)
    args = parser.parse_args(argv)
    dest = Path(args.fresh_private_sanitized_report)
    try:
        require(not dest.exists() and not dest.is_symlink()
                and dest.parent.is_dir() and not dest.parent.is_symlink(),
                "R145_PRIVATE_REPORT_MUST_BE_FRESH")
        result = compare_private_linked_owner_source(
            args.private_client_source_zip, args.exact_original_v309_jar,
            args.private_recovered_one_class_java_zip,
            source_sha256=args.source_sha256,
            donor_sha256=args.donor_sha256,
            original_sha256=args.original_sha256,
            maximum_diagnostics=args.maximum_diagnostics)
        dest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        print("R145_PRIVATE_ORIGINAL_LINKED_SOURCE_BRIDGE_MEASURED_NOT_CERTIFIED")
        print("private_report_sha256=" + sha_file(dest))
    except Exception:
        parser.error("R145_ORIGINAL_GAME_LINKED_SOURCE_BRIDGE_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
