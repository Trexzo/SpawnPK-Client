from __future__ import annotations

"""Research-only v309 multi-lane report concordance.

This joins strictly validated, already separately generated private-JAR
research reports. It never reads or publishes private bytecode, never asserts
semantic class equivalence, and NEVER mutates canonical class/field lineage.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .descriptor_class_dependencies import build_descriptor_class_dependency_report
from .descriptor_class_private_jar_replay import (
    _read_json_exact, write_research_report_no_clobber,
)
from .indexer import sha256_file
from .lineage import validate_lineage


class V309ConcordanceError(ValueError):
    pass


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _expect(condition: bool, failure: str) -> None:
    if not condition:
        raise V309ConcordanceError(failure)


def _nonnegative(value: Any) -> bool:
    return type(value) is int and value >= 0


def _check_common_report(
    doc: dict[str, Any],
    kind: str,
    prefix: str,
    exact: dict[str, str],
) -> None:
    _expect(
        isinstance(doc, dict)
        and doc.get("kind") == kind
        and doc.get("canonical") is False
        and isinstance(doc.get("report_id"), str)
        and doc["report_id"].startswith(prefix)
        and isinstance(doc.get("summary"), dict),
        f"{kind}: missing noncanonical report authority",
    )
    # Source research tools derive report_id from the COMPLETE body.
    # Checking prefixes and cross-links without independently recomputing
    # this digest would allow modified/stale source evidence to retain an
    # apparently matching provenance ID.
    body = {k: v for k, v in doc.items() if k != "report_id"}
    canonical_bytes = json.dumps(
        body, sort_keys=True, separators=(",", ":"),
        ensure_ascii=(kind == "v309_pinned_class_structural_drift_research"),
    ).encode("utf-8")
    expected_id = prefix + hashlib.sha256(canonical_bytes).hexdigest()[:20].upper()
    _expect(doc["report_id"] == expected_id,
            f"{kind}: report ID does not authenticate actual report body")
    pins = doc.get("exact_clients")
    if not isinstance(pins, dict):
        pins = {}
    old = doc.get("old_sha256", pins.get("v308_sha256"))
    new = doc.get("new_sha256", pins.get("v309_sha256"))
    _expect(
        isinstance(old, str) and isinstance(new, str)
        and old.lower() == exact["v308_sha256"].lower()
        and new.lower() == exact["v309_sha256"].lower(),
        f"{kind}: exact pinned client build mismatch",
    )


def _lane_rows(
    doc: dict[str, Any],
    source_name: str,
    expected: dict[str, int],
) -> dict[str, bool]:
    candidates = doc.get("candidates")
    rejected = doc.get("rejected")
    _expect(
        isinstance(candidates, list) and isinstance(rejected, list)
        and _nonnegative(doc["summary"].get("candidate_classes"))
        and _nonnegative(doc["summary"].get("rejected_classes"))
        and doc["summary"]["candidate_classes"] == len(candidates)
        and doc["summary"]["rejected_classes"] == len(rejected)
        and len(candidates) + len(rejected) == len(expected)
        and doc["summary"].get("accepted_unresolved_fields") == 143
        and doc["summary"].get("canonical_identities_accepted") == 0,
        f"{source_name}: candidate/rejection accounting drift",
    )
    out: dict[str, bool] = {}
    for item, positive in ((*((r, True) for r in candidates),
                            *((r, False) for r in rejected))):
        _expect(isinstance(item, dict), f"{source_name}: malformed class witness")
        cid = item.get("old_canonical_class_id")
        _expect(
            isinstance(cid, str) and cid in expected
            and cid not in out
            and item.get("blocked_fields") == expected[cid],
            f"{source_name}: missing, repeated or wrong blocked class group",
        )
        out[cid] = positive
    _expect(
        set(out) == set(expected)
        and doc["summary"].get("input_class_dependencies") == 8
        and doc["summary"].get("input_blocked_fields") == 26
        and doc["summary"].get("candidate_blocked_fields") ==
            sum(expected[c] for c, found in out.items() if found)
        and doc["summary"].get("remaining_blocked_fields") ==
            sum(expected[c] for c, found in out.items() if not found),
        f"{source_name}: group or blocked-field conservation failure",
    )
    return out


def _indexed_rows(
    doc: dict[str, Any],
    source_name: str,
    expected: dict[str, int],
) -> dict[str, dict[str, Any]]:
    rows = doc.get("rows")
    _expect(isinstance(rows, list) and len(rows) == len(expected),
            f"{source_name}: expected exact eight-row research report")
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        _expect(isinstance(r, dict), f"{source_name}: malformed row")
        cid = r.get("old_canonical_class_id")
        _expect(
            isinstance(cid, str) and cid in expected and cid not in out
            and r.get("blocked_fields") == expected[cid],
            f"{source_name}: duplicate/unknown/unbalanced class dependency",
        )
        out[cid] = r
    _expect(set(out) == set(expected), f"{source_name}: incomplete class coverage")
    return out


def build_v309_multilane_concordance(
    frontier: dict[str, Any],
    lineage: dict[str, Any],
    global_report: dict[str, Any],
    literal: dict[str, Any],
    shape: dict[str, Any],
    cp_pair: dict[str, Any],
    cp_rivals: dict[str, Any],
    structural: dict[str, Any],
) -> dict[str, Any]:
    """Report concordance only; no claim of class or field identity acceptance."""
    _expect(
        frontier.get("kind") == "v309_recovery_frontier"
        and frontier.get("state") == "ACCEPTED_INCOMPLETE"
        and frontier.get("build_id") == "v309"
        and frontier.get("frontier", {}).get("unresolved") == 143
        and frontier.get("frontier", {}).get("descriptor_identity_guard_rejected") == 26,
        "requires exact accepted incomplete v309 143/26 frontier",
    )
    validate_lineage(lineage)
    exact = frontier["exact_clients"]
    builds = {b["build_id"]: b["sha256"] for b in lineage["builds"]}
    _expect(
        set(builds) == {"v308", "v309"}
        and all(builds[b].lower() == exact[b + "_sha256"].lower() for b in builds),
        "exact lineage/client build fingerprint mismatch",
    )
    _expect(
        global_report.get("kind") == "global_field_usage_identity_candidates"
        and global_report.get("canonical") is False
        and global_report.get("report_id") ==
            frontier.get("files", {}).get("global_field_usage", {}).get("report_id")
        and global_report.get("summary", {}).get("descriptor_identity_guard_rejected") == 26
        and len(global_report.get("review_outcomes", [])) == 143
        and global_report.get("old_sha256", "").lower() == exact["v308_sha256"].lower()
        and global_report.get("new_sha256", "").lower() == exact["v309_sha256"].lower(),
        "accepted global field report must remain pinned 143/26",
    )
    deps = build_descriptor_class_dependency_report(global_report)
    _expect(
        deps.get("summary", {}).get("blocked_fields") == 26
        and deps["summary"].get("blocking_old_class_identities") == 8,
        "descriptor-class dependency queue drift",
    )
    expected: dict[str, int] = {}
    for d in deps["class_dependencies"]:
        cid = d["old_canonical_class_id"]
        _expect(
            isinstance(cid, str) and cid not in expected
            and _nonnegative(d.get("blocked_fields"))
            and d["blocked_fields"] > 0,
            "invalid descriptor-class dependency row",
        )
        expected[cid] = d["blocked_fields"]
    _expect(len(expected) == 8 and sum(expected.values()) == 26,
            "exact eight-class/26-field coverage required")

    reports = (
        (literal, "v309_changed_class_unique_literal_research", "V309LITERAL_"),
        (shape, "v309_changed_class_method_shape_research", "V309METHODSHAPE_"),
        (cp_pair, "v309_cp_method_referent_pairwise_research", "V309CPPAIR_"),
        (cp_rivals, "v309_cp_method_whole_archive_rival_research", "V309CPRIVALS_"),
        (structural, "v309_pinned_class_structural_drift_research", "V309STRUCTAUDIT_"),
    )
    for report, kind, prefix in reports:
        _check_common_report(report, kind, prefix, exact)
    _expect(
        len({report["report_id"] for report, _, _ in reports}) == len(reports),
        "research reports must have separate provenance IDs",
    )
    report_digest = _digest(global_report)
    lineage_digest = _digest(lineage)
    dependency_digest = _digest(deps)
    for report in (literal, shape):
        _expect(
            report.get("global_report_id") == global_report["report_id"]
            and report.get("global_report_digest") == report_digest
            and report.get("class_lineage_digest") == lineage_digest
            and report.get("dependency_digest") == dependency_digest,
            "literal/method-shape input proof digest drift",
        )
    _expect(
        cp_pair.get("global_report_id") == global_report["report_id"]
        and cp_pair.get("frontier_id") == frontier.get("report_id")
        and cp_rivals.get("source_cp_pair_report_id") == cp_pair["report_id"]
        and cp_rivals.get("source_global_field_report_id") == global_report["report_id"],
        "CP pair-to-rival report chain broken",
    )
    ss = structural["summary"]
    _expect(
        structural.get("state") == "PINNED_STRUCTURAL_FINGERPRINTS_EXACT_MATCH_RESEARCH_ONLY"
        and ss.get("canonical_class_records_checked") == 2221
        and ss.get("raw_pinned_sha_verified") == 2221
        and ss.get("structural_hash_matches") == 2221
        and ss.get("structural_hash_drifts") == 0
        and ss.get("canonical_class_identities_accepted") == 0
        and ss.get("canonical_member_identities_accepted") == 0
        and ss.get("canonical_unresolved_field_relationships") == 143,
        "structural hash drift or missing exact private lineage audit is a veto",
    )
    for b, count in (("v308", 1129), ("v309", 1092)):
        row = structural.get("by_build", {}).get(b, {})
        _expect(
            row.get("pinned_records") == count
            and row.get("exact_raw_entry_sha_matches") == count
            and row.get("structural_hash_matches") == count
            and row.get("structural_hash_drifts") == 0,
            f"{b}: exact pinned class audit coverage incomplete",
        )

    lit = _lane_rows(literal, "literal", expected)
    shp = _lane_rows(shape, "method_shape", expected)
    cp = _indexed_rows(cp_pair, "cp_pair", expected)
    rivals = _indexed_rows(cp_rivals, "cp_rivals", expected)
    _expect(
        cp_pair["summary"].get("reviewed_descriptor_class_pairs") == 8
        and cp_pair["summary"].get("input_blocked_field_relationships") == 26
        and cp_pair["summary"].get("class_identities_accepted") == 0
        and cp_pair["summary"].get("member_identities_accepted") == 0
        and cp_pair["summary"].get("accepted_frontier_unresolved") == 143
        and cp_rivals["summary"].get("examined_descriptor_classes") == 8
        and cp_rivals["summary"].get("blocked_field_relationships_preserved") == 26
        and cp_rivals["summary"].get("class_identities_accepted") == 0
        and cp_rivals["summary"].get("member_identities_accepted") == 0
        and cp_rivals["summary"].get("canonical_unresolved_fields") == 143,
        "CP research summary count/acceptance drift",
    )
    out = []
    for cid in sorted(expected):
        witness_count = cp[cid].get("unique_cp_semantic_method_matches")
        _expect(
            _nonnegative(witness_count)
            and cp[cid].get("accepted_class_identifications") == 0
            and cp[cid].get("accepted_member_identifications") == 0
            and rivals[cid].get("research_only") is True
            and rivals[cid].get("canonical_identity_accepted") is False,
            "noncanonical CP candidate data malformed",
        )
        state = rivals[cid].get("state")
        _expect(isinstance(state, str) and state, "missing rival-owner analysis state")
        viable = (
            (lit[cid] or shp[cid])
            and witness_count >= 3
            and state == "MUTUAL_WHOLE_ARCHIVE_SUPPORTED_SUBSET_RESEARCH_ONLY"
            and rivals[cid].get("proposed_pair_unique_cp_method_matches", -1) >= 3
        )
        out.append({
            "old_canonical_class_id": cid,
            "blocked_fields": expected[cid],
            "globally_unique_literal_lane": lit[cid],
            "whole_archive_method_shape_lane": shp[cid],
            "pairwise_supported_cp_witness_count": witness_count,
            "whole_archive_rival_research_state": state,
            "review_bucket": (
                "SUPPORTED_SUBSET_ONLY_NEEDS_EXPLICIT_REVIEW"
                if viable else "BLOCKED_OR_INSUFFICIENT_NO_ACCEPTANCE"
            ),
            "accepted_class_identity": False,
            "accepted_field_identities": 0,
        })

    summary = {
        "descriptor_class_groups": 8,
        "blocked_field_relationships": 26,
        "supported_subset_reviewable": sum(
            x["review_bucket"] == "SUPPORTED_SUBSET_ONLY_NEEDS_EXPLICIT_REVIEW"
            for x in out
        ),
        "blocked_or_insufficient": sum(
            x["review_bucket"] == "BLOCKED_OR_INSUFFICIENT_NO_ACCEPTANCE"
            for x in out
        ),
        "canonical_class_identities_accepted": 0,
        "canonical_field_identities_accepted": 0,
        "canonical_unresolved_field_relationships": 143,
    }
    body = {
        "schema_version": 1,
        "kind": "v309_multilane_research_concordance",
        "canonical": False,
        "state": "CONCORDANCE_ONLY_NO_CLASS_OR_FIELD_ACCEPTANCE",
        "exact_clients": exact,
        "report_source_ids": {
            "literal": literal["report_id"],
            "shape": shape["report_id"],
            "cp_pair": cp_pair["report_id"],
            "cp_rivals": cp_rivals["report_id"],
            "pinned_structural": structural["report_id"],
            "global_field": global_report["report_id"],
        },
        "summary": summary,
        "rows": out,
        "note": (
            "This is concordance of independent research reports, NOT "
            "a verified semantic equivalence or class/field acceptance. "
            "Every candidate needs manual review and separate member replay. "
            "No raw private classes, methods, literal values or indexes emitted."
        ),
    }
    return {"report_id": "V309CONCORDANCE_" + _digest(body)[:20].upper(), **body}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-multilane-proof-concordance")
    p.add_argument("--frontier", type=Path,
                   default=Path("research/v309-field-recovery/frontier.json"))
    p.add_argument("--class-lineage", type=Path,
                   default=Path("research/v309-field-recovery/class-lineage.json"))
    p.add_argument("--global-report", type=Path,
                   default=Path("research/v309-field-recovery/global-field-usage.json"))
    p.add_argument("--literal", type=Path, required=True)
    p.add_argument("--method-shape", type=Path, required=True)
    p.add_argument("--cp-pair", type=Path, required=True)
    p.add_argument("--cp-rivals", type=Path, required=True)
    p.add_argument("--pinned-structural", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        frontier = _read_json_exact(a.frontier)
        for name, path in (
            ("class_lineage", a.class_lineage),
            ("global_field_usage", a.global_report),
        ):
            expected = frontier.get("files", {}).get(name, {}).get("sha256")
            if (
                not isinstance(expected, str) or len(expected) != 64
                or sha256_file(path).lower() != expected.lower()
            ):
                raise V309ConcordanceError(f"accepted tracked {name} SHA drift")
        inputs = (
            a.frontier, a.class_lineage, a.global_report,
            a.literal, a.method_shape, a.cp_pair, a.cp_rivals,
            a.pinned_structural,
        )
        report = build_v309_multilane_concordance(
            *(_read_json_exact(p) for p in inputs),
        )
        write_research_report_no_clobber(report, a.out, inputs)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"SPK_V309_CONCORDANCE_FAIL: {exc}")
        return 1
    print("SPK_V309_CONCORDANCE_PASS_RESEARCH_ONLY")
    print("report_id=" + report["report_id"])
    for name, value in report["summary"].items():
        print(f"{name}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
