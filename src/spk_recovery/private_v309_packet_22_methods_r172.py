"""R172 — strictly compare 16 additional original Packet methods from Java.

Requires SHA-pinned original and private source, successful R171 six-reader
verification, and an isolated Java9 recompile. No original client binary
is a javac dependency. This is NOT complete Packet source acceptance.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .private_client_source_ast_census_r126 import sha_file, source_members
from .private_v309_packet_six_readers_r171 import verify_original_packet_six_readers
from .private_v309_matrix_source_method_parity_r150 import _strict_inspections

EXTRA=(("h","()I"),("i","()V"),("j","()I"),("k","()I"),
       ("z","()B"),("J","()V"),("K","()V"),("Z","()I"),
       ("aa","()I"),("ab","()I"),("ac","()[B"),
       ("N","()I"),("O","()I"),("P","()I"),
       ("Q","()B"),("R","()B"))

def verify_packet_22(original_jar,java_zip,*,original_sha256,
                     source_sha256,owner="rs/x/e",class_sha256,
                     first_six_kwargs=None,expected_legacy=186,
                     expected_extra=123):
    if (sha_file(original_jar)!=original_sha256 or
            sha_file(java_zip)!=source_sha256):
        raise ValueError("R172_ORIGINAL_OR_SOURCE_SHA_MISMATCH")
    first_six_kwargs=dict(first_six_kwargs or {})
    result=verify_original_packet_six_readers(
        original_jar,java_zip,original_sha256=original_sha256,
        private_source_sha256=source_sha256,
        original_owner=owner,original_class_sha256=class_sha256,
        expected_instructions=expected_legacy,**first_six_kwargs)
    if result["exact_original_jvm_instructions_matched"]!=expected_legacy:
        raise ValueError("R172_R171_SIX_METHOD_PROOF_NOT_ACCEPTED")
    source=source_members(java_zip,source_sha256)
    if len(source)!=1 or source[0][0]!=owner+".java":
        raise ValueError("R172_JAVA_SOURCE_OWNER_NOT_UNIQUE")
    with ZipFile(original_jar) as z:
        raw=z.read(owner+".class")
    if hashlib.sha256(raw).hexdigest()!=class_sha256:
        raise ValueError("R172_ORIGINAL_PACKET_CLASS_IDENTITY_DRIFT")
    javac=shutil.which("javac")
    if not javac: raise ValueError("R172_JDK_REQUIRED")
    with TemporaryDirectory(prefix="spk-r172-") as d:
        root=Path(d);path=root/"src"/(owner+".java")
        path.parent.mkdir(parents=True);path.write_bytes(source[0][1])
        out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        env=os.environ.copy()
        for k in ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(k,None)
        p=subprocess.run(
            [javac,"--release","9","-g:none","-proc:none","-implicit:none",
             "-classpath",str(empty),"-sourcepath",str(empty),"-d",str(out),
             str(path)],cwd=root,env=env,stdin=subprocess.DEVNULL,
            capture_output=True,timeout=60)
        if p.returncode or {x.relative_to(out).as_posix()
                for x in out.rglob("*.class")}!={owner+".class"}:
            raise ValueError("R172_SOURCE_ONLY_JAVAC_COMPILE_FAILED")
        rebuilt=(out/(owner+".class")).read_bytes()
    old=profile_class_field_accesses(raw)
    new=profile_class_field_accesses(rebuilt)
    six={("B","()I"),("r","()I"),("s","()F"),
         ("p","()I"),("o","()I"),("y","()I")}
    mapping=first_six_kwargs.get("selected_six",six)
    selection=set(mapping)|set(EXTRA)
    original={(m["name"],m["descriptor"]):m for m in old["methods"]}
    additional=sum(len(original[x]["instructions"]) for x in EXTRA)
    if additional!=expected_extra or len(selection)!=22:
        raise ValueError("R172_ORIGINAL_METHOD_FRONTIER_DRIFT")
    report=_strict_inspections(old,new,selected=sorted(selection))
    if (report["verified_selected_method_count"]!=22 or
        report["matched_opcode_count"]!=expected_legacy+expected_extra or
        not report["all_selected_core_method_code_equal"]):
        raise ValueError("R172_JVM_METHOD_CODE_PARITY_FAILED")
    if sha_file(original_jar)!=original_sha256 or sha_file(java_zip)!=source_sha256:
        raise ValueError("R172_SOURCE_CHANGED_DURING_PROOF")
    return {"verified_original_method_bodies":22,
            "verified_original_jvm_instructions":expected_legacy+expected_extra,
            "complete_packet_recovered":False,
            "canonical_source_tree_modified":False,
            "original_class_binary_used_as_dependency":False}
