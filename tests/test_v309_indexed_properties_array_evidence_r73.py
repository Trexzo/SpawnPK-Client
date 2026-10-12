"""R73 exact original indexed source evidence never certifies whole-method parity."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

PATH = (Path(__file__).resolve().parents[1] /
        "research/v309-source-recovery/indexed-properties-array-source-r73.json")


class IndexedOriginalV309EvidenceTests(unittest.TestCase):
    def test_original_index_loop_proven_with_four_remaining_regions(self):
        e = json.loads(PATH.read_text(encoding="utf-8"))
        self.assertEqual(e["schema_version"], 1)
        self.assertEqual(e["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(e["original_local_exception_regions"], 42)
        self.assertEqual(e["source_regions_previously_bounded_through_R72"], 37)
        self.assertEqual(e["original_R73_exact_indexed_integer_array_protected_regions"], 1)
        self.assertEqual(e["original_R73_protected_instruction_count"], 22)
        self.assertEqual(len(e["original_R73_for_loop_original_opcodes"]), 22)
        self.assertEqual(e["original_loop_array_getstatic_descriptor"], "[I")
        self.assertEqual(e["original_array_store_opcode"], "iastore")
        self.assertEqual(e["original_for_index_JVM_local_slot"], 3)
        self.assertTrue(e["original_two_dynamic_string_key_sites_same_original_bootstrap_index"])
        self.assertTrue(e["original_bootstrap_recipe_one_integer_placeholder_at_end"])
        self.assertEqual(e["original_string_concat_bootstrap_owner"],
                         "java/lang/invoke/StringConcatFactory")
        self.assertEqual(e["original_string_concat_bootstrap_name"],
                         "makeConcatWithConstants")
        self.assertEqual(e["bounded_local_source_regions_after_R73"], 38)
        self.assertEqual(e["original_local_exception_regions_unrecovered_after_R73"], 4)
        self.assertEqual(e["original_remaining_body_instruction_lengths"],
                         [15, 19, 23, 36])
        for key in (
            "original_concat_literal_recipe_published",
            "R73_private_original_JAR_CLI_replayed",
            "original_697_instruction_method_recompiled",
            "original_string_concat_runtime_equivalence_tested",
            "original_client_runtime_equivalence_certified",
        ):
            self.assertFalse(e[key], key)


if __name__ == "__main__":
    unittest.main()
