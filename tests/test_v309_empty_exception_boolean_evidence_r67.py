"""R67: original v309 empty-catch Boolean source forms, not runtime parity."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

DATA = (Path(__file__).resolve().parents[1] /
        "research/v309-source-recovery/empty-exception-boolean-regions-r67.json")


class OriginalEmptyCatchBooleanEvidenceTests(unittest.TestCase):
    def test_original_42_empty_catches_28_conditional_source_blocks(self):
        e = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertEqual(e["schema_version"], 1)
        self.assertEqual(e["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(e["original_large_method_instructions"], 697)
        self.assertEqual(e["original_large_method_exception_handler_count"], 44)
        self.assertEqual(e["original_exception_handler_type_counts"], {
            "java/lang/Exception": 42, "java/io/IOException": 2})
        self.assertTrue(e[
            "original_42_local_exception_handlers_have_single_astore_then_fallthrough_empty_catch"
        ])
        self.assertEqual(e[
            "original_exact_thirteen_instruction_conditional_boolean_protected_regions"
        ], 28)
        self.assertEqual(e["original_boolean_protected_regions_false_when_null"], 15)
        self.assertEqual(e["original_boolean_protected_regions_true_when_null"], 13)
        self.assertTrue(e["exact_original_lookup_string_equal_across_both_branches_in_all_28"])
        self.assertTrue(e["exact_original_lookup_virtual_member_equal_across_both_branches_in_all_28"])
        self.assertTrue(e["exact_original_static_boolean_field_equal_across_both_branches_in_all_28"])
        self.assertTrue(e["exact_original_all_28_gotos_bypass_catch_handler"])
        self.assertTrue(e["exact_original_nonnull_branch_repeats_virtual_lookup"])
        self.assertEqual(e["other_exception_local_regions_not_source_reconstructed"], 14)
        for flag in (
            "global_io_handler_java_source_reconstructed",
            "github_r67_original_private_jar_cli_replay_verified",
            "original_local_slot_one_java_type_recovered",
            "whole_original_697_instruction_method_compiled",
            "method_helper_side_effects_and_exception_parity_certified",
            "entire_client_source_or_runtime_equivalent",
            "private_original_field_names_literal_keys_and_jar_published",
        ):
            self.assertFalse(e[flag], flag)


if __name__ == "__main__":
    unittest.main()
