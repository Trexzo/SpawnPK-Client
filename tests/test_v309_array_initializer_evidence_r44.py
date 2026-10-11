"""R44: original-private array allocation proof is bounded and SHA pinned."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "research" / "v309-source-recovery"
EVIDENCE = ROOT / "int-array-initializer-r44.json"
FRONTIER = ROOT / "frontier.json"


class PrivateV309ArrayInitializerProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.baseline = json.loads(FRONTIER.read_text(encoding="utf-8"))

    def test_exact_private_original_and_baseline_pins(self):
        d, b = self.data, self.baseline
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["original_client_jar_sha256"],
                         b["original_client_jar_sha256"])
        self.assertEqual(d["original_owner_stable_id"], b["owner_stable_id"])
        self.assertEqual(d["r24_baseline_compiled_class_sha256"],
                         b["private_candidate"]["compiled_class_sha256"])
        for key in (
            "array_initialized_private_source_sha256",
            "array_initialized_private_compiled_class_sha256",
        ):
            self.assertRegex(d[key], r"\A[0-9a-f]{64}\Z")

    def test_one_array_initializer_prototype_preserves_existing_methods(self):
        d = self.data
        self.assertEqual(d["java_compile_release"], 9)
        self.assertEqual(d["measured_original_array_allocation_length"], 10)
        self.assertEqual(d["exact_original_array_allocation_opcode_count"], 3)
        self.assertEqual(d["matching_rebuilt_allocation_opcode_count"], 3)
        self.assertTrue(d["original_array_declared_static_final"])
        self.assertTrue(d["candidate_array_declared_static_final"])
        self.assertEqual(d["original_r24_candidate_field_declarations_before"], 4)
        self.assertEqual(d["prototype_candidate_field_declarations_after"], 4)
        self.assertEqual(d["original_r24_exact_field_metadata_matches_before"], 3)
        self.assertEqual(d["prototype_exact_field_metadata_matches_after"], 4)
        self.assertEqual(d["prototype_method_declarations_preserved"], 8)
        self.assertEqual(d["prototype_normalized_method_disassemblies_unchanged"], 8)
        self.assertEqual(d["original_remaining_field_declarations_still_missing"], 122)

    def test_not_a_complete_source_or_combined_r42_rebuild(self):
        for key in (
            "original_clinit_fully_reconstructed",
            "R42_thirty_three_literal_fields_applied_to_this_exact_prototype",
            "whole_original_method_parity_certified", "source_equivalence_certified",
            "runtime_equivalence_certified", "original_client_modified",
            "augmented_private_java_uploaded",
            "github_R44_verifier_executed_against_original_client",
        ):
            self.assertIs(self.data[key], False, key)

    def test_no_original_private_source_uploaded(self):
        src = EVIDENCE.read_text(encoding="utf-8")
        for item in ("rs/f/a", "rs.f.a", '"field_name"',
                     '"original_literal"', '"private_java_source"',
                     '"raw_bytecode"', "public static final int[]"):
            self.assertNotIn(item, src)


if __name__ == "__main__":
    unittest.main()
