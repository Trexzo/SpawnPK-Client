"""R186: strict private original-v309 rs/v/a selected Java 21/24 parity.

The 5 newly reconstructed Java methods reference 6 compiler-only declaration
helpers. These are not original-recovered classes and no helper bytes are
accepted as original evidence. Does NOT execute original networking code,
verify runtime, publish source, or integrate partial owner into canonical tree.
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
from .private_v309_signlink_sixteen_source_r185 import (
    SIXTEEN, ORIGINAL_OWNER, ORIGINAL_CLASS_SHA256,
    verify_sixteen_original_signlink_java,
)


NEW_FIVE = (
    ("b","()Ljava/lang/String;"),
    ("f","()Ljava/lang/String;"),
    ("d","()Z"),
    ("e","()Ljava/lang/String;"),
    ("a","(D)V"),
)
TWENTYONE=tuple((*SIXTEEN,*NEW_FIVE))
HELPER_OWNERS=(
    "rs/f/a", "rs/k/j", "rs/secure/a",
    "rs/secure/b", "rs/secure/c", "rs/w/c",
)
EXPECTED_MATCHED_INSTRUCTIONS=469
EXPECTED_ADDED_INSTRUCTIONS=113
EXPECTED_ORIGINAL_METHODS=24


class R186OriginalSignlinkTwentyOneSourceError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise R186OriginalSignlinkTwentyOneSourceError(message)


def verify_21_original_signlink_methods(
        original_jar, previous_six_zip, previous_eleven_zip,
        previous_sixteen_zip, source_21_zip, compiler_helper_zip, *,
        original_sha256=CANONICAL_V309,
        six_source_sha256,eleven_source_sha256,sixteen_source_sha256,
        source_21_sha256,compiler_helper_sha256,
        original_owner=ORIGINAL_OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        selected_methods=TWENTYONE,
        expected_total_instructions=EXPECTED_MATCHED_INSTRUCTIONS,
        expected_added_instructions=EXPECTED_ADDED_INSTRUCTIONS,
        expected_original_methods=EXPECTED_ORIGINAL_METHODS,
        six_previous_instructions=62,
        eleven_previous_instructions=147,
        sixteen_previous_instructions=356):
    need(len(selected_methods)==21 and
         len(set(selected_methods))==21 and
         set(SIXTEEN).issubset(set(selected_methods)) and
         set(selected_methods)-set(SIXTEEN)==set(NEW_FIVE) and
         expected_added_instructions ==
             expected_total_instructions-sixteen_previous_instructions,
         "R186_EXACT_TWENTYONE_METHODS_REQUIRED")
    archives=(
        (original_jar,original_sha256),
        (previous_six_zip,six_source_sha256),
        (previous_eleven_zip,eleven_source_sha256),
        (previous_sixteen_zip,sixteen_source_sha256),
        (source_21_zip,source_21_sha256),
        (compiler_helper_zip,compiler_helper_sha256),
    )
    need(all(sha_file(path)==digest for path,digest in archives),
         "R186_SHA_PINNED_ORIGINAL_OR_PRIVATE_SOURCE_CHANGED")
    prior=verify_sixteen_original_signlink_java(
        original_jar,previous_six_zip,previous_eleven_zip,
        previous_sixteen_zip,original_sha256=original_sha256,
        six_source_sha256=six_source_sha256,
        eleven_source_sha256=eleven_source_sha256,
        sixteen_source_sha256=sixteen_source_sha256,
        original_owner=original_owner,
        original_class_sha256=original_class_sha256,
        original_total_methods=expected_original_methods,
        previous_six_instructions=six_previous_instructions,
        previous_eleven_instructions=eleven_previous_instructions,
        expected_total_instructions=sixteen_previous_instructions,
        expected_new_instructions=
            sixteen_previous_instructions-eleven_previous_instructions)
    need(prior["selected_original_methods_verified"]==16,
         "R186_SIXTEEN_ORIGINAL_METHODS_NOT_VERIFIED")
    candidates=source_members(source_21_zip,source_21_sha256)
    need(len(candidates)==1 and
         candidates[0][0]==original_owner+".java" and
         0<len(candidates[0][1])<=150_000,
         "R186_ONE_ORIGINAL_NAMED_PARTIAL_CLASS_REQUIRED")
    helpers=source_members(compiler_helper_zip,compiler_helper_sha256)
    need(len(helpers)==len(HELPER_OWNERS) and
         {owner for owner,_ in helpers}==
             {o+".java" for o in HELPER_OWNERS} and
         sum(len(data) for _,data in helpers)<=50_000 and
         original_owner+".java" not in dict(helpers),
         "R186_ONLY_SIX_COMPILER_DECLARATION_HELPERS_ALLOWED")
    with ZipFile(original_jar) as original_archive:
        name=original_owner+".class"
        need(original_archive.namelist().count(name)==1,
             "R186_ORIGINAL_CLASSFILE_NOT_UNIQUE")
        original_binary=original_archive.read(name)
    need(hashlib.sha256(original_binary).hexdigest()==original_class_sha256,
         "R186_ORIGINAL_CLASSFILE_SHA_CHANGED")
    original=parse_class(original_binary)
    need(original.name==original_owner and
         original.super_name=="java/lang/Object" and
         original.major==53 and
         len(original.methods)==expected_original_methods,
         "R186_ORIGINAL_FULL_JVM_METHOD_INVENTORY_CHANGED")
    javac=shutil.which("javac")
    need(javac is not None,"R186_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r186-private-") as tmp:
        base=Path(tmp)
        srcroot=base/"source"
        files=[]
        for owner,data in [*candidates,*helpers]:
            dest=srcroot/owner
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(data)
            files.append(str(dest))
        empty=base/"empty"
        output=base/"classes"
        empty.mkdir();output.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            outcome=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(output),
                *files,
            ],cwd=base,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=120,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R186OriginalSignlinkTwentyOneSourceError(
                "R186_JAVA9_REBUILD_DID_NOT_COMPLETE") from exc
        classes={f.relative_to(output).as_posix()
                 for f in output.rglob("*.class")}
        need(outcome.returncode==0 and
             classes=={original_owner+".class"} |
             {o+".class" for o in HELPER_OWNERS},
             "R186_SOURCE_ONLY_OWNER_AND_DECLARATION_HELPERS_REQUIRED")
        rebuilt_binary=(output/(original_owner+".class")).read_bytes()
    rebuilt=parse_class(rebuilt_binary)
    need((original.name,original.super_name,original.access,
          original.major,original.interfaces)==
         (rebuilt.name,rebuilt.super_name,rebuilt.access,
          rebuilt.major,rebuilt.interfaces),
         "R186_OWNER_CLASS_HEADER_CHANGED")
    before=profile_class_field_accesses(original_binary)
    after=profile_class_field_accesses(rebuilt_binary)
    available=lambda x:{(m["name"],m["descriptor"])
                        for m in x["methods"]}
    need(set(selected_methods).issubset(available(before)) and
         set(selected_methods).issubset(available(after)),
         "R186_MISSING_SELECTED_METHOD_IDENTITY")
    try:
        proof=_strict_inspections(
            before,after,selected=sorted(selected_methods))
    except ValueError as exc:
        raise R186OriginalSignlinkTwentyOneSourceError(
            "R186_SOME_ORIGINAL_SELECTED_CODE_NOT_EQUAL") from exc
    need(proof["verified_selected_method_count"]==21 and
         proof["matched_opcode_count"]==expected_total_instructions and
         proof["all_selected_core_method_code_equal"],
         "R186_NOT_ALL_TWENTYONE_METHOD_BODIES_VERIFIED")
    need(all(sha_file(path)==digest for path,digest in archives),
         "R186_PRIVATE_INPUT_CHANGED_DURING_COMPILATION")
    return {
        "schema_version":1,
        "kind":"v309_original_signlink_21_selected_java_source_r186",
        "original_class_sha256":original_class_sha256,
        "verified_selected_method_count":21,
        "matched_original_jvm_instructions":expected_total_instructions,
        "new_methods_verified":5,
        "new_jvm_instructions_matched":expected_added_instructions,
        "original_method_inventory_count":expected_original_methods,
        "original_method_bodies_still_unverified":
            expected_original_methods-21,
        "selected_core_code_matches_original":True,
        "selected_stackmap_representation_matches":
            proof["all_selected_stackmap_representations_equal"],
        "compiler_only_helpers_original_source_verified":False,
        "unverified_methods_or_source_placeholders_accepted":False,
        "full_original_field_initializer_and_method_attributes_verified":False,
        "full_original_signlink_class_reconstructed":False,
        "partial_source_integrated_in_canonical_source_tree":False,
        "whole_original_v309_client_compiles":False,
        "original_networking_or_audio_code_executed":False,
        "original_derived_source_publication_authorized":False,
    }
