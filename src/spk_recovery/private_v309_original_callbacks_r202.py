"""R202: three original-v309 client callback scheduler/source interfaces.

Original-named rs/h/b, rs/h/e and rs/h/c Java are privately SHA-pinned and
compiled together with an EMPTY original and external classpath. All 121
scheduler JVM instructions, field ABI and nine method identities must match
the SHA-pinned original JAR. Interfaces have no Code; their abstract flags
and signatures are compared directly. No original code executes.

This public verifier contains no original derived Java source, only original
class fingerprints, exact private input ZIP pins and rejection rules.
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
from .private_v309_four_owner_javac_frontier_r192 import (
    compare_pinned_private_four_owner_javac,
)

ORIGINAL_CLASS_HASHES = {
    "rs/h/b": "a3a68a364e5c09d0c00c60816b3e92ed77517e801eee419664753933c837f578",
    "rs/h/e": "31c76d395cbc42e3146031208a4a4b1a8dfc4c9ec22b2a73d3f06a80fe6326e8",
    "rs/h/c": "279754600b461d48869a31e882a80b781d83d302113b532c23684d4f4da1dd06",
}
CALLBACK_PRIVATE_SOURCE_SHA256 = (
    "3c01c0c0e06d077dcd84ebaab8a1507b17562bcf05bfb4e63f4113dc7274604f"
)
PARENT_SOURCE_TREE_SHA256 = (
    "033a5a666e2efb279cd04da8e30ca527e9b198719558e3009cd2073fefdb742c"
)
R202_SOURCE_TREE_SHA256 = (
    "0dfe8e5bd245c6c6b51b562fc310f7730891a3aefaf1e18c97bd10fc6ba6fe39"
)
ORIGINAL_FIELDS={"rs/h/b":0, "rs/h/e":0, "rs/h/c":3}
ORIGINAL_METHODS={"rs/h/b":1, "rs/h/e":1, "rs/h/c":7}
SCHEDULER_INSTRUCTIONS=121


class R202OriginalCallbackError(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise R202OriginalCallbackError(why)


def _member_abi(parsed):
    fields=sorted(
        (x["name"],x["descriptor"],x["access"],x.get("signature"))
        for x in parsed.fields)
    methods=sorted(
        (x["name"],x["descriptor"],x["access"],x.get("signature"))
        for x in parsed.methods)
    return fields,methods


def verify_original_callback_java(
        original_jar, original_callback_source_zip, *,
        original_sha256=CANONICAL_V309,
        source_sha256=CALLBACK_PRIVATE_SOURCE_SHA256,
        original_class_hashes=ORIGINAL_CLASS_HASHES,
        expected_fields=ORIGINAL_FIELDS,
        expected_methods=ORIGINAL_METHODS,
        expected_scheduler_instructions=SCHEDULER_INSTRUCTIONS):
    need(sha_file(original_jar)==original_sha256 and
         sha_file(original_callback_source_zip)==source_sha256,
         "R202_EXACT_ORIGINAL_JAR_AND_SOURCE_ZIP_PINS_REQUIRED")
    need(set(original_class_hashes)==set(expected_fields)==
         set(expected_methods) and len(expected_fields)==3,
         "R202_EXPECTED_THREE_OWNERS_REQUIRED")
    sources=source_members(original_callback_source_zip,source_sha256)
    need(len(sources)==3 and
         {name for name,_ in sources}==
         {owner+".java" for owner in original_class_hashes} and
         all(0<len(data)<=100_000 for _,data in sources),
         "R202_ONLY_THREE_ORIGINAL_NAMED_SOURCE_FILES_ALLOWED")
    with ZipFile(original_jar) as jar:
        need(all(jar.namelist().count(owner+".class")==1
                 for owner in original_class_hashes),
             "R202_ORIGINAL_CALLBACK_BINARY_OWNER_NOT_UNIQUE")
        original={
            owner:jar.read(owner+".class")
            for owner in original_class_hashes
        }
    need(all(hashlib.sha256(original[owner]).hexdigest()==digest
             for owner,digest in original_class_hashes.items()),
         "R202_ORIGINAL_JVM_CLASS_SHA256_CHANGED")
    javac=shutil.which("javac")
    need(javac is not None,"R202_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r202-private-") as td:
        root=Path(td)
        java=[]
        for relative,data in sources:
            path=root/"source"/relative
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
            java.append(str(path))
        empty=root/"empty"
        output=root/"classes"
        empty.mkdir();output.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            done=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(output),*java],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=90,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R202OriginalCallbackError(
                "R202_SOURCE_ONLY_JAVA9_BUILD_FAILED") from exc
        emitted={x.relative_to(output).as_posix()
                 for x in output.rglob("*.class")}
        need(done.returncode==0 and
             emitted=={owner+".class" for owner in original_class_hashes},
             "R202_NEW_BINARY_DEPENDENCY_OR_COMPILER_FAILURE")
        rebuilt={
            owner:(output/(owner+".class")).read_bytes()
            for owner in original_class_hashes
        }
    total=0
    results={}
    for owner in original_class_hashes:
        left=parse_class(original[owner])
        right=parse_class(rebuilt[owner])
        need((left.name,left.super_name,left.major,left.minor,
              left.access,left.interfaces)==
             (right.name,right.super_name,right.major,right.minor,
              right.access,right.interfaces) and
             left.name==owner and
             left.super_name=="java/lang/Object" and
             left.major==53 and
             len(left.fields)==len(right.fields)==expected_fields[owner] and
             len(left.methods)==len(right.methods)==expected_methods[owner] and
             _member_abi(left)==_member_abi(right),
             "R202_ORIGINAL_INTERFACE_OR_SCHEDULER_ABI_CHANGED")
        result={
            "original_owner":owner,
            "field_declarations_verified":len(left.fields),
            "method_declarations_verified":len(left.methods),
            "abstract_method_signatures_verified":
                (left.access&0x0200)!=0,
            "original_bytecode_instructions_verified":0,
            "original_stackmap_encoding_identity_claimed":False,
        }
        if owner.endswith("/c"):
            original_profile=profile_class_field_accesses(original[owner])
            rebuilt_profile=profile_class_field_accesses(rebuilt[owner])
            identities=sorted(
                (m["name"],m["descriptor"])
                for m in original_profile["methods"])
            try:
                parity=_strict_inspections(
                    original_profile,rebuilt_profile,
                    selected=identities)
            except ValueError as exc:
                raise R202OriginalCallbackError(
                    "R202_ORIGINAL_CALLBACK_JVM_CODE_CHANGED") from exc
            need(parity["verified_selected_method_count"]==
                 expected_methods[owner] and
                 parity["matched_opcode_count"]==
                 expected_scheduler_instructions and
                 parity["all_selected_core_method_code_equal"],
                 "R202_ORIGINAL_CALLBACK_121_JVM_INSTRUCTIONS_NOT_PROVEN")
            result["original_bytecode_instructions_verified"] = (
                parity["matched_opcode_count"])
            result["original_stackmap_encoding_equal"] = (
                parity["all_selected_stackmap_representations_equal"])
            total+=parity["matched_opcode_count"]
        results[owner]=result
    need(total==expected_scheduler_instructions,
         "R202_ORIGINAL_SCHEDULER_INSTRUCTION_TOTAL_DRIFT")
    need(sha_file(original_jar)==original_sha256 and
         sha_file(original_callback_source_zip)==source_sha256,
         "R202_PRIVATE_ORIGINAL_INPUT_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_original_callbacks_three_java_sources_r202",
        "reconstructed_original_java_source_owners":3,
        "original_method_declarations_verified":sum(expected_methods.values()),
        "original_jvm_method_instructions_matched":total,
        "all_original_callback_field_and_method_abi_matched":True,
        "source_only_javac_release9":True,
        "original_client_jar_on_compiler_classpath":False,
        "original_callback_scheduler_executed":False,
        "entire_original_client_compiled":False,
        "original_source_redistribution_authorized":False,
        "owners":results,
    }


def compare_pinned_private_r202_javac_frontier(
        prior_1291_source_tree_zip, r202_1294_source_tree_zip, *,
        parent_sha256=PARENT_SOURCE_TREE_SHA256,
        candidate_sha256=R202_SOURCE_TREE_SHA256):
    result=compare_pinned_private_four_owner_javac(
        prior_1291_source_tree_zip,r202_1294_source_tree_zip,
        original_sha256=parent_sha256,
        candidate_sha256=candidate_sha256,
        expected_original_count=1291,
        expected_added_count=3)
    result["original_rs_h_callback_code_executed"]=False
    result["experimental_java_source_tree_only"]=True
    return result
