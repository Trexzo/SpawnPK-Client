"""R80: pinned original binary aggregate layout proof, never source-parity claim."""
import json
from pathlib import Path
import unittest

E = (Path(__file__).resolve().parents[1] /
     "research/v309-source-recovery/original-697-stitch-layout-r80.json")

class OriginalStitchEvidenceTests(unittest.TestCase):
    def test_original_697_op_source_stitch_layout_and_nonclaims(self):
        e = json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(e["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(e["original_method_JVM_instructions"], 697)
        self.assertEqual(e["original_JVM_partition_instructions_accounted_for"], 697)
        self.assertEqual(sum(e[k] for k in (
            "original_prefix_JVM_instructions",
            "original_42_protected_regions_JVM_instructions",
            "original_local_skip_goto_JVM_instructions",
            "original_local_astore_catch_JVM_instructions",
            "original_outer_IO_tail_JVM_instructions",
        )), 697)
        self.assertEqual(e["original_prefix_static_writes"] +
                         e["original_protected_body_static_writes"], 78)
        self.assertEqual(e["original_local_typed_exception_entries"] +
                         e["original_outer_IO_exception_entries"], 44)
        for key in (
            "exact_original_42_local_ranges_form_one_contiguous_ordered_chain",
            "every_original_local_protected_region_followed_by_one_goto",
            "every_original_local_goto_skips_one_astore_3_handler",
            "all_original_goto_targets_land_after_local_handler",
            "exact_original_final_5_instruction_IO_epilogue_verified",
            "no_unsupported_inter_region_JVM_instruction",
            "independent_original_binary_readonly_JVM_inspection_completed",
        ):
            self.assertTrue(e[key], key)
        for key in (
            "generic_R80_private_source_site_original_JAR_replay_completed",
            "reconstructed_original_java_method_full_compilation_passed",
            "original_44_handler_candidate_parity_certified",
            "original_runtime_equivalence_certified",
            "private_original_member_names_property_keys_or_disassembly_published",
        ):
            self.assertFalse(e[key], key)

if __name__ == "__main__":
    unittest.main()
