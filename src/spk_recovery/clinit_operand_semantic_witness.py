"""R58: semantic instruction-operand parity while retaining R56's strict gate.

A read-only original-vs-compiled-Java witness, with *explicit* private field
aliases. Only ldc <-> ldc_w is width-normalized, and ONLY when the JVM
constant-pool kind and actual constant value are exactly equal. All static
field refs, method refs, invokedynamic bootstrap callsites/arguments, branch
ordinal targets, and initializer assignment order must still match.
This does NOT verify method bodies or JVM runtime execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .clinit_store_order_witness import (
    ClinitOrderWitnessError, _verified_class, _stores,
)
from .mutable_scalar_initializer_source import _clinit


class ClinitOperandWitnessError(ValueError):
    """JVM initializer semantic operand comparison failed closed."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise ClinitOperandWitnessError(reason)


_WIDTHS = {"0x12", "0x13"}
_FIELDS = {"0xb2", "0xb3"}
_CALLS = {"0xb8"}
_INDY = "0xba"
_BRANCHES = {"0xa6", "0x9a", "0xa7"}
_SIMPLE = (
    {"0x01", "0xb1"}
    | {f"0x{x:02x}" for x in range(0x02, 0x09)}
)
_INT = {"0x10", "0x11"}
_NEWARRAY = {"0xbc"}
_SUPPORTED = (_WIDTHS | _FIELDS | _CALLS | {_INDY}
              | _BRANCHES | _SIMPLE | _INT | _NEWARRAY)


def _exact_aliases(original: dict, candidate: dict,
                   alias_rows: list[dict], a_writes: list[tuple[str, str]],
                   b_writes: list[tuple[str, str]]) -> dict:
    _require(isinstance(alias_rows, list) and bool(alias_rows),
             "PRIVATE_EXPLICIT_ALIASES_REQUIRED")
    aliases = {}
    mapped = set()
    a_field = {(f["name"], f["descriptor"]) for f in original["fields"]}
    b_field = {(f["name"], f["descriptor"]) for f in candidate["fields"]}
    for row in alias_rows:
        _require(isinstance(row, dict)
                 and isinstance(row.get("original"), dict)
                 and isinstance(row.get("candidate"), dict),
                 "INVALID_PRIVATE_FIELD_ALIAS")
        a, b = row["original"], row["candidate"]
        lhs = (a.get("name"), a.get("descriptor"))
        rhs = (b.get("name"), b.get("descriptor"))
        _require(all(type(x) is str and x for x in lhs + rhs)
                 and lhs in a_field and rhs in b_field,
                 "ALIAS_REFERENCE_NOT_DECLARED")
        _require(lhs not in aliases and rhs not in mapped,
                 "DUPLICATE_OR_NONINJECTIVE_FIELD_ALIAS")
        _require(lhs[1] == rhs[1],
                 "FIELD_ALIAS_JVM_DESCRIPTOR_NOT_IDENTICAL")
        aliases[lhs] = rhs
        mapped.add(rhs)
    _require(set(a_writes) == set(aliases)
             and set(b_writes) == mapped,
             "EXPLICIT_ALIAS_MAP_DOES_NOT_EXACTLY_COVER_STORES")
    _require([aliases[k] for k in a_writes] == b_writes,
             "EXACT_ORIGINAL_FIELD_WRITE_ORDER_DIFFERENT")
    return aliases


def _bootstrap(profile: dict, index: int) -> tuple:
    _require(type(index) is int and index >= 0,
             "INVALID_INVOKEDYNAMIC_BOOTSTRAP_INDEX")
    entries = [b for b in profile.get("bootstrap_methods", [])
               if b.get("index") == index]
    _require(len(entries) == 1, "INVOKEDYNAMIC_BOOTSTRAP_ENTRY_AMBIGUOUS")
    entry = entries[0]
    h = entry.get("bootstrap_method", {})
    _require(isinstance(h, dict), "INVALID_BOOTSTRAP_HANDLE")
    handle = tuple(h.get(k) for k in (
        "reference_kind", "target_kind", "owner", "name", "descriptor"
    ))
    _require(all(v is not None for v in handle),
             "BOOTSTRAP_METHOD_HANDLE_NOT_RESOLVED")
    args = []
    for a in entry.get("arguments", []):
        _require(isinstance(a, dict) and type(a.get("kind")) is str,
                 "INVALID_BOOTSTRAP_ARGUMENT")
        kind = a["kind"]
        if kind == "string":
            _require(type(a.get("value")) is str, "INVALID_RECIPE_LITERAL")
            args.append(("string", a["value"]))
        elif kind == "constant" and a.get("tag") == 3:
            _require(type(a.get("value")) is int,
                     "INVALID_BOOTSTRAP_INTEGER_LITERAL")
            args.append(("constant_int", a["value"]))
        elif kind == "method_type":
            args.append((kind, a.get("descriptor")))
        elif kind == "class":
            args.append((kind, a.get("name")))
        elif kind == "method_handle":
            h2 = a.get("method_handle", {})
            args.append((kind, tuple(h2.get(k) for k in (
                "reference_kind", "target_kind", "owner", "name", "descriptor"
            ))))
        else:
            raise ClinitOperandWitnessError(
                "UNSUPPORTED_BOOTSTRAP_ARGUMENT_KIND_REQUIRES_EXPLICIT_PROOF"
            )
    return handle, tuple(args)


