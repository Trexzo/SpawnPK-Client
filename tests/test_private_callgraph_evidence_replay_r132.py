"""R132: independently pinned R127/R130/R131 graph replay bundle tests."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from spk_recovery.private_callgraph_evidence_replay_r132 import (
    CallGraphReplayR132Error,
    _private_report,
    replay_private_call_graph_evidence,
)


def digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


class PrivateCallGraphReplayR132Tests(unittest.TestCase):
    def setUp(self):
        self.proposals = [
            {"source_java_type": "rs/A", "original_jvm_class": "rs/a",
             "shape_sha256": "a" * 64},
            {"source_java_type": "rs/B", "original_jvm_class": "rs/b",
             "shape_sha256": "b" * 64},
            {"source_java_type": "rs/C", "original_jvm_class": "rs/c",
             "shape_sha256": "c" * 64},
        ]
        self.source_edges = [
            {"caller": "rs/A", "callee": "rs/B", "count": 2},
            {"caller": "rs/A", "callee": "rs/C", "count": 1},
        ]
        self.original_edges = [
            {"caller": "rs/a", "callee": "rs/b", "count": 2},
            {"caller": "rs/a", "callee": "rs/c", "count": 1},
        ]
        self.source_sha = "1" * 64
        self.original_sha = "2" * 64
        self.shape = {
            "schema_version": 1,
            "kind": "private_v309_java_ast_jvm_structural_singleton_proposals_r127",
            "source_zip_sha256": self.source_sha,
            "original_v309_jar_sha256": self.original_sha,
            "candidate_proposals_are_identity_accepted": False,
            "whole_client_deobfuscation_complete": False,
            "source_files_rewritten_or_built": False,
            "private_review_only_proposals": self.proposals,
            "private_proposal_manifest_sha256": digest(self.proposals),
            "unique_undecided_shape_proposals": 3,
        }
        self.jvm = {
            "schema_version": 1,
            "kind": "private_original_v309_jvm_invoke_edges_r130",
            "original_client_sha256": self.original_sha,
            "original_client_executed": False,
            "invokedynamic_callees_guessed": False,
            "original_source_identity_accepted": False,
            "private_original_call_edges": self.original_edges,
            "private_edge_manifest_sha256": digest(self.original_edges),
            "direct_rs_owner_edge_count": 2,
            "direct_rs_callsite_count": 3,
        }
        self.source = {
            "schema_version": 1,
            "kind": "private_source_ast_symbol_resolved_calls_r131",
            "source_archive_sha256": self.source_sha,
            "source_call_owners_symbol_resolved": True,
            "source_symbols_missing_or_ambiguous": False,
            "ambient_project_classpath_disabled": True,
            "original_game_binary_used_as_fallback": False,
            "source_game_code_executed": False,
            "source_game_classes_generated": False,
            "private_source_call_edges": self.source_edges,
            "private_source_call_edge_manifest_sha256": digest(
                self.source_edges),
            "source_direct_rs_call_edge_count": 2,
            "source_direct_rs_callsite_count": 3,
        }

    def replay(self, *, private=False):
        return replay_private_call_graph_evidence(
            self.shape, self.jvm, self.source,
            include_private_rows=private)

    def test_positive_two_anchor_replay_never_promotes_class_identity(self):
        report = self.replay(private=True)
        self.assertEqual(report["review_tier_counts"][
            "multi_anchor_call_corrob"], 1)
        self.assertEqual(report["original_jvm_edge_count"], 2)
        self.assertEqual(report["source_ast_edge_count"], 2)
        self.assertFalse(report["class_member_identity_accepted"])
        self.assertFalse(report["callgraph_equivalence_certified"])
        self.assertFalse(report["complete_client_deobfuscated_source_built"])
        self.assertEqual(len(report["private_review_only_rows"]), 3)

    def test_public_report_leaks_neither_class_names_nor_pairs(self):
        report = self.replay()
        s = json.dumps(report)
        self.assertNotIn("rs/A", s)
        self.assertNotIn("rs/a", s)
        self.assertNotIn("private_review_only_rows", report)

    def test_original_hash_mismatch_denies_replay(self):
        self.jvm["original_client_sha256"] = "3" * 64
        with self.assertRaisesRegex(
                CallGraphReplayR132Error,
                "INDEPENDENT_INPUT_SHA256_PINS_DISAGREE"):
            self.replay()

    def test_source_input_hash_mismatch_denies_replay(self):
        self.source["source_archive_sha256"] = "4" * 64
        with self.assertRaisesRegex(
                CallGraphReplayR132Error,
                "INDEPENDENT_INPUT_SHA256_PINS_DISAGREE"):
            self.replay()

    def test_tampered_original_edges_denied_by_manifest(self):
        self.original_edges[0]["count"] += 1
        with self.assertRaisesRegex(
                CallGraphReplayR132Error,
                "PRIVATE_EVIDENCE_MANIFEST_SHA_MISMATCH"):
            self.replay()

    def test_tampered_shape_pair_denied_by_manifest(self):
        self.proposals[0]["original_jvm_class"] = "rs/guess"
        with self.assertRaisesRegex(
                CallGraphReplayR132Error,
                "PRIVATE_EVIDENCE_MANIFEST_SHA_MISMATCH"):
            self.replay()

    def test_missing_real_source_symbol_authority_fails_closed(self):
        self.source["source_symbols_missing_or_ambiguous"] = True
        with self.assertRaisesRegex(
                CallGraphReplayR132Error,
                "R131_SOURCE_SYMBOL_AUTHORITY_INCOMPLETE"):
            self.replay()

    def test_original_binary_fallback_fails_closed(self):
        self.source["original_game_binary_used_as_fallback"] = True
        with self.assertRaisesRegex(
                CallGraphReplayR132Error,
                "R131_SOURCE_SYMBOL_AUTHORITY_INCOMPLETE"):
            self.replay()

    def test_no_accepted_mapping_can_enter_r127_bundle(self):
        self.shape["candidate_proposals_are_identity_accepted"] = True
        with self.assertRaisesRegex(
                CallGraphReplayR132Error,
                "R127_UNSUPPORTED_ACCEPTANCE_CLAIM"):
            self.replay()

    def test_edge_total_mismatch_fails_closed(self):
        self.jvm["direct_rs_callsite_count"] = 999
        with self.assertRaisesRegex(
                CallGraphReplayR132Error,
                "REPORTED_CALLSITE_COUNTS_DISAGREE"):
            self.replay()

    def test_duplicate_json_keys_fail_closed(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "original-private.json"
        path.write_text(
            '{"schema_version":1,"schema_version":1,'
            '"kind":"private_original_v309_jvm_invoke_edges_r130"}',
            encoding="utf-8")
        with self.assertRaisesRegex(
                CallGraphReplayR132Error,
                "PRIVATE_EVIDENCE_JSON_INVALID"):
            _private_report(
                path,
                "private_original_v309_jvm_invoke_edges_r130")
