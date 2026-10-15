"""R193: reconstruct real v309 rs/secure/b Java, not a helper declaration.

Private original client ZIP plus one source-only Java owner are SHA-pinned.
This verifier compiles the original Java owner under isolated --release 9
without the original client, external classfiles, or source fallback. All
three methods (including the macOS system_profiler IO/try/finally routine)
must match the original resolved JVM Code, exception table and field ABI.

Verification NEVER invokes the recovered identifier lookup, which launches
an external system command. Original Java and client binaries stay private.
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
    build_private_four_owner_overlay,
    compare_pinned_private_four_owner_javac,
)

OWNER="rs/secure/b"
ORIGINAL_CLASS_SHA256=(
    "e2c302760621fce745f13619ad7ac079d0bd9dac40444573c64ca45793f0a61b"
)
PRIVATE_SOURCE_ZIP_SHA256=(
    "41470de78250b7a5bdf06aba9e77187ab4cec95fed422e0b05e630f6096e7282"
)
ORIGINAL_METHODS=3
ORIGINAL_INSTRUCTIONS=112
ORIGINAL_FIELDS=1
FOUR_OWNER_TREE_SHA256=(
    "d5e522ef9f7573b4e6009eb8fffee561767608b19a996791de4af8fe4c57c47b"
)
FIVE_OWNER_TREE_SHA256=(
    "7ec20525e1e2a51c78199102b46c54bd5b2ae9c0a9cd40783473d21a975e9eab"
)


class R193OriginalMacOSSerialSourceError(ValueError):
    pass


def need(condition,reason):
    if not condition:
        raise R193OriginalMacOSSerialSourceError(reason)


def verify_pinned_original_macos_serial_java(
        original_jar, original_source_zip, *,
        original_sha256=CANONICAL_V309,
        source_sha256=PRIVATE_SOURCE_ZIP_SHA256,
        original_owner=OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        expected_methods=ORIGINAL_METHODS,
        expected_instructions=ORIGINAL_INSTRUCTIONS,
        expected_fields=ORIGINAL_FIELDS):
    need(sha_file(original_jar)==original_sha256 and
         sha_file(original_source_zip)==source_sha256,
         "R193_ORIGINAL_JAR_OR_JAVA_SOURCE_PIN_MISMATCH")
    source=source_members(original_source_zip,source_sha256)
    need(len(source)==1 and
         source[0][0]==original_owner+".java" and
         0<len(source[0][1])<100_000,
         "R193_EXACT_ORIGINAL_NAMED_JAVA_OWNER_REQUIRED")
    with ZipFile(original_jar) as archive:
        path=original_owner+".class"
        need(archive.namelist().count(path)==1,
             "R193_ORIGINAL_CLASSFILE_NOT_UNIQUE")
        original_bytes=archive.read(path)
    need(hashlib.sha256(original_bytes).hexdigest()==original_class_sha256,
         "R193_ORIGINAL_CLASSFILE_SHA_CHANGED")
    original=parse_class(original_bytes)
    need(original.name==original_owner and
         original.super_name=="java/lang/Object" and
         original.major==53 and
         original.minor==0 and
         len(original.fields)==expected_fields and
         len(original.methods)==expected_methods,
         "R193_ORIGINAL_CLASS_INVENTORY_CHANGED")
    javac=shutil.which("javac")
    need(javac is not None,"R193_JDK_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r193-source-") as folder:
        root=Path(folder)
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
            compiled=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),str(src)],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=90,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R193OriginalMacOSSerialSourceError(
                "R193_SOURCE_ONLY_COMPILATION_ABORTED") from exc
        emitted={x.relative_to(out).as_posix()
                 for x in out.rglob("*.class")}
        need(compiled.returncode==0 and
             emitted=={original_owner+".class"},
             "R193_ONE_ORIGINAL_CLASS_SOURCE_ONLY_BUILD_REQUIRED")
        candidate_bytes=(out/(original_owner+".class")).read_bytes()
    candidate=parse_class(candidate_bytes)
    need((original.name,original.super_name,original.access,
          original.major,original.minor,original.interfaces)==
         (candidate.name,candidate.super_name,candidate.access,
          candidate.major,candidate.minor,candidate.interfaces),
         "R193_CLASS_HEADER_MISMATCH")
    fields=lambda c:sorted(
        (f["name"],f["descriptor"],f["access"]) for f in c.fields)
    need(fields(original)==fields(candidate),
         "R193_ORIGINAL_FIELD_ACCESS_OR_DESCRIPTOR_CHANGED")
    before=profile_class_field_accesses(original_bytes)
    after=profile_class_field_accesses(candidate_bytes)
    identities=lambda p:{(m["name"],m["descriptor"])
                         for m in p["methods"]}
    methods=sorted(identities(before))
    need(len(methods)==expected_methods and
         identities(before)==identities(after),
         "R193_FULL_ORIGINAL_JVM_METHOD_INVENTORY_NOT_PRESERVED")
    try:
        parity=_strict_inspections(before,after,selected=methods)
    except ValueError as exc:
        raise R193OriginalMacOSSerialSourceError(
            "R193_ORIGINAL_MACOS_JVM_CODE_NOT_EQUAL") from exc
    need(parity["verified_selected_method_count"]==expected_methods
         and parity["matched_opcode_count"]==expected_instructions
         and parity["all_selected_core_method_code_equal"],
         "R193_NOT_ALL_ORIGINAL_MACOS_METHODS_MATCH")
    need(sha_file(original_jar)==original_sha256 and
         sha_file(original_source_zip)==source_sha256,
         "R193_ORIGINAL_OR_JAVA_SOURCE_CHANGED_DURING_BUILD")
    return {
        "schema_version":1,
        "kind":"v309_original_macos_serial_full_java_source_r193",
        "original_class_sha256":original_class_sha256,
        "original_private_java_zip_sha256":source_sha256,
        "full_original_method_count_compiled":expected_methods,
        "full_original_jvm_instructions_matched":expected_instructions,
        "original_field_abi_and_class_header_match":True,
        "original_exception_handlers_and_control_flow_match":True,
        "original_stackmap_representation_matches":
            parity["all_selected_stackmap_representations_equal"],
        "source_only_javac_no_binary_fallback":True,
        "original_system_profiler_or_game_code_executed":False,
        "original_classfile_byte_identity_claimed":
            original_bytes==candidate_bytes,
        "whole_v309_client_compiles":False,
        "original_java_source_published":False,
        "redistribution_authorized":False,
    }


def measure_pinned_five_original_owner_frontier(
        previous_four_owner_zip,macos_original_java_zip,
        fresh_output_zip, *, old_source_sha256=FOUR_OWNER_TREE_SHA256,
        macos_source_sha256=PRIVATE_SOURCE_ZIP_SHA256,
        expected_new_zip_sha256=FIVE_OWNER_TREE_SHA256,
        old_java_count=1282):
    """Actual private old/new javac diagnostics, no fake helper source."""
    result=build_private_four_owner_overlay(
        previous_four_owner_zip,[macos_original_java_zip],fresh_output_zip,
        baseline_sha256=old_source_sha256,
        source_identities=((OWNER+".java",macos_source_sha256),),
        expected_baseline_java=old_java_count)
    need(result["new_overlay_zip_sha256"]==expected_new_zip_sha256,
         "R193_EXACT_FIVE_OWNER_PRIVATE_OVERLAY_SHA_CHANGED")
    measured=compare_pinned_private_four_owner_javac(
        previous_four_owner_zip,fresh_output_zip,
        original_sha256=old_source_sha256,
        candidate_sha256=expected_new_zip_sha256,
        expected_original_count=old_java_count,expected_added_count=1)
    measured["source_only_mac_serial_integration"]=True
    measured["original_macos_system_command_executed"]=False
    return measured