def _branch_shape(rows: list[dict]) -> dict:
    offsets = {r["offset"]: i for i, r in enumerate(rows)}
    _require(len(offsets) == len(rows), "DUPLICATE_JVM_INSTRUCTION_OFFSET")
    result = {}
    for i, row in enumerate(rows):
        if row["opcode"] not in _BRANCHES:
            _require("branch_target_offset" not in row,
                     "UNHANDLED_JVM_BRANCH_OPCODE")
            continue
        target = row.get("branch_target_offset")
        _require(type(target) is int and target in offsets,
                 "BRANCH_TARGET_NOT_EXACT_INSTRUCTION_OFFSET")
        result[i] = offsets[target]
    return result


def _normalized_operand(
    row: dict, profile: dict, original_owner: str,
    candidate_owner: str, aliases: dict, *, is_original: bool,
) -> tuple:
    op = row.get("opcode")
    _require(op in _SUPPORTED, "UNSUPPORTED_CLINIT_OPCODE_FOR_OPERAND_PARITY")
    if op in _WIDTHS:
        tag = row.get("constant_pool_tag")
        _require(tag in (3, 8), "UNPROVEN_LDC_CONSTANT_POOL_KIND")
        value = row.get("constant")
        _require((tag == 3 and type(value) is int)
                 or (tag == 8 and type(value) is str),
                 "LDC_CONSTANT_VALUE_OR_TYPE_MISSING")
        return ("ldc_value", tag, value)
    if op in _FIELDS:
        owner, name, desc = (
            row.get("owner"), row.get("name"), row.get("descriptor")
        )
        _require(all(type(x) is str and x for x in (owner, name, desc)),
                 "FIELD_OPERAND_UNRESOLVED")
        if is_original and owner == original_owner:
            owner = candidate_owner
            name, desc = aliases.get((name, desc), (name, desc))
        return ("field", op, owner, name, desc)
    if op in _CALLS:
        owner, name, desc = (row.get("owner"), row.get("name"),
                             row.get("descriptor"))
        _require(all(type(x) is str and x for x in (owner, name, desc)),
                 "METHOD_OPERAND_UNRESOLVED")
        if is_original and owner == original_owner:
            owner = candidate_owner
        return ("invokestatic", owner, name, desc)
    if op == _INDY:
        _require(row.get("invokedynamic_reserved") == 0,
                 "INVALID_INDY_RESERVED_BYTES")
        _require(type(row.get("name")) is str
                 and type(row.get("descriptor")) is str,
                 "INVOKEDYNAMIC_CALLSITE_NOT_RESOLVED")
        return ("invokedynamic", row["name"], row["descriptor"],
                _bootstrap(profile, row.get("bootstrap_method_attr_index")))
    if op in _INT:
        _require(type(row.get("int_constant")) is int,
                 "INTEGER_OPERAND_NOT_RESOLVED")
        return ("immediate", op, row["int_constant"])
    if op in _NEWARRAY:
        _require(type(row.get("array_primitive_atype")) is int,
                 "NEWARRAY_PRIMITIVE_TYPE_MISSING")
        return ("newarray", row["array_primitive_atype"])
    if op in _BRANCHES:
        return ("branch", op)
    return ("opcode", op)


