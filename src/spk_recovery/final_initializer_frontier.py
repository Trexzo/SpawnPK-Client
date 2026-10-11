"""Locate exact JVM <clinit> writes of static-final fields without ConstantValue.

The tool does not decompile an assignment expression. It verifies the
original-JAR Code store site, its immediately preceding instruction and
whether a reconstructed candidate field is missing or metadata-different.
Detailed original coordinates remain in a private, caller-owned report.
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


class FinalInitializerFrontierError(ValueError):
    """No reliable static-final initializer witness is available."""


def _check(test: bool, code: str) -> None:
    if not test:
        raise FinalInitializerFrontierError(code)


def _key(row: dict) -> tuple[str, str]:
    _check(isinstance(row, dict), "INVALID_JVM_FIELD_ROW")
    name, descriptor = row.get("name"), row.get("descriptor")
    _check(
        isinstance(name, str) and bool(name)
        and isinstance(descriptor, str) and bool(descriptor),
        "INVALID_JVM_FIELD_KEY",
    )
    return name, descriptor


def _opaque(original_sha: str, name: str, descriptor: str) -> str:
    payload = json.dumps([original_sha, name, descriptor], separators=(",", ":"))
    return "FINAL_" + hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()[:20]


def classify_descriptor(descriptor: str) -> str:
    if descriptor == "Ljava/lang/String;":
        return "string"
    if descriptor == "Ljava/lang/Integer;":
        return "boxed_integer"
    if descriptor == "[I":
        return "int_array"
    if descriptor in ("B", "C", "D", "F", "I", "J", "S", "Z"):
        return "primitive"
    if descriptor.startswith("["):
        return "other_array"
    if descriptor.startswith("L") and descriptor.endswith(";"):
        return "other_reference"
    raise FinalInitializerFrontierError("INVALID_FINAL_FIELD_TYPE")


def examine_final_initializers(
    original: dict, candidate: dict, matrix: dict, *,
    original_sha256: str,
) -> dict[str, Any]:
    owner = original.get("internal_name")
    _check(isinstance(owner, str) and bool(owner)
           and owner == candidate.get("internal_name"),
           "CLASS_OWNER_ALIAS_NOT_ACCEPTED")
    _check(
        matrix.get("research_only") is True
        and matrix.get("source_equivalence_certified") is False
        and matrix.get("canonical_identity_accepted") is False,
        "MATRIX_AUTHORITY_UNEXPECTED",
    )
    _check(type(original_sha256) is str
           and re.fullmatch(r"[a-fA-F0-9]{64}", original_sha256) is not None,
           "INVALID_ORIGINAL_SHA256")
    fields = original.get("fields")
    _check(isinstance(fields, list), "ORIGINAL_FIELDS_MISSING")
    candidates = candidate.get("fields")
    _check(isinstance(candidates, list), "CANDIDATE_FIELDS_MISSING")
    original_keys = {_key(x): x for x in fields}
    candidate_keys = {_key(x): x for x in candidates}
    _check(len(original_keys) == len(fields)
           and len(candidate_keys) == len(candidates),
           "DUPLICATE_JVM_FIELD_DECLARATION")
    methods = original.get("methods")
    _check(isinstance(methods, list), "ORIGINAL_METHODS_MISSING")
    initializers = [
        m for m in methods if m.get("name") == "<clinit>"
        and m.get("descriptor") == "()V"
    ]
    _check(len(initializers) == 1, "UNIQUE_ORIGINAL_CLINIT_REQUIRED")
    initializer = initializers[0]
    instructions = initializer.get("instructions")
    accesses = initializer.get("field_accesses")
    _check(isinstance(instructions, list)
           and isinstance(accesses, list),
           "CLINIT_CODE_EVIDENCE_MISSING")
    offset_map: dict[int, dict] = {}
    for insn in instructions:
        _check(isinstance(insn, dict)
               and type(insn.get("offset")) is int,
               "CLINIT_INSTRUCTION_INVALID")
        pc = insn["offset"]
        _check(pc not in offset_map and pc >= 0,
               "DUPLICATE_CLINIT_INSTRUCTION_OFFSET")
        offset_map[pc] = insn
    insns = sorted(offset_map)
    _check(bool(insns), "EMPTY_CLINIT_BODY")
    _check(type(initializer.get("code_length")) is int
           and initializer["code_length"] > insns[-1],
           "INVALID_CLINIT_CODE_LENGTH")
    writes: dict[tuple[str, str], list[int]] = {}
    for method in methods:
        _check(isinstance(method, dict), "INVALID_ORIGINAL_METHOD")
        accesses_in_method = method.get("field_accesses")
        _check(isinstance(accesses_in_method, list),
               "METHOD_FIELD_ACCESS_EVIDENCE_MISSING")
        for access in accesses_in_method:
            _check(isinstance(access, dict), "INVALID_FIELD_ACCESS")
            if (access.get("operation") != "putstatic"
                    or access.get("owner") != owner):
                continue
            key = access.get("name"), access.get("descriptor")
            _check(key in original_keys, "UNDECLARED_ORIGINAL_FIELD_WRITE")
            if method is initializer:
                pc = access.get("offset")
                _check(type(pc) is int and pc in offset_map,
                       "ORIGINAL_CLINIT_WRITE_NOT_AT_INSTRUCTION")
                actual = offset_map[pc]
                _check(actual.get("opcode") == "0xb3"
                       and actual.get("owner") == owner
                       and (actual.get("name"), actual.get("descriptor")) == key,
                       "CLINIT_WRITE_PROFILE_INCONSISTENT")
                writes.setdefault(key, []).append(pc)
            else:
                field = original_keys[key]
                if field.get("access", 0) & 0x0018 == 0x0018:
                    raise FinalInitializerFrontierError(
                        "FINAL_FIELD_WRITE_OUTSIDE_CLINIT"
                    )

    rows = []
    type_counts: dict[str, int] = {}
    for key, field in original_keys.items():
        access = field.get("access")
        _check(type(access) is int, "INVALID_ORIGINAL_FIELD_ACCESS")
        if access & 0x0018 != 0x0018 or field.get("constant_value") is not None:
            continue
        pcs = writes.get(key, [])
        _check(len(pcs) == 1, "FINAL_NONCONSTANT_REQUIRES_EXACTLY_ONE_CLINIT_WRITE")
        pc = pcs[0]
        position = insns.index(pc)
        _check(position > 0, "CLINIT_WRITE_LACKS_PRECEDING_INSTRUCTION")
        prev = offset_map[insns[position - 1]]
        kind = classify_descriptor(key[1])
        type_counts[kind] = type_counts.get(kind, 0) + 1
        cand = candidate_keys.get(key)
        status = "missing"
        if cand is not None:
            status = (
                "present_same_metadata"
                if all(field.get(prop) == cand.get(prop)
                       for prop in ("access", "signature", "constant_value"))
                else "present_metadata_difference"
            )
        rows.append({
            "field_id": _opaque(original_sha256.lower(), *key),
            "field_type_category": kind,
            "candidate_field_status": status,
            "original_clinit_write_pc": pc,
            "preceding_instruction_pc": prev["offset"],
            "preceding_opcode": prev.get("opcode"),
            "expression_or_runtime_value_recovered": False,
            "assignment_store_site_verified": True,
        })
    rows.sort(key=lambda r: r["original_clinit_write_pc"])
    statuses = {
        k: sum(row["candidate_field_status"] == k for row in rows)
        for k in ("missing", "present_metadata_difference",
                  "present_same_metadata")
    }
    result = {
        "schema_version": 1,
        "kind": "private_original_clinit_final_field_store_frontier",
        "research_only": True,
        "canonical_identity_accepted": False,
        "complete_source_reconstructed": False,
        "runtime_initializer_equivalence_certified": False,
        "source_expressions_emitted": False,
        "original_final_fields_without_constantvalue": len(rows),
        "original_clinit_code_bytes": initializer["code_length"],
        "type_counts": {k: type_counts[k] for k in sorted(type_counts)},
        "candidate_status_counts": statuses,
        "assignment_sites": rows,
    }
    return result


def build_final_initializer_frontier(
    original_jar: Path, candidate_jar: Path, *,
    original_sha256: str, candidate_sha256: str, class_entry: str,
) -> dict[str, Any]:
    try:
        matrix = build_class_method_matrix(
            Path(original_jar), Path(candidate_jar),
            original_sha256=original_sha256,
            candidate_sha256=candidate_sha256,
            class_entry=class_entry,
        )
        original = profile_jar_class(Path(original_jar), class_entry)
        candidate = profile_jar_class(Path(candidate_jar), class_entry)
        result = examine_final_initializers(
            original, candidate, matrix, original_sha256=original_sha256,
        )
        for path, pin in (
            (Path(original_jar), original_sha256),
            (Path(candidate_jar), candidate_sha256),
        ):
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            _check(digest.hexdigest() == pin.lower(),
                   "JAR_INPUT_CHANGED_DURING_REPLAY")
        core = {
            "original_jar_sha256": original_sha256.lower(),
            "candidate_jar_sha256": candidate_sha256.lower(),
            "strict_matrix_report_id": matrix["report_id"],
            **result,
        }
        report_id = hashlib.sha256(json.dumps(
            core, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest().upper()[:20]
        return {"report_id": "CLINITFINALS_" + report_id, **core}
    except (ClassMethodMatrixError, BytecodeProfileError,
            OSError, ValueError, KeyError, IndexError):
        raise FinalInitializerFrontierError(
            "CLINIT_OR_JAR_EVIDENCE_UNEVALUABLE"
        ) from None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("candidate_jar", type=Path)
    p.add_argument("class_entry")
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    p.add_argument("--out", type=Path, help="Private exclusive-create JSON")
    args = p.parse_args(argv)
    try:
        report = build_final_initializer_frontier(
            args.original_jar, args.candidate_jar,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
            class_entry=args.class_entry,
        )
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, sort_keys=True)
                stream.write("\n")
        print(json.dumps({
            "report_id": report["report_id"],
            "original_final_fields_without_constantvalue":
                report["original_final_fields_without_constantvalue"],
            "type_counts": report["type_counts"],
            "candidate_status_counts": report["candidate_status_counts"],
            "runtime_initializer_equivalence_certified": False,
        }, sort_keys=True))
        return 0
    except FinalInitializerFrontierError as exc:
        p.error(str(exc))
    except (OSError, ValueError):
        p.error("CLINIT_FRONTIER_FAILED")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
