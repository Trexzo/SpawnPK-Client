"""R63: recover typed private value-producer chains for original static writes.

Recognize six adjacent JVM instructions:
  aload_1, ldc String, invokevirtual(String)->ref,
  invokestatic(ref)->ref, invokevirtual()->Z/I, putstatic Z/I.
Original member signatures/CP strings and field coordinates remain PRIVATE.
This is a typed JVM operand graph, not Java source or proven local-variable
semantics. Exception table and unexpected branch-entry vetoes remain active.
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
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)

class TypedWriteChainError(ValueError):
    """Original static-write dataflow form is not fully proven."""

_SHA = re.compile(r"[a-fA-F0-9]{64}\Z")
_REF = re.compile(r"L[^;]+;")
_PATTERN = ("0x2b", "0x12", "0xb6", "0xb8", "0xb6", "0xb3")


def _need(cond: bool, reason: str) -> None:
    if not cond:
        raise TypedWriteChainError(reason)


def _descriptor_parts(desc: str) -> tuple[str, str] | None:
    if type(desc) is not str or not desc.startswith("(") or ")" not in desc:
        return None
    params, result = desc[1:].split(")", 1)
    return params, result


def plan_original_typed_write_chains(profile: dict, method_name: str,
                                     method_descriptor: str) -> dict:
    owner = profile.get("internal_name")
    _need(type(owner) is str and owner, "ORIGINAL_OWNER_NOT_RESOLVED")
    methods = profile.get("methods")
    _need(isinstance(methods, list), "METHOD_INVENTORY_MISSING")
    selected = [
        m for m in methods
        if m.get("name") == method_name
        and m.get("descriptor") == method_descriptor
    ]
    _need(len(selected) == 1, "ORIGINAL_PRIVATE_METHOD_IDENTITY_NOT_UNIQUE")
    method = selected[0]
    rows = _instructions(method)
    _need(rows and rows[0]["offset"] == 0
          and all(a["offset"] + a["length"] == b["offset"]
                  for a, b in zip(rows, rows[1:])),
          "ORIGINAL_METHOD_INSTRUCTIONS_NOT_CONTIGUOUS")
    try:
        edges = _edges(rows)
    except BooleanJoinWitnessError:
        raise TypedWriteChainError("INVALID_ORIGINAL_BRANCH_TARGET") from None
    incoming = {target for _, target in edges}
    handlers = method.get("exception_handlers")
    _need(isinstance(handlers, list), "EXCEPTION_TABLE_MISSING")
    fields = _fields(profile)
    raw = 0
    descriptor_matched = 0
    vetoed = 0
    accepted = []
    for i, store in enumerate(rows):
        if store.get("opcode") != "0xb3" or i < 5:
            continue
        window = rows[i-5:i+1]
        if tuple(row.get("opcode") for row in window) != _PATTERN:
            continue
        raw += 1
        load, string, lookup, convert, extract, target = window
        if (string.get("constant_pool_tag") != 8
                or type(string.get("constant")) is not str
                or target.get("owner") != owner
                or target.get("descriptor") not in ("Z", "I")
                or (target.get("name"), target.get("descriptor"))
                not in fields):
            vetoed += 1
            continue
        original_field = fields[(target["name"], target["descriptor"])]
        if not original_field["access"] & 0x0008:
            vetoed += 1
            continue
        lookup_type = _descriptor_parts(lookup.get("descriptor"))
        convert_type = _descriptor_parts(convert.get("descriptor"))
        extract_type = _descriptor_parts(extract.get("descriptor"))
        if (lookup_type is None or convert_type is None
                or extract_type is None):
            vetoed += 1
            continue
        lookup_arg, lookup_result = lookup_type
        convert_arg, convert_result = convert_type
        extract_arg, extract_result = extract_type
        if not (
            lookup_arg == "Ljava/lang/String;"
            and _REF.fullmatch(lookup_result)
            and convert_arg == lookup_result
            and _REF.fullmatch(convert_result)
            and extract_arg == ""
            and extract_result == target["descriptor"]
            and extract.get("owner") == convert_result[1:-1]
            and all(type(row.get("owner")) is str
                    and type(row.get("name")) is str
                    for row in (lookup, convert, extract))
        ):
            vetoed += 1
            continue
        descriptor_matched += 1
        offsets = [row["offset"] for row in window]
        if (any(off in incoming for off in offsets[1:])
                or any(h.get("handler_pc") in offsets[1:]
                       for h in handlers)):
            vetoed += 1
            continue
        _need(all(a["offset"] + a["length"] == b["offset"]
                  for a, b in zip(window, window[1:])),
              "ORIGINAL_WRITE_CHAIN_HAS_BYTECODE_GAPS")
        accepted.append({
            "first_offset": load["offset"],
            "target_offset": target["offset"],
            "original_private_literal": string["constant"],
            "original_private_target_field": {
                "owner": target["owner"], "name": target["name"],
                "descriptor": target["descriptor"],
            },
            "lookup_call": {
                "owner": lookup["owner"], "name": lookup["name"],
                "descriptor": lookup["descriptor"],
            },
            "conversion_call": {
                "owner": convert["owner"], "name": convert["name"],
                "descriptor": convert["descriptor"],
            },
            "primitive_extraction_call": {
                "owner": extract["owner"], "name": extract["name"],
                "descriptor": extract["descriptor"],
            },
        })
    return {
        "private_typed_chains": accepted,
        "original_raw_six_opcode_chain_sites": raw,
        "original_exact_descriptor_compatible_sites": descriptor_matched,
        "original_accepted_no_incoming_edge_sites": len(accepted),
        "sites_vetoed_due_to_metadata_or_cfg": vetoed,
        "original_boolean_target_chains": sum(
            x["original_private_target_field"]["descriptor"] == "Z"
            for x in accepted
        ),
        "original_int_target_chains": sum(
            x["original_private_target_field"]["descriptor"] == "I"
            for x in accepted
        ),
        "original_local_slot_one_declared_java_type_recovered": False,
        "original_source_expression_and_try_catch_recovered": False,
        "original_helper_implementations_or_side_effects_proven": False,
        "original_method_runtime_equivalent": False,
        "canonical_field_and_method_aliases_accepted": False,
    }


def private_typed_write_chain_replay(original_jar: Path,
                                     class_entry: str, method_name: str,
                                     method_descriptor: str, output_root: Path,
                                     *, original_sha256: str) -> dict:
    jar, out = Path(original_jar), Path(output_root)
    _need(not out.exists() and not out.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    _need(type(original_sha256) is str
          and _SHA.fullmatch(original_sha256) is not None,
          "INVALID_WHOLE_ORIGINAL_SHA256")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar) == original_sha256.lower(),
          "ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(class_entry) is str and class_entry.endswith(".class")
          and not class_entry.startswith("/") and "\\" not in class_entry
          and all(p not in ("", ".", "..") and ":" not in p
                  for p in class_entry.split("/")),
          "INVALID_PRIVATE_CLASS_ENTRY")
    try:
        with ZipFile(jar) as z:
            _need(z.namelist().count(class_entry) == 1,
                  "PRIVATE_ORIGINAL_CLASS_ENTRY_MISSING_OR_DUPLICATE")
            original = profile_jar_class(jar, class_entry)
        plan = plan_original_typed_write_chains(
            original, method_name, method_descriptor
        )
    except (BadZipFile, BytecodeProfileError, ScalarInitializerRecoveryError,
            OSError, KeyError, TypeError, IndexError):
        raise TypedWriteChainError(
            "ORIGINAL_TYPED_WRITE_CHAIN_EVIDENCE_UNVERIFIABLE"
        ) from None
    _need(_digest(jar) == original_sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_PROOF")
    private = plan.pop("private_typed_chains")
    _need(bool(private), "NO_EXACT_TYPED_STATIC_WRITE_CHAINS_RECOVERED")
    raw = json.dumps(private, indent=2, sort_keys=True) + "\n"
    report = {
        "schema_version": 1,
        "kind": "private_original_typed_jvm_write_chain_source_forms",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "private_typed_chain_data_sha256":
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        **plan,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "typed-write-chains.private.json").open(
            "x", encoding="utf-8", newline="\n") as fd:
        fd.write(raw)
    with (out / "typed-write-chains.aggregate.json").open(
            "x", encoding="utf-8", newline="\n") as fd:
        json.dump(report, fd, sort_keys=True, indent=2)
        fd.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("private_class_entry")
    p.add_argument("private_method_name")
    p.add_argument("private_method_descriptor")
    p.add_argument("new_private_output", type=Path)
    p.add_argument("--original-sha256", required=True)
    args = p.parse_args(argv)
    try:
        print(json.dumps(private_typed_write_chain_replay(
            args.original_jar, args.private_class_entry,
            args.private_method_name, args.private_method_descriptor,
            args.new_private_output, original_sha256=args.original_sha256,
        ), sort_keys=True))
    except TypedWriteChainError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
