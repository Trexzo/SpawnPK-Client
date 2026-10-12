"""R72: exact original enum/reference and Boolean two-write empty-catch Java source.

The source contains TWO calls to Properties.getProperty with independent
original keys, one static String-to-original-reference converter and one
String-to-Boolean converter/unbox. Only the exact original 11-op protected
range with a single empty Exception catch is accepted. Original enum source,
nested class metadata and runtime parity remain unproved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .boolean_join_witness import BooleanJoinWitnessError, _edges
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)
from .local_exception_primitive_source import _literal, _name, _owner_name


class DualProtectedSourceError(ValueError):
    """Two-write original JVM source form has not been proven."""


_PIN = re.compile(r"[a-fA-F0-9]{64}\Z")
_PATTERN = (
    "0x2b", "0x12", "0xb6", "0xb8", "0xb3",
    "0x2b", "0x12", "0xb6", "0xb8", "0xb6", "0xb3",
)


def _require(ok: bool, error: str) -> None:
    if not ok:
        raise DualProtectedSourceError(error)


def _getproperty(row: dict) -> bool:
    return all((
        row.get("opcode") == "0xb6",
        row.get("owner") == "java/util/Properties",
        row.get("name") == "getProperty",
        row.get("descriptor") == "(Ljava/lang/String;)Ljava/lang/String;",
    ))


def plan_original_dual_protected_source(
    profile: dict, private_method_name: str, descriptor: str,
) -> dict:
    owner = profile.get("internal_name")
    _require(type(owner) is str and owner, "ORIGINAL_OWNER_MISSING")
    methods = [m for m in profile.get("methods", [])
               if m.get("name") == private_method_name
               and m.get("descriptor") == descriptor]
    _require(len(methods) == 1, "ORIGINAL_PRIVATE_METHOD_IDENTITY_NOT_UNIQUE")
    method = methods[0]
    rows = _instructions(method)
    _require(rows and rows[0]["offset"] == 0
             and all(a["offset"] + a["length"] == b["offset"]
                     for a, b in zip(rows, rows[1:])),
             "ORIGINAL_METHOD_INSTRUCTIONS_NOT_CONTIGUOUS")
    handlers = method.get("exception_handlers")
    _require(isinstance(handlers, list), "ORIGINAL_EXCEPTION_TABLE_NOT_FOUND")
    fields = _fields(profile)
    try:
        incoming = {b for a, b in _edges(rows)}
    except BooleanJoinWitnessError:
        raise DualProtectedSourceError("ORIGINAL_BRANCH_EDGES_INVALID") from None
    offsets = {r["offset"]: i for i, r in enumerate(rows)}
    regions = []
    for h in handlers:
        if h.get("catch_type") != "java/lang/Exception":
            continue
        start, end, handler = (h.get("start_pc"), h.get("end_pc"),
                               h.get("handler_pc"))
        if any(type(x) is not int or x not in offsets
               for x in (start, end, handler)):
            continue
        a, b, c = offsets[start], offsets[end], offsets[handler]
        if (c != b+1 or c+1 >= len(rows)
                or b-a != len(_PATTERN)):
            continue
        block = rows[a:b]
        if tuple(row.get("opcode") for row in block) != _PATTERN:
            continue
        jump, caught, afterward = rows[b:c+2]
        if (jump.get("opcode") != "0xa7"
                or jump.get("branch_target_offset") != afterward["offset"]
                or caught.get("opcode") != "0x4e"):
            continue
        if (any(r["offset"] in incoming for r in block[1:])
                or any(other is not h and other.get("handler_pc")
                       in {r["offset"] for r in block[1:]}
                       for other in handlers)):
            continue
        (_, k1, lookup1, conv1, target1, _,
         k2, lookup2, conv2, unbox, target2) = block
        reference = target1.get("descriptor")
        if (not _getproperty(lookup1)
                or not _getproperty(lookup2)
                or type(reference) is not str
                or not reference.startswith("L")
                or not reference.endswith(";")
                or target1.get("owner") != owner
                or target2.get("owner") != owner
                or target2.get("descriptor") != "Z"
                or (target1.get("name"), reference) not in fields
                or (target2.get("name"), "Z") not in fields
                or not fields[(target1["name"], reference)]["access"] & 0x0008
                or not fields[(target2["name"], "Z")]["access"] & 0x0008
                or conv1.get("descriptor") != "(Ljava/lang/String;)" + reference
                or conv2.get("descriptor")
                != "(Ljava/lang/String;)Ljava/lang/Boolean;"
                or unbox.get("owner") != "java/lang/Boolean"
                or unbox.get("name") != "booleanValue"
                or unbox.get("descriptor") != "()Z"):
            continue
        if (type(k1.get("constant")) is not str
                or type(k2.get("constant")) is not str
                or k1.get("constant_pool_tag") != 8
                or k2.get("constant_pool_tag") != 8):
            continue
        first = (
            _name(target1["name"]) + " = "
            + _owner_name(conv1["owner"]) + "." + _name(conv1["name"])
            + "(originalLocalSlot1.getProperty(" + _literal(k1) + "));"
        )
        second = (
            _name(target2["name"]) + " = "
            + _owner_name(conv2["owner"]) + "." + _name(conv2["name"])
            + "(originalLocalSlot1.getProperty(" + _literal(k2)
            + ")).booleanValue();"
        )
        regions.append({
            "private_source": (
                "try {\n    " + first + "\n    " + second
                + "\n} catch (java.lang.Exception ignored) {\n}\n"
            ),
            "original_start_pc":start,
            "original_end_pc":end,
            "original_handler_pc":handler,
            "original_private_reference_type":reference,
            "original_private_reference_field":target1["name"],
            "original_private_boolean_field":target2["name"],
            "original_reference_and_boolean_converters_exact":True,
            "source_first_then_second_write_order_preserved":True,
        })
    _require(len({r["original_start_pc"] for r in regions}) == len(regions),
             "DUPLICATE_ORIGINAL_TWO_WRITE_SOURCE_REGIONS")
    return {
        "private_original_two_write_sources":regions,
        "original_exact_two_write_protected_source_regions":len(regions),
        "original_original_reference_converted_before_boolean":True,
        "original_exception_catch_has_empty_body":True,
        "original_properties_receiver_type_proven":True,
        "original_enum_nested_source_type_verified":False,
        "original_full_method_compiled_equivalent":False,
        "runtime_behavior_equivalent":False,
    }


def recover_private_two_write_source(
    original_jar:Path, owner_entry:str, private_method:str,
    descriptor:str, output_dir:Path,*,whole_jar_sha256:str,
)->dict:
    jar,out=Path(original_jar),Path(output_dir)
    _require(not out.exists() and not out.is_symlink(),
             "OUTPUT_ALREADY_EXISTS")
    _require(type(whole_jar_sha256) is str
             and _PIN.fullmatch(whole_jar_sha256) is not None,
             "INVALID_ORIGINAL_COMPLETE_JAR_PIN")
    _require(jar.is_file() and not jar.is_symlink(),
             "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _require(_digest(jar)==whole_jar_sha256.lower(),
             "ORIGINAL_COMPLETE_JAR_SHA256_MISMATCH")
    _require(type(owner_entry) is str and owner_entry.endswith(".class")
             and not owner_entry.startswith("/")
             and "\\" not in owner_entry
             and all(x not in ("",".","..") and ":" not in x
                     for x in owner_entry.split("/")),
             "INVALID_PRIVATE_CLASS_ENTRY")
    try:
        with ZipFile(jar) as z:
            _require(z.namelist().count(owner_entry)==1,
                     "ORIGINAL_OWNER_CLASS_ENTRY_NOT_UNIQUE")
            p=profile_jar_class(jar,owner_entry)
        result=plan_original_dual_protected_source(p,private_method,descriptor)
    except (BadZipFile,OSError,BytecodeProfileError,
            ScalarInitializerRecoveryError,KeyError,TypeError,IndexError):
        raise DualProtectedSourceError(
            "ORIGINAL_PROTECTED_DUAL_FIELD_SOURCE_NOT_VERIFIABLE"
        ) from None
    _require(_digest(jar)==whole_jar_sha256.lower(),
             "ORIGINAL_JAR_CHANGED_DURING_DUAL_SOURCE_RECOVERY")
    raw=result.pop("private_original_two_write_sources")
    _require(len(raw)>0,"NO_EXACT_DUAL_FIELD_SOURCE_REGION")
    text=json.dumps(raw,indent=2,sort_keys=True)+"\n"
    fragment="".join(x["private_source"] for x in raw)
    report={
        "schema_version":1,
        "kind":"private_original_enum_reference_and_boolean_empty_catch_source",
        "original_whole_jar_sha256":whole_jar_sha256.lower(),
        "private_region_graph_sha256":hashlib.sha256(text.encode()).hexdigest(),
        "private_java_source_sha256":hashlib.sha256(fragment.encode()).hexdigest(),
        "research_only":True,
        **result,
    }
    out.mkdir(parents=True,exist_ok=False)
    for name,contents in (
        ("reference-boolean-sites.private.json",text),
        ("reference-boolean-source.private.java.txt",fragment),
        ("reference-boolean-source.aggregate.json",
         json.dumps(report,sort_keys=True,indent=2)+"\n")
    ):
        with (out/name).open("x",encoding="utf-8",newline="\n") as fd:
            fd.write(contents)
    return report


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar",type=Path)
    p.add_argument("private_class_entry")
    p.add_argument("private_method_name")
    p.add_argument("private_method_descriptor")
    p.add_argument("new_private_output",type=Path)
    p.add_argument("--whole-jar-sha256",required=True)
    args=p.parse_args(argv)
    try:
        print(json.dumps(recover_private_two_write_source(
            args.original_jar,args.private_class_entry,
            args.private_method_name,args.private_method_descriptor,
            args.new_private_output,
            whole_jar_sha256=args.whole_jar_sha256,
        ),sort_keys=True))
    except DualProtectedSourceError as exc:
        p.error(str(exc))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
