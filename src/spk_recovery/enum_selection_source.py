"""R76: exact original v309 final 36-op enum selection protected source.

Prove two original same-key Properties.getProperty reads, exact String
contains/split/equalsIgnoreCase calls and exact double split evaluation,
conditional nested enum valueOf, and two ordered owner reference writes.
All original literals/members stay PRIVATE. Does not certify original
nested-class Java identities or whole method/runtime parity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, BadZipFile

from .boolean_join_witness import BooleanJoinWitnessError, _edges
from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .local_exception_primitive_source import _literal, _name, _owner_name
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)


class EnumSelectionSourceError(ValueError):
    """Original 36-op reference selector JVM source is unproven."""


_PIN = re.compile(r"[a-fA-F0-9]{64}\Z")
_OPS = (
    "0x01", "0xb3", "0x2b", "0x12", "0xb6", "0xc6",
    "0x2b", "0x12", "0xb6", "0x4e", "0x2d", "0x12",
    "0xb6", "0x99", "0x2d", "0x12", "0xb6", "0x03",
    "0x32", "0x3a", "0x2d", "0x12", "0xb6", "0x04",
    "0x32", "0x3a", "0x19", "0xb2", "0xb6", "0xb6",
    "0x99", "0x19", "0xb8", "0xb3", "0xb2", "0xb3",
)


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise EnumSelectionSourceError(reason)


def _field_same(a: dict, b: dict) -> bool:
    return all(a.get(k) == b.get(k)
               for k in ("owner", "name", "descriptor"))


def _call(row: dict, opcode: str, owner: str,
          name: str, descriptor: str) -> bool:
    return all((
        row.get("opcode") == opcode,
        row.get("owner") == owner,
        row.get("name") == name,
        row.get("descriptor") == descriptor,
    ))


def _parse_36(profile: dict, body: list[dict], endjump: dict,
              fields: dict) -> tuple[str, dict] | None:
    owner = profile["internal_name"]
    if tuple(row.get("opcode") for row in body) != _OPS:
        return None
    (null, unset, props, key, lookup, ifnull, props2, key2,
     lookup2, store_text, load_text, dot, contains, if_no_dot,
     load_text2, regex, split1, zero, first, store_first,
     load_text3, regex2, split2, one, second, store_second,
     load_suffix, external_enum, name_call, equals, if_diff,
     load_prefix, value_of, store_source_enum,
     load_source_enum, store_target_enum) = body
    if (unset.get("owner") != owner
            or store_source_enum.get("owner") != owner
            or store_target_enum.get("owner") != owner
            or not _field_same(unset, store_target_enum)
            or not _field_same(store_source_enum, load_source_enum)
            or unset.get("descriptor")
            != store_source_enum.get("descriptor")
            or type(unset.get("descriptor")) is not str
            or not unset["descriptor"].startswith("L")
            or not unset["descriptor"].endswith(";")
            or not all(fields.get((f.get("name"), f.get("descriptor")), {})
                       .get("access", 0) & 0x0008
                       for f in (unset, store_source_enum, store_target_enum))
            or not _call(lookup, "0xb6", "java/util/Properties",
                         "getProperty", "(Ljava/lang/String;)Ljava/lang/String;")
            or not _call(lookup2, "0xb6", "java/util/Properties",
                         "getProperty", "(Ljava/lang/String;)Ljava/lang/String;")
            or key.get("constant_pool_tag") != 8
            or key2.get("constant_pool_tag") != 8
            or type(key.get("constant")) is not str
            or key.get("constant") != key2.get("constant")
            or dot.get("constant_pool_tag") != 8
            or regex.get("constant_pool_tag") != 8
            or regex2.get("constant_pool_tag") != 8
            or type(dot.get("constant")) is not str
            or type(regex.get("constant")) is not str
            or regex.get("constant") != regex2.get("constant")
            or not _call(contains, "0xb6", "java/lang/String",
                         "contains", "(Ljava/lang/CharSequence;)Z")
            or not _call(split1, "0xb6", "java/lang/String",
                         "split", "(Ljava/lang/String;)[Ljava/lang/String;")
            or not _call(split2, "0xb6", "java/lang/String",
                         "split", "(Ljava/lang/String;)[Ljava/lang/String;")
            or not _call(equals, "0xb6", "java/lang/String",
                         "equalsIgnoreCase", "(Ljava/lang/String;)Z")):
        return None
    if (ifnull.get("branch_target_offset") != endjump["offset"]
            or if_no_dot.get("branch_target_offset") != endjump["offset"]
            or if_diff.get("branch_target_offset") != endjump["offset"]):
        return None
    field_enum_desc = external_enum.get("descriptor")
    if (external_enum.get("opcode") != "0xb2"
            or type(field_enum_desc) is not str
            or not field_enum_desc.startswith("L")
            or not field_enum_desc.endswith(";")
            or name_call.get("owner") != field_enum_desc[1:-1]
            or name_call.get("name") != "name"
            or name_call.get("descriptor") != "()Ljava/lang/String;"
            or value_of.get("owner") != unset["descriptor"][1:-1]
            or value_of.get("name") != "valueOf"
            or value_of.get("descriptor")
            != "(Ljava/lang/String;)" + unset["descriptor"]):
        return None
    # If producer/consumer storage was changed, a Java source fragment
    # might change the values of the original target fields.
    if (load_text["opcode"] != "0x2d"
            or load_text2["opcode"] != "0x2d"
            or load_text3["opcode"] != "0x2d"
            or load_prefix.get("opcode") != "0x19"
            or load_suffix.get("opcode") != "0x19"
            # Original local4/local5 correspond to the first/second split.
            # Checking only opcodes permits swapped values with identical CFG.
            or store_first.get("local_index") != 4
            or store_second.get("local_index") != 5
            or load_prefix.get("local_index") != 4
            or load_suffix.get("local_index") != 5
            or zero["opcode"] != "0x03"
            or one["opcode"] != "0x04"):
        return None
    enum_name = (_owner_name(external_enum["owner"])
                 + "." + _name(external_enum["name"]))
    field_source = _name(store_source_enum["name"])
    field_target = _name(unset["name"])
    prop = "originalLocalSlot1.getProperty(" + _literal(key) + ")"
    regex_lit = _literal(regex)
    src = (
        "try {\n"
        "    " + field_target + " = null;\n"
        "    if (" + prop + " != null) {\n"
        "        String originalPropertyText = " + prop + ";\n"
        "        if (originalPropertyText.contains(" + _literal(dot) + ")) {\n"
        "            String originalPrefix = originalPropertyText.split("
        + regex_lit + ")[0];\n"
        "            String originalSuffix = originalPropertyText.split("
        + regex_lit + ")[1];\n"
        "            if (originalSuffix.equalsIgnoreCase("
        + enum_name + ".name())) {\n"
        "                " + field_source + " = "
        + _owner_name(value_of["owner"]) + ".valueOf(originalPrefix);\n"
        "                " + field_target + " = " + field_source + ";\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "} catch (java.lang.Exception ignored) {\n}\n"
    )
    return src, {
        "private_property_key":key["constant"],
        "private_contains_literal":dot["constant"],
        "private_split_regex":regex["constant"],
        "private_owner_target_enum":unset["descriptor"],
        "private_enum_name_accessor":external_enum,
        "private_first_enum_write":store_source_enum,
        "private_second_enum_write":store_target_enum,
        "original_split_expression_evaluated_twice":True,
        "original_property_lookup_evaluated_twice_when_nonnull":True,
        "original_first_enum_field_copied_into_second_field":True,
    }


def plan_private_final_enum_source(
    original: dict, method_name: str, descriptor: str,
) -> dict:
    owner = original.get("internal_name")
    _need(type(owner) is str and owner, "ORIGINAL_OWNER_MISSING")
    selected = [m for m in original.get("methods", [])
                if m.get("name") == method_name
                and m.get("descriptor") == descriptor]
    _need(len(selected) == 1, "ORIGINAL_PRIVATE_METHOD_NOT_UNIQUE")
    method = selected[0]
    rows = _instructions(method)
    _need(rows and rows[0]["offset"] == 0
          and all(a["offset"] + a["length"] == b["offset"]
                  for a, b in zip(rows, rows[1:])),
          "ORIGINAL_JVM_INSTRUCTIONS_HAVE_GAP")
    handlers = method.get("exception_handlers")
    _need(isinstance(handlers, list), "ORIGINAL_EXCEPTION_TABLE_MISSING")
    positions = {r["offset"]: i for i, r in enumerate(rows)}
    try:
        incoming = {b for _, b in _edges(rows)}
    except BooleanJoinWitnessError:
        raise EnumSelectionSourceError("ORIGINAL_BRANCH_GRAPH_INVALID") from None
    fields = _fields(original)
    proven = []
    for h in handlers:
        if h.get("catch_type") != "java/lang/Exception":
            continue
        start, end, target = (h.get("start_pc"), h.get("end_pc"),
                              h.get("handler_pc"))
        if any(type(v) is not int or v not in positions
               for v in (start, end, target)):
            continue
        a,b,c = positions[start], positions[end], positions[target]
        if c != b+1 or c+1 >= len(rows) or b-a != len(_OPS):
            continue
        block = rows[a:b]
        if tuple(x.get("opcode") for x in block) != _OPS:
            continue
        jump, caught, after = rows[b:c+2]
        if (jump.get("opcode") != "0xa7"
                or jump.get("branch_target_offset") != after["offset"]
                or caught.get("opcode") != "0x4e"):
            continue
        # All original conditional branches target the protected exit.
        # No legal outside edge enters the source block interior.
        inside = {r["offset"] for r in block[1:]}
        if (incoming & inside
                or any(other is not h and other.get("handler_pc") in inside
                       for other in handlers)):
            continue
        form = _parse_36(original, block, jump, fields)
        if form is None:
            continue
        src, details = form
        proven.append({
            "original_start_pc":start,
            "original_end_pc":end,
            "original_exception_handler_pc":target,
            "private_generated_java_source":src,
            "private_original_source_facts":details,
        })
    _need(len({p["original_start_pc"] for p in proven}) == len(proven),
          "DUPLICATE_FINAL_ENUM_REGION")
    return {
        "private_original_final_enum_regions":proven,
        "exact_original_36_op_final_enum_regions":len(proven),
        "original_two_string_splits_preserved":True,
        "original_conditional_enum_copy_write_order_preserved":True,
        "original_empty_exception_catch_verified":True,
        "actual_java_nested_enum_identity_names_certified":False,
        "complete_original_697_op_method_java_compiled":False,
        "original_runtime_equivalence_certified":False,
    }


def replay_private_final_enum(
    jar: Path, class_entry: str, method: str, descriptor: str,
    output: Path, *, original_sha256: str,
) -> dict:
    jar, out = Path(jar), Path(output)
    _need(not out.exists() and not out.is_symlink(),
          "OUTPUT_ALREADY_EXISTS")
    _need(type(original_sha256) is str
          and _PIN.fullmatch(original_sha256) is not None,
          "INVALID_ORIGINAL_WHOLE_JAR_PIN")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_NOT_FOUND_OR_SYMLINK")
    _need(_digest(jar) == original_sha256.lower(),
          "ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(class_entry) is str and class_entry.endswith(".class")
          and not class_entry.startswith("/")
          and "\\" not in class_entry
          and all(x not in ("", ".", "..") and ":" not in x
                  for x in class_entry.split("/")),
          "INVALID_ORIGINAL_PRIVATE_CLASS_ENTRY")
    try:
        with ZipFile(jar) as archive:
            _need(archive.namelist().count(class_entry)==1,
                  "ORIGINAL_JVM_CLASSFILE_ENTRY_NOT_UNIQUE")
            source=profile_jar_class(jar,class_entry)
        proof=plan_private_final_enum_source(source,method,descriptor)
    except (BadZipFile,OSError,BytecodeProfileError,
            ScalarInitializerRecoveryError,KeyError,TypeError,IndexError):
        raise EnumSelectionSourceError(
            "ORIGINAL_FINAL_ENUM_SOURCE_INPUT_UNVERIFIABLE"
        ) from None
    _need(_digest(jar)==original_sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_SOURCE_PROOF")
    sites=proof.pop("private_original_final_enum_regions")
    _need(len(sites) == 1,"EXPECTED_SINGLE_EXACT_FINAL_ENUM_SOURCE_REGION")
    src="".join(x["private_generated_java_source"] for x in sites)
    raw=json.dumps(sites,indent=2,sort_keys=True)+"\n"
    report={
        "schema_version":1,
        "kind":"exact_original_private_enum_selection_source",
        "original_complete_jar_sha256":original_sha256.lower(),
        "private_source_sha256":hashlib.sha256(src.encode()).hexdigest(),
        "private_jvm_sites_sha256":hashlib.sha256(raw.encode()).hexdigest(),
        "research_only":True,
        **proof,
    }
    out.mkdir(parents=True,exist_ok=False)
    for name,value in (
        ("enum-selection.private.java.txt",src),
        ("enum-selection.private.json",raw),
        ("enum-selection.aggregate.json",
         json.dumps(report,indent=2,sort_keys=True)+"\n"),
    ):
        with (out/name).open("x",encoding="utf-8",newline="\n") as fd:
            fd.write(value)
    return report


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar",type=Path)
    p.add_argument("private_owner_class_entry")
    p.add_argument("private_method_name")
    p.add_argument("private_method_descriptor")
    p.add_argument("new_private_output",type=Path)
    p.add_argument("--original-sha256",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(replay_private_final_enum(
            a.original_jar,a.private_owner_class_entry,
            a.private_method_name,a.private_method_descriptor,
            a.new_private_output,original_sha256=a.original_sha256,
        ),sort_keys=True))
    except EnumSelectionSourceError as exc:
        p.error(str(exc))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
