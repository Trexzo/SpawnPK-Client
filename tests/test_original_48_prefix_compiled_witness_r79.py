"""R79: independent original-JAR vs private Java9 prefix compilation witness."""
import json
from pathlib import Path
import unittest

E=(Path(__file__).resolve().parents[1] /
   "research/v309-source-recovery/original-48-prefix-compiled-witness-r79.json")

class OriginalPrefixProofTests(unittest.TestCase):
    def test_exact_48_prefix_compiled_only_and_no_whole_method_claim(self):
        p=json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(p["stable_owner_id"],"CLIENT_CLASS_000167")
        self.assertEqual(p["original_jvm_prefix_instruction_count"],48)
        self.assertEqual(p["candidate_java_release"],9)
        self.assertEqual(p["candidate_jvm_prefix_instruction_count"],48)
        self.assertEqual(p["original_to_candidate_prefix_difference_count"],0)
        self.assertEqual(p["original_prefix_static_field_assignments"],4)
        for key in (
            "exact_first_48_instruction_ordinal_and_byte_offset_parity",
            "exact_first_48_opcode_parity",
            "checked_string_member_field_and_type_operand_parity",
            "real_original_compared_via_independent_local_javap",
            "private_original_java_source_not_published",
        ):
            self.assertTrue(p[key], key)
        for key in (
            "original_preflight_helper_side_effect_equivalence_certified",
            "whole_697_instruction_method_compiled",
            "all_original_44_exception_handler_parity_passed",
            "complete_client_runtime_equivalence_certified",
            "generic_R79_private_cli_original_JAR_replayed",
        ):
            self.assertFalse(p[key], key)

if __name__=="__main__":
    unittest.main()
