from __future__ import annotations

"""Inspect a private dual-lane research bundle without either private client JAR.

Checks accounting and bindings only. Does NOT independently authenticate class
fingerprints, field-declaration intervals, exact bytecode, or mappings.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from .descriptor_class_private_jar_replay import _read_json_exact
from .descriptor_class_replay_offline_review import build_descriptor_class_offline_review
from .v309_private_dual_proof_replay import _digest
from .v309_crosslane_class_impact import build_v309_crosslane_class_impact


class V309DualBundleOfflineVerifyError(ValueError):
    pass


_EMPTY_REASON_KEYS = (
    "raw_source_guard_rejected",
    "global_class_topology_guard_rejected",
    "missing_two_sided_canonical_anchor",
    "canonical_anchor_identity_mismatch",
    "declaration_interval_length_mismatch",
    "declaration_interval_shape_mismatch",
    "target_interval_offset_mismatch",
    "target_declaration_signature_not_unique",
)


def _is_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdefABCDEF" for c in value)
    )


def _ensure(condition: bool, msg: str) -> None:
    if not condition:
        raise V309DualBundleOfflineVerifyError(msg)


def _check_empty_report(
    report: dict[str, Any],
    field_report: dict[str, Any],
    member_lineage: dict[str, Any],
    v308_sha: str,
    v309_sha: str,
) -> dict[str, int]:
    _ensure(
        isinstance(report, dict)
        and set(report) == {
            "schema_version", "kind", "canonical", "report_id", "old_build_id",
            "new_build_id", "old_sha256", "new_sha256", "member_lineage_digest",
            "global_usage_report_id", "summary", "candidates", "rejected", "note",
        }
        and report.get("schema_version") == 1
        and report.get("kind") == "empty_field_declaration_identity_candidates"
        and report.get("canonical") is False
        and report.get("old_build_id") == "v308"
        and report.get("new_build_id") == "v309"
        and isinstance(report.get("old_sha256"), str)
        and isinstance(report.get("new_sha256"), str)
        and report["old_sha256"].lower() == v308_sha.lower()
        and report["new_sha256"].lower() == v309_sha.lower()
        and report.get("member_lineage_digest") == _digest(member_lineage)
        and report.get("global_usage_report_id") == field_report["report_id"]
        and isinstance(report.get("candidates"), list)
        and isinstance(report.get("rejected"), list)
        and isinstance(report.get("summary"), dict)
        and isinstance(report.get("note"), str),
        "empty-field report does not match pinned research contract",
    )
    material = {
        "old_build_id": report["old_build_id"],
        "new_build_id": report["new_build_id"],
        "old_sha256": report["old_sha256"],
        "new_sha256": report["new_sha256"],
        "member_lineage_digest": report["member_lineage_digest"],
        "global_usage_report_id": report["global_usage_report_id"],
        "candidates": report["candidates"],
        "rejected": report["rejected"],
    }
    _ensure(
        report["report_id"] == "EMPTYFIELDDECL_" + _digest(material)[:20].upper(),
        "empty-field report_id digest mismatch",
    )
    rows = [x for x in field_report["review_outcomes"] if x.get("outcome") == "empty_both"]
    originals = {x["relationship_id"]: x for x in rows}
    _ensure(len(rows) == len(originals) == 68, "accepted empty_both source frontier drift")
    seen: set[str] = set()
    reason_counts: Counter[str] = Counter()

    for accepted, collection in (
        (True, report["candidates"]),
        (False, report["rejected"]),
    ):
        for row in collection:
            _ensure(isinstance(row, dict), "invalid empty-field evidence row")
            rel = row.get("relationship_id")
            _ensure(rel in originals and rel not in seen, "duplicate or unknown empty-field relationship")
            seen.add(rel)
            old = originals[rel]
            _ensure(
                row.get("logical_class_id") == old["logical_class_id"]
                and row.get("old_owner") == old["old_owner"]
                and row.get("new_owner") == old["new_owner"],
                "empty-field canonical owner/relationship drift",
            )
            if accepted:
                _ensure(
                    set(row) == {
                        "relationship_id", "logical_class_id", "old_owner",
                        "new_owner", "old", "new", "strategy", "confidence",
                        "score", "supports_existing_review",
                        "left_anchor_member_id", "right_anchor_member_id",
                        "old_field_ordinal", "new_field_ordinal",
                        "interval_offset", "interval_length",
                        "interval_digest", "global_source_class_topology",
                        "global_observations",
                    },
                    "unknown empty-field candidate or acceptance fields",
                )
                _ensure(
                    row.get("strategy") == "canonical_anchor_declaration_interval_exact"
                    and row.get("confidence") == "INFERRED_HIGH"
                    and row.get("supports_existing_review") is True
                    and row.get("score") == 0.99
                    and row.get("old") == old.get("old")
                    and row.get("new") == old.get("new")
                    and isinstance(row.get("left_anchor_member_id"), str)
                    and isinstance(row.get("right_anchor_member_id"), str)
                    and row["left_anchor_member_id"] != row["right_anchor_member_id"]
                    and type(row.get("interval_offset")) is int
                    and type(row.get("interval_length")) is int
                    and 0 <= row["interval_offset"] < row["interval_length"]
                    and type(row.get("old_field_ordinal")) is int
                    and type(row.get("new_field_ordinal")) is int
                    and row["old_field_ordinal"] >= 0
                    and row["new_field_ordinal"] >= 0
                    and _is_sha(row.get("interval_digest"))
                    and isinstance(row.get("global_source_class_topology"), list)
                    and type(row.get("global_observations")) is int
                    and row["global_observations"] >= 0,
                    "unsupported or incomplete empty-field candidate",
                )
            else:
                reason = row.get("reason")
                _ensure(reason in _EMPTY_REASON_KEYS, "unknown empty-field rejection reason")
                _ensure(
                    not any(k in row for k in (
                        "accepted", "promoted", "supports_existing_review", "strategy",
                    )),
                    "rejected row contains unsupported acceptance claims",
                )
                reason_counts[reason] += 1
    _ensure(seen == set(originals), "empty-field research rows omit source relationships")
    summary = report["summary"]
    expected = {
        "input_empty_both_reviews": 68,
        "candidate_fields": len(report["candidates"]),
        "remaining_without_declaration_proof": len(report["rejected"]),
        **{reason: reason_counts[reason] for reason in _EMPTY_REASON_KEYS},
    }
    _ensure(summary == expected, "empty-field summary/rejection accounting drift")
    return expected


def _crosslane_candidate_status(
    impact: dict[str, Any], offline_descriptor_review: dict[str, Any],
) -> list[dict[str, Any]]:
    """Prioritize *reported* candidate rows, never infer recovered identities.

    Call only after independent bundle JSON consistency checks. No local index
    or proprietary bytecode is reauthenticated by this presentation layer.
    """
    if offline_descriptor_review.get("state") != (
        "CONSISTENCY_ONLY_NOT_INDEPENDENT_PROOF_NO_IDENTITIES_ACCEPTED"
    ):
        raise V309DualBundleOfflineVerifyError("unverified descriptor review state")
    candidates = offline_descriptor_review.get("candidates")
    rejected = offline_descriptor_review.get("rejected")
    groups = impact.get("class_hypotheses")
    if not all(isinstance(rows, list) for rows in (candidates, rejected, groups)):
        raise V309DualBundleOfflineVerifyError("invalid class-impact inputs")
    candidate_ids = [row["old_canonical_class_id"] for row in candidates]
    rejected_ids = [row["old_canonical_class_id"] for row in rejected]
    group_ids = [row["old_canonical_class_id"] for row in groups]
    if (
        len(groups) != 8
        or len(set(group_ids)) != 8
        or len(candidate_ids) + len(rejected_ids) != 8
        or len(set(candidate_ids + rejected_ids)) != 8
        or set(group_ids) != set(candidate_ids + rejected_ids)
    ):
        raise V309DualBundleOfflineVerifyError("class candidate/impact group drift")
    selected = set(candidate_ids)
    return [
        {
            "old_canonical_class_id": row["old_canonical_class_id"],
            "hypothetical_new_source_class": row["hypothetical_new_source_class"],
            "descriptor_blocked_fields": row["descriptor_blocked_fields"],
            "alias_only_topology_hypotheses": row[
                "topology_rows_equal_after_this_alias_only"
            ],
            "research_priority_rows": row["combined_research_priority_rows"],
            "reported_index_witness_candidate": (
                row["old_canonical_class_id"] in selected
            ),
            "state": "OFFLINE_CANDIDATE_OR_ALIAS_ONLY_NO_IDENTITY_ACCEPTED",
        }
        for row in groups
    ]


def verify_v309_dual_bundle_offline(
    frontier: dict[str, Any],
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    global_field_report: dict[str, Any],
    manifest: dict[str, Any],
    descriptor_report: dict[str, Any],
    empty_report: dict[str, Any],
) -> dict[str, Any]:
    """Bundle coherence only; passing is never a substitute for private-JAR replay."""
    for name, doc in (
        ("frontier", frontier), ("class lineage", class_lineage),
        ("member lineage", member_lineage), ("global report", global_field_report),
        ("bundle", manifest), ("descriptor report", descriptor_report),
        ("empty report", empty_report),
    ):
        _ensure(isinstance(doc, dict), f"{name} must be an object")
    _ensure(
        frontier.get("kind") == "v309_recovery_frontier"
        and frontier.get("state") == "ACCEPTED_INCOMPLETE"
        and frontier.get("build_id") == "v309"
        and frontier.get("frontier", {}).get("unresolved") == 143
        and frontier.get("frontier", {}).get("empty_both") == 68
        and frontier.get("frontier", {}).get("descriptor_identity_guard_rejected") == 26,
        "expected accepted incomplete 143/68/26 frontier",
    )
    exact = frontier["exact_clients"]
    old = exact.get("v308_sha256")
    new = exact.get("v309_sha256")
    _ensure(_is_sha(old) and _is_sha(new), "invalid pinned exact client hashes")

    _ensure(
        set(manifest) == {
            "bundle_id", "schema_version", "kind", "canonical", "state",
            "global_report_id", "v308_sha256", "v309_sha256",
            "descriptor_report_id", "descriptor_report_digest",
            "empty_report_id", "empty_report_digest",
            "descriptor_summary", "empty_summary",
            "unresolved_accepted_frontier", "warning",
        },
        "unexpected bundle metadata/authority fields",
    )
    _ensure(
        manifest.get("schema_version") == 1
        and manifest.get("kind") == "v309_private_dual_proof_research_bundle"
        and manifest.get("canonical") is False
        and manifest.get("state") == "BOTH_LANES_RESEARCH_ONLY_NO_IDENTITIES_ACCEPTED"
        and manifest.get("unresolved_accepted_frontier") == 143
        and manifest.get("global_report_id") == global_field_report.get("report_id")
        and manifest.get("v308_sha256", "").lower() == old.lower()
        and manifest.get("v309_sha256", "").lower() == new.lower()
        and manifest.get("descriptor_report_id") == descriptor_report.get("report_id")
        and manifest.get("empty_report_id") == empty_report.get("report_id")
        and manifest.get("descriptor_report_digest") == _digest(descriptor_report)
        and manifest.get("empty_report_digest") == _digest(empty_report)
        and isinstance(manifest.get("warning"), str),
        "dual-bundle source/report binding mismatch",
    )
    bare = {k: v for k, v in manifest.items() if k != "bundle_id"}
    _ensure(
        manifest.get("bundle_id") == "V309DUAL_" + _digest(bare)[:20].upper(),
        "dual-bundle deterministic ID mismatch",
    )
    descriptor_review = build_descriptor_class_offline_review(
        frontier, class_lineage, global_field_report, descriptor_report,
    )
    empty_summary = _check_empty_report(
        empty_report, global_field_report, member_lineage, old, new,
    )
    _ensure(
        manifest.get("descriptor_summary") == descriptor_report.get("summary")
        and manifest.get("empty_summary") == empty_summary
        and descriptor_review["summary"]["candidate_fields_blocked"]
            + descriptor_review["summary"]["still_blocked_fields"] == 26,
        "dual-bundle 26/8/68 summary drift",
    )
    impact = build_v309_crosslane_class_impact(global_field_report)
    crosslane_priorities = _crosslane_candidate_status(impact, descriptor_review)
    return {
        "schema_version": 1,
        "kind": "v309_dual_bundle_offline_consistency",
        "state": "CONSISTENCY_ONLY_NO_PRIVATE_JAR_PROOF_NO_IDENTITIES_ACCEPTED",
        "canonical": False,
        "bundle_id": manifest["bundle_id"],
        "descriptor_report_id": descriptor_report["report_id"],
        "empty_report_id": empty_report["report_id"],
        "descriptor_summary": descriptor_review["summary"],
        "empty_summary": empty_summary,
        "crosslane_candidate_priorities": crosslane_priorities,
        "accepted_frontier_unresolved": 143,
        "warning": (
            "This checks only local JSON consistency and tracked-file bindings. "
            "It does not authenticate private JAR contents or independent proof "
            "and cannot authorize identity acceptance."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-dual-bundle-offline-verify")
    p.add_argument("--bundle-dir", required=True, type=Path)
    p.add_argument("--frontier", type=Path, default=Path("research/v309-field-recovery/frontier.json"))
    p.add_argument("--class-lineage", type=Path, default=Path("research/v309-field-recovery/class-lineage.json"))
    p.add_argument("--member-lineage", type=Path, default=Path("research/v309-field-recovery/member-lineage.json"))
    p.add_argument("--global-field-report", type=Path, default=Path("research/v309-field-recovery/global-field-usage.json"))
    args = p.parse_args(argv)
    try:
        frontier = _read_json_exact(args.frontier)
        for key, path in (
            ("class_lineage", args.class_lineage),
            ("member_lineage", args.member_lineage),
            ("global_field_usage", args.global_field_report),
        ):
            expected = frontier.get("files", {}).get(key, {}).get("sha256")
            _ensure(
                _is_sha(expected)
                and hashlib.sha256(path.read_bytes()).hexdigest() == expected.lower(),
                f"{key} tracked SHA-256 differs from pinned frontier",
            )
        actual_files = {p.name for p in args.bundle_dir.iterdir()}
        _ensure(
            actual_files == {
                "BUNDLE.json",
                "descriptor-class-research.json",
                "empty-field-declaration-research.json",
            },
            "unexpected files or missing evidence in dual bundle",
        )
        result = verify_v309_dual_bundle_offline(
            frontier, _read_json_exact(args.class_lineage),
            _read_json_exact(args.member_lineage),
            _read_json_exact(args.global_field_report),
            _read_json_exact(args.bundle_dir / "BUNDLE.json"),
            _read_json_exact(args.bundle_dir / "descriptor-class-research.json"),
            _read_json_exact(args.bundle_dir / "empty-field-declaration-research.json"),
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"SPK_V309_DUAL_BUNDLE_OFFLINE_VERIFY_FAIL: {exc}")
        return 1
    print("SPK_V309_DUAL_BUNDLE_OFFLINE_CONSISTENCY_PASS_NOT_PROOF")
    print(f"bundle_id={result['bundle_id']}")
    for key, value in result["descriptor_summary"].items():
        print(f"descriptor.{key}={value}")
    for key, value in result["empty_summary"].items():
        print(f"empty.{key}={value}")
    for row in result["crosslane_candidate_priorities"]:
        print(
            "crosslane." + row["old_canonical_class_id"] + "="
            + ("REPORTED_RESEARCH_CANDIDATE" if row["reported_index_witness_candidate"]
               else "UNPROVEN_ALIAS_ONLY")
            + " priority=" + str(row["research_priority_rows"])
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
