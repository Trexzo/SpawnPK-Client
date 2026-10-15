"""R178: original v309 Packet 73 selected method bodies from Java source.

Requires original rs/t and rs/a superclass Java-source proof and exact
source-only rs/q/a owner signature (unverified implementation). Compiles
the private Packet Java source without the original client JAR on javac's
classpath. Requires all 73 selected original method identities, access
flags and JVM Code instructions; explicitly rejects full-class acceptance.
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

PACKET_CLASS_SHA = "b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2"
PARENT_CLASS_SHAS = {
    "rs/t": "430c61233ef1d46a3dadbe4947a3d4d17019db2bc1d4678dc732623ea1b3274f",
    "rs/a": "7c33983b6e49dc2cd8b4b5bde2bd0550a4977c1eaa483025630b5c16105e735f",
}
MISSING_ORIGINAL_PACKET_METHODS = frozenset((
    ("M", "()V"), ("a", "(I)V"), ("a", "(J)V"),
    ("c", "()Lrs/x/e;"), ("c", "(I)I"),
    ("g", "(I)V"), ("k", "(I)I"), ("<clinit>", "()V"),
))


class R178OriginalPacketSourceError(ValueError):
    pass


def require(ok, why):
    if not ok:
        raise R178OriginalPacketSourceError(why)


def verify_original_packet_73(
        original_jar, private_packet_java_zip, original_parent_java_zip,
        private_signature_only_java_zip, *,
        original_sha256=CANONICAL_V309,
        packet_source_sha256, parent_source_sha256, signature_source_sha256,
        original_owner="rs/x/e", original_class_sha256=PACKET_CLASS_SHA,
        original_parent_class_shas=None, helper_owner="rs/q/a",
        remaining_original_methods=MISSING_ORIGINAL_PACKET_METHODS,
        selected_method_count=73, selected_instructions=1727,
        original_total_noninitializer_methods=80,
        expected_parent_instructions=48, expected_parent_methods=4):
    inputs=((original_jar,original_sha256),
            (private_packet_java_zip,packet_source_sha256),
            (original_parent_java_zip,parent_source_sha256),
            (private_signature_only_java_zip,signature_source_sha256))
    require(all(sha_file(path)==digest for path,digest in inputs),
            "R178_SHA_PINNED_ORIGINAL_OR_JAVA_SOURCE_MISMATCH")
    require(remaining_original_methods and
            ("<clinit>","()V") in remaining_original_methods and
            selected_method_count>0 and selected_instructions>0,
            "R178_MISSING_METHOD_INVENTORY_NOT_EXPLICIT")
    parent_class_shas=original_parent_class_shas or PARENT_CLASS_SHAS
    parent=verify_original_packet_parents(
        original_jar,original_parent_java_zip,
        original_sha256=original_sha256,
        source_sha256=parent_source_sha256,
        original_class_shas=parent_class_shas,
        expected_methods=expected_parent_methods,
        expected_instructions=expected_parent_instructions)
    require(parent["complete_original_parent_classes_source_built"]==2,
            "R178_ORIGINAL_PACKET_PARENTS_NOT_VERIFIED")
    source=source_members(private_packet_java_zip,packet_source_sha256)
    parents=source_members(original_parent_java_zip,parent_source_sha256)
    helper=source_members(private_signature_only_java_zip,
                          signature_source_sha256)
    require(len(source)==1 and source[0][0]==original_owner+".java" and
            len(parents)==2 and
            {name for name,_ in parents}=={"rs/t.java","rs/a.java"} and
            len(helper)==1 and helper[0][0]==helper_owner+".java",
            "R178_REQUIRE_ORIGINAL_PACKET_PARENTS_AND_ONE_HELPER_TYPE")
    with ZipFile(original_jar) as z:
        require(z.namelist().count(original_owner+".class")==1 and
                z.namelist().count(helper_owner+".class")==1,
                "R178_ORIGINAL_CLASS_OWNER_NOT_PROVEN")
        binary=z.read(original_owner+".class")
    require(hashlib.sha256(binary).hexdigest()==original_class_sha256,
            "R178_ORIGINAL_PACKET_OWNER_SHA_DRIFT")
    original_class=parse_class(binary)
    require(original_class.name==original_owner and
            original_class.super_name=="rs/a",
            "R178_ORIGINAL_PACKET_SUPERCLASS_IDENTITY_DIFFERS")
    java=shutil.which("javac")
    require(java is not None,"R178_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r178-") as tmp:
        root=Path(tmp)
        java_files=[]
        for path,body in [*source,*parents,*helper]:
            require(path.endswith(".java") and
                    ".." not in path.split("/") and
                    "\\" not in path and len(body)<=150_000,
                    "R178_UNSAFE_ORIGINAL_SOURCE_PATH")
            target=root/"src"/path
            require(not target.exists(),
                    "R178_DUPLICATE_SOURCE_OWNER")
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(body)
            java_files.append(target)
        classes=root/"classes"
        empty=root/"empty"
        classes.mkdir()
        empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            p=subprocess.run(
                [java,"--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(classes),
                 *[str(path) for path in java_files]],
                env=env,cwd=root,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=90,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R178OriginalPacketSourceError(
                "R178_STANDALONE_JAVAC_UNAVAILABLE") from exc
        emitted={path.relative_to(classes).as_posix()
                 for path in classes.rglob("*.class")}
        expected_classes={original_owner+".class",
                          helper_owner+".class","rs/t.class","rs/a.class"}
        require(p.returncode==0 and emitted==expected_classes,
                "R178_SOURCE_ONLY_COMPILE_NOT_ACCEPTED")
        rebuilt=(classes/(original_owner+".class")).read_bytes()
    built_class=parse_class(rebuilt)
    require(built_class.name==original_class.name and
            built_class.super_name==original_class.super_name and
            built_class.major==original_class.major,
            "R178_ORIGINAL_PACKET_SUPERCLASS_OR_JAVA_VERSION_DIFFERS")
    old=profile_class_field_accesses(binary)
    new=profile_class_field_accesses(rebuilt)
    old_ids={(m["name"],m["descriptor"]) for m in old["methods"]}
    new_ids={(m["name"],m["descriptor"]) for m in new["methods"]}
    selected=old_ids-set(remaining_original_methods)
    require(len(old_ids-set([("<clinit>","()V")]))==
            original_total_noninitializer_methods and
            len(selected)==selected_method_count and
            new_ids==selected and selected.issubset(old_ids),
            "R178_SELECTION_EXCLUDES_WRONG_ORIGINAL_METHOD_SET")
    result=_strict_inspections(old,new,selected=sorted(selected))
    require(result["verified_selected_method_count"]==
            selected_method_count and
            result["matched_opcode_count"]==selected_instructions and
            result["all_selected_core_method_code_equal"],
            "R178_73_SELECTED_ORIGINAL_JVM_METHOD_CODE_NOT_EQUAL")
    require(all(sha_file(path)==digest for path,digest in inputs),
            "R178_ORIGINAL_OR_JAVA_SOURCE_CHANGED_DURING_COMPILATION")
    return {
        "schema_version":1,
        "kind":"v309_partial_packet_73_original_java_methods_r178",
        "original_packet_class_sha256":original_class_sha256,
        "original_packet_parent_classes_java_verified":2,
        "selected_original_packet_method_count":selected_method_count,
        "matching_selected_original_jvm_instructions":selected_instructions,
        "remaining_unverified_original_method_count":
            len(remaining_original_methods)-1,
        "original_static_initializer_recovered":False,
        "original_rs_q_a_helper_body_proven":False,
        "original_binary_compiler_fallback_used":False,
        "full_original_packet_class_recovered":False,
        "canonical_client_source_tree_modified":False,
        "complete_client_compilation_passed":False,
        "source_redistribution_authorized":False,
    }
