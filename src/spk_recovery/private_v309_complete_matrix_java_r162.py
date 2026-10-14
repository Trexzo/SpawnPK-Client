"""R162: verify all original v309 matrix methods from one PRIVATE Java class.

Requires exact original matrix+Packet JVM identities, full original-method
selection, source-only five-helper compilation (one rs/ owner), exact decoded
method Code with no binary fallback, field ABI and self-call closure.
Passing this does NOT verify helper behavior, full classfile attributes,
StackMap equivalence or the whole client source tree.
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

from .classfile import parse_class
from .bytecode_profile import profile_class_field_accesses
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file, source_members
from .private_v309_dependency_closure_r136 import audit_pinned_original_jar
from .private_v309_matrix_source_method_parity_r150 import (
    _method_list, _strict_inspections, _self_call_closure_for_selected,
)

MATRIX_SHA = "52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030"


class CompleteMatrixJavaR162Error(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise CompleteMatrixJavaR162Error(reason)


def verify_complete_original_matrix_java(
        original_jar, matrix_java_zip, helper_java_zip,
        exact_selection_json, *, original_sha256=CANONICAL_V309,
        matrix_source_sha256, helper_source_sha256, selection_sha256,
        matrix_owner="com/a/b/a/b", packet_owner="rs/x/e",
        expected_matrix_sha256=MATRIX_SHA,
        expected_members=24, expected_instructions=3780,
        expected_helper_classes=5, expected_self_calls=12):
    pins=[(original_jar,original_sha256),
          (matrix_java_zip,matrix_source_sha256),
          (helper_java_zip,helper_source_sha256),
          (exact_selection_json,selection_sha256)]
    require(all(sha_file(path)==digest for path,digest in pins),
            "R162_EXACT_PRIVATE_INPUT_HASH_MISMATCH")
    require(all(re.fullmatch(
                r"[A-Za-z_$][A-Za-z0-9_$]*(?:/[A-Za-z_$][A-Za-z0-9_$]*)+",
                owner) for owner in (matrix_owner,packet_owner))
            and packet_owner.startswith("rs/")
            and not matrix_owner.startswith("rs/")
            and 2 <= expected_members <= 64
            and expected_instructions > 0
            and 2 <= expected_helper_classes <= 6
            and 1 <= expected_self_calls <= 64,
            "R162_ORIGINAL_IDENTITIES_OR_BOUNDS_UNSAFE")
    partition=audit_pinned_original_jar(
        original_jar,original_sha256=original_sha256,
        include_private_names=True)["private_dependency_partition"]
    require(matrix_owner in partition["direct_rs_dependent_non_rs"],
            "R162_ORIGINAL_MATRIX_GAME_LINKED_BINARY_EXCLUSION_UNPROVEN")
    raw=Path(exact_selection_json).read_bytes()
    require(len(raw) <= 100000, "R162_UNBOUNDED_PRIVATE_MEMBER_SELECTION")
    selection=_method_list(json.loads(raw),
                           allow_constructor_methods=True,
                           allow_class_initializer=True)
    require(len(selection)==expected_members
            and ("<clinit>","()V") in selection
            and ("<init>","(L"+packet_owner+";Z)V") in selection
            and ("a","(L"+packet_owner+";Z)V") in selection,
            "R162_ALL_METHODS_CLASS_INITIALIZER_AND_PACKET_NOT_SELECTED")
    candidate=source_members(matrix_java_zip,matrix_source_sha256)
    helper=source_members(helper_java_zip,helper_source_sha256)
    require(len(candidate)==1 and
            candidate[0][0]==matrix_owner+".java" and
            len(helper)==expected_helper_classes,
            "R162_EXACT_MATRIX_AND_HELPER_SOURCE_FILE_COUNT_REQUIRED")
    owners=[p[:-5] for p,_ in helper]
    require(len(owners)==len(set(o.casefold() for o in owners))
            and matrix_owner not in owners
            and owners.count(packet_owner)==1
            and sum(o.startswith("rs/") for o in owners)==1
            and all(p.endswith(".java") and 0<len(body)<=100000
                    for p,body in helper),
            "R162_ONLY_ONE_PROVEN_GAME_PACKET_JAVA_TYPE_ALLOWED")
    with ZipFile(original_jar) as jar:
        known=set(jar.namelist())
        require(all(owner+".class" in known for owner in owners),
                "R162_NONORIGINAL_HELPER_JVM_OWNER_FORBIDDEN")
        binary=jar.read(matrix_owner+".class")
    require(hashlib.sha256(binary).hexdigest()==expected_matrix_sha256,
            "R162_ORIGINAL_MATRIX_CLASS_HASH_MISMATCH")
    java=shutil.which("javac")
    require(java is not None, "R162_JDK_COMPILER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r162-private-") as tmp:
        root=Path(tmp)
        files=[]
        for relative,data in [*candidate,*helper]:
            path=root/"src"/relative
            require(not path.exists(), "R162_JAVA_SOURCE_PATH_CONFLICT")
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
            files.append(path)
        output=root/"classes"
        empty=root/"empty"
        output.mkdir()
        empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            proc=subprocess.run(
                [java,"--release","9","-proc:none","-implicit:none",
                 "-g:none","-classpath",str(empty),"-sourcepath",str(empty),
                 "-d",str(output),*[str(p) for p in files]],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=90,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise CompleteMatrixJavaR162Error(
                "R162_JAVA_SOURCE_COMPILE_UNAVAILABLE") from exc
        require(proc.returncode==0,
                "R162_FULL_MATRIX_SOURCE_NOT_INDEPENDENTLY_COMPILABLE")
        produced={p.relative_to(output).as_posix()
                  for p in output.rglob("*.class")}
        require(produced=={matrix_owner+".class"} |
                {owner+".class" for owner in owners},
                "R162_JAVAC_EMITTED_UNEXPECTED_CLASS_OR_MISSING_HELPER")
        rebuilt_bytes=(output/(matrix_owner+".class")).read_bytes()
    original_class=parse_class(binary)
    rebuilt_class=parse_class(rebuilt_bytes)
    original_fields={(f["name"],f["descriptor"],f["access"])
                     for f in original_class.fields}
    rebuilt_fields={(f["name"],f["descriptor"],f["access"])
                    for f in rebuilt_class.fields}
    require(original_fields==rebuilt_fields,
            "R162_REBUILT_ORIGINAL_MATRIX_FIELD_ABI_DIFFERS")
    original=profile_class_field_accesses(binary)
    rebuilt=profile_class_field_accesses(rebuilt_bytes)
    original_members={(m["name"],m["descriptor"]) for m in original["methods"]}
    rebuilt_members={(m["name"],m["descriptor"]) for m in rebuilt["methods"]}
    require(original["internal_name"]==rebuilt["internal_name"]==matrix_owner
            and original_members==rebuilt_members==set(selection),
            "R162_ENTIRE_ORIGINAL_MATRIX_METHOD_ABI_NOT_COVERED")
    result=_strict_inspections(original,rebuilt,selected=selection)
    require(result["verified_selected_method_count"]==expected_members
            and result["matched_opcode_count"]==expected_instructions
            and result["all_selected_core_method_code_equal"],
            "R162_NOT_ALL_ORIGINAL_MATRIX_METHOD_JVM_CODE_EQUAL")
    first=_self_call_closure_for_selected(original,selection,matrix_owner)
    second=_self_call_closure_for_selected(rebuilt,selection,matrix_owner)
    require(first==second==expected_self_calls,
            "R162_ORIGINAL_MATRIX_METHOD_INVOKE_CLOSURE_DIFFERS")
    require(all(sha_file(path)==digest for path,digest in pins),
            "R162_INPUT_CHANGED_AFTER_COMPILATION")
    return {
        "schema_version":1,
        "kind":"v309_complete_matrix_java_method_code_r162",
        "original_client_sha256":original_sha256,
        "original_matrix_class_sha256":expected_matrix_sha256,
        "private_matrix_java_source_zip_sha256":matrix_source_sha256,
        "private_source_only_helpers_sha256":helper_source_sha256,
        "private_complete_selection_sha256":selection_sha256,
        "original_matrix_method_count":expected_members,
        "all_original_matrix_method_ids_present":True,
        "original_recompiled_jvm_instruction_count":expected_instructions,
        "original_matrix_field_abi_exact":True,
        "original_self_call_edges_closed":first,
        "isolated_source_only_java_compilation_passed":True,
        "strict_original_stackmap_representations_equal":
            result["all_selected_stackmap_representations_equal"],
        "all_original_method_code_attributes_byte_identical":False,
        "original_game_binary_fallback_used":False,
        "packet_and_external_helper_bodies_proven_original":False,
        "complete_original_client_java_compilation_passed":False,
        "source_redistribution_authorized":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("original_jar","matrix_source_zip","helper_java_zip",
                 "selection_json","fresh_private_report_json"):
        p.add_argument(name)
    for name in ("matrix-sha256","helpers-sha256","selection-sha256"):
        p.add_argument("--"+name,required=True)
    args=p.parse_args(argv)
    out=Path(args.fresh_private_report_json)
    try:
        require(not out.exists() and not out.is_symlink()
                and out.parent.is_dir() and not out.parent.is_symlink(),
                "R162_PRIVATE_OUTPUT_NOT_FRESH")
        result=verify_complete_original_matrix_java(
            args.original_jar,args.matrix_source_zip,args.helper_java_zip,
            args.selection_json,
            matrix_source_sha256=args.matrix_sha256,
            helper_source_sha256=args.helpers_sha256,
            selection_sha256=args.selection_sha256)
        out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",
                       encoding="utf-8")
        print("R162_COMPLETE_MATRIX_JAVA_CODE_VERIFIED_NOT_FULL_CLIENT")
        print("private_report_sha256="+sha_file(out))
    except Exception:
        p.error("R162_ALL_MATRIX_METHODS_JAVA_SOURCE_NOT_ACCEPTED")


if __name__=="__main__":
    main()
