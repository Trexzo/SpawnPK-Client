"""R65: all remaining original v309 static writes, without invented Java.

Join independently bounded R63 typed-value chains and R64 null-guarded
boolean sites, then classify only exact JVM opcode suffixes of *disjoint*
remaining putstatic operations. The unmatched writes are private JVM
operands, not reconstructed methods or restored exception behavior.
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
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)
from .typed_static_write_chains import (
    TypedWriteChainError, plan_original_typed_write_chains,
)
from .null_guard_boolean_source import (
    NullGuardBooleanSourceError, plan_original_null_guard_boolean_source,
)
from .boolean_join_witness import BooleanJoinWitnessError, _edges


class ResidualWriteAtlasError(ValueError):
    """Original static-write classification is incomplete or ambiguous."""


_PIN = re.compile(r"[a-fA-F0-9]{64}\Z")
_PREFIX = (
    ("boolean_extract_and_notify", ("0x2b", "0x12", "0xb6", "0xb8", "0xb6",
                                     "0x3e", "0x1d", "0xb8", "0x1d", "0xb3")),
    ("nullable_boolean_extra_call", ("0x2b", "0x12", "0xb6", "0xc7",
                                      "0x03", "0xb8", "0x03", "0xb3")),
    ("two_string_key_boolean_conversion", ("0x2b", "0x12", "0x12", "0xb6",
                                            "0xb8", "0xb3")),
    ("nullable_integer_immediate", ("0x2b", "0x12", "0xb6", "0xc7",
                                    "0x10", "0xb3")),
    ("nullable_string_literal", ("0x2b", "0x12", "0xb6", "0xc7",
                                 "0x12", "0xb3")),
    ("string_lookup_and_static_convert", ("0x2b", "0x12", "0xb6", "0xb8",
                                          "0xb3")),
    ("direct_string_lookup", ("0x2b", "0x12", "0xb6", "0xb3")),
    ("indexed_reference_helper", ("0x19", "0xb8", "0xb3")),
    ("direct_boolean_literal", ("0x03", "0xb3")),
    ("direct_null_reference", ("0x01", "0xb3")),
    ("direct_static_reference_copy", ("0xb2", "0xb3")),
)
_EXPECTED_TYPE = {
    "boolean_extract_and_notify": "Z",
    "nullable_boolean_extra_call": "Z",
    "two_string_key_boolean_conversion": "Z",
    "nullable_integer_immediate": "I",
    "nullable_string_literal": "Ljava/lang/String;",
    "string_lookup_and_static_convert": "reference",
    "direct_string_lookup": "Ljava/lang/String;",
    "indexed_reference_helper": "reference",
    "direct_boolean_literal": "Z",
    "direct_null_reference": "reference",
    "direct_static_reference_copy": "reference",
}


def _need(cond: bool, message: str) -> None:
    if not cond:
        raise ResidualWriteAtlasError(message)


def _site_kind(rows: list[dict], index: int, fields: dict,
               owner: str, incoming: set[int],
               handler_entries: set[int]) -> tuple[str, list[dict]]:
    store = rows[index]
    descriptor = store.get("descriptor")
    for kind, pattern in _PREFIX:
        if index + 1 < len(pattern):
            continue
        window = rows[index + 1 - len(pattern):index + 1]
        if tuple(r.get("opcode") for r in window) != pattern:
            continue
        needed_type = _EXPECTED_TYPE[kind]
        if (needed_type == "reference" and not (
                type(descriptor) is str
                and (descriptor.startswith("L") or descriptor.startswith("["))
                ) or needed_type != "reference" and descriptor != needed_type):
            continue
        if any(row.get("offset") in incoming | handler_entries
               for row in window[1:]):
            continue
        if any(a["offset"] + a["length"] != b["offset"]
               for a, b in zip(window, window[1:])):
            continue
        if kind == "direct_static_reference_copy":
            src = window[0]
            if src.get("descriptor") != descriptor:
                continue
            if src.get("owner") == owner and (
                    src.get("name"), descriptor) not in fields:
                continue
        if kind in ("nullable_integer_immediate", "nullable_string_literal",
                    "nullable_boolean_extra_call"):
            branch = next((r for r in window if r.get("opcode") == "0xc7"),
                          None)
            if (branch is None or type(branch.get("branch_target_offset")) is not int
                    or branch["branch_target_offset"] <= store["offset"]):
                continue
        if kind == "nullable_string_literal":
            if window[-2].get("constant_pool_tag") != 8:
                continue
        if kind == "direct_string_lookup":
            if (window[1].get("constant_pool_tag") != 8
                    or window[2].get("descriptor")
                    != "(Ljava/lang/String;)Ljava/lang/String;"):
                continue
        if kind == "direct_boolean_literal" and descriptor != "Z":
            continue
        return kind, window
    return "unsupported_original_write_shape", []


def plan_original_residual_writes(original: dict, private_method_name: str,
                                  private_descriptor: str) -> dict:
    owner = original.get("internal_name")
    _need(type(owner) is str and owner, "ORIGINAL_OWNER_NOT_RESOLVED")
    method = [m for m in original.get("methods", [])
              if m.get("name") == private_method_name
              and m.get("descriptor") == private_descriptor]
    _need(len(method) == 1, "ORIGINAL_PRIVATE_METHOD_IDENTITY_NOT_UNIQUE")
    rows = _instructions(method[0])
    _need(rows and rows[0]["offset"] == 0
          and all(a["offset"] + a["length"] == b["offset"]
                  for a, b in zip(rows, rows[1:])),
          "ORIGINAL_JVM_INSTRUCTION_LAYOUT_HAS_GAPS")
    handlers = method[0].get("exception_handlers")
    _need(isinstance(handlers, list), "ORIGINAL_EXCEPTION_TABLE_MISSING")
    _need(all(type(h.get("handler_pc")) is int for h in handlers),
          "INVALID_EXCEPTION_HANDLER_PC")
    handler_entries = {h["handler_pc"] for h in handlers}
    try:
        incoming = {target for _, target in _edges(rows)}
    except BooleanJoinWitnessError:
        raise ResidualWriteAtlasError(
            "ORIGINAL_EXPLICIT_BRANCH_TARGET_NOT_VALID"
        ) from None
    original_fields = _fields(original)
    stores = []
    for i, row in enumerate(rows):
        if row.get("opcode") != "0xb3":
            continue
        key = row.get("name"), row.get("descriptor")
        _need(row.get("owner") == owner and key in original_fields
              and original_fields[key]["access"] & 0x0008,
              "ORIGINAL_STORE_TARGET_NOT_DECLARED_STATIC_OWNER_FIELD")
        stores.append((i, row))
    _need(bool(stores), "NO_ORIGINAL_STATIC_WRITES_FOUND")
    typed = plan_original_typed_write_chains(
        original, private_method_name, private_descriptor
    )
    guarded = plan_original_null_guard_boolean_source(
        original, private_method_name, private_descriptor
    )
    typed_sites = {
        x["target_offset"] for x in typed["private_typed_chains"]
    }
    guard_sites = {
        x["store_offset"] for x in guarded["private_original_null_guard_sites"]
    }
    _need(len(typed_sites) == len(typed["private_typed_chains"])
          and len(guard_sites)
          == len(guarded["private_original_null_guard_sites"])
          and not (typed_sites & guard_sites),
          "ORIGINAL_TYPED_AND_NULL_WRITE_WINDOWS_OVERLAP")
    all_offsets = {r["offset"] for _, r in stores}
    _need((typed_sites | guard_sites) <= all_offsets,
          "BOUNDED_SOURCE_WINDOW_NOT_AN_ORIGINAL_OWNER_STATIC_WRITE")
    residual = []
    breakdown: dict[str, int] = {}
    for i, row in stores:
        if row["offset"] in (typed_sites | guard_sites):
            continue
        kind, exact_window = _site_kind(
            rows, i, original_fields, owner, incoming, handler_entries
        )
        breakdown[kind] = breakdown.get(kind, 0) + 1
        residual.append({
            "original_target_instruction_offset": row["offset"],
            "original_private_field": {
                "owner": owner, "name": row["name"],
                "descriptor": row["descriptor"],
            },
            "classification": kind,
            "exact_original_instruction_window": exact_window,
            "original_10_preceding_jvm_opcodes": [
                r["opcode"] for r in rows[max(0, i-10):i]
            ],
            "original_exception_region_indices": [
                k for k, h in enumerate(handlers)
                if h.get("start_pc", 0) <= row["offset"]
                < h.get("end_pc", -1)
            ],
        })
    _need(len(stores) == len(typed_sites) + len(guard_sites) + len(residual),
          "ORIGINAL_STATIC_WRITE_PARTITION_INCOMPLETE")
    return {
        "private_residual_sites": residual,
        "original_owner_static_field_writes": len(stores),
        "original_typed_producer_write_sites": len(typed_sites),
        "original_null_guard_boolean_write_sites": len(guard_sites),
        "original_other_write_sites": len(residual),
        "residual_local_jvm_opcode_shape_counts": dict(sorted(breakdown.items())),
        "residual_sites_without_exact_local_opcode_shape":
            breakdown.get("unsupported_original_write_shape", 0),
        "entire_original_static_write_site_partition_disjoint": True,
        "residual_java_expression_source_recovered": False,
        "full_original_method_control_flow_source_recovered": False,
        "original_method_runtime_parity_certified": False,
        "canonical_private_original_method_field_identities_accepted": False,
    }


def replay_private_residual_write_atlas(
    original_jar: Path, class_entry: str, method_name: str,
    method_descriptor: str, output_dir: Path, *, original_sha256: str,
) -> dict:
    jar, out = Path(original_jar), Path(output_dir)
    _need(not out.exists() and not out.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    _need(type(original_sha256) is str
          and _PIN.fullmatch(original_sha256) is not None,
          "ORIGINAL_JAR_WHOLE_SHA256_INVALID")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar) == original_sha256.lower(),
          "ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(class_entry) is str and class_entry.endswith(".class")
          and not class_entry.startswith("/") and "\\" not in class_entry
          and all(x not in ("", ".", "..") and ":" not in x
                  for x in class_entry.split("/")),
          "INVALID_PRIVATE_CLASS_ENTRY")
    try:
        with ZipFile(jar) as archive:
            _need(archive.namelist().count(class_entry) == 1,
                  "ORIGINAL_OWNER_CLASS_ENTRY_MISSING_OR_DUPLICATE")
            profile = profile_jar_class(jar, class_entry)
        report = plan_original_residual_writes(
            profile, method_name, method_descriptor
        )
    except (BadZipFile, BytecodeProfileError, ScalarInitializerRecoveryError,
            TypedWriteChainError, NullGuardBooleanSourceError,
            OSError, KeyError, IndexError, TypeError):
        raise ResidualWriteAtlasError(
            "ORIGINAL_RESIDUAL_SITE_EVIDENCE_UNVERIFIABLE"
        ) from None
    _need(_digest(jar) == original_sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_RESIDUAL_PROOF")
    private = report.pop("private_residual_sites")
    raw = json.dumps(private, sort_keys=True, indent=2) + "\n"
    aggregate = {
        "schema_version": 1,
        "kind": "private_original_complex_method_complete_static_write_partition",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "private_residual_site_graph_sha256":
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        **report,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "residual-static-write-sites.private.json").open(
            "x", encoding="utf-8", newline="\n") as fd:
        fd.write(raw)
    with (out / "residual-static-write-atlas.aggregate.json").open(
            "x", encoding="utf-8", newline="\n") as fd:
        json.dump(aggregate, fd, sort_keys=True, indent=2)
        fd.write("\n")
    return aggregate


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("private_original_class_entry")
    p.add_argument("private_method_name")
    p.add_argument("private_method_descriptor")
    p.add_argument("new_private_output_directory", type=Path)
    p.add_argument("--original-sha256", required=True)
    args = p.parse_args(argv)
    try:
        print(json.dumps(replay_private_residual_write_atlas(
            args.original_jar, args.private_original_class_entry,
            args.private_method_name, args.private_method_descriptor,
            args.new_private_output_directory,
            original_sha256=args.original_sha256,
        ), sort_keys=True))
    except ResidualWriteAtlasError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
