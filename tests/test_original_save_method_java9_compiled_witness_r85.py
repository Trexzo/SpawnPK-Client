"""R85 independent private compiled 364-op Java9 save-method witness (non-runtime)."""
import json
from pathlib import Path
import unittest

PATH=(Path(__file__).resolve().parents[1]/
      "research/v309-source-recovery/original-save-method-java9-compiled-witness-r85.json")

class OriginalSaveCompiledWitnessTests(unittest.TestCase):
    def test_exact_compiled_jvm_shape_and_explicit_external_alias_nonclaim(self):
        e=json.loads(PATH.read_text(encoding="utf-8"))
        self.assertEqual(e["stable_original_owner_id"],"CLIENT_CLASS_000167")
        self.assertEqual(e["original_method_jvm_instruction_count"],364)
        self.assertEqual(e["candidate_method_jvm_instruction_count"],364)
        self.assertEqual(e["original_method_code_length_bytes"],929)
        self.assertEqual(e["candidate_method_code_length_bytes"],929)
        self.assertEqual(e["candidate_java_release"],9)
        self.assertEqual(e["original_method_classfile_major"],53)
        self.assertEqual(e["candidate_method_classfile_major"],53)
        self.assertEqual(e["original_method_access_flags"],"0x000a")
        self.assertEqual(e["candidate_method_access_flags"],"0x000a")
        self.assertEqual(e["original_and_candidate_max_stack"],6)
        self.assertEqual(e["original_and_candidate_max_locals"],3)
        self.assertEqual(e["exact_opcode_ordinal_differences"],0)
        self.assertEqual(e["exact_bytecode_offset_differences"],0)
        self.assertEqual(e["explicit_branch_edges_checked"],9)
        self.assertEqual(e["explicit_branch_ordinal_target_differences"],0)
        self.assertEqual(e["original_exception_table_entries"],1)
        self.assertEqual(e["candidate_exception_table_entries"],1)
        self.assertTrue(e["original_candidate_exception_handler_start_end_and_handler_pc_identical"])
        self.assertEqual(e["original_and_candidate_exception_catch_type"],"java/lang/Exception")
        self.assertEqual(e["original_and_candidate_invokedynamic_sites"],46)
        self.assertEqual(e["original_candidate_java9_string_concat_bootstrap_recipe_differences"],0)
        self.assertEqual(e["original_candidate_string_ldc_value_differences"],0)
        self.assertEqual(e["original_candidate_checked_invoke_method_descriptor_differences"],0)
        self.assertTrue(e["compiled_from_independently_assembled_private_java_candidate"])
        self.assertTrue(e["candidate_uses_synthetic_non_original_class_and_enum_scaffolding"])
        for k in (
            "original_owner_class_identity_and_external_field_operand_parity_verified",
            "original_source_generated_by_R85_CLI_and_replayed",
            "original_full_method_source_authorial_identity_proven",
            "original_original_dependency_classes_and_helper_behavior_preserved",
            "original_java_class_and_nested_enum_metadata_exact",
            "runtime_or_file_system_side_effect_equivalence_certified",
            "original_jar_or_private_jvm_identifiers_and_literal_settings_keys_committed",
        ):
            self.assertFalse(e[k], k)

if __name__=="__main__":
    unittest.main()
