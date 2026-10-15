"""R174 original-v309 Packet: nine endian and transformed-integer readers.

Repeat R173's 34-method proof on the SAME SHA-pinned original/private Java
inputs before accepting nine further methods. Then independently compile
the one partial Packet Java source with an empty original/external binary
classpath and compare all 43 selected original JVM method Code bodies.
The original Packet superclass and other methods are NOT proven.
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
from .private_v309_packet_34_methods_r173 import (
    WRITERS,verify_packet_34)
from .private_v309_packet_22_methods_r172 import EXTRA
from .private_v309_matrix_source_method_parity_r150 import _strict_inspections

READERS=tuple((name,"()I") for name in
    ("S","T","U","V","W","X","Y","C","D"))

def verify_packet_43(jar,sourcezip,*,original_sha256,source_sha256,
                     owner="rs/x/e",class_sha256,
                     first_six_kwargs=None,
                     previous_count=611,new_count=360,
                     initial_six=186):
    kw=dict(first_six_kwargs or {})
    proof=verify_packet_34(
        jar,sourcezip,original_sha256=original_sha256,
        source_sha256=source_sha256,owner=owner,class_sha256=class_sha256,
        first_six_kwargs={**kw,
                          "base_six_instruction_count":initial_six},
        legacy=309,writes=previous_count-309)
    if proof["original_jvm_instructions_matched"]!=previous_count:
        raise ValueError("R174_R173_ORIGINAL_PROOF_NOT_ACCEPTED")
    if sha_file(jar)!=original_sha256 or sha_file(sourcezip)!=source_sha256:
        raise ValueError("R174_ORIGINAL_OR_SOURCE_PIN_MISMATCH")
    with ZipFile(jar) as z:
        if z.namelist().count(owner+".class")!=1:
            raise ValueError("R174_ORIGINAL_OWNER_NOT_UNIQUE")
        binary=z.read(owner+".class")
    if hashlib.sha256(binary).hexdigest()!=class_sha256:
        raise ValueError("R174_ORIGINAL_PACKET_CLASS_HASH_MISMATCH")
    source=source_members(sourcezip,source_sha256)
    if len(source)!=1 or source[0][0]!=owner+".java":
        raise ValueError("R174_PRIVATE_JAVA_OWNER_NOT_UNIQUE")
    javac=shutil.which("javac")
    if not javac:raise ValueError("R174_JAVA_COMPILER_REQUIRED")
    with TemporaryDirectory(prefix="spk-r174-") as folder:
        root=Path(folder)
        java=root/"src"/(owner+".java")
        java.parent.mkdir(parents=True,exist_ok=True)
        java.write_bytes(source[0][1])
        output=root/"classes";empty=root/"empty"
        output.mkdir();empty.mkdir()
        env=os.environ.copy()
        for k in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                  "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):env.pop(k,None)
        proc=subprocess.run(
            [javac,"--release","9","-proc:none","-g:none",
             "-implicit:none","-classpath",str(empty),
             "-sourcepath",str(empty),"-d",str(output),str(java)],
            env=env,cwd=root,stdin=subprocess.DEVNULL,
            capture_output=True,timeout=90)
        if proc.returncode!=0 or {
            p.relative_to(output).as_posix()
            for p in output.rglob("*.class")}!={owner+".class"}:
            raise ValueError("R174_ISOLATED_SOURCE_JAVA_COMPILATION_FAILED")
        rebuilt=(output/(owner+".class")).read_bytes()
    original=profile_class_field_accesses(binary)
    candidate=profile_class_field_accesses(rebuilt)
    six={(kw.get(key,default),desc) for key,default,desc in (
         ("signed_short","B","()I"),("raw_int","r","()I"),
         ("float_reader","s","()F"),
         ("alternate_raw_int","p","()I"),
         ("unsigned_short","o","()I"),("unsigned_byte","y","()I"))}
    selected=six|set(EXTRA)|set(WRITERS)|set(READERS)
    originals={(m["name"],m["descriptor"]):m
               for m in original["methods"]}
    if len(selected)!=43 or not selected.issubset(originals):
        raise ValueError("R174_INCOMPLETE_METHOD_SELECTION")
    opcodes=sum(len(originals[k]["instructions"]) for k in READERS)
    if opcodes!=new_count:
        raise ValueError("R174_ORIGINAL_NINE_MEMBER_OPCODE_COUNT_DRIFT")
    comparisons=_strict_inspections(
        original,candidate,selected=sorted(selected))
    if (comparisons["verified_selected_method_count"]!=43 or
        comparisons["matched_opcode_count"]!=previous_count+new_count or
        not comparisons["all_selected_core_method_code_equal"]):
        raise ValueError("R174_ORIGINAL_JVM_CODE_NOT_EQUAL")
    if sha_file(jar)!=original_sha256 or sha_file(sourcezip)!=source_sha256:
        raise ValueError("R174_PRIVATE_SOURCES_CHANGED_DURING_REPLAY")
    return {
        "kind":"private_original_v309_packet_43_source_methods_r174",
        "original_client_sha256":original_sha256,
        "original_packet_class_sha256":class_sha256,
        "private_recovered_java_sha256":source_sha256,
        "selected_original_java_method_count":43,
        "new_original_reader_method_count":9,
        "new_matching_original_jvm_instructions":new_count,
        "total_matching_original_jvm_instructions":previous_count+new_count,
        "original_packet_class_complete":False,
        "canonical_client_source_tree_modified":False,
        "original_binary_compiler_fallback_used":False,
        "full_original_v309_client_compiles":False,
        "derived_source_publication_authorized":False,
    }
