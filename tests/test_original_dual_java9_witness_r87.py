"""R87 recorded private original-binary dual-method witness; no inflated runtime claim."""
import json
from pathlib import Path
import unittest

E=Path(__file__).resolve().parents[1]/"research/v309-source-recovery/original-dual-method-one-candidate-java9-witness-r87.json"

class DualMethodOriginalEvidenceTests(unittest.TestCase):
    def test_two_methods_single_private_binary_exact_and_runtime_false(self):
        j=json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(j["original_owner_stable_id"],"CLIENT_CLASS_000167")
        self.assertTrue(j["single_candidate_jar_used_for_both_methods"])
        self.assertTrue(j["method_bytecode_independent_javap_readonly_comparison_completed"])
        for label,size,branches,dynamic,handlers,writes in (
            ("loader",697,120,2,44,78),("saver",364,9,46,1,0)):
            self.assertEqual(j[f"{label}_original_instructions"],size)
            self.assertEqual(j[f"{label}_compiled_candidate_instructions"],size)
            self.assertEqual(j[f"{label}_canonical_jvm_operand_differences"],0)
            self.assertEqual(j[f"{label}_explicit_branches_checked"],branches)
            self.assertEqual(j[f"{label}_invokedynamic_sites_checked"],dynamic)
            self.assertEqual(j[f"{label}_typed_exception_entries_checked"],handlers)
            self.assertEqual(j[f"{label}_original_static_writes"],writes)
            self.assertTrue(j[f"{label}_typed_exception_table_exact"])
        self.assertTrue(j["synthetic_external_dependency_implementations_used"])
        for k in (
            "generic_R87_original_private_CLI_replay_passed",
            "original_complete_owner_126_field_metadata_and_initializer_recovered",
            "original_helper_and_enum_implementations_behavior_proven",
            "real_gameplay_and_filesystem_side_effects_equivalent",
            "whole_client_runtime_equivalence_certified",
            "private_original_names_keys_java_source_or_candidate_binary_committed",
        ):
            self.assertFalse(j[k],k)

if __name__=="__main__":
    unittest.main()
