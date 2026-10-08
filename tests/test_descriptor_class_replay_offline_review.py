from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from spk_recovery.descriptor_class_dependencies import build_descriptor_class_dependency_report
from spk_recovery.descriptor_class_replay_offline_review import (
    DescriptorClassOfflineReviewError,
    build_descriptor_class_offline_review,
)


ROOT = Path(__file__).resolve().parents[1] / "research" / "v309-field-recovery"


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _fixture():
    frontier = json.loads((ROOT / "frontier.json").read_text(encoding="utf-8"))
    lineage = json.loads((ROOT / "class-lineage.json").read_text(encoding="utf-8"))
    global_report = json.loads((ROOT / "global-field-usage.json").read_text(encoding="utf-8"))
    groups = build_descriptor_class_dependency_report(global_report)
    owners = {
        c["logical_id"]: next(
            r["internal_name"] for r in c["lineage"] if r["build_id"] == "v308"
        )
        for c in lineage["classes"]
        if any(r["build_id"] == "v308" for r in c["lineage"])
    }
    rejected = [
        {
            "old_canonical_class_id": row["old_canonical_class_id"],
            "old_class": owners[row["old_canonical_class_id"]],
            "blocked_relationship_ids": row["relationship_ids"],
            "blocked_fields": row["blocked_fields"],
            "reason": "no_independent_global_index_identity_witness",
        }
        for row in groups["class_dependencies"]
    ]
    body = {
        "schema_version": 1,
        "kind": "v309_descriptor_class_verified_replay_research",
        "canonical": False,
        "state": "NO_CLASS_OR_MEMBER_IDENTITY_ACCEPTED",
        "global_field_report_id": global_report["report_id"],
        "global_field_report_digest": _digest(global_report),
        "class_lineage_digest": _digest(lineage),
        "old_index_sha256": frontier["exact_clients"]["v308_sha256"],
        "new_index_sha256": frontier["exact_clients"]["v309_sha256"],
        "dependency_report_digest": _digest(groups),
        "summary": {
            "input_class_dependencies": 8,
            "candidate_classes": 0,
            "rejected_classes": 8,
            "candidate_fields_blocked": 0,
            "still_blocked_fields": 26,
        },
        "candidates": [],
        "rejected": rejected,
        "note": "Synthetic replay report for offline-consistency tests; not measured private proof.",
    }
    report = {"report_id": "DESCCLASSREPLAY_" + _digest(body)[:20].upper(), **body}
    return frontier, lineage, global_report, report, groups


def _rebind(report):
    body = {k: v for k, v in report.items() if k != "report_id"}
    report["report_id"] = "DESCCLASSREPLAY_" + _digest(body)[:20].upper()


class DescriptorClassReplayOfflineReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = _fixture()

    def test_tracked_frontier_all_rejections_consistency_not_proof(self):
        frontier, lineage, global_report, report, _ = self.base
        result = build_descriptor_class_offline_review(frontier, lineage, global_report, report)
        self.assertEqual(result, build_descriptor_class_offline_review(frontier, lineage, global_report, report))
        self.assertFalse(result["canonical"])
        self.assertEqual(result["state"], "CONSISTENCY_ONLY_NOT_INDEPENDENT_PROOF_NO_IDENTITIES_ACCEPTED")
        self.assertEqual(result["summary"]["input_class_dependencies"], 8)
        self.assertEqual(result["summary"]["still_blocked_fields"], 26)
        self.assertEqual(result["summary"]["candidate_classes"], 0)

    def test_replay_report_id_must_commit_to_contents(self):
        args = list(self.base[:4])
        args[3] = copy.deepcopy(args[3])
        args[3]["rejected"][0]["reason"] = "ambiguous_new_descriptor"
        with self.assertRaisesRegex(DescriptorClassOfflineReviewError, "digest drift"):
            build_descriptor_class_offline_review(*args)

    def test_malicious_canonical_state_rejected_even_with_updated_digest(self):
        args = list(self.base[:4])
        args[3] = copy.deepcopy(args[3])
        args[3]["canonical"] = True
        _rebind(args[3])
        with self.assertRaisesRegex(DescriptorClassOfflineReviewError, "state mismatch"):
            build_descriptor_class_offline_review(*args)

    def test_changed_blocked_relationships_rejected_even_with_updated_digest(self):
        args = list(self.base[:4])
        args[3] = copy.deepcopy(args[3])
        args[3]["rejected"][0]["blocked_relationship_ids"][0] = "FORGED"
        _rebind(args[3])
        with self.assertRaisesRegex(DescriptorClassOfflineReviewError, "relationship drift"):
            build_descriptor_class_offline_review(*args)

    def test_duplicate_class_row_rejected_even_with_updated_digest(self):
        args = list(self.base[:4])
        args[3] = copy.deepcopy(args[3])
        args[3]["rejected"][1]["old_canonical_class_id"] = args[3]["rejected"][0]["old_canonical_class_id"]
        _rebind(args[3])
        with self.assertRaisesRegex(DescriptorClassOfflineReviewError, "duplicate or unknown"):
            build_descriptor_class_offline_review(*args)

    def test_forged_index_sha_rejected_even_with_updated_digest(self):
        args = list(self.base[:4])
        args[3] = copy.deepcopy(args[3])
        args[3]["new_index_sha256"] = "f" * 64
        _rebind(args[3])
        with self.assertRaisesRegex(DescriptorClassOfflineReviewError, "index build hashes"):
            build_descriptor_class_offline_review(*args)

    def test_recomputed_digest_cannot_hide_unknown_state_fields(self):
        args = list(self.base[:4])
        args[3] = copy.deepcopy(args[3])
        args[3]["accepted_class_ids"] = ["CLIENT_CLASS_000029"]
        _rebind(args[3])
        with self.assertRaisesRegex(DescriptorClassOfflineReviewError, "unexpected replay report fields"):
            build_descriptor_class_offline_review(*args)

    def test_hidden_acceptance_field_in_rejection_is_rejected(self):
        args = list(self.base[:4])
        args[3] = copy.deepcopy(args[3])
        args[3]["rejected"][0]["accepted"] = True
        _rebind(args[3])
        with self.assertRaisesRegex(DescriptorClassOfflineReviewError, "unknown rejection"):
            build_descriptor_class_offline_review(*args)

    def test_rejection_detail_must_match_its_reason(self):
        args = list(self.base[:4])
        args[3] = copy.deepcopy(args[3])
        args[3]["rejected"][0]["reason"] = "new_class_already_owned"
        _rebind(args[3])
        with self.assertRaisesRegex(DescriptorClassOfflineReviewError, "rejection details inconsistent"):
            build_descriptor_class_offline_review(*args)

    def test_consistent_synthetic_candidate_is_not_independent_proof(self):
        args = list(self.base[:4])
        args[3] = copy.deepcopy(args[3])
        deps = self.base[4]["class_dependencies"]
        idx = next(i for i, g in enumerate(deps) if len(g["new_raw_descriptors"]) == 1)
        group = deps[idx]
        row = args[3]["rejected"].pop(idx)
        name = group["new_raw_descriptors"][0][1:-1]
        record = {
            **{k: row[k] for k in (
                "old_canonical_class_id", "old_class", "blocked_fields",
                "blocked_relationship_ids",
            )},
            "proposed_new_class": name,
            "strategy": "globally_unique_exact_entry_sha256",
            "proof_fingerprint": "1" * 64,
            "classification": "RESEARCH_CANDIDATE_NOT_ACCEPTED",
            "old_index_sha256": args[3]["old_index_sha256"],
            "new_index_sha256": args[3]["new_index_sha256"],
            "new_entry_sha256": "1" * 64,
            "new_structural_sha256": "2" * 64,
            "independent_global_uniqueness": True,
        }
        args[3]["candidates"] = [record]
        args[3]["summary"]["candidate_classes"] = 1
        args[3]["summary"]["rejected_classes"] = 7
        args[3]["summary"]["candidate_fields_blocked"] = row["blocked_fields"]
        args[3]["summary"]["still_blocked_fields"] = 26 - row["blocked_fields"]
        _rebind(args[3])
        result = build_descriptor_class_offline_review(*args)
        self.assertEqual(result["summary"]["candidate_classes"], 1)
        self.assertIn("NOT_INDEPENDENT_PROOF", result["state"])
        self.assertEqual(result["candidates"][0]["proposed_new_class"], name)

        args[3]["candidates"][0]["proof_fingerprint"] = "f" * 64
        _rebind(args[3])
        with self.assertRaisesRegex(DescriptorClassOfflineReviewError, "fingerprint inconsistency"):
            build_descriptor_class_offline_review(*args)


if __name__ == "__main__":
    unittest.main()
