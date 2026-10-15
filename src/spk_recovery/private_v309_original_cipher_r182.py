"""R182: full original-v309 ISAAC cipher (rs/q/a) Java source parity.

Private original source and original client binary MUST be supplied separately
with SHA-256 pins. Hosted CI only builds synthetic test classes. No unverified
compiler helpers, original JAR fallback or original game execution is allowed.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

from .bytecode_profile import profile_class_field_accesses
from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file, source_members
from .private_v309_matrix_source_method_parity_r150 import _strict_inspections


ORIGINAL_OWNER = "rs/q/a"
ORIGINAL_CLASS_SHA256 = (
    "eea77b6d7a3a00c997acd46926005ef5e6fe93cd1d4f06668d62bdee85b3c7d0"
)
EXPECTED_SOURCE_METHODS = 4
EXPECTED_INSTRUCTIONS = 802
EXPECTED_FIELDS = 6


class OriginalCipherR182Error(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise OriginalCipherR182Error(message)


def verify_original_cipher_source(
        original_jar, original_source_zip, *,
        original_sha256=CANONICAL_V309,
        source_sha256, original_owner=ORIGINAL_OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        expected_methods=EXPECTED_SOURCE_METHODS,
        expected_instructions=EXPECTED_INSTRUCTIONS,
        expected_fields=EXPECTED_FIELDS,
        expected_major=53):
    require(sha_file(original_jar)==original_sha256 and
            sha_file(original_source_zip)==source_sha256,
            "R182_EXACT_ORIGINAL_OR_JAVA_SOURCE_SHA256_MISMATCH")
    source=source_members(original_source_zip,source_sha256)
    require(len(source)==1 and source[0][0]==original_owner+".java" and
            0<len(source[0][1])<=100_000,
            "R182_ONE_EXACT_ORIGINAL_OWNER_SOURCE_FILE_REQUIRED")
    with ZipFile(original_jar) as jar:
        path=original_owner+".class"
        require(jar.namelist().count(path)==1,
                "R182_ORIGINAL_CLASSFILE_NOT_UNIQUE")
        original_bytes=jar.read(path)
    require(hashlib.sha256(original_bytes).hexdigest()==original_class_sha256,
            "R182_ORIGINAL_CLASSFILE_SHA256_CHANGED")
    original=parse_class(original_bytes)
    require(original.name==original_owner and
            original.super_name=="java/lang/Object" and
            original.major==expected_major and
            len(original.fields)==expected_fields and
            len(original.methods)==expected_methods,
            "R182_ORIGINAL_JVM_OWNER_CLASS_ABI_CHANGED")
    javac=shutil.which("javac")
    require(javac is not None,"R182_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r182-source-") as tmp:
        root=Path(tmp)
        src=root/"src"/source[0][0]
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_bytes(source[0][1])
        out=root/"classes"
        empty=root/"empty"
        out.mkdir()
        empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            result=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),str(src)
            ],cwd=root,env=env,stdin=subprocess.DEVNULL,
               capture_output=True,timeout=90,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise OriginalCipherR182Error(
                "R182_SOURCE_ONLY_JAVA_COMPILATION_ABORTED") from exc
        produced={p.relative_to(out).as_posix()
                  for p in out.rglob("*.class")}
        require(result.returncode==0 and
                produced=={original_owner+".class"},
                "R182_ORIGINAL_SOURCE_ONLY_BUILD_NOT_CLOSED")
        rebuilt_bytes=(out/(original_owner+".class")).read_bytes()
    rebuilt=parse_class(rebuilt_bytes)
    require((original.name,original.super_name,original.access,
             original.major,original.interfaces)==
            (rebuilt.name,rebuilt.super_name,rebuilt.access,
             rebuilt.major,rebuilt.interfaces),
            "R182_ORIGINAL_JVM_CLASS_METADATA_NOT_EQUAL")
    fields=lambda cls:sorted(
        (f["name"],f["descriptor"],f["access"]) for f in cls.fields)
    require(fields(original)==fields(rebuilt) and
            len(fields(original))==expected_fields,
            "R182_ORIGINAL_CIPHER_FIELDS_NOT_EQUAL")
    left=profile_class_field_accesses(original_bytes)
    right=profile_class_field_accesses(rebuilt_bytes)
    identifiers=lambda cls:{(x["name"],x["descriptor"])
                            for x in cls["methods"]}
    methods=sorted(identifiers(left))
    require(len(methods)==expected_methods and
            identifiers(right)==set(methods) and
            all(x["code_length"] is not None for x in left["methods"]),
            "R182_ORIGINAL_METHOD_INVENTORY_NOT_COMPLETE")
    try:
        proof=_strict_inspections(left,right,selected=methods)
    except ValueError as exc:
        raise OriginalCipherR182Error(
            "R182_ORIGINAL_CIPHER_JVM_CODE_NOT_EQUAL") from exc
    require(proof["verified_selected_method_count"]==expected_methods
            and proof["matched_opcode_count"]==expected_instructions
            and proof["all_selected_core_method_code_equal"],
            "R182_ORIGINAL_CIPHER_JVM_CODE_NOT_EQUAL")
    require(sha_file(original_jar)==original_sha256 and
            sha_file(original_source_zip)==source_sha256,
            "R182_SOURCE_OR_BINARY_CHANGED_DURING_VERIFICATION")
    return {
        "schema_version":1,
        "kind":"v309_original_cipher_rs_q_a_full_java_source_r182",
        "original_cipher_class_sha256":original_class_sha256,
        "original_private_source_sha256":source_sha256,
        "complete_original_methods_compiled":expected_methods,
        "matching_original_jvm_instructions":expected_instructions,
        "original_field_abi_verified":True,
        "original_class_super_version_access_verified":True,
        "source_only_no_original_or_external_binary_fallback":True,
        "original_jvm_classfile_bytes_identical":original_bytes==rebuilt_bytes,
        "original_client_code_executed":False,
        "full_v309_client_compiles":False,
        "source_redistribution_authorized":False,
    }


def overlay_verified_cipher_source(
        original_tree_zip, verified_cipher_source_zip, fresh_output_zip, *,
        original_tree_sha256, verified_source_sha256,
        expected_previous_java=1278, original_owner=ORIGINAL_OWNER):
    """Exact-byte overlay into a private canonical-source ZIP, no mutation."""
    require(sha_file(original_tree_zip)==original_tree_sha256 and
            sha_file(verified_cipher_source_zip)==verified_source_sha256,
            "R182_PRIVATE_SOURCE_TREE_INPUT_SHA_MISMATCH")
    target=Path(fresh_output_zip)
    require(not target.exists() and not target.is_symlink() and
            target.parent.is_dir() and not target.parent.is_symlink(),
            "R182_FRESH_PRIVATE_OUTPUT_REQUIRED")
    sources=source_members(verified_cipher_source_zip,
                           verified_source_sha256)
    require(len(sources)==1 and sources[0][0]==original_owner+".java",
            "R182_ONE_ACCEPTED_CIPHER_SOURCE_OWNER_REQUIRED")
    prefix="recovered-source/v309/src/"
    with ZipFile(original_tree_zip) as zipped:
        infos=zipped.infolist()
        paths=[item.filename for item in infos]
        require(len(infos)==expected_previous_java and
                len(paths)==len(set(paths)) and
                len(paths)==len({name.casefold() for name in paths}) and
                all(x.startswith(prefix) and x.endswith(".java")
                    and not x.startswith("/") and "\\" not in x
                    and not any(s in ("",".","..") for s in x.split("/"))
                    for x in paths) and
                all(not x.is_dir() and
                    ((x.external_attr>>16)&0o170000)!=0o120000
                    for x in infos),
                "R182_ORIGINAL_TREE_MANIFEST_NOT_CANONICAL")
        unchanged={name:zipped.read(name) for name in paths}
    key=prefix+original_owner+".java"
    require(key.casefold() not in {name.casefold() for name in unchanged},
            "R182_ALREADY_CONTAINS_ORIGINAL_CIPHER_SOURCE")
    with ZipFile(target,"w",ZIP_DEFLATED) as output:
        for name in sorted([*unchanged,key]):
            output.writestr(name,
                            sources[0][1] if name==key else unchanged[name])
    with ZipFile(target) as verify:
        require(len(verify.namelist())==expected_previous_java+1 and
                verify.read(key)==sources[0][1] and
                all(verify.read(p)==v for p,v in unchanged.items()),
                "R182_OVERLAY_PRESERVATION_PROOF_FAILED")
    return {
        "schema_version":1,
        "new_private_recovered_java_files":expected_previous_java+1,
        "unchanged_previous_java_files":expected_previous_java,
        "added_original_cipher_source":True,
        "original_cipher_source_fully_verified_by_overlay_alone":False,
        "whole_client_compilation_passed":False,
        "private_tree_sha256":sha_file(target),
    }
