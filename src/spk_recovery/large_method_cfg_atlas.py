"""R62: private, exact JVM control-flow/source-evidence atlas for large methods.

Extract every original branch edge, exception-handler region, and static field
write from a SHA-256-pinned original class. Build a private basic-block atlas
for method source recovery; deliberately DO NOT guess Java try/catch, boolean
predicates, default values, static field aliases, or method/runtime semantics.
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


class LargeMethodCfgError(ValueError):
    """Pinned original JVM method control-flow evidence is not trustworthy."""


_SHA = re.compile(r"[0-9a-fA-F]{64}\Z")


def _need(value: bool, reason: str) -> None:
    if not value:
        raise LargeMethodCfgError(reason)


def plan_private_original_cfg(profile: dict, method_name: str,
                              descriptor: str) -> dict:
    owner = profile.get("internal_name")
    _need(type(owner) is str and bool(owner), "ORIGINAL_CLASS_OWNER_UNKNOWN")
    _need(type(method_name) is str and method_name
          and type(descriptor) is str and descriptor, "INVALID_PRIVATE_METHOD")
    methods = profile.get("methods")
    _need(isinstance(methods, list), "ORIGINAL_METHODS_UNAVAILABLE")
    selected = [m for m in methods
                if m.get("name") == method_name
                and m.get("descriptor") == descriptor]
    _need(len(selected) == 1, "PRIVATE_METHOD_EXACT_JVM_IDENTITY_NOT_UNIQUE")
    method = selected[0]
    rows = _instructions(method)
    _need(bool(rows), "ORIGINAL_METHOD_HAS_NO_INSTRUCTIONS")
    code_length = method.get("code_length")
    _need(type(code_length) is int and code_length > 0,
          "METHOD_CODE_LENGTH_UNAVAILABLE")
    _need(rows[0]["offset"] == 0
          and all(x["offset"] + x["length"] == y["offset"]
                  for x, y in zip(rows, rows[1:]))
          and rows[-1]["offset"] + rows[-1]["length"] == code_length,
          "ORIGINAL_JVM_METHOD_HAS_GAPS_OR_UNACCOUNTED_BYTES")
    positions = {row["offset"]: i for i, row in enumerate(rows)}
    try:
        explicit = _edges(rows)
    except BooleanJoinWitnessError:
        raise LargeMethodCfgError("INVALID_ORIGINAL_BRANCH_TARGET") from None

    handlers = method.get("exception_handlers")
    _need(isinstance(handlers, list), "ORIGINAL_EXCEPTION_TABLE_UNAVAILABLE")
    checked_handlers = []
    for h in handlers:
        _need(isinstance(h, dict)
              and all(type(h.get(k)) is int for k in
                      ("start_pc", "end_pc", "handler_pc")),
              "INVALID_EXCEPTION_TABLE_ENTRY")
        start, end, target = h["start_pc"], h["end_pc"], h["handler_pc"]
        _need(start in positions and (end in positions or end == code_length)
              and target in positions and 0 <= start < end <= code_length,
              "EXCEPTION_HANDLER_NOT_AT_JVM_BOUNDARY")
        checked_handlers.append(h)

    declarations = _fields(profile)
    writes = []
    for index, row in enumerate(rows):
        if row.get("opcode") != "0xb3":
            continue
        target_owner, name, desc = (
            row.get("owner"), row.get("name"), row.get("descriptor")
        )
        _need(all(type(x) is str and x for x in
                  (target_owner, name, desc)),
              "UNRESOLVED_STATIC_WRITE_OPERAND")
        if target_owner == owner:
            _need((name, desc) in declarations
                  and declarations[(name, desc)]["access"] & 0x0008,
                  "STATIC_WRITE_TO_NONDECLARED_OR_NONSTATIC_OWNER_FIELD")
        writes.append({
            "ordinal": index,
            "offset": row["offset"],
            "owner": target_owner,
            "name": name,
            "descriptor": desc,
            "within_exception_handlers": [
                n for n, h in enumerate(checked_handlers)
                if h["start_pc"] <= row["offset"] < h["end_pc"]
            ],
            "prior_opcode_window": [
                r["opcode"] for r in rows[max(0, index - 10):index]
            ],
        })

    leaders = {0}
    for a, b in explicit:
        leaders.add(b)
        next_index = positions[a] + 1
        if next_index < len(rows):
            leaders.add(rows[next_index]["offset"])
    for h in checked_handlers:
        leaders.update([h["start_pc"], h["handler_pc"]])
        if h["end_pc"] != code_length:
            leaders.add(h["end_pc"])
    starts = sorted(leaders)
    _need(all(x in positions for x in starts),
          "INVALID_BASIC_BLOCK_LEADER")
    blocks = []
    for i, start in enumerate(starts):
        end = starts[i+1] if i+1 < len(starts) else code_length
        region = rows[positions[start]:positions[end]
                      if end in positions else len(rows)]
        _need(bool(region) and region[0]["offset"] == start
              and region[-1]["offset"] + region[-1]["length"] == end,
              "BAD_BASIC_BLOCK_PARTITION")
        tail = region[-1]
        dests = [b for a, b in explicit if a == tail["offset"]]
        if not dests and (tail["opcode"] not in (
                "0xac", "0xad", "0xae", "0xaf", "0xb0", "0xb1", "0xbf")
                and i+1 < len(starts)):
            dests = [starts[i+1]]
        elif dests and (tail.get("opcode") not in
                         ("0xa7", "0xc8", "0xaa", "0xab")
                         and i+1 < len(starts)):
            dests.append(starts[i+1])
        dests = sorted(set(dests))
        _need(all(x in leaders for x in dests),
              "BASIC_BLOCK_JUMP_OUTSIDE_LEADERS")
        blocks.append({
            "start": start, "end": end, "first_instruction_ordinal":
                positions[start], "instruction_count": len(region),
            "last_opcode": tail["opcode"], "successors": dests,
            "exception_handlers_covering": [
                j for j, h in enumerate(checked_handlers)
                if h["start_pc"] < end and h["end_pc"] > start
            ],
        })
    _need(sum(b["instruction_count"] for b in blocks) == len(rows),
          "INCOMPLETE_ORIGINAL_JVM_BASIC_BLOCK_COVERAGE")

    atlas = {
        "private_owner": owner,
        "private_method_name": method_name,
        "private_method_descriptor": descriptor,
        "code_length": code_length,
        "instruction_opcodes": [r["opcode"] for r in rows],
        "explicit_control_flow_edges": explicit,
        "exception_table": checked_handlers,
        "basic_blocks": blocks,
        "static_field_writes": writes,
    }
    return {
        "private_cfg_atlas": atlas,
        "original_jvm_instruction_count": len(rows),
        "original_jvm_code_bytes": code_length,
        "basic_block_count": len(blocks),
        "explicit_branch_edge_count": len(explicit),
        "exception_handler_entries": len(checked_handlers),
        "static_field_writes_total": len(writes),
        "static_field_writes_to_original_owner":
            sum(w["owner"] == owner for w in writes),
        "static_field_writes_to_external_owners":
            sum(w["owner"] != owner for w in writes),
        "writes_under_exception_regions":
            sum(bool(w["within_exception_handlers"]) for w in writes),
        "control_flow_and_exception_ranges_all_accounted_for": True,
        "exact_java_source_or_try_catch_structure_recovered": False,
        "field_write_value_expressions_recovered": False,
        "original_method_side_effects_equivalent": False,
        "runtime_equivalence_certified": False,
        "private_member_names_accepted_as_canonical": False,
    }


def build_private_cfg_atlas(original_jar: Path, class_entry: str,
                            method_name: str, descriptor: str,
                            output_dir: Path, *, sha256: str) -> dict:
    jar, out = Path(original_jar), Path(output_dir)
    _need(not out.exists() and not out.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    _need(type(sha256) is str and _SHA.fullmatch(sha256) is not None,
          "INVALID_COMPLETE_ORIGINAL_JAR_SHA256")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar) == sha256.lower(),
          "ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(class_entry) is str and class_entry.endswith(".class")
          and not class_entry.startswith("/") and "\\" not in class_entry
          and all(x not in ("", ".", "..") and ":" not in x
                  for x in class_entry.split("/")),
          "INVALID_PRIVATE_CLASS_ENTRY")
    try:
        with ZipFile(jar) as zipfile:
            _need(zipfile.namelist().count(class_entry) == 1,
                  "ORIGINAL_CLASSFILE_ENTRY_NOT_UNIQUE")
            original = profile_jar_class(jar, class_entry)
        plan = plan_private_original_cfg(original, method_name, descriptor)
    except (BadZipFile, BytecodeProfileError, BooleanJoinWitnessError,
            ScalarInitializerRecoveryError, OSError, KeyError, IndexError):
        raise LargeMethodCfgError(
            "ORIGINAL_METHOD_CFG_PROFILE_UNVERIFIABLE"
        ) from None
    _need(_digest(jar) == sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_CFG_PROFILE")
    private_atlas = plan.pop("private_cfg_atlas")
    raw = json.dumps(private_atlas, sort_keys=True, indent=2) + "\n"
    report = {
        "schema_version": 1,
        "kind": "exact_original_private_method_basic_block_exception_write_atlas",
        "original_complete_jar_sha256": sha256.lower(),
        "private_cfg_atlas_sha256":
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "research_only": True,
        **plan,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "original-method-cfg.private.json").open(
            "x", encoding="utf-8", newline="\n") as fd:
        fd.write(raw)
    with (out / "original-method-cfg.aggregate.json").open(
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
    p.add_argument("new_private_output_directory", type=Path)
    p.add_argument("--sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(build_private_cfg_atlas(
            a.original_jar, a.private_class_entry, a.private_method_name,
            a.private_method_descriptor, a.new_private_output_directory,
            sha256=a.sha256,
        ), sort_keys=True))
    except LargeMethodCfgError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
