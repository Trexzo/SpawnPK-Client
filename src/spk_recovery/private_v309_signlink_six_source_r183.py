"""R183 — original-v309 Signlink/bridge selected Java method source recovery.

Recompile one original-named partial Java candidate with an EMPTY original
and external classpath, and strictly compare only six selected JVM methods.
The original class has unverified methods, fields, dependencies and runtime
behavior. Its partial Java source MUST NOT be canonicalized as full source.
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


ORIGINAL_OWNER = "rs/v/a"
ORIGINAL_CLASS_SHA256 = "d0dc35deddc8016c3fdcaf2615810efa200c042120b83bed86cad5d04b1c0ddc"
SELECTED_METHODS = (
    ("<init>", "()V"),
    ("a", "(Ljava/lang/Runnable;I)V"),
    ("a", "(Ljava/lang/String;)Z"),
    ("b", "(Ljava/lang/String;)Z"),
    ("d", "(Ljava/lang/String;)V"),
    ("i", "()Z"),
)
EXPECTED_SELECTED_INSTRUCTIONS = 62
EXPECTED_ORIGINAL_METHODS = 24


class R183OriginalSignlinkPartialSourceError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise R183OriginalSignlinkPartialSourceError(reason)


def verify_six_original_signlink_methods(
        original_jar, partial_source_zip, *,
        original_sha256=CANONICAL_V309,
        partial_source_sha256,
        original_owner=ORIGINAL_OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        selected_methods=SELECTED_METHODS,
        expected_original_methods=EXPECTED_ORIGINAL_METHODS,
        expected_selected_instructions=EXPECTED_SELECTED_INSTRUCTIONS,
        expected_major=53):
    require(re.fullmatch(
        r"[A-Za-z_$][A-Za-z0-9_$]*(?:/[A-Za-z_$][A-Za-z0-9_$]*)+",
        original_owner) is not None and
        len(selected_methods)==6 and
        len(set(selected_methods))==6 and
        ("<init>","()V") in selected_methods and
        expected_original_methods>=6 and
        expected_selected_instructions>0,
        "R183_SELECTED_ORIGINAL_METHOD_IDENTITIES_INVALID")
    require(sha_file(original_jar)==original_sha256 and
            sha_file(partial_source_zip)==partial_source_sha256,
            "R183_EXACT_ORIGINAL_AND_SOURCE_ARCHIVE_PINS_REQUIRED")
    source=source_members(partial_source_zip,partial_source_sha256)
    require(len(source)==1 and
            source[0][0]==original_owner+".java" and
            0<len(source[0][1])<=100_000,
            "R183_ONLY_ONE_ORIGINAL_NAMED_PARTIAL_JAVA_SOURCE")
    with ZipFile(original_jar) as jar:
        path=original_owner+".class"
        require(jar.namelist().count(path)==1,
                "R183_ORIGINAL_OWNER_NOT_UNIQUE")
        original_bytes=jar.read(path)
    require(hashlib.sha256(original_bytes).hexdigest()==
            original_class_sha256,
            "R183_ORIGINAL_SIGNLINK_CLASS_SHA_MISMATCH")
    original=parse_class(original_bytes)
    require(original.name==original_owner and
            original.super_name=="java/lang/Object" and
            original.major==expected_major and
            len(original.methods)==expected_original_methods,
            "R183_ORIGINAL_FULL_CLASS_INVENTORY_CHANGED")
    javac=shutil.which("javac")
    require(javac is not None,"R183_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r183-source-") as td:
        root=Path(td)
        src=root/"src"/source[0][0]
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_bytes(source[0][1])
        out=root/"built"
        empty=root/"empty"
        out.mkdir()
        empty.mkdir()
        env=os.environ.copy()
        for k in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                  "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(k,None)
        try:
            proc=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),str(src),
            ],cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=90,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R183OriginalSignlinkPartialSourceError(
                "R183_SOURCE_ONLY_JAVAC_FAILED_TO_COMPLETE") from exc
        classes={x.relative_to(out).as_posix()
                 for x in out.rglob("*.class")}
        require(proc.returncode==0 and
                classes=={original_owner+".class"},
                "R183_PARTIAL_JAVA_REBUILD_NOT_SOURCE_ONLY_CLOSED")
        rebuilt_bytes=(out/(original_owner+".class")).read_bytes()
    rebuilt=parse_class(rebuilt_bytes)
    require((original.name,original.super_name,original.access,
             original.major,original.interfaces)==
            (rebuilt.name,rebuilt.super_name,rebuilt.access,
             rebuilt.major,rebuilt.interfaces),
            "R183_ORIGINAL_SIGNLINK_CLASS_HEADER_CHANGED")
    baseline=profile_class_field_accesses(original_bytes)
    updated=profile_class_field_accesses(rebuilt_bytes)
    method_set=lambda x:{(m["name"],m["descriptor"]) for m in x["methods"]}
    require(set(selected_methods).issubset(method_set(baseline)) and
            set(selected_methods).issubset(method_set(updated)),
            "R183_ALL_SIX_SELECTED_ORIGINAL_METHODS_REQUIRED")
    try:
        proof=_strict_inspections(
            baseline,updated,selected=sorted(selected_methods))
    except ValueError as exc:
        raise R183OriginalSignlinkPartialSourceError(
            "R183_SELECTED_ORIGINAL_JVM_CODE_MISMATCH") from exc
    require(proof["verified_selected_method_count"]==6 and
            proof["matched_opcode_count"]==expected_selected_instructions and
            proof["all_selected_core_method_code_equal"],
            "R183_SIX_ORIGINAL_METHODS_NOT_IDENTICAL")
    require(sha_file(original_jar)==original_sha256 and
            sha_file(partial_source_zip)==partial_source_sha256,
            "R183_INPUTS_CHANGED_DURING_SOURCE_VERIFICATION")
    return {
        "schema_version":1,
        "kind":"v309_original_signlink_six_partial_java_methods_r183",
        "original_class_sha256":original_class_sha256,
        "private_source_sha256":partial_source_sha256,
        "selected_original_methods_verified":6,
        "matched_original_jvm_instructions":expected_selected_instructions,
        "original_total_method_count":len(original.methods),
        "remaining_original_method_implementations_not_verified":
            expected_original_methods-6,
        "selected_methods_complete_original_jvm_code_match":True,
        "source_only_compilation_no_original_binary_fallback":True,
        "original_full_class_field_abi_verified":False,
        "full_original_signlink_java_source_recovered":False,
        "original_partial_source_installed_canonically":False,
        "entire_original_client_compiles":False,
        "original_runtime_networking_executed":False,
        "derived_source_publication_authorized":False,
    }
