"""R72: original two-write reference and Boolean block remains research-only."""
import json
from pathlib import Path
import unittest

E = Path(__file__).resolve().parents[1] / "research/v309-source-recovery/dual-reference-boolean-source-r72.json"

class DualReferenceBooleanV309EvidenceTests(unittest.TestCase):
    def test_original_protected_two_write_region_and_remaining_five(self):
        x=json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(x["schema_version"],1)
        self.assertEqual(x["stable_owner_id"],"CLIENT_CLASS_000167")
        self.assertEqual(x["original_local_exception_protected_regions"],42)
        self.assertEqual(x["original_R67_R68_R71_bounded_protected_regions"],36)
        self.assertEqual(x["original_R72_reference_and_boolean_two_write_protected_regions"],1)
        self.assertEqual(x["original_R72_protected_instruction_count"],11)
        self.assertEqual(x["original_R72_exact_jvm_opcodes"],
                         ["aload_1","ldc","invokevirtual","invokestatic","putstatic",
                          "aload_1","ldc","invokevirtual","invokestatic","invokevirtual","putstatic"])
        self.assertEqual(x["original_R72_second_static_write_type"],"boolean")
        self.assertTrue(x["original_R72_first_conversion_result_equals_target_field_descriptor"])
        self.assertTrue(x["original_R72_protected_exception_catch_empty_and_normal_goto_skips_handler"])
        self.assertEqual(x["total_original_local_source_regions_bounded_after_R72"],37)
        self.assertEqual(x["original_local_exception_regions_remaining"],5)
        self.assertEqual(x["remaining_original_protected_instruction_lengths"],[22,15,19,23,36])
        for key in ("original_exact_nested_enum_java_source_name_collision_resolved",
                    "original_R72_generic_private_JAR_CLI_replayed",
                    "complete_original_697_instruction_method_compiled",
                    "real_original_helper_side_effect_and_runtime_parity",
                    "original_binary_strings_or_member_names_published"):
            self.assertFalse(x[key])

if __name__=="__main__":
    unittest.main()
