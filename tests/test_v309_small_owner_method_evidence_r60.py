"""R60 original-v309 small-method claims remain bounded and non-certifying."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

_PATH = (Path(__file__).resolve().parents[1] /
         "research/v309-source-recovery/small-owner-methods-r60.json")


class SmallOwnerMethodV309EvidenceTests(unittest.TestCase):
    def test_six_original_methods_not_nine_are_recoverable(self):
        e = json.loads(_PATH.read_text(encoding="utf-8"))
        self.assertEqual(e["schema_version"], 1)
        self.assertEqual(e["owner_stable_id"], "CLIENT_CLASS_000167")
        self.assertEqual(e["original_jvm_methods"], 10)
        self.assertEqual(e["original_non_clinit_methods"], 9)
        self.assertEqual(e["short_method_sources_accounted_for"], 6)
        self.assertEqual(e["source_form_counts"], {
            "default_constructor": 1,
            "constant_false_boolean": 2,
            "static_boolean_delegate": 1,
            "two_branch_boolean_toggle": 1,
            "array_element_writer": 1,
        })
        self.assertEqual(e["original_boolean_toggle_then_else_field_stores"], 8)
        self.assertEqual(e["original_array_writer_indexed_integer_stores"], 10)
        self.assertEqual(e["original_unrecovered_methods"], 3)
        self.assertEqual(e["remaining_method_instruction_counts"], [4, 364, 697])
        for key in (
            "original_source_bytes_published",
            "original_full_method_source_equivalent",
            "real_private_original_input_executed_via_r60_cli",
            "helper_external_side_effects_equivalent",
            "compiled_recovered_method_parity_certified",
            "full_original_client_runtime_equivalence_certified",
            "original_nested_enum_method_sources_equivalent",
        ):
            self.assertFalse(e[key], key)


if __name__ == "__main__":
    unittest.main()
