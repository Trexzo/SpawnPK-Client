"""R69: exact original v309 Properties/FileInputStream Java method prefix.

Recover original 24-instruction prefix: static preflight call, File
construction from original static String, exists/return, creation of one
java.util.Properties local1, FileInputStream local2, Properties.load,
and stream.close. Proves original local slot 1's Java type; DOES NOT
reconstruct enclosing IOException catches or 697-op runtime behavior.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)
from .local_exception_primitive_source import _name


class PropertiesPrefixSourceError(ValueError):
    """Original File/Properties JVM source prefix not exactly proven."""


_SHA = re.compile(r"[0-9a-fA-F]{64}\Z")
_OPS = (
    "0xb8", "0xbb", "0x59", "0xb2", "0xb7", "0x4b", "0x2a",
    "0xb6", "0x9a", "0xb1", "0xbb", "0x59", "0xb7", "0x4c",
    "0xbb", "0x59", "0x2a", "0xb7", "0x4d", "0x2b", "0x2c",
    "0xb6", "0x2c", "0xb6",
)


def _need(value: bool, why: str) -> None:
    if not value:
        raise PropertiesPrefixSourceError(why)


def _call(row: dict, op: str, owner: str,
          name: str, desc: str) -> bool:
    return all((
        row.get("opcode") == op, row.get("owner") == owner,
        row.get("name") == name, row.get("descriptor") == desc,
    ))


def plan_original_properties_method_prefix(
    original: dict, private_method_name: str, descriptor: str
) -> dict:
    owner = original.get("internal_name")
    _need(type(owner) is str and owner, "ORIGINAL_OWNER_UNAVAILABLE")
    candidates = [
        m for m in original.get("methods", [])
        if m.get("name") == private_method_name
        and m.get("descriptor") == descriptor
    ]
    _need(len(candidates) == 1,
          "ORIGINAL_PRIVATE_METHOD_SIGNATURE_NOT_UNIQUE")
    method = candidates[0]
    _need(method.get("access") == 0x0009 and descriptor == "()V",
          "ORIGINAL_METHOD_NOT_EXACT_PUBLIC_STATIC_VOID")
    rows = _instructions(method)
    _need(len(rows) >= len(_OPS)+1
          and tuple(r.get("opcode") for r in rows[:24]) == _OPS
          and all(a["offset"]+a["length"]==b["offset"]
                  for a,b in zip(rows,rows[1:])),
          "EXACT_JVM_FILE_PROPERTIES_PREFIX_NOT_PRESENT")
    s = rows[:24]
    _need(_call(s[0],"0xb8",owner,s[0].get("name"),"()V"),
          "STATIC_PREFLIGHT_CALL_NOT_EXACT_ORIGINAL_OWNER")
    preflight=[m for m in original.get("methods", [])
               if m.get("name")==s[0].get("name")
               and m.get("descriptor")=="()V"
               and m.get("access",0)&0x0008]
    _need(len(preflight)==1,
          "ORIGINAL_PREFLIGHT_MEMBER_NOT_DECLARED_STATIC")
    _need(s[1].get("type")=="java/io/File"
          and s[4].get("owner")=="java/io/File"
          and s[4].get("name")=="<init>"
          and s[4].get("descriptor")=="(Ljava/lang/String;)V",
          "FILE_STRING_CONSTRUCTION_NOT_PROVEN")
    fields=_fields(original)
    file_field=(s[3].get("name"),s[3].get("descriptor"))
    _need(s[3].get("owner")==owner
          and file_field[1]=="Ljava/lang/String;"
          and file_field in fields and fields[file_field]["access"]&0x0008,
          "FILE_NAME_NOT_ORIGINAL_DECLARED_STATIC_STRING")
    _need(_call(s[7],"0xb6","java/io/File","exists","()Z")
          and s[8].get("branch_target_offset")==s[10]["offset"],
          "ORIGINAL_FILE_EXISTS_RETURN_BRANCH_NOT_EXACT")
    _need(s[10].get("type")=="java/util/Properties"
          and _call(s[12],"0xb7","java/util/Properties","<init>","()V"),
          "PROPERTIES_LOCAL_ONE_CONSTRUCTOR_NOT_EXACT")
    _need(s[14].get("type")=="java/io/FileInputStream"
          and _call(s[17],"0xb7","java/io/FileInputStream",
                    "<init>","(Ljava/io/File;)V"),
          "FILE_INPUT_STREAM_LOCAL_TWO_NOT_EXACT")
    _need(_call(s[21],"0xb6","java/util/Properties",
                "load","(Ljava/io/InputStream;)V")
          and _call(s[23],"0xb6","java/io/FileInputStream",
                    "close","()V"),
          "PROPERTIES_LOAD_AND_STREAM_CLOSE_NOT_EXACT")
    # Slot1 is assigned exactly once by astore_1 in the entire original
    # method. It is NEVER reassigned to another JVM reference type.
    _need(sum(r.get("opcode")=="0x4c" for r in rows)==1,
          "ORIGINAL_PROPERTIES_LOCAL_ONE_REASSIGNED")
    # No extra instructions or branches may cut through the prefix.
    _need(not any("branch_target_offset" in row
                  and row is not s[8]
                  for row in s),
          "UNEXPECTED_JVM_BRANCH_IN_PROPERTIES_PREFIX")
    handler_data=method.get("exception_handlers")
    _need(isinstance(handler_data,list),
          "ORIGINAL_METHOD_EXCEPTION_TABLE_UNAVAILABLE")
    io_handlers=[
        h for h in handler_data
        if h.get("catch_type")=="java/io/IOException"
    ]
    source=(
        "// PRIVATE original JVM File/Properties loading prefix.\n"
        "// Original outer IOException source control flow is NOT included.\n"
        + "    " + _name(s[0]["name"]) + "();\n"
        + "    java.io.File originalLocalSlot0 = new java.io.File("
        + _name(s[3]["name"]) + ");\n"
        + "    if (!originalLocalSlot0.exists()) return;\n"
        + "    java.util.Properties originalLocalSlot1 = "
        "new java.util.Properties();\n"
        + "    java.io.FileInputStream originalLocalSlot2 = "
        "new java.io.FileInputStream(originalLocalSlot0);\n"
        + "    originalLocalSlot1.load(originalLocalSlot2);\n"
        + "    originalLocalSlot2.close();\n"
    )
    return {
        "private_source_prefix":source,
        "exact_original_prefix_instructions":24,
        "original_properties_local_slot_index":1,
        "original_properties_local_initialized_once":True,
        "original_file_stream_local_slot_index":2,
        "original_file_exists_guard_verbatim":True,
        "original_getProperty_type_java_util_Properties_verified":True,
        "original_properties_load_then_stream_close_verified":True,
        "original_io_exception_table_entries":len(io_handlers),
        "original_outer_io_try_catch_java_source_recovered":False,
        "remaining_original_JVM_method_source_recovered":False,
        "original_helper_method_side_effects_proven":False,
        "compiled_full_original_method_equivalent":False,
        "real_client_runtime_equivalent":False,
    }


def recover_private_properties_prefix(
    original_jar:Path,original_class_entry:str,
    private_method_name:str, private_method_descriptor:str,
    output_dir:Path,*,original_sha256:str
)->dict:
    jar,out=Path(original_jar),Path(output_dir)
    _need(not out.exists() and not out.is_symlink(),
          "OUTPUT_ALREADY_EXISTS")
    _need(type(original_sha256) is str
          and _SHA.fullmatch(original_sha256) is not None,
          "INVALID_ORIGINAL_WHOLE_JAR_PIN")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar)==original_sha256.lower(),
          "ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(original_class_entry) is str
          and original_class_entry.endswith(".class")
          and not original_class_entry.startswith("/")
          and "\\" not in original_class_entry
          and all(p not in ("",".","..") and ":" not in p
                  for p in original_class_entry.split("/")),
          "ORIGINAL_CLASS_ENTRY_NOT_SAFE")
    try:
        with ZipFile(jar) as z:
            _need(z.namelist().count(original_class_entry)==1,
                  "ORIGINAL_CLASS_ENTRY_NOT_UNIQUE")
            original=profile_jar_class(jar,original_class_entry)
        proof=plan_original_properties_method_prefix(
            original,private_method_name,private_method_descriptor)
    except (OSError,BadZipFile,BytecodeProfileError,
            ScalarInitializerRecoveryError,KeyError,IndexError,TypeError):
        raise PropertiesPrefixSourceError(
            "ORIGINAL_FILE_PROPERTIES_PREFIX_NOT_VERIFIABLE"
        ) from None
    _need(_digest(jar)==original_sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_PREFIX_RECOVERY")
    private=proof.pop("private_source_prefix")
    report={
        "schema_version":1,
        "kind":"exact_private_original_properties_file_stream_method_prefix",
        "research_only":True,
        "original_complete_jar_sha256":original_sha256.lower(),
        "private_source_prefix_sha256":
            hashlib.sha256(private.encode("utf-8")).hexdigest(),
        **proof,
    }
    out.mkdir(parents=True,exist_ok=False)
    with (out/"properties-load-prefix.private.java.txt").open(
        "x",encoding="utf-8",newline="\n"
    ) as fd:fd.write(private)
    with (out/"properties-load-prefix.aggregate.json").open(
        "x",encoding="utf-8",newline="\n"
    ) as fd:json.dump(report,fd,sort_keys=True,indent=2);fd.write("\n")
    return report


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar",type=Path)
    p.add_argument("private_class_entry")
    p.add_argument("private_method_name")
    p.add_argument("private_method_descriptor")
    p.add_argument("new_private_output",type=Path)
    p.add_argument("--original-sha256",required=True)
    args=p.parse_args(argv)
    try:
        print(json.dumps(recover_private_properties_prefix(
            args.original_jar,args.private_class_entry,
            args.private_method_name,args.private_method_descriptor,
            args.new_private_output,original_sha256=args.original_sha256,
        ),sort_keys=True))
    except PropertiesPrefixSourceError as exc:
        p.error(str(exc))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
