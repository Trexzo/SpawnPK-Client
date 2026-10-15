"""R168: exact original v309 five-class recovered math SOURCE closure.

Read-only original-client authority. Compile only five exact original-named
reconstructed Java owners and one explicit game-owned Packet type *source*
stub. No original classfile, third-party binary, or original client Jar is
supplied as a compile dependency. Verify ALL Code across the 5 owners, their
field/method/class ABI, and the exact 54-method/4656-instruction frontier.

Original code, Java files, Packet type signatures and JAR remain PRIVATE.
The Packet compiler-only source implementation is NEVER accepted as original.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import source_members, sha_file
from .private_v309_dependency_closure_r136 import audit_pinned_original_jar
from .private_v309_matrix_source_method_parity_r150 import (
    _strict_inspections, _self_call_closure_for_selected,
)

MATH_CLASS_SHA256 = {
    "com/a/b/a/a": "6b4119f5c96d9ac6d2a2ecd3b0ead16c09539e919df47266820ac3020bbfb709",
    "com/a/b/a/b": "52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030",
    "com/a/b/a/c": "37ffe0bbc272b080bcede9b975f99f877da05375089b256c656566d8790c41df",
    "com/a/b/a/d": "6b60fd4224532042707da6eda83c17879d0c5fcb0aaa478b9fcc035ed6bdda6b",
    "com/a/b/a/e": "64f3e4ee692bb549129e2a41342beae83ac94edd28296b88a7694777268334b0",
}


class OriginalFiveMathSourceR168Error(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise OriginalFiveMathSourceR168Error(reason)


def verify_original_five_math_source_bundle(
        original_jar, five_math_java_zip, packet_java_zip, *,
        original_sha256=CANONICAL_V309,
        math_source_sha256, packet_source_sha256,
        original_math_owners=MATH_CLASS_SHA256,
        original_packet_owner="rs/x/e",
        expected_original_methods=54,
        expected_original_instructions=4656):
    inputs=((original_jar,original_sha256),
            (five_math_java_zip,math_source_sha256),
            (packet_java_zip,packet_source_sha256))
    require(all(sha_file(path)==digest for path,digest in inputs),
            "R168_PRIVATE_PINNED_INPUT_MISMATCH")
    require(isinstance(original_math_owners,dict)
            and len(original_math_owners)==5
            and len(set(k.casefold() for k in original_math_owners))==5
            and all(re.fullmatch(
                r"[a-zA-Z_$][a-zA-Z0-9_$]*(?:/[a-zA-Z_$][a-zA-Z0-9_$]*)+",
                name) and isinstance(digest,str) and
                re.fullmatch(r"[0-9a-f]{64}",digest)
                for name,digest in original_math_owners.items())
            and re.fullmatch(
                r"rs/(?:[a-zA-Z_$][a-zA-Z0-9_$]*/)+[a-zA-Z_$][a-zA-Z0-9_$]*",
                original_packet_owner)
            and 1<=expected_original_methods<=200
            and 1<=expected_original_instructions<=50000,
            "R168_UNSAFE_ORIGINAL_OWNER_OR_COUNT_BOUND")
    matrix=next((owner for owner in original_math_owners
                 if owner.endswith("/b")),None)
    require(matrix is not None and matrix not in (original_packet_owner,),
            "R168_ORIGINAL_GAME_LINKED_MATRIX_OWNER_REQUIRED")
    closure=audit_pinned_original_jar(
        original_jar,original_sha256=original_sha256,
        include_private_names=True)
    require(matrix in closure["private_dependency_partition"][
        "direct_rs_dependent_non_rs"],
        "R168_ORIGINAL_RS_LINKED_MATRIX_EXCLUSION_NOT_PROVEN")
    math=source_members(five_math_java_zip,math_source_sha256)
    packet=source_members(packet_java_zip,packet_source_sha256)
    require(len(math)==5 and len(packet)==1 and
            {name for name,_ in math} ==
            {owner+".java" for owner in original_math_owners}
            and packet[0][0]==original_packet_owner+".java"
            and all(0<len(value)<=100_000 for _,value in [*math,*packet]),
            "R168_EXACT_FIVE_ORIGINAL_MATH_PLUS_ONE_PACKET_JAVA_REQUIRED")
    with ZipFile(original_jar) as original:
        names=set(original.namelist())
        require(all(owner+".class" in names
                    for owner in [*original_math_owners,original_packet_owner]),
                "R168_PROVEN_ORIGINAL_JVM_OWNER_MISSING")
        original_bytes={owner:original.read(owner+".class")
                        for owner in original_math_owners}
    for owner,digest in original_math_owners.items():
        require(hashlib.sha256(original_bytes[owner]).hexdigest()==digest,
                "R168_ORIGINAL_CLASS_SHA256_IDENTITY_DRIFTED")
    javac=shutil.which("javac")
    require(javac is not None,"R168_REAL_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r168-private-") as temp:
        root=Path(temp)
        files=[]
        for name,body in [*math,*packet]:
            dest=root/"source"/name
            require(not dest.exists(),
                    "R168_SOURCE_OWNER_ALREADY_PRESENT")
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(body)
            files.append(dest)
        classes=root/"classes"
        empty=root/"empty"
        classes.mkdir()
        empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            result=subprocess.run(
                [javac,"--release","9","-proc:none","-implicit:none",
                 "-g:none","-classpath",str(empty),"-sourcepath",str(empty),
                 "-d",str(classes),*[str(file) for file in files]],
                env=env,cwd=root,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=120,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise OriginalFiveMathSourceR168Error(
                "R168_ISOLATED_JAVA9_SOURCE_COMPILATION_UNAVAILABLE") from exc
        require(result.returncode==0,
                "R168_FIVE_CLASS_SOURCE_ONLY_COMPILATION_FAILED")
        produced={p.relative_to(classes).as_posix()
                  for p in classes.rglob("*.class")}
        require(produced ==
                {owner+".class" for owner in original_math_owners} |
                {original_packet_owner+".class"},
                "R168_UNEXPECTED_COMPILER_EMITTED_BINARY_CLASS")
        reconstructed={owner:(classes/(owner+".class")).read_bytes()
                       for owner in original_math_owners}
    original_methods=0
    original_ops=0
    internal_self_edges=0
    details={}
    for owner in sorted(original_math_owners):
        original_class=parse_class(original_bytes[owner])
        recovered_class=parse_class(reconstructed[owner])
        require(original_class.name==recovered_class.name==owner
                and original_class.access==recovered_class.access
                and original_class.super_name==recovered_class.super_name
                and original_class.interfaces==recovered_class.interfaces,
                "R168_ORIGINAL_JVM_CLASS_ABI_OR_MODIFIERS_DIFFER")
        old_fields={(f["name"],f["descriptor"],f["access"])
                    for f in original_class.fields}
        new_fields={(f["name"],f["descriptor"],f["access"])
                    for f in recovered_class.fields}
        require(old_fields==new_fields,
                "R168_ORIGINAL_JVM_FIELD_ABI_DIFFERENT")
        orig=profile_class_field_accesses(original_bytes[owner])
        new=profile_class_field_accesses(reconstructed[owner])
        ids={(m["name"],m["descriptor"]) for m in orig["methods"]}
        require(ids=={(m["name"],m["descriptor"]) for m in new["methods"]},
                "R168_ORIGINAL_METHOD_SET_NOT_COMPLETE")
        parity=_strict_inspections(orig,new,selected=sorted(ids))
        count=len(ids)
        ops=parity["matched_opcode_count"]
        require(parity["all_selected_core_method_code_equal"]
                and parity["verified_selected_method_count"]==count,
                "R168_ORIGINAL_METHOD_CODE_NOT_EXACT")
        original_methods+=count
        original_ops+=ops
        old_edges=_self_call_closure_for_selected(orig,sorted(ids),owner)
        new_edges=_self_call_closure_for_selected(new,sorted(ids),owner)
        require(old_edges==new_edges,
                "R168_ORIGINAL_SOURCE_SELF_CALL_CLOSURE_DIFFERS")
        internal_self_edges+=old_edges
        details[owner.split("/")[-1]]={
            "methods":count,
            "original_jvm_instructions":ops,
            "field_count":len(old_fields),
        }
    require(original_methods==expected_original_methods and
            original_ops==expected_original_instructions,
            "R168_ALL_FIVE_ORIGINAL_MATH_METHOD_INSTRUCTIONS_NOT_COMPLETE")
    require(all(sha_file(path)==digest for path,digest in inputs),
            "R168_PRIVATE_INPUT_DRIFT_DURING_VERIFICATION")
    return {
        "schema_version":1,
        "kind":"private_v309_joint_original_five_math_java_r168",
        "original_client_sha256":original_sha256,
        "private_five_original_math_java_zip_sha256":math_source_sha256,
        "private_compile_only_packet_java_zip_sha256":packet_source_sha256,
        "five_original_reconstructed_owner_count":len(details),
        "verified_original_jvm_method_count":original_methods,
        "verified_original_jvm_instruction_count":original_ops,
        "verified_original_internal_source_self_calls":internal_self_edges,
        "original_source_class_counts":details,
        "java9_joint_original_source_only_compile_passed":True,
        "compiler_only_packet_method_bodies_original_evidenced":False,
        "original_game_binary_on_compiler_classpath":False,
        "full_original_client_compiled":False,
        "original_source_publication_authorized":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_original_client_jar")
    p.add_argument("private_five_original_math_sources_zip")
    p.add_argument("private_packet_source_stub_zip")
    p.add_argument("fresh_private_sanitized_report")
    p.add_argument("--math-sha256",required=True)
    p.add_argument("--packet-sha256",required=True)
    args=p.parse_args(argv)
    out=Path(args.fresh_private_sanitized_report)
    try:
        require(not out.exists() and not out.is_symlink() and
                out.parent.is_dir() and not out.parent.is_symlink(),
                "R168_FRESH_PRIVATE_REPORT_REQUIRED")
        result=verify_original_five_math_source_bundle(
            args.private_original_client_jar,
            args.private_five_original_math_sources_zip,
            args.private_packet_source_stub_zip,
            math_source_sha256=args.math_sha256,
            packet_source_sha256=args.packet_sha256)
        out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",
                       encoding="utf-8")
        print("R168_FIVE_ORIGINAL_MATH_SOURCE_JVM_CODE_MATCH_NOT_CLIENT_BUILD")
        print("private_report_sha256="+sha_file(out))
    except Exception:
        p.error("R168_ALL_FIVE_MATH_JAVA_SOURCES_NOT_VERIFIED")


if __name__=="__main__":
    main()
