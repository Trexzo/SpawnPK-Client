"""Strict three-instruction static-final int-array allocation micro-parity.

A candidate's Java array initialization may be checked against the
original JVM bipush/sipush/iconst; newarray int; putstatic sequence.
Only this sequence is proven, not any other part of class initialization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from zipfile import BadZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class


class ArrayInitializerParityError(ValueError):
    """No reliable original/candidate array initializer micro-parity."""


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise ArrayInitializerParityError(reason)


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fields(p: dict) -> dict[tuple[str, str], dict]:
    rows = p.get("fields")
    _need(isinstance(rows, list), "FIELD_INVENTORY_MISSING")
    result = {}
    for row in rows:
        _need(isinstance(row, dict), "INVALID_FIELD")
        key = row.get("name"), row.get("descriptor")
        _need(all(isinstance(x, str) and x for x in key)
              and key not in result, "INVALID_OR_DUPLICATE_FIELD")
        result[key] = row
    return result


def _allocation(p: dict, name: str) -> dict[str, Any]:
    owner = p.get("internal_name")
    _need(isinstance(owner, str) and owner, "MISSING_ORIGINAL_OWNER")
    fields = _fields(p)
    key = name, "[I"
    field = fields.get(key)
    _need(field is not None, "TARGET_INT_ARRAY_FIELD_MISSING")
    _need(type(field.get("access")) is int
          and field["access"] & 0x0018 == 0x0018,
          "TARGET_ARRAY_NOT_STATIC_FINAL")
    _need(field.get("constant_value") is None,
          "TARGET_ARRAY_HAS_UNEXPECTED_CONSTANTVALUE")
    methods = p.get("methods")
    _need(isinstance(methods, list), "METHOD_INVENTORY_MISSING")
    init = [m for m in methods if m.get("name") == "<clinit>"
            and m.get("descriptor") == "()V"]
    _need(len(init) == 1, "UNIQUE_CLINIT_REQUIRED")
    m = init[0]
    insns = m.get("instructions")
    _need(isinstance(insns, list), "CLINIT_INSTRUCTIONS_MISSING")
    _need(all(isinstance(x, dict) and type(x.get("offset")) is int
              and type(x.get("length")) is int for x in insns),
          "CLINIT_INSTRUCTION_METADATA_INVALID")
    insns = sorted(insns, key=lambda x: x["offset"])
    _need(len({x["offset"] for x in insns}) == len(insns),
          "DUPLICATE_CLINIT_OFFSET")
    stores = [i for i, row in enumerate(insns)
              if row.get("opcode") == "0xb3"
              and row.get("owner") == owner
              and (row.get("name"), row.get("descriptor")) == key]
    _need(len(stores) == 1, "ARRAY_ALLOCATION_STORE_NOT_UNIQUE")
    index = stores[0]
    _need(index >= 2, "ARRAY_ALLOCATION_HAS_NO_IMMEDIATE_PREFIX")
    count, array, store = insns[index-2:index+1]
    _need(
        count["offset"] + count["length"] == array["offset"]
        and array["offset"] + array["length"] == store["offset"],
        "ARRAY_ALLOCATION_PREFIX_NOT_CONTIGUOUS",
    )
    _need(count.get("opcode") in
          ("0x02", "0x03", "0x04", "0x05", "0x06", "0x07",
           "0x08", "0x10", "0x11"),
          "ARRAY_ALLOCATION_LENGTH_NOT_IMMEDIATE",
    )
    n = count.get("int_constant")
    _need(type(n) is int and n >= 0, "ARRAY_ALLOCATION_SIZE_INVALID")
    _need(array.get("opcode") == "0xbc"
          and array.get("array_primitive_atype") == 10,
          "ARRAY_ALLOCATION_IS_NOT_INT_ARRAY",
    )
    _need(store.get("opcode") == "0xb3", "ARRAY_ALLOCATION_NO_PUTSTATIC")
    _need(all(ins.get("length", 0) > 0 for ins in (count, array, store)),
          "ARRAY_ALLOCATION_INVALID_CODE_LENGTH")
    return {
        "bytecode_opcodes": [count["opcode"], array["opcode"], store["opcode"]],
        "length": n,
        "array_primitive_atype": 10,
        "original_or_candidate_pc": count["offset"],
        "jvm_field_access": field["access"],
        "field_signature": field.get("signature"),
        "field_constant_value": field.get("constant_value"),
    }


def compare_array_initializer_profiles(
    original: dict, candidate: dict, *, field_name: str,
    original_sha256: str,
) -> dict[str, Any]:
    _need(isinstance(field_name, str) and bool(field_name),
          "TARGET_FIELD_NAME_REQUIRED")
    _need(original.get("internal_name") == candidate.get("internal_name")
          and isinstance(original.get("internal_name"), str),
          "NO_ACCEPTED_CLASS_ALIAS")
    _need(type(original_sha256) is str
          and re.fullmatch(r"[0-9a-fA-F]{64}", original_sha256) is not None,
          "INVALID_ORIGINAL_SHA256")
    old = _allocation(original, field_name)
    new = _allocation(candidate, field_name)
    checks = {
        "exact_field_metadata": all(old[k] == new[k] for k in
                                    ("jvm_field_access", "field_signature",
                                     "field_constant_value")),
        "exact_array_length": old["length"] == new["length"],
        "exact_primitive_type": old["array_primitive_atype"]
        == new["array_primitive_atype"],
        "exact_allocation_opcode_sequence":
        old["bytecode_opcodes"] == new["bytecode_opcodes"],
    }
    identifier = hashlib.sha256(json.dumps(
        [original_sha256.lower(), field_name, "[I"],
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest().upper()[:20]
    return {
        "schema_version": 1,
        "kind": "private_static_final_int_array_initializer_microparity",
        "research_only": True,
        "field_id": "ARRAY_" + identifier,
        "checks": checks,
        "microparity_pass": all(checks.values()),
        "original_allocation_length": old["length"],
        "candidate_allocation_length": new["length"],
        "original_allocation_start_pc": old["original_or_candidate_pc"],
        "candidate_allocation_start_pc": new["original_or_candidate_pc"],
        "source_equivalence_certified": False,
        "full_clinit_equivalence_certified": False,
        "original_class_identity_accepted": False,
        "runtime_equivalence_certified": False,
    }


def verify_array_initializer(
    original_jar: Path, candidate_jar: Path, *, original_sha256: str,
    candidate_sha256: str, class_entry: str, field_name: str,
) -> dict[str, Any]:
    for path, pin in ((Path(original_jar), original_sha256),
                      (Path(candidate_jar), candidate_sha256)):
        _need(type(pin) is str
              and re.fullmatch(r"[0-9a-fA-F]{64}", pin) is not None,
              "INVALID_WHOLE_JAR_SHA256_PIN")
        _need(path.is_file() and not path.is_symlink(),
              "JAR_MISSING_OR_SYMLINK")
        _need(_digest(path) == pin.lower(), "WHOLE_JAR_SHA256_MISMATCH")
    _need(isinstance(class_entry, str) and class_entry.endswith(".class")
          and not class_entry.startswith("/")
          and "\\" not in class_entry
          and all(x not in ("", ".", "..") and ":" not in x
                  for x in class_entry.split("/")),
          "INVALID_ORIGINAL_CLASS_ENTRY")
    try:
        original = profile_jar_class(Path(original_jar), class_entry)
        candidate = profile_jar_class(Path(candidate_jar), class_entry)
        result = compare_array_initializer_profiles(
            original, candidate, field_name=field_name,
            original_sha256=original_sha256,
        )
    except (BytecodeProfileError, BadZipFile, OSError, KeyError,
            IndexError, ValueError):
        raise ArrayInitializerParityError(
            "ARRAY_INITIALIZER_EVIDENCE_UNEVALUABLE"
        ) from None
    for path, pin in ((Path(original_jar), original_sha256),
                      (Path(candidate_jar), candidate_sha256)):
        _need(_digest(path) == pin.lower(), "JAR_CHANGED_DURING_REPLAY")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("candidate_jar", type=Path)
    parser.add_argument("class_entry")
    parser.add_argument("field_name")
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = verify_array_initializer(
            args.original_jar, args.candidate_jar,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
            class_entry=args.class_entry, field_name=args.field_name,
        )
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, sort_keys=True)
                handle.write("\n")
        # Only aggregate evidence, no user-supplied original private name.
        print(json.dumps({
            "microparity_pass": report["microparity_pass"],
            "checks": report["checks"],
            "original_allocation_length": report["original_allocation_length"],
            "candidate_allocation_length": report["candidate_allocation_length"],
            "source_equivalence_certified": False,
        }, sort_keys=True))
    except ArrayInitializerParityError as exc:
        parser.error(str(exc))
    except (OSError, ValueError):
        parser.error("ARRAY_INITIALIZER_MICROPARITY_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
