"""R132 synthetic pinned three-evidence integration and no-acceptance tests."""
import hashlib
import json
import unittest

from spk_recovery.private_three_evidence_callgraph_replay_r132 import (
    PrivateThreeEvidenceR132Error,
    replay_three_private_call_evidences,
)


def digest(rows, *, ascii_only=True):
    return hashlib.sha256(json.dumps(
        rows, sort_keys=True, separators=(",", ":"),
        ensure_ascii=ascii_only).encode()).hexdigest()


class PrivateThreeEvidenceR132Tests(unittest.TestCase):
    def setUp(self):
        self.source_pin = "1" * 64
        self.original_pin = "2" * 64
        self.proposals = [
            {"source_java_type": "rs/A", "original_jvm_class": "rs/a",
             "shape_sha256": "3" * 64},
            {"source_java_type": "rs/B", "original_jvm_class": "rs/b",
             "shape_sha256": "4" * 64},
            {"source_java_type": "rs/C", "original_jvm_class": "rs/c",
             "shape_sha256": "5" * 64},
        ]
        self.source_edges = [
            {"caller": "rs/A", "callee": "rs/B", "count": 1},
            {"caller": "rs/A", "callee": "rs/C", "count": 2},
        ]
        self.original_edges = [
            {"caller": "rs/a", "callee": "rs/b", "count": 1},
            {"caller": "rs/a", "callee": "rs/c", "count": 2},
        ]
        self.shape = {
            "schema_version": 1,
            "kind":
                "private_v309_java_ast_jvm_structural_singleton_proposals_r127",
            "source_zip_sha256": self.source_pin,
            "original_v309_jar_sha256": self.original_pin,
            "private_class_names_included": True,
            "private_review_only_proposals": self.proposals,
            "private_proposal_manifest_sha256": digest(self.proposals),
        }
        self.jvm = {
            "schema_version": 1,
            "kind": "private_original_v309_jvm_invoke_edges_r130",
            "original_client_sha256": self.original_pin,
            "private_identifiers_included": True,
            "private_original_call_edges": self.original_edges,
            "edge_manifest_sha256": digest(
                self.original_edges, ascii_only=False),
        }
        self.ast = {
            "schema_version": 1,
            "kind": "private_v309_source_ast_attributed_call_edges_r131",
            "source_archive_sha256": self.source_pin,
            "private_identifiers_included": True,
            "private_source_call_edges": self.source_edges,
            "private_edge_manifest_sha256": digest(self.source_edges),
            "java_symbol_attribution_errors": 0,
            "unresolved_source_method_invocations": 0,
        }

    def replay(self, **opts):
        return replay_three_private_call_evidences(
            self.shape, self.jvm, self.ast, **opts)

    def test_two_matched_source_calls_are_only_review_witness(self):
        result = self.replay()
        self.assertEqual(result["review_only_candidate_pair_count"], 3)
        self.assertEqual(
            result["two_anchor_review_tier_counts"]["multi_anchor_call_corrob"],
            1)
        self.assertFalse(result["source_graph_semantically_equivalent_to_jvm"])
        self.assertEqual(result["accepted_client_class_mappings"], 0)
        self.assertFalse(result["fully_deobfuscated_client_certified"])
        self.assertNotIn("private_callgraph_review_rows", result)

    def test_source_errors_stay_visible_and_strict_mode_refuses(self):
        self.ast["java_symbol_attribution_errors"] = 13
        result = self.replay()
        self.assertFalse(result["source_symbol_resolution_exhaustive"])
        self.assertEqual(result["source_java_attribution_error_count"], 13)
        with self.assertRaisesRegex(
                PrivateThreeEvidenceR132Error,
                "SOURCE_SYMBOL_UNRESOLVED_STRICT_REPLAY_BLOCKED"):
            self.replay(require_no_errors=True)

    def test_original_and_source_pins_must_both_match(self):
        self.jvm["original_client_sha256"] = "9" * 64
        with self.assertRaisesRegex(
                PrivateThreeEvidenceR132Error,
                "THREE_EVIDENCE_INPUT_SHA256_MISMATCH"):
            self.replay()

    def test_source_edge_tamper_rejected_even_if_counts_unchanged(self):
        self.ast["private_source_call_edges"][0]["count"] = 2
        with self.assertRaisesRegex(
                PrivateThreeEvidenceR132Error,
                "R131_SOURCE_EDGE_MANIFEST_SHA256_INVALID"):
            self.replay()

    def test_original_edge_tamper_rejected(self):
        self.jvm["private_original_call_edges"][0]["count"] = 9
        with self.assertRaisesRegex(
                PrivateThreeEvidenceR132Error,
                "R130_ORIGINAL_EDGE_MANIFEST_SHA256_INVALID"):
            self.replay()

    def test_proposal_tamper_rejected(self):
        self.proposals[0]["shape_sha256"] = "6" * 64
        with self.assertRaisesRegex(
                PrivateThreeEvidenceR132Error,
                "R127_PROPOSAL_MANIFEST_SHA256_INVALID"):
            self.replay()

    def test_private_opt_in_does_not_certify_identity(self):
        result = self.replay(include_identifiers=True)
        self.assertEqual(len(result["private_callgraph_review_rows"]), 3)
        self.assertFalse(all(
            x["original_identity_accepted"] for x in
            result["private_callgraph_review_rows"]))

    def test_private_list_is_required(self):
        del self.ast["private_source_call_edges"]
        with self.assertRaisesRegex(
                PrivateThreeEvidenceR132Error,
                "THREE_EVIDENCE_PRIVATE_EDGE_LISTS_MISSING"):
            self.replay()
