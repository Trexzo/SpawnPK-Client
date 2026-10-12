"""R95: pinned original v309 quartet observed independently, not certified source."""
import json
from pathlib import Path
import unittest
PATH=(Path(__file__).resolve().parents[1]/
      "research/v309-source-recovery/original-nested-four-innerclasses-evidence-r95.json")
class OriginalQuartetEvidenceTests(unittest.TestCase):
    def test_readonly_classfile_inventory_and_explicit_vetoes(self):
        a=json.loads(PATH.read_text(encoding="utf-8"))
        self.assertEqual(a["original_owner_stable_id"],"CLIENT_CLASS_000167")
        self.assertEqual(a["nested_original_classfile_count"],4)
        self.assertEqual(a["each_original_nested_classfile_major"],53)
        self.assertEqual(a["original_nested_classfile_sizes_bytes_sorted"],
                         [960,1010,1039,1165])
        self.assertTrue(a["each_nested_enum_ACC_PUBLIC_ACC_FINAL_ACC_SUPER_ACC_ENUM"])
        self.assertTrue(a["each_original_nested_enum_InnerClasses_attribute_present"])
        self.assertEqual(a["original_owner_InnerClasses_attribute_entries"],6)
        self.assertTrue(a["original_owner_four_nested_enum_entries_present"])
        self.assertEqual(a["original_owner_other_referenced_inner_entries"],2)
        self.assertTrue(a["original_binary_read_only_javap_independently_verified"])
        for key in (
            "all_four_nested_source_implementations_exactly_recompiled",
            "actual_R95_private_original_and_candidate_cli_replay_passed",
            "fourth_flattened_source_workaround_exact_nested_metadata_accepted",
            "original_nested_enum_helper_and_callback_runtime_equivalent",
            "original_client_runtime_equivalence_certified",
            "original_binary_or_private_member_identifiers_published",
        ):
            self.assertFalse(a[key],key)

if __name__=="__main__":
    unittest.main()
