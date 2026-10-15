"""R185: source-only original-v309 Signlink 16 selected methods, 356 JVM ops.

This is NOT a full original class: original class has 24 methods. The
unselected run and f() bodies and static initializer are not verified; some
selected methods invoke those unverified bodies. No code is executed.
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
from .private_v309_signlink_eleven_source_r184 import (
    SELECTED_ELEVEN, ORIGINAL_OWNER, ORIGINAL_CLASS_SHA256,
    SELECTED_METHODS, verify_eleven_signlink_methods,
)

NEW_FIVE = (
    ("c","(Ljava/lang/String;)Ljava/io/DataInputStream;"),
    ("a","()V"),
    ("a","(Ljava/net/InetAddress;)V"),
    ("f","(Ljava/lang/String;)I"),
    ("c","()Ljava/lang/String;"),
)
SIXTEEN=tuple((*SELECTED_ELEVEN,*NEW_FIVE))
ORIGINAL_METHODS=24
MATCHED_INSTRUCTIONS=356
NEW_INSTRUCTIONS=209


class R185PartialOriginalSignlinkError(ValueError):
    pass


def need(ok, label):
    if not ok:
        raise R185PartialOriginalSignlinkError(label)


def verify_sixteen_original_signlink_java(
        original_jar, source_six_zip, source_eleven_zip,
        source_sixteen_zip, *,
        original_sha256=CANONICAL_V309,
        six_source_sha256,eleven_source_sha256,sixteen_source_sha256,
        original_owner=ORIGINAL_OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        selected_methods=SIXTEEN,
        original_total_methods=ORIGINAL_METHODS,
        expected_total_instructions=MATCHED_INSTRUCTIONS,
        expected_new_instructions=NEW_INSTRUCTIONS,
        previous_six_instructions=62,
        previous_eleven_instructions=147):
    need(len(selected_methods)==16 and
         len(set(selected_methods))==16 and
         set(SELECTED_ELEVEN).issubset(set(selected_methods)) and
         set(selected_methods)-set(SELECTED_ELEVEN)==set(NEW_FIVE),
         "R185_EXACT_SIXTEEN_ORIGINAL_METHOD_IDENTITIES_REQUIRED")
    need(sha_file(original_jar)==original_sha256 and
         sha_file(source_six_zip)==six_source_sha256 and
         sha_file(source_eleven_zip)==eleven_source_sha256 and
         sha_file(source_sixteen_zip)==sixteen_source_sha256,
         "R185_EXACT_FOUR_PRIVATE_SHA256_INPUTS_REQUIRED")

    prior=verify_eleven_signlink_methods(
        original_jar,source_six_zip,source_eleven_zip,
        original_sha256=original_sha256,
        previous_six_sha256=six_source_sha256,
        eleven_source_sha256=eleven_source_sha256,
        original_owner=original_owner,
        original_class_sha256=original_class_sha256,
        expected_original_methods=original_total_methods,
        expected_instructions=previous_eleven_instructions,
        expected_new_instructions=
            previous_eleven_instructions-previous_six_instructions,
        expected_previous_instructions=previous_six_instructions)
    need(prior["selected_original_method_bodies_verified"]==11,
         "R185_R184_ELEVEN_PRIOR_METHODS_NOT_VERIFIED")
    source=source_members(source_sixteen_zip,sixteen_source_sha256)
    need(len(source)==1 and
         source[0][0]==original_owner+".java" and
         0<len(source[0][1])<=100_000,
         "R185_ONE_PRIVATE_ORIGINAL_NAMED_JAVA_FILE_REQUIRED")
    with ZipFile(original_jar) as archive:
        path=original_owner+".class"
        need(archive.namelist().count(path)==1,
             "R185_ORIGINAL_CLASS_OWNER_NOT_UNIQUE")
        original_bytes=archive.read(path)
    need(hashlib.sha256(original_bytes).hexdigest()==
         original_class_sha256,
         "R185_ORIGINAL_CLASSFILE_SHA_CHANGED")
    original=parse_class(original_bytes)
    need(original.name==original_owner and
         original.super_name=="java/lang/Object" and
         original.major==53 and
         len(original.methods)==original_total_methods,
         "R185_ORIGINAL_FULL_CLASS_INVENTORY_CHANGED")
    javac=shutil.which("javac")
    need(javac is not None,"R185_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r185-private-") as d:
        root=Path(d)
        src=root/"src"/source[0][0]
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_bytes(source[0][1])
        empty=root/"empty"
        out=root/"classes"
        empty.mkdir();out.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            compiled=subprocess.run(
                [javac,"--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),str(src)],
                stdin=subprocess.DEVNULL,
                cwd=root,env=env,capture_output=True,
                timeout=120,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R185PartialOriginalSignlinkError(
                "R185_JAVA9_SOURCE_ONLY_BUILD_ABORTED") from exc
        created={p.relative_to(out).as_posix() for p in out.rglob("*.class")}
        need(compiled.returncode==0 and
             created=={original_owner+".class"},
             "R185_PRIVATE_SOURCE_JAVA9_BUILD_NOT_CLOSED")
        rebuilt_bytes=(out/(original_owner+".class")).read_bytes()
    rebuilt=parse_class(rebuilt_bytes)
    need((original.name,original.super_name,original.access,
          original.major,original.interfaces)==
         (rebuilt.name,rebuilt.super_name,rebuilt.access,
          rebuilt.major,rebuilt.interfaces),
         "R185_SELECTED_SOURCE_OWNER_HEADER_CHANGED")
    left=profile_class_field_accesses(original_bytes)
    right=profile_class_field_accesses(rebuilt_bytes)
    members=lambda c:{(x["name"],x["descriptor"]) for x in c["methods"]}
    need(set(selected_methods).issubset(members(left)) and
         set(selected_methods).issubset(members(right)),
         "R185_SELECTED_JVM_METHOD_MISSING")
    try:
        matched=_strict_inspections(
            left,right,selected=sorted(selected_methods))
    except ValueError as exc:
        raise R185PartialOriginalSignlinkError(
            "R185_ORIGINAL_JVM_CODE_NOT_EQUAL") from exc
    need(matched["verified_selected_method_count"]==16 and
         matched["matched_opcode_count"]==expected_total_instructions and
         expected_total_instructions-previous_eleven_instructions==
            expected_new_instructions and
         matched["all_selected_core_method_code_equal"],
         "R185_ALL_SIXTEEN_METHOD_BODIES_NOT_PROVEN")
    need(sha_file(original_jar)==original_sha256 and
         sha_file(source_six_zip)==six_source_sha256 and
         sha_file(source_eleven_zip)==eleven_source_sha256 and
         sha_file(source_sixteen_zip)==sixteen_source_sha256,
         "R185_SHA_PINNED_INPUT_CHANGED_DURING_VERIFICATION")
    return {
        "schema_version":1,
        "kind":"v309_original_signlink_16_selected_java_source_r185",
        "original_signlink_class_sha256":original_class_sha256,
        "selected_original_methods_verified":16,
        "matched_original_jvm_instructions":expected_total_instructions,
        "new_selected_original_methods_verified":5,
        "new_original_jvm_instructions":expected_new_instructions,
        "original_class_total_methods":original_total_methods,
        "original_methods_not_yet_verified":original_total_methods-16,
        "selected_method_core_code_matches":True,
        "selected_stackmap_representation_matches":
            matched["all_selected_stackmap_representations_equal"],
        "original_full_class_fields_verified":False,
        "all_original_method_attributes_verified":False,
        "selected_method_self_call_closure_verified":False,
        "unselected_f_noarg_compiler_placeholder_verified":False,
        "unselected_run_compiler_placeholder_verified":False,
        "full_original_signlink_class_recovered":False,
        "partial_source_added_to_canonical_tree":False,
        "original_game_binary_executed":False,
        "full_v309_client_build_passed":False,
        "source_redistribution_authorized":False,
    }
