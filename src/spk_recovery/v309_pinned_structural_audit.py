from __future__ import annotations

"""Exact-JAR research audit of already pinned classfile structural digests.

Does not update or accept any canonical lineage. Reports only aggregate
per-build counts and full-archive SHA fingerprints already in public frontier.
Private class names, method bodies, String literals, or divergent digests
NEVER leave memory.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .classfile import parse_class, ClassFormatError
from .descriptor_class_private_jar_replay import (
    _read_json_exact, write_research_report_no_clobber,
)
from .indexer import sha256_file
from .lineage import validate_lineage


class V309PinnedStructuralAuditError(ValueError):
    pass


_CLASS_COUNTS = {"v308": 10472, "v309": 10502}
_LINEAGE_COUNTS = {"v308": 1129, "v309": 1092}


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("utf-8")).hexdigest()


def _pinned_class_records(lineage: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Reject any ambiguous canonical record before touching the private JAR."""
    validate_lineage(lineage)
    records: dict[str, list[dict[str, Any]]] = {"v308": [], "v309": []}
    seen: set[tuple[str, str]] = set()
    for c in lineage["classes"]:
        for row in c["lineage"]:
            build = row.get("build_id")
            if build not in records:
                raise V309PinnedStructuralAuditError("unexpected pinned build identity")
            path = row.get("entry_path")
            if (
                not isinstance(path, str) or not path.endswith(".class")
                or row.get("internal_name") != path[:-6]
                or (build, path) in seen
                or not isinstance(row.get("entry_sha256"), str)
                or not isinstance(row.get("structural_sha256"), str)
            ):
                raise V309PinnedStructuralAuditError("ambiguous or malformed canonical class entry")
            seen.add((build, path))
            records[build].append(row)
    for build, rows in records.items():
        if len(rows) != _LINEAGE_COUNTS[build]:
            raise V309PinnedStructuralAuditError(f"{build}: canonical lineage count drift")
    return records


def audit_pinned_jar(
    jar_path: Path,
    build: str,
    records: list[dict[str, Any]],
    expected_sha: str,
) -> dict[str, int]:
    """Scan ONLY canonical pinned class entries, fail closed on archive drift.

    A structural mismatch is counted, never rewritten or accepted. Raw-entry
    mismatches, duplicate archive entries and missing paths are fatal.
    """
    if build not in _CLASS_COUNTS:
        raise V309PinnedStructuralAuditError("unsupported build")
    actual = sha256_file(jar_path)
    if actual.lower() != expected_sha.lower():
        raise V309PinnedStructuralAuditError(f"{build}: private exact JAR SHA mismatch")
    counts: Counter[str] = Counter()
    with zipfile.ZipFile(jar_path, "r") as archive:
        infos = archive.infolist()
        all_paths = [info.filename for info in infos]
        if len(set(all_paths)) != len(all_paths):
            raise V309PinnedStructuralAuditError(f"{build}: duplicate archive entry path")
        class_count = sum(name.endswith(".class") for name in all_paths)
        if class_count != _CLASS_COUNTS[build]:
            raise V309PinnedStructuralAuditError(f"{build}: full archive class count drift")
        lookup = set(all_paths)
        for record in records:
            path = record["entry_path"]
            if path not in lookup:
                raise V309PinnedStructuralAuditError(f"{build}: missing pinned class")
            raw = archive.read(path)
            if hashlib.sha256(raw).hexdigest().lower() != record["entry_sha256"].lower():
                raise V309PinnedStructuralAuditError(f"{build}: pinned class raw SHA mismatch")
            try:
                parsed = parse_class(raw)
                current_structural = parsed.structural_sha256()
            except (ValueError, UnicodeError, ClassFormatError) as exc:
                raise V309PinnedStructuralAuditError(
                    f"{build}: pinned class cannot be parsed losslessly"
                ) from exc
            if parsed.name != record["internal_name"]:
                raise V309PinnedStructuralAuditError(f"{build}: pinned internal name mismatch")
            counts["exact_raw_entry_sha_matches"] += 1
            if current_structural.lower() == record["structural_sha256"].lower():
                counts["structural_hash_matches"] += 1
            else:
                counts["structural_hash_drifts"] += 1
    counts["pinned_records"] = len(records)
    counts["complete_jar_class_entries"] = class_count
    if (counts["structural_hash_matches"] + counts["structural_hash_drifts"]
        != counts["pinned_records"]):
        raise V309PinnedStructuralAuditError(f"{build}: structural accounting mismatch")
    return {
        "pinned_records": counts["pinned_records"],
        "complete_jar_class_entries": counts["complete_jar_class_entries"],
        "exact_raw_entry_sha_matches": counts["exact_raw_entry_sha_matches"],
        "structural_hash_matches": counts["structural_hash_matches"],
        "structural_hash_drifts": counts["structural_hash_drifts"],
    }


