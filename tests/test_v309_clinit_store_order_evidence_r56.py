"""R56 guard: original-v309 initializer inventory is not candidate parity."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


_E = Path(__file__).resolve().parents[1] / "research/v309-source-recovery/clinit-store-order-r56.json"


class V309ClinitStoreOrderEvidenceTests(unittest.TestCase):
    def test_original_213_instructions_93_writes_and_explicit_vetoes(self):
        x = json.loads(_E.read_text(encoding="utf-8"))
        self.assertEqual(x["schema_version"], 1)
        self.assertEqual(x["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(x["original_owner_declared_fields"], 126)
        self.assertEqual(x["original_classfile_major_version"], 53)
        self.assertEqual(x["original_clinit_instruction_count"], 213)
        self.assertEqual(x["original_clinit_putstatic_count"], 93)
        self.assertEqual(x["original_clinit_getstatic_count"], 14)
        self.assertEqual(x["original_clinit_invokestatic_count"], 4)
        self.assertEqual(x["original_clinit_invokedynamic_count"], 3)
        self.assertEqual(x["original_clinit_explicit_branch_edge_count"], 8)
        self.assertEqual(x["original_clinit_control_flow_instruction_counts"],
                         {"if_acmpne": 3, "ifne": 1, "goto": 4})
        self.assertEqual(x["original_static_final_without_constantvalue_count"], 8)
        self.assertEqual(
            sum(x["original_dynamic_final_initialization_form_counts"].values()), 8
        )
        self.assertEqual(len(x["original_full_initializer_opcode_offset_projection_sha256"]), 64)
        for key in (
            "private_alias_map_and_recompiled_candidate_supplied",
            "github_r56_private_original_candidate_pair_replayed",
            "all_93_putstatic_mapped_equal_in_recompiled_candidate",
            "full_213_opcode_sequence_equal_in_recompiled_candidate",
            "full_branch_ordinal_topology_equal_in_recompiled_candidate",
            "constant_pool_arguments_and_helper_side_effects_equivalent",
            "complete_original_source_equivalent",
            "runtime_equivalent",
            "canonical_aliases_accepted",
            "private_jar_or_source_published",
        ):
            self.assertFalse(x[key], key)


if __name__ == "__main__":
    unittest.main()
