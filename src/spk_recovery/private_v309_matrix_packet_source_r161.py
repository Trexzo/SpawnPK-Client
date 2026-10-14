"""R161: exact original-linked matrix Packet constructor + loader Java source proof.

Compiles privately recovered matrix JAVA together with SHA-pinned, explicitly
unverified Java-only auxiliary types, including exactly one original rs/
Packet owner. Never loads original game binaries into javac or executes them.
Only explicitly selected original-vs-recompiled MATRIX JVM Code can pass.
"""
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

from .bytecode_profile import profile_class_field_accesses
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import source_members, sha_file
from .private_v309_dependency_closure_r136 import audit_pinned_original_jar
from .private_v309_matrix_source_method_parity_r150 import (
    _method_list, _strict_inspections, _self_call_closure_for_selected,
)

MATRIX_SHA = "52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030"


class R161MatrixPacketSourceError(ValueError):
    pass


def check(ok, reason):
    if not ok:
        raise R161MatrixPacketSourceError(reason)


def verify_original_packet_loader_java(
        original_jar, private_matrix_source_zip, private_helpers_source_zip,
        private_selection_json, *,
        original_sha256=CANONICAL_V309, matrix_source_sha256,
        helper_source_sha256, selection_sha256,
        matrix_owner="com/a/b/a/b", packet_owner="rs/x/e",
        loader_method="a", expected_matrix_sha256=MATRIX_SHA,
        expected_methods=11, expected_instructions=3430,
        expected_helper_sources=5, expected_self_calls=5):
    pins = [(original_jar, original_sha256),
            (private_matrix_source_zip, matrix_source_sha256),
            (private_helpers_source_zip, helper_source_sha256),
            (private_selection_json, selection_sha256)]
    check(all(sha_file(file) == digest for file, digest in pins),
          "R161_EXACT_PINNED_PRIVATE_INPUT_MISMATCH")
    check(all(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*(?:/[A-Za-z_$][A-Za-z0-9_$]*)+",
                           name) for name in (matrix_owner,packet_owner)),
          "R161_UNSAFE_ORIGINAL_CLASS_IDENTITY")
    check(packet_owner.startswith("rs/") and
          not matrix_owner.startswith("rs/") and
          expected_methods in range(2,33) and expected_instructions > 0 and
          2 <= expected_helper_sources <= 6 and
          1 <= expected_self_calls <= 32,
          "R161_BOUNDED_SOURCE_REPLAY_REQUIRED")
    graph = audit_pinned_original_jar(
        original_jar, original_sha256=original_sha256,
        include_private_names=True)
    check(matrix_owner in graph["private_dependency_partition"][
        "direct_rs_dependent_non_rs"],
        "R161_ORIGINAL_MATRIX_MUST_BE_EXCLUDED_RS_LINKED_OWNER")
    raw = Path(private_selection_json).read_bytes()
    check(len(raw) < 100_000, "R161_SELECTION_NOT_BOUNDED")
    selected = _method_list(json.loads(raw), allow_constructor_methods=True)
    mandatory = {("<init>","(L"+packet_owner+";Z)V"),
                 (loader_method,"(L"+packet_owner+";Z)V")}
    check(mandatory.issubset(set(selected)) and
          len(selected) == expected_methods,
          "R161_PACKET_CONSTRUCTOR_AND_LOADER_MUST_BOTH_BE_SELECTED")
    source = source_members(private_matrix_source_zip, matrix_source_sha256)
    check(len(source) == 1 and source[0][0] == matrix_owner+".java",
          "R161_EXACT_ONE_RECOVERED_JAVA_MATRIX_OWNER")
    helpers = source_members(private_helpers_source_zip, helper_source_sha256)
    check(len(helpers) == expected_helper_sources and
          len(helpers) <= 6 and
          all(path.endswith(".java") and
              0 < len(body) <= 100_000 for path, body in helpers),
          "R161_EXACT_SOURCE_HELPER_COUNT_OR_SIZE_MISMATCH")
    helper_names = [p[:-5] for p,_ in helpers]
    check(len(helper_names) == len(set(n.casefold() for n in helper_names))
          and matrix_owner not in helper_names
          and helper_names.count(packet_owner) == 1
          and sum(n.startswith("rs/") for n in helper_names) == 1,
          "R161_EXACTLY_ONE_REAL_ORIGINAL_PACKET_RS_SOURCE_HELPER")
    with ZipFile(original_jar) as jar:
        all_entries = set(jar.namelist())
        check(all(n+".class" in all_entries for n in helper_names),
              "R161_HELPER_MUST_HAVE_EXACT_PROVEN_ORIGINAL_JVM_IDENTITY")
        original_binary = jar.read(matrix_owner+".class")
    check(hashlib.sha256(original_binary).hexdigest() ==
          expected_matrix_sha256,
          "R161_ORIGINAL_MATRIX_CLASS_SHA256_MISMATCH")
    javac = shutil.which("javac")
    check(javac is not None, "R161_TRUSTED_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r161-source-only-") as temp:
        root = Path(temp)
        paths = []
        for relative,contents in [*source,*helpers]:
            target = root / "src" / relative
            target.parent.mkdir(parents=True,exist_ok=True)
            check(not target.exists() and not target.is_symlink(),
                  "R161_DUPLICATE_SOURCE_OVERWRITE")
            target.write_bytes(contents)
            paths.append(target)
        classes = root / "compiled"
        empty = root / "empty"
        classes.mkdir()
        empty.mkdir()
        env = os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            proc = subprocess.run(
                [javac,"--release","9","-proc:none","-implicit:none",
                 "-g:none","-classpath",str(empty),"-sourcepath",str(empty),
                 "-d",str(classes),*[str(path) for path in paths]],
                env=env,cwd=root,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=90,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R161MatrixPacketSourceError(
                "R161_PRIVATE_SOURCE_JAVAC_DID_NOT_FINISH") from exc
        check(proc.returncode == 0,
              "R161_PRIVATE_MATRIX_JAVA_SOURCE_DID_NOT_COMPILE")
        emitted = {p.relative_to(classes).as_posix()
                   for p in classes.rglob("*.class")}
        required = {matrix_owner+".class"} | {
            n+".class" for n in helper_names}
        check(emitted == required, "R161_UNEXPECTED_OR_MISSING_CLASSFILE")
        rebuilt_binary=(classes/(matrix_owner+".class")).read_bytes()
    original = profile_class_field_accesses(original_binary)
    rebuilt = profile_class_field_accesses(rebuilt_binary)
    check(original["internal_name"] == rebuilt["internal_name"] == matrix_owner,
          "R161_RECOMPILED_JVM_OWNER_IDENTITY_MISMATCH")
    details = _strict_inspections(original,rebuilt,selected=selected)
    check(details["verified_selected_method_count"] == expected_methods
          and details["matched_opcode_count"] == expected_instructions
          and details["all_selected_core_method_code_equal"],
          "R161_ORIGINAL_JVM_SELECTED_METHOD_INSTRUCTIONS_NOT_EQUAL")
    original_edges = _self_call_closure_for_selected(original,selected,matrix_owner)
    rebuilt_edges = _self_call_closure_for_selected(rebuilt,selected,matrix_owner)
    check(original_edges == rebuilt_edges == expected_self_calls,
          "R161_PACKET_AND_MATRIX_SELF_INVOCATION_CLOSURE_NOT_PROVEN")
    check(all(sha_file(file) == digest for file,digest in pins),
          "R161_PRIVATE_SOURCE_INPUT_CHANGED_DURING_COMPILE")
    return {
        "schema_version":1,
        "kind":"v309_private_original_packet_matrix_source_r161",
        "original_client_sha256":original_sha256,
        "original_matrix_class_sha256":expected_matrix_sha256,
        "private_matrix_java_source_sha256":matrix_source_sha256,
        "private_helper_java_sources_sha256":helper_source_sha256,
        "private_selected_method_ids_sha256":selection_sha256,
        "original_selected_method_count_verified":expected_methods,
        "exact_selected_rebuilt_jvm_instruction_count":expected_instructions,
        "verified_same_owner_method_edges":original_edges,
        "compiler_only_helper_java_class_count":len(helpers),
        "original_packet_and_converter_helper_method_bodies_verified":False,
        "original_game_binary_used_for_compiler_dependencies":False,
        "all_original_matrix_method_bodies_proven_by_this_subset":False,
        "complete_matrix_java_source_accepted":False,
        "whole_original_v309_client_compiled":False,
        "private_original_source_publication_authorized":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_v309_jar")
    parser.add_argument("private_matrix_java_zip")
    parser.add_argument("private_five_helpers_java_zip")
    parser.add_argument("private_selection_json")
    parser.add_argument("fresh_private_report_json")
    parser.add_argument("--matrix-sha256",required=True)
    parser.add_argument("--helpers-sha256",required=True)
    parser.add_argument("--selection-sha256",required=True)
    args=parser.parse_args(argv)
    path=Path(args.fresh_private_report_json)
    try:
        check(not path.exists() and not path.is_symlink() and
              path.parent.is_dir() and not path.parent.is_symlink(),
              "R161_REPORT_DESTINATION_NOT_FRESH")
        report=verify_original_packet_loader_java(
            args.original_v309_jar,args.private_matrix_java_zip,
            args.private_five_helpers_java_zip,args.private_selection_json,
            matrix_source_sha256=args.matrix_sha256,
            helper_source_sha256=args.helpers_sha256,
            selection_sha256=args.selection_sha256)
        path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                        encoding="utf-8")
        print("R161_PRIVATE_MATRIX_PACKET_SOURCE_INSTRUCTION_MATCH_NOT_FULL_CLIENT")
        print("private_report_sha256="+sha_file(path))
    except Exception:
        parser.error("R161_ORIGINAL_PACKET_JAVA_SOURCE_NOT_ACCEPTED")


if __name__=="__main__":
    main()
