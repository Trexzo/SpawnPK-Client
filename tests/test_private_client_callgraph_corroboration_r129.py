"""R129 call-graph evidence is review-only; no class names accepted."""
import unittest

from spk_recovery.private_client_callgraph_corroboration_r129 import (
    CallGraphCorroborationR129Error,
    corroborate_source_original_call_edges,
)


class PrivateCallGraphR129Tests(unittest.TestCase):
    def setUp(self):
        self.proposals = [
            {"source_java_type": "rs/A", "original_jvm_class": "rs/x"},
            {"source_java_type": "rs/B", "original_jvm_class": "rs/y"},
            {"source_java_type": "rs/C", "original_jvm_class": "rs/z"},
        ]
        self.source = [
            {"caller": "rs/A", "callee": "rs/B", "count": 2},
            {"caller": "rs/A", "callee": "rs/C", "count": 1},
            {"caller": "rs/B", "callee": "rs/C", "count": 1},
        ]
        self.original = [
            {"caller": "rs/x", "callee": "rs/y", "count": 2},
            {"caller": "rs/x", "callee": "rs/z", "count": 1},
            {"caller": "rs/y", "callee": "rs/z", "count": 1},
        ]

    def test_two_corresponding_calls_are_only_review_corroboration(self):
        report = corroborate_source_original_call_edges(
            self.proposals, self.source, self.original)
        self.assertEqual(report["proposal_count"], 3)
        self.assertEqual(report["tier_counts"]["multi_anchor_call_corrob"], 1)
        self.assertFalse(report["source_original_names_accepted"])
        self.assertFalse(report["method_operand_parity_proven"])
        row = next(r for r in report["private_review_only_rows"]
                   if r["source_java_type"] == "rs/A")
        self.assertEqual(row["matched_anchored_callees"], 2)
        self.assertFalse(row["original_identity_accepted"])

    def test_one_missing_original_edge_is_a_contradiction(self):
        report = corroborate_source_original_call_edges(
            self.proposals, self.source, self.original[:1])
        self.assertEqual(
            report["tier_counts"]["anchored_call_contradiction"], 2)

    def test_call_count_shortage_is_a_contradiction(self):
        original = [dict(e) for e in self.original]
        original[0]["count"] = 1
        report = corroborate_source_original_call_edges(
            self.proposals, self.source, original)
        row = report["private_review_only_rows"][0]
        self.assertEqual(row["call_graph_evidence_tier"],
                         "anchored_call_contradiction")

    def test_unsupported_targets_do_not_count_as_anchors(self):
        extra = self.source + [{
            "caller": "rs/A", "callee": "org/unknown/Library", "count": 100
        }]
        report = corroborate_source_original_call_edges(
            self.proposals, extra, self.original)
        row = report["private_review_only_rows"][0]
        self.assertEqual(row["eligible_anchored_callees"], 2)

    def test_proposals_must_be_one_to_one(self):
        bad = self.proposals + [{
            "source_java_type": "rs/D", "original_jvm_class": "rs/x"
        }]
        with self.assertRaisesRegex(CallGraphCorroborationR129Error,
                                    "PROPOSALS_NOT_ONE_TO_ONE"):
            corroborate_source_original_call_edges(
                bad, self.source, self.original)

    def test_duplicate_edges_fail_closed(self):
        with self.assertRaisesRegex(CallGraphCorroborationR129Error,
                                    "SOURCE_EDGE_DUPLICATE"):
            corroborate_source_original_call_edges(
                self.proposals, self.source + self.source[:1],
                self.original)

    def test_negative_count_fail_closed(self):
        src = [dict(e) for e in self.source]
        src[0]["count"] = -1
        with self.assertRaisesRegex(CallGraphCorroborationR129Error,
                                    "SOURCE_EDGE_INVALID"):
            corroborate_source_original_call_edges(
                self.proposals, src, self.original)

    def test_inadequate_anchors_never_become_success(self):
        report = corroborate_source_original_call_edges(
            self.proposals, self.source, self.original,
            required_anchors=3)
        self.assertNotIn("multi_anchor_call_corrob",
                         report["tier_counts"])
        self.assertEqual(
            report["tier_counts"]["insufficient_anchored_calls"], 2)
