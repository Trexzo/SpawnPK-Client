"""R53 exact original-v309 aggregate must preserve unresolved String vetoes."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

_PATH = (Path(__file__).resolve().parents[1] /
         "research/v309-source-recovery/enum-helper-string-finals-r53.json")


class EnumHelperStringEvidenceTests(unittest.TestCase):
    def test_two_exact_helper_chains_but_three_strings_remain(self):
        x = json.loads(_PATH.read_text(encoding="utf-8"))
        self.assertEqual(x["schema_version"], 1)
        self.assertEqual(x["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(x["original_nonconstant_final_string_fields"], 5)
        self.assertEqual(x["direct_enum_helper_backed_string_fields"], 2)
        self.assertEqual(x["original_getstatic_invokestatic_putstatic_operand_chains_reproduced"], 2)
        self.assertTrue(x["exact_method_access_static"])
        self.assertFalse(x["original_branch_target_or_exception_entry_in_chains"])
        self.assertEqual(len(x["independently_reconstructed_private_source_fragment_sha256"]), 64)
        self.assertEqual(x["outstanding_dynamic_string_finals_without_verified_local_source_form"], 3)
        self.assertFalse(x["exact_enum_method_name_field_coordinate_published"])
        for k in (
            "github_r53_cli_replayed_on_private_original",
            "original_enum_helper_body_full_binary_parity_verified",
            "nested_enum_original_source_and_innerclasses_attributes_equivalent",
            "source_name_collision_resolved",
            "complete_original_clinit_reconstructed",
            "original_runtime_behavior_certified",
            "canonical_field_identifiers_accepted",
            "original_private_source_or_binary_published",
        ):
            self.assertFalse(x[k], k)


if __name__ == "__main__":
    unittest.main()
