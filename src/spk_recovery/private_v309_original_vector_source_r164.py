"""R164 — original-v309 vector helper, independently restored from Java source.

Verify the exact original JVM class against an isolated Java 9 source rebuild.
No original client binaries on javac classpath. Verify ALL original methods,
fields and instructions; compare StackMap metadata separately, never assume
runtime equivalence, original source licensing, or full client compilation.

Optionally create a PRIVATE canonical source-tree overlay with one new
verified source owner, without copying any compiler-only scaffolds.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

from .classfile import parse_class
from .bytecode_profile import profile_class_field_accesses
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file, source_members
from .private_v309_matrix_source_method_parity_r150 import (
    _strict_inspections, _self_call_closure_for_selected,
)

VECTOR_SHA = "64f3e4ee692bb549129e2a41342beae83ac94edd28296b88a7694777268334b0"


class R164OriginalVectorError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise R164OriginalVectorError(reason)


def verify_original_vector_java(original_jar, vector_java_zip, *,
                                original_sha256=CANONICAL_V309,
                                vector_source_sha256,
                                original_owner="com/a/b/a/e",
                                original_class_sha256=VECTOR_SHA,
                                expected_methods=5, expected_fields=3,
                                expected_instructions=80):
    require(sha_file(original_jar)==original_sha256 and
            sha_file(vector_java_zip)==vector_source_sha256,
            "R164_PINNED_ORIGINAL_OR_JAVA_SOURCE_HASH_MISMATCH")
    require(1<=expected_methods<=32 and 1<=expected_fields<=32
            and expected_instructions>0 and original_owner.count("/")>=2
            and all(p and p.replace("_","").isalnum()
                    for p in original_owner.split("/")),
            "R164_UNSAFE_ORIGINAL_VECTOR_OWNER_OR_BOUNDS")
    candidate=source_members(vector_java_zip,vector_source_sha256)
    require(len(candidate)==1 and
            candidate[0][0]==original_owner+".java" and
            0<len(candidate[0][1])<=100_000,
            "R164_EXACT_SINGLE_ORIGINAL_OWNER_JAVA_REQUIRED")
    with ZipFile(original_jar) as original:
        entry=original_owner+".class"
        require(original.namelist().count(entry)==1,
                "R164_ORIGINAL_JVM_OWNER_NOT_UNIQUE")
        binary=original.read(entry)
    require(hashlib.sha256(binary).hexdigest()==original_class_sha256,
            "R164_ORIGINAL_VECTOR_CLASS_SHA256_MISMATCH")
    javac=shutil.which("javac")
    require(javac is not None, "R164_TRUSTED_JDK_COMPILER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r164-private-") as folder:
        root=Path(folder)
        source=root/"src"/(original_owner+".java")
        source.parent.mkdir(parents=True,exist_ok=True)
        source.write_bytes(candidate[0][1])
        classes=root/"classes"
        empty=root/"empty"
        classes.mkdir()
        empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            run=subprocess.run(
                [javac,"--release","9","-proc:none","-implicit:none",
                 "-g:none","-classpath",str(empty),"-sourcepath",str(empty),
                 "-d",str(classes),str(source)],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=60,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R164OriginalVectorError(
                "R164_ISOLATED_JAVA_COMPILATION_UNAVAILABLE") from exc
        require(run.returncode==0,
                "R164_ORIGINAL_VECTOR_JAVA_SOURCE_CANNOT_COMPILE")
        generated=classes/(original_owner+".class")
        require({f.relative_to(classes).as_posix()
                 for f in classes.rglob("*.class")} ==
                {original_owner+".class"},
                "R164_UNEXPECTED_COMPILED_CLASS_OWNER")
        rebuilt=generated.read_bytes()
    orig=parse_class(binary)
    compiled=parse_class(rebuilt)
    require(orig.name==compiled.name==original_owner,
            "R164_SOURCE_AND_ORIGINAL_JVM_OWNER_DIFFER")
    f_orig={(f["name"],f["descriptor"],f["access"]) for f in orig.fields}
    f_new={(f["name"],f["descriptor"],f["access"]) for f in compiled.fields}
    require(f_orig==f_new and len(f_orig)==expected_fields,
            "R164_VECTOR_ORIGINAL_FIELD_ABI_DIFFERENT")
    o_profile=profile_class_field_accesses(binary)
    n_profile=profile_class_field_accesses(rebuilt)
    method_orig={(m["name"],m["descriptor"]) for m in o_profile["methods"]}
    method_new={(m["name"],m["descriptor"]) for m in n_profile["methods"]}
    require(method_orig==method_new and len(method_orig)==expected_methods,
            "R164_ALL_ORIGINAL_VECTOR_METHODS_REQUIRED")
    ids=sorted(method_orig)
    parity=_strict_inspections(o_profile,n_profile,selected=ids)
    require(parity["verified_selected_method_count"]==expected_methods
            and parity["matched_opcode_count"]==expected_instructions
            and parity["all_selected_core_method_code_equal"],
            "R164_ORIGINAL_VECTOR_JVM_CODE_NOT_IDENTICAL")
    original_edges=_self_call_closure_for_selected(o_profile,ids,original_owner)
    rebuilt_edges=_self_call_closure_for_selected(n_profile,ids,original_owner)
    require(original_edges==rebuilt_edges,
            "R164_SOURCE_SELF_CALL_CLOSURE_DIFFERS")
    require(sha_file(original_jar)==original_sha256 and
            sha_file(vector_java_zip)==vector_source_sha256,
            "R164_PRIVATE_INPUT_CHANGED_DURING_BUILD")
    return {
        "schema_version":1,
        "kind":"private_v309_original_vector_full_java_source_r164",
        "original_client_sha256":original_sha256,
        "original_vector_class_sha256":original_class_sha256,
        "original_vector_java_source_sha256":vector_source_sha256,
        "original_source_recompiled_jvm_class_sha256":
            hashlib.sha256(rebuilt).hexdigest(),
        "full_original_vector_field_count":len(f_orig),
        "full_original_vector_method_count":len(method_orig),
        "original_recompiled_jvm_instruction_count":
            parity["matched_opcode_count"],
        "original_recompiled_method_code_equal":True,
        "original_self_calls_closed":original_edges,
        "stackmap_representations_equal":
            parity["all_selected_stackmap_representations_equal"],
        "original_classfile_byte_identical":binary==rebuilt,
        "no_original_binary_compiler_fallback":True,
        "private_java_source_publication_authorized":False,
        "full_original_v309_client_compiles":False,
    }


def private_vector_source_overlay(baseline_zip, vector_java_zip, output_zip, *,
                                  baseline_sha256, vector_source_sha256,
                                  expected_original_files=1272,
                                  expected_vector_source_rel="com/a/b/a/e.java"):
    require(sha_file(baseline_zip)==baseline_sha256 and
            sha_file(vector_java_zip)==vector_source_sha256,
            "R164_OVERLAY_INPUT_PIN_MISMATCH")
    target=Path(output_zip)
    require(not target.exists() and target.parent.is_dir(),
            "R164_PRIVATE_NEW_OVERLAY_PATH_REQUIRED")
    with ZipFile(baseline_zip) as original:
        base={i.filename:original.read(i.filename) for i in original.infolist()}
    prefix="recovered-source/v309/src/"
    require(len(base)==expected_original_files and
            all(k.startswith(prefix) and k.endswith(".java")
                and ".." not in k.split("/") for k in base),
            "R164_CANONICAL_SOURCE_ARCHIVE_NOT_EXACT_EXPECTED_TREE")
    v=source_members(vector_java_zip,vector_source_sha256)
    require(len(v)==1 and v[0][0]==expected_vector_source_rel,
            "R164_VECTOR_OWNER_SOURCE_NOT_EXPECTED")
    new=prefix+v[0][0]
    require(new.casefold() not in {k.casefold() for k in base},
            "R164_MUST_NOT_OVERWRITE_EXISTING_RECOVERED_JAVA")
    with ZipFile(target,"w",ZIP_DEFLATED,compresslevel=6) as out:
        for k,val in sorted(base.items()):
            out.writestr(k,val)
        out.writestr(new,v[0][1])
    with ZipFile(target) as verify:
        names=verify.namelist()
        require(len(names)==expected_original_files+1 and
                len(set(n.casefold() for n in names))==len(names)
                and all(verify.read(k)==val for k,val in base.items())
                and verify.read(new)==v[0][1],
                "R164_OVERLAY_ALTERED_PRIOR_JAVA_FILES")
    require(sha_file(baseline_zip)==baseline_sha256 and
            sha_file(vector_java_zip)==vector_source_sha256,
            "R164_OVERLAY_INPUT_CHANGED")
    return {"original_java_files_preserved":expected_original_files,
            "new_proven_original_vector_java_added":True,
            "new_client_java_file_count":expected_original_files+1,
            "output_private_source_tree_zip_sha256":sha_file(target),
            "source_only_unverified_helpers_added":False,
            "entire_v309_client_compiles":False}
