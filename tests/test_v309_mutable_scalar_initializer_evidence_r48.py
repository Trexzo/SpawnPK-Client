"""R48 v309 private scalar initialization proof stays bounded, not runtime."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "research" / "v309-source-recovery"
R48 = ROOT / "mutable-scalar-initializers-r48.json"
R46 = ROOT / "mutable-scalar-declarations-r46.json"
R37 = ROOT / "frontier.json"


class V309ScalarInitializerAggregateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(R48.read_text(encoding="utf-8"))
        cls.r46 = json.loads(R46.read_text(encoding="utf-8"))
        cls.r37 = json.loads(R37.read_text(encoding="utf-8"))

    def test_original_pin_and_independent_r24_baseline(self):
        d = self.data
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(
            d["original_client_jar_sha256"],
            self.r37["original_client_jar_sha256"],
        )
        self.assertEqual(d["stable_owner_id"], self.r37["owner_stable_id"])
        self.assertEqual(
            d["independently_reproduced_r24_baseline_owner_sha256"],
            self.r37["private_candidate"]["compiled_class_sha256"],
        )
        for key in (
            "private_recompiled_owner_source_sha256",
            "private_recompiled_owner_class_sha256",
            "private_recompiled_candidate_jar_sha256",
        ):
            self.assertRegex(d[key], r"\A[0-9a-f]{64}\Z")

    def test_all_mutable_scalar_original_clinit_pairs_accounted_for(self):
        d = self.data
        self.assertEqual(d["target_java_release"], 9)
        self.assertEqual(d["original_owner_field_declarations"], 126)
        self.assertEqual(d["private_candidate_field_declarations"], 120)
        self.assertEqual(d["private_candidate_field_declarations_matching_original"], 120)
        self.assertEqual(d["original_owner_field_declarations_absent"], 6)
        self.assertEqual(
            d["original_mutable_scalar_fields_examined"], 80,
        )
        self.assertEqual(d["unique_original_clinit_static_scalar_stores"], 80)
        self.assertEqual(
            d["original_mutable_scalar_store_pairs_matched_after_recompile"], 80,
        )
        self.assertEqual(d["original_mutable_scalar_store_pairs_mismatched"], 0)
        self.assertEqual(d["distinct_mutable_scalar_fields_with_exact_original_initial_store"], 80)
        self.assertEqual(
            d["original_mutable_scalar_assignment_type_counts"],
            {"boolean": 72, "integer": 6, "string": 2},
        )
        self.assertEqual(
            d["original_mutable_boolean_literal_breakdown"],
            {"true": 31, "false": 41},
        )
        self.assertEqual(31 + 41, 72)
        self.assertEqual(72 + 6 + 2, 80)
        self.assertEqual(
            d["private_candidate_field_declarations"]
            + d["original_owner_field_declarations_absent"], 126,
        )
        self.assertEqual(
            d["original_mutable_scalar_fields_examined"],
            self.r46["newly_staged_mutable_scalar_declarations"] + 3,
        )
        self.assertEqual(d["original_r24_method_disassemblies_preserved"], 8)

    def test_no_full_runtime_or_source_acceptance_claim(self):
        d = self.data
        self.assertEqual(d["original_nested_enum_type_shells_still_unverified"], 3)
        self.assertEqual(d["original_dynamic_final_fields_still_missing"], 6)
        for flag in (
            "full_original_clinit_store_and_side_effect_order_reconstructed",
            "original_unrepresented_final_assignments_recovered",
            "original_nested_enum_constants_and_methods_reconstructed",
            "non_clinit_field_mutation_methods_recovered",
            "three_substantive_original_methods_recovered",
            "full_runtime_field_values_certified",
            "complete_source_or_stackmap_parity_certified",
            "canonical_owner_or_field_identity_accepted",
            "private_java_classfiles_or_original_values_published",
            "original_client_binary_modified",
            "github_r48_cli_executed_against_original_v309",
        ):
            self.assertIs(d[flag], False, flag)

    def test_no_original_field_values_or_jvm_coordinates_exposed(self):
        source = R48.read_text(encoding="utf-8")
        for restricted in (
            "rs/f/a", "rs.f.a", '"original_field_name"',
            '"raw_jvm_value"', '"java_source"', '"original_disassembly"',
            "public static boolean", "RIMMINGTON", "spawnpk.org",
        ):
            self.assertNotIn(restricted, source)


if __name__ == "__main__":
    unittest.main()
