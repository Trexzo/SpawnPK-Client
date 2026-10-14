"""R153: original v309 matrix Packet-loader SOURCE-ONLY Java instruction proof.

One original game-linked class and THREE signature-only Java support classes
are supplied as exact private SHA-pinned source archives. No original rs/
binary classfiles, third-party libraries or client runtime enter javac.
Only two explicit selected methods (one constructor and one decoder method)
are checked against original resolved JVM Code; the other source methods and
three support-class BODIES are *never* certified original.

This is an isolated compilation witness, not the full 1,271-file source
tree or original full classfile/StackMap equivalence. Keep all archives local.
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

from .bytecode_profile import profile_class_field_accesses, BytecodeProfileError
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import (
    source_members, sha_file, _java_ast_declarations,
)
from .private_v309_dependency_closure_r136 import audit_pinned_original_jar
from .private_v309_matrix_source_method_parity_r150 import (
    _method_list, _strict_inspections, PrivateMatrixMethodSourceR150Error,
)


class PrivateMatrixLoaderR153Error(ValueError):
    pass


def require(value, reason):
    if not value:
        raise PrivateMatrixLoaderR153Error(reason)


def _exact_selection(selection, *, allow_euler_method_bodies=False,
                     allow_transform_projection_method=False,
                     allow_matrix_string_method=False):
    data = Path(selection).read_bytes()
    require(len(data) <= 32768, "R153_SELECTION_NOT_BOUNDED")
    try:
        values = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise PrivateMatrixLoaderR153Error("R153_SELECTION_NOT_JSON") from exc
    selected = _method_list(values, allow_constructor_methods=True)
    expected = (2 + (2 if allow_euler_method_bodies else 0) +
                (1 if allow_transform_projection_method else 0) +
                (1 if allow_matrix_string_method else 0))
    require(len(selected) == expected
            and sum(x[0] == "<init>" for x in selected) == 1,
            "R155_BOUNDED_EXACT_MEMBER_SELECTION_REQUIRED")
    constructor = next(x for x in selected if x[0] == "<init>")
    decoders = [x for x in selected
                if x[0] != "<init>" and x[1] == constructor[1]]
    require(len(decoders) == 1, "R155_UNIQUE_PACKET_DECODER_REQUIRED")
    decoder = decoders[0]
    other = [x for x in selected if x not in (constructor, decoder)]
    eulers = [m for m in other if m[1] == "()[F"]
    strings = [m for m in other
               if m == ("toString", "()Ljava/lang/String;")]
    projections = [m for m in other
                   if m[1] != "()[F" and m not in strings]
    require(len(eulers) == (2 if allow_euler_method_bodies else 0)
            and len(strings) == (1 if allow_matrix_string_method else 0)
            and len(projections) == (1 if allow_transform_projection_method else 0)
            and all(m[0] not in ("<init>", "<clinit>") for m in other)
            and all(re.fullmatch(r"(L[A-Za-z0-9_$/]+;)V", p[1])
                    for p in projections),
            "R156_ONLY_EULER_TRANSFORM_AND_STRING_EXACT_SELECTION")
    require(constructor[1] == decoder[1] and
            re.fullmatch(r"\(L([A-Za-z0-9_$]+/)*[A-Za-z0-9_$]+;Z\)V",
                         constructor[1]) is not None,
            "R153_CONSTRUCTOR_AND_DECODER_BUFFER_SIGNATURES_DIFFER")
    return selected


def _relevant_original_invocations(original_profile, selected):
    methods = {
        (m["name"], m["descriptor"]): m
        for m in original_profile["methods"]
    }
    require(all(x in methods for x in selected),
            "R153_ORIGINAL_SELECTED_MEMBER_MISSING")
    owner = original_profile["internal_name"]
    constructor = next(methods[x] for x in selected if x[0] == "<init>")
    ctor_id = next(x for x in selected if x[0] == "<init>")
    decoder = next(x for x in selected
                   if x[0] != "<init>" and x[1] == ctor_id[1])
    require(any(
        call["owner"] == owner and
        call["name"] == decoder[0] and
        call["descriptor"] == decoder[1]
        for call in constructor["method_invocations"]),
        "R153_CONSTRUCTOR_DOES_NOT_DELEGATE_TO_SELECTED_DECODER")
    referenced = set()
    decoder_method = methods[decoder]
    require(decoder_method["method_invocations"]
            and decoder_method["code_length"] >= 20,
            "R153_ORIGINAL_DECODER_HAS_NO_EXTERNAL_CALLS")
    for identity in selected:
        for call in methods[identity]["method_invocations"]:
            name = call["owner"]
            if (name != owner and
                not name.startswith(("java/", "javax/"))):
                referenced.add(name)
    return referenced


def verify_private_original_matrix_packet_loader(
        original_jar, private_matrix_java_zip,
        private_source_only_support_zip, private_selection_json, *,
        original_sha256=CANONICAL_V309,
        matrix_source_sha256, support_source_sha256, selection_sha256,
        original_owner="com/a/b/a/b",
        allow_euler_method_bodies=False,
        allow_transform_projection_method=False,
        allow_matrix_string_method=False):
    inputs = [
        (original_jar, original_sha256),
        (private_matrix_java_zip, matrix_source_sha256),
        (private_source_only_support_zip, support_source_sha256),
        (private_selection_json, selection_sha256),
    ]
    require(all(sha_file(path) == digest for path, digest in inputs),
            "R153_ANY_INPUT_SHA256_DRIFT")
    require(re.fullmatch(
        r"[A-Za-z_$][A-Za-z0-9_$]*(?:/[A-Za-z_$][A-Za-z0-9_$]*)+",
        original_owner) is not None,
        "R153_INVALID_ORIGINAL_OWNER")
    selected = _exact_selection(
        private_selection_json,
        allow_euler_method_bodies=allow_euler_method_bodies,
        allow_transform_projection_method=allow_transform_projection_method,
        allow_matrix_string_method=allow_matrix_string_method)
    matrix_java = source_members(private_matrix_java_zip, matrix_source_sha256)
    helpers = source_members(private_source_only_support_zip,
                             support_source_sha256)
    require(len(matrix_java) == 1 and
            matrix_java[0][0] == original_owner + ".java",
            "R153_SOURCE_MUST_DECLARE_ONE_ORIGINAL_MATRIX_OWNER")
    require(len(helpers) == 3 and
            len(set(x.casefold() for x, _ in helpers)) == 3 and
            original_owner + ".java" not in {name for name, _ in helpers},
            "R153_THREE_DISTINCT_PRIVATE_SUPPORT_SOURCES_REQUIRED")
    graph = audit_pinned_original_jar(
        original_jar, original_sha256=original_sha256,
        include_private_names=True)
    partition = graph["private_dependency_partition"]
    require(original_owner in
            partition["direct_rs_dependent_non_rs"],
            "R153_ORIGINAL_MATRIX_NOT_PROVEN_GAME_LINKED")

    with ZipFile(original_jar) as jar:
        original_name = original_owner + ".class"
        require(jar.namelist().count(original_name) == 1,
                "R153_ORIGINAL_JVM_OWNER_DUPLICATE")
        original_raw = jar.read(original_name)
        present_original = set(jar.namelist())

    try:
        original_profile = profile_class_field_accesses(original_raw)
    except (BytecodeProfileError, ValueError, KeyError) as exc:
        raise PrivateMatrixLoaderR153Error(
            "R153_ORIGINAL_JVM_BYTECODE_UNREADABLE") from exc
    require(original_profile["internal_name"] == original_owner,
            "R153_ORIGINAL_BINARY_IDENTITY_MISMATCH")
    referenced = _relevant_original_invocations(
        original_profile, selected)
    if allow_euler_method_bodies:
        extras = [m for m in selected if m[1] == "()[F"]
        declared = [
            m for m in original_profile["methods"]
            if m["descriptor"] == "()[F"
        ]
        # The real original matrix has exactly two Euler-output methods,
        # one package-private and one public. The source must reproduce
        # their actual Math-only code without helper invocation fallback.
        require(len(extras) == 2
                and sorted(extras) == sorted(
                    (m["name"], m["descriptor"]) for m in declared)
                and sorted(m["access"] & 0x0007 for m in declared) == [0, 1]
                and all(
                    call["owner"].startswith("java/lang/Math")
                    for method in declared
                    for call in method["method_invocations"]
                ),
                "R154_ORIGINAL_EULER_METHODS_NOT_EXACT_TWO_MATH_ONLY")
    provided_owners = {name[:-5] for name, _ in helpers}
    if allow_matrix_string_method:
        require(allow_euler_method_bodies,
                "R156_MATRIX_STRING_REQUIRES_TWO_PROVEN_EULER_READERS")
        strings = [
            m for m in original_profile["methods"]
            if m["name"] == "toString"
            and m["descriptor"] == "()Ljava/lang/String;"
        ]
        require(len(strings) == 1 and
                (strings[0]["access"] & 0x0007) == 1 and
                strings[0]["code_length"] >= 55,
                "R156_ORIGINAL_PUBLIC_MATRIX_STRING_NOT_FOUND")
        callsites = {
            (call["owner"], call["name"], call["descriptor"])
            for call in strings[0]["method_invocations"]
        }
        require(
            (original_owner, "c", "()[F") in callsites
            and (original_owner, "d", "()[F") in callsites
            and ("java/lang/Math", "sqrt", "(D)D") in callsites
            and any(owner == "java/lang/StringBuilder"
                    for owner, _, _ in callsites),
            "R156_ORIGINAL_MATRIX_STRING_CALLGRAPH_NOT_PROVEN")
    if allow_transform_projection_method:
        projected = [m for m in selected
                     if m[0] != "<init>" and m[1] not in
                     ("()[F", next(x[1] for x in selected
                                  if x[0] == "<init>"))]
        require(len(projected) == 1, "R155_EXACTLY_ONE_PROJECTED_METHOD")
        projection_identity = projected[0]
        target_type = projection_identity[1][2:-3]
        original_projection = [
            m for m in original_profile["methods"]
            if (m["name"], m["descriptor"]) == projection_identity
        ]
        require(len(original_projection) == 1
                and target_type in provided_owners
                and not target_type.startswith("rs/")
                and (original_projection[0]["access"] & 0x0007) == 0
                and original_projection[0]["code_length"] >= 30
                and not original_projection[0]["method_invocations"]
                and len(original_projection[0]["field_accesses"]) >= 8
                and all(field["owner"] in (original_owner, target_type)
                        for field in original_projection[0]["field_accesses"]),
                "R155_ORIGINAL_TRANSFORM_PROJECTION_BODY_NOT_JVM_GROUNDED")
    require(len(referenced) == len(provided_owners) == 3
            and referenced == provided_owners
            and all(owner + ".class" in present_original
                    for owner in provided_owners)
            and any(owner.startswith("rs/") for owner in provided_owners),
            "R153_HELPER_SOURCES_NOT_EXACT_ORIGINAL_DECODER_DEPENDENCIES")
    # JDK AST verifies the *top-level class names* of support Java and
    # matrix Java. This does not verify or run any support class body.
    with tempfile.TemporaryDirectory(prefix="spk-r153-private-loader-") as td:
        root = Path(td)
        declarations = _java_ast_declarations(
            matrix_java + helpers, root)
        require({name for _, name in declarations} ==
                {original_owner} | provided_owners and
                len(declarations) == 4,
                "R153_SOURCE_AST_DECLARATIONS_NOT_EXACT_ORIGINAL_OWNERS")

        sources_root = root / "matrix-source"
        output = root / "source-only-compiled"
        empty = root / "no-original-classpath"
        output.mkdir()
        empty.mkdir()
        paths = []
        for rel, data in matrix_java + helpers:
            path = sources_root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            paths.append(str(path))
        javac = shutil.which("javac")
        require(javac is not None, "R153_JDK_COMPILER_NOT_FOUND")
        env = os.environ.copy()
        for key in ("CLASSPATH", "JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS"):
            env.pop(key, None)
        try:
            run = subprocess.run(
                [javac, "--release", "9", "-proc:none",
                 "-implicit:none", "-g:none",
                 "-classpath", str(empty), "-sourcepath", str(empty),
                 "-d", str(output), *paths],
                cwd=root, env=env, stdin=subprocess.DEVNULL,
                capture_output=True, timeout=90, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PrivateMatrixLoaderR153Error(
                "R153_JDK_COMPILATION_NOT_COMPLETED") from exc
        require(run.returncode == 0,
                "R153_PRIVATE_GAME_SOURCE_ONLY_COMPILATION_FAILED")
        binary_path = output / (original_owner + ".class")
        require(binary_path.is_file() and not binary_path.is_symlink(),
                "R153_RECOMPILED_MATRIX_OWNER_MISSING")
        compiled_names = {
            path.relative_to(output).as_posix()
            for path in output.rglob("*.class")
        }
        require(compiled_names ==
                {name + ".class" for name in
                 {original_owner} | provided_owners},
                "R153_UNEXPECTED_CLASSFILE_OR_INNER_OUTPUT")
        built_binary = binary_path.read_bytes()

    try:
        built_profile = profile_class_field_accesses(built_binary)
        checks = _strict_inspections(original_profile, built_profile,
                                     selected=selected)
    except (BytecodeProfileError, PrivateMatrixMethodSourceR150Error,
            KeyError, ValueError) as exc:
        raise PrivateMatrixLoaderR153Error(
            "R153_SELECTED_ORIGINAL_JVM_CODE_PARITY_FAILED") from exc
    require(built_profile["internal_name"] == original_owner
            and checks["verified_selected_method_count"] ==
                (2 + (2 if allow_euler_method_bodies else 0) +
                 (1 if allow_transform_projection_method else 0) +
                 (1 if allow_matrix_string_method else 0))
            and checks["verified_constructor_count"] == 1
            and checks["core_method_bytecode_differences"] == 0,
            "R153_SELECTED_ORIGINAL_MATRIX_METHOD_BODY_NOT_VERIFIED")
    private_method_evidence = checks.pop("private_methods")
    result = {
        "schema_version": 1,
        "kind": "private_v309_matrix_packet_constructor_decoder_java9_r153",
        "original_client_sha256": original_sha256,
        "private_matrix_java_zip_sha256": matrix_source_sha256,
        "private_unverified_support_java_zip_sha256": support_source_sha256,
        "private_method_selection_sha256": selection_sha256,
        "original_matrix_classfile_sha256":
            hashlib.sha256(original_raw).hexdigest(),
        "privately_recompiled_matrix_classfile_sha256":
            hashlib.sha256(built_binary).hexdigest(),
        **checks,
        "source_only_supporting_class_count": len(provided_owners),
        "euler_float_array_source_methods_checked":
            2 if allow_euler_method_bodies else 0,
        "euler_methods_required_explicit_opt_in": True,
        "transform_projection_method_checked":
            1 if allow_transform_projection_method else 0,
        "transform_projection_requires_explicit_opt_in": True,
        "matrix_string_method_checked":
            1 if allow_matrix_string_method else 0,
        "matrix_string_method_requires_explicit_opt_in": True,
        "support_transform_type_field_values_accepted": False,
        "support_class_bodies_original_equivalence_accepted": False,
        "support_class_bodies_executed": False,
        "source_supports_are_original_class_binary_fallback": False,
        "original_game_class_binary_or_jar_on_javac_classpath": False,
        "compiler_external_classpath_empty": True,
        "original_packet_reader_member_semantics_verified": False,
        "complete_original_matrix_class_source_accepted": False,
        "whole_v309_client_source_compilation_accepted": False,
        "original_source_publication_authorized": False,
        "private_selected_method_evidence_sha256": hashlib.sha256(
            json.dumps(private_method_evidence, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")).hexdigest(),
    }
    require(all(sha_file(path) == digest for path, digest in inputs),
            "R153_ORIGINAL_INPUTS_CHANGED_DURING_SOURCE_REBUILD")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_original_v309_jar")
    p.add_argument("private_one_matrix_source_java_zip")
    p.add_argument("private_three_supporting_source_java_zip")
    p.add_argument("private_exact_two_method_selection_json")
    p.add_argument("fresh_private_sanitized_report_json")
    p.add_argument("--matrix-sha256", required=True)
    p.add_argument("--support-sha256", required=True)
    p.add_argument("--selection-sha256", required=True)
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    p.add_argument("--original-owner", default="com/a/b/a/b")
    p.add_argument("--allow-euler-method-bodies", action="store_true")
    p.add_argument("--allow-transform-projection-method",
                   action="store_true")
    p.add_argument("--allow-matrix-string-method",
                   action="store_true")
    a = p.parse_args(argv)
    dest = Path(a.fresh_private_sanitized_report_json)
    try:
        require(not dest.exists() and not dest.is_symlink()
                and dest.parent.is_dir() and not dest.parent.is_symlink(),
                "R153_PRIVATE_REPORT_MUST_NOT_EXIST")
        results = verify_private_original_matrix_packet_loader(
            a.private_original_v309_jar,
            a.private_one_matrix_source_java_zip,
            a.private_three_supporting_source_java_zip,
            a.private_exact_two_method_selection_json,
            original_sha256=a.original_sha256,
            matrix_source_sha256=a.matrix_sha256,
            support_source_sha256=a.support_sha256,
            selection_sha256=a.selection_sha256,
            original_owner=a.original_owner,
            allow_euler_method_bodies=a.allow_euler_method_bodies,
            allow_transform_projection_method=a.allow_transform_projection_method,
            allow_matrix_string_method=a.allow_matrix_string_method)
        dest.write_text(json.dumps(
            results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("R153_ORIGINAL_PACKET_DEPENDENT_MATRIX_JAVA_METHODS_PROVEN")
        print("private_report_sha256=" + sha_file(dest))
    except Exception:
        p.error("R153_ORIGINAL_MATRIX_PACKET_LOADER_SOURCE_PROOF_FAILED")


if __name__ == "__main__":
    main()
