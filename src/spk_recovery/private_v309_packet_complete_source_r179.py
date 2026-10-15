"""R179: complete original v309 Packet Java source method-ABI and Code proof.

Independently source-compiles rs/x/e with recovered Java rs/a and rs/t
and four type-signature-only Java auxiliary classes. No original client
or third-party classfiles enter the compiler classpath. Require ALL
original methods, class initializer, fields, and 2,296 JVM instructions.
Helper source method implementations remain UNVERIFIED and are excluded
from canonical recovered client source.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file, source_members
from .private_v309_matrix_source_method_parity_r150 import _strict_inspections
from .private_v309_packet_parent_source_r177 import verify_original_packet_parents

ORIGINAL_PACKET_SHA="b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2"
PARENT_SHAS={
    "rs/t":"430c61233ef1d46a3dadbe4947a3d4d17019db2bc1d4678dc732623ea1b3274f",
    "rs/a":"7c33983b6e49dc2cd8b4b5bde2bd0550a4977c1eaa483025630b5c16105e735f",
}
COMPILER_ONLY_HELPERS=("rs/q/a","rs/v/a","rs/h","rs/f/a")


class OriginalPacketCompleteR179Error(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise OriginalPacketCompleteR179Error(reason)


def verify_original_complete_packet_java(
        original_jar, packet_source_zip, verified_parent_source_zip,
        compiler_only_helper_source_zip, *,
        original_sha256=CANONICAL_V309,
        packet_source_sha256,parent_source_sha256,helpers_source_sha256,
        original_owner="rs/x/e",original_class_sha256=ORIGINAL_PACKET_SHA,
        parent_class_shas=None,
        original_helper_owners=COMPILER_ONLY_HELPERS,
        expected_method_count=81,expected_opcode_count=2296,
        expected_field_count=11,
        expected_parent_method_count=4,
        expected_parent_opcode_count=48):
    pins=((original_jar,original_sha256),
          (packet_source_zip,packet_source_sha256),
          (verified_parent_source_zip,parent_source_sha256),
          (compiler_only_helper_source_zip,helpers_source_sha256))
    require(all(sha_file(path)==pin for path,pin in pins),
            "R179_SHA_PINNED_PRIVATE_INPUT_MISMATCH")
    require(expected_method_count>1 and expected_opcode_count>0 and
            expected_field_count>0 and len(original_helper_owners)>=1 and
            len(set(original_helper_owners))==len(original_helper_owners) and
            original_owner not in original_helper_owners,
            "R179_ORIGINAL_BOUNDED_METHOD_OR_HELPER_PROOF_INVALID")
    parents=verify_original_packet_parents(
        original_jar,verified_parent_source_zip,
        original_sha256=original_sha256,
        source_sha256=parent_source_sha256,
        original_class_shas=parent_class_shas or PARENT_SHAS,
        expected_methods=expected_parent_method_count,
        expected_instructions=expected_parent_opcode_count)
    require(parents["complete_original_parent_classes_source_built"]==2,
            "R179_TWO_ORIGINAL_PARENT_JAVA_SOURCE_OWNERS_NOT_VERIFIED")
    candidate=source_members(packet_source_zip,packet_source_sha256)
    parent_sources=source_members(verified_parent_source_zip,parent_source_sha256)
    helpers=source_members(compiler_only_helper_source_zip,
                           helpers_source_sha256)
    require(len(candidate)==1 and
            candidate[0][0]==original_owner+".java" and
            len(parent_sources)==2 and
            {x for x,_ in parent_sources}=={"rs/t.java","rs/a.java"} and
            len(helpers)==len(original_helper_owners) and
            {x for x,_ in helpers}==
                {owner+".java" for owner in original_helper_owners},
            "R179_EXACT_PRIVATE_JAVA_SOURCE_OWNER_PARTITION_REQUIRED")
    with ZipFile(original_jar) as original:
        index=original.namelist()
        for owner in (original_owner,*original_helper_owners):
            require(index.count(owner+".class")==1,
                    "R179_JVM_ORIGINAL_SOURCE_OWNER_NOT_PROVEN")
        original_bytes=original.read(original_owner+".class")
    require(hashlib.sha256(original_bytes).hexdigest()==
            original_class_sha256,
            "R179_ORIGINAL_PACKET_CLASS_HASH_CHANGED")
    original_cls=parse_class(original_bytes)
    require(original_cls.name==original_owner and
            original_cls.super_name=="rs/a" and original_cls.major==53,
            "R179_ORIGINAL_PACKET_OWNER_SUPERCHAIN_JAVA_VERSION_INVALID")
    javac=shutil.which("javac")
    require(javac is not None,"R179_TRUSTED_JAVA9_COMPILER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r179-private-source-") as d:
        root=Path(d)
        source_files=[]
        for relative,body in [*candidate,*parent_sources,*helpers]:
            require(relative.endswith(".java") and
                    "\\" not in relative and
                    ".." not in relative.split("/") and
                    len(body)<=150000,
                    "R179_UNSAFE_COMPILER_SOURCE_PATH")
            file=root/"src"/relative
            require(not file.exists(),"R179_DUPLICATE_JAVA_SOURCE_IDENTITY")
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_bytes(body)
            source_files.append(file)
        out=root/"classes"
        empty=root/"empty"
        out.mkdir()
        empty.mkdir()
        env=os.environ.copy()
        for k in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                  "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(k,None)
        try:
            built=subprocess.run(
                [javac,"--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),
                 *[str(p) for p in source_files]],
                env=env,cwd=root,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=120,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise OriginalPacketCompleteR179Error(
                "R179_JAVA_COMPILATION_FAILED_TO_COMPLETE") from exc
        expected_owners={original_owner,"rs/t","rs/a",
                         *original_helper_owners}
        emitted={p.relative_to(out).as_posix()
                 for p in out.rglob("*.class")}
        require(built.returncode==0 and
                emitted=={name+".class" for name in expected_owners},
                "R179_COMPLETE_ORIGINAL_PACKET_SOURCE_NOT_COMPILABLE")
        rebuilt_bytes=(out/(original_owner+".class")).read_bytes()
    new_cls=parse_class(rebuilt_bytes)
    require((original_cls.name,original_cls.super_name,original_cls.access,
             original_cls.major)==
            (new_cls.name,new_cls.super_name,new_cls.access,new_cls.major),
            "R179_COMPLETE_ORIGINAL_PACKET_JVM_CLASS_IDENTITY_DIFFERS")
    field_ids=lambda c:{
        (f["name"],f["descriptor"],f["access"]) for f in c.fields}
    require(len(field_ids(original_cls))==expected_field_count and
            field_ids(original_cls)==field_ids(new_cls),
            "R179_ORIGINAL_PACKET_FULL_FIELD_ABI_NOT_EQUAL")
    original=profile_class_field_accesses(original_bytes)
    rebuilt=profile_class_field_accesses(rebuilt_bytes)
    ids=lambda c:{(m["name"],m["descriptor"]) for m in c["methods"]}
    selected=sorted(ids(original))
    require(len(selected)==expected_method_count and
            ids(rebuilt)==set(selected) and
            ("<clinit>","()V") in selected,
            "R179_PACKET_ALL_ORIGINAL_CONSTRUCTORS_METHODS_CLINIT_REQUIRED")
    parity=_strict_inspections(original,rebuilt,selected=selected)
    require(parity["verified_selected_method_count"]==expected_method_count and
            parity["matched_opcode_count"]==expected_opcode_count and
            parity["all_selected_core_method_code_equal"],
            "R179_COMPLETE_ORIGINAL_PACKET_JVM_INSTRUCTIONS_NOT_EQUAL")
    require(all(sha_file(path)==pin for path,pin in pins),
            "R179_ORIGINAL_PRIVATE_SOURCE_CHANGED_DURING_VERIFICATION")
    return {
        "schema_version":1,
        "kind":"v309_original_packet_complete_java_source_code_r179",
        "original_packet_class_sha256":original_class_sha256,
        "verified_original_jvm_methods_including_initializer":expected_method_count,
        "matched_original_jvm_instructions":expected_opcode_count,
        "complete_packet_original_field_abi_verified":True,
        "original_packet_superclass_source_verified":True,
        "source_only_compiler_helper_count":len(helpers),
        "source_only_helper_bodies_verified_original":False,
        "original_client_binary_compiler_fallback":False,
        "original_classfile_byte_identical":
            original_bytes==rebuilt_bytes,
        "entire_original_v309_client_compiles":False,
        "derived_source_redistribution_authorized":False,
    }
