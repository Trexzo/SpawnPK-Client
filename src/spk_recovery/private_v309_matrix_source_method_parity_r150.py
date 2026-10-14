"""R150: recompile separately recovered v309 matrix Java methods without binary fallback.

The original non-rs matrix owner depends on rs/ game classes, so its
.class CANNOT be accepted as an independent dependency. Supply ONE privately
reconstructed Java class, an explicit exact method allowlist and SHA pins.
Compile using JDK --release 9 with empty classpath and sourcepath, then
compare only selected source methods with original, resolved JVM Code.

Other source methods/temporary compilation scaffolds are NEVER accepted as
original. Matching instructions is NOT full Code metadata/source equivalence.
Neither the original JVM game classfile nor its runtime is ever executed.
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
from zipfile import ZipFile

from .bytecode_profile import BytecodeProfileError, profile_class_field_accesses
from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import source_members, sha_file
from .private_v309_dependency_closure_r136 import audit_pinned_original_jar
from .source_method_parity import MethodParityError, _normalized_instructions


class PrivateMatrixMethodSourceR150Error(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise PrivateMatrixMethodSourceR150Error(reason)


def _method_list(raw, *, allow_constructor_methods=False):
    require(type(raw) is list and 1 <= len(raw) <= 32,
            "R150_EXPECT_EXPLICIT_BOUNDED_METHOD_SELECTION")
    results = []
    for entry in raw:
        require(type(entry) is dict and set(entry) == {"name", "descriptor"}
                and type(entry["name"]) is str
                and re.fullmatch(r"(?:[A-Za-z_$][A-Za-z0-9_$]*|<init>)",
                                 entry["name"]) is not None
                and type(entry["descriptor"]) is str
                and re.fullmatch(r"\([a-zA-Z0-9;_$/\[]*\)[A-Za-z0-9;_$/\[]+",
                                 entry["descriptor"]) is not None,
                "R150_INVALID_METHOD_IDENTITY")
        # Constructors require an explicit opt-in. Unselected constructors,
        # source-only scaffolds and class initializers are NEVER accepted.
        require(entry["name"] != "<clinit>" and
                (entry["name"] != "<init>" or allow_constructor_methods),
                "R151_CONSTRUCTOR_NOT_EXPLICITLY_AUTHORIZED")
        results.append((entry["name"], entry["descriptor"]))
    require(len(results) == len(set(results)),
            "R150_DUPLICATE_PRIVATE_SELECTED_METHOD")
    return results


def _strict_inspections(original, rebuilt, *, selected):
    def lookup(profile, method):
        found = [m for m in profile["methods"]
                 if (m.get("name"), m.get("descriptor")) == method]
        require(len(found) == 1 and found[0]["code_length"] is not None,
                "R150_SELECTED_METHOD_ABSENT_OR_NO_CODE")
        return found[0]

    original_methods = []
    frame_differences = 0
    code_differences = 0
    for identifier in selected:
        old = lookup(original, identifier)
        new = lookup(rebuilt, identifier)
        try:
            old_ops = _normalized_instructions(original, old)
            new_ops = _normalized_instructions(rebuilt, new)
        except (MethodParityError, ValueError, KeyError) as exc:
            raise PrivateMatrixMethodSourceR150Error(
                "R150_JVM_BYTECODE_NOT_FULLY_DECODABLE") from exc
        # All CP references are resolved by source_method_parity. CP
        # slot numbers alone are permitted to differ between builds.
        core = (
            old["access"] == new["access"] and
            old["code_length"] == new["code_length"] and
            old["max_stack"] == new["max_stack"] and
            old["max_locals"] == new["max_locals"] and
            old_ops == new_ops and
            old["exception_handlers"] == new["exception_handlers"]
        )
        if not core:
            code_differences += 1
        stackmaps = (
            old["stackmap_table_present"] ==
            new["stackmap_table_present"] and
            old["stackmap_frames"] == new["stackmap_frames"]
        )
        if not stackmaps:
            frame_differences += 1
        original_methods.append({
            # Sensitive names deliberately excluded from public report.
            "private_method_id": identifier,
            "original_opcode_count": len(old_ops),
            "rebuilt_opcode_count": len(new_ops),
            "exact_core_instructions_limits_and_handlers": core,
            "exact_stackmap_representation": stackmaps,
        })
    require(code_differences == 0,
            "R150_SELECTED_JAVA_SOURCE_METHOD_CODE_DIFFERS_FROM_ORIGINAL")
    return {
        "verified_selected_method_count": len(original_methods),
        "verified_constructor_count": sum(
            method[0] == "<init>" for method in selected),
        "matched_opcode_count": sum(x["original_opcode_count"]
                                   for x in original_methods),
        "core_method_bytecode_differences": code_differences,
        "strict_stackmap_representation_mismatches": frame_differences,
        "all_selected_core_method_code_equal": True,
        "all_selected_stackmap_representations_equal":
            frame_differences == 0,
        "private_methods": original_methods,
    }


def verify_private_matrix_source_subset(
        original_jar, recovered_java_zip, method_selection_json, *,
        original_sha256=CANONICAL_V309,
        recovered_source_sha256, selection_sha256,
        original_owner="com/a/b/a/b",
        allow_constructor_methods=False):
    pins = (
        (original_jar, original_sha256),
        (recovered_java_zip, recovered_source_sha256),
        (method_selection_json, selection_sha256),
    )
    require(all(sha_file(p) == digest for p, digest in pins),
            "R150_PRIVATE_ORIGINAL_OR_DONOR_SHA_MISMATCH")
    require(type(original_owner) is str and
            re.fullmatch(r"[a-zA-Z_$][a-zA-Z0-9_$]*(?:/[a-zA-Z_$][a-zA-Z0-9_$]*)+",
                         original_owner) is not None,
            "R150_UNSAFE_BINARY_OWNER_NAME")
    config_bytes = Path(method_selection_json).read_bytes()
    require(len(config_bytes) <= 100_000,
            "R150_PRIVATE_SELECTION_TOO_LARGE")
    try:
        selected = _method_list(
            json.loads(config_bytes),
            allow_constructor_methods=allow_constructor_methods)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PrivateMatrixMethodSourceR150Error(
            "R150_INVALID_PRIVATE_METHOD_SELECTION") from exc

    graph = audit_pinned_original_jar(
        original_jar, original_sha256=original_sha256,
        include_private_names=True)
    linked = set(graph["private_dependency_partition"][
        "direct_rs_dependent_non_rs"])
    require(original_owner in linked,
            "R150_ORIGINAL_OWNER_NOT_PROVEN_GAME_LINKED_EXCLUSION")
    with ZipFile(original_jar, "r") as jar:
        path = original_owner + ".class"
        require(jar.namelist().count(path) == 1,
                "R150_ORIGINAL_OWNER_MISSING_OR_DUPLICATE")
        original_binary = jar.read(path)
    source = source_members(recovered_java_zip, recovered_source_sha256)
    require(len(source) == 1 and source[0][0] == original_owner + ".java",
            "R150_ONE_EXACT_JAVA_SOURCE_OWNER_REQUIRED")
    source_bytes = source[0][1]
    require(type(source_bytes) is bytes and len(source_bytes) <= 2_000_000,
            "R150_UNBOUNDED_JAVA_SOURCE")
    # Only JDK parsing/compilation, annotation processing disabled; no
    # original binary on classpath and no project fallback sourcepath.
    javac = shutil.which("javac")
    require(javac is not None, "R150_TRUSTED_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r150-private-matrix-") as tmp:
        root = Path(tmp)
        owner_source = root / "src" / (original_owner + ".java")
        owner_source.parent.mkdir(parents=True, exist_ok=True)
        owner_source.write_bytes(source_bytes)
        classes = root / "classes"
        empty = root / "empty"
        classes.mkdir()
        empty.mkdir()
        env = os.environ.copy()
        for key in ("CLASSPATH", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS",
                    "_JAVA_OPTIONS"):
            env.pop(key, None)
        try:
            built = subprocess.run(
                [javac, "--release", "9", "-proc:none", "-implicit:none",
                 "-g:none", "-classpath", str(empty),
                 "-sourcepath", str(empty),
                 "-d", str(classes), str(owner_source)],
                cwd=root, env=env, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=90, check=False)
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise PrivateMatrixMethodSourceR150Error(
                "R150_PRIVATE_JAVA_SOURCE_COMPILE_UNAVAILABLE") from exc
        require(built.returncode == 0,
                "R150_PRIVATE_PARTIAL_JAVA_SOURCE_NOT_INDEPENDENTLY_COMPILABLE")
        candidate = classes / (original_owner + ".class")
        require(candidate.is_file() and not candidate.is_symlink(),
                "R150_PRIVATE_JAVA_COMPILER_WRONG_OUTPUT")
        rebuilt_binary = candidate.read_bytes()
        require(0 < len(rebuilt_binary) <= 2_000_000,
                "R150_PRIVATE_REBUILT_CLASS_UNBOUNDED")
        require(len(list(classes.rglob("*.class"))) == 1,
                "R150_UNEXPECTED_ADDITIONAL_COMPILED_JAVA_CLASSES")

    parsed = parse_class(original_binary)
    require(parsed.name == original_owner,
            "R150_ORIGINAL_CLASSFILE_OWNER_MISMATCH")
    try:
        original_profile = profile_class_field_accesses(original_binary)
        rebuilt_profile = profile_class_field_accesses(rebuilt_binary)
    except (BytecodeProfileError, KeyError, ValueError) as exc:
        raise PrivateMatrixMethodSourceR150Error(
            "R150_ORIGINAL_OR_REBUILT_CLASS_NOT_PARSEABLE") from exc
    require(original_profile["internal_name"] ==
            rebuilt_profile["internal_name"] == original_owner,
            "R150_ORIGINAL_AND_REBUILT_OWNER_NOT_EQUAL")
    checks = _strict_inspections(
        original_profile, rebuilt_profile, selected=selected)
    private = checks.pop("private_methods")
    report = {
        "schema_version": 1,
        "kind": "private_v309_linked_matrix_independent_java_method_rebuild_r150",
        "original_client_sha256": original_sha256,
        "private_recovered_matrix_source_zip_sha256": recovered_source_sha256,
        "private_method_selection_sha256": selection_sha256,
        "original_matrix_owner_class_sha256":
            hashlib.sha256(original_binary).hexdigest(),
        "isolated_recompiled_partial_class_sha256":
            hashlib.sha256(rebuilt_binary).hexdigest(),
        **checks,
        "verified_methods_cover_full_original_matrix_class": False,
        "constructor_selection_requires_explicit_opt_in": True,
        "unselected_constructors_or_initializers_recovered": False,
        "unselected_private_methods_and_scaffolding_accepted": False,
        "original_game_class_binary_fallback_used": False,
        "source_compiled_with_empty_original_external_classpath": True,
        "original_client_or_recovered_matrix_class_executed": False,
        "complete_original_member_semantics_accepted": False,
        "complete_original_matrix_java_source_restored": False,
        "whole_v309_java_client_compilation_accepted": False,
        "derived_original_source_publication_authorized": False,
        "private_selected_method_manifest_sha256":
            hashlib.sha256(json.dumps(
                private, sort_keys=True,
                separators=(",", ":")).encode("utf-8")).hexdigest(),
    }
    require(all(sha_file(p) == digest for p, digest in pins),
            "R150_INPUT_HASH_CHANGED_DURING_REBUILD")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_original_client_v309_jar")
    p.add_argument("private_one_class_recovered_java_zip")
    p.add_argument("private_exact_method_selection_json")
    p.add_argument("fresh_private_sanitized_report_json")
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--selection-sha256", required=True)
    p.add_argument("--original-owner", default="com/a/b/a/b")
    p.add_argument("--allow-constructor-methods", action="store_true")
    args = p.parse_args(argv)
    output = Path(args.fresh_private_sanitized_report_json)
    try:
        require(not output.exists() and not output.is_symlink()
                and output.parent.is_dir()
                and not output.parent.is_symlink(),
                "R150_PRIVATE_SANITIZED_REPORT_MUST_BE_FRESH")
        results = verify_private_matrix_source_subset(
            args.private_original_client_v309_jar,
            args.private_one_class_recovered_java_zip,
            args.private_exact_method_selection_json,
            original_sha256=args.original_sha256,
            recovered_source_sha256=args.source_sha256,
            selection_sha256=args.selection_sha256,
            original_owner=args.original_owner,
            allow_constructor_methods=args.allow_constructor_methods)
        output.write_text(json.dumps(
            results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("R150_PRIVATE_ORIGINAL_LINKED_MATRIX_JAVA_METHODS_RECOMPILED")
        print("sanitized_report_sha256=" + sha_file(output))
    except Exception:
        p.error("R150_ORIGINAL_MATRIX_METHOD_SOURCE_REBUILD_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
