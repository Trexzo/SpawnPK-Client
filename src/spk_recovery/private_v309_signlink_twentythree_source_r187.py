"""R187: SHA-pinned original v309 Signlink g() + <clinit> Java-source proof.

Previous R186 21-method source is independently replayed, then the candidate
23-method Java source is recompiled with only explicitly enumerated, NOT
ORIGINAL, compiler declarations. The large run() remains deliberately unproved.
No game code is executed and no partial class is canonically installed.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file, source_members
from .private_v309_matrix_source_method_parity_r150 import _strict_inspections
from .private_v309_signlink_twentyone_source_r186 import (
    TWENTYONE, HELPER_OWNERS, ORIGINAL_OWNER, ORIGINAL_CLASS_SHA256,
    verify_21_original_signlink_methods,
)

NEW_TWO = (("g", "()Ljava/lang/String;"), ("<clinit>", "()V"))
TWENTYTHREE = tuple((*TWENTYONE, *NEW_TWO))
TOTAL_METHODS = 24
MATCHED_JVM_INSTRUCTIONS = 622
NEW_JVM_INSTRUCTIONS = 153


class R187OriginalSignlinkTwentyThreeError(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise R187OriginalSignlinkTwentyThreeError(why)


def verify_23_original_signlink_java(
        original_jar, source_6_zip, source_11_zip, source_16_zip,
        source_21_zip, source_23_zip, compiler_helpers_zip, *,
        original_sha256=CANONICAL_V309,
        source_6_sha256, source_11_sha256, source_16_sha256,
        source_21_sha256, source_23_sha256, compiler_helpers_sha256,
        original_owner=ORIGINAL_OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        expected_original_method_count=TOTAL_METHODS,
        expected_six_instructions=62,
        expected_eleven_instructions=147,
        expected_sixteen_instructions=356,
        expected_twentyone_instructions=469,
        expected_all_instructions=MATCHED_JVM_INSTRUCTIONS,
        expected_new_instructions=NEW_JVM_INSTRUCTIONS):
    need(expected_all_instructions-expected_twentyone_instructions==
         expected_new_instructions and
         len(TWENTYTHREE)==23 and
         len(set(TWENTYTHREE))==23 and
         set(TWENTYTHREE)-set(TWENTYONE)==set(NEW_TWO),
         "R187_ONLY_ORIGINAL_G_AND_CLINIT_ADDED")
    inputs=(
        (original_jar,original_sha256),
        (source_6_zip,source_6_sha256),
        (source_11_zip,source_11_sha256),
        (source_16_zip,source_16_sha256),
        (source_21_zip,source_21_sha256),
        (source_23_zip,source_23_sha256),
        (compiler_helpers_zip,compiler_helpers_sha256),
    )
    need(all(sha_file(f)==sha for f,sha in inputs),
         "R187_ALL_PRIVATE_BINARY_AND_SOURCE_SHA256_PINS_REQUIRED")

    prior=verify_21_original_signlink_methods(
        original_jar,source_6_zip,source_11_zip,source_16_zip,
        source_21_zip,compiler_helpers_zip,
        original_sha256=original_sha256,
        six_source_sha256=source_6_sha256,
        eleven_source_sha256=source_11_sha256,
        sixteen_source_sha256=source_16_sha256,
        source_21_sha256=source_21_sha256,
        compiler_helper_sha256=compiler_helpers_sha256,
        original_owner=original_owner,
        original_class_sha256=original_class_sha256,
        expected_original_methods=expected_original_method_count,
        six_previous_instructions=expected_six_instructions,
        eleven_previous_instructions=expected_eleven_instructions,
        sixteen_previous_instructions=expected_sixteen_instructions,
        expected_total_instructions=expected_twentyone_instructions,
        expected_added_instructions=
            expected_twentyone_instructions-expected_sixteen_instructions)
    need(prior["verified_selected_method_count"]==21,
         "R187_R186_21_METHOD_EVIDENCE_NOT_REVERIFIED")
    original_candidates=source_members(source_23_zip,source_23_sha256)
    helpers=source_members(compiler_helpers_zip,compiler_helpers_sha256)
    need(len(original_candidates)==1 and
         original_candidates[0][0]==original_owner+".java" and
         0<len(original_candidates[0][1])<=150_000,
         "R187_EXACT_ONE_PRIVATE_ORIGINAL_OWNER_JAVA_SOURCE")
    need(len(helpers)==len(HELPER_OWNERS) and
         {rel for rel,_ in helpers}==
             {o+".java" for o in HELPER_OWNERS} and
         sum(len(body) for _,body in helpers)<=50_000,
         "R187_NO_EXTRA_OR_ORIGINAL_HELPER_CLASSFILES")
    with ZipFile(original_jar) as z:
        owner_path=original_owner+".class"
        need(z.namelist().count(owner_path)==1,
             "R187_ORIGINAL_OWNER_CLASSFILE_NOT_UNIQUE")
        original_bytes=z.read(owner_path)
    need(hashlib.sha256(original_bytes).hexdigest()==original_class_sha256,
         "R187_ORIGINAL_SIGNLINK_CLASS_SHA_CHANGED")
    original=parse_class(original_bytes)
    need(original.name==original_owner and
         original.super_name=="java/lang/Object" and
         original.major==53 and
         len(original.methods)==expected_original_method_count,
         "R187_FULL_ORIGINAL_OWNER_HEADER_CHANGED")

    javac=shutil.which("javac")
    need(javac is not None,"R187_JDK_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r187-private-") as tmp:
        root=Path(tmp)
        srcroot=root/"source"
        files=[]
        for rel,body in [*original_candidates,*helpers]:
            output=srcroot/rel
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_bytes(body)
            files.append(str(output))
        classes=root/"classfiles"
        empty=root/"empty"
        classes.mkdir()
        empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            result=subprocess.run(
                [javac,"--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(classes),*files],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=120,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R187OriginalSignlinkTwentyThreeError(
                "R187_INDEPENDENT_SOURCE_BUILD_ABORTED") from exc
        emitted={p.relative_to(classes).as_posix()
                 for p in classes.rglob("*.class")}
        need(result.returncode==0 and
             emitted==({original_owner+".class"} |
                       {o+".class" for o in HELPER_OWNERS}),
             "R187_ORIGINAL_OWNER_AND_SIX_DECLARATION_CLASS_SET_REQUIRED")
        built=(classes/(original_owner+".class")).read_bytes()

    rebuilt=parse_class(built)
    need((original.name,original.super_name,original.access,
          original.major,original.interfaces)==
         (rebuilt.name,rebuilt.super_name,rebuilt.access,
          rebuilt.major,rebuilt.interfaces),
         "R187_ORIGINAL_CLASS_HEADER_NOT_EQUAL")
    left=profile_class_field_accesses(original_bytes)
    right=profile_class_field_accesses(built)
    known=lambda x:{(m["name"],m["descriptor"]) for m in x["methods"]}
    need(set(TWENTYTHREE).issubset(known(left)) and
         set(TWENTYTHREE).issubset(known(right)),
         "R187_MISSING_G_OR_CLASS_INITIALIZER_METHOD")
    try:
        matched=_strict_inspections(
            left,right,selected=sorted(TWENTYTHREE))
    except ValueError as exc:
        raise R187OriginalSignlinkTwentyThreeError(
            "R187_ORIGINAL_23_METHOD_CODE_DIFFERENCE") from exc
    need(matched["verified_selected_method_count"]==23 and
         matched["verified_selected_class_initializer_count"]==1 and
         matched["matched_opcode_count"]==expected_all_instructions and
         matched["all_selected_core_method_code_equal"],
         "R187_G_AND_CLINIT_EXACT_JVM_METHOD_CODE_NOT_ESTABLISHED")
    need(all(sha_file(f)==sha for f,sha in inputs),
         "R187_PRIVATE_INPUTS_CHANGED_DURING_VERIFICATION")
    return {
        "schema_version":1,
        "kind":"v309_original_signlink_23_selected_java_methods_r187",
        "original_class_sha256":original_class_sha256,
        "original_method_count":expected_original_method_count,
        "verified_original_method_count":23,
        "matched_original_jvm_instructions":expected_all_instructions,
        "new_original_method_count":2,
        "new_original_jvm_instructions":expected_new_instructions,
        "original_method_count_remaining":expected_original_method_count-23,
        "original_run_method_unverified":True,
        "class_initializer_complete_original_code_verified":True,
        "full_class_field_and_support_type_abi_verified":False,
        "compiler_only_helper_java_is_original":False,
        "full_original_signlink_source_verified":False,
        "canonical_client_source_tree_modified":False,
        "entire_original_client_compiled":False,
        "original_client_code_executed":False,
        "publication_authorized":False,
    }
