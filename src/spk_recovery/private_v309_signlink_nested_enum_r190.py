"""R190: recover original v309 rs/v/a$a direction enum as compilable Java.

The original binary names its enum INSTANCE FIELDS a/b/c, but their genuine
Enum.name() labels are LEFT/RIGHT/NORMAL. Java source cannot independently
rename an enum declaration field without also changing Enum.name(). We
preserve the labels with LEFT/RIGHT/NORMAL real enum constants and expose
a/b/c as compiler-visible aliases required by the original outer owner.

This is proven semantic source compatibility, NOT byte-identical enum ABI:
the generated class has three extra alias fields; synthetic enum helper
and original d array are generated as $values/$VALUES by javac, and original
InnerClasses metadata cannot be reproduced by a top-level a$a source.
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
from .private_v309_signlink_whole_semantic_r189 import (
    audit_original_owner_semantic_classfiles,
)
from .private_v309_signlink_twentyone_source_r186 import (
    HELPER_OWNERS, ORIGINAL_CLASS_SHA256, ORIGINAL_OWNER,
)
from .source_method_parity import _normalized_instructions

ORIGINAL_ENUM_OWNER="rs/v/a$a"
ORIGINAL_ENUM_SHA256=(
    "b93d684eef2b78751121637f1a3175ea7d5dc6d26cf7aea933b9ac9b1a773e3c"
)
ORIGINAL_ENUM_FIELDS={"a":"LEFT","b":"RIGHT","c":"NORMAL","d":"$VALUES"}
ORIGINAL_ENUM_ARRAY_METHOD={"a":"$values"}


class R190NestedDirectionEnumError(ValueError):
    pass


def require(condition,reason):
    if not condition:
        raise R190NestedDirectionEnumError(reason)


def _members(profile):
    output={}
    for method in profile["methods"]:
        key=(method["name"],method["descriptor"])
        require(key not in output,"R190_DUPLICATE_JVM_METHOD")
        output[key]=method
    return output


def _mapped_instructions(profile, method, *, renamed_fields, renamed_methods):
    instructions=_normalized_instructions(profile,method)
    output=[]
    for instruction in instructions:
        row=dict(instruction)
        row.pop("offset",None)
        row.pop("length",None)
        if row.get("owner")==profile["internal_name"]:
            if row["opcode"] in ("0xb2","0xb3","0xb4","0xb5"):
                row["name"]=renamed_fields.get(row["name"],row["name"])
            elif row["opcode"] in ("0xb6","0xb7","0xb8","0xb9"):
                row["name"]=renamed_methods.get(row["name"],row["name"])
        output.append(row)
    return output


def audit_original_direction_enum_java(
        original_bytes,candidate_bytes, *,
        original_owner=ORIGINAL_ENUM_OWNER,
        original_enum_class_sha256=None,
        original_field_map=ORIGINAL_ENUM_FIELDS,
        original_array_method_map=ORIGINAL_ENUM_ARRAY_METHOD):
    require(type(original_bytes) is bytes and
            type(candidate_bytes) is bytes,
            "R190_ORIGINAL_AND_REBUILT_CLASS_BYTES_REQUIRED")
    if original_enum_class_sha256 is not None:
        require(hashlib.sha256(original_bytes).hexdigest()==
                original_enum_class_sha256,
                "R190_ORIGINAL_ENUM_CLASS_SHA256_CHANGED")
    original=parse_class(original_bytes)
    rebuilt=parse_class(candidate_bytes)
    require((original.name,original.super_name,original.major,original.minor,
             original.access,original.interfaces)==
            (rebuilt.name,rebuilt.super_name,rebuilt.major,rebuilt.minor,
             rebuilt.access,rebuilt.interfaces) and
            original.name==original_owner and
            original.super_name=="java/lang/Enum" and
            (original.access&0x4000)!=0 and
            original.major==53,
            "R190_ORIGINAL_ENUM_CLASS_HEADER_CHANGED")
    require(len(original.fields)==4 and len(rebuilt.fields)==7 and
            len(original.methods)==len(rebuilt.methods)==5,
            "R190_ENUM_FIELD_OR_JVM_METHOD_INVENTORY_CHANGED")
    require(set(original_field_map)=={x["name"] for x in original.fields}
            and len(set(original_field_map.values()))==4,
            "R190_EXPLICIT_ENUM_FIELD_MAP_REQUIRED")
    original_fields={x["name"]:x for x in original.fields}
    generated_fields={x["name"]:x for x in rebuilt.fields}
    for old,new in original_field_map.items():
        of=original_fields[old]
        nf=generated_fields.get(new)
        require(nf is not None and
                (of["access"],of["descriptor"])==
                (nf["access"],nf["descriptor"]),
                "R190_ORIGINAL_ENUM_CORE_FIELD_ABI_NOT_MAPPED")
    # Original users reference these exact obfuscated public field IDs.
    # Compiler-generated enum constants retain their actual original labels.
    expected_aliases={name for name in ("a","b","c")
                      if name not in original_field_map.values()}
    require(set(generated_fields)==set(original_field_map.values()) |
            expected_aliases,"R190_UNEXPECTED_ENUM_SOURCE_FIELD")
    for name in expected_aliases:
        field=generated_fields[name]
        require(field["descriptor"]=="L"+original_owner+";" and
                field["access"]==0x0019,
                "R190_ORIGINAL_NAMED_ENUM_ALIAS_MUST_BE_PUBLIC_STATIC_FINAL")
    left=profile_class_field_accesses(original_bytes)
    right=profile_class_field_accesses(candidate_bytes)
    before=_members(left)
    after=_members(right)
    remapped={}
    for (name,descriptor),old_method in before.items():
        renamed=original_array_method_map.get(name,name)
        remapped[(renamed,descriptor)]=old_method
    require(set(remapped)==set(after),
            "R190_ALL_FIVE_ENUM_METHOD_IDENTITIES_REQUIRED")
    matched=0
    for key,old_method in remapped.items():
        new_method=after[key]
        require(old_method["access"]==new_method["access"] and
                old_method["max_stack"]==new_method["max_stack"] and
                old_method["max_locals"]==new_method["max_locals"] and
                old_method["exception_handlers"]==
                new_method["exception_handlers"],
                "R190_ORIGINAL_ENUM_METHOD_ACCESS_OR_LIMITS_CHANGED")
        lhs=_mapped_instructions(
            left,old_method,
            renamed_fields=original_field_map,
            renamed_methods=original_array_method_map)
        rhs=_mapped_instructions(
            right,new_method,renamed_fields={},renamed_methods={})
        if key==("<clinit>","()V"):
            require(lhs[-1]["opcode"]=="0xb1" and
                    rhs[-1]["opcode"]=="0xb1" and
                    rhs[:len(lhs)-1]==lhs[:-1],
                    "R190_ORIGINAL_ENUM_INITIALIZATION_PREFIX_CHANGED")
            # Exactly three expected alias initializations precede RETURN.
            remainder=rhs[len(lhs)-1:-1]
            expected=[]
            for alias,label in (("a","LEFT"),("b","RIGHT"),
                                ("c","NORMAL")):
                expected.extend([
                    ("0xb2",label),("0xb3",alias)])
            actual=[(x["opcode"],x.get("name")) for x in remainder]
            require(actual==expected and len(remainder)==6,
                    "R190_ALIAS_INITIALIZERS_NOT_EXACTLY_MAPPED")
            matched+=len(lhs)
        else:
            require(lhs==rhs,
                    "R190_ORIGINAL_ENUM_METHOD_CODE_NOT_SEMANTICALLY_EQUAL")
            matched+=len(lhs)
    require(len(after)==5,"R190_FIVE_ORIGINAL_ENUM_METHODS_REQUIRED")
    return {
        "schema_version":1,
        "kind":"v309_original_nested_direction_enum_java_r190",
        "original_enum_owner":original_owner,
        "original_enum_class_sha256":
            hashlib.sha256(original_bytes).hexdigest(),
        "all_five_original_enum_methods_semantically_matched":True,
        "matched_original_enum_jvm_instructions":matched,
        "original_enum_values_in_order":["LEFT","RIGHT","NORMAL"],
        "original_enum_ordinal_and_name_labels_preserved":True,
        "obfuscated_outer_java_field_aliases_preserved":True,
        "original_enum_classfile_byte_identity":False,
        "original_innerclasses_attribute_equivalence_verified":False,
        "java_derived_class_has_three_extra_alias_fields":True,
        "runtime_enum_code_executed":False,
        "original_game_code_executed":False,
    }


def verify_pinned_v309_nested_direction_enum_source(
        original_jar,outer_source_zip,enum_source_zip,
        six_compiler_helpers_zip, *,
        original_sha256=CANONICAL_V309,
        outer_source_sha256,enum_source_sha256,
        six_helpers_sha256,
        original_owner=ORIGINAL_OWNER,
        original_outer_sha256=ORIGINAL_CLASS_SHA256,
        original_enum_sha256=ORIGINAL_ENUM_SHA256):
    """Rebuild original-named outer Java + REAL enum, without original JAR jars.

    Only the six explicitly unrecovered source dependencies are declaration
    helpers, not bytecode fallback. The original JAR is SHA-checked read-only.
    """
    inputs=(
        (original_jar,original_sha256),
        (outer_source_zip,outer_source_sha256),
        (enum_source_zip,enum_source_sha256),
        (six_compiler_helpers_zip,six_helpers_sha256),
    )
    require(all(sha_file(p)==s for p,s in inputs),
            "R190_EXACT_PRIVATE_SHA256_PINS_REQUIRED")
    outer=source_members(outer_source_zip,outer_source_sha256)
    enum=source_members(enum_source_zip,enum_source_sha256)
    helpers=source_members(six_compiler_helpers_zip,six_helpers_sha256)
    require(len(outer)==1 and outer[0][0]==original_owner+".java",
            "R190_EXACT_ONE_ORIGINAL_OUTER_JAVA_REQUIRED")
    require(len(enum)==1 and enum[0][0]==ORIGINAL_ENUM_OWNER+".java",
            "R190_EXACT_ONE_ORIGINAL_ENUM_OWNER_JAVA_REQUIRED")
    require(len(helpers)==6 and
            {k for k,_ in helpers}=={x+".java" for x in HELPER_OWNERS},
            "R190_ONLY_SIX_NONORIGINAL_DECLARATION_HELPERS")
    with ZipFile(original_jar) as archive:
        for path in (original_owner+".class",ORIGINAL_ENUM_OWNER+".class"):
            require(archive.namelist().count(path)==1,
                    "R190_ORIGINAL_CLASSFILE_NOT_UNIQUE")
        original_outer=archive.read(original_owner+".class")
        original_enum=archive.read(ORIGINAL_ENUM_OWNER+".class")
    require(hashlib.sha256(original_outer).hexdigest()==original_outer_sha256
            and hashlib.sha256(original_enum).hexdigest()==original_enum_sha256,
            "R190_ORIGINAL_CLASSFILE_SHA_CHANGED")
    javac=shutil.which("javac")
    require(javac is not None,"R190_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r190-enum-") as tmp:
        root=Path(tmp)
        java_files=[]
        for rel,body in [*outer,*enum,*helpers]:
            dest=root/"source"/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(body)
            java_files.append(str(dest))
        out=root/"classes"
        empty=root/"empty"
        out.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS",
                    "_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            run=subprocess.run(
                [javac,"--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),*java_files],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,check=False,timeout=120)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R190NestedDirectionEnumError(
                "R190_SOURCE_ONLY_ENUM_COMPILATION_ABORTED") from exc
        paths={p.relative_to(out).as_posix()
               for p in out.rglob("*.class")}
        require(run.returncode==0 and
                paths==({original_owner+".class",
                         ORIGINAL_ENUM_OWNER+".class"} |
                        {name+".class" for name in HELPER_OWNERS}),
                "R190_ONLY_VERIFIED_OUTER_ENUM_AND_SIX_DECLARATIONS")
        built_outer=(out/(original_owner+".class")).read_bytes()
        built_enum=(out/(ORIGINAL_ENUM_OWNER+".class")).read_bytes()
    enum_proof=audit_original_direction_enum_java(
        original_enum,built_enum,
        original_enum_class_sha256=original_enum_sha256)
    outer_proof=audit_original_owner_semantic_classfiles(
        original_outer,built_outer,
        expected_owner=original_owner,
        expected_original_class_sha256=original_outer_sha256)
    require(outer_proof["methods_semantically_recompiled_in_one_java_class"]
            ==24 and
            outer_proof["resolved_original_jvm_instructions_compared"]==870
            and
            outer_proof["only_ldc_to_ldc_w_opcode_encoding_differences"]==35,
            "R190_ORIGINAL_OUTER_JVM_SEMANTICS_REGRESSED")
    require(all(sha_file(p)==s for p,s in inputs),
            "R190_PRIVATE_SOURCE_OR_ORIGINAL_BINARY_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_signlink_owner_with_original_direction_enum_r190",
        "outer":outer_proof,
        "nested_enum":enum_proof,
        "original_named_source_owners_compiled_together":2,
        "previous_fake_direction_helper_replaced_by_real_java_enum":True,
        "remaining_nonoriginal_declaration_helper_count":6,
        "full_original_client_compilation_claimed":False,
        "original_game_executed":False,
        "byte_identical_classfiles_claimed":False,
        "original_source_publication_authorized":False,
    }
