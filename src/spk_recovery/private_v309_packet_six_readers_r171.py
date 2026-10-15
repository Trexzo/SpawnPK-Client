"""R171: six original-v309 Packet Java read methods, not full Packet source.

Adds independently reconstructed duplicate raw32 p(), unsigned 16-bit o()
and unsigned 8-bit y() to R170's signed16 B(), raw32 r(), float s().
No original game/client binary is ever a compiler dependency. All six
selected method Code streams must exactly match the original JVM methods.
Original Packet superclass, fields beyond selected buffer/cursor, remaining
method implementations, networking and pool behavior are NOT restored.
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
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file, source_members
from .private_v309_packet_partial_methods_r169 import ORIGINAL_PACKET_SHA
from .private_v309_packet_three_methods_r170 import (
    verify_original_packet_B_r_s,
)
from .private_v309_matrix_source_method_parity_r150 import (
    _strict_inspections,
)


class R171SixPacketMethodsError(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise R171SixPacketMethodsError(code)


def verify_original_packet_six_readers(
        original_jar, private_java_zip, *,
        original_sha256=CANONICAL_V309,
        private_source_sha256,
        original_owner="rs/x/e",
        original_class_sha256=ORIGINAL_PACKET_SHA,
        signed_short="B", raw_int="r", float_reader="s",
        alternate_raw_int="p", unsigned_short="o",
        unsigned_byte="y",
        bytes_field="g", cursor_field="h",
        expected_selected_methods=6,
        expected_instructions=186,
        expected_raw_int_instructions=52,
        expected_unsigned_short_instructions=28,
        expected_unsigned_byte_instructions=13):
    require(sha_file(original_jar)==original_sha256 and
            sha_file(private_java_zip)==private_source_sha256,
            "R171_PINNED_ORIGINAL_CLIENT_OR_JAVA_SOURCE_MISMATCH")
    names=[signed_short,raw_int,float_reader,alternate_raw_int,
           unsigned_short,unsigned_byte]
    require(re.fullmatch(
                r"[A-Za-z_$][A-Za-z0-9_$]*(?:/[A-Za-z_$][A-Za-z0-9_$]*)+",
                original_owner) and original_owner.startswith("rs/") and
            all(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*",name)
                for name in names+[bytes_field,cursor_field]) and
            len(set(names))==6 and expected_selected_methods==6 and
            expected_instructions>0 and
            all(x>0 for x in (
                expected_raw_int_instructions,
                expected_unsigned_short_instructions,
                expected_unsigned_byte_instructions)),
            "R171_METHOD_SELECTION_OR_JVM_OWNER_INVALID")
    initial_instructions=(expected_instructions-
                          expected_raw_int_instructions-
                          expected_unsigned_short_instructions-
                          expected_unsigned_byte_instructions)
    # This is an actual R170 (and transitively R169) verification of
    # B()+r()+s() against the SAME exact original/private Java inputs.
    initial=verify_original_packet_B_r_s(
        original_jar,private_java_zip,
        original_sha256=original_sha256,
        private_packet_sha256=private_source_sha256,
        original_owner=original_owner,
        original_class_sha256=original_class_sha256,
        signed_short=signed_short,raw_int=raw_int,
        float_reader=float_reader,
        bytes_field=bytes_field,position_field=cursor_field,
        expected_selected_methods=3,
        expected_instructions=initial_instructions,
        expected_raw_int_instructions=expected_raw_int_instructions)
    require(initial["selected_original_jvm_instructions_matched"]==
            initial_instructions and
            initial["selected_java_source_self_call_closed"],
            "R171_R170_ORIGINAL_THREE_METHOD_PROOF_MISSING")
    sources=source_members(private_java_zip,private_source_sha256)
    require(len(sources)==1 and sources[0][0]==original_owner+".java" and
            len(sources[0][1])<=100_000,
            "R171_EXACT_SINGLE_PRIVATE_PACKET_JAVA_REQUIRED")
    with ZipFile(original_jar) as z:
        require(z.namelist().count(original_owner+".class")==1,
                "R171_ORIGINAL_PACKET_CLASS_IDENTITY_NOT_UNIQUE")
        original=z.read(original_owner+".class")
    require(hashlib.sha256(original).hexdigest()==original_class_sha256,
            "R171_ORIGINAL_PACKET_CLASS_BYTES_CHANGED")
    javac=shutil.which("javac")
    require(javac is not None,"R171_TRUSTED_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r171-private-") as temp:
        root=Path(temp)
        source=root/"src"/(original_owner+".java")
        source.parent.mkdir(parents=True,exist_ok=True)
        source.write_bytes(sources[0][1])
        output=root/"classes";empty=root/"empty"
        output.mkdir();empty.mkdir()
        env=os.environ.copy()
        for name in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                     "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(name,None)
        try:
            compiled=subprocess.run(
                [javac,"--release","9","-proc:none","-implicit:none",
                 "-g:none","-classpath",str(empty),"-sourcepath",str(empty),
                 "-d",str(output),str(source)],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=60,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R171SixPacketMethodsError(
                "R171_JAVA_SOURCE_COMPILATION_UNAVAILABLE") from exc
        require(compiled.returncode==0 and
                {p.relative_to(output).as_posix()
                 for p in output.rglob("*.class")}==
                {original_owner+".class"},
                "R171_UNEXPECTED_OR_UNCOMPILABLE_JAVA_BINARY_OUTPUT")
        rebuilt=(output/(original_owner+".class")).read_bytes()
    old=profile_class_field_accesses(original)
    new=profile_class_field_accesses(rebuilt)
    require(old["internal_name"]==new["internal_name"]==original_owner,
            "R171_ORIGINAL_RECOMPILED_JVM_OWNER_NOT_EQUAL")
    selected={
        (signed_short,"()I"),(raw_int,"()I"),
        (float_reader,"()F"),(alternate_raw_int,"()I"),
        (unsigned_short,"()I"),(unsigned_byte,"()I")}
    original_methods={(m["name"],m["descriptor"]):m
                      for m in old["methods"]}
    rebuilt_methods={(m["name"],m["descriptor"]):m
                     for m in new["methods"]}
    require(selected.issubset(
        original_methods.keys() & rebuilt_methods.keys()) and
        len(original_methods[(alternate_raw_int,"()I")]["instructions"])==
             expected_raw_int_instructions and
        len(original_methods[(unsigned_short,"()I")]["instructions"])==
             expected_unsigned_short_instructions and
        len(original_methods[(unsigned_byte,"()I")]["instructions"])==
             expected_unsigned_byte_instructions,
        "R171_ORIGINAL_ADDITIONAL_PACKET_METHODS_NOT_PROVEN")
    parity=_strict_inspections(old,new,selected=sorted(selected))
    require(parity["verified_selected_method_count"]==
            expected_selected_methods and
            parity["matched_opcode_count"]==expected_instructions and
            parity["all_selected_core_method_code_equal"],
            "R171_SELECTED_ORIGINAL_PACKET_SIX_METHOD_CODE_NOT_EQUAL")
    require(sha_file(original_jar)==original_sha256 and
            sha_file(private_java_zip)==private_source_sha256,
            "R171_ORIGINAL_OR_PRIVATE_SOURCE_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"private_v309_original_packet_six_java_readers_r171",
        "original_client_sha256":original_sha256,
        "original_packet_class_sha256":original_class_sha256,
        "private_packet_java_source_zip_sha256":private_source_sha256,
        "exact_original_method_bodies_verified":expected_selected_methods,
        "exact_original_jvm_instructions_matched":expected_instructions,
        "original_unsigned_8bit_reader_verified":True,
        "original_unsigned_16bit_reader_verified":True,
        "original_signed_16bit_reader_verified":True,
        "both_original_32bit_reader_bodies_verified":True,
        "float_reader_calls_verified_original_32bit_source":True,
        "complete_packet_superclass_and_other_methods_verified":False,
        "entire_original_packet_class_java_recovered":False,
        "partial_packet_added_to_canonical_source_tree":False,
        "original_binary_used_for_java_compiler_dependencies":False,
        "full_client_compilation_accepted":False,
        "original_derived_source_publication_authorized":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_original_client_jar")
    parser.add_argument("private_six_method_packet_source_zip")
    parser.add_argument("fresh_private_report")
    parser.add_argument("--source-sha256",required=True)
    args=parser.parse_args(argv)
    out=Path(args.fresh_private_report)
    try:
        require(not out.exists() and not out.is_symlink() and
                out.parent.is_dir() and not out.parent.is_symlink(),
                "R171_PRIVATE_REPORT_MUST_BE_FRESH")
        report=verify_original_packet_six_readers(
            args.private_original_client_jar,
            args.private_six_method_packet_source_zip,
            private_source_sha256=args.source_sha256)
        out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                       encoding="utf-8")
        print("R171_ORIGINAL_PACKET_SIX_SELECTED_JAVA_CODE_BODIES_MATCH")
        print("private_report_sha256="+sha_file(out))
    except Exception:
        parser.error("R171_PACKET_SIX_JAVA_METHODS_NOT_ACCEPTED")


if __name__=="__main__":
    main()
