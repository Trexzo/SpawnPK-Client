"""Exact JVM three-opcode boxed-Integer initializer micro-parity.

Checks ldc Integer constant, Integer.valueOf(int), putstatic of an
identical static-final Integer field in original and compiled candidate.
This does not prove the full class initializer, method bodies or runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class


class BoxedIntegerInitializerError(ValueError):
    """An original-vs-source boxed Integer initialization cannot be proven."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise BoxedIntegerInitializerError(reason)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _slice(profile: dict, name: str) -> dict:
    owner = profile.get("internal_name")
    _require(isinstance(owner, str) and owner, "CLASS_OWNER_MISSING")
    fields = profile.get("fields")
    _require(isinstance(fields, list), "FIELD_INVENTORY_MISSING")
    rows = [field for field in fields
            if field.get("name") == name
            and field.get("descriptor") == "Ljava/lang/Integer;"]
    _require(len(rows) == 1, "BOXED_INTEGER_FIELD_NOT_UNIQUE")
    field = rows[0]
    _require(type(field.get("access")) is int
             and field["access"] & 0x0018 == 0x0018,
             "BOXED_INTEGER_NOT_STATIC_FINAL")
    _require(field.get("constant_value") is None,
             "UNEXPECTED_FIELD_CONSTANTVALUE")
    methods = profile.get("methods")
    _require(isinstance(methods, list), "ORIGINAL_METHODS_MISSING")
    clinit = [m for m in methods if m.get("name") == "<clinit>"
              and m.get("descriptor") == "()V"]
    _require(len(clinit) == 1, "EXACT_CLINIT_MISSING")
    method = clinit[0]
    instructions = method.get("instructions")
    _require(isinstance(instructions, list) and
             all(isinstance(row, dict)
                 and type(row.get("offset")) is int
                 and type(row.get("length")) is int
                 for row in instructions),
             "INVALID_CLINIT_INSTRUCTIONS")
    instructions = sorted(instructions, key=lambda x: x["offset"])
    _require(len({x["offset"] for x in instructions}) == len(instructions),
             "CLINIT_DUPLICATE_INSTRUCTION")
    targets = [i for i, row in enumerate(instructions)
               if row.get("opcode") == "0xb3"
               and row.get("owner") == owner
               and row.get("name") == name
               and row.get("descriptor") == "Ljava/lang/Integer;"]
    _require(len(targets) == 1, "BOXED_INTEGER_CLINIT_STORE_NOT_UNIQUE")
    idx = targets[0]
    _require(idx >= 2, "BOXED_INTEGER_MISSING_THREE_OP_SEQUENCE")
    ldc, call, store = instructions[idx-2:idx+1]
    _require(
        ldc["offset"] + ldc["length"] == call["offset"]
        and call["offset"] + call["length"] == store["offset"],
        "BOXED_INTEGER_INSTRUCTIONS_NOT_CONTIGUOUS",
    )
    _require(ldc.get("opcode") in ("0x12", "0x13")
             and ldc.get("constant_pool_tag") == 3
             and type(ldc.get("constant")) is int
             and re.fullmatch(r"[a-f0-9]{8}",
                              str(ldc.get("constant_raw_bits", ""))) is not None,
             "BOXED_INTEGER_SOURCE_NOT_JVM_INT_LDC",
    )
    _require(call.get("opcode") == "0xb8"
             and call.get("owner") == "java/lang/Integer"
             and call.get("name") == "valueOf"
             and call.get("descriptor") == "(I)Ljava/lang/Integer;",
             "BOXED_INTEGER_VALUEOF_CALL_DIFFERENT")
    _require(store.get("opcode") == "0xb3",
             "BOXED_INTEGER_MISSING_PUTSTATIC")
    return {
        "opcodes": [ldc["opcode"], call["opcode"], store["opcode"]],
        "integer_raw_bits": ldc["constant_raw_bits"],
        "initializer_start_offset": ldc["offset"],
        "field_access": field["access"],
        "field_signature": field.get("signature"),
    }


