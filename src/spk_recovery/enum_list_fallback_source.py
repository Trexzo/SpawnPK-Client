"""R75: exact original v309 23-op external Boolean/list fallback Java source.

Null branch: set one external Boolean true, add two distinct enum values
to the SAME external List, set another external Boolean false, skip else.
Non-null: repeat same Properties lookup, parse Boolean and write the first
external Boolean. Preserve every original ordering/side effect, keep
original literal/member names in PRIVATE source only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, BadZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .boolean_join_witness import BooleanJoinWitnessError, _edges
from .local_exception_primitive_source import _literal, _name, _owner_name
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _instructions,
)


class EnumListFallbackSourceError(ValueError):
    """Original 23-op enum/list/boolean source pattern cannot be proven."""


_SHA = re.compile(r"[a-f0-9A-F]{64}\Z")
_SHAPE = (
    "0x2b", "0x12", "0xb6", "0xc7", "0x04", "0xb3",
    "0xb2", "0xb2", "0xb9", "0x57", "0xb2", "0xb2",
    "0xb9", "0x57", "0x03", "0xb3", "0xa7",
    "0x2b", "0x12", "0xb6", "0xb8", "0xb6", "0xb3",
)


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise EnumListFallbackSourceError(reason)


def _getproperty(row: dict) -> bool:
    return (
        row.get("opcode") == "0xb6"
        and row.get("owner") == "java/util/Properties"
        and row.get("name") == "getProperty"
        and row.get("descriptor")
        == "(Ljava/lang/String;)Ljava/lang/String;"
    )


def _field_equal(a: dict, b: dict) -> bool:
    return all(a.get(k) == b.get(k) for k in
               ("owner", "name", "descriptor"))


def _ref_expr(row: dict) -> str:
    _need(row.get("opcode") == "0xb2"
          and type(row.get("owner")) is str
          and type(row.get("name")) is str
          and type(row.get("descriptor")) is str,
          "PRIVATE_STATIC_REFERENCE_UNRESOLVED")
    return _owner_name(row["owner"]) + "." + _name(row["name"])


def _parse_block(profile: dict, block: list[dict],
                 endjump: dict) -> tuple[str, dict] | None:
    (recv, key, first_lookup, branch, true_literal, field_true,
     list_a, enum_a, add_a, pop_a, list_b, enum_b, add_b,
     pop_b, false_literal, field_false, jump,
     recv2, key2, second_lookup, convert, unbox, field_else) = block

    # No implicit reuse of the property result; exact original JVM calls
    # perform the lookup twice on the non-null path.
    if (not _getproperty(first_lookup)
            or not _getproperty(second_lookup)
            or key.get("constant_pool_tag") != 8
            or key2.get("constant_pool_tag") != 8
            or type(key.get("constant")) is not str
            or key.get("constant") != key2.get("constant")
            or branch.get("branch_target_offset") != recv2["offset"]
            or jump.get("branch_target_offset") != endjump["offset"]
            or not _field_equal(field_true, field_else)
            or field_true.get("descriptor") != "Z"
            or field_false.get("descriptor") != "Z"
            or field_false.get("owner") != field_true.get("owner")
            or field_false.get("name") == field_true.get("name")
            or not _field_equal(list_a, list_b)
            or list_a.get("descriptor") != "Ljava/util/List;"
            or list_a.get("owner") != field_true.get("owner")
            or enum_a.get("owner") != enum_b.get("owner")
            or enum_a.get("name") == enum_b.get("name")
            or enum_a.get("descriptor") != enum_b.get("descriptor")
            or type(enum_a.get("descriptor")) is not str
            or not enum_a["descriptor"].startswith("L")
            or not enum_a["descriptor"].endswith(";")
            or convert.get("owner") != "java/lang/Boolean"
            or convert.get("name") != "valueOf"
            or convert.get("descriptor")
            != "(Ljava/lang/String;)Ljava/lang/Boolean;"
            or unbox.get("owner") != "java/lang/Boolean"
            or unbox.get("name") != "booleanValue"
            or unbox.get("descriptor") != "()Z"):
        return None
    for call in (add_a, add_b):
        if (call.get("opcode") != "0xb9"
                or call.get("owner") != "java/util/List"
                or call.get("name") != "add"
                or call.get("descriptor") != "(Ljava/lang/Object;)Z"):
            return None
    first_field = _owner_name(field_true["owner"]) + "." + _name(field_true["name"])
    second_field = _owner_name(field_false["owner"]) + "." + _name(field_false["name"])
    array = _ref_expr(list_a)
    first_enum = _ref_expr(enum_a)
    second_enum = _ref_expr(enum_b)
    prop = "originalLocalSlot1.getProperty(" + _literal(key) + ")"
    source = (
        "try {\n"
        "    if (" + prop + " == null) {\n"
        "        " + first_field + " = true;\n"
        "        " + array + ".add(" + first_enum + ");\n"
        "        " + array + ".add(" + second_enum + ");\n"
        "        " + second_field + " = false;\n"
        "    } else {\n"
        "        " + first_field + " = java.lang.Boolean.valueOf("
        + prop + ").booleanValue();\n"
        "    }\n"
        "} catch (java.lang.Exception ignored) {\n}\n"
    )
    detail = {
        "private_first_boolean_field": field_true,
        "private_second_boolean_field": field_false,
        "private_original_list": list_a,
        "private_first_enum_constant": enum_a,
        "private_second_enum_constant": enum_b,
        "private_original_property_key": key["constant"],
        "private_java_source": source,
        "original_side_effect_order_preserved": True,
    }
    return source, detail


def plan_original_enum_list_fallback(
    original: dict, private_method: str, descriptor: str,
) -> dict:
    owner = original.get("internal_name")
    _need(type(owner) is str and owner, "ORIGINAL_OWNER_MISSING")
    candidates = [
        m for m in original.get("methods", [])
        if m.get("name") == private_method
        and m.get("descriptor") == descriptor
    ]
    _need(len(candidates) == 1, "ORIGINAL_PRIVATE_METHOD_NOT_UNIQUE")
    method = candidates[0]
    rows = _instructions(method)
    _need(rows and rows[0]["offset"] == 0
          and all(a["offset"] + a["length"] == b["offset"]
                  for a, b in zip(rows, rows[1:])),
          "ORIGINAL_JVM_INSTRUCTIONS_HAVE_GAPS")
    handlers = method.get("exception_handlers")
    _need(isinstance(handlers, list), "ORIGINAL_EXCEPTION_TABLE_MISSING")
    positions = {r["offset"]: i for i, r in enumerate(rows)}
    try:
        incoming = {to for _, to in _edges(rows)}
    except BooleanJoinWitnessError:
        raise EnumListFallbackSourceError(
            "ORIGINAL_BRANCH_GRAPH_INVALID"
        ) from None
    regions = []
    for handler in handlers:
        if handler.get("catch_type") != "java/lang/Exception":
            continue
        start, end, catch = (
            handler.get("start_pc"), handler.get("end_pc"),
            handler.get("handler_pc")
        )
        if any(type(x) is not int or x not in positions
               for x in (start, end, catch)):
            continue
        a, b, c = positions[start], positions[end], positions[catch]
        if c != b+1 or c+1 >= len(rows) or b-a != len(_SHAPE):
            continue
        block = rows[a:b]
        if tuple(r.get("opcode") for r in block) != _SHAPE:
            continue
        after_jump, caught, after = rows[b:c+2]
        if (after_jump.get("opcode") != "0xa7"
                or after_jump.get("branch_target_offset") != after["offset"]
                or caught.get("opcode") != "0x4e"):
            continue
        # The alternative (non-null) body is the only permitted explicit
        # incoming branch into this local protected region.
        allowed = {block[17]["offset"]}
        interior = {row["offset"] for row in block[1:]}
        if (interior & (incoming - allowed)
                or any(h is not handler and h.get("handler_pc") in interior
                       for h in handlers)):
            continue
        parsed = _parse_block(original, block, after_jump)
        if parsed is None:
            continue
        source, details = parsed
        regions.append({
            "original_start_pc":start,
            "original_end_pc":end,
            "original_catch_pc":catch,
            "original_protected_opcode_count":len(block),
            **details,
        })
    _need(len({r["original_start_pc"] for r in regions}) == len(regions),
          "ORIGINAL_PROTECTED_SOURCE_REGION_DUPLICATE")
    return {
        "private_verified_enum_list_boolean_regions":regions,
        "exact_original_enum_list_fallback_source_regions":len(regions),
        "original_two_list_add_results_discarded":True,
        "original_reference_and_boolean_side_effect_order_preserved":True,
        "original_nested_enum_java_source_names_certified":False,
        "original_external_field_declaration_owners_verified":False,
        "complete_original_java_method_compiled":False,
        "runtime_equivalence_certified":False,
    }


def recover_private_enum_list_fallback(
    jar:Path,owner_entry:str,private_method:str,descriptor:str,
    output:Path,*,original_sha256:str,
)->dict:
    jar,out=Path(jar),Path(output)
    _need(not out.exists() and not out.is_symlink(),"OUTPUT_ALREADY_EXISTS")
    _need(type(original_sha256) is str
          and _SHA.fullmatch(original_sha256) is not None,
          "INVALID_ORIGINAL_COMPLETE_JAR_PIN")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar)==original_sha256.lower(),
          "ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(owner_entry) is str and owner_entry.endswith(".class")
          and not owner_entry.startswith("/")
          and "\\" not in owner_entry
          and all(x not in ("",".","..") and ":" not in x
                  for x in owner_entry.split("/")),
          "INVALID_ORIGINAL_JVM_OWNER_ENTRY")
    try:
        with ZipFile(jar) as archive:
            _need(archive.namelist().count(owner_entry)==1,
                  "ORIGINAL_CLASSFILE_NOT_UNIQUE")
            original=profile_jar_class(jar,owner_entry)
        proof=plan_original_enum_list_fallback(
            original,private_method,descriptor)
    except (OSError,BadZipFile,BytecodeProfileError,
            ScalarInitializerRecoveryError,KeyError,IndexError):
        raise EnumListFallbackSourceError(
            "ORIGINAL_ENUM_LIST_SOURCE_INPUT_UNVERIFIABLE"
        ) from None
    _need(_digest(jar)==original_sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_PROOF")
    private=proof.pop("private_verified_enum_list_boolean_regions")
    _need(bool(private),"NO_EXACT_ENUM_LIST_BOOLEAN_FALLBACK_REGION")
    source="".join(x["private_java_source"] for x in private)
    raw=json.dumps(private,sort_keys=True,indent=2)+"\n"
    public={
        "schema_version":1,
        "kind":"exact_original_private_enum_list_boolean_source",
        "research_only":True,
        "whole_original_jar_sha256":original_sha256.lower(),
        "private_jvm_operands_sha256":hashlib.sha256(raw.encode()).hexdigest(),
        "private_java_source_sha256":hashlib.sha256(source.encode()).hexdigest(),
        **proof,
    }
    out.mkdir(parents=True,exist_ok=False)
    for name,value in (
        ("enum-list-fallback.private.json",raw),
        ("enum-list-fallback.private.java.txt",source),
        ("enum-list-fallback.aggregate.json",
         json.dumps(public,sort_keys=True,indent=2)+"\n"),
    ):
        with (out/name).open("x",encoding="utf-8",newline="\n") as file:
            file.write(value)
    return public


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar",type=Path)
    p.add_argument("private_owner_class_entry")
    p.add_argument("private_method_name")
    p.add_argument("private_method_descriptor")
    p.add_argument("new_private_output_directory",type=Path)
    p.add_argument("--original-sha256",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(recover_private_enum_list_fallback(
            a.original_jar,a.private_owner_class_entry,
            a.private_method_name,a.private_method_descriptor,
            a.new_private_output_directory,original_sha256=a.original_sha256,
        ),sort_keys=True))
    except EnumListFallbackSourceError as e:
        p.error(str(e))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
