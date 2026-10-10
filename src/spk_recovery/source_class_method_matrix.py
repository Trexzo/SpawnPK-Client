"""Class-wide method-body research matrix for separately compiled Java candidates.

Runs only on local SHA-256-pinned JARs. This does NOT compare entire classes,
infer cross-build aliases, accept mappings or certify recovered source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any
from zipfile import ZipFile, BadZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .source_method_parity import MethodParityError, compare_profiles


class ClassMethodMatrixError(ValueError):
    """Unreliable or malformed evidence must never report source parity."""


def _require(ok: bool, code: str) -> None:
    if not ok:
        raise ClassMethodMatrixError(code)


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _preflight(path: Path, expected: str, class_entry: str) -> str:
    _require(
        isinstance(expected, str) and re.fullmatch(r"[0-9a-fA-F]{64}", expected) is not None,
        "INVALID_JAR_SHA256_PIN",
    )
    _require(path.is_file(), "JAR_NOT_FOUND")
    measured = _digest(path)
    _require(measured.lower() == expected.lower(), "JAR_SHA256_MISMATCH")
    with ZipFile(path) as archive:
        count = sum(x.filename == class_entry and not x.is_dir()
                    for x in archive.infolist())
        _require(count == 1, "MISSING_OR_DUPLICATE_CLASS")
    return measured


def _methods(profile: dict) -> dict[tuple[str, str], dict]:
    rows = profile.get("methods")
    _require(isinstance(rows, list), "MALFORMED_METHOD_INVENTORY")
    result = {}
    for row in rows:
        _require(isinstance(row, dict), "MALFORMED_METHOD_INVENTORY")
        key = (row.get("name"), row.get("descriptor"))
        _require(
            all(isinstance(value, str) and value for value in key)
            and key not in result,
            "DUPLICATE_OR_INVALID_METHOD_DECLARATION",
        )
        result[key] = row
    return result


def _fields(profile: dict) -> dict[tuple[str, str], dict]:
    rows = profile.get("fields")
    _require(isinstance(rows, list), "FIELD_INVENTORY_MISSING")
    result: dict[tuple[str, str], dict] = {}
    for row in rows:
        _require(isinstance(row, dict), "INVALID_FIELD_DECLARATION")
        name, descriptor = row.get("name"), row.get("descriptor")
        _require(
            isinstance(name, str) and bool(name)
            and isinstance(descriptor, str) and bool(descriptor)
            and (name, descriptor) not in result,
            "INVALID_OR_DUPLICATE_FIELD_DECLARATION",
        )
        _require(
            type(row.get("access")) is int and 0 <= row["access"] <= 65535,
            "INVALID_FIELD_ACCESS",
        )
        _require(
            row.get("signature") is None or isinstance(row.get("signature"), str),
            "INVALID_FIELD_SIGNATURE",
        )
        _require("constant_value" in row, "MISSING_FIELD_CONSTANT_EVIDENCE")
        result[(name, descriptor)] = row
    return result


def _field_constant(value: Any) -> Any:
    if isinstance(value, float):
        # Source class profiles currently expose parsed IEEE values, not
        # original field ConstantValue raw payloads. Distinguish signed zero;
        # reject NaN because payload bits could differ without being visible.
        _require(not math.isnan(value), "UNSAFE_NAN_CONSTANT_VALUE")
        return {"type": "float", "hex": value.hex()}
    _require(
        value is None or type(value) in (int, str),
        "UNSUPPORTED_FIELD_CONSTANT_VALUE",
    )
    return value


def _field_metadata(field: dict) -> dict[str, Any]:
    return {
        "access": field["access"],
        "signature": field.get("signature"),
        "constant": _field_constant(field["constant_value"]),
    }


def _compare_fields(
    original: dict, candidate: dict, *, original_sha: str,
) -> dict[str, Any]:
    a, b = _fields(original), _fields(candidate)
    counts = {
        "shared_exact": 0,
        "shared_metadata_difference": 0,
        "missing_field": 0,
        "extra_field": 0,
    }
    details = []
    for name, descriptor in sorted(a.keys() | b.keys()):
        old, new = a.get((name, descriptor)), b.get((name, descriptor))
        if old is None:
            state = "extra_field"
        elif new is None:
            state = "missing_field"
        else:
            state = (
                "shared_exact"
                if _field_metadata(old) == _field_metadata(new)
                else "shared_metadata_difference"
            )
        counts[state] += 1
        opaque_id = "FIELD_" + hashlib.sha256(json.dumps(
            [original_sha, name, descriptor], separators=(",", ":")
        ).encode("utf-8")).hexdigest().upper()[:20]
        details.append({"field_id": opaque_id, "classification": state})
    return {
        "original_declared_field_count": len(a),
        "candidate_declared_field_count": len(b),
        "field_counts": counts,
        "field_inventory_exact": (
            len(a) == len(b) and counts["shared_exact"] == len(a)
        ),
        "field_rows": sorted(details, key=lambda d: d["field_id"]),
    }


def _private_stable_id(original_sha: str, name: str, descriptor: str) -> str:
    payload = json.dumps([original_sha, name, descriptor], separators=(",", ":"))
    return "METHOD_" + hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()[:20]


def compare_class_method_profiles(original: dict, rebuilt: dict, *, original_sha: str) -> dict[str, Any]:
    _require(
        original.get("internal_name") == rebuilt.get("internal_name"),
        "NO_ACCEPTED_OWNER_ALIAS",
    )
    a, b = _methods(original), _methods(rebuilt)
    fields = _compare_fields(original, rebuilt, original_sha=original_sha)
    counts = {
        "instruction_parity": 0,
        "body_difference": 0,
        "missing_method": 0,
        "extra_method": 0,
        "no_original_code": 0,
        "candidate_has_no_code": 0,
    }
    rows = []
    for name, descriptor in sorted(a.keys() | b.keys()):
        method_id = _private_stable_id(original_sha, name, descriptor)
        orig, cand = a.get((name, descriptor)), b.get((name, descriptor))
        checks: dict[str, bool] | None = None
        if orig is None:
            state = "extra_method"
        elif cand is None:
            state = "missing_method"
        elif orig.get("code_length") is None:
            state = "no_original_code"
        elif cand.get("code_length") is None:
            state = "candidate_has_no_code"
        else:
            try:
                evidence = compare_profiles(original, rebuilt, name, descriptor)
            except MethodParityError as exc:
                # Incomplete CP, bootstrap, Code or StackMapTable evidence
                # invalidates this entire batch; never silently skip a row.
                raise ClassMethodMatrixError("NON_EVALUABLE_METHOD_BODY") from None
            checks = evidence["checks"]
            state = (
                "instruction_parity"
                if evidence["classification"] == "CANDIDATE_INSTRUCTION_PARITY"
                else "body_difference"
            )
        counts[state] += 1
        row = {"method_id": method_id, "classification": state}
        if checks is not None:
            row["checks"] = checks
        rows.append(row)
    core = {
        "schema_version": 1,
        "kind": "private_source_class_method_matrix",
        "research_only": True,
        "canonical_identity_accepted": False,
        "source_equivalence_certified": False,
        "whole_class_equivalence_certified": False,
        "other_code_subattributes_and_runtime_unverified": True,
        "original_declared_method_count": len(a),
        "candidate_declared_method_count": len(b),
        "class_signature_exact": (
            original.get("signature") == rebuilt.get("signature")
        ),
        **fields,
        "counts": counts,
        "all_method_bodies_instruction_parity": (
            bool(a)
            and len(a) == len(b)
            and counts["instruction_parity"] == len(a)
        ),
        "method_rows": sorted(rows, key=lambda x: x["method_id"]),
    }
    report_id = hashlib.sha256(json.dumps(
        core, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest().upper()[:20]
    return {"report_id": "CLASSMETHOD_" + report_id, **core}


def build_class_method_matrix(
    original_jar: Path, candidate_jar: Path, *,
    original_sha256: str, candidate_sha256: str, class_entry: str,
) -> dict[str, Any]:
    _require(
        isinstance(class_entry, str)
        and class_entry.endswith(".class")
        and not class_entry.startswith("/")
        and "\\" not in class_entry
        and all(s and s not in (".", "..") and ":" not in s for s in class_entry.split("/")),
        "INVALID_CLASS_ENTRY",
    )
    original_jar, candidate_jar = Path(original_jar), Path(candidate_jar)
    try:
        original_sha = _preflight(original_jar, original_sha256, class_entry)
        _preflight(candidate_jar, candidate_sha256, class_entry)
        old = profile_jar_class(original_jar, class_entry)
        new = profile_jar_class(candidate_jar, class_entry)
    except (OSError, BadZipFile, BytecodeProfileError, IndexError, KeyError) as exc:
        raise ClassMethodMatrixError("JAR_OR_CLASS_PROFILE_INVALID") from None
    report = compare_class_method_profiles(old, new, original_sha=original_sha)
    _require(
        _digest(original_jar) == original_sha
        and _digest(candidate_jar).lower() == candidate_sha256.lower(),
        "INPUT_CHANGED_DURING_REPLAY",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("candidate_jar", type=Path)
    parser.add_argument("class_entry")
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--out", type=Path, help="Private new report path only")
    args = parser.parse_args(argv)
    try:
        report = build_class_method_matrix(
            args.original_jar, args.candidate_jar,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
            class_entry=args.class_entry,
        )
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8", newline="\n") as output:
                json.dump(report, output, sort_keys=True, indent=2)
                output.write("\n")
        # Public terminal output is aggregate only; never print method IDs
        # or original source coordinates. Keep the detailed report private.
        print(json.dumps({
            "report_id": report["report_id"],
            "original_declared_method_count": report["original_declared_method_count"],
            "candidate_declared_method_count": report["candidate_declared_method_count"],
            "counts": report["counts"],
            "original_declared_field_count": report["original_declared_field_count"],
            "candidate_declared_field_count": report["candidate_declared_field_count"],
            "field_counts": report["field_counts"],
            "field_inventory_exact": report["field_inventory_exact"],
            "source_equivalence_certified": False,
        }, sort_keys=True))
    except (ClassMethodMatrixError, OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
