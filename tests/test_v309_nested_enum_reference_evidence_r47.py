"""R47 private source-only enum reference proof; do not certify enum semantics."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "research" / "v309-source-recovery"
R47 = ROOT / "nested-enum-references-r47.json"
R46 = ROOT / "mutable-scalar-declarations-r46.json"
R37 = ROOT / "frontier.json"


class ExactOriginalNestedEnumBridgeAggregateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(R47.read_text(encoding="utf-8"))
        cls.r46 = json.loads(R46.read_text(encoding="utf-8"))
        cls.r37 = json.loads(R37.read_text(encoding="utf-8"))

    def test_exact_original_and_reproduced_r24_pins(self):
        d = self.data
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["stable_owner_id"], self.r37["owner_stable_id"])
        self.assertEqual(
            d["original_client_jar_sha256"],
            self.r37["original_client_jar_sha256"],
        )
        self.assertEqual(
            d["independently_reproduced_r24_compiled_owner_sha256"],
            self.r37["private_candidate"]["compiled_class_sha256"],
        )
        for key in (
            "r47_private_owner_java_sha256",
            "r47_private_compiled_owner_class_sha256",
            "r47_private_compiled_candidate_jar_sha256",
        ):
            self.assertRegex(d[key], r"\A[a-f0-9]{64}\Z")

    def test_five_nested_reference_fields_increase_coverage(self):
        d = self.data
        self.assertEqual(d["target_java_release"], 9)
        self.assertEqual(d["original_declared_owner_fields"], 126)
        self.assertEqual(
            d["previously_reported_r46_candidate_fields"],
            self.r46["candidate_field_declarations_after"],
        )
        self.assertEqual(d["verified_original_nested_enum_mutable_references_added"], 5)
        self.assertEqual(d["distinct_original_nested_enum_types_referenced"], 3)
        self.assertEqual(d["compile_only_nested_enum_shells"], 3)
        self.assertEqual(d["private_r47_compiled_owner_fields"], 120)
        self.assertEqual(d["original_owner_field_declarations_matching"], 120)
        self.assertEqual(d["original_owner_field_declarations_remaining_missing"], 6)
        self.assertEqual(
            d["private_r47_compiled_owner_fields"]
            + d["original_owner_field_declarations_remaining_missing"],
            d["original_declared_owner_fields"],
        )
        self.assertEqual(
            d["previously_reported_r46_candidate_fields"]
            + d["verified_original_nested_enum_mutable_references_added"],
            d["private_r47_compiled_owner_fields"],
        )
        self.assertEqual(
            d["remaining_missing_final_field_categories"],
            {"dynamic_final_string": 5, "dynamic_final_nested_enum": 1},
        )
        self.assertEqual(
            sum(d["remaining_missing_final_field_categories"].values()), 6,
        )
        self.assertEqual(d["compiled_candidate_class_entry_count"], 7)

    def test_eight_original_r24_methods_preserved(self):
        d = self.data
        self.assertEqual(d["original_r24_method_bodies_retained"], 8)
        self.assertEqual(
            d["identical_normalized_original_r24_method_instruction_sequences"], 8,
        )

    def test_stubbed_enum_types_never_claim_original_source(self):
        d = self.data
        for key in (
            "original_enum_constant_values_recovered",
            "original_nested_enum_method_bodies_recovered",
            "original_nested_enum_class_equivalence_certified",
            "original_clinit_full_initialization_equivalence_certified",
            "original_mutable_field_initialization_values_recovered",
            "three_original_substantive_method_bodies_recovered",
            "strict_whole_class_frame_and_method_parity_certified",
            "original_client_runtime_equivalence_certified",
            "canonical_class_or_field_identity_accepted",
            "proprietary_private_java_and_classfiles_published",
            "original_client_binary_modified",
            "github_r47_cli_executed_against_private_original",
        ):
            self.assertIs(d[key], False, key)
        self.assertIn("not recovered nested enum source", d["caveat"])

    def test_private_field_names_and_original_java_absent(self):
        source = R47.read_text(encoding="utf-8")
        for sensitive in (
            "rs/f/a", "rs.f.a", '"raw_obfuscated_field_name"',
            '"java_source"', '"enum_constants"', '"original_bytecode"',
            "public static rs.f.", "return a::",
        ):
            self.assertNotIn(sensitive, source)


if __name__ == "__main__":
    unittest.main()
