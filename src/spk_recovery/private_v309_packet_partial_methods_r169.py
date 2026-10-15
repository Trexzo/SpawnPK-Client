"""R169: real v309 Packet two-method Java source recovery, NOT full Packet.

Prove only original signed-short reader B():int and float-wrapper s():float
from one privately pinned partial original-name rs/x/e Java source. r():int
is separately identified as a COMPILATION-ONLY stub and NOT recovered.
Original full Packet class ABI, superclass, behavior and source ownership are
NEVER accepted here. No original JVM binary on compiler classpath.
"""
from __future__ import annotations
import argparse
import hashlib
import json
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
from .private_v309_matrix_source_method_parity_r150 import (
    _strict_inspections,
)

ORIGINAL_PACKET_SHA = "b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2"


class R169OriginalPacketTwoMethodsError(ValueError):
    pass


def require(ok,reason):
    if not ok:
        raise R169OriginalPacketTwoMethodsError(reason)


def verify_original_packet_signed_short_and_float_wrapper(
        original_jar, private_partial_java_zip, *,
        original_sha256=CANONICAL_V309,
        partial_java_sha256,
        original_owner="rs/x/e",
        original_class_sha256=ORIGINAL_PACKET_SHA,
        signed_short_method="B",
        float_wrapper_method="s",
        delegated_unrecovered_int_method="r",
        byte_array_field="g",
        cursor_field="h",
        expected_selected_methods=2,
        expected_jvm_instructions=41):
    require(sha_file(original_jar)==original_sha256 and
            sha_file(private_partial_java_zip)==partial_java_sha256,
            "R169_EXACT_INPUT_JAR_OR_SOURCE_SHA_MISMATCH")
    names=[original_owner,*[signed_short_method,float_wrapper_method,
                              delegated_unrecovered_int_method,
                              byte_array_field,cursor_field]]
    require(re.fullmatch(
        r"[A-Za-z_$][A-Za-z0-9_$]*(?:/[A-Za-z_$][A-Za-z0-9_$]*)+",
        names[0]) and
        all(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*",name)
            for name in names[1:]) and
        len(set(names[1:4]))==3 and
        expected_selected_methods==2 and
        1<=expected_jvm_instructions<=1000,
        "R169_METHODS_OR_ORIGINAL_JVM_OWNER_INVALID")
    source=source_members(private_partial_java_zip,partial_java_sha256)
    require(len(source)==1 and
            source[0][0]==original_owner+".java" and
            0<len(source[0][1])<=100_000,
            "R169_ONE_PRIVATE_ORIGINAL_PACKET_JAVA_FILE_REQUIRED")
    with ZipFile(original_jar) as original:
        path=original_owner+".class"
        require(original.namelist().count(path)==1,
                "R169_ORIGINAL_PACKET_CLASSFILE_NOT_UNIQUE")
        original_bytes=original.read(path)
    require(hashlib.sha256(original_bytes).hexdigest()==original_class_sha256,
            "R169_ORIGINAL_PACKET_CLASS_SHA256_CHANGED")
    parsed=parse_class(original_bytes)
    require(parsed.name==original_owner and
            {(f["name"],f["descriptor"]) for f in parsed.fields}.issuperset({
                (byte_array_field,"[B"),(cursor_field,"I")}),
            "R169_ORIGINAL_PACKET_BUFFER_FIELDS_NOT_PROVEN")
    chosen={(signed_short_method,"()I"),(float_wrapper_method,"()F")}
    real_method_ids={(m["name"],m["descriptor"]) for m in parsed.methods}
    require(chosen.issubset(real_method_ids) and
            (delegated_unrecovered_int_method,"()I") in real_method_ids,
            "R169_ORIGINAL_SIGNED_SHORT_FLOAT_AND_DELEGATE_NOT_PROVEN")
    javac=shutil.which("javac")
    require(javac is not None, "R169_REAL_JAVA9_COMPILER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r169-private-") as td:
        root=Path(td)
        java=root/"source"/(original_owner+".java")
        java.parent.mkdir(parents=True,exist_ok=True)
        java.write_bytes(source[0][1])
        classes=root/"classes"
        empty=root/"empty"
        classes.mkdir()
        empty.mkdir()
        env=os.environ.copy()
        for name in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                     "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(name,None)
        try:
            run=subprocess.run(
                [javac,"--release","9","-proc:none","-implicit:none",
                 "-g:none","-classpath",str(empty),"-sourcepath",str(empty),
                 "-d",str(classes),str(java)],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=60,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R169OriginalPacketTwoMethodsError(
                "R169_ISOLATED_PARTIAL_PACKET_JAVA_COMPILE_UNAVAILABLE") from exc
        require(run.returncode==0,
                "R169_PRIVATE_PACKET_PARTIAL_JAVA_NOT_COMPILABLE")
        emitted={p.relative_to(classes).as_posix()
                 for p in classes.rglob("*.class")}
        require(emitted=={original_owner+".class"},
                "R169_UNEXPECTED_COMPILED_JAVA_CLASS_OWNER")
        rebuilt=(classes/(original_owner+".class")).read_bytes()
    original_profile=profile_class_field_accesses(original_bytes)
    rebuilt_profile=profile_class_field_accesses(rebuilt)
    selected=sorted(chosen)
    original_available={(m["name"],m["descriptor"])
                        for m in original_profile["methods"]}
    rebuilt_available={(m["name"],m["descriptor"])
                       for m in rebuilt_profile["methods"]}
    require(chosen.issubset(original_available & rebuilt_available),
            "R169_MISSING_ORIGINAL_SELECTED_PACKET_METHOD")
    details=_strict_inspections(original_profile,rebuilt_profile,
                                selected=selected)
    require(details["verified_selected_method_count"]==expected_selected_methods
            and details["matched_opcode_count"]==expected_jvm_instructions
            and details["all_selected_core_method_code_equal"],
            "R169_ORIGINAL_PACKET_TWO_SELECTED_JVM_CODE_DIFFER")
    # The float wrapper's exact-original self-call to r():I is verified as
    # a CALLSITE ONLY. r() is an unselected, unverified Java placeholder.
    wrapper=next(m for m in original_profile["methods"]
                 if (m["name"],m["descriptor"])==
                    (float_wrapper_method,"()F"))
    calls=[(c.get("owner"),c.get("name"),c.get("descriptor"))
           for c in wrapper.get("method_invocations",[])
           if c.get("owner")==original_owner]
    require(calls==[(original_owner,
                     delegated_unrecovered_int_method,"()I")],
            "R169_ORIGINAL_FLOAT_READER_UNVERIFIED_DELEGATE_CHANGED")
    require(sha_file(original_jar)==original_sha256 and
            sha_file(private_partial_java_zip)==partial_java_sha256,
            "R169_PRIVATE_SOURCE_ORIGINAL_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"private_v309_original_packet_two_partial_java_methods_r169",
        "original_client_sha256":original_sha256,
        "original_packet_class_sha256":original_class_sha256,
        "private_partial_java_source_sha256":partial_java_sha256,
        "selected_original_packet_java_methods":expected_selected_methods,
        "original_jvm_instructions_verified":expected_jvm_instructions,
        "original_signed_short_two_byte_method_jvm_code_verified":True,
        "original_float_reader_wrapper_jvm_code_verified":True,
        "float_reader_delegated_method_body_verified":False,
        "partial_packet_original_superclass_and_all_fields_verified":False,
        "complete_original_packet_java_class_recovered":False,
        "add_partial_packet_source_to_canonical_tree":False,
        "original_binary_used_as_compiler_dependency":False,
        "whole_original_v309_client_compilation_verified":False,
        "recovered_original_source_publication_authorized":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_original_v309_jar")
    p.add_argument("private_partial_packet_java_zip")
    p.add_argument("fresh_private_report")
    p.add_argument("--source-sha256",required=True)
    args=p.parse_args(argv)
    out=Path(args.fresh_private_report)
    try:
        require(not out.exists() and not out.is_symlink() and
                out.parent.is_dir() and not out.parent.is_symlink(),
                "R169_REPORT_MUST_BE_NEW_PRIVATE_FILE")
        result=verify_original_packet_signed_short_and_float_wrapper(
            args.private_original_v309_jar,args.private_partial_packet_java_zip,
            partial_java_sha256=args.source_sha256)
        out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                       encoding="utf-8")
        print("R169_PACKET_TWO_ORIGINAL_METHODS_MATCH_NOT_FULL_PACKET")
        print("private_report_sha256="+sha_file(out))
    except Exception:
        p.error("R169_PRIVATE_PACKET_JVM_SOURCE_METHODS_NOT_ACCEPTED")


if __name__=="__main__":
    main()
