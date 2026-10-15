"""R188 — original-v309 Signlink run() Java-source recovery (single method).

The original rs/v/a.run():void JDK9 Code is verified independently of the
R187 23-method source candidate. The JVM compiler's constant-pool ordering
means these two separate private Java source builds are NOT a proven single
full-owner parity build. Seven Java dependencies are compiler-only stubs, NOT
original recovered class source. No original game code is executed.
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
from .private_v309_signlink_twentythree_source_r187 import (
    ORIGINAL_OWNER, ORIGINAL_CLASS_SHA256, HELPER_OWNERS,
    verify_23_original_signlink_java,
)

RUN_METHOD = ("run", "()V")
EXPECTED_RUN_JVM_INSTRUCTIONS = 248
ORIGINAL_METHODS = 24
REQUIRED_COMPILER_HELPERS = tuple(sorted((*HELPER_OWNERS, "rs/v/a$a")))


class R188OriginalSignlinkRunSourceError(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise R188OriginalSignlinkRunSourceError(why)


def verify_original_signlink_run_source(
        original_jar, previous_six_zip, previous_eleven_zip,
        previous_sixteen_zip, previous_twentyone_zip,
        previous_twentythree_zip, previous_six_helpers_zip,
        run_candidate_zip, run_compiler_helpers_zip, *,
        original_sha256=CANONICAL_V309,
        six_source_sha256, eleven_source_sha256, sixteen_source_sha256,
        twentyone_source_sha256, twentythree_source_sha256,
        six_helpers_sha256, run_source_sha256, run_helpers_sha256,
        original_owner=ORIGINAL_OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        original_methods=ORIGINAL_METHODS,
        expected_run_instructions=EXPECTED_RUN_JVM_INSTRUCTIONS,
        previous_six_instructions=62, previous_eleven_instructions=147,
        previous_sixteen_instructions=356,
        previous_twentyone_instructions=469,
        previous_twentythree_instructions=622,
):
    need(expected_run_instructions>0 and original_methods==24 and
         isinstance(original_owner,str) and "/" in original_owner,
         "R188_EXACT_ORIGINAL_RUN_METHOD_SCOPE_REQUIRED")
    private_inputs=(
        (original_jar,original_sha256),
        (previous_six_zip,six_source_sha256),
        (previous_eleven_zip,eleven_source_sha256),
        (previous_sixteen_zip,sixteen_source_sha256),
        (previous_twentyone_zip,twentyone_source_sha256),
        (previous_twentythree_zip,twentythree_source_sha256),
        (previous_six_helpers_zip,six_helpers_sha256),
        (run_candidate_zip,run_source_sha256),
        (run_compiler_helpers_zip,run_helpers_sha256),
    )
    need(all(sha_file(path)==sha for path,sha in private_inputs),
         "R188_EXACT_ORIGINAL_AND_ALL_PRIVATE_SOURCE_SHA_PINS_REQUIRED")

    earlier=verify_23_original_signlink_java(
        original_jar,previous_six_zip,previous_eleven_zip,
        previous_sixteen_zip,previous_twentyone_zip,
        previous_twentythree_zip,previous_six_helpers_zip,
        original_sha256=original_sha256,
        source_6_sha256=six_source_sha256,
        source_11_sha256=eleven_source_sha256,
        source_16_sha256=sixteen_source_sha256,
        source_21_sha256=twentyone_source_sha256,
        source_23_sha256=twentythree_source_sha256,
        compiler_helpers_sha256=six_helpers_sha256,
        original_owner=original_owner,
        original_class_sha256=original_class_sha256,
        expected_original_method_count=original_methods,
        expected_six_instructions=previous_six_instructions,
        expected_eleven_instructions=previous_eleven_instructions,
        expected_sixteen_instructions=previous_sixteen_instructions,
        expected_twentyone_instructions=previous_twentyone_instructions,
        expected_all_instructions=previous_twentythree_instructions,
        expected_new_instructions=
            previous_twentythree_instructions-previous_twentyone_instructions)
    need(earlier["verified_original_method_count"]==23,
         "R188_ORIGINAL_PREVIOUS_23_METHODS_NOT_INDEPENDENTLY_VERIFIED")

    recovered=source_members(run_candidate_zip,run_source_sha256)
    helpers=source_members(run_compiler_helpers_zip,run_helpers_sha256)
    need(len(recovered)==1 and
         recovered[0][0]==original_owner+".java" and
         0<len(recovered[0][1])<=160_000,
         "R188_ONE_ORIGINAL_NAMED_RUN_SOURCE_ONLY")
    need(len(helpers)==len(REQUIRED_COMPILER_HELPERS) and
         {path for path,_ in helpers}==
             {owner+".java" for owner in REQUIRED_COMPILER_HELPERS} and
         sum(len(data) for _,data in helpers)<=50_000,
         "R188_ONLY_SEVEN_EXPLICIT_COMPILER_HELPERS_ALLOWED")
    with ZipFile(original_jar) as archive:
        owner_file=original_owner+".class"
        need(archive.namelist().count(owner_file)==1,
             "R188_ORIGINAL_OWNER_CLASSFILE_NOT_UNIQUE")
        original_bytes=archive.read(owner_file)
    need(hashlib.sha256(original_bytes).hexdigest()==original_class_sha256,
         "R188_ORIGINAL_CLASSFILE_SHA_MISMATCH")
    original=parse_class(original_bytes)
    need(original.name==original_owner and
         original.super_name=="java/lang/Object" and
         original.major==53 and
         len(original.methods)==original_methods,
         "R188_ORIGINAL_FULL_METHOD_AND_OWNER_HEADER_CHANGED")

    javac=shutil.which("javac")
    need(javac is not None,"R188_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r188-private-") as tmp:
        root=Path(tmp)
        src=root/"sources"
        paths=[]
        for rel,data in [*recovered,*helpers]:
            output=src/rel
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_bytes(data)
            paths.append(str(output))
        empty=root/"empty"
        classes=root/"classes"
        empty.mkdir()
        classes.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            compiled=subprocess.run(
                [javac,"--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(classes),*paths],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=120,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R188OriginalSignlinkRunSourceError(
                "R188_PRIVATE_JAVA9_SOURCE_COMPILATION_ABORTED") from exc
        written={f.relative_to(classes).as_posix()
                 for f in classes.rglob("*.class")}
        need(compiled.returncode==0 and
             written==({original_owner+".class"} |
                       {name+".class" for name in REQUIRED_COMPILER_HELPERS}),
             "R188_SOURCE_ONLY_RUN_COMPILATION_NOT_CLOSED")
        candidate_bytes=(classes/(original_owner+".class")).read_bytes()

    candidate=parse_class(candidate_bytes)
    need((original.name,original.super_name,original.access,
          original.major,original.interfaces)==
         (candidate.name,candidate.super_name,candidate.access,
          candidate.major,candidate.interfaces),
         "R188_ORIGINAL_OWNER_JVM_CLASS_HEADER_CHANGED")
    fields=lambda c:sorted(
        (f["name"],f["descriptor"],f["access"]) for f in c.fields)
    need(fields(original)==fields(candidate) and
         len(original.methods)==len(candidate.methods)==original_methods,
         "R188_RUN_CANDIDATE_FIELD_ABI_OR_METHOD_COUNT_CHANGED")
    left=profile_class_field_accesses(original_bytes)
    right=profile_class_field_accesses(candidate_bytes)
    try:
        proof=_strict_inspections(left,right,selected=[RUN_METHOD])
    except ValueError as exc:
        raise R188OriginalSignlinkRunSourceError(
            "R188_ORIGINAL_RUN_METHOD_CODE_NOT_EQUAL") from exc
    need(proof["verified_selected_method_count"]==1 and
         proof["matched_opcode_count"]==expected_run_instructions and
         proof["all_selected_core_method_code_equal"],
         "R188_NOT_ALL_248_ORIGINAL_RUN_JVM_INSTRUCTIONS_MATCH")
    need(all(sha_file(f)==sha for f,sha in private_inputs),
         "R188_ORIGINAL_OR_PRIVATE_INPUTS_CHANGED_DURING_VERIFY")
    return {
        "schema_version":1,
        "kind":"v309_original_signlink_run_jvm_code_recovered_r188",
        "original_class_sha256":original_class_sha256,
        "independently_verified_prior_original_methods":23,
        "independently_verified_original_run_method":True,
        "run_matching_original_jvm_instructions":expected_run_instructions,
        "prior_stage_original_jvm_instructions":previous_twentythree_instructions,
        "all_24_method_bodies_individually_recovered_in_separate_builds":True,
        "run_jvm_stackmap_representation_equal":
            proof["all_selected_stackmap_representations_equal"],
        "original_full_field_declaration_abi_equal":True,
        "all_24_original_method_code_equal_in_one_recompiled_class":False,
        "original_nested_enum_java_source_recovered":False,
        "seven_compiler_only_helpers_original_source_verified":False,
        "complete_original_classfile_identical":False,
        "original_runtime_behavior_tested":False,
        "original_game_code_executed":False,
        "canonical_source_tree_modified":False,
        "whole_original_v309_client_compiles":False,
        "original_source_redistribution_authorized":False,
    }
