"""R79: recover original v309 full 48-op direct Properties settings prefix.

R69 proved the first 24 JVM instructions. R79 checks and reconstructs the four
subsequent original typed field assignments without changing the R69 file/
stream order. Private exact keys and field names are emitted ONLY locally.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .local_exception_primitive_source import _literal, _name
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)
from .properties_load_prefix_source import (
    PropertiesPrefixSourceError, _call, plan_original_properties_method_prefix,
)

class OriginalPrefix48Error(ValueError):
    pass

SHA = re.compile(r"[a-fA-F0-9]{64}\Z")
SIX_DIRECT = ("0x2b","0x12","0xb6","0xb8","0xb6","0xb3")
FULL_SUFFIX = (
    "0x2b","0x12","0x12","0xb6","0xb8","0xb3",
    *SIX_DIRECT, *SIX_DIRECT, *SIX_DIRECT,
)

def require(ok, code):
    if not ok:
        raise OriginalPrefix48Error(code)

def plan_private_original_48_op_prefix(original, method_name, descriptor):
    try:
        previous = plan_original_properties_method_prefix(
            original, method_name, descriptor)
    except PropertiesPrefixSourceError as exc:
        raise OriginalPrefix48Error("R69_FILE_PROPERTIES_PREFIX_NOT_PROVEN") from exc
    method = [m for m in original.get("methods", [])
              if m.get("name")==method_name and m.get("descriptor")==descriptor]
    require(len(method)==1, "ORIGINAL_METHOD_NOT_UNIQUE")
    rows = _instructions(method[0])
    require(len(rows) >= 48 and
            tuple(r.get("opcode") for r in rows[24:48]) == FULL_SUFFIX,
            "EXPECTED_EXACT_ORIGINAL_FOUR_TYPED_ASSIGNMENT_PATTERNS")
    prefix, following = rows[:24], rows[24:48]
    owner = original["internal_name"]
    fields = _fields(original)
    # R69 establishes that slot1 contains the original java.util.Properties.
    # Verify original property overload, argument literal, typed conversion,
    # field declaration, and three single-key Boolean/Integer stores.
    first = following[:6]
    require(_call(first[3],"0xb6","java/util/Properties",
                  "getProperty","(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;")
            and _call(first[4],"0xb8","java/lang/Boolean",
                      "parseBoolean","(Ljava/lang/String;)Z"),
            "ORIGINAL_TWO_ARGUMENT_PROPERTY_BOOLEAN_PARSE_NOT_PROVEN")
    require(first[1].get("constant_pool_tag")==8 and
            first[2].get("constant_pool_tag")==8,
            "TWO_ARGUMENT_PROPERTY_STRING_LITERALS_NOT_PROVEN")
    source = [previous["private_source_prefix"]]
    def verify_field(row, descriptor):
        require(row.get("owner")==owner and row.get("descriptor")==descriptor,
                "WRONG_ORIGINAL_FIELD_OWNER_OR_DESCRIPTOR")
        declared = fields.get((row.get("name"),descriptor))
        require(declared is not None and declared.get("access",0)&0x0008,
                "UNDECLARED_OR_NONSTATIC_ORIGINAL_TARGET")
        return _name(row["name"])
    first_field = verify_field(first[5],"Z")
    source.append(
        "    "+first_field+" = java.lang.Boolean.parseBoolean("
        "originalLocalSlot1.getProperty("+_literal(first[1])+","
        +_literal(first[2])+"));\n"
    )
    descriptors = ("Z","I","Z")
    for index, desc in enumerate(descriptors, start=1):
        group = following[index*6:(index+1)*6]
        kind = "Boolean" if desc=="Z" else "Integer"
        method_name_conv = "booleanValue" if desc=="Z" else "intValue"
        require(_call(group[2],"0xb6","java/util/Properties",
                      "getProperty","(Ljava/lang/String;)Ljava/lang/String;"),
                "SINGLE_PROPERTY_LOOKUP_SIGNATURE_MISMATCH")
        require(_call(group[3],"0xb8","java/lang/"+kind,
                      "valueOf","(Ljava/lang/String;)Ljava/lang/"+kind+";"),
                "BOXED_PROPERTY_VALUE_OF_MISMATCH")
        require(_call(group[4],"0xb6","java/lang/"+kind,
                      method_name_conv,"()"+desc),
                "ORIGINAL_BOXED_UNBOXING_MISMATCH")
        require(group[1].get("constant_pool_tag")==8,
                "ORIGINAL_PROPERTY_KEY_NOT_STRING")
        field = verify_field(group[5],desc)
        source.append(
            "    "+field+" = java.lang."+kind+".valueOf("
            "originalLocalSlot1.getProperty("+_literal(group[1])+
            "))."+method_name_conv+"();\n"
        )
    # The next original instruction must begin an independently checked
    # protected region. Do not silently consume any additional source.
    require(len(rows)>48 and rows[48].get("offset") == rows[47]["offset"]+rows[47]["length"],
            "ORIGINAL_PREFIX_NOT_CONTIGUOUS_WITH_METHOD_BODY")
    require(sum(r.get("opcode")=="0xb3" for r in rows[:48])==4,
            "ORIGINAL_PREFIX_FOUR_WRITE_COUNT_MISMATCH")
    require(not any(r.get("branch_target_offset") in
                    {x["offset"] for x in rows[24:48]}
                    for r in rows[:48] if "branch_target_offset" in r),
            "UNEXPECTED_INCOMING_BRANCH_IN_DIRECT_ASSIGNMENTS")
    return {
        "private_original_48_instruction_java_source":"".join(source),
        "exact_original_48_prefix_instruction_count":48,
        "original_first_24_prefix_preserved_from_R69":True,
        "original_initial_typed_assignment_counts":{"boolean":3,"integer":1},
        "original_first_property_has_two_argument_default":True,
        "original_four_static_writes_in_original_order":True,
        "complete_original_697_instruction_method_compiled":False,
        "all_original_enclosing_exception_ranges_verified_in_candidate":False,
        "runtime_or_helper_side_effects_equivalent":False,
    }

def replay_private_48_prefix(jar, class_entry, private_method, descriptor,
                             output, original_sha256):
    jar, output = Path(jar), Path(output)
    require(not output.exists() and not output.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    require(type(original_sha256) is str and SHA.fullmatch(original_sha256),
            "INVALID_COMPLETE_ORIGINAL_JAR_PIN")
    require(jar.is_file() and not jar.is_symlink()
            and _digest(jar)==original_sha256.lower(),
            "ORIGINAL_JAR_SHA256_MISMATCH")
    require(type(class_entry) is str and class_entry.endswith(".class")
            and not class_entry.startswith("/") and "\\" not in class_entry
            and all(s not in ("",".","..") and ":" not in s
                    for s in class_entry.split("/")),
            "INVALID_PRIVATE_JVM_OWNER_PATH")
    try:
        with ZipFile(jar) as z:
            require(z.namelist().count(class_entry)==1,
                    "ORIGINAL_JVM_CLASS_ENTRY_NOT_UNIQUE")
            original=profile_jar_class(jar,class_entry)
        result=plan_private_original_48_op_prefix(
            original,private_method,descriptor)
    except (BadZipFile,BytecodeProfileError,ScalarInitializerRecoveryError,
            PropertiesPrefixSourceError,KeyError,IndexError,TypeError):
        raise OriginalPrefix48Error("ORIGINAL_PREFIX_SOURCE_NOT_VERIFIABLE") from None
    require(_digest(jar)==original_sha256.lower(),
            "ORIGINAL_JAR_CHANGED_DURING_PROOF")
    private=result.pop("private_original_48_instruction_java_source")
    public={
        "schema_version":1,"kind":"original_v309_private_complete_48_op_method_prefix",
        "complete_original_jar_sha256":original_sha256.lower(),
        "private_source_sha256":hashlib.sha256(private.encode()).hexdigest(),
        "research_only":True,**result,
    }
    output.mkdir(parents=True,exist_ok=False)
    with (output/"properties-48-prefix.private.java.txt").open("x",encoding="utf-8") as f:
        f.write(private)
    with (output/"properties-48-prefix.aggregate.json").open("x",encoding="utf-8") as f:
        json.dump(public,f,sort_keys=True,indent=2);f.write("\n")
    return public

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar")
    p.add_argument("private_owner_class")
    p.add_argument("private_method")
    p.add_argument("descriptor")
    p.add_argument("new_private_output")
    p.add_argument("--original-sha256",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(replay_private_48_prefix(
            a.original_jar,a.private_owner_class,a.private_method,a.descriptor,
            a.new_private_output,a.original_sha256),sort_keys=True))
    except OriginalPrefix48Error as e:
        p.error(str(e))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
