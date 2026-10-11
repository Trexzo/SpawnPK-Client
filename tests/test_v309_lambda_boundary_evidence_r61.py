"""R61 original lambda-boundary evidence is not method implementation parity."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


_E = (Path(__file__).resolve().parents[1]
      / "research/v309-source-recovery/lambda-boundary-r61.json")


class OriginalV309LambdaBoundaryEvidenceTests(unittest.TestCase):
    def test_original_four_op_boundary_and_unrecovered_bodies(self):
        x = json.loads(_E.read_text(encoding="utf-8"))
        self.assertEqual(x["schema_version"], 1)
        self.assertEqual(x["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(x["original_jvm_method_inventory"], 10)
        self.assertEqual(x["short_methods_with_R60_bounded_source_forms"], 6)
        self.assertEqual(x["original_distinct_four_instruction_lambda_boundary_methods"], 1)
        self.assertEqual(x["lambda_boundary_instructions"], 4)
        self.assertEqual(x["verified_opcode_sequence"],
                         ["ldc", "invokedynamic", "invokestatic", "return"])
        self.assertEqual(x["invokedynamic_bootstrap_owner"],
                         "java/lang/invoke/LambdaMetafactory")
        self.assertEqual(x["invokedynamic_bootstrap_method"], "metafactory")
        self.assertTrue(x["invokedynamic_returns_functional_interface"])
        self.assertTrue(x["consumer_declared_with_string_and_exact_factory_interface_parameters"])
        self.assertEqual(x["original_full_complex_methods_remaining"], 2)
        self.assertEqual(x["remaining_complex_method_instruction_counts"], [364, 697])
        for name in (
            "private_original_four_op_lambda_witness_hash_generated_by_new_github_cli",
            "github_r61_private_original_jar_replay_verified",
            "lambda_implementation_method_body_reconstructed",
            "consumer_method_implementation_recovered",
            "original_bootstrap_method_execution_equivalent",
            "original_remaining_complex_method_sources_recovered",
            "full_original_class_source_or_runtime_equivalence_certified",
            "private_original_members_literals_or_binary_published",
        ):
            self.assertFalse(x[name], name)


if __name__ == "__main__":
    unittest.main()
