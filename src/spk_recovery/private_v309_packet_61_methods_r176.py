"""R176: original Packet Java source, 61 selected method verification.

Source-only Java9 recompilation; original Packet class is not complete.
"""
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from subprocess import run
from zipfile import ZipFile
from shutil import which
from .bytecode_profile import profile_class_field_accesses
from .private_client_source_ast_census_r126 import sha_file,source_members
from .private_v309_packet_49_methods_r175 import verify_packet_49,NEW as SIX
from .private_v309_packet_43_methods_r174 import READERS
from .private_v309_packet_34_methods_r173 import WRITERS
from .private_v309_packet_22_methods_r172 import EXTRA
from .private_v309_matrix_source_method_parity_r150 import _strict_inspections,_self_call_closure_for_selected

ADDED=(("g","()I"),("E","()J"),("w","()Ljava/lang/String;"),
       ("F","()Ljava/lang/String;"),("G","()V"),("I","()V"),
       ("H","()[B"),("a","([BII)V"),("a","(II[B)V"),
       ("a","(I[BI)V"),("b","(II[B)V"),("b","([BII)V"))

def verify_packet_61(jar,sourcezip,*,original_sha256,source_sha256,
                     owner="rs/x/e",class_sha256,first_six_kwargs=None,
                     legacy=1183,new_count=311,first_six=186,
                     prior_endian=360,prior_twenty_two=309,
                     expected_calls=5):
    kw=dict(first_six_kwargs or {})
    before=verify_packet_49(
        jar,sourcezip,original_sha256=original_sha256,
        source_sha256=source_sha256,owner=owner,
        class_sha256=class_sha256,first_six_kwargs=kw,
        old_count=legacy-212,new_count=212,first_six=first_six,
        previous_endian_count=prior_endian,
        previous_22_count=prior_twenty_two,self_call_edges=3)
    if before["total_matching_original_jvm_instructions"]!=legacy:
        raise ValueError("R176_PREVIOUS_49_METHOD_PROOF_FAILED")
    with ZipFile(jar) as z:
        original=z.read(owner+".class")
    if hashlib.sha256(original).hexdigest()!=class_sha256:
        raise ValueError("R176_ORIGINAL_CLASS_SHA_DRIFT")
    source=source_members(sourcezip,source_sha256)
    if len(source)!=1 or source[0][0]!=owner+".java":
        raise ValueError("R176_EXACT_SOURCE_OWNER_REQUIRED")
    javac=which("javac")
    if not javac:raise ValueError("R176_JDK_REQUIRED")
    with TemporaryDirectory(prefix="spk-r176-") as tmp:
        root=Path(tmp);src=root/"source"/(owner+".java")
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_bytes(source[0][1])
        out=root/"out";empty=root/"empty";out.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        p=run([javac,"--release","9","-g:none","-proc:none",
               "-implicit:none","-classpath",str(empty),
               "-sourcepath",str(empty),"-d",str(out),str(src)],
              capture_output=True,timeout=90,cwd=root,env=env)
        if p.returncode or {x.relative_to(out).as_posix()
                for x in out.rglob("*.class")}!={owner+".class"}:
            raise ValueError("R176_SOURCE_ONLY_JAVA_COMPILE_FAILED")
        rebuilt=(out/(owner+".class")).read_bytes()
    original_profile=profile_class_field_accesses(original)
    rebuilt_profile=profile_class_field_accesses(rebuilt)
    six={(kw.get(k,default),descriptor) for k,default,descriptor in (
        ("signed_short","B","()I"),("raw_int","r","()I"),
        ("float_reader","s","()F"),("alternate_raw_int","p","()I"),
        ("unsigned_short","o","()I"),("unsigned_byte","y","()I"))}
    selected=six|set(EXTRA)|set(WRITERS)|set(READERS)|set(SIX)|set(ADDED)
    index={(m["name"],m["descriptor"]):m for m in original_profile["methods"]}
    if len(selected)!=61 or not selected.issubset(index):
        raise ValueError("R176_METHOD_SELECTION_DRIFT")
    if sum(len(index[k]["instructions"]) for k in ADDED)!=new_count:
        raise ValueError("R176_ADDED_INSTRUCTION_COUNT_DRIFT")
    result=_strict_inspections(
        original_profile,rebuilt_profile,selected=sorted(selected))
    if result["verified_selected_method_count"]!=61 or result[
        "matched_opcode_count"]!=legacy+new_count or not result[
        "all_selected_core_method_code_equal"]:
        raise ValueError("R176_ORIGINAL_JVM_METHOD_CODE_MISMATCH")
    calls=_self_call_closure_for_selected(
        original_profile,sorted(selected),owner)
    new_calls=_self_call_closure_for_selected(
        rebuilt_profile,sorted(selected),owner)
    if calls!=new_calls or calls!=expected_calls:
        raise ValueError("R176_JVM_METHOD_SELF_CALL_CLOSURE_MISMATCH")
    if sha_file(jar)!=original_sha256 or sha_file(sourcezip)!=source_sha256:
        raise ValueError("R176_PRIVATE_INPUT_SHA_CHANGED")
    return {"selected_packet_method_bodies":61,
            "new_original_methods":12,
            "new_original_jvm_instructions":new_count,
            "total_matching_original_jvm_instructions":legacy+new_count,
            "selected_original_self_calls_closed":calls,
            "original_packet_class_complete":False,
            "canonical_client_tree_modified":False,
            "original_binary_compiler_fallback":False}
