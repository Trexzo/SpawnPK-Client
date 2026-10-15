"""R175 — six more privately verified original-v309 Packet Java readers.

Re-run the complete pinned R174 source proof before accepting l(), m(),
q(), u(), x(), t(). Private original and source Java bytes never enter CI
or public GitHub; synthetic CI only. Partial Packet remains unpublishable.
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
from .private_v309_packet_43_methods_r174 import (
    verify_packet_43,READERS)
from .private_v309_packet_34_methods_r173 import WRITERS
from .private_v309_packet_22_methods_r172 import EXTRA
from .private_v309_matrix_source_method_parity_r150 import (
    _strict_inspections,_self_call_closure_for_selected)

NEW=tuple((name,"()I") for name in ("l","m","q","u","x","t"))

def verify_packet_49(jar,sourcezip,*,original_sha256,
                     source_sha256,owner="rs/x/e",class_sha256,
                     first_six_kwargs=None,
                     old_count=971,new_count=212,first_six=186,
                     self_call_edges=3):
    kw=dict(first_six_kwargs or {})
    old=verify_packet_43(
        jar,sourcezip,original_sha256=original_sha256,
        source_sha256=source_sha256,owner=owner,class_sha256=class_sha256,
        first_six_kwargs=kw,previous_count=old_count-new_count*0-360,
        new_count=360,initial_six=first_six)
    if old["total_matching_original_jvm_instructions"]!=old_count:
        raise ValueError("R175_PRIOR_43_METHOD_SOURCE_PROOF_FAILED")
    if sha_file(jar)!=original_sha256 or sha_file(sourcezip)!=source_sha256:
        raise ValueError("R175_PINNED_ORIGINAL_SOURCE_CHANGED")
    with ZipFile(jar) as z:
        if z.namelist().count(owner+".class")!=1:
            raise ValueError("R175_ORIGINAL_PACKET_JVM_OWNER_NOT_UNIQUE")
        original=z.read(owner+".class")
    if hashlib.sha256(original).hexdigest()!=class_sha256:
        raise ValueError("R175_ORIGINAL_PACKET_CLASS_CHANGED")
    src=source_members(sourcezip,source_sha256)
    if len(src)!=1 or src[0][0]!=owner+".java":
        raise ValueError("R175_EXACT_ONE_PRIVATE_JAVA_SOURCE_REQUIRED")
    compiler=shutil.which("javac")
    if not compiler:raise ValueError("R175_TRUSTED_JDK_REQUIRED")
    with TemporaryDirectory(prefix="spk-r175-") as td:
        root=Path(td);file=root/"src"/(owner+".java")
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_bytes(src[0][1])
        output=root/"classes";empty=root/"empty"
        output.mkdir();empty.mkdir()
        env=os.environ.copy()
        for k in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                  "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):env.pop(k,None)
        p=subprocess.run([compiler,"--release","9","-proc:none",
            "-g:none","-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(output),str(file)],
            cwd=root,env=env,stdin=subprocess.DEVNULL,
            capture_output=True,timeout=90)
        if p.returncode or {p.relative_to(output).as_posix()
                for p in output.rglob("*.class")}!={owner+".class"}:
            raise ValueError("R175_STANDALONE_PACKET_JAVA_SOURCE_FAILED")
        rebuilt=(output/(owner+".class")).read_bytes()
    a=profile_class_field_accesses(original)
    b=profile_class_field_accesses(rebuilt)
    six={(kw.get(k,d),desc) for k,d,desc in (
        ("signed_short","B","()I"),
        ("raw_int","r","()I"),
        ("float_reader","s","()F"),
        ("alternate_raw_int","p","()I"),
        ("unsigned_short","o","()I"),
        ("unsigned_byte","y","()I"))}
    selected=six|set(EXTRA)|set(WRITERS)|set(READERS)|set(NEW)
    index={(m["name"],m["descriptor"]):m for m in a["methods"]}
    if len(selected)!=49 or not selected.issubset(index):
        raise ValueError("R175_SELECTED_ORIGINAL_METHODS_MISSING")
    count=sum(len(index[k]["instructions"]) for k in NEW)
    if count!=new_count:
        raise ValueError("R175_SIX_ORIGINAL_INSTRUCTION_COUNT_DRIFT")
    proof=_strict_inspections(a,b,selected=sorted(selected))
    if proof["verified_selected_method_count"]!=49 or proof[
            "matched_opcode_count"]!=old_count+new_count or not proof[
            "all_selected_core_method_code_equal"]:
        raise ValueError("R175_ORIGINAL_PACKET_JVM_CODE_MISMATCH")
    first=_self_call_closure_for_selected(a,sorted(selected),owner)
    second=_self_call_closure_for_selected(b,sorted(selected),owner)
    if first!=second or first!=self_call_edges:
        raise ValueError("R175_ORIGINAL_CALLCHAIN_NOT_CLOSED")
    if sha_file(jar)!=original_sha256 or sha_file(sourcezip)!=source_sha256:
        raise ValueError("R175_INPUT_CHANGED_DURING_PRIVATE_REPLAY")
    return {
        "private_v309_packet_selected_method_count":49,
        "new_exact_original_method_bodies":6,
        "new_matching_original_jvm_instructions":new_count,
        "total_matching_original_jvm_instructions":old_count+new_count,
        "same_original_self_call_edges_closed":first,
        "complete_original_packet_restored":False,
        "canonical_client_tree_modified":False,
        "original_binary_compiler_fallback_used":False,
        "full_original_client_java_compiled":False,
    }
