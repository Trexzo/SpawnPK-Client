"""R173: privately verify twelve additional original Packet byte writers.

This extends the SHA-pinned, source-only R172 22-member JVM verification.
Partial Packet source is not complete client source.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from .bytecode_profile import profile_class_field_accesses
from .private_client_source_ast_census_r126 import sha_file,source_members
from .private_v309_packet_22_methods_r172 import EXTRA,verify_packet_22
from .private_v309_matrix_source_method_parity_r150 import _strict_inspections

WRITERS=tuple((name,"(I)V") for name in
    ("b","d","e","f","h","i","j","l","m","n","o","p"))

def verify_packet_34(jar,sourcezip,*,original_sha256,source_sha256,
                     owner="rs/x/e",class_sha256,
                     first_six_kwargs=None,legacy=309,writes=302):
    kw=dict(first_six_kwargs or {})
    base_six=kw.pop("base_six_instruction_count",186)
    first=verify_packet_22(
        jar,sourcezip,original_sha256=original_sha256,
        source_sha256=source_sha256,owner=owner,
        class_sha256=class_sha256,first_six_kwargs=kw,
        expected_legacy=base_six,
        expected_extra=legacy-base_six)
    if first["verified_original_jvm_instructions"]!=legacy:
        raise ValueError("R173_R172_METHOD_PROOF_FAILED")
    with ZipFile(jar) as z:original=z.read(owner+".class")
    if hashlib.sha256(original).hexdigest()!=class_sha256:
        raise ValueError("R173_CLASS_SHA256_MISMATCH")
    content=source_members(sourcezip,source_sha256)
    if len(content)!=1 or content[0][0]!=owner+".java":
        raise ValueError("R173_SOURCE_OWNER_NOT_UNIQUE")
    java=shutil.which("javac")
    if not java:raise ValueError("R173_TRUSTED_JDK_MISSING")
    with TemporaryDirectory(prefix="spk-r173-") as td:
        root=Path(td);p=root/"src"/(owner+".java")
        p.parent.mkdir(parents=True);p.write_bytes(content[0][1])
        out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS",
                    "_JAVA_OPTIONS"):env.pop(key,None)
        result=subprocess.run([java,"--release","9","-g:none",
            "-proc:none","-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(out),str(p)],
            cwd=root,env=env,stdin=subprocess.DEVNULL,
            capture_output=True,timeout=60)
        if result.returncode:raise ValueError("R173_JAVA_COMPILE_FAILED")
        if {f.relative_to(out).as_posix() for f in out.rglob("*.class")}!={
                owner+".class"}:
            raise ValueError("R173_UNEXPECTED_BINARY_CLASS_OUTPUT")
        rebuilt=(out/(owner+".class")).read_bytes()
    original_profile=profile_class_field_accesses(original)
    rebuilt_profile=profile_class_field_accesses(rebuilt)
    six={(kw.get(key,default),desc) for key,default,desc in (
         ("signed_short","B","()I"),("raw_int","r","()I"),
         ("float_reader","s","()F"),("alternate_raw_int","p","()I"),
         ("unsigned_short","o","()I"),("unsigned_byte","y","()I"))}
    selected=six|set(EXTRA)|set(WRITERS)
    methods={(m["name"],m["descriptor"]):m
             for m in original_profile["methods"]}
    count=sum(len(methods[k]["instructions"]) for k in WRITERS)
    if count!=writes or len(selected)!=34:
        raise ValueError("R173_ORIGINAL_SELECTED_METHOD_DRIFT")
    result=_strict_inspections(
        original_profile,rebuilt_profile,selected=sorted(selected))
    if result["verified_selected_method_count"]!=34 or result[
            "matched_opcode_count"]!=legacy+writes:
        raise ValueError("R173_ORIGINAL_METHOD_JVM_CODE_DIFFERS")
    if sha_file(jar)!=original_sha256 or sha_file(sourcezip)!=source_sha256:
        raise ValueError("R173_PRIVATE_SOURCE_CHANGED_DURING_REPLAY")
    return {"verified_selected_packet_methods":34,
            "new_original_byte_writer_methods":12,
            "original_jvm_instructions_matched":legacy+writes,
            "full_packet_class_recovered":False,
            "canonical_client_tree_modified":False}
