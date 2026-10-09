from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

import spk_recovery.v309_multilane_concordance as m


def fixtures():
    old = "a" * 64
    new = "b" * 64
    ids = ["CLIENT_CLASS_%06d" % i for i in range(1, 9)]
    blocked = dict(zip(ids, [4, 4, 3, 3, 3, 3, 3, 3]))
    exact = {"v308_sha256": old, "v309_sha256": new}
    frontier = {
        "kind": "v309_recovery_frontier",
        "state": "ACCEPTED_INCOMPLETE", "build_id": "v309",
        "frontier": {"unresolved": 143, "descriptor_identity_guard_rejected": 26},
        "exact_clients": exact, "files": {
            "global_field_usage": {"report_id": "GLOBAL_1234"}
        },
    }
    lineage = {"builds": [
        {"build_id": "v308", "sha256": old},
        {"build_id": "v309", "sha256": new},
    ], "classes": []}
    global_report = {
        "kind": "global_field_usage_identity_candidates",
        "canonical": False, "report_id": "GLOBAL_1234",
        "summary": {"descriptor_identity_guard_rejected": 26},
        "review_outcomes": [{} for _ in range(143)],
        "old_sha256": old, "new_sha256": new,
    }
    deps = {
        "summary": {
            "blocked_fields": 26, "blocking_old_class_identities": 8,
        },
        "class_dependencies": [
            {"old_canonical_class_id": cid, "blocked_fields": blocked[cid]}
            for cid in ids
        ],
    }
    def lane(kind, prefix, candidates):
        return {
            "kind": kind, "report_id": prefix + "EXACT_REPORT",
            "canonical": False,
            "old_sha256": old, "new_sha256": new,
            "global_report_id": global_report["report_id"],
            "global_report_digest": m._digest(global_report),
            "class_lineage_digest": m._digest(lineage),
            "dependency_digest": m._digest(deps),
            "summary": {
                "input_class_dependencies": 8, "input_blocked_fields": 26,
                "candidate_classes": len(candidates),
                "rejected_classes": 8 - len(candidates),
                "candidate_blocked_fields": sum(blocked[cid] for cid in candidates),
                "remaining_blocked_fields": sum(blocked[cid] for cid in ids
                                                if cid not in candidates),
                "accepted_unresolved_fields": 143,
                "canonical_identities_accepted": 0,
            },
            "candidates": [
                {"old_canonical_class_id": cid, "blocked_fields": blocked[cid],
                 "internal_private_literal": "do-not-export-this"}
                for cid in ids if cid in candidates
            ],
            "rejected": [
                {"old_canonical_class_id": cid, "blocked_fields": blocked[cid]}
                for cid in ids if cid not in candidates
            ],
        }
    literal = lane("v309_changed_class_unique_literal_research",
                   "V309LITERAL_", set(ids[:5]))
    shape = lane("v309_changed_class_method_shape_research",
                 "V309METHODSHAPE_", set(ids[2:]))
    pair = {
        "kind": "v309_cp_method_referent_pairwise_research",
        "canonical": False, "report_id": "V309CPPAIR_EXACT_REPORT",
        "old_sha256": old, "new_sha256": new,
        "frontier_id": None, "global_report_id": global_report["report_id"],
        "summary": {
            "reviewed_descriptor_class_pairs": 8,
            "input_blocked_field_relationships": 26,
            "class_identities_accepted": 0,
            "member_identities_accepted": 0,
            "accepted_frontier_unresolved": 143,
        },
        "rows": [{
            "old_canonical_class_id": cid, "blocked_fields": blocked[cid],
            "unique_cp_semantic_method_matches": 3,
            "accepted_class_identifications": 0,
            "accepted_member_identifications": 0,
        } for cid in ids],
    }
    rivals = {
        "kind": "v309_cp_method_whole_archive_rival_research",
        "canonical": False, "report_id": "V309CPRIVALS_EXACT_REPORT",
        "old_sha256": old, "new_sha256": new,
        "source_cp_pair_report_id": pair["report_id"],
        "source_global_field_report_id": global_report["report_id"],
        "summary": {
            "examined_descriptor_classes": 8,
            "blocked_field_relationships_preserved": 26,
            "class_identities_accepted": 0,
            "member_identities_accepted": 0,
            "canonical_unresolved_fields": 143,
        },
        "rows": [{
            "old_canonical_class_id": cid, "blocked_fields": blocked[cid],
            "research_only": True, "canonical_identity_accepted": False,
            "state": "MUTUAL_WHOLE_ARCHIVE_SUPPORTED_SUBSET_RESEARCH_ONLY",
            "proposed_pair_unique_cp_method_matches": 3,
        } for cid in ids],
    }
    structural = {
        "kind": "v309_pinned_class_structural_drift_research",
        "canonical": False, "report_id": "V309STRUCTAUDIT_EXACT_REPORT",
        "exact_clients": exact,
        "state": "PINNED_STRUCTURAL_FINGERPRINTS_EXACT_MATCH_RESEARCH_ONLY",
        "summary": {
            "canonical_class_records_checked": 2221,
            "raw_pinned_sha_verified": 2221,
            "structural_hash_matches": 2221,
            "structural_hash_drifts": 0,
            "canonical_class_identities_accepted": 0,
            "canonical_member_identities_accepted": 0,
            "canonical_unresolved_field_relationships": 143,
        },
        "by_build": {
            "v308": {"pinned_records": 1129,
                     "exact_raw_entry_sha_matches": 1129,
                     "structural_hash_matches": 1129, "structural_hash_drifts": 0},
            "v309": {"pinned_records": 1092,
                     "exact_raw_entry_sha_matches": 1092,
                     "structural_hash_matches": 1092, "structural_hash_drifts": 0},
        },
    }
    return {
        "frontier": frontier, "lineage": lineage, "global_report": global_report,
        "literal": literal, "shape": shape, "cp_pair": pair,
        "cp_rivals": rivals, "structural": structural,
        "_deps": deps,
    }


