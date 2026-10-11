"""R50 public aggregate evidence guards: no original JVM identities leaked."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


_ROOT = Path(__file__).resolve().parents[1]
_EVIDENCE = _ROOT / "research/v309-source-recovery/boolean-join-shape-r50.json"


class OriginalV309BooleanJoinEvidenceTests(unittest.TestCase):
    def test_two_real_original_v309_join_shapes_distinct_from_cli_replay(self):
        data = json.loads(_EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(len(data["original_client_jar_sha256"]), 64)
        self.assertEqual(data["owner_identified_by_exact_classfile_structure"]["matching_original_class_count"], 1)
        self.assertEqual(data["branch_targeted_putstatic_stores"], 2)
        self.assertEqual(data["branch_join_short_diamonds_exactly_matching_shape"], 2)
        self.assertEqual(data["original_clinit_instruction_count"], 213)
        shapes = data["local_conditional_branches"]
        self.assertEqual([row["predicate_branch_opcode"] for row in shapes],
                         ["if_acmpne", "ifne"])
        self.assertTrue(all(row["fallthrough_boolean"] is True for row in shapes))
        self.assertTrue(all(row["branch_taken_boolean"] is False for row in shapes))
        self.assertTrue(all(row["exclusive_expected_incoming_edges"] is True
                            for row in shapes))
        self.assertEqual(data["original_handler_regions_overlapping_diamonds"], 0)
        self.assertTrue(data["branch_values_and_edges_independently_observed"])
        self.assertFalse(data["github_r50_strict_parser_replayed_on_original_candidate_pair"])
        for veto in (
            "original_java_predicate_expressions_compiled",
            "original_class_initializer_complete",
            "original_source_equivalence_certified",
            "runtime_equivalence_certified",
            "canonical_identity_accepted",
            "original_binaries_or_source_published",
        ):
            self.assertFalse(data[veto], veto)

    def test_manifest_contains_no_original_field_names_or_raw_owner_paths(self):
        data = json.loads(_EVIDENCE.read_text(encoding="utf-8"))
        self.assertNotIn("private_witnesses", data)
        self.assertFalse(data["original_predicate_field_identity_published"])
        self.assertEqual(len(data["local_conditional_branches"]), 2)
        for row in data["local_conditional_branches"]:
            self.assertEqual(set(row) - {
                "index", "predicate_branch_opcode", "fallthrough_boolean",
                "branch_taken_boolean", "read_of_static_references_immediately_before_branch",
                "read_of_static_boolean_immediately_before_branch",
                "exclusive_expected_incoming_edges",
            }, set())


if __name__ == "__main__":
    unittest.main()
