"""R68 original direct protected-source evidence cannot claim runtime parity."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

E=(Path(__file__).resolve().parents[1]/
   "research/v309-source-recovery/direct-empty-catch-boolean-r68.json")

class OriginalDirectProtectedEvidenceTests(unittest.TestCase):
    def test_two_original_direct_boolean_regions_remain_noncertified(self):
        d=json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(d["schema_version"],1)
        self.assertEqual(d["stable_owner_id"],"CLIENT_CLASS_000167")
        self.assertEqual(d["original_local_typed_exception_handlers"],42)
        self.assertEqual(d["original_R67_conditional_primitive_protected_regions"],29)
        self.assertEqual(d["original_R68_direct_six_instruction_boolean_protected_regions"],2)
        self.assertEqual(d["original_local_exception_regions_after_R67_R68_without_java_source"],11)
        self.assertEqual(d["direct_original_six_opcodes"],
                         ["aload_1","ldc","invokevirtual","invokestatic",
                          "invokevirtual","putstatic"])
        self.assertEqual(d["both_original_conversion_return_types"],"java/lang/Boolean")
        self.assertEqual(d["both_original_unboxing_methods"],"booleanValue():Z")
        self.assertTrue(d["original_exact_both_direct_handlers_have_only_caught_exception_astore"])
        self.assertTrue(d["original_exact_both_direct_handler_goto_bypasses_catch"])
        for key in (
            "private_R68_original_v309_cli_replay_verified",
            "original_local_slot_one_java_type_recovered",
            "original_full_697_instruction_method_source_reconstructed",
            "original_helper_method_implementation_equivalent",
            "original_method_runtime_equivalent",
            "original_client_private_binary_or_literal_keys_published",
        ):
            self.assertFalse(d[key],key)

if __name__=="__main__":
    unittest.main()
