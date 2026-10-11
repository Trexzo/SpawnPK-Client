"""R45 private literal-free evidence of second nonconstant final initializer."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "research" / "v309-source-recovery"
R45 = ROOT / "boxed-integer-initializer-r45.json"
R42 = ROOT / "exact-constantvalue-r42.json"
R37 = ROOT / "frontier.json"


class V309BoxedIntegerSourceProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(R45.read_text(encoding="utf-8"))
        cls.r42 = json.loads(R42.read_text(encoding="utf-8"))
        cls.r37 = json.loads(R37.read_text(encoding="utf-8"))

    def test_source_and_original_jar_pins(self):
        d = self.d
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["original_client_jar_sha256"],
                         self.r37["original_client_jar_sha256"])
        self.assertEqual(d["stable_owner_id"], self.r37["owner_stable_id"])
        for k in (
            "private_combined_source_sha256",
            "private_compiled_class_sha256",
            "private_compiled_candidate_jar_sha256",
        ):
            self.assertRegex(d[k], r"\A[0-9a-f]{64}\Z")

    def test_exact_field_progress_beyond_r42(self):
        d = self.d
        previous = self.r42["private_r24_source_augmentation"]
        self.assertEqual(d["original_field_declarations"], 126)
        self.assertEqual(d["candidate_field_declarations"], 38)
        self.assertEqual(d["candidate_fields_with_exact_original_jvm_metadata"], 38)
        self.assertEqual(d["original_fields_still_missing"], 88)
        self.assertEqual(d["candidate_field_declarations"]
                         + d["original_fields_still_missing"], 126)
        self.assertEqual(
            d["candidate_field_declarations"],
            previous["candidate_fields_after"] + 1,
        )
        self.assertEqual(
            d["candidate_fields_with_exact_original_jvm_metadata"],
            previous["fields_with_exact_original_metadata_after"] + 2,
        )
        self.assertEqual(d["exact_original_constantvalue_attributes"], 33)
        self.assertEqual(d["exact_static_final_integer_array_allocation_opcodes"], 3)
        self.assertEqual(d["exact_static_final_boxed_integer_valueof_opcodes"], 3)
        self.assertEqual(d["verified_nonconstant_final_fields_recovered"], 2)
        self.assertEqual(d["original_nonconstant_final_fields_total"], 8)
        self.assertEqual(d["nonconstant_final_fields_remaining_unrecovered"], 6)
        self.assertEqual(
            d["remaining_nonconstant_final_type_counts"],
            {"string": 5, "other_reference": 1},
        )

    def test_eight_existing_method_bodies_still_unchanged(self):
        d = self.d
        self.assertEqual(d["compiler_target_release"], 9)
        self.assertEqual(d["candidate_method_declarations_preserved"], 8)
        self.assertEqual(d["candidate_method_disassemblies_unchanged"], 8)
        for key in (
            "class_initializer_full_bytecode_parity_certified",
            "full_method_stackmap_parity_recertified",
            "actual_original_literal_integer_published",
            "private_candidate_source_uploaded",
            "original_client_binary_modified",
            "full_source_runtime_equivalence_certified",
            "canonical_identity_accepted",
            "github_r45_verifier_run_against_private_original",
        ):
            self.assertIs(d[key], False, key)

    def test_no_private_field_names_or_literal_exposed(self):
        contents = R45.read_text(encoding="utf-8")
        for excluded in (
            "rs/f/a", "rs.f.a", '"field_name"', '"original_literal"',
            "public static final java.lang.Integer", '"raw_method"',
            '"java_source"', '"original_constantvalue"',
        ):
            self.assertNotIn(excluded, contents)


if __name__ == "__main__":
    unittest.main()
