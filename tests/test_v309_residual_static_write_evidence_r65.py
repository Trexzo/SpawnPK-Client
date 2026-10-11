"""R65: actual v309 original residual-site inventory is not Java parity."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

_E = (Path(__file__).resolve().parents[1] /
      "research/v309-source-recovery/residual-static-write-shapes-r65.json")


class OriginalV309ResidualWriteEvidenceTests(unittest.TestCase):
    def test_original_78_static_writes_partition_37_plus_30_plus_11(self):
        d = json.loads(_E.read_text(encoding="utf-8"))
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(d["original_large_method_instructions"], 697)
        self.assertEqual(d["original_large_method_exception_table_entries"], 44)
        self.assertEqual(d["original_large_method_static_write_sites"], 78)
        self.assertEqual(d["independently_measured_R63_typed_value_chains"], 37)
        self.assertEqual(d["independently_measured_R64_boolean_null_guard_chains"], 30)
        self.assertEqual(d["independently_measured_residual_static_write_sites"], 11)
        self.assertEqual(37 + 30 + 11, 78)
        self.assertEqual(len(d["residual_opcode_shape_counts"]), 11)
        self.assertEqual(sum(d["residual_opcode_shape_counts"].values()), 11)
        self.assertEqual(set(d["residual_opcode_shape_counts"]), {
            "boolean_extract_and_notify",
            "nullable_boolean_extra_call",
            "two_string_key_boolean_conversion",
            "nullable_integer_immediate",
            "nullable_string_literal",
            "string_lookup_and_static_convert",
            "direct_string_lookup",
            "indexed_reference_helper",
            "direct_boolean_literal",
            "direct_null_reference",
            "direct_static_reference_copy",
        })
        self.assertEqual(d["original_residual_field_descriptor_bands"],
                         {"boolean": 4, "integer": 1, "reference": 6})
        self.assertTrue(
            d["all_78_static_write_sites_disjointly_partitioned_by_independent_original_disassembly"]
        )
        for flag in (
            "original_residual_source_names_or_literals_publicly_published",
            "github_R65_cli_replayed_on_actual_private_original_v309",
            "all_11_residual_site_cfg_handler_admissibility_rechecked_by_R65_cli",
            "all_11_residual_original_java_expressions_recovered",
            "original_remaining_exception_order_and_helper_side_effects_recovered",
            "original_method_source_compilation_equivalence_certified",
            "original_method_runtime_equivalence_certified",
        ):
            self.assertFalse(d[flag], flag)


if __name__ == "__main__":
    unittest.main()
