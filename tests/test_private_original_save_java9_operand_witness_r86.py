"""R86: private real original Jar->Java9 evidence is NOT a R86 replay pass."""
import json
from pathlib import Path
import unittest
E=(Path(__file__).resolve().parents[1]/
  "research/v309-source-recovery/private-save-java9-recompiled-canonical-operands-r86.json")

class PrivateOriginalJava9RecompiledWitness(unittest.TestCase):
    def test_all_364_canonical_insn_operands_and_nonclaims(self):
        e=json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(e["original_stable_owner_id"],"CLIENT_CLASS_000167")
        self.assertEqual(e["java_release"],9)
        self.assertEqual(e["private_compile_only_java_source_files"],6)
        self.assertEqual(e["original_jvm_instructions"],364)
        self.assertEqual(e["candidate_jvm_instructions"],364)
        self.assertEqual(
            e["ordinal_opcode_offset_and_javap_canonical_operand_differences"],0)
        self.assertEqual(e["checked_original_invokedynamic_bootstrap_recipe_sites"],46)
        self.assertEqual(e["checked_original_explicit_branch_sites"],9)
        self.assertTrue(e["original_candidate_typed_exception_table_equal"])
        self.assertTrue(e["original_candidate_original_owner_name_retained"])
        self.assertTrue(e["candidate_external_enums_and_helper_classes_synthetic"])
        self.assertTrue(e["original_SPK_original_bytecode_unmodified"])
        for k in ("candidate_compiled_against_original_dependency_implementations",
                  "exact_R66_R81_module_private_replay_completed",
                  "exact_R86_module_private_replay_completed",
                  "original_complete_owner_static_initializer_equivalent",
                  "original_nested_enum_binary_metadata_equivalent",
                  "client_runtime_and_file_io_side_effects_equivalent",
                  "private_java_source_class_names_and_original_keys_published"):
            self.assertFalse(e[k],k)

if __name__=="__main__":
    unittest.main()
