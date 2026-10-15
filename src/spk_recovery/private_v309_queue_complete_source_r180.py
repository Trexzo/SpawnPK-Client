"""R180 — complete original-v309 rs/h queue Java-source reconstruction.

Full original field and method identity and exact Java9 source-recompiled
JVM Code verification, after R177 proves source of both parent types.
Private source-tree overlay must not overwrite any previous Java file.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile,ZIP_DEFLATED

from .classfile import parse_class
from .bytecode_profile import profile_class_field_accesses
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file,source_members
from .private_v309_matrix_source_method_parity_r150 import _strict_inspections
from .private_v309_packet_parent_source_r177 import verify_original_packet_parents

QUEUE_SHA="c1d9899c7ecb157e8e587b8fda9e661923d68c0a62a073164c152d073156788e"
PARENTS={
    "rs/t":"430c61233ef1d46a3dadbe4947a3d4d17019db2bc1d4678dc732623ea1b3274f",
    "rs/a":"7c33983b6e49dc2cd8b4b5bde2bd0550a4977c1eaa483025630b5c16105e735f",
}


def verify_original_queue_java(
        original_jar,private_queue_java_zip,private_parents_java_zip,*,
        original_sha256=CANONICAL_V309,
        queue_source_sha256,parents_source_sha256,
        queue_class_sha256=QUEUE_SHA,parent_class_shas=None,
        queue_owner="rs/h",expected_methods=9,expected_opcodes=171,
        expected_fields=2,parent_method_count=4,parent_opcodes=48):
    pins=((original_jar,original_sha256),
          (private_queue_java_zip,queue_source_sha256),
          (private_parents_java_zip,parents_source_sha256))
    if not all(sha_file(f)==digest for f,digest in pins):
        raise ValueError("R180_PRIVATE_JAVA_OR_ORIGINAL_SHA_MISMATCH")
    parent=verify_original_packet_parents(
        original_jar,private_parents_java_zip,
        original_sha256=original_sha256,
        source_sha256=parents_source_sha256,
        original_class_shas=parent_class_shas or PARENTS,
        expected_methods=parent_method_count,
        expected_instructions=parent_opcodes)
    if parent["complete_original_parent_classes_source_built"]!=2:
        raise ValueError("R180_ORIGINAL_NODE_PARENT_SOURCES_NOT_PROVEN")
    q=source_members(private_queue_java_zip,queue_source_sha256)
    p=source_members(private_parents_java_zip,parents_source_sha256)
    if len(q)!=1 or q[0][0]!=queue_owner+".java" or len(p)!=2:
        raise ValueError("R180_EXACT_THREE_SOURCE_JAVA_OWNER_IDENTITIES")
    with ZipFile(original_jar) as archive:
        if archive.namelist().count(queue_owner+".class")!=1:
            raise ValueError("R180_ORIGINAL_JVM_QUEUE_OWNER_NOT_UNIQUE")
        binary=archive.read(queue_owner+".class")
    if hashlib.sha256(binary).hexdigest()!=queue_class_sha256:
        raise ValueError("R180_ORIGINAL_QUEUE_CLASS_SHA_CHANGED")
    original=parse_class(binary)
    java=shutil.which("javac")
    if not java:raise ValueError("R180_TRUSTED_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r180-source-") as tmp:
        root=Path(tmp)
        files=[]
        for relative,content in [*q,*p]:
            if (".." in relative.split("/") or
                    "\\" in relative or not relative.endswith(".java")):
                raise ValueError("R180_UNSAFE_SOURCE_PATH")
            path=root/"src"/relative
            if path.exists():raise ValueError("R180_JAVA_IDENTITY_COLLISION")
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(content)
            files.append(path)
        out=root/"classes"
        empty=root/"empty"
        out.mkdir()
        empty.mkdir()
        env=os.environ.copy()
        for name in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                     "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(name,None)
        try:
            proc=subprocess.run(
                [java,"--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),
                 *[str(p) for p in files]],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=90)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise ValueError("R180_STANDALONE_JAVA_COMPILATION_UNAVAILABLE") from exc
        compiled_names={p.relative_to(out).as_posix()
                        for p in out.rglob("*.class")}
        if proc.returncode!=0 or compiled_names!={
            queue_owner+".class","rs/t.class","rs/a.class"}:
            raise ValueError("R180_FULL_QUEUE_ORIGINAL_SOURCE_COMPILATION_FAILED")
        rebuilt=(out/(queue_owner+".class")).read_bytes()
    generated=parse_class(rebuilt)
    if ((original.name,original.super_name,original.major,original.access)!=
        (generated.name,generated.super_name,generated.major,generated.access)
        or original.super_name!="java/lang/Object"):
        raise ValueError("R180_ORIGINAL_QUEUE_JVM_CLASS_ABI_MISMATCH")
    fields=lambda x:{(f["name"],f["descriptor"],f["access"]) for f in x.fields}
    if (len(fields(original))!=expected_fields or
            fields(original)!=fields(generated)):
        raise ValueError("R180_ORIGINAL_QUEUE_FIELD_ABI_MISMATCH")
    old=profile_class_field_accesses(binary)
    new=profile_class_field_accesses(rebuilt)
    ids=lambda x:{(m["name"],m["descriptor"]) for m in x["methods"]}
    selected=sorted(ids(old))
    if len(selected)!=expected_methods or ids(new)!=set(selected):
        raise ValueError("R180_ORIGINAL_QUEUE_METHOD_INVENTORY_CHANGED")
    result=_strict_inspections(old,new,selected=selected)
    if (result["verified_selected_method_count"]!=expected_methods or
        result["matched_opcode_count"]!=expected_opcodes or
        not result["all_selected_core_method_code_equal"]):
        raise ValueError("R180_ORIGINAL_QUEUE_METHOD_JVM_CODE_DIFFERENT")
    if not all(sha_file(f)==digest for f,digest in pins):
        raise ValueError("R180_ORIGINAL_PRIVATE_INPUT_CHANGED")
    return {
        "schema_version":1,
        "kind":"v309_complete_original_queue_rs_h_java_r180",
        "original_queue_class_sha256":queue_class_sha256,
        "all_original_queue_fields_verified":expected_fields,
        "all_original_queue_methods_verified":expected_methods,
        "all_original_queue_jvm_instructions_matched":expected_opcodes,
        "original_parent_source_and_superclass_verified":True,
        "original_binary_used_as_java_compiler_dependency":False,
        "original_queue_java_source_complete":True,
        "entire_v309_client_compiled":False,
        "source_publication_authorized":False,
    }


def overlay_original_queue_java(previous_zip,queue_zip,fresh_zip,*,
                                previous_sha256,queue_source_sha256,
                                expected_previous_java=1279,
                                queue_owner="rs/h"):
    if (sha_file(previous_zip)!=previous_sha256 or
            sha_file(queue_zip)!=queue_source_sha256):
        raise ValueError("R180_PRIVATE_OVERLAY_SOURCE_SHA_MISMATCH")
    p=Path(fresh_zip)
    if p.exists() or not p.parent.is_dir():
        raise ValueError("R180_OVERLAY_REQUIRES_NEW_PRIVATE_OUTPUT")
    with ZipFile(previous_zip) as z:
        base={x.filename:z.read(x.filename) for x in z.infolist()}
    q=source_members(queue_zip,queue_source_sha256)
    key="recovered-source/v309/src/"+queue_owner+".java"
    if (len(base)!=expected_previous_java or len(q)!=1 or
            q[0][0]!=queue_owner+".java" or
            key.casefold() in {name.casefold() for name in base}):
        raise ValueError("R180_ONLY_ONE_NEW_ORIGINAL_QUEUE_OWNER_ALLOWED")
    with ZipFile(p,"w",ZIP_DEFLATED) as out:
        for path,content in sorted({**base,key:q[0][1]}.items()):
            out.writestr(path,content)
    with ZipFile(p) as z:
        if len(z.namelist())!=expected_previous_java+1 or any(
                z.read(path)!=body for path,body in base.items()):
            raise ValueError("R180_PRIOR_CANONICAL_JAVA_CHANGED")
    return {
        "canonical_source_files":expected_previous_java+1,
        "prior_source_files_unchanged":True,
        "new_full_original_queue_java_added":True,
        "compiler_only_helper_sources_included":False,
        "whole_client_compiles":False,
        "private_source_tree_sha256":sha_file(p),
    }
