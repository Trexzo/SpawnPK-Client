"""Stage narrowly proved JVM boolean predicate source *forms* privately.

Only pure getstatic reference equality and boolean negation producers with an
R50-certified local branch diamond qualify. Exact candidate Java expressions
are NOT proof of original authorial source, initializer order or runtime parity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from .boolean_join_witness import (
    BooleanJoinWitnessError, _edges, plan_conditional_boolean_witnesses,
)
from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _clinit, _digest, _instructions,
)
from .source_class_method_matrix import (
    ClassMethodMatrixError, build_class_method_matrix,
)


class PredicateSourceFormError(ValueError):
    """Cannot prove a supported exact original JVM predicate source form."""


_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")
_PIN = re.compile(r"[0-9a-fA-F]{64}\Z")


def _require(value: bool, reason: str) -> None:
    if not value:
        raise PredicateSourceFormError(reason)


def _name(row: dict, current_owner: str) -> str | None:
    """Private Java-friendly static field text; never displayed publicly."""
    owner, field = row.get("owner"), row.get("name")
    if not (type(owner) is str and owner
            and type(field) is str and _IDENTIFIER.fullmatch(field)):
        return None
    if owner == current_owner:
        return field
    parts = owner.split("/")
    if not parts or any(not _IDENTIFIER.fullmatch(p) for p in parts):
        return None
    return ".".join(parts) + "." + field


def _input_field(row: dict) -> bool:
    return (
        row.get("opcode") == "0xb2"
        and type(row.get("owner")) is str
        and type(row.get("name")) is str
        and type(row.get("descriptor")) is str
    )


def _exact_predicate_form(
    rows: list[dict], condition_offset: int, owner: str,
    incoming_edges: list[tuple[int, int]], handlers: list[dict],
    *, fallthrough: bool, branch_taken: bool,
) -> dict | None:
    positions = {r["offset"]: i for i, r in enumerate(rows)}
    if condition_offset not in positions:
        return None
    index = positions[condition_offset]
    cond = rows[index]
    op = cond.get("opcode")
    if (fallthrough, branch_taken) != (True, False):
        return None
    if op == "0xa6":  # if_acmpne: getstatic A; getstatic B; store (A == B)
        n = 2
        kind = "reference_identity_equality"
    elif op == "0x9a":  # ifne: getstatic boolean; store (!boolean)
        n = 1
        kind = "boolean_negation"
    else:
        return None
    if index < n:
        return None
    loads = rows[index - n:index]
    if any(not _input_field(r) for r in loads):
        return None
    if any(a["offset"] + a["length"] != b["offset"]
           for a, b in zip(loads + [cond], (loads + [cond])[1:])):
        return None
    load_offsets = {r["offset"] for r in loads}
    if any(target in load_offsets for _, target in incoming_edges):
        return None
    if any(
        handler["handler_pc"] in load_offsets
        or any(handler["start_pc"] <= offset < handler["end_pc"]
               for offset in load_offsets)
        for handler in handlers
    ):
        return None
    names = [_name(row, owner) for row in loads]
    if any(name is None for name in names):
        return None
    if kind == "reference_identity_equality":
        a, b = (x.get("descriptor") for x in loads)
        if a != b or not (a.startswith("L") and a.endswith(";")
                            or a.startswith("[")):
            return None
        expression = f"({names[0]} == {names[1]})"
    else:
        if loads[0]["descriptor"] != "Z":
            return None
        expression = f"(!{names[0]})"
    return {
        "kind": kind,
        "expression": expression,
        "input_static_field_count": n,
        "original_condition_offset": condition_offset,
        "predicate_operand_semantics_verified": True,
        "private_source_compiled_against_original_dependencies": False,
    }


def plan_exact_boolean_predicate_forms(original: dict, candidate: dict) -> dict:
    """Return private source forms; never synthesize unsupported expressions."""
    owner = original.get("internal_name")
    _require(type(owner) is str and owner, "ORIGINAL_OWNER_UNAVAILABLE")
    prior = plan_conditional_boolean_witnesses(original, candidate)
    init = _clinit(original, required=True)
    rows = _instructions(init)
    edges = _edges(rows)
    handlers = init.get("exception_handlers")
    _require(isinstance(handlers, list), "EXCEPTION_TABLE_UNAVAILABLE")
    recovered = []
    for witness in prior["private_witnesses"]:
        field = witness["field_name"]
        _require(_IDENTIFIER.fullmatch(field) is not None,
                 "UNREPRESENTABLE_SOURCE_FIELD_NAME")
        shape = _exact_predicate_form(
            rows, witness["condition_offset"], owner, edges, handlers,
            fallthrough=witness["fallthrough_value"],
            branch_taken=witness["branch_taken_value"],
        )
        if shape is not None:
            recovered.append({
                "original_store_offset": witness["store_offset"],
                "field_name": field,
                **shape,
            })
    recovered.sort(key=lambda x: x["original_store_offset"])
    snippet = (
        "// PRIVATE JVM-derived predicate forms, not complete <clinit>.\n"
        "// Original predicate operands preserved; source equivalence pending.\n"
        "static {\n"
        + "".join(
            f"    {row['field_name']} = {row['expression']};\n"
            for row in recovered
        )
        + "}\n"
    )
    return {
        "private_java_fragment": snippet,
        "private_source_rows": recovered,
        "exact_join_witnesses": prior["short_diamond_witnesses"],
        "candidate_predicate_expressions_staged": len(recovered),
        "unproven_predicate_forms":
            prior["short_diamond_witnesses"] - len(recovered),
        "expression_type_counts": {
            k: sum(r["kind"] == k for r in recovered)
            for k in ("reference_identity_equality", "boolean_negation")
        },
        "original_static_initializer_complete": False,
        "original_authorial_java_source_certified": False,
        "jvm_classfile_parity_certified": False,
        "private_source_compiled_against_original_dependencies": False,
        "canonical_identity_accepted": False,
        "runtime_equivalence_certified": False,
    }


def build_private_boolean_predicate_source(
    original_jar: Path, candidate_jar: Path, class_entry: str,
    output_root: Path, *, original_sha256: str, candidate_sha256: str,
) -> dict:
    orig, cand, out = map(Path, (original_jar, candidate_jar, output_root))
    _require(not out.exists() and not out.is_symlink(),
             "PREDICATE_SOURCE_OUTPUT_ALREADY_EXISTS")
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
            orig, cand,
            original_sha256=original_sha256,
            candidate_sha256=candidate_sha256,
            class_entry=class_entry,
        )
        _require(matrix.get("research_only") is True
                 and matrix.get("source_equivalence_certified") is False
                 and matrix.get("canonical_identity_accepted") is False,
                 "UNEXPECTED_MATRIX_AUTHORITY")
        plan = plan_exact_boolean_predicate_forms(
            profile_jar_class(orig, class_entry),
            profile_jar_class(cand, class_entry),
        )
    except (BooleanJoinWitnessError, BytecodeProfileError,
            ClassMethodMatrixError, ScalarInitializerRecoveryError):
        raise PredicateSourceFormError("PREDICATE_EVIDENCE_UNEVALUABLE") from None
    for path, pin in ((orig, original_sha256), (cand, candidate_sha256)):
        _require(_digest(path) == pin.lower(), "INPUT_JAR_CHANGED_DURING_PROOF")
    snippet = plan.pop("private_java_fragment")
    details = plan.pop("private_source_rows")
    report = {
        "schema_version": 1,
        "kind": "private_jvm_derived_boolean_predicate_java_forms",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "candidate_complete_jar_sha256": candidate_sha256.lower(),
        "matrix_report_id": matrix["report_id"],
        "private_fragment_sha256":
            hashlib.sha256(snippet.encode("utf-8")).hexdigest(),
        **plan,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "boolean-predicate-source.private.txt").open(
        "x", encoding="utf-8", newline="\n"
    ) as f:
        f.write(snippet)
    with (out / "boolean-predicate-rows.private.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as f:
        json.dump(details, f, sort_keys=True, indent=2)
        f.write("\n")
    with (out / "boolean-predicate-aggregate.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as f:
        json.dump(report, f, sort_keys=True, indent=2)
        f.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("candidate_jar", type=Path)
    p.add_argument("class_entry")
    p.add_argument("output_root", type=Path)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    args = p.parse_args(argv)
    try:
        print(json.dumps(build_private_boolean_predicate_source(
            args.original_jar, args.candidate_jar,
            args.class_entry, args.output_root,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
        ), sort_keys=True))
    except PredicateSourceFormError as exc:
        p.error(str(exc))
    except (OSError, ValueError):
        p.error("BOOLEAN_PREDICATE_SOURCE_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
