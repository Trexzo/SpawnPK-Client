"""Verify one original Java boolean-negation initializer bytecode micro-slice.

Pattern: getstatic Z; ifne -> iconst_0; iconst_1; goto -> putstatic;
iconst_0; putstatic Z. Equivalence is limited to these six instructions;
the full JVM <clinit>, enum dependencies and runtime remain unverified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from .bytecode_profile import BytecodeProfileError, profile_jar_class


class BooleanNegationParityError(ValueError):
    """An original-vs-candidate negated field initialization is not proven."""


def _need(valid: bool, reason: str) -> None:
    if not valid:
        raise BooleanNegationParityError(reason)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fields(profile: dict) -> dict:
    rows = profile.get("fields")
    _need(isinstance(rows, list), "JVM_FIELD_METADATA_MISSING")
    fields = {}
    for row in rows:
        _need(isinstance(row, dict), "JVM_FIELD_METADATA_INVALID")
        key = row.get("name"), row.get("descriptor")
        _need(all(type(x) is str and x for x in key)
              and key not in fields, "DUPLICATE_OR_INVALID_JVM_FIELD")
        fields[key] = row
    return fields


def _six_instruction_slice(profile: dict, source: str, target: str) -> dict:
    owner = profile.get("internal_name")
    _need(type(owner) is str and owner, "CLASS_OWNER_MISSING")
    fields = _fields(profile)
    for name in (source, target):
        declaration = fields.get((name, "Z"))
        _need(declaration is not None,
              "SOURCE_OR_TARGET_BOOLEAN_FIELD_MISSING")
        _need(
            declaration.get("access") == 0x0009
            and declaration.get("signature") is None
            and declaration.get("constant_value") is None,
            "BOOLEAN_FIELD_DECLARATION_NOT_EXACT_MUTABLE_STATIC",
        )
    methods = profile.get("methods")
    _need(isinstance(methods, list), "ORIGINAL_METHOD_INVENTORY_MISSING")
    initializers = [m for m in methods if
                    m.get("name") == "<clinit>" and m.get("descriptor") == "()V"]
    _need(len(initializers) == 1, "UNIQUE_CLASS_INITIALIZER_REQUIRED")
    instructions = initializers[0].get("instructions")
    _need(
        isinstance(instructions, list)
        and all(isinstance(x, dict)
                and type(x.get("offset")) is int
                and type(x.get("length")) is int
                and x["length"] > 0 for x in instructions),
        "INCOMPLETE_CLINIT_INSTRUCTION_EVIDENCE",
    )
    instructions = sorted(instructions, key=lambda x: x["offset"])
    _need(len({x["offset"] for x in instructions}) == len(instructions),
          "DUPLICATE_CLASS_INITIALIZER_PC")
    matches = [i for i, row in enumerate(instructions)
               if row.get("opcode") == "0xb3" and row.get("owner") == owner
               and (row.get("name"), row.get("descriptor")) == (target, "Z")]
    _need(len(matches) == 1, "TARGET_BOOLEAN_STORE_NOT_UNIQUE")
    index = matches[0]
    _need(index >= 5, "NEGATION_SIX_OPCODE_PREFIX_MISSING")
    block = instructions[index - 5:index + 1]
    _need(
        all(x["offset"] + x["length"] == y["offset"]
            for x, y in zip(block, block[1:])),
        "NEGATION_INSTRUCTIONS_NOT_CONTIGUOUS",
    )
    get, branch, truthy, jump, falsy, put = block
    _need(
        [x["opcode"] for x in block]
        == ["0xb2", "0x9a", "0x04", "0xa7", "0x03", "0xb3"],
        "NOT_EXACT_BOOLEAN_NEGATION_OPCODE_PATTERN",
    )
    _need(
        get.get("owner") == owner
        and (get.get("name"), get.get("descriptor")) == (source, "Z"),
        "NEGATION_USES_DIFFERENT_SOURCE_FIELD",
    )
    _need(
        branch.get("branch_target_offset") == falsy["offset"],
        "NEGATION_FALSE_BRANCH_TARGET_DIFFERS",
    )
    _need(
        jump.get("branch_target_offset") == put["offset"],
        "NEGATION_STORE_JOIN_TARGET_DIFFERS",
    )
    _need(
        put.get("owner") == owner
        and (put.get("name"), put.get("descriptor")) == (target, "Z"),
        "NEGATION_STORES_DIFFERENT_FIELD",
    )
    return {
        "start": get["offset"],
        "store": put["offset"],
        "source_flags": fields[(source, "Z")]["access"],
        "target_flags": fields[(target, "Z")]["access"],
        "opcodes": [row["opcode"] for row in block],
    }


def compare_boolean_negation_profiles(
    original: dict, candidate: dict, *,
    source_field: str, target_field: str, original_sha256: str,
) -> dict:
    _need(type(source_field) is str and bool(source_field)
          and type(target_field) is str and bool(target_field)
          and source_field != target_field,
          "EXACT_DISTINCT_SOURCE_AND_TARGET_REQUIRED")
    _need(
        type(original_sha256) is str
        and re.fullmatch(r"[0-9a-fA-F]{64}", original_sha256) is not None,
        "INVALID_ORIGINAL_SHA_PIN",
    )
    _need(
        original.get("internal_name") == candidate.get("internal_name")
        and type(original.get("internal_name")) is str,
        "ORIGINAL_CANDIDATE_OWNER_ALIAS_UNACCEPTED",
    )
    old = _six_instruction_slice(original, source_field, target_field)
    new = _six_instruction_slice(candidate, source_field, target_field)
    checks = {
        "source_and_target_jvm_declaration_flags":
            (old["source_flags"], old["target_flags"])
            == (new["source_flags"], new["target_flags"]),
        "exact_original_branch_and_store_topology": True,
        "exact_six_jvm_opcodes": old["opcodes"] == new["opcodes"],
    }
    opaque = hashlib.sha256(json.dumps(
        [original_sha256.lower(), source_field, target_field, "Z"],
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest().upper()[:20]
    return {
        "schema_version": 1,
        "kind": "private_boolean_negation_clinit_microparity",
        "research_only": True,
        "field_relation_id": "BOOLNEG_" + opaque,
        "checks": checks,
        "microparity_pass": all(checks.values()),
        "original_slice_instruction_count": 6,
        "candidate_slice_instruction_count": 6,
        "original_slice_start_pc": old["start"],
        "candidate_slice_start_pc": new["start"],
        "full_clinit_equivalence_certified": False,
        "enum_dependent_boolean_initializer_recovered": False,
        "original_runtime_semantics_certified": False,
        "complete_source_equivalence_certified": False,
        "canonical_identity_accepted": False,
    }


def verify_boolean_negation_initializer(
    original_jar: Path, candidate_jar: Path, *,
    original_sha256: str, candidate_sha256: str, class_entry: str,
    source_field: str, target_field: str,
) -> dict:
    for path, pin in ((Path(original_jar), original_sha256),
                      (Path(candidate_jar), candidate_sha256)):
        _need(type(pin) is str and re.fullmatch(r"[0-9a-fA-F]{64}", pin)
              is not None, "INVALID_COMPLETE_JAR_SHA256")
        _need(path.is_file() and not path.is_symlink(), "JAR_MISSING_OR_SYMLINK")
        _need(_sha(path) == pin.lower(), "COMPLETE_JAR_SHA256_MISMATCH")
    _need(
        type(class_entry) is str and class_entry.endswith(".class")
        and not class_entry.startswith("/") and "\\" not in class_entry
        and all(x not in ("", ".", "..") and ":" not in x
                for x in class_entry.split("/")),
        "INVALID_ORIGINAL_CLASS_ENTRY",
    )
    try:
        original = profile_jar_class(Path(original_jar), class_entry)
        candidate = profile_jar_class(Path(candidate_jar), class_entry)
        result = compare_boolean_negation_profiles(
            original, candidate,
            source_field=source_field, target_field=target_field,
            original_sha256=original_sha256,
        )
    except (BytecodeProfileError, OSError, KeyError, ValueError):
        raise BooleanNegationParityError(
            "BOOLEAN_NEGATION_JVM_EVIDENCE_UNEVALUABLE"
        ) from None
    for path, pin in ((Path(original_jar), original_sha256),
                      (Path(candidate_jar), candidate_sha256)):
        _need(_sha(path) == pin.lower(), "INPUT_CHANGED_DURING_REPLAY")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("candidate_jar", type=Path)
    parser.add_argument("class_entry")
    parser.add_argument("source_field")
    parser.add_argument("target_field")
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = verify_boolean_negation_initializer(
            args.original_jar, args.candidate_jar,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
            class_entry=args.class_entry,
            source_field=args.source_field,
            target_field=args.target_field,
        )
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as fh:
                json.dump(report, fh, indent=2, sort_keys=True)
                fh.write("\n")
        print(json.dumps({
            "microparity_pass": report["microparity_pass"],
            "checks": report["checks"],
            "full_clinit_equivalence_certified": False,
        }, sort_keys=True))
    except BooleanNegationParityError as exc:
        parser.error(str(exc))
    except (OSError, ValueError):
        parser.error("BOOLEAN_NEGATION_PROOF_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
