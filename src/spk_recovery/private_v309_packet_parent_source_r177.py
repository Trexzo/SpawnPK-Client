"""R177: independently verify complete Java source for original Packet parent chain.

Two original JVM class owners, rs/t and rs/a, are source-built together
with EMPTY game/external classpath. All field and method ABI and all
method Code are required to match the pinned original client JAR.
Neither Packet rs/x/e nor the full original client is accepted here.
"""
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from subprocess import run
from shutil import which
from zipfile import ZipFile,ZIP_DEFLATED
from .classfile import parse_class
from .bytecode_profile import profile_class_field_accesses
from .private_client_source_ast_census_r126 import sha_file,source_members
from .private_v309_matrix_source_method_parity_r150 import _strict_inspections

OWNERS=("rs/t","rs/a")

def verify_original_packet_parents(jar,sourcezip,*,original_sha256,
                                   source_sha256,original_class_shas,
                                   expected_methods=4,
                                   expected_instructions=48):
    if sha_file(jar)!=original_sha256 or sha_file(sourcezip)!=source_sha256:
        raise ValueError("R177_PRIVATE_INPUT_SHA256_MISMATCH")
    sources=source_members(sourcezip,source_sha256)
    if len(sources)!=2 or {x[0] for x in sources}!={o+".java" for o in OWNERS}:
        raise ValueError("R177_TWO_EXACT_SOURCE_OWNERS_REQUIRED")
    with ZipFile(jar) as original:
        binary={}
        for owner in OWNERS:
            if original.namelist().count(owner+".class")!=1:
                raise ValueError("R177_ORIGINAL_OWNER_NOT_UNIQUE")
            binary[owner]=original.read(owner+".class")
            if hashlib.sha256(binary[owner]).hexdigest()!=original_class_shas[owner]:
                raise ValueError("R177_ORIGINAL_CLASS_SHA_CHANGED")
    java=which("javac")
    if java is None:raise ValueError("R177_JDK_REQUIRED")
    with TemporaryDirectory(prefix="spk-r177-") as td:
        root=Path(td)
        paths=[]
        for relative,data in sources:
            target=root/"src"/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
            paths.append(target)
        compiled=root/"compiled";empty=root/"empty"
        compiled.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        proc=run([java,"--release","9","-g:none","-proc:none","-implicit:none",
                  "-classpath",str(empty),"-sourcepath",str(empty),
                  "-d",str(compiled),*[str(p) for p in paths]],
                 capture_output=True,cwd=root,env=env,timeout=90)
        if proc.returncode or {p.relative_to(compiled).as_posix()
                              for p in compiled.rglob("*.class")}!={
                              x+".class" for x in OWNERS}:
            raise ValueError("R177_JAVA_SOURCE_ONLY_COMPILE_FAILED")
        rebuilt={o:(compiled/(o+".class")).read_bytes() for o in OWNERS}
    count=0
    methods=0
    for owner,super_name in (("rs/t","java/lang/Object"),("rs/a","rs/t")):
        a,b=parse_class(binary[owner]),parse_class(rebuilt[owner])
        if (a.name,b.name,a.super_name,b.super_name)!=(owner,owner,
                                                       super_name,super_name):
            raise ValueError("R177_ORIGINAL_CLASS_SUPERCHAIN_MISMATCH")
        if a.access!=b.access or a.major!=b.major:
            raise ValueError("R177_CLASS_ACCESS_OR_JAVA_RELEASE_MISMATCH")
        fields=lambda c:{(f["name"],f["descriptor"],f["access"]) for f in c.fields}
        if fields(a)!=fields(b):
            raise ValueError("R177_ORIGINAL_LINKED_NODE_FIELD_ABI_MISMATCH")
        old=profile_class_field_accesses(binary[owner])
        new=profile_class_field_accesses(rebuilt[owner])
        members=lambda x:{(m["name"],m["descriptor"]) for m in x["methods"]}
        if members(old)!=members(new) or len(members(old))!=2:
            raise ValueError("R177_ORIGINAL_CLASS_METHOD_INVENTORY_MISMATCH")
        comparison=_strict_inspections(old,new,selected=sorted(members(old)))
        if comparison["verified_selected_method_count"]!=2 or not comparison[
                "all_selected_core_method_code_equal"]:
            raise ValueError("R177_ORIGINAL_SOURCE_JVM_CODE_MISMATCH")
        count+=comparison["matched_opcode_count"]
        methods+=2
    if count!=expected_instructions or methods!=expected_methods:
        raise ValueError("R177_TOTAL_ORIGINAL_METHOD_CODE_COUNT_CHANGED")
    if sha_file(jar)!=original_sha256 or sha_file(sourcezip)!=source_sha256:
        raise ValueError("R177_PRIVATE_INPUT_CHANGED_DURING_BUILD")
    return {"complete_original_parent_classes_source_built":2,
            "all_original_parent_method_bodies_matched":methods,
            "matched_original_jvm_instructions":count,
            "original_superchain_and_field_abi_verified":True,
            "original_class_binary_compiler_fallback":False,
            "original_packet_rs_x_e_complete":False,
            "full_client_compilation_accepted":False}

def overlay_verified_parent_java(baseline,parents,output,*,
                                 baseline_sha256,parents_sha256,
                                 expected_original_java=1276):
    if sha_file(baseline)!=baseline_sha256 or sha_file(parents)!=parents_sha256:
        raise ValueError("R177_PRIVATE_SOURCE_TREE_PIN_MISMATCH")
    target=Path(output)
    if target.exists() or not target.parent.is_dir():
        raise ValueError("R177_NEW_PRIVATE_OUTPUT_REQUIRED")
    with ZipFile(baseline) as source:
        original={m.filename:source.read(m.filename) for m in source.infolist()}
    prefix="recovered-source/v309/src/"
    if len(original)!=expected_original_java:
        raise ValueError("R177_BASELINE_TREE_NOT_PINNED_COUNT")
    files=source_members(parents,parents_sha256)
    additions={prefix+k:v for k,v in files}
    if {k for k,_ in files}!={owner+".java" for owner in OWNERS} or (
        set(k.casefold() for k in original)&set(k.casefold() for k in additions)):
        raise ValueError("R177_NOT_EXACT_TWO_UNSHADOWED_PARENT_SOURCES")
    with ZipFile(target,"w",ZIP_DEFLATED) as dest:
        for k,v in sorted({**original,**additions}.items()):
            dest.writestr(k,v)
    with ZipFile(target) as verify:
        if len(verify.namelist())!=expected_original_java+2 or any(
                verify.read(k)!=v for k,v in original.items()):
            raise ValueError("R177_PREVIOUS_RECOVERED_SOURCES_NOT_PRESERVED")
    return {"source_files":expected_original_java+2,
            "previous_files_unchanged":True,
            "partial_packet_installed":False,
            "full_client_compiled":False,
            "output_source_tree_sha256":sha_file(target)}
