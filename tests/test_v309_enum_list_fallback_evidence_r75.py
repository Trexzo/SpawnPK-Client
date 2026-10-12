"""R75 original enum/list/Boolean fallback source does not prove runtime."""
import json
from pathlib import Path
import unittest

E=Path(__file__).resolve().parents[1]/"research/v309-source-recovery/enum-list-fallback-r75.json"


class V309EnumListFallbackEvidenceTests(unittest.TestCase):
    def test_original_23_op_side_effects_with_one_block_remaining(self):
        d=json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(d["schema_version"],1)
        self.assertEqual(d["stable_owner_id"],"CLIENT_CLASS_000167")
        self.assertEqual(d["original_local_exception_regions"],42)
        self.assertEqual(d["bounded_local_source_forms_through_R74"],40)
        self.assertEqual(d["original_R75_external_enum_list_fallback_regions"],1)
        self.assertEqual(d["original_R75_protected_JVM_instructions"],23)
        self.assertEqual(len(d["original_R75_exact_opcodes"]),23)
        self.assertEqual(d["original_null_branch_list_add_calls"],2)
        self.assertTrue(d["original_null_branch_first_boolean_true"])
        self.assertTrue(d["original_null_branch_final_boolean_false"])
        self.assertTrue(d["original_null_branch_list_add_calls"])
        self.assertTrue(d["original_two_list_add_calls_same_original_static_list_field"])
        self.assertTrue(d["original_nonnull_branch_assigns_same_first_boolean_field"])
        self.assertEqual(d["bounded_local_source_forms_after_R75"],41)
        self.assertEqual(d["original_local_exception_regions_unrecovered_after_R75"],1)
        self.assertEqual(d["original_final_unrecovered_local_protected_body_instructions"],36)
        for k in (
            "external_original_nested_enum_source_name_parity_certified",
            "private_R75_actual_original_JAR_CLI_replayed",
            "complete_697_instruction_method_java_source_compiled",
            "original_external_helper_and_list_side_effects_runtime_equivalent",
            "original_binary_keys_and_original_names_publicly_published",
        ):
            self.assertFalse(d[k],k)

if __name__=="__main__":
    unittest.main()
