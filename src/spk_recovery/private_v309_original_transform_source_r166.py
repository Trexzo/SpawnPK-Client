"""R166: fully reconstruct original v309 12-component transform from private Java.

Requires all original methods, float-field ABI, source-only Java 9 recompile
and exact instruction parity from R164. Additional class-flag + original
invokedynamic string-concat recipe parity is separately enforced here.
Original Java, original JAR and generated source-tree ZIP stay private.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file, source_members
from .private_v309_original_vector_source_r164 import (
    verify_original_vector_java, private_vector_source_overlay,
)

TRANSFORM_SHA = "6b4119f5c96d9ac6d2a2ecd3b0ead16c09539e919df47266820ac3020bbfb709"


class R166OriginalTransformError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise R166OriginalTransformError(reason)


def verify_original_transform_java(original_jar, transform_java_zip, *,
                                   original_sha256=CANONICAL_V309,
                                   transform_source_sha256,
                                   owner="com/a/b/a/a",
                                   original_class_sha256=TRANSFORM_SHA,
                                   expected_methods=8, expected_fields=13,
                                   expected_instructions=401):
    proof=verify_original_vector_java(
        original_jar,transform_java_zip,
        original_sha256=original_sha256,
        vector_source_sha256=transform_source_sha256,
        original_owner=owner,
        original_class_sha256=original_class_sha256,
        expected_methods=expected_methods,
        expected_fields=expected_fields,
        expected_instructions=expected_instructions)
    src=source_members(transform_java_zip,transform_source_sha256)
    require(len(src)==1 and src[0][0]==owner+".java",
            "R166_JAVA_OWNER_MUST_BE_EXACT_TRANSFORM_CLASS")
    with ZipFile(original_jar) as jar:
        original=jar.read(owner+".class")
    javac=shutil.which("javac")
    javap=shutil.which("javap")
    require(javac is not None and javap is not None,
            "R166_REAL_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r166-private-") as tmp:
        root=Path(tmp)
        file=root/"source"/(owner+".java")
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_bytes(src[0][1])
        output=root/"classes"
        empty=root/"empty"
        output.mkdir()
        empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            run=subprocess.run(
                [javac,"--release","9","-proc:none","-implicit:none",
                 "-g:none","-classpath",str(empty),"-sourcepath",str(empty),
                 "-d",str(output),str(file)],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=60)
            require(run.returncode==0,
                    "R166_SOURCE_ONLY_TRANSFORM_JAVA_DID_NOT_COMPILE")
            compiled=(output/(owner+".class")).read_bytes()
            def recipe(classpath):
                r=subprocess.run(
                    [javap,"-p","-v","-classpath",str(classpath),
                     owner.replace("/",".")],
                    cwd=root,env=env,stdin=subprocess.DEVNULL,
                    capture_output=True,timeout=60)
                require(r.returncode==0,
                        "R166_TRUSTED_STRING_CONCAT_BOOTSTRAP_INSPECTION_FAILED")
                lines=r.stdout.decode("utf-8",errors="strict").replace(
                    "\r\n","\n").splitlines()
                # Extract StringConcatFactory recipe and all method arguments
                # without any constant-pool index dependence.
                output=[]
                for i,line in enumerate(lines):
                    if "REF_invokeStatic java/lang/invoke/StringConcatFactory." in line:
                        output.append(line.split("REF_invokeStatic ",1)[1].strip())
                        for next_line in lines[i+1:i+8]:
                            if next_line.strip().startswith("Method arguments:"):
                                continue
                            if next_line.strip().startswith("#") and " " in next_line:
                                output.append(next_line.strip().split(" ",1)[1])
                            elif output and (
                                next_line.startswith("InnerClasses:") or
                                next_line.startswith("  public ") or
                                next_line.startswith("  private ")):
                                break
                return output
            original_recipe=recipe(original_jar)
            rebuilt_recipe=recipe(output)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R166OriginalTransformError(
                "R166_TRUSTED_JDK_INVOCATION_UNAVAILABLE") from exc
    original_abi=parse_class(original)
    rebuilt_abi=parse_class(compiled)
    require(original_abi.access==rebuilt_abi.access and
            original_abi.super_name==rebuilt_abi.super_name and
            original_abi.interfaces==rebuilt_abi.interfaces,
            "R166_ORIGINAL_TRANSFORM_JVM_CLASS_FLAGS_DIFFER")
    require(original_recipe==rebuilt_recipe,
            "R166_ORIGINAL_STRING_CONCAT_BOOTSTRAP_RECIPE_DIFFERS")
    require(sha_file(original_jar)==original_sha256 and
            sha_file(transform_java_zip)==transform_source_sha256,
            "R166_EXACT_PRIVATE_SOURCE_PIN_CHANGED")
    return {
        "schema_version":1,
        "kind":"private_v309_original_transform_java_r166",
        "original_client_jar_sha256":original_sha256,
        "original_transform_class_sha256":original_class_sha256,
        "private_recovered_transform_java_zip_sha256":transform_source_sha256,
        "verified_transform_field_count":expected_fields,
        "verified_all_original_method_count":expected_methods,
        "verified_all_original_jvm_instructions":expected_instructions,
        "original_class_flags_super_and_interfaces_equal":True,
        "original_string_concatenation_bootstrap_recipe_equal":True,
        "java9_source_only_full_transform_compilation_passed":True,
        "original_transform_classfile_byte_identical":
            original==compiled,
        "original_external_binary_compiler_fallback":False,
        "whole_original_v309_client_compiles":False,
        "recovered_java_redistribution_authorized":False,
    }


def verify_and_overlay_transform(original_jar,java_zip,previous_tree,
                                 fresh_private_tree, *,
                                 java_sha256,previous_tree_sha256,
                                 original_sha256=CANONICAL_V309,
                                 owner="com/a/b/a/a",
                                 original_class_sha256=TRANSFORM_SHA,
                                 expected_methods=8,expected_fields=13,
                                 expected_instructions=401,
                                 expected_previous_sources=1274):
    proof=verify_original_transform_java(
        original_jar,java_zip,
        original_sha256=original_sha256,
        transform_source_sha256=java_sha256,
        owner=owner,
        original_class_sha256=original_class_sha256,
        expected_methods=expected_methods,
        expected_fields=expected_fields,
        expected_instructions=expected_instructions)
    overlay=private_vector_source_overlay(
        previous_tree,java_zip,fresh_private_tree,
        baseline_sha256=previous_tree_sha256,
        vector_source_sha256=java_sha256,
        expected_original_files=expected_previous_sources,
        expected_vector_source_rel=owner+".java")
    return {"original_transform_java":proof,
            "private_canonical_source_overlay":overlay,
            "full_original_client_build_verified":False}
