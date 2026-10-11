"""R57: 213 original instructions partitioned across 93 ordered writes."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

P = (Path(__file__).resolve().parents[1] /
     "research/v309-source-recovery/full-clinit-expression-partition-r57.json")


class WholeClinitV309EvidenceTests(unittest.TestCase):
    def test_original_bytecode_partition_is_bounded_and_not_certified(self):
        x = json.loads(P.read_text(encoding="utf-8"))
        self.assertEqual(x["schema_version"], 1)
        self.assertEqual(x["owner_stable_id"], "CLIENT_CLASS_000167")
        self.assertEqual(x["original_classfile_major"], 53)
        self.assertEqual(x["original_owner_declared_fields"], 126)
        self.assertEqual(x["original_clinit_instructions"], 213)
        self.assertEqual(x["original_clinit_owner_putstatic_writes"], 93)
        self.assertEqual(x["original_clinit_trailing_returns"], 1)
        self.assertEqual(x["original_write_pattern_counts"], {
            "direct": 84,
            "conditional_concat_string": 2,
            "enum_helper_string": 2,
            "boolean_reference_equality": 1,
            "boolean_negation": 1,
            "array": 1,
            "external_concat_string": 1,
            "boxed_integer": 1,
        })
        sizes = {
            "direct": 2,
            "conditional_concat_string": 8,
            "enum_helper_string": 3,
            "boolean_reference_equality": 7,
            "boolean_negation": 6,
            "array": 3,
            "external_concat_string": 3,
            "boxed_integer": 3,
        }
        self.assertEqual(sum(x["original_write_pattern_counts"].values()), 93)
        self.assertEqual(
            sum(x["original_write_pattern_counts"][k] * size
                for k, size in sizes.items()) + 1,
            213,
        )
        self.assertEqual(x["original_topology_branch_edges"], 8)
        for flag in (
            "private_original_complete_fragment_written_and_hash_verified_by_r57_cli",
            "private_original_fragment_compiled_into_candidate",
            "compiled_candidate_r56_complete_order_pass",
            "original_authorial_source_equivalence_certified",
            "jvm_bootstrap_operands_and_dependency_runtime_parity_certified",
            "private_original_class_names_strings_literals_published",
        ):
            self.assertFalse(x[flag], flag)


if __name__ == "__main__":
    unittest.main()
