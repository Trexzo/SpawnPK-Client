"""R195 — original v309 Windows machine-installation identifier Java.

Recover ALL SEVEN original rs/secure/c JVM methods (334 instructions) by
compiling exact original-named Java with a single, explicitly NONORIGINAL
compiler-only rs/v/a signature declaration. This fake declaration is never
accepted as recovered original client source and NEVER enters private
canonical source overlay; source-only integrated build uses the real rs/v/a.

No recovered command handler is executed (cmd/systeminfo/PowerShell).
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

OWNER="rs/secure/c"
ORIGINAL_CLASS_SHA256=(
    "be5a4f8bd5b953f1160c7608cd626d81393bba9c53adf94233d35af53203005f"
)
ORIGINAL_JAVA_ZIP_SHA256=(
    "eeb0ea82c015ef1f8a8bc6e355c0fe1b9f3b05b06dfe70514810a7ea7432b4c5"
)
NOT_ORIGINAL_COMPILER_HELPER_ZIP_SHA256=(
    "dfe2aa4c70719c2c7d118cb0ac98a19298c585fdd676a7f4f148f6ac9618cf17"
)
EXPECTED_METHODS=7
EXPECTED_INSTRUCTIONS=334
EXPECTED_FIELDS=4
PRIOR_SIX_JAVA_TREE_SHA256=(
    "dc5a23e63c03506093b21ffc4ab013a14fcbd21f70c847c688c9441b2b8d1b65"
)
SEVEN_JAVA_TREE_SHA256=(
    "99b852851b198d526596c9feb43a41572bf8519ad40245b2e7a221255c22a9a9"
)


class R195OriginalWindowsIdentifierError(ValueError):
    pass


def need(ok,message):
    if not ok:
        raise R195OriginalWindowsIdentifierError(message)


def verify_pinned_original_windows_identifier_source(
        original_jar,original_named_windows_java_zip,
        compiler_only_outer_signature_zip, *,
        original_sha256=CANONICAL_V309,
        source_sha256=ORIGINAL_JAVA_ZIP_SHA256,
        compiler_only_signature_sha256=
            NOT_ORIGINAL_COMPILER_HELPER_ZIP_SHA256,
        original_owner=OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        expected_methods=EXPECTED_METHODS,
        expected_instructions=EXPECTED_INSTRUCTIONS,
        expected_fields=EXPECTED_FIELDS,
        helper_owner="rs/v/a"):
    """Fail closed unless all method Code+field declarations match v309."""
    input_pins=(
        (original_jar,original_sha256),
        (original_named_windows_java_zip,source_sha256),
        (compiler_only_outer_signature_zip,compiler_only_signature_sha256),
    )
    need(all(sha_file(f)==sha for f,sha in input_pins),
         "R195_PRIVATE_ORIGINAL_CLASS_SOURCE_SHA_MISMATCH")
    sources=source_members(original_named_windows_java_zip,source_sha256)
    helpers=source_members(compiler_only_outer_signature_zip,
                           compiler_only_signature_sha256)
    need(len(sources)==1 and
         sources[0][0]==original_owner+".java" and
         0<len(sources[0][1])<=130_000 and
         len(helpers)==1 and helpers[0][0]==helper_owner+".java" and
         0<len(helpers[0][1])<=20_000 and
         original_owner!=helper_owner,
         "R195_ONLY_ONE_ORIGINAL_SOURCE_AND_ONE_FAKE_SIGNATURE")
    with ZipFile(original_jar) as jar:
        path=original_owner+".class"
        need(jar.namelist().count(path)==1,
             "R195_ORIGINAL_JVM_CLASSFILE_NOT_UNIQUE")
        original_bytes=jar.read(path)
    need(hashlib.sha256(original_bytes).hexdigest()==
         original_class_sha256,
         "R195_ORIGINAL_WINDOWS_CLASS_SHA256_DRIFT")
    old=parse_class(original_bytes)
    need(old.name==original_owner and
         old.super_name=="java/lang/Object" and
         old.major==53 and old.minor==0 and
         len(old.methods)==expected_methods and
         len(old.fields)==expected_fields,
         "R195_ORIGINAL_WINDOWS_OWNER_OR_MEMBER_INVENTORY_CHANGED")
    javac=shutil.which("javac")
    need(javac is not None,"R195_JDK_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r195-source-") as td:
        root=Path(td)
        files=[]
        for rel,body in [*sources,*helpers]:
            dest=root/"src"/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(body)
            files.append(str(dest))
        out=root/"classes"
        empty=root/"empty"
        out.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            built=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),*files],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=100,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R195OriginalWindowsIdentifierError(
                "R195_PRIVATE_SOURCE_ONLY_BUILD_ABORTED") from exc
        classes={x.relative_to(out).as_posix()
                 for x in out.rglob("*.class")}
        need(built.returncode==0 and classes=={
             original_owner+".class",helper_owner+".class"},
             "R195_ONLY_SOURCE_ORIGINAL_OWNER_AND_FAKE_HELPER_ALLOWED")
        new_bytes=(out/(original_owner+".class")).read_bytes()
    new=parse_class(new_bytes)
    need((old.name,old.super_name,old.major,old.minor,
          old.access,old.interfaces)==
         (new.name,new.super_name,new.major,new.minor,
          new.access,new.interfaces),
         "R195_ORIGINAL_CLASS_HEADER_CHANGED")
    fields=lambda c:sorted(
        (f["name"],f["descriptor"],f["access"]) for f in c.fields)
    need(fields(old)==fields(new),
         "R195_ORIGINAL_FOUR_FIELD_DECLARATION_ABI_CHANGED")
    before=profile_class_field_accesses(original_bytes)
    after=profile_class_field_accesses(new_bytes)
    ids=lambda p:{(m["name"],m["descriptor"]) for m in p["methods"]}
    methods=sorted(ids(before))
    need(len(methods)==expected_methods and ids(before)==ids(after),
         "R195_NOT_ALL_SEVEN_ORIGINAL_JVM_METHODS_REBUILT")
    try:
        matched=_strict_inspections(before,after,selected=methods)
    except ValueError as exc:
        raise R195OriginalWindowsIdentifierError(
            "R195_WINDOWS_INSTALLATION_JVM_CODE_MISMATCH") from exc
    need(matched["verified_selected_method_count"]==expected_methods and
         matched["matched_opcode_count"]==expected_instructions and
         matched["all_selected_core_method_code_equal"],
         "R195_NOT_ALL_334_JVM_INSTRUCTIONS_MATCH")
    need(all(sha_file(f)==sha for f,sha in input_pins),
         "R195_PRIVATE_SOURCE_OR_BINARY_CHANGED_DURING_VERIFICATION")
    return {
        "schema_version":1,
        "kind":"v309_original_windows_install_identifier_java_r195",
        "original_jvm_owner":original_owner,
        "original_class_sha256":original_class_sha256,
        "original_methods_compiled_and_matched":expected_methods,
        "original_jvm_instructions_matched":expected_instructions,
        "original_field_header_and_method_abi_matched":True,
        "original_control_flow_and_exception_handlers_matched":True,
        "stackmap_representation_equal":
            matched["all_selected_stackmap_representations_equal"],
        "compiler_only_signature_source_is_original":False,
        "original_systeminfo_or_powershell_command_executed":False,
        "original_client_code_executed":False,
        "complete_client_compiled":False,
        "original_source_published":False,
        "derived_source_redistribution_authorized":False,
    }


def measure_pinned_seven_original_java_owner_frontier(
        prior_six_owner_tree_zip,original_windows_java_zip,
        fresh_seven_owner_tree_zip, *,
        old_tree_sha256=PRIOR_SIX_JAVA_TREE_SHA256,
        source_sha256=ORIGINAL_JAVA_ZIP_SHA256,
        new_tree_sha256=SEVEN_JAVA_TREE_SHA256,
        old_java_count=1284):
    """No original binary or fake compiler helper in the private tree."""
    result=build_private_four_owner_overlay(
        prior_six_owner_tree_zip,[original_windows_java_zip],
        fresh_seven_owner_tree_zip,
        baseline_sha256=old_tree_sha256,
        source_identities=((OWNER+".java",source_sha256),),
        expected_baseline_java=old_java_count)
    need(result["baseline_java_files_exactly_preserved"]==
         old_java_count and
         result["new_overlay_zip_sha256"]==new_tree_sha256,
         "R195_PRIVATE_1285_JAVA_OVERLAY_SHA_DRIFT")
    report=compare_pinned_private_four_owner_javac(
        prior_six_owner_tree_zip,fresh_seven_owner_tree_zip,
        original_sha256=old_tree_sha256,
        candidate_sha256=new_tree_sha256,
        expected_original_count=old_java_count,
        expected_added_count=1)
    report["original_system_commands_executed"]=False
    report["invented_compiler_helpers_in_original_source_tree"]=False
    return report
