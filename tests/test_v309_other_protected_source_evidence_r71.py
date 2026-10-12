"""R71 original bytecode source evidence; complete client remains unverified."""
import json
from pathlib import Path
import unittest

_E = Path(__file__).resolve().parents[1] / "research/v309-source-recovery/other-protected-region-sources-r71.json"

class OtherProtectedOriginalEvidenceTests(unittest.TestCase):
    def test_five_bounded_local_source_forms_six_remaining(self):
        e = json.loads(_E.read_text(encoding="utf-8"))
        self.assertEqual(e["schema_version"], 1)
        self.assertEqual(e["stable_original_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(e["original_697_instruction_owner_method_local_exception_regions"], 42)
        self.assertEqual(e["previously_bounded_R67_conditional_primitive_regions"], 29)
        self.assertEqual(e["previously_bounded_R68_direct_boolean_regions"], 2)
        self.assertEqual(e["original_R71_three_list_add_guarded_regions"], 3)
        self.assertEqual(e["original_R71_one_integer_conversion_guarded_region"], 1)
        self.assertEqual(e["original_R71_one_nullable_string_default_region"], 1)
        self.assertEqual(e["original_R71_total_protected_source_forms"], 5)
        self.assertEqual(e["original_total_bounded_local_source_regions_after_R71"], 36)
        self.assertEqual(e["original_local_exception_regions_not_source_reconstructed_after_R71"], 6)
        self.assertEqual(e["original_protected_region_opcode_lengths"],
                         {"guarded_list_add": 8,
                          "guarded_integer_conversion": 10,
                          "nullable_string_default": 11})
        self.assertEqual(e["original_six_remaining_local_body_instruction_lengths"],
                         [11, 22, 15, 19, 23, 36])
        self.assertEqual(29 + 2 + 5 + 6, 42)
        self.assertTrue(e["original_R71_all_five_exception_handlers_single_astore_and_no_catch_body"])
        self.assertTrue(e["original_R71_properties_getProperty_string_receiver_proven_from_R69"])
        for flag in ("private_original_literal_and_member_values_published",
                     "github_R71_complete_original_private_JAR_replayed",
                     "original_697_instruction_method_compiled",
                     "original_full_exception_and_helper_side_effect_parity",
                     "original_client_runtime_equivalence_certified"):
            self.assertFalse(e[flag], flag)

if __name__ == "__main__":
    unittest.main()
