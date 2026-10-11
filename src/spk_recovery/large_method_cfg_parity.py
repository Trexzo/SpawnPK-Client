"""R66: strict original-vs-recompiled method CFG and exception-table gate.

For one private exact original JVM method and separately compiled candidate:
compare complete instruction-ordinal opcode shape, all branch edges, the
ORDERED typed catch-handler table with matching region boundaries, and
explicitly aliased owner static-field write order. LDC width may differ,
but literal/constant-pool *values* are NOT compared here: those remain
a separate mandatory operand-parity gate. Source/runtime parity is FALSE.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .boolean_join_witness import BooleanJoinWitnessError, _edges
from .clinit_store_order_witness import (
    ClinitOrderWitnessError, _verified_class,
)
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)


class LargeMethodParityError(ValueError):
    """Original/candidate JVM CFG or exception/write structure diverges."""


_WIDTH = {"0x12", "0x13"}


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise LargeMethodParityError(reason)


def _select(profile: dict, name: str, desc: str) -> tuple[dict, list[dict]]:
    methods = profile.get("methods")
    _need(isinstance(methods, list) and bool(methods),
          "JVM_METHOD_INVENTORY_UNAVAILABLE")
    matches = [m for m in methods
               if m.get("name") == name and m.get("descriptor") == desc]
    _need(len(matches) == 1, "SELECTED_METHOD_JVM_IDENTITY_NOT_UNIQUE")
    method = matches[0]
    rows = _instructions(method)
    size = method.get("code_length")
    _need(type(size) is int and size > 0 and rows
          and rows[0]["offset"] == 0
          and rows[-1]["offset"] + rows[-1]["length"] == size
          and all(a["offset"] + a["length"] == b["offset"]
                  for a, b in zip(rows, rows[1:])),
          "METHOD_BYTECODE_NOT_CONTIGUOUS_OR_COMPLETE")
    return method, rows


def _handler_ordinals(method: dict, rows: list[dict]) -> tuple:
    positions = {r["offset"]: i for i, r in enumerate(rows)}
    _need(len(positions) == len(rows),
          "DUPLICATE_JVM_INSTRUCTION_OFFSET")
    code_length = method["code_length"]
    handlers = method.get("exception_handlers")
    _need(isinstance(handlers, list),
          "JVM_EXCEPTION_TABLE_UNAVAILABLE")
    evidence = []
    for h in handlers:
        _need(isinstance(h, dict)
              and all(type(h.get(x)) is int
                      for x in ("start_pc", "end_pc", "handler_pc")),
              "INVALID_TYPED_EXCEPTION_REGION")
        start, end, target = h["start_pc"], h["end_pc"], h["handler_pc"]
        _need(start in positions and (end in positions or end == code_length)
              and target in positions and 0 <= start < end <= code_length,
              "EXCEPTION_RANGE_NOT_AT_JVM_INSTRUCTION_BOUNDARY")
        catch = h.get("catch_type")
        _need(catch is None or (type(catch) is str and catch),
              "ORIGINAL_EXCEPTION_TYPE_UNRESOLVED")
        evidence.append((positions[start],
                         positions[end] if end != code_length else len(rows),
                         positions[target], catch))
    return tuple(evidence)


def _branch_ordinals(rows: list[dict]) -> tuple:
    positions = {r["offset"]: i for i, r in enumerate(rows)}
    try:
        edges = _edges(rows)
    except BooleanJoinWitnessError:
        raise LargeMethodParityError(
            "JVM_EXPLICIT_BRANCH_TARGET_NOT_VERIFIABLE"
        ) from None
    _need(all(a in positions and b in positions for a, b in edges),
          "BRANCH_NOT_AT_VERIFIED_INSTRUCTION_BOUNDARY")
    return tuple(sorted((positions[a], positions[b]) for a, b in edges))


def _static_writes(profile: dict, rows: list[dict]) -> list[tuple]:
    owner = profile.get("internal_name")
    _need(type(owner) is str and owner,
          "STATIC_WRITE_OWNER_UNAVAILABLE")
    fields = _fields(profile)
    writes = []
    for row in rows:
        if row.get("opcode") != "0xb3":
            continue
        ref_owner, name, desc = (
            row.get("owner"), row.get("name"), row.get("descriptor")
        )
        _need(all(type(x) is str and x
                  for x in (ref_owner, name, desc)),
              "STATIC_WRITE_REFERENCE_NOT_RESOLVED")
        if ref_owner == owner:
            key = name, desc
            _need(key in fields and fields[key]["access"] & 0x0008,
                  "OWNER_STATIC_WRITE_TARGET_NOT_DECLARED_STATIC")
        writes.append((ref_owner, name, desc))
    return writes


def _private_field_aliases(original: dict, candidate: dict,
                           aliases: list[dict],
                           a_writes: list[tuple],
                           b_writes: list[tuple]) -> dict:
    _need(isinstance(aliases, list),
          "PRIVATE_FIELD_ALIAS_ROWS_REQUIRED")
    original_owner, candidate_owner = (
        original.get("internal_name"), candidate.get("internal_name")
    )
    original_fields, candidate_fields = _fields(original), _fields(candidate)
    originals = {(name, desc) for o, name, desc in a_writes
                 if o == original_owner}
    candidates = {(name, desc) for o, name, desc in b_writes
                  if o == candidate_owner}
    aliases_map = {}
    used = set()
    for alias in aliases:
        _need(isinstance(alias, dict)
              and isinstance(alias.get("original"), dict)
              and isinstance(alias.get("candidate"), dict),
              "PRIVATE_ALIAS_ROW_MALFORMED")
        o, c = alias["original"], alias["candidate"]
        a, b = (o.get("name"), o.get("descriptor")), (
            c.get("name"), c.get("descriptor"))
        _need(all(type(x) is str and x for x in a + b)
              and a in original_fields and b in candidate_fields
              and a[1] == b[1]
              and original_fields[a]["access"] & 0x0008
              and candidate_fields[b]["access"] & 0x0008,
              "ALIAS_ORIGINAL_CANDIDATE_DECLARATION_NOT_PROVED")
        _need(a not in aliases_map and b not in used,
              "PRIVATE_FIELD_ALIASES_NOT_INJECTIVE")
        aliases_map[a] = b
        used.add(b)
    _need(set(aliases_map) == originals and used == candidates,
          "PRIVATE_FIELD_ALIASES_NOT_EXACTLY_COVERING_WRITES")
    return aliases_map


def compare_large_method_cfg(original: dict, original_method: str,
                             original_descriptor: str,
                             candidate: dict, candidate_method: str,
                             candidate_descriptor: str,
                             aliases: list[dict]) -> dict:
    _need(original.get("classfile_major") == candidate.get("classfile_major"),
          "ORIGINAL_CANDIDATE_JVM_MAJOR_VERSION_DIFFERS")
    a, a_rows = _select(original, original_method, original_descriptor)
    b, b_rows = _select(candidate, candidate_method, candidate_descriptor)
    _need(a.get("access") == b.get("access"),
          "ORIGINAL_CANDIDATE_METHOD_ACCESS_DIFFERENT")
    _need(len(a_rows) == len(b_rows),
          "ORIGINAL_CANDIDATE_JVM_INSTRUCTION_COUNT_DIFFERS")
    widths = 0
    for left, right in zip(a_rows, b_rows):
        if left.get("opcode") != right.get("opcode"):
            _need(left.get("opcode") in _WIDTH
                  and right.get("opcode") in _WIDTH,
                  "ORIGINAL_CANDIDATE_JVM_OPCODE_SHAPE_MISMATCH")
            widths += 1
    branches_a = _branch_ordinals(a_rows)
    branches_b = _branch_ordinals(b_rows)
    _need(branches_a == branches_b,
          "ORIGINAL_CANDIDATE_BRANCH_ORDINAL_TOPOLOGY_MISMATCH")
    handlers_a = _handler_ordinals(a, a_rows)
    handlers_b = _handler_ordinals(b, b_rows)
    _need(handlers_a == handlers_b,
          "ORIGINAL_CANDIDATE_TYPED_EXCEPTION_HANDLER_ORDER_OR_RANGE_MISMATCH")
    writes_a = _static_writes(original, a_rows)
    writes_b = _static_writes(candidate, b_rows)
    _need(len(writes_a) == len(writes_b),
          "ORIGINAL_CANDIDATE_STATIC_WRITE_COUNT_DIFFERENT")
    mapped = _private_field_aliases(
        original, candidate, aliases, writes_a, writes_b)
    source_owner, target_owner = (original["internal_name"],
                                   candidate["internal_name"])
    expected_writes = [
        ((target_owner, *mapped[(name, desc)])
         if owner == source_owner else (owner, name, desc))
        for owner, name, desc in writes_a
    ]
    _need(expected_writes == writes_b,
          "ORIGINAL_CANDIDATE_ORDERED_STATIC_FIELD_WRITES_DIFFER")
    return {
        "original_jvm_instructions": len(a_rows),
        "candidate_jvm_instructions": len(b_rows),
        "ordered_static_field_writes": len(writes_a),
        "unique_mapped_original_owner_fields": len(mapped),
        "explicit_branch_edges": len(branches_a),
        "ordered_typed_exception_table_entries": len(handlers_a),
        "exact_exception_type_and_instruction_ordinal_ranges": True,
        "exact_branch_target_instruction_ordinals": True,
        "exact_mapped_static_field_write_order": True,
        "ldc_to_ldc_w_only_opcode_width_changes": widths,
        "all_other_jvm_opcodes_equal": True,
        "complete_invoke_and_field_read_operands_equal": False,
        "ldc_constant_values_equivalent": False,
        "helper_method_bodies_and_side_effects_equivalent": False,
        "original_java_source_equivalence_certified": False,
        "runtime_equivalence_certified": False,
        "canonical_private_field_aliases_accepted": False,
    }


def replay_private_large_method_cfg(original_jar: Path,
                                     original_entry: str,
                                     original_method: str,
                                     original_descriptor: str,
                                     candidate_jar: Path,
                                     candidate_entry: str,
                                     candidate_method: str,
                                     candidate_descriptor: str,
                                     alias_file: Path,
                                     output_directory: Path, *,
                                     original_sha256: str,
                                     candidate_sha256: str) -> dict:
    a, b, alias, out = (Path(original_jar), Path(candidate_jar),
                        Path(alias_file), Path(output_directory))
    _need(not out.exists() and not out.is_symlink(),
          "OUTPUT_ALREADY_EXISTS")
    _need(alias.is_file() and not alias.is_symlink()
          and alias.stat().st_size <= 131072,
          "PRIVATE_FIELD_ALIAS_FILE_MISSING_OR_UNSAFE")
    try:
        source = _verified_class(a, original_entry, original_sha256)
        compiled = _verified_class(b, candidate_entry, candidate_sha256)
        aliases = json.loads(alias.read_text(encoding="utf-8"))
        _need(type(aliases) is dict and aliases.get("schema_version") == 1,
              "UNSUPPORTED_PRIVATE_ALIAS_FILE_SCHEMA")
        result = compare_large_method_cfg(
            source, original_method, original_descriptor,
            compiled, candidate_method, candidate_descriptor,
            aliases.get("aliases"),
        )
    except (OSError, ValueError, KeyError, IndexError,
            ClinitOrderWitnessError, ScalarInitializerRecoveryError) as exc:
        if isinstance(exc, LargeMethodParityError):
            raise
        raise LargeMethodParityError(
            "PRIVATE_METHOD_CFG_PAIR_NOT_VERIFIABLE"
        ) from None
    _need(_digest(a) == original_sha256.lower()
          and _digest(b) == candidate_sha256.lower(),
          "COMPLETE_INPUT_JAR_CHANGED_DURING_PROOF")
    report = {
        "schema_version": 1,
        "kind": "private_original_candidate_exact_method_cfg_handler_write_parity",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "candidate_complete_jar_sha256": candidate_sha256.lower(),
        **result,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "method-cfg-parity.aggregate.json").open(
            "x", encoding="utf-8", newline="\n") as fd:
        json.dump(report, fd, sort_keys=True, indent=2)
        fd.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for parameter in ("original_jar", "original_class_entry",
                      "original_method_name", "original_method_descriptor",
                      "candidate_jar", "candidate_class_entry",
                      "candidate_method_name", "candidate_method_descriptor",
                      "private_alias_json", "new_private_output_directory"):
        if parameter in ("original_jar", "candidate_jar", "private_alias_json",
                         "new_private_output_directory"):
            p.add_argument(parameter, type=Path)
        else:
            p.add_argument(parameter)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    args = p.parse_args(argv)
    try:
        print(json.dumps(replay_private_large_method_cfg(
            args.original_jar, args.original_class_entry,
            args.original_method_name, args.original_method_descriptor,
            args.candidate_jar, args.candidate_class_entry,
            args.candidate_method_name, args.candidate_method_descriptor,
            args.private_alias_json, args.new_private_output_directory,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
        ), sort_keys=True))
    except LargeMethodParityError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
