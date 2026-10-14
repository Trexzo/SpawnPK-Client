"""R165: recover entire original v309 angle/trigonometry helper Java source.

Original class Java9 Code, method/field ABI and all public static final
ConstantValue literals must match. Previously only a compilation-only stub.
No original binary on javac classpath and no original source in GitHub.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import source_members, sha_file
from .private_v309_original_vector_source_r164 import (
    verify_original_vector_java, private_vector_source_overlay,
)

ANGLE_CLASS_SHA = "6b60fd4224532042707da6eda83c17879d0c5fcb0aaa478b9fcc035ed6bdda6b"


class R165OriginalAngleError(ValueError):
    pass


def require(ok,reason):
    if not ok:
        raise R165OriginalAngleError(reason)


def verify_original_angle_java(original_jar, angle_java_zip, *,
                               original_sha256=CANONICAL_V309,
                               angle_source_sha256,
                               original_owner="com/a/b/a/d",
                               class_sha256=ANGLE_CLASS_SHA,
                               expected_methods=6,
                               expected_fields=10,
                               expected_instructions=81):
    # Full original Code and exact field/method inventory, no binary fallback.
    code=verify_original_vector_java(
        original_jar,angle_java_zip,
        original_sha256=original_sha256,
        vector_source_sha256=angle_source_sha256,
        original_owner=original_owner,
        original_class_sha256=class_sha256,
        expected_methods=expected_methods,
        expected_fields=expected_fields,
        expected_instructions=expected_instructions)
    source=source_members(angle_java_zip,angle_source_sha256)
    require(len(source)==1 and source[0][0]==original_owner+".java",
            "R165_SOURCE_MUST_BE_EXACT_ORIGINAL_ANGLE_OWNER")
    javac=shutil.which("javac")
    javap=shutil.which("javap")
    require(javac is not None and javap is not None,
            "R165_TRUSTED_JDK_REQUIRED")
    env=os.environ.copy()
    for name in ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
        env.pop(name,None)
    with tempfile.TemporaryDirectory(prefix="spk-r165-private-") as tmp:
        root=Path(tmp)
        path=root/"source"/(original_owner+".java")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(source[0][1])
        classes=root/"classes"
        empty=root/"empty"
        classes.mkdir()
        empty.mkdir()
        cmd=[javac,"--release","9","-proc:none","-implicit:none",
             "-g:none","-classpath",str(empty),"-sourcepath",str(empty),
             "-d",str(classes),str(path)]
        try:
            compile_result=subprocess.run(
                cmd,cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=60)
            require(compile_result.returncode==0,
                    "R165_JAVA_SOURCE_NOT_STANDALONE_COMPILABLE")
            class_name=original_owner.replace("/",".")
            def constants(classpath):
                result=subprocess.run(
                    [javap,"-p","-constants","-classpath",str(classpath),
                     class_name],cwd=root,env=env,
                    stdin=subprocess.DEVNULL,capture_output=True,timeout=60)
                require(result.returncode==0 and
                        0<len(result.stdout)<=40000,
                        "R165_JAVAP_CONSTANT_VALUE_INSPECTION_FAILED")
                return result.stdout.decode("utf-8",errors="strict").replace(
                    "\r\n","\n").strip()
            original_decls=constants(original_jar)
            rebuilt_decls=constants(classes)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R165OriginalAngleError(
                "R165_JDK_VERIFICATION_UNAVAILABLE") from exc
        require(original_decls==rebuilt_decls,
                "R165_ORIGINAL_STATIC_FINAL_CONSTANT_VALUES_NOT_EQUAL")
    require(sha_file(original_jar)==original_sha256 and
            sha_file(angle_java_zip)==angle_source_sha256,
            "R165_PRIVATE_ORIGINAL_INPUT_CHANGED")
    return {
        "schema_version":1,
        "kind":"private_v309_original_angle_helper_source_r165",
        "original_class_sha256":class_sha256,
        "private_java_source_sha256":angle_source_sha256,
        "verified_original_jvm_method_count":expected_methods,
        "verified_original_jvm_instruction_count":expected_instructions,
        "original_field_abi_complete":True,
        "all_original_static_final_constants_equal":True,
        "isolated_java_source_only_compiler_passed":True,
        "original_binary_used_as_compiler_dependency":False,
        "original_classfile_byte_identical":
            code["original_classfile_byte_identical"],
        "complete_client_compiled":False,
        "original_java_source_publication_authorized":False,
    }


def verified_private_source_tree_overlay(original_jar,angle_java_zip,
                                         previous_tree_zip,new_tree_zip,*,
                                         angle_source_sha256,
                                         previous_tree_sha256,
                                         original_sha256=CANONICAL_V309,
                                         original_owner="com/a/b/a/d",
                                         original_class_sha256=ANGLE_CLASS_SHA,
                                         expected_methods=6,expected_fields=10,
                                         expected_instructions=81,
                                         expected_prior_java=1273):
    evidence=verify_original_angle_java(
        original_jar,angle_java_zip,
        original_sha256=original_sha256,
        angle_source_sha256=angle_source_sha256,
        original_owner=original_owner,
        class_sha256=original_class_sha256,
        expected_methods=expected_methods,
        expected_fields=expected_fields,
        expected_instructions=expected_instructions)
    overlay=private_vector_source_overlay(
        previous_tree_zip,angle_java_zip,new_tree_zip,
        baseline_sha256=previous_tree_sha256,
        vector_source_sha256=angle_source_sha256,
        expected_original_files=expected_prior_java,
        expected_vector_source_rel=original_owner+".java")
    return {"original_angle_java_evidence":evidence,
            "private_source_tree":overlay,
            "complete_client_compilation_accepted":False}
