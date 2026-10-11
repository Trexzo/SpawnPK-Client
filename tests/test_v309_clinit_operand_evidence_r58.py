"""R58 original-v309 private compile evidence; no source/runtime certification."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

E = (Path(__file__).resolve().parents[1] /
     "research/v309-source-recovery/clinit-operand-private-skeleton-r58.json")


class V309PrivateOperandEvidenceTests(unittest.TestCase):
    def test_exact_private_jvm_operand_observations_and_vetoes(self):
        x = json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(x["schema_version"], 1)
        self.assertEqual(x["stable_original_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(x["original_owner_field_declarations"], 126)
        self.assertEqual(x["private_skeleton_owner_field_declarations"], 126)
        self.assertEqual(x["compiler_generated_jvm_initializer_instructions_original"], 213)
        self.assertEqual(x["compiler_generated_jvm_initializer_instructions_candidate"], 213)
        self.assertEqual(x["original_owner_putstatic_count"], 93)
        self.assertEqual(x["candidate_owner_putstatic_count"], 93)
        self.assertTrue(x["exact_93_target_field_names_and_descriptors_same_order"])
        self.assertTrue(x["original_and_candidate_branch_target_ordinals_equal"])
        self.assertEqual(x["branch_target_count"], 8)
        self.assertTrue(x["exact_14_getstatic_member_operands_identical"])
        self.assertTrue(x["exact_4_invokestatic_member_operands_identical"])
        self.assertTrue(x["exact_7_literal_constant_values_identical"])
        self.assertTrue(x["exact_3_stringconcatfactory_recipe_contents_identical"])
        self.assertEqual(x["exact_opcode_sequence_differences"], [{
            "original_opcode": "ldc",
            "candidate_opcode": "ldc_w",
            "count": 2,
            "reason": "constant-pool index width",
        }])
        self.assertTrue(x["all_other_211_instruction_opcodes_identical"])
        self.assertFalse(x["strict_r56_exact_opcode_gate_passed"])
        for key in (
            "original_static_final_constvalue_metadata_preserved_in_skeleton",
            "original_nested_enum_binary_and_methods_restored_in_skeleton",
            "github_r58_cli_executed_on_private_pair",
            "all_external_helper_method_bodies_equivalent",
            "innerclasses_attribute_equivalence_certified",
            "original_java_source_equivalence_certified",
            "runtime_equivalence_certified",
            "private_source_or_original_jar_published",
        ):
            self.assertFalse(x[key], key)


if __name__ == "__main__":
    unittest.main()
