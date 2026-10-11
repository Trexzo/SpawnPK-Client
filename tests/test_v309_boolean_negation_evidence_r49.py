"""R49 exact original-v309 conditional Boolean recovery remains bounded."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "research" / "v309-source-recovery"
R49 = ROOT / "boolean-negation-initializer-r49.json"
R47 = ROOT / "nested-enum-references-r47.json"
R37 = ROOT / "frontier.json"


class V309OriginalBooleanNegationPrivateProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(R49.read_text(encoding="utf-8"))
        cls.r47 = json.loads(R47.read_text(encoding="utf-8"))
        cls.r37 = json.loads(R37.read_text(encoding="utf-8"))

    def test_original_and_private_source_pins(self):
        d = self.d
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["stable_owner_id"], self.r37["owner_stable_id"])
        self.assertEqual(
            d["original_client_jar_sha256"],
            self.r37["original_client_jar_sha256"],
        )
        for key in (
            "private_previous_78_scalar_source_class_sha256",
            "private_boolean_negation_source_sha256",
            "private_boolean_negation_class_sha256",
            "private_boolean_negation_jar_sha256",
        ):
            self.assertRegex(d[key], r"\A[a-f0-9]{64}\Z")

    def test_single_extra_conditional_initializer_verified(self):
        d = self.d
        self.assertEqual(d["compiler_release"], 9)
        self.assertEqual(
            d["private_candidate_field_declarations_exact"],
            self.r47["private_r47_compiled_owner_fields"],
        )
        self.assertEqual(d["original_owner_field_declarations"], 126)
        self.assertEqual(d["original_owner_fields_still_missing"], 6)
        self.assertEqual(d["original_mutable_scalar_fields"], 80)
        self.assertEqual(d["direct_literal_initializer_pairs_previously_recovered"], 78)
        self.assertEqual(d["newly_verified_conditional_boolean_negation_pairs"], 1)
        self.assertEqual(d["mutable_scalar_fields_with_verified_initialization_microparity"], 79)
        self.assertEqual(d["mutable_scalar_fields_with_unrecovered_initialization"], 1)
        self.assertEqual(d["original_conditional_boolean_negation_instructions"], 6)
        self.assertEqual(d["rebuilt_conditional_boolean_negation_instructions_matching"], 6)
        self.assertEqual(
            d["direct_literal_initializer_pairs_previously_recovered"]
            + d["newly_verified_conditional_boolean_negation_pairs"],
            d["mutable_scalar_fields_with_verified_initialization_microparity"],
        )
        self.assertEqual(79 + 1, 80)
        self.assertEqual(d["prior_r24_existing_method_disassemblies_preserved"], 8)

    def test_no_full_class_or_enum_source_acceptance(self):
        d = self.d
        self.assertTrue(d["remaining_conditional_field_depends_on_unrecovered_original_enum"])
        for key in (
            "full_original_clinit_method_instruction_parity_certified",
            "non_clinit_field_mutation_source_recovered",
            "nested_enum_type_shells_behavior_recovered",
            "final_six_original_dynamic_fields_recovered",
            "three_substantive_original_methods_recovered",
            "source_or_runtime_equivalence_certified",
            "canonical_identity_accepted",
            "original_client_binary_modified",
            "proprietary_source_and_original_field_names_published",
            "github_r49_cli_replayed_against_original_v309",
        ):
            self.assertIs(d[key], False, key)

    def test_no_original_private_names_or_values_in_public_record(self):
        contents = R49.read_text(encoding="utf-8")
        for word in (
            "rs/f/a", "rs.f.a", '"original_field_name"',
            '"java_source"', '"original_bytecode"',
            "public static boolean aw", "public static boolean ai",
            '"enum_constant_name"',
        ):
            self.assertNotIn(word, contents)


if __name__ == "__main__":
    unittest.main()
