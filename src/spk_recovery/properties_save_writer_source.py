"""R82: original v309 364-op settings-save writer source forms.

Only the exact bounded field -> StringConcatFactory -> BufferedWriter.write ->
newLine local JVM patterns are converted to PRIVATE Java source. File streams,
array loop, list filters, null-handling and file copy/delete are NOT invented.
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
from .local_exception_primitive_source import _literal, _name, _owner_name
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)


class SaveWriterSourceError(ValueError):
    """Original bounded BufferedWriter source pattern not proven."""


_PIN = re.compile(r"[0-9a-fA-F]{64}\Z")
_FIELD = ("0x2b", "0xb2", "0xba", "0xb6", "0x2b", "0xb6")
_ENUM = ("0x2b", "0xb2", "0xb6", "0xba", "0xb6", "0x2b", "0xb6")
_DESCRIPTORS = {"Z", "I", "Ljava/lang/String;"}


def require(ok: bool, why: str):
    if not ok:
        raise SaveWriterSourceError(why)


def _concat(profile: dict, row: dict, expected: str) -> str | None:
    if (row.get("opcode") != "0xba"
            or row.get("descriptor") != "(" + expected + ")Ljava/lang/String;"
            or row.get("name") != "makeConcatWithConstants"
            or row.get("invokedynamic_reserved") != 0):
        return None
    b = profile.get("bootstrap_methods")
    index = row.get("bootstrap_method_attr_index")
    if not (isinstance(b, list) and type(index) is int
            and 0 <= index < len(b)):
        return None
    site = b[index]
    handle = site.get("bootstrap_method", {})
    args = site.get("arguments", [])
    if (handle.get("owner") != "java/lang/invoke/StringConcatFactory"
            or handle.get("name") != "makeConcatWithConstants"
            or handle.get("reference_kind") != 6
            or not isinstance(args, list) or len(args) != 1
            or args[0].get("kind") != "string"):
        return None
    recipe = args[0].get("value")
    # One dynamic slot, a printable literal key, no constants or suffix.
    if (not isinstance(recipe, str) or not recipe.endswith("\x01")
            or recipe.count("\x01") != 1
            or "\x02" in recipe
            or not all(32 <= ord(ch) <= 126 for ch in recipe[:-1])):
        return None
    return recipe[:-1]


def _writer(row: dict, name: str) -> bool:
    return (row.get("opcode") == "0xb6"
            and row.get("owner") == "java/io/BufferedWriter"
            and row.get("name") == name
            and row.get("descriptor") == (
                "(Ljava/lang/String;)V" if name == "write" else "()V"))


def extract_writer_lines(profile: dict, method: dict) -> list[dict]:
    rows = _instructions(method)
    try:
        incoming = {destination for _, destination in _edges(rows)}
    except BooleanJoinWitnessError:
        raise SaveWriterSourceError("ORIGINAL_SAVE_METHOD_BRANCH_GRAPH_INVALID") from None
    owner = profile.get("internal_name")
    require(isinstance(owner, str) and owner,
            "ORIGINAL_SAVE_OWNER_NAME_MISSING")
    fields = _fields(profile)
    sites = []
    occupied = set()
    for i in range(len(rows)):
        opcodes = tuple(row.get("opcode") for row in rows[i:i+7])
        kind, size = None, 0
        if opcodes[:6] == _FIELD:
            kind, size = "direct", 6
        elif opcodes == _ENUM:
            kind, size = "enum_name", 7
        if kind is None:
            continue
        block = rows[i:i+size]
        field = block[1]
        dyn = block[2] if kind == "direct" else block[3]
        write = block[3] if kind == "direct" else block[4]
        new_line = block[5] if kind == "direct" else block[6]
        if not (_writer(write, "write") and _writer(new_line, "newLine")):
            continue
        desc = field.get("descriptor")
        if kind == "direct":
            if desc not in _DESCRIPTORS:
                continue
            value_desc = desc
            expr_suffix = ""
        else:
            call = block[2]
            if (not isinstance(desc, str) or not desc.startswith("L")
                    or not desc.endswith(";")
                    or call.get("opcode") != "0xb6"
                    or call.get("owner") != desc[1:-1]
                    or call.get("name") != "name"
                    or call.get("descriptor") != "()Ljava/lang/String;"):
                continue
            value_desc = "Ljava/lang/String;"
            expr_suffix = ".name()"
        literal = _concat(profile, dyn, value_desc)
        if literal is None:
            continue
        if (field.get("owner") == owner
                and not fields.get((field.get("name"), desc), {}).get("access", 0) & 0x0008):
            continue
        if (not isinstance(field.get("owner"), str)
                or not isinstance(field.get("name"), str)
                or not isinstance(desc, str)):
            continue
        interior = {row["offset"] for row in block[1:]}
        if incoming & interior:
            continue
        if any(j in occupied for j in range(i,i+size)):
            continue
        occupied.update(range(i,i+size))
        java_field = (_name(field["name"]) if field["owner"] == owner
                      else _owner_name(field["owner"]) + "." + _name(field["name"]))
        # Original static field is read exactly once, and concatenation
        # occurs before BufferedWriter.write and then newLine.
        source = ("originalLocalSlot1.write("
                  + json.dumps(literal, ensure_ascii=True)
                  + " + " + java_field + expr_suffix + ");\n"
                  + "originalLocalSlot1.newLine();\n")
        sites.append({
            "kind": kind,
            "original_JVM_start_offset": block[0]["offset"],
            "original_JVM_end_next_offset": (
                rows[i+size]["offset"] if i+size < len(rows) else method["code_length"]),
            "private_original_field": field,
            "private_original_concat_bootstrap": dyn.get("bootstrap_method_attr_index"),
            "private_original_concat_prefix": literal,
            "private_java_source_fragment": source,
        })
    return sites


def plan_original_save_writer_source(
    original: dict, private_method: str, descriptor: str,
) -> dict:
    method = [m for m in original.get("methods", [])
              if m.get("name") == private_method and m.get("descriptor") == descriptor]
    require(len(method) == 1, "ORIGINAL_SAVE_METHOD_NOT_UNIQUE")
    m = method[0]
    rows = _instructions(m)
    require(m.get("access") == 0x000a and descriptor == "()V"
            and len(rows) == 364 and rows[0]["offset"] == 0
            and all(x["offset"] + x["length"] == y["offset"]
                    for x,y in zip(rows,rows[1:])),
            "EXPECTED_ORIGINAL_PRIVATE_STATIC_364_OP_METHOD")
    handlers = m.get("exception_handlers")
    require(isinstance(handlers, list) and len(handlers) == 1
            and handlers[0].get("catch_type") == "java/lang/Exception",
            "EXPECTED_ONE_ORIGINAL_EXCEPTION_HANDLER")
    require(sum(x.get("opcode") == "0xba" for x in rows) == 46
            and sum(x.get("opcode") == "0xb6" for x in rows) == 102,
            "ORIGINAL_SAVE_DYNAMIC_AND_VIRTUAL_COUNTS_CHANGED")
    sites = extract_writer_lines(original, m)
    kinds = {"direct": 0, "enum_name": 0}
    descriptors = {"Z": 0, "I": 0, "Ljava/lang/String;": 0}
    for site in sites:
        kinds[site["kind"]] += 1
        desc = site["private_original_field"]["descriptor"]
        if site["kind"] == "direct":
            descriptors[desc] += 1
    require(kinds == {"direct": 41, "enum_name": 1}
            and descriptors == {"Z": 35, "I": 5, "Ljava/lang/String;": 1},
            "ORIGINAL_42_SAVE_WRITER_SOURCE_FORMS_NOT_EXACT")
    require(sum(_writer(x,"write") for x in rows) == 47
            and sum(_writer(x,"newLine") for x in rows) == 48,
            "ORIGINAL_BUFFERED_WRITER_CALL_INVENTORY_CHANGED")
    return {
        "private_original_writer_source_sites": sites,
        "private_ordered_writer_java_fragments": "\n".join(
            site["private_java_source_fragment"] for site in sites),
        "original_complete_method_jvm_instructions": 364,
        "original_BW_write_calls": 47,
        "original_BW_newline_calls": 48,
        "exact_original_simple_writer_source_forms": 41,
        "exact_original_enum_name_writer_source_forms": 1,
        "other_original_write_calls_unrecovered": 5,
        "original_simple_writer_field_descriptor_counts": descriptors,
        "original_invokedynamic_sites": 46,
        "original_invokevirtual_sites": 102,
        "original_typed_exception_entries": 1,
        "whole_original_save_method_java_compiled": False,
        "original_file_io_and_special_write_cases_recovered": False,
        "runtime_equivalence_certified": False,
    }


def replay_private_save_writer(
    jar: Path, class_entry: str, method: str, descriptor: str,
    output: Path, *, original_sha256: str,
) -> dict:
    jar, output = Path(jar), Path(output)
    require(not output.exists() and not output.is_symlink(),
            "OUTPUT_ALREADY_EXISTS")
    require(isinstance(original_sha256,str) and _PIN.fullmatch(original_sha256),
            "INVALID_ORIGINAL_JAR_PIN")
    require(jar.is_file() and not jar.is_symlink()
            and _digest(jar) == original_sha256.lower(),
            "ORIGINAL_JAR_SHA256_MISMATCH")
    require(isinstance(class_entry,str) and class_entry.endswith(".class")
            and not class_entry.startswith("/") and "\\" not in class_entry
            and all(part not in ("", ".", "..") and ":" not in part
                    for part in class_entry.split("/")),
            "INVALID_ORIGINAL_CLASS_ENTRY")
    try:
        with ZipFile(jar) as archive:
            require(archive.namelist().count(class_entry) == 1,
                    "ORIGINAL_CLASS_ENTRY_NOT_UNIQUE")
            profile = profile_jar_class(jar, class_entry)
        proof = plan_original_save_writer_source(profile,method,descriptor)
    except (BadZipFile,OSError,KeyError,TypeError,IndexError,
            BytecodeProfileError,ScalarInitializerRecoveryError):
        raise SaveWriterSourceError("PRIVATE_SAVE_WRITER_INPUT_UNVERIFIABLE") from None
    require(_digest(jar) == original_sha256.lower(),
            "ORIGINAL_JAR_CHANGED_DURING_SOURCE_RECOVERY")
    fragments = proof.pop("private_ordered_writer_java_fragments")
    sites = proof.pop("private_original_writer_source_sites")
    raw = json.dumps(sites,sort_keys=True,indent=2)+"\n"
    result = {
        "schema_version":1,"kind":"original_private_v309_364_op_writer_source",
        "complete_original_jar_sha256":original_sha256.lower(),
        "private_source_sha256":hashlib.sha256(fragments.encode()).hexdigest(),
        "private_site_evidence_sha256":hashlib.sha256(raw.encode()).hexdigest(),
        "research_only":True,**proof,
    }
    output.mkdir(parents=True,exist_ok=False)
    for file,content in (
        ("writer-sites.private.json",raw),
        ("writer-source.private.java.txt",fragments),
        ("writer-source.aggregate.json",json.dumps(result,sort_keys=True,indent=2)+"\n"),
    ):
        with (output/file).open("x",encoding="utf-8",newline="\n") as fd:
            fd.write(content)
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar",type=Path)
    p.add_argument("private_class_entry")
    p.add_argument("private_method")
    p.add_argument("descriptor")
    p.add_argument("new_private_output",type=Path)
    p.add_argument("--original-sha256",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(replay_private_save_writer(
            a.original_jar,a.private_class_entry,a.private_method,
            a.descriptor,a.new_private_output,original_sha256=a.original_sha256),
            sort_keys=True))
    except SaveWriterSourceError as exc:
        p.error(str(exc))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