def compare_clinit_operand_semantics(
    original: dict, candidate: dict, alias_rows: list[dict],
) -> dict[str, Any]:
    a_writes, a_rows, _ = _stores(original)
    b_writes, b_rows, _ = _stores(candidate)
    _require(original.get("classfile_major") == candidate.get("classfile_major"),
             "JVM_CLASSFILE_MAJOR_DIFFERENT")
    _require(len(a_rows) == len(b_rows),
             "COMPLETE_CLINIT_INSTRUCTION_COUNT_DIFFERENT")
    for profile in (original, candidate):
        init = _clinit(profile, required=True)
        _require(isinstance(init.get("exception_handlers"), list)
                 and not init["exception_handlers"],
                 "HANDLER_CONTROL_FLOW_NOT_SUPPORTED")
    aliases = _exact_aliases(original, candidate, alias_rows, a_writes, b_writes)
    branches_a = _branch_shape(a_rows)
    branches_b = _branch_shape(b_rows)
    _require(branches_a == branches_b,
             "BRANCH_TARGET_INSTRUCTION_ORDINALS_DIFFERENT")
    a_owner, b_owner = original["internal_name"], candidate["internal_name"]
    width_changes = 0
    counts = {"static_field_reference": 0, "static_method_reference": 0,
              "indy_bootstrap_recipe": 0, "ldc_literal": 0}
    for left, right in zip(a_rows, b_rows):
        lo, ro = left["opcode"], right["opcode"]
        if lo != ro:
            _require(lo in _WIDTHS and ro in _WIDTHS,
                     "NON_LDC_OPCODE_CHANGE_NOT_SUPPORTED")
            width_changes += 1
        norm_a = _normalized_operand(
            left, original, a_owner, b_owner, aliases, is_original=True
        )
        norm_b = _normalized_operand(
            right, candidate, a_owner, b_owner, aliases, is_original=False
        )
        _require(norm_a == norm_b,
                 "EXACT_JVM_INSTRUCTION_OPERAND_SEMANTICS_MISMATCH")
        if lo in _FIELDS:
            counts["static_field_reference"] += 1
        if lo in _CALLS:
            counts["static_method_reference"] += 1
        if lo == _INDY:
            counts["indy_bootstrap_recipe"] += 1
        if lo in _WIDTHS:
            counts["ldc_literal"] += 1
    return {
        "original_initializer_instructions": len(a_rows),
        "candidate_initializer_instructions": len(b_rows),
        "original_owner_static_writes_in_order": len(a_writes),
        "explicit_private_field_aliases": len(aliases),
        "same_order_all_static_writes": True,
        "equal_ordinal_branch_edges": len(branches_a),
        "identical_normalized_initializer_operand_semantics": True,
        "ldc_to_ldc_w_width_differences_exactly_validated": width_changes,
        "operand_proof_counts": counts,
        "exact_jvm_opcode_sequence_identical": width_changes == 0,
        "strict_r56_original_opcode_gate_certified": width_changes == 0,
        "original_java_authorial_source_equivalence_certified": False,
        "original_nested_enum_classfile_and_method_bodies_equivalent": False,
        "original_helper_side_effects_and_runtime_execution_equivalent": False,
        "canonical_class_field_identities_accepted": False,
    }


def private_clinit_operand_replay(
    original_jar: Path, original_entry: str, candidate_jar: Path,
    candidate_entry: str, alias_file: Path, output_dir: Path, *,
    original_sha256: str, candidate_sha256: str,
) -> dict:
    a, b, alias, out = (Path(original_jar), Path(candidate_jar),
                        Path(alias_file), Path(output_dir))
    _require(not out.exists() and not out.is_symlink(),
             "OUTPUT_ALREADY_EXISTS")
    _require(alias.is_file() and not alias.is_symlink()
             and alias.stat().st_size <= 131072,
             "PRIVATE_ALIAS_FILE_NOT_SAFE")
    try:
        original = _verified_class(a, original_entry, original_sha256)
        candidate = _verified_class(b, candidate_entry, candidate_sha256)
        data = json.loads(alias.read_text(encoding="utf-8"))
        _require(type(data) is dict and data.get("schema_version") == 1,
                 "PRIVATE_ALIAS_SCHEMA_MISMATCH")
        report = compare_clinit_operand_semantics(
            original, candidate, data.get("aliases")
        )
    except (OSError, ValueError, KeyError, IndexError,
            ClinitOrderWitnessError) as exc:
        if isinstance(exc, ClinitOperandWitnessError):
            raise
        raise ClinitOperandWitnessError(
            "PRIVATE_JVM_OPERAND_REPLAY_UNVERIFIABLE"
        ) from None
    from .mutable_scalar_initializer_source import _digest
    _require(_digest(a) == original_sha256.lower()
             and _digest(b) == candidate_sha256.lower(),
             "INPUT_JAR_CHANGED_DURING_REPLAY")
    result = {
        "schema_version": 1,
        "kind": "private_full_clinit_semantically_normalized_operand_witness",
        "original_complete_jar_sha256": original_sha256.lower(),
        "candidate_complete_jar_sha256": candidate_sha256.lower(),
        "research_only": True,
        **report,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "clinit-operand-parity.aggregate.json").open(
            "x", encoding="utf-8", newline="\n") as fd:
        json.dump(result, fd, sort_keys=True, indent=2)
        fd.write("\n")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("original_class_entry")
    p.add_argument("candidate_jar", type=Path)
    p.add_argument("candidate_class_entry")
    p.add_argument("private_alias_json", type=Path)
    p.add_argument("output_directory", type=Path)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(private_clinit_operand_replay(
            a.original_jar, a.original_class_entry,
            a.candidate_jar, a.candidate_class_entry,
            a.private_alias_json, a.output_directory,
            original_sha256=a.original_sha256,
            candidate_sha256=a.candidate_sha256,
        ), sort_keys=True))
    except ClinitOperandWitnessError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
