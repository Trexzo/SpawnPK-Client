"""R189: semantic (NOT byte-identical) original-v309 Signlink whole-owner Java proof.

This comparator explicitly permits ONLY JVM ldc (0x12) vs ldc_w (0x13)
constant-pool-index width changes, after resolving the exact referenced
constant/tag/raw bits. Branch and exception endpoints are resolved to
instruction ordinals, not unstable byte offsets. No other opcode, operand,
handler, access flag, stack/local limit, or field ABI drift is accepted.

The original class constant pool is type-grouped, unlike javac's output.
Classfile byte identity, StackMapTable semantic validity, optional non-Code
attributes, original support-class source, runtime and full-client builds
are outside this proof. No original code is executed.
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
from .private_client_source_ast_census_r126 import sha_file, source_members
from .private_v309_signlink_run_source_r188 import (
    ORIGINAL_OWNER, ORIGINAL_CLASS_SHA256, REQUIRED_COMPILER_HELPERS,
    verify_original_signlink_run_source,
)
from .source_method_parity import _normalized_instructions


EXPECTED_TOTAL_METHODS = 24
EXPECTED_TOTAL_INSTRUCTIONS = 870
EXPECTED_LDC_TO_LDC_W = 35
_BRANCHES = {f"0x{x:02x}" for x in range(0x99,0xA9)} | {
    "0xc6","0xc7","0xc8","0xc9",
}


class R189SignlinkWholeSourceSemanticError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise R189SignlinkWholeSourceSemanticError(message)


def _method_map(profile):
    found={}
    for method in profile["methods"]:
        key=(method["name"],method["descriptor"])
        need(key not in found,"R189_DUPLICATE_ORIGINAL_METHOD")
        found[key]=method
    return found


def _semantic_method(profile, method):
    """Strictly decode ALL instructions first, then narrow one encoding rule."""
    raw=_normalized_instructions(profile,method)
    boundaries={x["offset"]:n for n,x in enumerate(raw)}
    need(len(boundaries)==len(raw),"R189_DUPLICATE_INSTRUCTION_OFFSET")

    def instruction_index(byte_offset, *, may_end=False):
        if may_end and byte_offset==method["code_length"]:
            return len(raw)
        need(type(byte_offset) is int and byte_offset in boundaries,
             "R189_TARGET_IS_NOT_AN_INSTRUCTION_BOUNDARY")
        return boundaries[byte_offset]

    instructions=[]
    for record in raw:
        item=dict(record)
        item.pop("offset",None)
        item.pop("length",None)
        opcode=item["opcode"]
        if opcode in ("0x12","0x13"):
            need(item.get("constant_pool_tag") in (3,4,5,6,7,8),
                 "R189_LDC_LITERAL_CLASS_OR_BITS_UNRESOLVED")
            item["opcode"]="0x12"
            item["mnemonic"]="ldc"
        if opcode in _BRANCHES:
            item["branch_target_instruction_index"]=instruction_index(
                item.pop("branch_target_offset"))
        if opcode in ("0xaa","0xab"):
            item["default_target_instruction_index"]=instruction_index(
                item.pop("switch_default_target_offset"))
            if opcode=="0xaa":
                item["switch_target_instruction_indices"]=[
                    instruction_index(x) for x in item.pop("switch_targets")]
            else:
                item["switch_pairs_as_instruction_indices"]=[
                    (key,instruction_index(target))
                    for key,target in item.pop("switch_pairs")]
        instructions.append(item)
    handlers=[]
    for row in method["exception_handlers"]:
        handlers.append({
            "start_instruction":instruction_index(row["start_pc"]),
            "end_instruction":instruction_index(
                row["end_pc"],may_end=True),
            "handler_instruction":instruction_index(row["handler_pc"]),
            "catch_type":row["catch_type"],
        })
    return instructions,handlers


def audit_original_owner_semantic_classfiles(
        original_bytes, rebuilt_bytes, *,
        expected_total_methods=EXPECTED_TOTAL_METHODS,
        expected_total_instructions=EXPECTED_TOTAL_INSTRUCTIONS,
        expected_ldc_widenings=EXPECTED_LDC_TO_LDC_W,
        expected_owner=None,
        expected_original_class_sha256=None):
    """Research-only whole-owner Code audit over two exact classfile byte blobs.

    Synthetic tests can set their own expected counts and owner. The original
    production path fixes those counts and uses independently SHA-pinned
    original source/JAR inputs.
    """
    need(type(original_bytes) is bytes and
         type(rebuilt_bytes) is bytes and
         len(original_bytes)>50 and len(rebuilt_bytes)>50,
         "R189_BOTH_COMPLETE_JVM_CLASSFILES_REQUIRED")
    if expected_original_class_sha256 is not None:
        need(hashlib.sha256(original_bytes).hexdigest()==
             expected_original_class_sha256,
             "R189_ORIGINAL_BINARY_CLASS_SHA256_MISMATCH")
    old=parse_class(original_bytes)
    new=parse_class(rebuilt_bytes)
    need((old.name,old.super_name,old.major,old.minor,
          old.access,old.interfaces)==
         (new.name,new.super_name,new.major,new.minor,
          new.access,new.interfaces),
         "R189_FULL_CLASS_HEADER_OR_INTERFACE_CHANGED")
    if expected_owner is not None:
        need(old.name==expected_owner,
             "R189_ORIGINAL_OWNER_DOES_NOT_MATCH_PIN")
    fields=lambda c:sorted(
        (f["name"],f["descriptor"],f["access"])
        for f in c.fields)
    need(fields(old)==fields(new),
         "R189_DECLARED_ORIGINAL_FIELD_ABI_DIFFERS")
    a=profile_class_field_accesses(original_bytes)
    b=profile_class_field_accesses(rebuilt_bytes)
    fields_full=lambda profile:sorted(
        (f["name"],f["descriptor"],f["access"],
         f.get("signature"),repr(f.get("constant_value")))
        for f in profile["fields"])
    need(fields_full(a)==fields_full(b),
         "R189_FIELD_CONST_VALUE_OR_SIGNATURE_CHANGED")
    old_methods=_method_map(a)
    new_methods=_method_map(b)
    need(set(old_methods)==set(new_methods) and
         len(old_methods)==expected_total_methods,
         "R189_ALL_ORIGINAL_METHOD_IDENTITIES_REQUIRED")
    total=0
    widenings=0
    identical_encoding_methods=0
    stackmap_encoding_mismatches=0
    for method_id in sorted(old_methods):
        left=old_methods[method_id]
        right=new_methods[method_id]
        need(left["code_length"] is not None and
             right["code_length"] is not None and
             left["access"]==right["access"] and
             left.get("signature")==right.get("signature") and
             left["max_stack"]==right["max_stack"] and
             left["max_locals"]==right["max_locals"],
             "R189_ORIGINAL_METHOD_FLAGS_OR_STACK_LOCALS_DIFFER")
        lhs,hleft=_semantic_method(a,left)
        rhs,hright=_semantic_method(b,right)
        need(lhs==rhs and hleft==hright,
             "R189_WHOLE_METHOD_SEMANTIC_CODE_OR_CATCH_DIFFERS")
        total+=len(lhs)
        lraw=left["instructions"]
        rraw=right["instructions"]
        need(len(lraw)==len(rraw),
             "R189_ORIGINAL_METHOD_INSTRUCTION_COUNT_DIFFERS")
        exact_encoding=True
        for x,y in zip(lraw,rraw):
            if x["opcode"]!=y["opcode"]:
                need(x["opcode"]=="0x12" and y["opcode"]=="0x13",
                     "R189_UNAUTHORIZED_NON_LDC_OPCODE_CHANGE")
                widenings+=1
                exact_encoding=False
        if exact_encoding:
            identical_encoding_methods+=1
        need(left["stackmap_table_present"]==
             right["stackmap_table_present"],
             "R189_STACKMAP_PRESENCE_CHANGED")
        if left["stackmap_frames"]!=right["stackmap_frames"]:
            stackmap_encoding_mismatches+=1
    need(total==expected_total_instructions and
         widenings==expected_ldc_widenings,
         "R189_ORIGINAL_OWNER_INSTRUCTION_OR_LDC_WIDTH_COUNT_DRIFT")
    return {
        "schema_version":1,
        "kind":"original_source_whole_owner_jvm_semantic_code_r189",
        "verified_original_owner":old.name,
        "all_method_signatures_flags_and_core_semantics_match":True,
        "all_declared_field_abi_and_constant_values_match":True,
        "methods_semantically_recompiled_in_one_java_class":
            expected_total_methods,
        "resolved_original_jvm_instructions_compared":total,
        "only_ldc_to_ldc_w_opcode_encoding_differences":widenings,
        "methods_with_unchanged_opcode_encoding":
            identical_encoding_methods,
        "methods_with_differing_stackmap_encoding":
            stackmap_encoding_mismatches,
        "all_original_byte_offsets_and_classfile_bytes_identical":False,
        "stackmap_semantic_equivalence_or_jvm_verifier_acceptance_proved":False,
        "optional_non_code_method_attributes_all_verified":False,
        "original_support_helper_java_sources_recovered":False,
        "original_game_executed":False,
        "original_runtime_validated":False,
        "complete_original_client_compiled":False,
        "original_derived_source_publication_authorized":False,
    }


def verify_pinned_v309_signlink_semantic_source(
        original_jar, source_6_zip,source_11_zip,
        source_16_zip,source_21_zip,source_23_zip,
        previous_six_helpers_zip,run_source_zip,run_helpers_zip, *,
        original_sha256,
        source_6_sha256,source_11_sha256,source_16_sha256,
        source_21_sha256,source_23_sha256,
        six_helpers_sha256,run_source_sha256,run_helpers_sha256,
        original_owner=ORIGINAL_OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256):
    """Private exact-source replay. Inputs are not eligible for public CI."""
    earlier=verify_original_signlink_run_source(
        original_jar,source_6_zip,source_11_zip,
        source_16_zip,source_21_zip,source_23_zip,
        previous_six_helpers_zip,run_source_zip,run_helpers_zip,
        original_sha256=original_sha256,
        six_source_sha256=source_6_sha256,
        eleven_source_sha256=source_11_sha256,
        sixteen_source_sha256=source_16_sha256,
        twentyone_source_sha256=source_21_sha256,
        twentythree_source_sha256=source_23_sha256,
        six_helpers_sha256=six_helpers_sha256,
        run_source_sha256=run_source_sha256,
        run_helpers_sha256=run_helpers_sha256,
        original_owner=original_owner,
        original_class_sha256=original_class_sha256,
        previous_twentythree_instructions=622)
    need(earlier["independently_verified_original_run_method"] and
         earlier["independently_verified_prior_original_methods"]==23,
         "R189_PRIOR_SHA_PINNED_PRIVATE_RUN_ACCEPTANCE_FAILED")
    fixed=(
        (original_jar,original_sha256),
        (run_source_zip,run_source_sha256),
        (run_helpers_zip,run_helpers_sha256),
    )
    need(all(sha_file(f)==sha for f,sha in fixed),
         "R189_ORIGINAL_BINARY_OR_JAVA_INPUT_SHA_CHANGED")
    with ZipFile(original_jar) as archive:
        path=original_owner+".class"
        need(archive.namelist().count(path)==1,
             "R189_ORIGINAL_CLASS_NOT_UNIQUE")
        original_class=archive.read(path)
    need(hashlib.sha256(original_class).hexdigest()==original_class_sha256,
         "R189_ORIGINAL_OWNER_CLASS_SHA_CHANGED")
    source=source_members(run_source_zip,run_source_sha256)
    helpers=source_members(run_helpers_zip,run_helpers_sha256)
    need(len(source)==1 and source[0][0]==original_owner+".java",
         "R189_EXACT_ONE_ORIGINAL_NAMED_SOURCE_FILE")
    need(len(helpers)==len(REQUIRED_COMPILER_HELPERS) and
         {rel for rel,_ in helpers}==
             {x+".java" for x in REQUIRED_COMPILER_HELPERS},
         "R189_ONLY_SEVEN_COMPILER_DECLARATION_HELPERS_ALLOWED")
    javac=shutil.which("javac")
    need(javac is not None,"R189_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r189-private-") as tmp:
        root=Path(tmp)
        files=[]
        for rel,raw in [*source,*helpers]:
            path=root/"source"/rel
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(raw)
            files.append(str(path))
        classes=root/"classes"
        empty=root/"empty"
        classes.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            run=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(classes),*files],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=120,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R189SignlinkWholeSourceSemanticError(
                "R189_JAVA9_SOURCE_ONLY_COMPILATION_ABORTED") from exc
        emitted={p.relative_to(classes).as_posix()
                 for p in classes.rglob("*.class")}
        need(run.returncode==0 and
             emitted==({original_owner+".class"} |
                      {x+".class" for x in REQUIRED_COMPILER_HELPERS}),
             "R189_NONORIGINAL_COMPILED_INPUT_OR_EXTRA_OUTPUT")
        rebuilt=(classes/(original_owner+".class")).read_bytes()
    result=audit_original_owner_semantic_classfiles(
        original_class,rebuilt,
        expected_owner=original_owner,
        expected_original_class_sha256=original_class_sha256)
    need(all(sha_file(f)==sha for f,sha in fixed),
         "R189_PRIVATE_ORIGINAL_AND_SOURCE_CHANGED_DURING_REPLAY")
    return result
