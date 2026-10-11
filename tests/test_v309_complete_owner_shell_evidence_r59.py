"""R59 original-v309 exact private field shell evidence, no runtime claim."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

E = (Path(__file__).resolve().parents[1] /
     "research/v309-source-recovery/complete-owner-field-shell-r59.json")


class V309CompleteOwnerShellEvidenceTests(unittest.TestCase):
    def test_all_field_metadata_restored_but_external_methods_unverified(self):
        d = json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["stable_original_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(d["owner_classfile_major"], 53)
        self.assertEqual(d["owner_class_access_flags_hex"], "0031")
        self.assertEqual(d["original_declared_field_count"], 126)
        self.assertEqual(d["private_candidate_declared_field_count"], 126)
        self.assertEqual(d["original_static_final_count"], 41)
        self.assertEqual(d["original_constantvalue_fields"], 33)
        self.assertEqual(d["original_constantvalue_breakdown"],
                         {"boolean": 28, "integer": 4, "string": 1})
        self.assertEqual(d["original_static_final_blank_dynamic_fields"], 8)
        self.assertEqual(d["original_mutable_static_fields"], 85)
        self.assertEqual(d["original_fields_with_generic_signature"], 0)
        self.assertTrue(
            d["all_126_field_names_descriptors_access_flags_constantvalues_and_signatures_match_exactly"]
        )
        self.assertEqual(d["original_and_candidate_clinit_instruction_count"], 213)
        self.assertEqual(d["original_and_candidate_ordered_putstatic_count"], 93)
        self.assertTrue(
            d["all_93_original_and_candidate_putstatic_field_targets_match_exactly_in_order"]
        )
        self.assertTrue(d["all_eight_branch_destination_ordinals_equal"])
        self.assertEqual(d["only_opcode_width_differences"], {"ldc_to_ldc_w": 2})
        self.assertTrue(d["other_211_opcodes_identical"])
        for key in (
            "original_all_method_bodies_restored",
            "original_nested_enum_innerclasses_and_method_bodies_restored",
            "complete_original_source_equivalence_certified",
            "runtime_equivalence_certified",
            "strict_r56_raw_opcode_gate_pass",
            "github_r59_full_shell_cli_replayed_against_private_original",
            "private_original_strings_field_names_or_source_published",
        ):
            self.assertFalse(d[key], key)


if __name__ == "__main__":
    unittest.main()
