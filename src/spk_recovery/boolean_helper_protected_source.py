"""R74: exact original v309 Boolean helper/callback protected Java sources.

Recover two 15/19-op JVM empty-Exception-catch regions. The 15-op
form writes false on null, but otherwise calls the original owner static
boolean helper WITHOUT writing the field. The 19-op form calls an external
static boolean helper BEFORE the static field write on both branches.
Original literal keys/member names are emitted only in private outputs.
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


class BooleanHelperSourceError(ValueError):
    """Original Boolean helper protected source is unsupported."""


_SHA = re.compile(r"[a-fA-F0-9]{64}\Z")
_FIFTEEN = ("0x2b","0x12","0xb6","0xc7","0x03","0xb3","0xa7",
            "0x2b","0x12","0xb6","0xb8","0xb6","0x3e","0x1d","0xb8")
_NINETEEN = ("0x2b","0x12","0xb6","0xc7","0x03","0xb8","0x03","0xb3",
             "0xa7","0x2b","0x12","0xb6","0xb8","0xb6","0x3e",
             "0x1d","0xb8","0x1d","0xb3")


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise BooleanHelperSourceError(message)


def _lookup(x: dict) -> bool:
    return (x.get("opcode") == "0xb6"
            and x.get("owner") == "java/util/Properties"
            and x.get("name") == "getProperty"
            and x.get("descriptor")
            == "(Ljava/lang/String;)Ljava/lang/String;")


def _unbox(convert: dict, val: dict) -> bool:
    return (convert.get("opcode") == "0xb8"
            and convert.get("descriptor")
            == "(Ljava/lang/String;)Ljava/lang/Boolean;"
            and val.get("opcode") == "0xb6"
            and val.get("owner") == "java/lang/Boolean"
            and val.get("name") == "booleanValue"
            and val.get("descriptor") == "()Z")


def _helper_expression(row: dict, owner: str,
                       original: dict, *, external: bool) -> str | None:
    if (row.get("opcode") != "0xb8"
            or row.get("descriptor") != "(Z)V"
            or type(row.get("owner")) is not str
            or type(row.get("name")) is not str):
        return None
    if external:
        if row["owner"] == owner:
            return None
        return _owner_name(row["owner"]) + "." + _name(row["name"])
    if row["owner"] != owner:
        return None
    methods = original.get("methods", [])
    if not any(m.get("name") == row["name"]
               and m.get("descriptor") == "(Z)V"
               and m.get("access", 0) & 0x0008
               for m in methods):
        return None
    return _name(row["name"])


def _parse_family(
    profile: dict, group: list[dict], owner: str, fields: dict,
    endjump: dict
) -> tuple[str, str] | None:
    ops = tuple(row.get("opcode") for row in group)
    if ops == _FIFTEEN:
        (r0, key, get, cond, _, null_store, jump,
         r1, key2, get2, convert, val, local, load, helper) = group
        field = null_store
        helper_name = _helper_expression(
            helper, owner, profile, external=False)
        other_helper = None
        branch_target = r1["offset"]
    elif ops == _NINETEEN:
        (r0, key, get, cond, _, null_helper, _,
         null_store, jump, r1, key2, get2, convert,
         val, local, load, helper, load2, field2) = group
        field = null_store
        helper_name = _helper_expression(
            helper, owner, profile, external=True)
        other_helper = _helper_expression(
            null_helper, owner, profile, external=True)
        branch_target = r1["offset"]
        if (load2["opcode"] != "0x1d"
                or not other_helper or other_helper != helper_name
                or field2.get("owner") != field.get("owner")
                or field2.get("name") != field.get("name")
                or field2.get("descriptor") != field.get("descriptor")):
            return None
    else:
        return None
    if (not helper_name
            or not _lookup(get)
            or not _lookup(get2)
            or not _unbox(convert, val)
            or key.get("constant_pool_tag") != 8
            or key2.get("constant_pool_tag") != 8
            or type(key.get("constant")) is not str
            or key.get("constant") != key2.get("constant")
            or cond.get("branch_target_offset") != branch_target
            or jump.get("branch_target_offset") != endjump["offset"]
            or field.get("owner") != owner
            or field.get("descriptor") != "Z"
            or (field.get("name"), "Z") not in fields
            or not fields[(field["name"], "Z")]["access"] & 0x0008):
        return None
    field_name = _name(field["name"])
    lookup = "originalLocalSlot1.getProperty(" + _literal(key) + ")"
    converter = (_owner_name(convert["owner"]) + "."
                 + _name(convert["name"]))
    inner = (
        "        boolean originalParsedBoolean = " + converter
        + "(" + lookup + ").booleanValue();\n"
        + "        " + helper_name + "(originalParsedBoolean);\n"
    )
    if ops == _FIFTEEN:
        source = (
            "try {\n    if (" + lookup + " == null) {\n"
            "        " + field_name + " = false;\n"
            "    } else {\n"
            + inner
            + "    }\n"
            "} catch (java.lang.Exception ignored) {\n}\n"
        )
        return "nonnull_owner_boolean_helper", source
    source = (
        "try {\n    if (" + lookup + " == null) {\n"
        "        " + other_helper + "(false);\n"
        "        " + field_name + " = false;\n"
        "    } else {\n"
        + inner
        + "        " + field_name + " = originalParsedBoolean;\n"
        "    }\n"
        "} catch (java.lang.Exception ignored) {\n}\n"
    )
    return "boolean_helper_then_field_write", source


def plan_original_boolean_helper_regions(
    profile: dict, private_method_name: str, descriptor: str,
) -> dict:
    owner = profile.get("internal_name")
    _need(type(owner) is str and owner, "ORIGINAL_OWNER_MISSING")
    selected = [
        m for m in profile.get("methods", [])
        if m.get("name") == private_method_name
        and m.get("descriptor") == descriptor
    ]
    _need(len(selected) == 1, "PRIVATE_JVM_METHOD_IDENTITY_NOT_UNIQUE")
    method = selected[0]
    rows = _instructions(method)
    _need(rows and rows[0]["offset"] == 0
          and all(a["offset"] + a["length"] == b["offset"]
                  for a, b in zip(rows, rows[1:])),
          "ORIGINAL_JVM_METHOD_HAS_GAP")
    fields = _fields(profile)
    handlers = method.get("exception_handlers")
    _need(isinstance(handlers, list), "ORIGINAL_EXCEPTION_TABLE_MISSING")
    positions = {x["offset"]: i for i, x in enumerate(rows)}
    try:
        incoming = {target for _, target in _edges(rows)}
    except BooleanJoinWitnessError:
        raise BooleanHelperSourceError("ORIGINAL_BRANCH_GRAPH_INVALID") from None
    results = []
    types: dict[str, int] = {}
    for h in handlers:
        if h.get("catch_type") != "java/lang/Exception":
            continue
        start, end, caught_pc = (h.get("start_pc"),
                                  h.get("end_pc"), h.get("handler_pc"))
        if any(type(v) is not int or v not in positions
               for v in (start, end, caught_pc)):
            continue
        a,b,c = positions[start], positions[end], positions[caught_pc]
        if c != b + 1 or c + 1 >= len(rows):
            continue
        block=rows[a:b]
        if len(block) not in (15,19):
            continue
        skip, exception, afterward=rows[b:c+2]
        if (skip.get("opcode") != "0xa7"
                or skip.get("branch_target_offset") != afterward["offset"]
                or exception.get("opcode") != "0x4e"):
            continue
        valid_targets = {block[7]["offset"]} if len(block)==15 else {
            block[9]["offset"]
        }
        interior = {r["offset"] for r in block[1:]}
        if (interior & (incoming - valid_targets)
                or any(other is not h and other.get("handler_pc") in interior
                       for other in handlers)):
            continue
        found=_parse_family(profile,block,owner,fields,skip)
        if found is None:
            continue
        kind,source=found
        types[kind]=types.get(kind,0)+1
        results.append({
            "kind":kind,
            "original_protected_start":start,
            "original_protected_end":end,
            "original_exception_handler_pc":caught_pc,
            "private_original_JVM_rows":block,
            "private_java_source":source,
        })
    _need(len({r["original_protected_start"] for r in results})
          == len(results), "DUPLICATED_ORIGINAL_HELPER_REGIONS")
    return {
        "private_original_boolean_helper_regions":results,
        "original_exact_boolean_helper_source_regions":len(results),
        "source_form_counts":dict(sorted(types.items())),
        "original_exception_handlers_empty":True,
        "original_nullable_boolean_lookup_repeated_when_nonnull":True,
        "original_boolean_helper_invocations_in_branch_order_preserved":True,
        "complete_original_method_compiled":False,
        "external_helper_method_side_effects_certified":False,
        "real_client_runtime_equivalence_certified":False,
    }


def private_replay_boolean_helper(
    jar:Path,class_entry:str,method_name:str,descriptor:str,
    dest:Path,*,sha256:str,
)->dict:
    jar,out=Path(jar),Path(dest)
    _need(not out.exists() and not out.is_symlink(),
          "OUTPUT_ALREADY_EXISTS")
    _need(type(sha256) is str and _SHA.fullmatch(sha256) is not None,
          "INVALID_WHOLE_JAR_SHA256")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_NOT_FILE_OR_SYMLINK")
    _need(_digest(jar)==sha256.lower(),"ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(class_entry) is str and class_entry.endswith(".class")
          and not class_entry.startswith("/")
          and "\\" not in class_entry
          and all(x not in ("",".","..") and ":" not in x
                  for x in class_entry.split("/")),
          "INVALID_ORIGINAL_PRIVATE_CLASS_ENTRY")
    try:
        with ZipFile(jar) as z:
            _need(z.namelist().count(class_entry)==1,
                  "ORIGINAL_OWNER_CLASSFILE_NOT_UNIQUE")
            original=profile_jar_class(jar,class_entry)
        proof=plan_original_boolean_helper_regions(
            original,method_name,descriptor)
    except (OSError,BadZipFile,BytecodeProfileError,
            ScalarInitializerRecoveryError,KeyError,IndexError,TypeError):
        raise BooleanHelperSourceError(
            "ORIGINAL_BOOLEAN_HELPER_PROOF_INPUT_UNVERIFIABLE"
        ) from None
    _need(_digest(jar)==sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_SOURCE_PROOF")
    private=proof.pop("private_original_boolean_helper_regions")
    _need(private,"NO_EXACT_BOOLEAN_HELPER_PROTECTED_SOURCE")
    raw=json.dumps(private,sort_keys=True,indent=2)+"\n"
    fragment="".join(x["private_java_source"] for x in private)
    public={
        "schema_version":1,
        "kind":"private_original_boolean_helper_empty_catch_source",
        "original_complete_jar_sha256":sha256.lower(),
        "private_regions_sha256":hashlib.sha256(raw.encode()).hexdigest(),
        "private_java_source_sha256":hashlib.sha256(fragment.encode()).hexdigest(),
        "research_only":True,
        **proof,
    }
    out.mkdir(parents=True,exist_ok=False)
    for name,payload in (
        ("boolean-helper-regions.private.json",raw),
        ("boolean-helper-sources.private.java.txt",fragment),
        ("boolean-helper-sources.aggregate.json",
         json.dumps(public,sort_keys=True,indent=2)+"\n"),
    ):
        with (out/name).open("x",encoding="utf-8",newline="\n") as fd:
            fd.write(payload)
    return public


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar",type=Path)
    p.add_argument("original_private_class_entry")
    p.add_argument("original_private_method_name")
    p.add_argument("original_private_method_descriptor")
    p.add_argument("new_private_output",type=Path)
    p.add_argument("--sha256",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(private_replay_boolean_helper(
            a.original_jar,a.original_private_class_entry,
            a.original_private_method_name,
            a.original_private_method_descriptor,
            a.new_private_output,sha256=a.sha256,
        ),sort_keys=True))
    except BooleanHelperSourceError as exc:
        p.error(str(exc))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
