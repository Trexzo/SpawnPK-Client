"""R85 same binary owner private JVM operand witness, with explicit nonclaims."""
import json
from pathlib import Path
import unittest

E=(Path(__file__).resolve().parents[1]/
   "research/v309-source-recovery/original-save-java9-same-owner-operand-witness-r85.json")
class SameOwnerMethodParityWitness(unittest.TestCase):
    def test_method_code_operands_exact_but_external_behavior_uncertified(self):
        e=json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(e["stable_original_owner_id"],"CLIENT_CLASS_000167")
        self.assertTrue(e["candidate_owner_internal_name_equals_original"])
        self.assertTrue(e["candidate_used_same_named_external_class_references"])
        self.assertTrue(e["candidate_uses_synthetic_external_class_implementations"])
        self.assertTrue(e["candidate_uses_synthetic_nested_enum_declarations"])
        self.assertEqual(e["original_method_instruction_count"],364)
        self.assertEqual(e["candidate_method_instruction_count"],364)
        self.assertEqual(e["original_candidate_method_code_bytes"],929)
        self.assertEqual(e["original_candidate_jvm_major"],53)
        self.assertEqual(e["original_candidate_private_static_method_access"],"0x000a")
        self.assertEqual(e["original_candidate_max_stack"],6)
        self.assertEqual(e["original_candidate_max_locals"],3)
        self.assertEqual(e["instruction_opcode_differences"],0)
        self.assertEqual(e["instruction_bytecode_offset_differences"],0)
        self.assertEqual(e["explicit_branch_count"],9)
        self.assertEqual(e["branch_target_offset_differences"],0)
        self.assertEqual(e["ordered_exception_table_entries"],1)
        self.assertTrue(e["original_candidate_exception_region_exact_start_end_handler_and_type"])
        self.assertEqual(e["original_candidate_string_concat_invokedynamic_sites"],46)
        self.assertEqual(e["string_concat_recipe_or_call_descriptor_differences"],0)
        self.assertEqual(e["non_dynamic_member_class_literal_reference_operands_checked"],179)
        self.assertEqual(e["non_dynamic_member_class_literal_reference_differences"],0)
        self.assertTrue(e["independent_original_vs_candidate_javap_verbose_comparison"])
        self.assertTrue(e["java9_javac_release_9_g_none_proc_none_success"])
        for key in ("original_method_stackmap_frame_encoding_binary_identical",
                    "complete_owner_126_field_declarations_and_static_initializer_exact",
                    "original_external_dependencies_or_enums_exactly_recovered",
                    "generic_R85_cli_original_jar_replay_passed",
                    "R66_R81_exact_original_candidate_tool_replay_completed",
                    "full_client_runtime_equivalence_certified",
                    "private_java_source_or_original_class_and_setting_identifiers_published"):
            self.assertFalse(e[key], key)

if __name__=="__main__":
    unittest.main()
