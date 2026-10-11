"""R63 exact-original typed producer chain research is not source parity."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


_PATH = (Path(__file__).resolve().parents[1] /
         "research/v309-source-recovery/typed-static-write-chains-r63.json")


class OriginalV309TypedWriteChainEvidenceTests(unittest.TestCase):
    def test_thirty_seven_typed_chains_no_runtime_claim(self):
        d = json.loads(_PATH.read_text(encoding="utf-8"))
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(d["original_target_large_method_instructions"], 697)
        self.assertEqual(d["original_target_large_method_static_writes"], 78)
        self.assertEqual(d["original_exact_six_opcode_source_pattern"],
                         ["aload_1", "ldc", "invokevirtual",
                          "invokestatic", "invokevirtual", "putstatic"])
        self.assertEqual(d["raw_exact_six_opcode_chain_sites"], 37)
        self.assertTrue(d["all_37_chains_have_exact_input_output_JVM_descriptor_alignment"])
        self.assertEqual(d["exact_static_boolean_result_chains"], 32)
        self.assertEqual(d["exact_static_integer_result_chains"], 5)
        self.assertEqual(d["original_remaining_static_write_sites_not_of_this_pattern"], 41)
        for key in (
            "private_literal_and_original_member_coordinates_publicly_released",
            "original_local_slot_one_java_type_recovered",
            "original_exception_handler_and_branch_admissibility_for_all_37_verified_by_r63_cli",
            "private_actual_original_jar_replayed_against_r63_cli",
            "original_source_expression_reconstructed_and_compiled",
            "original_helper_method_behavior_proven",
            "original_large_method_runtime_equivalent",
        ):
            self.assertFalse(d[key], key)


if __name__ == "__main__":
    unittest.main()
