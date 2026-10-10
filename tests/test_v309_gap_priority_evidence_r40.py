"""R40: public aggregate evidence must retain private-source vetoes."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "v309-source-recovery" / "gap-priority-r40.json"
FRONTIER = ROOT / "research" / "v309-source-recovery" / "frontier.json"


class PrivateV309GapPriorityEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(PATH.read_text(encoding="utf-8"))
        cls.frontier = json.loads(FRONTIER.read_text(encoding="utf-8"))

    def test_class_fingerprints_match_exact_original_frontier(self):
        evidence, frontier = self.report, self.frontier
        self.assertEqual(evidence["schema_version"], 1)
        self.assertEqual(evidence["stable_owner_id"], frontier["owner_stable_id"])
        self.assertEqual(evidence["original_client_sha256"],
                         frontier["original_client_jar_sha256"])
        self.assertEqual(evidence["research_candidate_class_sha256"],
                         frontier["private_candidate"]["compiled_class_sha256"])
        self.assertEqual(evidence["original_declared_fields"],
                         frontier["private_candidate"]["original_field_declarations"])
        self.assertEqual(evidence["candidate_declared_fields"],
                         frontier["private_candidate"]["candidate_field_declarations"])
        self.assertEqual(evidence["missing_candidate_fields"],
                         frontier["private_candidate"]["missing_original_field_declarations"])
        self.assertEqual(evidence["unrecovered_substantive_method_count"],
                         frontier["private_candidate"]["original_substantive_method_bodies_unrecovered"])

    def test_three_missing_method_dependencies_are_self_consistent(self):
        evidence = self.report
        rows = evidence["methods"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            [r["role"] for r in rows],
            ["class_initializer", "unreconstructed_public_method",
             "save_dispatch_target_placeholder"],
        )
        self.assertEqual(
            [r["distinct_missing_candidate_field_dependencies"] for r in rows],
            [89, 42, 41],
        )
        self.assertEqual(
            [r["original_code_bytes"] for r in rows], [473, 1614, 929],
        )
        for row in rows:
            self.assertGreater(row["original_instruction_count"], 0)
            self.assertGreaterEqual(
                row["original_self_field_reference_sites"],
                row["missing_candidate_field_reference_sites"],
            )
            self.assertGreaterEqual(
                row["missing_candidate_field_reference_sites"],
                row["distinct_missing_candidate_field_dependencies"],
            )
            self.assertEqual(
                row["reads_original_fields"] + row["writes_original_fields"],
                row["original_self_field_reference_sites"],
            )
            self.assertLessEqual(
                row["distinct_missing_candidate_field_dependencies"],
                evidence["missing_candidate_fields"],
            )
            self.assertIs(row["recovered_body"], False)

    def test_no_silent_original_source_or_mapping_acceptance(self):
        evidence = self.report
        for key in (
            "original_binary_modified", "private_client_source_published",
            "canonical_owner_identity_accepted",
            "automatic_source_recovery_performed",
            "current_strict_recompiled_parity_of_unrecovered_methods_passed",
            "source_equivalence_certified",
        ):
            self.assertIs(evidence[key], False, key)
        self.assertIn("not strict R40", evidence["research_method"])
        self.assertIn("not semantic complexity",
                      evidence["method_priority_basis"])

    def test_no_private_class_coordinates_or_bytecode_in_json(self):
        text = PATH.read_text(encoding="utf-8")
        for restricted in (
            "rs/f/a", "rs.f.a", "public static void g(",
            '"original_source"', '"raw_jvm_method"',
            '"javap_dump"', '"bytecode_instructions"',
            "-----BEGIN PRIVATE KEY-----",
        ):
            self.assertNotIn(restricted, text)


if __name__ == "__main__":
    unittest.main()
