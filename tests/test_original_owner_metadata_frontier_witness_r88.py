"""R88: exact original owner aggregate inventory; not full recovery."""
import json
from pathlib import Path
import unittest

E=Path(__file__).resolve().parents[1]/"research/v309-source-recovery/owner-original-candidate-metadata-frontier-r88.json"

class OriginalOwnerAggregateTests(unittest.TestCase):
    def test_unrecovered_member_frontier_and_no_runtime_claim(self):
        v=json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(v["original_owner_stable_id"],"CLIENT_CLASS_000167")
        self.assertEqual(v["original_field_declarations"],126)
        self.assertEqual(v["candidate_field_declarations"],46)
        self.assertEqual(v["matched_original_field_identities"],46)
        self.assertEqual(v["original_missing_field_identities"],80)
        self.assertEqual(v["candidate_extra_field_identities"],0)
        self.assertEqual(v["shared_field_declaration_modifier_differences"],2)
        self.assertEqual(v["original_method_declarations"],10)
        self.assertEqual(v["candidate_method_declarations"],5)
        self.assertEqual(v["matched_original_method_identities"],5)
        self.assertEqual(v["original_missing_method_identities"],5)
        self.assertEqual(v["candidate_extra_method_identities"],0)
        self.assertEqual(v["original_nested_classfile_entries"],4)
        self.assertEqual(v["candidate_nested_classfile_entries"],3)
        self.assertTrue(v["original_vs_candidate_field_and_method_inventory_independently_readonly_measured"])
        for name in (
            "actual_R88_python_module_private_replay_completed",
            "original_static_initializer_semantic_parity_proven",
            "original_external_helper_nested_enum_behavior_proven",
            "whole_client_runtime_equivalence_certified",
            "private_member_names_source_or_binary_published",
        ):
            self.assertFalse(v[name],name)

if __name__=="__main__":
    unittest.main()
