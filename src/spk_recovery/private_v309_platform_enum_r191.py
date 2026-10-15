"""R191: original v309 rs/k/j platform enum Java semantics and outer closure.

Original JVM enums use obfuscated enum field names a/b/c/d but Enum.name()
labels Windows/MacOS/Linux/Other. Plain Java cannot generate differing enum
field names and Enum.name(); the source contains real readable enum constants
plus exact a/b/c/d final aliases. The static OS detector is reconstructed
from original JVM evidence and is NEVER executed by this audit.
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
from .private_v309_signlink_nested_enum_r190 import (
    ORIGINAL_ENUM_OWNER,ORIGINAL_ENUM_SHA256,
    audit_original_direction_enum_java,
)
from .private_v309_signlink_twentyone_source_r186 import (
    ORIGINAL_OWNER, ORIGINAL_CLASS_SHA256, HELPER_OWNERS,
)
from .private_v309_signlink_whole_semantic_r189 import (
    _semantic_method,audit_original_owner_semantic_classfiles,
)

PLATFORM_OWNER="rs/k/j"
PLATFORM_CLASS_SHA256=(
    "820acef9584e669760389461af78b899530a32ef1dfcd5b4c22a72b3309d995e"
)
PLATFORM_FIELD_MAPPING={
    "a":"Windows","b":"MacOS","c":"Linux","d":"Other",
    "e":"e","f":"$VALUES",
}
PLATFORM_METHOD_MAPPING={"b":"$values"}
NONORIGINAL_HELPERS=tuple(sorted(set(HELPER_OWNERS)-{PLATFORM_OWNER}))
ALIAS_LAYOUT=(("a","Windows"),("b","MacOS"),
              ("c","Linux"),("d","Other"))


class R191PlatformEnumSourceError(ValueError):
    pass


def need(condition,message):
    if not condition:
        raise R191PlatformEnumSourceError(message)


def _method_index(profile):
    result={}
    for method in profile["methods"]:
        key=(method["name"],method["descriptor"])
        need(key not in result,"R191_DUPLICATE_JVM_METHOD")
        result[key]=method
    return result


def _rename_original_symbols(instructions,owner):
    out=[]
    for item in instructions:
        entry=dict(item)
        if entry.get("owner")==owner:
            if entry["opcode"] in ("0xb2","0xb3","0xb4","0xb5"):
                entry["name"]=PLATFORM_FIELD_MAPPING.get(
                    entry["name"],entry["name"])
            elif entry["opcode"] in ("0xb6","0xb7","0xb8","0xb9"):
                entry["name"]=PLATFORM_METHOD_MAPPING.get(
                    entry["name"],entry["name"])
        out.append(entry)
    return out


def audit_original_platform_enum_java(
        original_binary,recompiled_binary, *,
        original_owner=PLATFORM_OWNER,
        original_class_sha256=None):
    """Full original six-method Code semantics with eight extra alias ops.

    All control-flow targets are expressed as instruction indices; the eight
    inserted alias operations are strictly validated then excluded before
    comparing ORIGINAL OS detection branches/catches.
    """
    if original_class_sha256 is not None:
        need(hashlib.sha256(original_binary).hexdigest()==original_class_sha256,
             "R191_ORIGINAL_OS_ENUM_SHA256_CHANGED")
    original=parse_class(original_binary)
    candidate=parse_class(recompiled_binary)
    need((original.name,original.super_name,original.major,
          original.minor,original.access,original.interfaces)==
         (candidate.name,candidate.super_name,candidate.major,
          candidate.minor,candidate.access,candidate.interfaces)
         and original.name==original_owner
         and original.super_name=="java/lang/Enum"
         and original.major==53
         and (original.access&0x4000)!=0,
         "R191_PLATFORM_ENUM_HEADER_NOT_ORIGINAL")
    need(len(original.fields)==6 and len(candidate.fields)==10
         and len(original.methods)==len(candidate.methods)==6,
         "R191_ORIGINAL_ENUM_FIELD_METHOD_COUNTS_CHANGED")
    old_fields={x["name"]:x for x in original.fields}
    new_fields={x["name"]:x for x in candidate.fields}
    need(set(old_fields)==set(PLATFORM_FIELD_MAPPING) and
         set(new_fields)==set(PLATFORM_FIELD_MAPPING.values()) |
         {alias for alias,_ in ALIAS_LAYOUT},
         "R191_EXPECTED_CORE_AND_ALIAS_FIELDS_ONLY")
    for original_name,source_name in PLATFORM_FIELD_MAPPING.items():
        old=old_fields[original_name];new=new_fields[source_name]
        need((old["descriptor"],old["access"])==
             (new["descriptor"],new["access"]),
             "R191_ORIGINAL_PLATFORM_ENUM_FIELD_FLAGS_MISMATCH")
    for alias,_ in ALIAS_LAYOUT:
        need(new_fields[alias]["access"]==0x0019 and
             new_fields[alias]["descriptor"]=="L"+original_owner+";",
             "R191_ALIAS_FIELDS_NOT_SOURCE_COMPILE_COMPATIBLE")
    old=profile_class_field_accesses(original_binary)
    new=profile_class_field_accesses(recompiled_binary)
    left=_method_index(old)
    right=_method_index(new)
    need(len(left)==6 and len(right)==6,
         "R191_SIX_ORIGINAL_PLATFORM_ENUM_METHODS_REQUIRED")
    need({(PLATFORM_METHOD_MAPPING.get(n,n),d) for n,d in left}==
         set(right),"R191_PUBLIC_OR_SYNTHETIC_METHOD_SET_CHANGED")

    total=0
    stackmap_differences=0
    for (name,desc),before in left.items():
        other=(PLATFORM_METHOD_MAPPING.get(name,name),desc)
        after=right[other]
        need(before["access"]==after["access"] and
             before["max_stack"]==after["max_stack"] and
             before["max_locals"]==after["max_locals"],
             "R191_ENUM_METHOD_ABI_OR_CODE_LIMITS_CHANGED")
        a,old_handlers=_semantic_method(old,before)
        b,new_handlers=_semantic_method(new,after)
        a=_rename_original_symbols(a,original_owner)
        if other==("<clinit>","()V"):
            # Enum constants and the generated values array are constructed
            # first. Exactly four alias assignments appear immediately after.
            array_write=[i for i,x in enumerate(b)
                         if x["opcode"]=="0xb3" and
                         x.get("owner")==original_owner and
                         x.get("name")=="$VALUES"]
            need(len(array_write)==1,
                 "R191_ENUM_VALUES_ARRAY_NOT_UNIQUE")
            start=array_write[0]+1
            aliases=b[start:start+8]
            expected=[]
            for alias,label in ALIAS_LAYOUT:
                expected.extend([("0xb2",label),("0xb3",alias)])
            need([(x["opcode"],x.get("name")) for x in aliases]==
                 expected,"R191_FOUR_SOURCE_ALIAS_INITIALIZERS_DIFFER")
            # Remap ONLY valid instruction-index destinations. Any branch
            # into the inserted alias block is invalid and must be rejected.
            def remap_index(n):
                need(type(n) is int and (n<start or n>=start+8),
                     "R191_BRANCH_ENTERED_NONORIGINAL_ALIAS_BLOCK")
                return n-8 if n>=start+8 else n
            b=b[:start]+b[start+8:]
            b=[dict(x) for x in b]
            for row in b:
                if "branch_target_instruction_index" in row:
                    row["branch_target_instruction_index"]=remap_index(
                        row["branch_target_instruction_index"])
                if "default_target_instruction_index" in row:
                    row["default_target_instruction_index"]=remap_index(
                        row["default_target_instruction_index"])
                if "switch_target_instruction_indices" in row:
                    row["switch_target_instruction_indices"]=[
                        remap_index(i)
                        for i in row["switch_target_instruction_indices"]]
                if "switch_pairs_as_instruction_indices" in row:
                    row["switch_pairs_as_instruction_indices"]=[
                        (key,remap_index(i)) for key,i in
                        row["switch_pairs_as_instruction_indices"]]
            new_handlers=[{
                **h,
                "start_instruction":remap_index(h["start_instruction"]),
                "end_instruction":remap_index(h["end_instruction"]),
                "handler_instruction":remap_index(h["handler_instruction"])
            } for h in new_handlers]
        need(a==b and old_handlers==new_handlers,
             "R191_ORIGINAL_OS_BRANCH_OR_METHOD_SEMANTIC_CODE_DIFFERS")
        total+=len(a)
        if before["stackmap_frames"]!=after["stackmap_frames"]:
            stackmap_differences+=1
    return {
        "schema_version":1,
        "kind":"original_v309_platform_enum_source_semantics_r191",
        "original_platform_enum_owner":original_owner,
        "all_six_original_enum_methods_semantically_matched":True,
        "matched_original_jvm_instructions":total,
        "original_os_labels_in_order":
            ["Windows","MacOS","Linux","Other"],
        "original_os_detection_branches_and_literal_checks_match":True,
        "original_enum_obfuscated_field_aliases_preserved":True,
        "stackmap_encoded_method_count_differing":stackmap_differences,
        "original_binary_field_abi_byte_identical":False,
        "four_extra_alias_fields_in_source_generated_class":True,
        "original_platform_detection_code_executed":False,
        "original_game_executed":False,
        "full_original_client_compiled":False,
    }


def verify_pinned_v309_platform_enum_source(
        original_jar,outer_source_zip,direction_enum_source_zip,
        platform_enum_source_zip,five_helper_source_zip, *,
        original_sha256=CANONICAL_V309,
        outer_source_sha256,direction_enum_source_sha256,
        platform_enum_source_sha256,five_helpers_sha256,
        original_platform_class_sha256=PLATFORM_CLASS_SHA256):
    """Prove both original-named enum source owners plus 24-method outer Code."""
    inputs=[
        (original_jar,original_sha256),
        (outer_source_zip,outer_source_sha256),
        (direction_enum_source_zip,direction_enum_source_sha256),
        (platform_enum_source_zip,platform_enum_source_sha256),
        (five_helper_source_zip,five_helpers_sha256)]
    need(all(sha_file(p)==digest for p,digest in inputs),
         "R191_ALL_PRIVATE_SOURCE_AND_BINARY_PINS_REQUIRED")
    outer=source_members(outer_source_zip,outer_source_sha256)
    direction=source_members(
        direction_enum_source_zip,direction_enum_source_sha256)
    platform=source_members(platform_enum_source_zip,
                            platform_enum_source_sha256)
    helpers=source_members(five_helper_source_zip,five_helpers_sha256)
    need(len(outer)==len(direction)==len(platform)==1 and
         outer[0][0]==ORIGINAL_OWNER+".java" and
         direction[0][0]==ORIGINAL_ENUM_OWNER+".java" and
         platform[0][0]==PLATFORM_OWNER+".java" and
         len(helpers)==5 and
         {n for n,_ in helpers}=={x+".java" for x in NONORIGINAL_HELPERS},
         "R191_EXACT_ORIGINAL_THREE_OWNERS_PLUS_FIVE_COMPILER_HELPERS")
    with ZipFile(original_jar) as archive:
        keys=[ORIGINAL_OWNER+".class",ORIGINAL_ENUM_OWNER+".class",
              PLATFORM_OWNER+".class"]
        need(all(archive.namelist().count(key)==1 for key in keys),
             "R191_ORIGINAL_BINARY_CLASSES_NOT_UNIQUE")
        original={key:archive.read(key) for key in keys}
    need(hashlib.sha256(original[PLATFORM_OWNER+".class"]).hexdigest()==
         original_platform_class_sha256 and
         hashlib.sha256(original[ORIGINAL_OWNER+".class"]).hexdigest()==
         ORIGINAL_CLASS_SHA256 and
         hashlib.sha256(original[ORIGINAL_ENUM_OWNER+".class"]).hexdigest()==
         ORIGINAL_ENUM_SHA256,
         "R191_ORIGINAL_JVM_CLASS_SHAS_CHANGED")
    javac=shutil.which("javac")
    need(javac is not None,"R191_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r191-private-") as temp:
        root=Path(temp)
        paths=[]
        for rel,body in [*outer,*direction,*platform,*helpers]:
            path=root/"src"/rel
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(body)
            paths.append(str(path))
        classes=root/"classfiles";empty=root/"empty"
        classes.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            run=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(classes),*paths],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=120,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R191PlatformEnumSourceError(
                "R191_JDK9_SOURCE_ONLY_BUILD_ABORTED") from exc
        expected={ORIGINAL_OWNER+".class",ORIGINAL_ENUM_OWNER+".class",
                  PLATFORM_OWNER+".class"} | {
                  x+".class" for x in NONORIGINAL_HELPERS}
        emitted={p.relative_to(classes).as_posix()
                 for p in classes.rglob("*.class")}
        need(run.returncode==0 and emitted==expected,
             "R191_SOURCE_ONLY_THREE_ORIGINAL_AND_FIVE_FAKE_CLASS_SET")
        built={key:(classes/key).read_bytes()
               for key in (ORIGINAL_OWNER+".class",
                           ORIGINAL_ENUM_OWNER+".class",
                           PLATFORM_OWNER+".class")}
    outer_proof=audit_original_owner_semantic_classfiles(
        original[ORIGINAL_OWNER+".class"],built[ORIGINAL_OWNER+".class"],
        expected_owner=ORIGINAL_OWNER,
        expected_original_class_sha256=ORIGINAL_CLASS_SHA256)
    direction_proof=audit_original_direction_enum_java(
        original[ORIGINAL_ENUM_OWNER+".class"],
        built[ORIGINAL_ENUM_OWNER+".class"],
        original_enum_class_sha256=ORIGINAL_ENUM_SHA256)
    platform_proof=audit_original_platform_enum_java(
        original[PLATFORM_OWNER+".class"],
        built[PLATFORM_OWNER+".class"],
        original_class_sha256=original_platform_class_sha256)
    need(outer_proof["methods_semantically_recompiled_in_one_java_class"]
         ==24 and
         outer_proof["resolved_original_jvm_instructions_compared"]==870 and
         outer_proof["only_ldc_to_ldc_w_opcode_encoding_differences"]==35,
         "R191_24_ORIGINAL_OUTER_CODE_METHODS_REGRESSED")
    need(all(sha_file(p)==digest for p,digest in inputs),
         "R191_PRIVATE_SOURCE_ORIGINAL_BINARY_CHANGED_DURING_AUDIT")
    return {
        "schema_version":1,
        "kind":"v309_signlink_outer_with_two_original_java_enums_r191",
        "original_named_sources_compiled_in_one_java9_build":3,
        "original_enum_compiler_stubs_replaced":2,
        "nonoriginal_declaration_helpers_remaining":5,
        "original_outer":outer_proof,
        "direction_enum":direction_proof,
        "platform_enum":platform_proof,
        "original_game_code_executed":False,
        "whole_original_client_compiled":False,
        "source_publication_authorized":False,
    }
