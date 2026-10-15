"""R170: exact original-v309 Packet B/r/s Java source, NOT full Packet.

Extend R169's selected signed-short and float-wrapper proof by recovering
the concrete unsigned four-byte big-endian r():int implementation. The
three methods are compiled together from privately SHA-pinned Java source
with NO original client binaries on the compiler classpath. The original
superclass, other Packet methods, fields and runtime behavior remain open.
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
from .private_v309_packet_partial_methods_r169 import (
    ORIGINAL_PACKET_SHA,
    verify_original_packet_signed_short_and_float_wrapper,
)

class R170PacketThreeSourceError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise R170PacketThreeSourceError(code)


def verify_original_packet_B_r_s(
        original_jar, private_packet_java_zip, *,
        original_sha256=CANONICAL_V309,
        private_packet_sha256,
        original_owner="rs/x/e",
        original_class_sha256=ORIGINAL_PACKET_SHA,
        signed_short="B", raw_int="r", float_reader="s",
        bytes_field="g", position_field="h",
        expected_selected_methods=3,
        expected_instructions=93,
        expected_raw_int_instructions=52):
    """Prove three selected original JVM Code bodies, not the entire class."""
    require(sha_file(original_jar)==original_sha256 and
            sha_file(private_packet_java_zip)==private_packet_sha256,
            "R170_EXACT_SOURCE_OR_ORIGINAL_SHA256_MISMATCH")
    require(re.fullmatch(
        r"[A-Za-z_$][A-Za-z0-9_$]*(?:/[A-Za-z_$][A-Za-z0-9_$]*)+",
        original_owner) and original_owner.startswith("rs/") and
        all(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", item)
            for item in (signed_short,raw_int,float_reader,
                         bytes_field,position_field)) and
        len({signed_short,raw_int,float_reader})==3 and
        expected_selected_methods==3 and
        1<=expected_instructions<=2000 and
        1<=expected_raw_int_instructions<=2000,
        "R170_ORIGINAL_JVM_IDENTITIES_OR_SELECTION_BOUNDS_INVALID")
    # R169 must continue to prove the exact B/s caller methods and reject
    # a change to either original signed-short implementation or float wrapper.
    previous=verify_original_packet_signed_short_and_float_wrapper(
        original_jar,private_packet_java_zip,
        original_sha256=original_sha256,
        partial_java_sha256=private_packet_sha256,
        original_owner=original_owner,
        original_class_sha256=original_class_sha256,
        signed_short_method=signed_short,
        float_wrapper_method=float_reader,
        delegated_unrecovered_int_method=raw_int,
        byte_array_field=bytes_field,
        cursor_field=position_field,
        expected_selected_methods=2,
        expected_jvm_instructions=expected_instructions-
                                  expected_raw_int_instructions)
    require(previous["original_jvm_instructions_verified"]==
            expected_instructions-expected_raw_int_instructions,
            "R170_R169_PARENT_METHODS_NOT_STILL_PROVEN")
    source=source_members(private_packet_java_zip,private_packet_sha256)
    require(len(source)==1 and
            source[0][0]==original_owner+".java" and
            0<len(source[0][1])<=100_000,
            "R170_EXACT_ONE_PRIVATE_ORIGINAL_JAVA_OWNER_REQUIRED")
    with ZipFile(original_jar) as archive:
        name=original_owner+".class"
        require(archive.namelist().count(name)==1,
                "R170_ORIGINAL_PACKET_CLASS_NOT_UNIQUE")
        original_bytes=archive.read(name)
    require(hashlib.sha256(original_bytes).hexdigest()==
            original_class_sha256,
            "R170_ORIGINAL_PACKET_CLASS_HASH_CHANGED")
    original_class=parse_class(original_bytes)
    require(original_class.name==original_owner and
            {(f["name"],f["descriptor"]) for f in
             original_class.fields}.issuperset({
                (bytes_field,"[B"),(position_field,"I")}),
            "R170_ORIGINAL_PACKET_FIELDS_NOT_PROVEN")
    ids={(signed_short,"()I"),(raw_int,"()I"),(float_reader,"()F")}
    require(ids.issubset(
        {(m["name"],m["descriptor"]) for m in original_class.methods}),
        "R170_THREE_ORIGINAL_MEMBER_IDENTITIES_MISSING")
    javac=shutil.which("javac")
    require(javac is not None,"R170_TRUSTED_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r170-private-") as temp:
        root=Path(temp)
        src=root/"src"/(original_owner+".java")
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
            result=subprocess.run([
                javac,"--release","9","-proc:none","-implicit:none",
                "-g:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),str(src)],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,check=False,timeout=60)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R170PacketThreeSourceError(
                "R170_SOURCE_ONLY_COMPILATION_UNAVAILABLE") from exc
        require(result.returncode==0,
                "R170_ORIGINAL_NAMED_PACKET_SOURCE_DOES_NOT_COMPILE")
        names={p.relative_to(out).as_posix()
               for p in out.rglob("*.class")}
        require(names=={original_owner+".class"},
                "R170_ORIGINAL_JAVA_SOURCE_CREATED_UNEXPECTED_CLASSES")
        rebuilt=(out/(original_owner+".class")).read_bytes()
    old=profile_class_field_accesses(original_bytes)
    new=profile_class_field_accesses(rebuilt)
    require(old["internal_name"]==new["internal_name"]==original_owner,
            "R170_JVM_OWNER_CHANGED_AFTER_SOURCE_COMPILATION")
    selected=sorted(ids)
    before={(m["name"],m["descriptor"]):m for m in old["methods"]}
    after={(m["name"],m["descriptor"]):m for m in new["methods"]}
    require(ids.issubset(before.keys() & after.keys()) and
            len(before[(raw_int,"()I")]["instructions"])==
                  expected_raw_int_instructions and
            len(after[(raw_int,"()I")]["instructions"])==
                  expected_raw_int_instructions,
            "R170_ORIGINAL_32BIT_READER_INSTRUCTION_COUNT_DRIFTED")
    # Fully decode original/rebuilt JVM instructions with CP-resolved
    # operands, branch offsets, limits and handlers. Selected methods only.
    proof=_strict_inspections(old,new,selected=selected)
    require(proof["verified_selected_method_count"]==
            expected_selected_methods and
            proof["matched_opcode_count"]==expected_instructions and
            proof["all_selected_core_method_code_equal"],
            "R170_ORIGINAL_B_R_S_METHOD_CODE_NOT_IDENTICAL")
    self_calls=[]
    for scope in (old,new):
        wrapper=next(m for m in scope["methods"]
                     if (m["name"],m["descriptor"])==(float_reader,"()F"))
        delegates=[
            (x.get("owner"),x.get("name"),x.get("descriptor"))
            for x in wrapper.get("method_invocations",[])
            if x.get("owner")==original_owner]
        self_calls.append(delegates)
    require(self_calls==[[(original_owner,raw_int,"()I")]]*2,
            "R170_ORIGINAL_FLOAT_TO_RAW32_SOURCE_CALL_NOT_CLOSED")
    require(sha_file(original_jar)==original_sha256 and
            sha_file(private_packet_java_zip)==private_packet_sha256,
            "R170_PINNED_ORIGINAL_CHANGED_DURING_COMPILATION")
    return {
        "schema_version":1,
        "kind":"private_v309_original_packet_signed_short_raw_int_float_r170",
        "original_client_sha256":original_sha256,
        "original_packet_class_sha256":original_class_sha256,
        "private_packet_java_source_sha256":private_packet_sha256,
        "original_selected_java_method_count":3,
        "selected_original_jvm_instructions_matched":expected_instructions,
        "original_32bit_reader_jvm_instructions_matched":
            expected_raw_int_instructions,
        "signed_short_reader_method_verified":True,
        "raw_big_endian_int_reader_method_verified":True,
        "float_reader_wrapper_and_original_raw_int_call_verified":True,
        "selected_java_source_self_call_closed":True,
        "original_packet_class_superclass_and_other_methods_complete":False,
        "complete_original_packet_java_source_accepted":False,
        "add_partial_packet_source_to_canonical_client_tree":False,
        "original_client_binary_compiler_fallback_used":False,
        "full_client_java_compilation_passed":False,
        "original_derived_java_source_publication_authorized":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_original_client_jar")
    p.add_argument("private_three_packet_methods_zip")
    p.add_argument("fresh_private_sanitized_report_json")
    p.add_argument("--source-sha256",required=True)
    args=p.parse_args(argv)
    out=Path(args.fresh_private_sanitized_report_json)
    try:
        require(not out.exists() and not out.is_symlink() and
                out.parent.is_dir() and not out.parent.is_symlink(),
                "R170_PRIVATE_REPORT_MUST_BE_NEW")
        report=verify_original_packet_B_r_s(
            args.private_original_client_jar,
            args.private_three_packet_methods_zip,
            private_packet_sha256=args.source_sha256)
        out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                       encoding="utf-8")
        print("R170_ORIGINAL_PACKET_THREE_JAVA_METHOD_CODE_VERIFIED")
        print("private_report_sha256="+sha_file(out))
    except Exception:
        p.error("R170_PACKET_THREE_METHOD_SOURCE_NOT_ACCEPTED")


if __name__=="__main__":
    main()
