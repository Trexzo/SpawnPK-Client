"""R184: original-v309 Signlink/bridge 11 selected Java methods (147 JVM ops).

Full owner still contains unverified original methods. This is strictly
partial original-code recovery, not full class acceptance, networking
execution, or canonical source-tree publication. All binary and Java inputs
are separately SHA-pinned private files. Hosted tests use synthetic Java.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file, source_members
from .private_v309_matrix_source_method_parity_r150 import _strict_inspections
from .private_v309_signlink_six_source_r183 import (
    ORIGINAL_OWNER, ORIGINAL_CLASS_SHA256, SELECTED_METHODS,
    verify_six_original_signlink_methods,
)

NEW_METHODS = (
    ("a", "(I)Ljava/net/Socket;"),
    ("a", "([BI)Z"),
    ("b", "([BI)V"),
    ("h", "()Z"),
    ("e", "(Ljava/lang/String;)V"),
)
SELECTED_ELEVEN = tuple((*SELECTED_METHODS, *NEW_METHODS))
EXPECTED_JVM_INSTRUCTIONS = 147
EXPECTED_NEW_INSTRUCTIONS = 85
EXPECTED_ORIGINAL_METHODS = 24


class R184SignlinkElevenSourceError(ValueError):
    pass


def need(value, label):
    if not value:
        raise R184SignlinkElevenSourceError(label)


def verify_eleven_signlink_methods(
        original_jar, previous_six_source_zip, eleven_source_zip, *,
        original_sha256=CANONICAL_V309,
        previous_six_sha256, eleven_source_sha256,
        original_owner=ORIGINAL_OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        selected_methods=SELECTED_ELEVEN,
        previous_six_methods=SELECTED_METHODS,
        expected_original_methods=EXPECTED_ORIGINAL_METHODS,
        expected_instructions=EXPECTED_JVM_INSTRUCTIONS,
        expected_new_instructions=EXPECTED_NEW_INSTRUCTIONS,
        expected_previous_instructions=62):
    need(len(selected_methods)==11 and
         len(set(selected_methods))==11 and
         set(previous_six_methods).issubset(set(selected_methods)) and
         len(previous_six_methods)==6 and
         set(selected_methods)-set(previous_six_methods)==set(NEW_METHODS),
         "R184_SELECTED_ELEVEN_AND_NEW_FIVE_REQUIRED")
    need(sha_file(original_jar)==original_sha256 and
         sha_file(previous_six_source_zip)==previous_six_sha256 and
         sha_file(eleven_source_zip)==eleven_source_sha256,
         "R184_PRIVATE_INPUT_SHA256_MISMATCH")

    prior=verify_six_original_signlink_methods(
        original_jar,previous_six_source_zip,
        original_sha256=original_sha256,
        partial_source_sha256=previous_six_sha256,
        original_owner=original_owner,
        original_class_sha256=original_class_sha256,
        selected_methods=previous_six_methods,
        expected_original_methods=expected_original_methods,
        expected_selected_instructions=expected_previous_instructions)
    need(prior["selected_original_methods_verified"]==6,
         "R184_R183_PREVIOUS_SIX_NOT_VERIFIED")

    source=source_members(eleven_source_zip,eleven_source_sha256)
    need(len(source)==1 and
         source[0][0]==original_owner+".java" and
         0<len(source[0][1])<=100_000,
         "R184_ONE_ORIGINAL_NAMED_PARTIAL_JAVA_FILE_REQUIRED")
    with ZipFile(original_jar) as archive:
        path=original_owner+".class"
        need(archive.namelist().count(path)==1,
             "R184_ORIGINAL_OWNER_CLASS_NOT_UNIQUE")
        original_bytes=archive.read(path)
    need(hashlib.sha256(original_bytes).hexdigest()==original_class_sha256,
         "R184_ORIGINAL_CLASS_SHA256_CHANGED")
    original=parse_class(original_bytes)
    need(original.name==original_owner and
         original.super_name=="java/lang/Object" and
         original.major==53 and
         len(original.methods)==expected_original_methods,
         "R184_ORIGINAL_CLASS_ABI_OR_METHOD_COUNT_CHANGED")
    javac=shutil.which("javac")
    need(javac is not None,"R184_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r184-source-") as temp:
        root=Path(temp)
        src=root/"source"/source[0][0]
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_bytes(source[0][1])
        out=root/"classes"
        empty=root/"empty"
        out.mkdir()
        empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            build=subprocess.run(
                [javac,"--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),str(src)],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=90,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R184SignlinkElevenSourceError(
                "R184_JAVA9_SOURCE_COMPILATION_ABORTED") from exc
        written={x.relative_to(out).as_posix() for x in out.rglob("*.class")}
        need(build.returncode==0 and
             written=={original_owner+".class"},
             "R184_SOURCE_ONLY_PARTIAL_CLASS_BUILD_NOT_CLOSED")
        rebuilt_bytes=(out/(original_owner+".class")).read_bytes()

    rebuilt=parse_class(rebuilt_bytes)
    need((original.name,original.super_name,original.access,
          original.major,original.interfaces)==
         (rebuilt.name,rebuilt.super_name,rebuilt.access,
          rebuilt.major,rebuilt.interfaces),
         "R184_ORIGINAL_CLASS_HEADER_MISMATCH")
    before=profile_class_field_accesses(original_bytes)
    after=profile_class_field_accesses(rebuilt_bytes)
    ids=lambda profile:{(m["name"],m["descriptor"])
                        for m in profile["methods"]}
    need(set(selected_methods).issubset(ids(before)) and
         set(selected_methods).issubset(ids(after)),
         "R184_SELECTED_METHODS_MISSING")
    try:
        comparison=_strict_inspections(
            before,after,selected=sorted(selected_methods))
    except ValueError as exc:
        raise R184SignlinkElevenSourceError(
            "R184_ORIGINAL_SELECTED_METHOD_CODE_NOT_EQUAL") from exc
    need(comparison["verified_selected_method_count"]==11 and
         comparison["matched_opcode_count"]==expected_instructions and
         comparison["all_selected_core_method_code_equal"] and
         expected_instructions-expected_previous_instructions==
             expected_new_instructions,
         "R184_SELECTED_METHOD_INSTRUCTION_COUNTS_DIFFER")
    need(sha_file(original_jar)==original_sha256 and
         sha_file(eleven_source_zip)==eleven_source_sha256 and
         sha_file(previous_six_source_zip)==previous_six_sha256,
         "R184_ORIGINAL_OR_PRIVATE_SOURCES_CHANGED_DURING_VERIFY")
    return {
        "schema_version":1,
        "kind":"v309_original_signlink_eleven_partial_java_methods_r184",
        "original_class_sha256":original_class_sha256,
        "previous_private_source_sha256":previous_six_sha256,
        "eleven_method_private_source_sha256":eleven_source_sha256,
        "selected_original_method_bodies_verified":11,
        "selected_original_jvm_instructions_matched":expected_instructions,
        "new_original_method_bodies_verified":5,
        "new_original_jvm_instructions_matched":expected_new_instructions,
        "original_total_method_count":expected_original_methods,
        "remaining_original_method_bodies_unverified":
            expected_original_methods-11,
        "stackmap_representation_identical":
            comparison["all_selected_stackmap_representations_equal"],
        "source_only_javac_no_original_binary_fallback":True,
        "original_full_class_fields_verified":False,
        "original_full_class_method_attributes_verified":False,
        "original_entire_signlink_source_recovered":False,
        "private_partial_source_added_to_canonical_tree":False,
        "original_game_binary_executed":False,
        "full_client_compiled":False,
        "publication_authorized":False,
    }