def compare_boxed_initializer_profiles(
    original: dict, candidate: dict, *,
    field_name: str, original_sha256: str,
) -> dict:
    _require(type(field_name) is str and bool(field_name),
             "BOXED_INTEGER_FIELD_NAME_REQUIRED")
    _require(original.get("internal_name") == candidate.get("internal_name")
             and isinstance(original.get("internal_name"), str),
             "NO_ACCEPTED_CLASS_ALIAS")
    _require(type(original_sha256) is str
             and re.fullmatch(r"[a-fA-F0-9]{64}", original_sha256) is not None,
             "INVALID_ORIGINAL_JAR_PIN")
    a, b = _slice(original, field_name), _slice(candidate, field_name)
    checks = {
        "exact_field_access_and_signature":
            (a["field_access"], a["field_signature"])
            == (b["field_access"], b["field_signature"]),
        "exact_jvm_integer_constant_bits":
            a["integer_raw_bits"] == b["integer_raw_bits"],
        "exact_three_opcode_sequence": a["opcodes"] == b["opcodes"],
        "exact_integer_valueof_call": True,
    }
    opaque = hashlib.sha256(json.dumps(
        [original_sha256.lower(), field_name, "Ljava/lang/Integer;"],
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest().upper()[:20]
    return {
        "schema_version": 1,
        "kind": "private_boxed_integer_initialization_microparity",
        "research_only": True,
        "field_id": "BOXED_" + opaque,
        "checks": checks,
        "microparity_pass": all(checks.values()),
        "original_init_start_offset": a["initializer_start_offset"],
        "candidate_init_start_offset": b["initializer_start_offset"],
        "original_constant_value_sha256": hashlib.sha256(
            bytes.fromhex(a["integer_raw_bits"])
        ).hexdigest(),
        "full_clinit_equivalence_certified": False,
        "whole_source_equivalence_certified": False,
        "runtime_semantics_certified": False,
        "canonical_identity_accepted": False,
    }


def verify_boxed_initializer(
    original_jar: Path, candidate_jar: Path, *,
    original_sha256: str, candidate_sha256: str,
    class_entry: str, field_name: str,
) -> dict:
    for path, expected in ((Path(original_jar), original_sha256),
                           (Path(candidate_jar), candidate_sha256)):
        _require(type(expected) is str and
                 re.fullmatch(r"[0-9a-fA-F]{64}", expected) is not None,
                 "INVALID_WHOLE_JAR_SHA256")
        _require(path.is_file() and not path.is_symlink(),
                 "JAR_MISSING_OR_SYMLINK")
        _require(_sha(path) == expected.lower(), "WHOLE_JAR_SHA256_MISMATCH")
    _require(isinstance(class_entry, str) and class_entry.endswith(".class")
             and not class_entry.startswith("/")
             and "\\" not in class_entry
             and all(part not in ("", ".", "..") and ":" not in part
                     for part in class_entry.split("/")),
             "INVALID_CLASS_ENTRY")
    try:
        original = profile_jar_class(Path(original_jar), class_entry)
        candidate = profile_jar_class(Path(candidate_jar), class_entry)
        report = compare_boxed_initializer_profiles(
            original, candidate, field_name=field_name,
            original_sha256=original_sha256,
        )
    except (BytecodeProfileError, BadZipFile, OSError,
            KeyError, IndexError, ValueError):
        raise BoxedIntegerInitializerError(
            "BOXED_INTEGER_EVIDENCE_UNEVALUABLE"
        ) from None
    for path, expected in ((Path(original_jar), original_sha256),
                           (Path(candidate_jar), candidate_sha256)):
        _require(_sha(path) == expected.lower(), "INPUT_CHANGED_DURING_REPLAY")
    return report


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
        report = verify_boxed_initializer(
            args.original_jar, args.candidate_jar,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
            class_entry=args.class_entry, field_name=args.field_name,
        )
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, sort_keys=True)
                stream.write("\n")
        print(json.dumps({
            "microparity_pass": report["microparity_pass"],
            "checks": report["checks"],
            "whole_source_equivalence_certified": False,
        }, sort_keys=True))
    except BoxedIntegerInitializerError as exc:
        parser.error(str(exc))
    except (OSError, ValueError):
        parser.error("BOXED_INTEGER_INIT_REPLAY_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
