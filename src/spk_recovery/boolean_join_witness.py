"""Research-only proof of short, branch-joined boolean stores in JVM <clinit>.

This verifies the *two possible values and local edges*, not the predicate,
the complete initializer, reconstructed Java, or runtime equivalence.
Never print original class/member names or bytecode coordinates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _clinit, _digest, _fields, _instructions,
)
from .source_class_method_matrix import (
    ClassMethodMatrixError, build_class_method_matrix,
)


class BooleanJoinWitnessError(ValueError):
    """Insufficient evidence for an exact conditional boolean store."""


_CONDITIONS = {f"0x{x:02x}" for x in (*range(0x99, 0xa7), 0xc6, 0xc7)}
_JUMPS = {"0xa7", "0xc8"}
_PIN = re.compile(r"[0-9a-fA-F]{64}\Z")


def _require(ok: bool, code: str) -> None:
    if not ok:
        raise BooleanJoinWitnessError(code)


def _edges(rows: list[dict]) -> list[tuple[int, int]]:
    """Validate all explicit branch targets before inferring local CFG edges."""
    offsets = {r["offset"] for r in rows}
    result = []
    for row in rows:
        targets = []
        if "branch_target_offset" in row:
            targets.append(row["branch_target_offset"])
        if "switch_default_target_offset" in row:
            targets.append(row["switch_default_target_offset"])
        if "switch_targets" in row:
            _require(isinstance(row["switch_targets"], list),
                     "INVALID_SWITCH_TARGETS")
            targets.extend(row["switch_targets"])
        if "switch_pairs" in row:
            _require(isinstance(row["switch_pairs"], list),
                     "INVALID_SWITCH_PAIRS")
            for pair in row["switch_pairs"]:
                _require(isinstance(pair, (tuple, list)) and len(pair) == 2,
                         "INVALID_SWITCH_PAIR")
                targets.append(pair[1])
        for target in targets:
            _require(type(target) is int and target in offsets,
                     "INVALID_BRANCH_TARGET")
            result.append((row["offset"], target))
    return result


def _literal(row: dict) -> int | None:
    if row.get("opcode") == "0x03":
        return 0
    if row.get("opcode") == "0x04":
        return 1
    return None


def _diamond(
    rows: list[dict], index: int, edges: list[tuple[int, int]],
    handlers: list[dict],
) -> dict | None:
    """Only accept contiguous condition/value/goto/value/store diamonds."""
    if index < 4:
        return None
    cond, first, jump, second, store = rows[index - 4:index + 1]
    window = (cond, first, jump, second, store)
    if any(a["offset"] + a["length"] != b["offset"]
           for a, b in zip(window, window[1:])):
        return None
    if cond.get("opcode") not in _CONDITIONS or jump.get("opcode") not in _JUMPS:
        return None
    if cond.get("branch_target_offset") != second["offset"]:
        return None
    if jump.get("branch_target_offset") != store["offset"]:
        return None
    fallthrough, taken = _literal(first), _literal(second)
    if fallthrough is None or taken is None or fallthrough == taken:
        return None
    allowed = {(cond["offset"], second["offset"]),
               (jump["offset"], store["offset"])}
    inside = {r["offset"] for r in window}
    if any(target in inside and (source, target) not in allowed
           for source, target in edges):
        return None
    _require(isinstance(handlers, list), "INVALID_EXCEPTION_TABLE")
    for handler in handlers:
        _require(isinstance(handler, dict)
                 and all(type(handler.get(k)) is int
                         for k in ("start_pc", "end_pc", "handler_pc")),
                 "INVALID_EXCEPTION_HANDLER")
        if (handler["handler_pc"] in inside
                or any(handler["start_pc"] <= offset < handler["end_pc"]
                       for offset in inside)):
            return None
    return {
        "store_offset": store["offset"],
        "condition_offset": cond["offset"],
        "condition_opcode": cond["opcode"],
        "fallthrough_value": bool(fallthrough),
        "branch_taken_value": bool(taken),
        "condition_source_recovered": False,
        "java_expression_reconstructed": False,
    }


def plan_conditional_boolean_witnesses(original: dict, candidate: dict) -> dict:
    """Find exact local boolean diamonds; do not infer a Java expression."""
    owner = original.get("internal_name")
    _require(type(owner) is str and owner
             and owner == candidate.get("internal_name"),
             "CLASS_OWNER_UNVERIFIED")
    old, new = _fields(original), _fields(candidate)
    mutable = {
        key: field for key, field in old.items()
        if field["access"] == 0x0009 and key[1] == "Z"
        and field["signature"] is None and field["constant_value"] is None
    }
    _require(bool(mutable), "NO_MUTABLE_BOOLEAN_DECLARATIONS")
    init = _clinit(original, required=True)
    rows = _instructions(init)
    _require(bool(rows), "EMPTY_ORIGINAL_CLINIT")
    edges = _edges(rows)
    targeted = {t for _, t in edges}
    handlers = init.get("exception_handlers")
    _require(isinstance(handlers, list), "EXCEPTION_TABLE_MISSING")
    cand_init = _clinit(candidate, required=False)
    candidate_writes = set()
    if cand_init:
        candidate_writes = {
            (r.get("name"), r.get("descriptor"))
            for r in _instructions(cand_init)
            if r.get("opcode") == "0xb3" and r.get("owner") == owner
        }

    seen = set()
    joined = 0
    witnesses = []
    for i, row in enumerate(rows):
        if row.get("opcode") != "0xb3" or row.get("owner") != owner:
            continue
        key = row.get("name"), row.get("descriptor")
        if key not in mutable:
            continue
        _require(key not in seen, "DUPLICATE_ORIGINAL_BOOLEAN_STORE")
        seen.add(key)
        if row["offset"] not in targeted:
            continue
        joined += 1
        counterpart = new.get(key)
        _require(counterpart is not None
                 and all(counterpart.get(k) == mutable[key].get(k)
                         for k in ("access", "signature", "constant_value")),
                 "CANDIDATE_BOOLEAN_FIELD_METADATA_DRIFT")
        shape = _diamond(rows, i, edges, handlers)
        if shape is None:
            continue
        _require(key not in candidate_writes,
                 "CANDIDATE_BOOLEAN_JOIN_ALREADY_INITIALIZED")
        shape["field_name"] = key[0]
        witnesses.append(shape)

    return {
        "conditional_boolean_stores_examined": joined,
        "short_diamond_witnesses": len(witnesses),
        "unresolved_conditional_boolean_stores": joined - len(witnesses),
        "private_witnesses": witnesses,
        "conditional_boolean_value_pairs_verified_locally":
            len(witnesses) > 0,
        "original_predicate_source_recovered": False,
        "standalone_java_assignment_reconstructed": False,
        "whole_clinit_equivalence_certified": False,
        "runtime_equivalence_certified": False,
        "canonical_identifiers_accepted": False,
    }


def build_private_boolean_join_witness(
    original_jar: Path, candidate_jar: Path, class_entry: str,
    out_root: Path, *, original_sha256: str, candidate_sha256: str,
) -> dict:
    """Pinned local replay, private detail file and aggregate-only stdout."""
    orig, cand, out = map(Path, (original_jar, candidate_jar, out_root))
    _require(not out.exists() and not out.is_symlink(),
             "WITNESS_OUTPUT_ALREADY_EXISTS")
    for path, pin in ((orig, original_sha256), (cand, candidate_sha256)):
        _require(type(pin) is str and _PIN.fullmatch(pin) is not None,
                 "INVALID_COMPLETE_JAR_SHA256")
        _require(path.is_file() and not path.is_symlink(),
                 "INPUT_JAR_MISSING_OR_SYMLINK")
        _require(_digest(path) == pin.lower(), "INPUT_JAR_SHA256_MISMATCH")
    _require(type(class_entry) is str and class_entry.endswith(".class")
             and not class_entry.startswith("/") and "\\" not in class_entry
             and all(p not in ("", ".", "..") and ":" not in p
                     for p in class_entry.split("/")),
             "INVALID_PRIVATE_CLASS_ENTRY")
    try:
        matrix = build_class_method_matrix(
            orig, cand, original_sha256=original_sha256,
            candidate_sha256=candidate_sha256, class_entry=class_entry,
        )
        _require(matrix.get("research_only") is True
                 and matrix.get("source_equivalence_certified") is False
                 and matrix.get("canonical_identity_accepted") is False,
                 "UNEXPECTED_MATRIX_AUTHORITY")
        result = plan_conditional_boolean_witnesses(
            profile_jar_class(orig, class_entry),
            profile_jar_class(cand, class_entry),
        )
    except (BytecodeProfileError, ClassMethodMatrixError,
            ScalarInitializerRecoveryError):
        raise BooleanJoinWitnessError("BOOLEAN_JOIN_EVIDENCE_UNEVALUABLE") from None
    for path, pin in ((orig, original_sha256), (cand, candidate_sha256)):
        _require(_digest(path) == pin.lower(), "INPUT_JAR_CHANGED_DURING_PROOF")
    detail = result.pop("private_witnesses")
    report = {
        "schema_version": 1,
        "kind": "private_original_jvm_boolean_join_witness",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "candidate_complete_jar_sha256": candidate_sha256.lower(),
        "strict_matrix_report_id": matrix["report_id"],
        **result,
        "private_detail_sha256": hashlib.sha256(
            json.dumps(detail, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "original-boolean-join-private.json").open(
        "x", encoding="utf-8"
    ) as f:
        json.dump(detail, f, indent=2, sort_keys=True)
        f.write("\n")
    with (out / "boolean-join-aggregate.json").open(
        "x", encoding="utf-8"
    ) as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    return report


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
        print(json.dumps(build_private_boolean_join_witness(
            args.original_jar, args.candidate_jar, args.class_entry,
            args.output_root, original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
        ), sort_keys=True))
    except BooleanJoinWitnessError as exc:
        parser.error(str(exc))
    except (OSError, ValueError):
        parser.error("BOOLEAN_JOIN_PROOF_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