def build_v309_pinned_structural_audit(
    frontier: dict[str, Any],
    lineage: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
) -> dict[str, Any]:
    if (
        frontier.get("kind") != "v309_recovery_frontier"
        or frontier.get("state") != "ACCEPTED_INCOMPLETE"
        or frontier.get("frontier", {}).get("unresolved") != 143
        or frontier.get("frontier", {}).get("descriptor_identity_guard_rejected") != 26
    ):
        raise V309PinnedStructuralAuditError("pinned 143/26 incomplete frontier required")
    exact = frontier.get("exact_clients")
    if not isinstance(exact, dict):
        raise V309PinnedStructuralAuditError("missing exact JAR pins")
    records = _pinned_class_records(lineage)
    builds = {b["build_id"]: b["sha256"] for b in lineage["builds"]}
    if set(builds) != {"v308", "v309"}:
        raise V309PinnedStructuralAuditError("lineage build declarations drift")
    for b in builds:
        if (
            not isinstance(exact.get(b + "_sha256"), str)
            or len(exact[b + "_sha256"]) != 64
            or builds[b].lower() != exact[b + "_sha256"].lower()
        ):
            raise V309PinnedStructuralAuditError("lineage/exact build SHA mismatch")
    results = {
        "v308": audit_pinned_jar(old_jar, "v308", records["v308"], builds["v308"]),
        "v309": audit_pinned_jar(new_jar, "v309", records["v309"], builds["v309"]),
    }
    drift = sum(x["structural_hash_drifts"] for x in results.values())
    body = {
        "schema_version": 1,
        "kind": "v309_pinned_class_structural_drift_research",
        "canonical": False,
        "state": (
            "STRUCTURAL_FINGERPRINT_DRIFT_REVIEW_VETO"
            if drift else "PINNED_STRUCTURAL_FINGERPRINTS_EXACT_MATCH_RESEARCH_ONLY"
        ),
        "exact_clients": exact,
        "summary": {
            "canonical_class_records_checked": sum(x["pinned_records"] for x in results.values()),
            "raw_pinned_sha_verified": sum(x["exact_raw_entry_sha_matches"] for x in results.values()),
            "structural_hash_matches": sum(x["structural_hash_matches"] for x in results.values()),
            "structural_hash_drifts": drift,
            "canonical_class_identities_accepted": 0,
            "canonical_member_identities_accepted": 0,
            "canonical_unresolved_field_relationships": 143,
        },
        "by_build": results,
        "note": (
            "Research-only verification of pre-existing pinned v308/v309 "
            "class entries using lossless JVM Modified UTF-8 parser. "
            "A structural mismatch is a VETO requiring a separate reviewed "
            "canonical evidence migration; no private string, class name, "
            "member body, entry digest or mapping is emitted."
        ),
    }
    return {"report_id": "V309STRUCTAUDIT_" + _sha(body)[:20].upper(), **body}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-pinned-structural-audit")
    p.add_argument("--v308-jar", type=Path, required=True)
    p.add_argument("--v309-jar", type=Path, required=True)
    p.add_argument("--frontier", type=Path,
                   default=Path("research/v309-field-recovery/frontier.json"))
    p.add_argument("--class-lineage", type=Path,
                   default=Path("research/v309-field-recovery/class-lineage.json"))
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        frontier = _read_json_exact(args.frontier)
        expected = frontier.get("files", {}).get("class_lineage", {}).get("sha256")
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or sha256_file(args.class_lineage).lower() != expected.lower()
        ):
            raise V309PinnedStructuralAuditError("tracked canonical class lineage SHA drift")
        result = build_v309_pinned_structural_audit(
            frontier, _read_json_exact(args.class_lineage),
            args.v308_jar, args.v309_jar,
        )
        write_research_report_no_clobber(
            result, args.out,
            (args.v308_jar, args.v309_jar, args.frontier, args.class_lineage),
        )
    except (OSError, KeyError, ValueError, TypeError, zipfile.BadZipFile) as exc:
        print(f"SPK_V309_PINNED_STRUCTURAL_AUDIT_FAIL: {exc}")
        return 1
    print("SPK_V309_PINNED_STRUCTURAL_AUDIT_PASS_RESEARCH_ONLY")
    print("report_id=" + result["report_id"])
    for name, value in result["summary"].items():
        print(f"{name}={value}")
    print("report_path=" + str(args.out))
    # Drift is research evidence, never an accepted success state.
    return 2 if result["summary"]["structural_hash_drifts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
