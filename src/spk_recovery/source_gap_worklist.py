"""Prioritize *measured* private recovered-Java gaps without publishing JVM names.

Reads two SHA-256-pinned JARs and reuses the complete R31/R32/R35/R36
method, field, frame and class-header verifier. Never accepts lineage or
claims generated Java is a functional replacement for the original client.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .source_class_method_matrix import (
    ClassMethodMatrixError, _private_stable_id, build_class_method_matrix,
)


class SourceGapWorklistError(ValueError):
    """A strict source gap cannot be derived from the supplied inputs."""


def _require(value: bool, code: str) -> None:
    if not value:
        raise SourceGapWorklistError(code)


def _field_id(original_sha: str, name: str, descriptor: str) -> str:
    return "FIELD_" + hashlib.sha256(json.dumps(
        [original_sha, name, descriptor], separators=(",", ":")
    ).encode("utf-8")).hexdigest().upper()[:20]


def _method_inventory(profile: dict) -> dict[tuple[str, str], dict]:
    methods = profile.get("methods")
    _require(isinstance(methods, list), "INVALID_METHOD_INVENTORY")
    out = {}
    for row in methods:
        _require(isinstance(row, dict), "INVALID_METHOD_INVENTORY")
        key = row.get("name"), row.get("descriptor")
        _require(
            all(isinstance(x, str) and x for x in key) and key not in out,
            "INVALID_OR_DUPLICATE_METHOD",
        )
        out[key] = row
    return out


def _references(
    methods: dict[tuple[str, str], dict],
    owner: str,
    declared_fields: set[tuple[str, str]],
) -> tuple[
    dict[tuple[str, str], list[tuple[str, str, str]]],
    dict[tuple[str, str], int],
]:
    accesses = {}
    incoming = {key: 0 for key in methods}
    for key, row in methods.items():
        raw = row.get("field_accesses")
        inv = row.get("method_invocations")
        _require(isinstance(raw, list) and isinstance(inv, list),
                 "FIELD_OR_CALLSITE_EVIDENCE_MISSING")
        local = []
        for access in raw:
            _require(isinstance(access, dict), "FIELD_REFERENT_INVALID")
            operation = access.get("operation")
            _require(operation in ("getstatic", "putstatic", "getfield", "putfield"),
                     "UNKNOWN_FIELD_ACCESS_OPERATION")
            for attr in ("owner", "name", "descriptor"):
                _require(isinstance(access.get(attr), str) and access[attr],
                         "FIELD_REFERENT_INVALID")
            member = (access["name"], access["descriptor"])
            if access["owner"] == owner and member in declared_fields:
                local.append((operation, *member))
        accesses[key] = local
        for invoke in inv:
            _require(isinstance(invoke, dict), "METHOD_CALLSITE_INVALID")
            if invoke.get("owner") == owner:
                target = invoke.get("name"), invoke.get("descriptor")
                if target in incoming:
                    incoming[target] += 1
    return accesses, incoming


def compare_source_gap_profiles(
    original: dict, candidate: dict, matrix: dict, *,
    original_sha256: str,
) -> dict[str, Any]:
    """Classify gap dependencies and order recovery tasks by measurable leverage.

    Priority is a deterministic *heuristic* (missing-field dependencies,
    inbound owner callsites, original bytecode length), not a semantic
    importance verdict and never acceptance authority.
    """
    _require(isinstance(matrix, dict), "STRICT_MATRIX_MISSING")
    _require(matrix.get("research_only") is True
             and matrix.get("source_equivalence_certified") is False
             and matrix.get("canonical_identity_accepted") is False,
             "STRICT_MATRIX_AUTHORITY_UNEXPECTED")
    owner = original.get("internal_name")
    _require(isinstance(owner, str) and owner and owner == candidate.get("internal_name"),
             "NO_ACCEPTED_OWNER_ALIAS")
    _require(isinstance(original_sha256, str) and len(original_sha256) == 64,
             "ORIGINAL_SHA256_MISSING")
    a = _method_inventory(original)
    b = _method_inventory(candidate)
    expected_method_rows = matrix.get("method_rows")
    _require(isinstance(expected_method_rows, list), "METHOD_MATRIX_ROWS_MISSING")
    method_state = {row["method_id"]: row["classification"]
                    for row in expected_method_rows}
    _require(len(method_state) == len(expected_method_rows),
             "DUPLICATE_OPAQUE_METHOD_ID")
    declared = original.get("fields")
    _require(isinstance(declared, list), "ORIGINAL_FIELD_INVENTORY_MISSING")
    field_keys = {(f["name"], f["descriptor"]) for f in declared}
    _require(len(field_keys) == len(declared), "DUPLICATE_ORIGINAL_FIELD")
    field_rows = matrix.get("field_rows")
    _require(isinstance(field_rows, list), "FIELD_MATRIX_ROWS_MISSING")
    field_state = {f["field_id"]: f["classification"] for f in field_rows}
    _require(len(field_state) == len(field_rows), "DUPLICATE_OPAQUE_FIELD_ID")
    gaps = {"missing_field", "shared_metadata_difference"}
    open_fields = {
        key for key in field_keys
        if field_state.get(_field_id(original_sha256, *key)) in gaps
    }
    missing_fields = {
        key for key in field_keys
        if field_state.get(_field_id(original_sha256, *key)) == "missing_field"
    }
    _require(len(missing_fields) == matrix["field_counts"]["missing_field"],
             "FIELD_GAP_MATRIX_DISAGREES")

    owner_accesses, incoming = _references(a, owner, field_keys)
    method_tasks = []
    touched_fields = set()
    for key, old in a.items():
        method_id = _private_stable_id(original_sha256, *key)
        state = method_state.get(method_id)
        _require(state is not None, "METHOD_GAP_MATRIX_DISAGREES")
        if state not in ("missing_method", "body_difference", "candidate_has_no_code"):
            continue
        _require(old.get("code_length") is not None,
                 "GAP_HAS_NO_ORIGINAL_METHOD_BODY")
        access = owner_accesses[key]
        missing_refs = [
            (operation, name, descriptor) for operation, name, descriptor in access
            if (name, descriptor) in missing_fields
        ]
        affected = sorted({
            _field_id(original_sha256, name, descriptor)
            for _, name, descriptor in access if (name, descriptor) in open_fields
        })
        touched_fields.update(affected)
        _require(type(old["code_length"]) is int and old["code_length"] >= 0,
                 "INVALID_ORIGINAL_CODE_LENGTH")
        method_tasks.append({
            "method_id": method_id,
            "classification": state,
            "original_code_bytes": old["code_length"],
            "incoming_same_owner_calls": incoming[key],
            "missing_field_reference_sites": len(missing_refs),
            "missing_field_dependencies": len({
                (name, descriptor) for _, name, descriptor in missing_refs
            }),
            "original_local_field_reference_sites": len(access),
            "affected_missing_or_changed_field_ids": affected,
            "candidate_method_declared": key in b,
            "method_semantics_recovered": False,
        })

    method_tasks.sort(key=lambda row: (
        -row["missing_field_dependencies"],
        -row["incoming_same_owner_calls"],
        -row["original_code_bytes"],
        row["method_id"],
    ))
    for index, task in enumerate(method_tasks, 1):
        task["suggested_review_order"] = index

    _require(
        len(method_tasks)
        == (matrix["counts"]["missing_method"]
            + matrix["counts"]["body_difference"]
            + matrix["counts"]["candidate_has_no_code"]),
        "METHOD_GAP_TOTAL_DISAGREES",
    )
    field_work = []
    field_usage = {field: {"read_sites": 0, "write_sites": 0,
                           "referencing_methods": set()}
                   for field in open_fields}
    for method_key, accessed in owner_accesses.items():
        for operation, name, descriptor in accessed:
            field = name, descriptor
            if field not in field_usage:
                continue
            value = field_usage[field]
            value["read_sites" if operation.startswith("get")
                  else "write_sites"] += 1
            value["referencing_methods"].add(
                _private_stable_id(original_sha256, *method_key)
            )
    for name, descriptor in open_fields:
        usage = field_usage[name, descriptor]
        field_work.append({
            "field_id": _field_id(original_sha256, name, descriptor),
            "classification": field_state[_field_id(original_sha256, name, descriptor)],
            "read_sites": usage["read_sites"],
            "write_sites": usage["write_sites"],
            "referencing_method_count": len(usage["referencing_methods"]),
        })
    field_work.sort(key=lambda row: (
        -row["referencing_method_count"],
        -(row["read_sites"] + row["write_sites"]),
        row["field_id"],
    ))
    core = {
        "schema_version": 1,
        "kind": "private_source_reconstruction_gap_worklist",
        "research_only": True,
        "source_equivalence_certified": False,
        "canonical_identity_accepted": False,
        "automatic_recovery_performed": False,
        "worklist_priority_is_heuristic_only": True,
        "strict_matrix_report_id": matrix["report_id"],
        "original_declared_methods": matrix["original_declared_method_count"],
        "candidate_declared_methods": matrix["candidate_declared_method_count"],
        "original_declared_fields": matrix["original_declared_field_count"],
        "candidate_declared_fields": matrix["candidate_declared_field_count"],
        "method_gap_count": len(method_tasks),
        "missing_field_count": len(missing_fields),
        "changed_field_metadata_count":
            matrix["field_counts"]["shared_metadata_difference"],
        "referenced_gap_field_count": len({
            (n, d) for (n, d), usage in field_usage.items()
            if usage["referencing_methods"]
        }),
        "method_worklist": method_tasks,
        "field_worklist": field_work,
    }
    report_id = hashlib.sha256(json.dumps(
        core, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest().upper()[:20]
    return {"report_id": "SOURCEGAPS_" + report_id, **core}


def build_source_gap_worklist(
    original_jar: Path, candidate_jar: Path, *,
    original_sha256: str, candidate_sha256: str, class_entry: str,
) -> dict[str, Any]:
    try:
        matrix = build_class_method_matrix(
            original_jar, candidate_jar,
            original_sha256=original_sha256,
            candidate_sha256=candidate_sha256,
            class_entry=class_entry,
        )
        original = profile_jar_class(Path(original_jar), class_entry)
        candidate = profile_jar_class(Path(candidate_jar), class_entry)
        result = compare_source_gap_profiles(
            original, candidate, matrix,
            original_sha256=original_sha256.lower(),
        )
        # The shared strict matrix already checks complete input JAR pins,
        # but a later reparse must never trust mutable original inputs.
        h = hashlib.sha256()
        for path, expected in ((original_jar, original_sha256),
                               (candidate_jar, candidate_sha256)):
            h = hashlib.sha256()
            with Path(path).open("rb") as src:
                for part in iter(lambda: src.read(1024 * 1024), b""):
                    h.update(part)
            _require(h.hexdigest() == expected.lower(),
                     "INPUT_CHANGED_AFTER_MATRIX")
        return result
    except (ClassMethodMatrixError, BytecodeProfileError, OSError, KeyError, ValueError):
        raise SourceGapWorklistError("SOURCE_GAP_INPUT_OR_MATRIX_INVALID") from None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("candidate_jar", type=Path)
    p.add_argument("class_entry")
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    p.add_argument("--out", type=Path, help="Private JSON output (exclusive-create)")
    args = p.parse_args(argv)
    try:
        result = build_source_gap_worklist(
            args.original_jar, args.candidate_jar,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
            class_entry=args.class_entry,
        )
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as target:
                json.dump(result, target, sort_keys=True, indent=2)
                target.write("\n")
        print(json.dumps({
            "report_id": result["report_id"],
            "method_gap_count": result["method_gap_count"],
            "missing_field_count": result["missing_field_count"],
            "changed_field_metadata_count": result["changed_field_metadata_count"],
            "referenced_gap_field_count": result["referenced_gap_field_count"],
            "source_equivalence_certified": False,
        }, sort_keys=True))
    except SourceGapWorklistError as exc:
        p.error(str(exc))
    except (OSError, ValueError):
        p.error("SOURCE_GAP_REPLAY_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
