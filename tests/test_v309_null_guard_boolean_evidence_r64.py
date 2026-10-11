"""R64 original conditional boolean-source evidence preserves runtime vetoes."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


_E = (Path(__file__).resolve().parents[1] /
      "research/v309-source-recovery/null-guard-boolean-stores-r64.json")


class OriginalV309NullGuardEvidenceTests(unittest.TestCase):
    def test_thirty_null_boolean_store_micro_forms_and_eleven_remaining(self):
        e = json.loads(_E.read_text(encoding="utf-8"))
        self.assertEqual(e["schema_version"], 1)
        self.assertEqual(e["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(e["original_large_method_jvm_instructions"], 697)
        self.assertEqual(e["original_large_method_static_writes"], 78)
        self.assertEqual(e["original_exact_null_boolean_six_instruction_windows"], 30)
        self.assertEqual(e["original_true_literal_stores_when_lookup_is_null"], 14)
        self.assertEqual(e["original_false_literal_stores_when_lookup_is_null"], 16)
        self.assertTrue(e["original_lookups_return_reference_types"])
        self.assertTrue(e["original_jvm_null_branch_destination_beyond_putstatic"])
        self.assertTrue(
            e["original_none_of_30_windows_have_incoming_branch_or_handler_to_interior"]
        )
        self.assertEqual(e["original_post_store_next_opcode_counts"],
                         {"goto": 29, "getstatic": 1})
        self.assertEqual(
            e["original_remaining_static_writes_after_r63_and_r64_raw_shape_partition"],
            11
        )
        self.assertEqual(37 + 30 + 11, 78)
        for k in (
            "private_original_literals_or_member_names_publicly_exposed",
            "github_r64_cli_replayed_on_private_original_client",
            "original_local_slot_1_java_type_recovered",
            "full_java_try_catch_nesting_and_control_flow_recovered",
            "original_30_conditional_statements_compiled_and_replayed",
            "original_method_exception_side_effects_and_behavior_equivalent",
            "original_entire_client_runtime_equivalent",
        ):
            self.assertFalse(e[k], k)


if __name__ == "__main__":
    unittest.main()
