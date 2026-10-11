"""R66 original method CFG acceptance evidence is not a parity pass."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

E = (Path(__file__).resolve().parents[1] /
     "research/v309-source-recovery/large-method-cfg-acceptance-r66.json")

class V309LargeMethodAcceptanceEvidenceTests(unittest.TestCase):
    def test_original_697_and_364_method_frontier_unaccepted(self):
        x = json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(x["schema_version"], 1)
        self.assertEqual(x["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(x["original_larger_method_instructions"], 697)
        self.assertEqual(x["original_larger_method_ordered_static_writes"], 78)
        self.assertEqual(x["original_larger_method_explicit_branch_edges"], 120)
        self.assertEqual(x["original_larger_method_typed_exception_table_entries"], 44)
        self.assertEqual(x["original_other_complex_method_instructions"], 364)
        self.assertEqual(x["original_other_complex_method_typed_exception_table_entries"], 1)
        for key in (
            "comparison_requires_complete_private_original_candidate_sha256_pins",
            "comparison_requires_explicit_private_owner_field_aliases",
            "comparison_checks_full_JVM_opcode_ordinal_sequence_except_ldc_width",
            "comparison_checks_all_explicit_branch_destinations_by_instruction_ordinal",
            "comparison_checks_exception_ranges_and_catch_types_in_order",
            "comparison_checks_owner_mapped_static_field_write_order",
        ):
            self.assertTrue(x[key], key)
        for key in (
            "recompiled_private_large_original_method_available",
            "exact_697_instructions_and_44_handlers_compared_to_real_candidate",
            "exact_364_instruction_method_compared_to_real_candidate",
            "nonstatic_operand_constantpool_semantics_certified",
            "real_original_helper_method_side_effect_parity_certified",
            "original_java_source_equivalence_certified",
            "runtime_equivalence_certified",
            "private_original_member_aliases_or_source_published",
        ):
            self.assertFalse(x[key], key)

if __name__ == "__main__":
    unittest.main()