class ResearchConcordanceTests(unittest.TestCase):
    def setUp(self):
        self.data = fixtures()

    def build(self, data=None):
        d = self.data if data is None else data
        with patch.object(m, "validate_lineage"):
            with patch.object(m, "build_descriptor_class_dependency_report",
                              return_value=d["_deps"]):
                return m.build_v309_multilane_concordance(
                    *(d[k] for k in (
                        "frontier", "lineage", "global_report", "literal",
                        "shape", "cp_pair", "cp_rivals", "structural",
                    ))
                )

    def test_independent_lanes_join_all_eight_without_identity_acceptance(self):
        report = self.build()
        self.assertEqual(report["summary"]["descriptor_class_groups"], 8)
        self.assertEqual(report["summary"]["blocked_field_relationships"], 26)
        self.assertEqual(report["summary"]["supported_subset_reviewable"], 8)
        self.assertEqual(report["summary"]["blocked_or_insufficient"], 0)
        self.assertEqual(report["summary"]["canonical_class_identities_accepted"], 0)
        self.assertEqual(report["summary"]["canonical_field_identities_accepted"], 0)
        self.assertEqual(report["summary"]["canonical_unresolved_field_relationships"], 143)
        self.assertFalse(report["canonical"])
        self.assertEqual(len(report["rows"]), 8)
        self.assertEqual(len({x["old_canonical_class_id"] for x in report["rows"]}), 8)

    def test_candidate_is_rejected_by_any_exact_cp_rival_veto(self):
        d = copy.deepcopy(self.data)
        d["cp_rivals"]["rows"][0]["state"] = "RIVAL_CLASS_CP_WITNESS_VETO"
        report = self.build(d)
        self.assertEqual(report["summary"]["supported_subset_reviewable"], 7)
        self.assertEqual(report["summary"]["blocked_or_insufficient"], 1)

    def test_three_cp_bearing_methods_required_even_when_other_lanes_agree(self):
        d = copy.deepcopy(self.data)
        d["cp_pair"]["rows"][0]["unique_cp_semantic_method_matches"] = 2
        report = self.build(d)
        self.assertEqual(report["summary"]["supported_subset_reviewable"], 7)

    def test_structural_drift_is_a_hard_stop_not_weak_review_score(self):
        d = copy.deepcopy(self.data)
        d["structural"]["state"] = "STRUCTURAL_FINGERPRINT_DRIFT_REVIEW_VETO"
        d["structural"]["summary"]["structural_hash_drifts"] = 1
        with self.assertRaisesRegex(m.V309ConcordanceError, "structural hash"):
            self.build(d)

    def test_bad_global_report_proof_digest_blocks_join(self):
        d = copy.deepcopy(self.data)
        d["literal"]["global_report_digest"] = "0" * 64
        with self.assertRaisesRegex(m.V309ConcordanceError, "digest drift"):
            self.build(d)

    def test_bad_lineage_proof_digest_blocks_join(self):
        d = copy.deepcopy(self.data)
        d["shape"]["class_lineage_digest"] = "9" * 64
        with self.assertRaisesRegex(m.V309ConcordanceError, "digest drift"):
            self.build(d)

    def test_changed_cp_report_id_rejects_chained_rival_evidence(self):
        d = copy.deepcopy(self.data)
        d["cp_rivals"]["source_cp_pair_report_id"] = "V309CPPAIR_OTHER"
        with self.assertRaisesRegex(m.V309ConcordanceError, "chain broken"):
            self.build(d)

    def test_duplicate_candidate_class_id_rejects_overlap(self):
        d = copy.deepcopy(self.data)
        d["literal"]["rejected"][0]["old_canonical_class_id"] = (
            d["literal"]["candidates"][0]["old_canonical_class_id"])
        with self.assertRaisesRegex(m.V309ConcordanceError, "missing, repeated"):
            self.build(d)

    def test_field_group_count_mismatch_is_fatal(self):
        d = copy.deepcopy(self.data)
        d["cp_rivals"]["rows"][1]["blocked_fields"] = 99
        with self.assertRaisesRegex(m.V309ConcordanceError, "unbalanced"):
            self.build(d)

    def test_missing_group_report_is_not_a_negative_or_a_positive(self):
        d = copy.deepcopy(self.data)
        d["cp_pair"]["rows"].pop()
        with self.assertRaisesRegex(m.V309ConcordanceError, "eight-row"):
            self.build(d)

    def test_incompatible_exact_client_build_is_rejected(self):
        d = copy.deepcopy(self.data)
        d["cp_pair"]["new_sha256"] = "f" * 64
        with self.assertRaisesRegex(m.V309ConcordanceError, "pinned client"):
            self.build(d)

    def test_frontier_142_unresolved_is_not_silently_accepted(self):
        d = copy.deepcopy(self.data)
        d["frontier"]["frontier"]["unresolved"] = 142
        with self.assertRaisesRegex(m.V309ConcordanceError, "143/26"):
            self.build(d)

    def test_an_accepted_identity_in_input_is_immediately_rejected(self):
        d = copy.deepcopy(self.data)
        d["cp_pair"]["rows"][2]["accepted_class_identifications"] = 1
        with self.assertRaisesRegex(m.V309ConcordanceError, "noncanonical"):
            self.build(d)

    def test_output_never_contains_private_witness_string(self):
        blob = json.dumps(self.build())
        self.assertNotIn("do-not-export-this", blob)
        self.assertNotIn("Methodref", blob)
        self.assertNotIn("private literal", blob)

    def test_report_is_deterministic_and_input_objects_unchanged(self):
        before = repr(self.data)
        a, b = self.build(), self.build()
        self.assertEqual(a, b)
        self.assertEqual(before, repr(self.data))


if __name__ == "__main__":
    unittest.main()
