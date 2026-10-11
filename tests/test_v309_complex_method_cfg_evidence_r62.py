"""R62 original-v309 complex JVM method frontier remains read-only."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


_PATH = (Path(__file__).resolve().parents[1] /
         "research/v309-source-recovery/complex-method-cfg-frontier-r62.json")


class OriginalV309ComplexCfgEvidenceTests(unittest.TestCase):
    def test_original_complex_methods_and_provenance_vetoes(self):
        x = json.loads(_PATH.read_text(encoding="utf-8"))
        self.assertEqual(x["schema_version"], 1)
        self.assertEqual(x["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(x["large_method_count"], 2)
        big = x["largest_method"]
        self.assertEqual(big["jvm_instructions"], 697)
        self.assertEqual(big["static_field_writes"], 78)
        self.assertEqual(big["exception_handler_entries"], 44)
        self.assertEqual(big["explicit_conditional_and_unconditional_branches"], 120)
        self.assertEqual(len(big["opcode_sequence_sha256"]), 64)
        self.assertEqual(big["opcode_counts"]["goto"], 77)
        self.assertEqual(big["opcode_counts"]["ifnonnull"], 33)
        self.assertEqual(
            sum(big["opcode_counts"][op] for op in
                ("goto", "ifnonnull", "ifnull", "ifeq", "ifne", "if_icmpge")),
            120,
        )
        other = x["other_large_method"]
        self.assertEqual(other["jvm_instructions"], 364)
        self.assertEqual(other["static_field_writes"], 0)
        self.assertEqual(other["exception_handler_entries"], 1)
        self.assertEqual(other["opcode_counts"]["invokedynamic"], 46)
        self.assertTrue(x["jvm_opcode_counts_measured_from_exact_original"])
        for k in (
            "private_exact_method_name_descriptor_publicly_published",
            "private_cfg_atlas_generated_by_r62_cli_on_original_client",
            "original_method_java_try_catch_sources_recovered",
            "original_method_static_field_write_value_expressions_recovered",
            "original_dependency_method_bodies_verified",
            "runtime_equivalence_certified",
            "original_jar_or_method_strings_published",
        ):
            self.assertFalse(x[k], k)


if __name__ == "__main__":
    unittest.main()
