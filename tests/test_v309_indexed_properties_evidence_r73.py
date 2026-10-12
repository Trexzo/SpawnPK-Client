"""R73 exact original indexed-loop bootstrap evidence stays bounded."""
import json
from pathlib import Path
import unittest

P = Path(__file__).resolve().parents[1] / "research/v309-source-recovery/indexed-properties-loop-r73.json"

class IndexedPropertiesEvidenceTests(unittest.TestCase):
    def test_exact_original_bootstrap_and_noncertification(self):
        e=json.loads(P.read_text(encoding="utf-8"))
        self.assertEqual(e["schema_version"],1)
        self.assertEqual(e["stable_owner_id"],"CLIENT_CLASS_000167")
        self.assertEqual(e["original_protected_jvm_instruction_count"],22)
        self.assertEqual(e["original_invokedynamic_site_count"],2)
        self.assertEqual(e["original_invokedynamic_descriptor"],"(I)Ljava/lang/String;")
        self.assertEqual(e["original_both_invokedynamic_bootstrap_index"],46)
        self.assertEqual(e["original_bootstrap_owner"],"java/lang/invoke/StringConcatFactory")
        self.assertEqual(e["original_bootstrap_method"],"makeConcatWithConstants")
        self.assertTrue(e["original_two_same_recipe"])
        self.assertEqual(e["original_getProperty_String_calls"],2)
        self.assertEqual(e["original_array_element_store_opcode"],"iastore")
        for k in ("original_private_key_prefix_published",
                  "generic_original_v309_R73_replay_completed",
                  "generated_original_complete_java_loop_source_compiled",
                  "whole_original_697_method_compiled",
                  "runtime_equivalence_certified"):
            self.assertFalse(e[k],k)
if __name__=="__main__":
    unittest.main()
