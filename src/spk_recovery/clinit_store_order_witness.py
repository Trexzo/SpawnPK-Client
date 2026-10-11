"""R56: fail-closed v309 complete <clinit> owner-write order witness.

This is an acceptance gate for a *private* recompiled candidate. It proves
only mapped field-write order plus opcode/branch-topology shape; it cannot
prove matching constant-pool operands, helper side effects or runtime parity.
No original obfuscated names or source are emitted in aggregate reports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, BadZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _clinit, _digest, _fields, _instructions,
)


class ClinitOrderWitnessError(ValueError):
    """A pinned JVM initializer order/source-shape witness was rejected."""


_PIN = re.compile(r"[a-f0-9]{64}\Z", re.I)


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise ClinitOrderWitnessError(reason)


def _key(row: dict) -> tuple[str, str]:
    n, d = row.get("name"), row.get("descriptor")
    _need(type(n) is str and bool(n) and type(d) is str and bool(d),
          "INVALID_ORIGINAL_OR_CANDIDATE_FIELD")
    return n, d


def _stores(class_profile: dict) -> tuple[list[tuple[str, str]], list[dict], dict]:
    owner = class_profile.get("internal_name")
    _need(type(owner) is str and bool(owner), "OWNER_NOT_RESOLVED")
    fields = _fields(class_profile)
    init = _clinit(class_profile, required=True)
    rows = _instructions(init)
    _need(rows, "EMPTY_CLASS_INITIALIZER")
    writes: list[tuple[str, str]] = []
    for r in rows:
        if r.get("opcode") != "0xb3":
            continue
        _need(r.get("owner") == owner,
              "CROSS_OWNER_STATIC_WRITE_UNSUPPORTED")
        field = _key(r)
        _need(field in fields, "PUTSTATIC_TARGET_NOT_DECLARED_IN_OWNER")
        writes.append(field)
    _need(writes, "NO_OWNER_CLASS_INITIALIZER_WRITES")
    return writes, rows, fields


def _shape(rows: list[dict]) -> tuple:
    offsets = {}
    for index, row in enumerate(rows):
        offset = row.get("offset")
        opcode = row.get("opcode")
        _need(type(offset) is int and type(opcode) is str
              and offset not in offsets, "INVALID_INSTRUCTION_ROW")
        offsets[offset] = index
    operations = []
    branches = []
    for index, row in enumerate(rows):
        operations.append(row["opcode"])
        if "branch_target_offset" in row:
            t = row["branch_target_offset"]
            _need(type(t) is int and t in offsets,
                  "INVALID_BRANCH_TARGET")
            branches.append((index, offsets[t]))
    return tuple(operations), tuple(branches)


def verify_ordered_owner_stores(
    original: dict, candidate: dict, alias_rows: list[dict],
) -> dict:
    """Use *explicit private alias rows*, never inferred field identity."""
    a_writes, a_rows, a_fields = _stores(original)
    b_writes, b_rows, b_fields = _stores(candidate)
    _need(isinstance(alias_rows, list) and bool(alias_rows),
          "PRIVATE_ALIAS_MAP_REQUIRED")
    aliases: dict[tuple[str, str], tuple[str, str]] = {}
    inverse = set()
    for alias in alias_rows:
        _need(isinstance(alias, dict)
              and isinstance(alias.get("original"), dict)
              and isinstance(alias.get("candidate"), dict),
              "INVALID_EXPLICIT_ALIAS_ROW")
        a, b = _key(alias["original"]), _key(alias["candidate"])
        _need(a in a_fields and b in b_fields,
              "ALIAS_FIELD_DECLARATION_MISMATCH")
        _need(a not in aliases and b not in inverse,
              "DUPLICATED_PRIVATE_FIELD_ALIAS")
        aliases[a] = b
        inverse.add(b)
    _need(set(aliases) == set(a_writes)
          and inverse == set(b_writes),
          "ALIAS_DOES_NOT_COVER_EXACT_STORED_FIELDS")
    _need(len(a_writes) == len(b_writes),
          "ORIGINAL_CANDIDATE_WRITE_COUNT_MISMATCH")
    _need([aliases[x] for x in a_writes] == b_writes,
          "ORIGINAL_CANDIDATE_STORE_ORDER_MISMATCH")
    a_ops, a_edges = _shape(a_rows)
    b_ops, b_edges = _shape(b_rows)
    _need(a_ops == b_ops,
          "ORIGINAL_CANDIDATE_OPCODE_SEQUENCE_MISMATCH")
    _need(a_edges == b_edges,
          "ORIGINAL_CANDIDATE_BRANCH_TOPOLOGY_MISMATCH")
    return {
        "owner_static_field_writes": len(a_writes),
        "unique_static_field_targets_written": len(set(a_writes)),
        "original_clinit_instruction_count": len(a_rows),
        "candidate_clinit_instruction_count": len(b_rows),
        "normalized_explicit_control_flow_edges": len(a_edges),
        "explicit_mapping_covers_all_original_and_candidate_stores": True,
        "exact_mapped_static_store_order": True,
        "exact_jvm_opcode_sequence_shape": True,
        "exact_branch_target_instruction_ordinals": True,
        "constant_pool_operand_semantics_equivalent": False,
        "nested_enum_source_or_helper_method_parity_certified": False,
        "all_original_initializer_side_effects_reproduced": False,
        "original_java_source_equivalence_certified": False,
        "runtime_equivalence_certified": False,
        "canonical_class_or_field_aliases_accepted": False,
    }


def _verified_class(path: Path, class_entry: str, pin: str) -> dict:
    _need(type(pin) is str and _PIN.fullmatch(pin) is not None,
          "INVALID_COMPLETE_JAR_SHA256_PIN")
    _need(path.is_file() and not path.is_symlink(),
          "JAR_MISSING_OR_SYMLINK")
    _need(_digest(path) == pin.lower(),
          "COMPLETE_JAR_SHA256_MISMATCH")
    _need(type(class_entry) is str
          and class_entry.endswith(".class")
          and not class_entry.startswith("/") and "\\" not in class_entry
          and all(p not in ("", ".", "..") and ":" not in p
                  for p in class_entry.split("/")),
          "INVALID_CLASS_ENTRY")
    with ZipFile(path) as jar:
        _need(jar.namelist().count(class_entry) == 1,
              "CLASSFILE_MISSING_OR_DUPLICATE")
        result = profile_jar_class(path, class_entry)
    _need(_digest(path) == pin.lower(), "JAR_CHANGED_DURING_REPLAY")
    return result


def prove_private_clinit_order(
    original_jar: Path, original_entry: str,
    candidate_jar: Path, candidate_entry: str,
    private_alias_json: Path, output_directory: Path, *,
    original_sha256: str, candidate_sha256: str,
) -> dict:
    a, b, aliasfile, out = (
        Path(original_jar), Path(candidate_jar),
        Path(private_alias_json), Path(output_directory),
    )
    _need(not out.exists() and not out.is_symlink(),
          "OUTPUT_ALREADY_EXISTS")
    _need(aliasfile.is_file() and not aliasfile.is_symlink(),
          "PRIVATE_ALIAS_FILE_MISSING_OR_SYMLINK")
    _need(aliasfile.stat().st_size <= 131072,
          "PRIVATE_ALIAS_MAP_TOO_LARGE")
    try:
        original = _verified_class(a, original_entry, original_sha256)
        candidate = _verified_class(b, candidate_entry, candidate_sha256)
        aliases = json.loads(aliasfile.read_text(encoding="utf-8"))
        _need(type(aliases) is dict and aliases.get("schema_version") == 1,
              "UNSUPPORTED_PRIVATE_ALIAS_SCHEMA")
        report = verify_ordered_owner_stores(
            original, candidate, aliases.get("aliases")
        )
    except (OSError, ValueError, BadZipFile, BytecodeProfileError,
            ScalarInitializerRecoveryError, KeyError, IndexError) as exc:
        if isinstance(exc, ClinitOrderWitnessError):
            raise
        raise ClinitOrderWitnessError(
            "PRIVATE_CLINIT_INPUT_NOT_VERIFIABLE"
        ) from None
    _need(_digest(a) == original_sha256.lower()
          and _digest(b) == candidate_sha256.lower(),
          "INPUT_JAR_CHANGED_DURING_REPLAY")
    result = {
        "schema_version": 1,
        "kind": "private_original_candidate_clinit_store_order_and_shape_witness",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "candidate_complete_jar_sha256": candidate_sha256.lower(),
        **report,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "clinit-order.aggregate.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
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
    args = p.parse_args(argv)
    try:
        print(json.dumps(prove_private_clinit_order(
            args.original_jar, args.original_class_entry,
            args.candidate_jar, args.candidate_class_entry,
            args.private_alias_json, args.output_directory,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
        ), sort_keys=True))
    except ClinitOrderWitnessError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
