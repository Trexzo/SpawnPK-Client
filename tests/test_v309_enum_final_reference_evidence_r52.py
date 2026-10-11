"""R52 original-v309 enumeration proof must not claim source parity."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

_E = (Path(__file__).resolve().parents[1] /
      "research/v309-source-recovery/enum-final-reference-source-r52.json")


class EnumFinalSourceEvidenceTests(unittest.TestCase):
    def test_one_original_enum_reference_pair_and_five_pending_strings(self):
        x = json.loads(_E.read_text(encoding="utf-8"))
        self.assertEqual(x["schema_version"], 1)
        self.assertEqual(x["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(x["original_static_final_without_constantvalue_total"], 8)
        self.assertEqual(
            x["original_dynamic_finals_previously_recovered_under_r44_r45"],
            {"int_array": 1, "boxed_integer": 1}
        )
        self.assertEqual(x["remaining_dynamic_final_fields"],
                         {"strings": 5, "nested_enum_references": 1})
        self.assertEqual(x["original_enum_reference_direct_getstatic_putstatic_pairs"], 1)
        self.assertTrue(x["original_enum_reference_store_at_class_initializer_start"])
        self.assertTrue(x["direct_reference_producer_descriptor_equals_target_descriptor"])
        self.assertFalse(x["local_branch_target_enters_micro_slice"])
        self.assertFalse(x["original_jvm_exception_handler_overlaps_micro_slice"])
        self.assertEqual(len(x["private_jvm_derived_source_fragment_sha256"]), 64)
        self.assertFalse(x["github_r52_cli_replayed_against_original_v309"])
        for veto in (
            "nested_enum_original_source_equivalence_certified",
            "enum_reference_java_compilation_against_original_enum_source_certified",
            "source_name_collision_resolved",
            "original_classfile_or_runtime_equivalence_certified",
            "five_remaining_string_initializer_sources_recovered",
            "canonical_owner_or_field_identity_accepted",
            "private_original_java_or_client_bytes_published",
        ):
            self.assertFalse(x[veto], veto)


if __name__ == "__main__":
    unittest.main()
