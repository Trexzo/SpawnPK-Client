"""Stage exact JVM <clinit> scalar constant assignments as *private* Java source.

Requires SHA-256-pinned original and candidate classfiles, exact owner field
metadata and an immediately adjacent literal-producer + putstatic pair.
Preserves original order *among selected stores*, not the complete JVM
initializer. Never recovers other side effects or promotes canonical identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .source_class_method_matrix import (
    ClassMethodMatrixError, build_class_method_matrix,
)


class ScalarInitializerRecoveryError(ValueError):
    """Original scalar initializer evidence is incomplete or changed."""


_PIN = re.compile(r"[0-9a-fA-F]{64}\Z")
_INT_OPCODES = frozenset(
    ["0x02", "0x03", "0x04", "0x05", "0x06",
     "0x07", "0x08", "0x10", "0x11", "0x12", "0x13"]
)
_SCALAR_TYPES = {"Z": "boolean", "I": "integer",
                 "Ljava/lang/String;": "string"}


def _need(check: bool, code: str) -> None:
    if not check:
        raise ScalarInitializerRecoveryError(code)


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def _fields(profile: dict) -> dict[tuple[str, str], dict]:
    fields = profile.get("fields")
    _need(isinstance(fields, list), "JVM_FIELD_INVENTORY_MISSING")
    result = {}
    names = set()
    for field in fields:
        _need(isinstance(field, dict), "JVM_FIELD_DECLARATION_INVALID")
        key = field.get("name"), field.get("descriptor")
        _need(
            all(type(x) is str and x for x in key)
            and key not in result and key[0] not in names,
            "DUPLICATE_OR_INVALID_JVM_FIELD",
        )
        _need(
            type(field.get("access")) is int
            and "signature" in field and "constant_value" in field,
            "INCOMPLETE_JVM_FIELD_METADATA",
        )
        result[key] = field
        names.add(key[0])
    return result


def _clinit(profile: dict, *, required: bool) -> dict | None:
    methods = profile.get("methods")
    _need(isinstance(methods, list), "METHOD_INVENTORY_MISSING")
    found = [m for m in methods if
             m.get("name") == "<clinit>" and m.get("descriptor") == "()V"]
    _need(len(found) <= 1, "DUPLICATE_CLASS_INITIALIZER")
    if required:
        _need(len(found) == 1, "ORIGINAL_CLASS_INITIALIZER_MISSING")
    return found[0] if found else None


def _instructions(method: dict) -> list[dict]:
    rows = method.get("instructions")
    _need(isinstance(rows, list), "CLINIT_INSTRUCTIONS_MISSING")
    _need(
        all(isinstance(r, dict) and
            type(r.get("offset")) is int and r["offset"] >= 0 and
            type(r.get("length")) is int and r["length"] > 0
            for r in rows),
        "CLINIT_INSTRUCTION_METADATA_INVALID",
    )
    rows = sorted(rows, key=lambda x: x["offset"])
    _need(
        len({r["offset"] for r in rows}) == len(rows),
        "DUPLICATE_CLINIT_INSTRUCTION_OFFSET",
    )
    return rows


def _literal(insn: dict, descriptor: str) -> tuple[str, str]:
    op = insn.get("opcode")
    _need(op in _INT_OPCODES, "SCALAR_ORIGINAL_VALUE_NOT_LITERAL")
    if descriptor in ("Z", "I"):
        _need(op in _INT_OPCODES, "INTEGER_LITERAL_OPCODE_UNSUPPORTED")
        if op in ("0x12", "0x13"):
            _need(
                insn.get("constant_pool_tag") == 3
                and type(insn.get("constant")) is int,
                "INTEGER_LDC_CONSTANT_KIND_MISMATCH",
            )
            val = insn["constant"]
        else:
            val = insn.get("int_constant")
            _need(type(val) is int, "INTEGER_LITERAL_VALUE_MISSING")
        _need(-(2**31) <= val <= 2**31 - 1,
              "INTEGER_LITERAL_OUTSIDE_JVM_RANGE")
        if descriptor == "Z":
            _need(val in (0, 1), "BOOLEAN_LITERAL_NOT_ZERO_OR_ONE")
            return ("true" if val == 1 else "false"), "boolean"
        return str(val), "integer"

    _need(descriptor == "Ljava/lang/String;",
          "UNSUPPORTED_MUTABLE_SCALAR_DESCRIPTOR")
    _need(
        op in ("0x12", "0x13")
        and insn.get("constant_pool_tag") == 8
        and type(insn.get("constant")) is str,
        "STRING_LITERAL_NOT_EXACT_JVM_STRING",
    )
    value = insn["constant"]
    _need(
        all(32 <= ord(ch) <= 126 for ch in value),
        "NON_ASCII_STRING_REQUIRES_MANUAL_LITERAL_RECOVERY",
    )
    return json.dumps(value, ensure_ascii=True), "string"


def plan_exact_scalar_initializer_fragment(original: dict, candidate: dict) -> dict:
    owner = original.get("internal_name")
    _need(
        type(owner) is str and owner
        and owner == candidate.get("internal_name"),
        "ORIGINAL_CANDIDATE_CLASS_ALIAS_UNACCEPTED",
    )
    old_fields, new_fields = _fields(original), _fields(candidate)
    selected = {
        key: field for key, field in old_fields.items()
        if field["access"] == 0x0009
        and key[1] in _SCALAR_TYPES
        and field["signature"] is None
        and field["constant_value"] is None
    }
    _need(bool(selected), "NO_ORIGINAL_MUTABLE_SCALAR_FIELDS")
    for key, original_field in selected.items():
        rebuilt = new_fields.get(key)
        _need(rebuilt is not None, "CANDIDATE_SCALAR_DECLARATION_MISSING")
        _need(
            all(original_field.get(k) == rebuilt.get(k) for k in
                ("access", "signature", "constant_value")),
            "CANDIDATE_SCALAR_DECLARATION_METADATA_DIFFERENT",
        )
    original_init = _clinit(original, required=True)
    old_instr = _instructions(original_init)
    _need(old_instr, "EMPTY_ORIGINAL_CLASS_INITIALIZER")
    by_offset = {x["offset"]: i for i, x in enumerate(old_instr)}
    _need(
        type(original_init.get("code_length")) is int
        and original_init["code_length"] > old_instr[-1]["offset"],
        "ORIGINAL_CLINIT_LENGTH_INVALID",
    )

    new_init = _clinit(candidate, required=False)
    if new_init is not None:
        for insn in _instructions(new_init):
            if (insn.get("opcode") == "0xb3"
                    and insn.get("owner") == owner
                    and (insn.get("name"), insn.get("descriptor")) in selected):
                raise ScalarInitializerRecoveryError(
                    "CANDIDATE_SCALAR_ALREADY_INITIALIZED"
                )

    assignments = []
    seen = set()
    counts = {"boolean": 0, "integer": 0, "string": 0}
    for insn in old_instr:
        if insn.get("opcode") != "0xb3" or insn.get("owner") != owner:
            continue
        key = insn.get("name"), insn.get("descriptor")
        if key not in selected:
            continue
        _need(key not in seen, "ORIGINAL_SCALAR_ASSIGNED_MORE_THAN_ONCE")
        seen.add(key)
        index = by_offset[insn["offset"]]
        _need(index > 0, "SCALAR_STORE_WITHOUT_DIRECT_VALUE_PRODUCER")
        before = old_instr[index - 1]
        _need(
            before["offset"] + before["length"] == insn["offset"],
            "ORIGINAL_SCALAR_LITERAL_AND_STORE_NOT_CONTIGUOUS",
        )
        literal, kind = _literal(before, key[1])
        name = key[0]
        _need(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", name) is not None,
              "PRIVATE_FIELD_NAME_NOT_JAVA_IDENTIFIER")
        assignments.append((insn["offset"], name, literal))
        counts[kind] += 1
    _need(
        len(assignments) == len(selected)
        and seen == set(selected),
        "ORIGINAL_MUTABLE_SCALAR_INITIALIZATION_MISSING",
    )
    assignments.sort()
    snippet = (
        "// PRIVATE exact original JVM scalar store pairs, review ONLY.\n"
        "// All omitted class-initialization instructions are still UNRECOVERED.\n"
        "// Original order preserved only among these selected field stores.\n"
        "    static {\n"
        + "".join(f"        {name} = {literal};\n"
                  for _, name, literal in assignments)
        + "    }\n"
    )
    return {
        "snippet": snippet,
        "original_mutable_scalar_field_count": len(selected),
        "literal_assignment_count": len(assignments),
        "assignment_type_counts": counts,
        "original_clinit_code_bytes": original_init["code_length"],
        "all_selected_assignments_have_immediate_literal_producers": True,
        "selected_assignment_order_matches_original": True,
        "full_class_initializer_order_recovered": False,
        "other_class_initializer_operations_recovered": False,
        "later_runtime_field_writes_recovered": False,
        "original_class_runtime_equivalence_certified": False,
        "source_equivalence_certified": False,
        "canonical_class_and_field_identities_accepted": False,
    }


def build_private_scalar_initializer_fragment(
    original_jar: Path, candidate_jar: Path, out_root: Path, *,
    original_sha256: str, candidate_sha256: str, class_entry: str,
) -> dict[str, Any]:
    original_jar, candidate_jar, out_root = map(
        Path, (original_jar, candidate_jar, out_root)
    )
    _need(not out_root.exists() and not out_root.is_symlink(),
          "SCALAR_OUTPUT_ALREADY_EXISTS")
    for path, pin in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        _need(
            type(pin) is str and _PIN.fullmatch(pin) is not None,
            "INVALID_COMPLETE_JAR_SHA256",
        )
        _need(path.is_file() and not path.is_symlink(),
              "JAR_MISSING_OR_SYMLINK")
        _need(_digest(path) == pin.lower(), "COMPLETE_JAR_SHA256_MISMATCH")
    _need(
        type(class_entry) is str and class_entry.endswith(".class")
        and not class_entry.startswith("/") and "\\" not in class_entry
        and all(p not in ("", ".", "..") and ":" not in p
                for p in class_entry.split("/")),
        "INVALID_PRIVATE_CLASS_ENTRY",
    )
    try:
        matrix = build_class_method_matrix(
            original_jar, candidate_jar,
            original_sha256=original_sha256,
            candidate_sha256=candidate_sha256,
            class_entry=class_entry,
        )
        _need(
            matrix.get("research_only") is True
            and matrix.get("source_equivalence_certified") is False
            and matrix.get("canonical_identity_accepted") is False,
            "UNEXPECTED_STRICT_MATRIX_AUTHORITY",
        )
        original = profile_jar_class(original_jar, class_entry)
        candidate = profile_jar_class(candidate_jar, class_entry)
        plan = plan_exact_scalar_initializer_fragment(original, candidate)
    except (
        BytecodeProfileError, ClassMethodMatrixError, OSError, KeyError,
        IndexError,
    ):
        raise ScalarInitializerRecoveryError(
            "SCALAR_SOURCE_INPUT_OR_PROFILE_UNEVALUABLE"
        ) from None
    for path, pin in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        _need(_digest(path) == pin.lower(),
              "JAR_CHANGED_DURING_SCALAR_REPLAY")
    text = plan.pop("snippet")
    manifest = {
        "schema_version": 1,
        "kind": "private_exact_jvm_mutable_scalar_initializer_source",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "candidate_complete_jar_sha256": candidate_sha256.lower(),
        "strict_matrix_report_id": matrix["report_id"],
        "private_source_fragment_sha256": hashlib.sha256(
            text.encode("utf-8")).hexdigest(),
        **plan,
    }
    out_root.mkdir(parents=True, exist_ok=False)
    with (out_root / "mutable-scalars-clinit.fragment.txt").open(
        "x", encoding="utf-8", newline="\n"
    ) as file:
        file.write(text)
    with (out_root / "aggregate-private-scalar-proof.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as file:
        json.dump(manifest, file, indent=2, sort_keys=True)
        file.write("\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("candidate_jar", type=Path)
    parser.add_argument("class_entry")
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        report = build_private_scalar_initializer_fragment(
            args.original_jar, args.candidate_jar, args.output_root,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
            class_entry=args.class_entry,
        )
        print(json.dumps(report, sort_keys=True))
    except ScalarInitializerRecoveryError as exc:
        parser.error(str(exc))
    except (OSError, ValueError):
        parser.error("PRIVATE_SCALAR_INITIALIZATION_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
