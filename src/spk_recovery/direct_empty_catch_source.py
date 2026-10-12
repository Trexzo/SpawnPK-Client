"""R68: recover exact six-op original Boolean stores under empty catches.

Extract PRIVATE Java source for contiguous original JVM protected regions:
aload_1; ldc String; invokevirtual lookup; invokestatic conversion;
invokevirtual Boolean.booleanValue; putstatic Boolean target;
goto over a single astore_3 empty Exception catch.
No surrounding Java method, local types or runtime parity is implied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from .boolean_join_witness import BooleanJoinWitnessError, _edges
from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .local_exception_primitive_source import (
    _literal, _name, _owner_name,
)
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)


class DirectLocalExceptionSourceError(ValueError):
    """No exact original direct protected Boolean source form exists."""


_PIN = re.compile(r"[0-9a-fA-F]{64}\Z")
_OPS = ("0x2b", "0x12", "0xb6", "0xb8", "0xb6", "0xb3")


def _need(test: bool, reason: str) -> None:
    if not test:
        raise DirectLocalExceptionSourceError(reason)


def plan_direct_empty_catch_sources(
    original: dict, method_name: str, descriptor: str,
) -> dict:
    owner = original.get("internal_name")
    _need(type(owner) is str and owner, "ORIGINAL_OWNER_UNAVAILABLE")
    matched = [
        method for method in original.get("methods", [])
        if method.get("name") == method_name
        and method.get("descriptor") == descriptor
    ]
    _need(len(matched) == 1, "PRIVATE_ORIGINAL_METHOD_NOT_UNIQUE")
    method = matched[0]
    instructions = _instructions(method)
    _need(instructions and instructions[0]["offset"] == 0
          and all(a["offset"] + a["length"] == b["offset"]
                  for a, b in zip(instructions, instructions[1:])),
          "ORIGINAL_JVM_METHOD_INSTRUCTION_GAP")
    try:
        edges = _edges(instructions)
    except BooleanJoinWitnessError:
        raise DirectLocalExceptionSourceError(
            "ORIGINAL_JVM_BRANCH_TARGET_NOT_VERIFIABLE"
        ) from None
    incoming = {target for _, target in edges}
    handlers = method.get("exception_handlers")
    _need(isinstance(handlers, list), "ORIGINAL_EXCEPTION_TABLE_MISSING")
    locals_ = [h for h in handlers if h.get("catch_type")
               == "java/lang/Exception"]
    offsets = {row["offset"]: i for i, row in enumerate(instructions)}
    declared = _fields(original)
    accepted = []
    for handler in locals_:
        a,b,c=(handler.get("start_pc"),handler.get("end_pc"),
               handler.get("handler_pc"))
        if (any(type(v) is not int or v not in offsets
                for v in (a,b,c))):
            continue
        i,j,k=offsets[a],offsets[b],offsets[c]
        if k!=j+1 or k+1>=len(instructions):
            continue
        group=instructions[i:j]
        if len(group)!=6 or tuple(x.get("opcode") for x in group)!=_OPS:
            continue
        outside, ignored, after = instructions[j:k+2]
        if (outside.get("opcode")!="0xa7"
                or outside.get("branch_target_offset")!=after["offset"]
                or ignored.get("opcode")!="0x4e"):
            continue
        load,key,lookup,convert,unbox,store=group
        if (store.get("owner")!=owner
                or store.get("descriptor")!="Z"
                or (store.get("name"),"Z") not in declared
                or not declared[(store["name"],"Z")]["access"] & 0x0008
                or key.get("opcode")!="0x12"
                or key.get("constant_pool_tag")!=8
                or type(key.get("constant")) is not str):
            continue
        rdesc=lookup.get("descriptor")
        if (type(rdesc) is not str
                or not rdesc.startswith("(Ljava/lang/String;)L")
                or not rdesc.endswith(";")
                or convert.get("descriptor")
                != "(" + rdesc.split(")",1)[1] + ")Ljava/lang/Boolean;"
                or unbox.get("owner")!="java/lang/Boolean"
                or unbox.get("name")!="booleanValue"
                or unbox.get("descriptor")!="()Z"):
            continue
        if (any(row["offset"] in incoming
                for row in group[1:])
                or any(other is not handler
                       and other.get("handler_pc")
                       in {row["offset"] for row in group[1:]}
                       for other in handlers)):
            continue
        # Preserve the original virtual lookup and conversion call exactly.
        source=(
            "try {\n"
            "    " + _name(store["name"]) + " = "
            + _owner_name(convert["owner"]) + "."
            + _name(convert["name"]) + "("
            "originalLocalSlot1." + _name(lookup["name"])
            + "(" + _literal(key) + ")).booleanValue();\n"
            "} catch (java.lang.Exception ignored) {\n"
            "}\n"
        )
        accepted.append({
            "private_original_string_key":key["constant"],
            "private_original_target_field":store["name"],
            "private_original_lookup_owner":lookup["owner"],
            "original_start_pc":a,
            "original_end_pc":b,
            "original_handler_pc":c,
            "private_source":source,
            "exact_original_empty_catch_verified":True,
            "source_local_slot_one_type_recovered":False,
        })
    _need(len({x["original_start_pc"] for x in accepted})==len(accepted),
          "DUPLICATE_OR_OVERLAPPING_DIRECT_PROTECTED_REGIONS")
    return {
        "private_original_protected_sources":accepted,
        "original_local_exception_handlers":len(locals_),
        "direct_six_instruction_boolean_try_catch_regions":len(accepted),
        "other_local_exception_regions_not_handled_by_R68":
            len(locals_)-len(accepted),
        "original_empty_catch_and_virtual_lookup_once_proven":True,
        "original_local_slot_one_java_type_recovered":False,
        "full_original_method_control_flow_source_recovered":False,
        "original_helper_side_effects_equivalent":False,
        "real_client_runtime_equivalence_certified":False,
    }


def recover_private_direct_empty_catch_sources(
    original_jar:Path, original_class_entry:str,
    method_name:str, method_descriptor:str,
    output_root:Path, *,sha256:str,
)->dict:
    jar,out=Path(original_jar),Path(output_root)
    _need(not out.exists() and not out.is_symlink(),
          "OUTPUT_ALREADY_EXISTS")
    _need(type(sha256) is str and _PIN.fullmatch(sha256) is not None,
          "INVALID_WHOLE_ORIGINAL_JAR_SHA256")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar)==sha256.lower(),"ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(original_class_entry) is str
          and original_class_entry.endswith(".class")
          and not original_class_entry.startswith("/")
          and "\\" not in original_class_entry
          and all(p not in ("",".","..") and ":" not in p
                  for p in original_class_entry.split("/")),
          "INVALID_PRIVATE_ORIGINAL_CLASS_ENTRY")
    try:
        with ZipFile(jar) as zipfile:
            _need(zipfile.namelist().count(original_class_entry)==1,
                  "ORIGINAL_JAR_CLASS_ENTRY_NOT_UNIQUE")
            original=profile_jar_class(jar,original_class_entry)
        proof=plan_direct_empty_catch_sources(
            original,method_name,method_descriptor)
    except (OSError,BadZipFile,BytecodeProfileError,
            ScalarInitializerRecoveryError,KeyError,TypeError,IndexError):
        raise DirectLocalExceptionSourceError(
            "PRIVATE_ORIGINAL_DIRECT_REGION_NOT_VERIFIABLE"
        ) from None
    _need(_digest(jar)==sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_PROOF")
    private=proof.pop("private_original_protected_sources")
    _need(bool(private),"NO_EXACT_ORIGINAL_DIRECT_PROTECTED_SOURCES")
    source="".join(
        "// PRIVATE exact original protected Boolean source; local1 unresolved.\n"
        + x["private_source"] for x in private)
    raw=json.dumps(private,indent=2,sort_keys=True)+"\n"
    report={
        "schema_version":1,
        "kind":"private_original_exact_direct_boolean_empty_catch_source",
        "original_complete_jar_sha256":sha256.lower(),
        "private_protected_region_graph_sha256":
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "private_java_fragment_sha256":
            hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "research_only":True,
        **proof,
    }
    out.mkdir(parents=True,exist_ok=False)
    for filename,content in (
        ("direct-exception-sites.private.json",raw),
        ("direct-exception-source.private.java.txt",source),
        ("direct-exception.aggregate.json",
         json.dumps(report,indent=2,sort_keys=True)+"\n")
    ):
        with (out/filename).open("x",encoding="utf-8",newline="\n") as fd:
            fd.write(content)
    return report


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar",type=Path)
    p.add_argument("private_class_entry")
    p.add_argument("private_method_name")
    p.add_argument("private_method_descriptor")
    p.add_argument("new_private_output",type=Path)
    p.add_argument("--sha256",required=True)
    args=p.parse_args(argv)
    try:
        print(json.dumps(recover_private_direct_empty_catch_sources(
            args.original_jar,args.private_class_entry,
            args.private_method_name,args.private_method_descriptor,
            args.new_private_output,sha256=args.sha256,
        ),sort_keys=True))
    except DirectLocalExceptionSourceError as exc:
        p.error(str(exc))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
