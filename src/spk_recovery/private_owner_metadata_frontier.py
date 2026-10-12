"""R88: whole-original owner declaration/nested metadata frontier after R87.

Compare exact original/candidate class profiles, enumerate missing fields and
methods PRIVATELY, and emit aggregate-only public-safe counts. A matching
loader/saver method does not imply an equivalent owner class or runtime.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from zipfile import ZipFile

from .clinit_store_order_witness import _verified_class
from .mutable_scalar_initializer_source import _digest


class OriginalOwnerFrontierError(ValueError):
    pass


def require(ok, why):
    if not ok:
        raise OriginalOwnerFrontierError(why)


def _unique(rows, kind):
    require(isinstance(rows, list), "INVALID_" + kind + "_TABLE")
    out = {}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get("name"), str)
                and isinstance(row.get("descriptor"), str)
                and type(row.get("access")) is int,
                "INVALID_" + kind + "_DECLARATION")
        key = (row["name"], row["descriptor"])
        require(key not in out, "DUPLICATE_" + kind + "_DECLARATION")
        out[key] = row
    return out


def private_owner_frontier(original: dict, candidate: dict,
                           original_nested: set[str],
                           candidate_nested: set[str]) -> dict:
    require(original.get("internal_name") == candidate.get("internal_name"),
            "ORIGINAL_CANDIDATE_OWNER_NAME_DIFFERENT")
    a = _unique(original.get("fields"), "ORIGINAL_FIELD")
    b = _unique(candidate.get("fields"), "CANDIDATE_FIELD")
    x = _unique(original.get("methods"), "ORIGINAL_METHOD")
    y = _unique(candidate.get("methods"), "CANDIDATE_METHOD")
    f_a, f_b = set(a), set(b)
    m_a, m_b = set(x), set(y)
    shared_fields = sorted(f_a & f_b)
    shared_methods = sorted(m_a & m_b)
    field_drift = [
        k for k in shared_fields
        if any(a[k].get(p) != b[k].get(p)
               for p in ("access", "signature", "constant_value"))
    ]
    method_declaration_drift = [
        k for k in shared_methods
        if any(x[k].get(p) != y[k].get(p)
               for p in ("access", "signature"))
    ]
    require(all(isinstance(v, str) and v.endswith(".class")
                for v in original_nested | candidate_nested),
            "INVALID_NESTED_CLASS_IDENTITY")
    private = {
        "missing_original_fields": sorted(f_a - f_b),
        "candidate_extra_fields": sorted(f_b - f_a),
        "shared_field_declaration_mismatches": field_drift,
        "missing_original_methods": sorted(m_a - m_b),
        "candidate_extra_methods": sorted(m_b - m_a),
        "shared_method_declaration_mismatches": method_declaration_drift,
        "missing_original_nested_classes": sorted(original_nested - candidate_nested),
        "candidate_extra_nested_classes": sorted(candidate_nested - original_nested),
    }
    report = {
        "original_fields": len(a), "candidate_fields": len(b),
        "shared_field_identities": len(shared_fields),
        "missing_original_fields": len(private["missing_original_fields"]),
        "extra_candidate_fields": len(private["candidate_extra_fields"]),
        "shared_field_declaration_mismatches": len(field_drift),
        "original_methods": len(x), "candidate_methods": len(y),
        "shared_method_identities": len(shared_methods),
        "missing_original_methods": len(private["missing_original_methods"]),
        "extra_candidate_methods": len(private["candidate_extra_methods"]),
        "shared_method_declaration_mismatches": len(method_declaration_drift),
        "original_owner_clinit_present": any(k[0] == "<clinit>" for k in x),
        "candidate_owner_clinit_present": any(k[0] == "<clinit>" for k in y),
        "original_nested_classes": len(original_nested),
        "candidate_nested_classes": len(candidate_nested),
        "missing_original_nested_classes": len(private["missing_original_nested_classes"]),
        "extra_candidate_nested_classes": len(private["candidate_extra_nested_classes"]),
        "original_candidate_major_equal":
            original.get("classfile_major") == candidate.get("classfile_major"),
        "original_candidate_super_equal":
            original.get("super_name") == candidate.get("super_name"),
        "original_candidate_class_access_equal":
            original.get("class_access") == candidate.get("class_access"),
        "original_candidate_class_signature_equal":
            original.get("signature") == candidate.get("signature"),
        "original_candidate_interface_list_equal":
            original.get("interfaces") == candidate.get("interfaces"),
        "complete_owner_method_implementation_parity_proven": False,
        "static_initializer_instruction_and_side_effect_parity_proven": False,
        "nested_enum_class_implementation_parity_proven": False,
        "whole_client_runtime_equivalence_certified": False,
    }
    require(len(a) == report["shared_field_identities"] +
            report["missing_original_fields"]
            and len(b) == report["shared_field_identities"] +
            report["extra_candidate_fields"]
            and len(x) == report["shared_method_identities"] +
            report["missing_original_methods"]
            and len(y) == report["shared_method_identities"] +
            report["extra_candidate_methods"],
            "OWNER_FRONTIER_COUNT_ACCOUNTING_FAILED")
    return {"private_missing_and_drift_identities": private, **report}


def _nested(jar: Path, entry: str) -> set[str]:
    require(entry.endswith(".class")
            and not entry.startswith("/")
            and "\\" not in entry and ".." not in entry.split("/"),
            "OWNER_CLASS_ENTRY_UNSAFE")
    prefix = entry[:-6] + "$"
    with ZipFile(jar) as archive:
        require(archive.namelist().count(entry) == 1,
                "OWNER_CLASS_ENTRY_NOT_UNIQUE")
        return {name for name in archive.namelist()
                if name.startswith(prefix) and name.endswith(".class")}


def replay_private_owner_frontier(
    original_jar: Path, candidate_jar: Path, original_entry: str,
    candidate_entry: str, output: Path, *, original_sha256: str,
    candidate_sha256: str,
) -> dict:
    original_jar, candidate_jar, output = (
        Path(original_jar), Path(candidate_jar), Path(output))
    require(not output.exists() and not output.is_symlink(),
            "OUTPUT_ALREADY_EXISTS")
    try:
        original = _verified_class(original_jar, original_entry, original_sha256)
        candidate = _verified_class(candidate_jar, candidate_entry, candidate_sha256)
        proof = private_owner_frontier(
            original, candidate, _nested(original_jar, original_entry),
            _nested(candidate_jar, candidate_entry))
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        if isinstance(exc, OriginalOwnerFrontierError):
            raise
        raise OriginalOwnerFrontierError(
            "PRIVATE_ORIGINAL_OWNER_METADATA_NOT_VERIFIABLE") from exc
    require(_digest(original_jar) == original_sha256.lower()
            and _digest(candidate_jar) == candidate_sha256.lower(),
            "PINNED_OWNER_JARS_CHANGED_DURING_PROOF")
    detail = proof.pop("private_missing_and_drift_identities")
    aggregate = {
        "schema_version": 1, "kind": "private_original_v309_complete_owner_metadata_frontier",
        "original_complete_jar_sha256": original_sha256.lower(),
        "candidate_complete_jar_sha256": candidate_sha256.lower(),
        "research_only": True, **proof,
    }
    output.mkdir(parents=True, exist_ok=False)
    with (output / "missing-owner-identities.private.json").open(
            "x", encoding="utf-8", newline="\n") as f:
        json.dump(detail, f, indent=2, sort_keys=True)
        f.write("\n")
    with (output / "owner-frontier.aggregate.json").open(
            "x", encoding="utf-8", newline="\n") as f:
        json.dump(aggregate, f, indent=2, sort_keys=True)
        f.write("\n")
    return aggregate


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("original_jar", "candidate_jar", "original_class_entry",
                 "candidate_class_entry", "new_private_output"):
        p.add_argument(name)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(replay_private_owner_frontier(
            Path(a.original_jar), Path(a.candidate_jar),
            a.original_class_entry, a.candidate_class_entry,
            Path(a.new_private_output),
            original_sha256=a.original_sha256, candidate_sha256=a.candidate_sha256),
            sort_keys=True))
    except OriginalOwnerFrontierError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
