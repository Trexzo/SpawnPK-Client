"""R81: full JVM instruction operand parity after R66 CFG/handler/write parity.

All original/candidate class names, literal values, invokedynamic bootstraps,
field and method aliases remain PRIVATE. A positive structural+operand result
does NOT certify dependent helper bodies, source authorship or runtime parity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from .clinit_store_order_witness import _verified_class
from .large_method_cfg_parity import (
    LargeMethodParityError, compare_large_method_cfg, _select,
)
from .mutable_scalar_initializer_source import _digest


class WholeMethodOperandError(ValueError):
    """Original-versus-recompiled JVM operand equivalence is not verified."""


def need(ok: bool, message: str) -> None:
    if not ok:
        raise WholeMethodOperandError(message)


FIELD_OPS = {"0xb2", "0xb3", "0xb4", "0xb5"}
CALL_OPS = {"0xb6", "0xb7", "0xb8", "0xb9"}
WIDTH_OPS = {"0x12", "0x13"}
# Every parsed semantic operand currently emitted by bytecode_profile.
PARAMS = {
    "constant_pool_tag", "constant_raw_bits", "constant", "int_constant",
    "local_index", "increment", "wide_opcode", "wide_mnemonic",
    "member_constant_pool_tag", "owner", "name", "descriptor",
    "invokeinterface_count", "invokeinterface_reserved",
    "invokedynamic_reserved", "type", "array_primitive_atype",
    "array_dimensions", "switch_low", "switch_high",
}
META = {
    "offset", "length", "mnemonic", "opcode", "constant_pool_index",
    "bootstrap_method_attr_index", "branch_target_offset",
    "switch_default_target_offset", "switch_targets", "switch_pairs",
}
BOOTSTRAP_META = {"constant_pool_index", "reference_index",
                  "bootstrap_method_ref", "index"}


def aliases_to_map(rows: list, *, original: dict, candidate: dict,
                   role: str) -> dict:
    need(isinstance(rows, list), "PRIVATE_" + role + "_ALIASES_MISSING")
    source_owner = original.get("internal_name")
    target_owner = candidate.get("internal_name")
    need(type(source_owner) is str and type(target_owner) is str,
         "PRIVATE_MEMBER_OWNER_MISSING")
    out, seen = {}, set()
    for row in rows:
        need(isinstance(row, dict) and isinstance(row.get("original"), dict)
             and isinstance(row.get("candidate"), dict),
             "PRIVATE_" + role + "_ALIAS_MALFORMED")
        a = row["original"]
        b = row["candidate"]
        orig = (source_owner, a.get("name"), a.get("descriptor"))
        cand = (target_owner, b.get("name"), b.get("descriptor"))
        need(all(isinstance(v, str) and v for v in orig+cand)
             and orig not in out and cand not in seen
             and orig[2] == cand[2], "PRIVATE_" + role + "_ALIAS_NOT_INJECTIVE")
        out[orig] = cand
        seen.add(cand)
    return out


def canonical_bootstrap(value):
    """Discard CP indices, NEVER referenced method/field identity or raw bits."""
    if isinstance(value, dict):
        return {k: canonical_bootstrap(v) for k, v in sorted(value.items())
                if k not in BOOTSTRAP_META}
    if isinstance(value, (list, tuple)):
        return [canonical_bootstrap(x) for x in value]
    return value


def invokedynamic_site(profile: dict, row: dict):
    bootstraps = profile.get("bootstrap_methods")
    need(isinstance(bootstraps, list), "BOOTSTRAP_TABLE_UNAVAILABLE")
    index = row.get("bootstrap_method_attr_index")
    need(type(index) is int and 0 <= index < len(bootstraps),
         "DYNAMIC_BOOTSTRAP_SITE_INDEX_INVALID")
    return canonical_bootstrap(bootstraps[index])


def semantic_row(profile: dict, row: dict, field_aliases: dict,
                 method_aliases: dict, candidate_owner: str):
    opcode = row.get("opcode")
    need(type(opcode) is str, "JVM_OPCODE_UNRESOLVED")
    need(not (set(row) - PARAMS - META), "UNRECOGNIZED_JVM_OPERAND_MUST_FAIL_CLOSED")
    output = {key: row[key] for key in PARAMS if key in row}
    output["opcode"] = "ldc_any_width" if opcode in WIDTH_OPS else opcode
    if opcode in FIELD_OPS | CALL_OPS:
        triple = (row.get("owner"), row.get("name"), row.get("descriptor"))
        need(all(isinstance(x, str) and x for x in triple),
             "JVM_MEMBER_OPERAND_UNRESOLVED")
        mapped = (field_aliases if opcode in FIELD_OPS else method_aliases).get(triple)
        if mapped is not None:
            triple = mapped
        elif row["owner"] == profile.get("internal_name"):
            # Identity across a renamed class requires an explicit alias.
            need(profile.get("internal_name") == candidate_owner,
                 "PRIVATE_OWNER_MEMBER_ALIAS_REQUIRED")
        output.update(owner=triple[0], name=triple[1], descriptor=triple[2])
    if opcode == "0xba":
        output["bootstrap_semantics"] = invokedynamic_site(profile, row)
    if opcode in {"0xaa", "0xab"}:
        # R66 verifies branch edge topology but does not compare switch keys
        # or ordinal position of each labelled switch branch.
        instructions = _select_switch_rows(profile, row)
        positions = {ins["offset"]: i for i, ins in enumerate(instructions)}
        default = row.get("switch_default_target_offset")
        need(default in positions, "SWITCH_DEFAULT_JVM_TARGET_INVALID")
        output["switch_default_ordinal"] = positions[default]
        if opcode == "0xaa":
            targets = row.get("switch_targets")
            need(isinstance(targets, list) and all(t in positions for t in targets),
                 "TABLESWITCH_TARGETS_UNVERIFIABLE")
            output["switch_target_ordinals"] = [positions[t] for t in targets]
        else:
            pairs = row.get("switch_pairs")
            need(isinstance(pairs, list) and all(
                isinstance(p, (list, tuple)) and len(p)==2
                and p[1] in positions for p in pairs),
                "LOOKUPSWITCH_TARGETS_UNVERIFIABLE")
            output["switch_pair_ordinals"] = [(p[0], positions[p[1]]) for p in pairs]
    return output


def _select_switch_rows(profile: dict, row: dict) -> list:
    # Select exact owning JVM method, never infer another member's offsets.
    candidates = [m.get("instructions", []) for m in profile.get("methods", [])
                  if any(ins is row for ins in m.get("instructions", []))]
    need(len(candidates) == 1, "SWITCH_INSTRUCTION_OWNER_UNIQUE_REQUIRED")
    return candidates[0]


def compare_all_method_operands(
    original: dict, original_method: str, original_descriptor: str,
    candidate: dict, candidate_method: str, candidate_descriptor: str,
    field_write_aliases: list[dict], read_only_field_aliases: list[dict],
    method_aliases: list[dict],
) -> dict:
    # R66 must pass FIRST, so no partial operand match hides control-flow drift.
    try:
        structure = compare_large_method_cfg(
            original, original_method, original_descriptor,
            candidate, candidate_method, candidate_descriptor,
            field_write_aliases,
        )
    except LargeMethodParityError as exc:
        raise WholeMethodOperandError("R66_WHOLE_METHOD_STRUCTURAL_PARITY_FAILED: " + str(exc)) from exc
    _, left = _select(original, original_method, original_descriptor)
    _, right = _select(candidate, candidate_method, candidate_descriptor)
    field_map = aliases_to_map(field_write_aliases, original=original,
                               candidate=candidate, role="WRITE_FIELD")
    extra = aliases_to_map(read_only_field_aliases, original=original,
                           candidate=candidate, role="READ_FIELD")
    need(not (set(field_map) & set(extra))
         and not (set(field_map.values()) & set(extra.values())),
         "OVERLAPPING_PRIVATE_FIELD_ALIAS_FAMILIES")
    field_map.update(extra)
    method_map = aliases_to_map(method_aliases, original=original,
                                candidate=candidate, role="METHOD")
    # The mapped original and the unmodified compiled candidate are compared
    # at each instruction position. Field/member CP indices are meaningless.
    for index, (a, b) in enumerate(zip(left, right)):
        source = semantic_row(original, a, field_map, method_map,
                              candidate["internal_name"])
        target = semantic_row(candidate, b, {}, {},
                              candidate["internal_name"])
        need(source == target,
             "JVM_OPERAND_SEMANTIC_MISMATCH_AT_INSTRUCTION_ORDINAL_" + str(index))
    return {
        "original_instructions_with_all_semantic_operands_compared": len(left),
        "original_ordered_typed_exception_entries": structure["ordered_typed_exception_table_entries"],
        "original_ordered_static_writes": structure["ordered_static_field_writes"],
        "original_explicit_branches": structure["explicit_branch_edges"],
        "original_vs_compiled_CFG_exception_and_write_structure_pass": True,
        "all_parsed_JVM_operands_equal_with_private_aliases": True,
        "original_constants_equal_including_raw_float_bits": True,
        "original_invokedynamic_bootstrap_semantics_equal": True,
        "original_local_slot_operands_equal": True,
        "all_original_helper_method_bodies_equivalent": False,
        "original_authorial_source_equivalent": False,
        "runtime_equivalence_certified": False,
    }


def replay_private_method_operand_parity(
    original_jar: Path, original_entry: str, original_method: str,
    original_descriptor: str, candidate_jar: Path, candidate_entry: str,
    candidate_method: str, candidate_descriptor: str,
    alias_json: Path, output: Path, *, original_sha256: str,
    candidate_sha256: str,
):
    original_jar, candidate_jar, alias_json, output = (
        Path(original_jar), Path(candidate_jar), Path(alias_json), Path(output))
    need(not output.exists() and not output.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    need(alias_json.is_file() and not alias_json.is_symlink()
         and alias_json.stat().st_size <= 1024*1024, "PRIVATE_ALIAS_FILE_UNAVAILABLE")
    try:
        original = _verified_class(original_jar, original_entry, original_sha256)
        candidate = _verified_class(candidate_jar, candidate_entry, candidate_sha256)
        aliases = json.loads(alias_json.read_text(encoding="utf-8"))
        need(isinstance(aliases, dict) and aliases.get("schema_version") == 1,
             "PRIVATE_ALIAS_SCHEMA_INVALID")
        result = compare_all_method_operands(
            original, original_method, original_descriptor,
            candidate, candidate_method, candidate_descriptor,
            aliases.get("aliases"), aliases.get("read_only_field_aliases", []),
            aliases.get("method_aliases", []))
    except (ValueError, KeyError, OSError, TypeError, IndexError) as exc:
        if isinstance(exc, WholeMethodOperandError):
            raise
        raise WholeMethodOperandError("PRIVATE_WHOLE_METHOD_OPERAND_INPUT_INVALID") from exc
    need(_digest(original_jar) == original_sha256.lower()
         and _digest(candidate_jar) == candidate_sha256.lower(),
         "PINNED_JARS_CHANGED_DURING_OPERAND_PROOF")
    result = {
        "schema_version": 1,
        "kind": "private_original_recompiled_complete_method_semantic_operand_parity",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "candidate_complete_jar_sha256": candidate_sha256.lower(),
        **result,
    }
    output.mkdir(parents=True, exist_ok=False)
    with (output / "operand-parity.aggregate.json").open(
            "x", encoding="utf-8", newline="\n") as file:
        json.dump(result, file, indent=2, sort_keys=True)
        file.write("\n")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for label in ("original_jar", "original_entry", "original_method",
                  "original_descriptor", "candidate_jar", "candidate_entry",
                  "candidate_method", "candidate_descriptor", "private_alias_json",
                  "new_private_output"):
        p.add_argument(label)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    a = p.parse_args(argv)
    try:
        result = replay_private_method_operand_parity(
            Path(a.original_jar), a.original_entry, a.original_method,
            a.original_descriptor, Path(a.candidate_jar), a.candidate_entry,
            a.candidate_method, a.candidate_descriptor, Path(a.private_alias_json),
            Path(a.new_private_output), original_sha256=a.original_sha256,
            candidate_sha256=a.candidate_sha256)
        print(json.dumps(result, sort_keys=True))
    except WholeMethodOperandError as exc:
        p.error(str(exc))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
