"""R74 original 15/19 instruction protected helper source evidence is bounded."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

PATH=(Path(__file__).resolve().parents[1]/
      "research/v309-source-recovery/boolean-helper-source-r74.json")


class OriginalBooleanHelperSourceEvidenceTests(unittest.TestCase):
    def test_exact_two_helper_source_forms_and_remaining_two(self):
        x=json.loads(PATH.read_text(encoding="utf-8"))
        self.assertEqual(x["schema_version"],1)
        self.assertEqual(x["stable_owner_id"],"CLIENT_CLASS_000167")
        self.assertEqual(x["original_local_typed_exception_regions"],42)
        self.assertEqual(x["bounded_local_source_regions_through_R73"],38)
        self.assertEqual(x["original_R74_owner_boolean_helper_null_guard_regions"],1)
        self.assertEqual(x["original_R74_external_boolean_helper_before_field_write_regions"],1)
        self.assertEqual(len(x["original_R74_15_instruction_region_opcodes"]),15)
        self.assertEqual(len(x["original_R74_19_instruction_region_opcodes"]),19)
        self.assertTrue(x["original_15_op_nonnull_branch_only_calls_owner_static_helper_with_boolean"])
        self.assertTrue(x["original_19_op_both_branches_call_external_static_helper_before_field_write"])
        self.assertTrue(x["original_lookup_repeat_on_nonnull_branch_preserved"])
        self.assertTrue(x["original_R74_both_empty_Exception_handlers_verified"])
        self.assertEqual(x["bounded_original_local_source_regions_after_R74"],40)
        self.assertEqual(x["original_local_regions_remaining"],2)
        self.assertEqual(x["original_two_remaining_body_instruction_counts"],[23,36])
        for field in ("original_external_helper_original_source_behavior_recovered",
                      "R74_actual_v309_JAR_CLI_replay_verified",
                      "complete_697_instruction_original_java_source_compiled",
                      "original_client_runtime_equivalence_certified",
                      "private_original_member_names_literal_keys_or_binary_published"):
            self.assertFalse(x[field],field)

if __name__ == "__main__":
    unittest.main()
