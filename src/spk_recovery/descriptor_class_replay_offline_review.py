from __future__ import annotations

"""Offline consistency review for a private v309 class replay result.

A valid self-consistent report is NOT independent class-index proof, an accepted
class mapping, or authority. Exact private indexes/JARs remain required to
recompute a candidate's cryptographic witness.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .descriptor_class_dependencies import build_descriptor_class_dependency_report
from .descriptor_class_private_jar_replay import (
    _read_json_exact,
    write_research_report_no_clobber,
)


class DescriptorClassOfflineReviewError(ValueError):
    pass


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _hex64(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdefABCDEF" for char in value)
    )


def _pinned(frontier: dict[str, Any], source: dict[str, Any]) -> None:
    if (
        frontier.get("kind") != "v309_recovery_frontier"
        or frontier.get("state") != "ACCEPTED_INCOMPLETE"
        or frontier.get("build_id") != "v309"
        or frontier.get("frontier", {}).get("unresolved") != 143
        or source.get("old_build_id") != "v308"
        or source.get("new_build_id") != "v309"
        or source.get("report_id") != frontier.get("files", {}).get(
            "global_field_usage", {}
        ).get("report_id")
    ):
        raise DescriptorClassOfflineReviewError("not the pinned accepted v309 frontier")
    exact = frontier.get("exact_clients", {})
    if any(
        not _hex64(exact.get(b + "_sha256"))
        or source.get(k + "_sha256", "").lower() != exact[b + "_sha256"].lower()
        for b, k in (("v308", "old"), ("v309", "new"))
    ):
        raise DescriptorClassOfflineReviewError("frontier exact client hashes differ")


def build_descriptor_class_offline_review(
    frontier: dict[str, Any],
    class_lineage: dict[str, Any],
    global_report: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, Any]:
    """Check the reported candidates' structure against tracked data, not JAR bytes."""
    if any(not isinstance(x, dict) for x in (frontier, class_lineage, global_report, replay)):
        raise DescriptorClassOfflineReviewError("inputs must be JSON objects")
    _pinned(frontier, global_report)
    expected_keys = {
        "report_id", "schema_version", "kind", "canonical", "state",
        "global_field_report_id", "global_field_report_digest",
        "class_lineage_digest", "old_index_sha256", "new_index_sha256",
        "dependency_report_digest", "summary", "candidates", "rejected", "note",
    }
    if set(replay) != expected_keys:
        raise DescriptorClassOfflineReviewError("unexpected replay report fields")
    if (
        replay["schema_version"] != 1
        or replay["kind"] != "v309_descriptor_class_verified_replay_research"
        or replay["canonical"] is not False
        or replay["state"] != "NO_CLASS_OR_MEMBER_IDENTITY_ACCEPTED"
        or replay["global_field_report_id"] != global_report["report_id"]
        or replay["global_field_report_digest"] != _digest(global_report)
        or replay["class_lineage_digest"] != _digest(class_lineage)
    ):
        raise DescriptorClassOfflineReviewError("replay source binding or state mismatch")
    bare = {k: v for k, v in replay.items() if k != "report_id"}
    if replay["report_id"] != "DESCCLASSREPLAY_" + _digest(bare)[:20].upper():
        raise DescriptorClassOfflineReviewError("replay content/report ID digest drift")
    hashes = frontier["exact_clients"]
    if (
        not _hex64(replay["old_index_sha256"])
        or not _hex64(replay["new_index_sha256"])
        or replay["old_index_sha256"].lower() != hashes["v308_sha256"].lower()
        or replay["new_index_sha256"].lower() != hashes["v309_sha256"].lower()
    ):
        raise DescriptorClassOfflineReviewError("unbound private index build hashes")
    dependencies = build_descriptor_class_dependency_report(global_report)
    if replay["dependency_report_digest"] != _digest(dependencies):
        raise DescriptorClassOfflineReviewError("descriptor inventory digest mismatch")
    groups = {
        d["old_canonical_class_id"]: d
        for d in dependencies["class_dependencies"]
    }
    owners: dict[str, str] = {}
    for c in class_lineage.get("classes", []):
        rows = [v for v in c["lineage"] if v["build_id"] == "v308"]
        if len(rows) == 1:
            owners[c["logical_id"]] = rows[0]["internal_name"]
    if set(groups) - set(owners):
        raise DescriptorClassOfflineReviewError("canonical old class owners unavailable")
    if not isinstance(replay["candidates"], list) or not isinstance(replay["rejected"], list):
        raise DescriptorClassOfflineReviewError("invalid candidate/rejection lists")

    allowed_candidate_keys = {
        "old_canonical_class_id", "old_class", "blocked_relationship_ids",
        "blocked_fields", "proposed_new_class", "strategy", "proof_fingerprint",
        "classification", "old_index_sha256", "new_index_sha256",
        "new_entry_sha256", "new_structural_sha256",
        "independent_global_uniqueness",
    }
    base_rejected_keys = {
        "old_canonical_class_id", "old_class", "blocked_relationship_ids",
        "blocked_fields", "reason",
    }
    paired_v309 = {
        item["internal_name"]
        for c in class_lineage.get("classes", [])
        for item in c["lineage"]
        if item["build_id"] == "v309"
    }
    covered: set[str] = set()
    proposed_new_classes: set[str] = set()
    candidates = []
    rejected = []
    for accepted, rows, output in (
        (True, replay["candidates"], candidates),
        (False, replay["rejected"], rejected),
    ):
        for row in rows:
            if not isinstance(row, dict):
                raise DescriptorClassOfflineReviewError("malformed replay row")
            cid = row.get("old_canonical_class_id")
            if cid not in groups or cid in covered:
                raise DescriptorClassOfflineReviewError("duplicate or unknown class group")
            covered.add(cid)
            group = groups[cid]
            if (
                row.get("old_class") != owners[cid]
                or row.get("blocked_fields") != group["blocked_fields"]
                or row.get("blocked_relationship_ids") != group["relationship_ids"]
            ):
                raise DescriptorClassOfflineReviewError("blocked class relationship drift")
            if accepted:
                if set(row) != allowed_candidate_keys:
                    raise DescriptorClassOfflineReviewError("unknown candidate proof or acceptance fields")
                name = row.get("proposed_new_class")
                strategy = row.get("strategy")
                proof = row.get("proof_fingerprint")
                if (
                    row.get("classification") != "RESEARCH_CANDIDATE_NOT_ACCEPTED"
                    or row.get("independent_global_uniqueness") is not True
                    or not isinstance(name, str)
                    or name in proposed_new_classes
                    or name in paired_v309
                    or ["L" + name + ";"] != group["new_raw_descriptors"]
                    or strategy not in (
                        "globally_unique_exact_entry_sha256",
                        "globally_unique_structural_sha256_research",
                    )
                    or not _hex64(proof)
                    or not _hex64(row.get("new_entry_sha256"))
                    or not _hex64(row.get("new_structural_sha256"))
                    or row.get("old_index_sha256", "").lower() != replay["old_index_sha256"].lower()
                    or row.get("new_index_sha256", "").lower() != replay["new_index_sha256"].lower()
                ):
                    raise DescriptorClassOfflineReviewError("unbound or unsupported candidate claim")
                matching = (
                    "new_entry_sha256"
                    if strategy == "globally_unique_exact_entry_sha256"
                    else "new_structural_sha256"
                )
                if proof.lower() != row[matching].lower():
                    raise DescriptorClassOfflineReviewError("candidate fingerprint inconsistency")
                proposed_new_classes.add(name)
                output.append({"old_canonical_class_id": cid, "proposed_new_class": name,
                               "blocked_fields": row["blocked_fields"], "strategy": strategy})
            else:
                extra = set(row) - base_rejected_keys
                if not base_rejected_keys.issubset(row) or extra not in (
                    set(), {"owner_logical_id"}, {"witness_new_class"}
                ):
                    raise DescriptorClassOfflineReviewError("unknown rejection or acceptance fields")
                reason = row.get("reason")
                if (
                    (reason == "new_class_already_owned" and extra != {"owner_logical_id"})
                    or (reason == "independent_witness_disagrees_with_field_descriptor"
                        and extra != {"witness_new_class"})
                    or (reason not in (
                        "new_class_already_owned",
                        "independent_witness_disagrees_with_field_descriptor",
                    ) and extra)
                ):
                    raise DescriptorClassOfflineReviewError("rejection details inconsistent")
                if row.get("reason") not in {
                    "class_already_paired_requires_replay",
                    "ambiguous_new_descriptor",
                    "non_rs_new_descriptor",
                    "referenced_new_class_absent_from_index",
                    "new_class_already_owned",
                    "no_independent_global_index_identity_witness",
                    "independent_witness_disagrees_with_field_descriptor",
                }:
                    raise DescriptorClassOfflineReviewError("unsupported rejection reason")
                rejected.append({"old_canonical_class_id": cid, "blocked_fields": row["blocked_fields"],
                                 "reason": row["reason"]})

    if covered != set(groups):
        raise DescriptorClassOfflineReviewError("not all descriptor class groups accounted for")
    total_candidates = sum(r["blocked_fields"] for r in candidates)
    total_rejected = sum(r["blocked_fields"] for r in rejected)
    expected_summary = {
        "input_class_dependencies": len(groups),
        "candidate_classes": len(candidates),
        "rejected_classes": len(rejected),
        "candidate_fields_blocked": total_candidates,
        "still_blocked_fields": total_rejected,
    }
    if replay["summary"] != expected_summary or len(groups) != 8 or total_candidates + total_rejected != 26:
        raise DescriptorClassOfflineReviewError("26/8 replay accounting drift")

    body = {
        "schema_version": 1,
        "kind": "v309_descriptor_class_replay_offline_consistency",
        "canonical": False,
        "state": "CONSISTENCY_ONLY_NOT_INDEPENDENT_PROOF_NO_IDENTITIES_ACCEPTED",
        "source_replay_id": replay["report_id"],
        "source_global_report_id": global_report["report_id"],
        "summary": expected_summary,
        "candidates": candidates,
        "rejected": rejected,
        "warning": (
            "Offline consistency cannot verify class-index uniqueness or JAR byte "
            "authenticity. Do not accept class/member identities from this output."
        ),
    }
    return {"review_id": "DESCCLASSOFFLINE_" + _digest(body)[:20].upper(), **body}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-class-replay-offline-review")
    p.add_argument("--frontier", type=Path, default=Path("research/v309-field-recovery/frontier.json"))
    p.add_argument("--class-lineage", type=Path, default=Path("research/v309-field-recovery/class-lineage.json"))
    p.add_argument("--global-field-report", type=Path, default=Path("research/v309-field-recovery/global-field-usage.json"))
    p.add_argument("--replay", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        inputs = [args.frontier, args.class_lineage, args.global_field_report]
        frontier = _read_json_exact(args.frontier)
        for key, path in zip(("class_lineage", "global_field_usage"), inputs[1:]):
            pinned = frontier.get("files", {}).get(key, {}).get("sha256")
            if not _hex64(pinned) or hashlib.sha256(path.read_bytes()).hexdigest() != pinned.lower():
                raise DescriptorClassOfflineReviewError(f"{key}: tracked SHA-256 mismatch")
        result = build_descriptor_class_offline_review(
            frontier, _read_json_exact(args.class_lineage),
            _read_json_exact(args.global_field_report), _read_json_exact(args.replay),
        )
        write_research_report_no_clobber(result, args.out, (
            args.frontier, args.class_lineage, args.global_field_report, args.replay,
        ))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"SPK_V309_CLASS_REPLAY_OFFLINE_REVIEW_FAIL: {exc}")
        return 1
    print("SPK_V309_CLASS_REPLAY_OFFLINE_CONSISTENCY_PASS_NOT_PROOF")
    print(f"review_id={result['review_id']}")
    for key, value in result["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
