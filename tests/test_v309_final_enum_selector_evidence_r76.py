"""R76: 42 original local source patterns do NOT mean a recovered method."""
import json
from pathlib import Path
import unittest

E = Path(__file__).resolve().parents[1] / "research/v309-source-recovery/final-enum-selector-r76.json"

class FinalOriginalEnumSourceEvidenceTests(unittest.TestCase):
    def test_bounded_original_local_source_patterns_are_not_runtime_certified(self):
        e = json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(e["schema_version"], 1)
        self.assertEqual(e["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(e["original_local_exception_handler_regions"], 42)
        self.assertEqual(e["bounded_JVM_source_patterns_through_R75"], 41)
        self.assertEqual(e["original_R76_final_enum_setting_regions"], 1)
        self.assertEqual(e["original_R76_protected_JVM_instructions"], 36)
        self.assertEqual(len(e["original_R76_protected_opcode_sequence"]), 36)
        for key in (
            "original_same_Properties_getProperty_key_on_both_calls",
            "original_String_split_regex_identical_both_times",
            "original_String_split_invoked_twice_without_caching",
            "original_String_equalsIgnoreCase_enum_name_verified",
            "original_first_enum_store_then_getstatic_copy_second_store",
            "original_exception_handler_empty",
        ):
            self.assertTrue(e[key], key)
        self.assertEqual(
            e["all_original_42_local_protected_regions_have_bounded_source_pattern_after_R76"], 42)
        self.assertEqual(
            e["original_local_protected_regions_without_bounded_pattern_after_R76"], 0)
        self.assertTrue(e["private_original_property_literal_member_names_not_published"])
        for key in (
            "original_nested_enum_compilable_canonical_source_recovered",
            "generic_R76_cli_replayed_on_original_private_client_JAR",
            "actual_697_instruction_method_candidate_compiled",
            "whole_original_44_exception_entry_parity_passed",
            "all_original_method_operand_and_helper_side_effect_parity_passed",
            "full_client_source_or_runtime_equivalence_certified",
        ):
            self.assertFalse(e[key], key)

if __name__ == "__main__":
    unittest.main()
