"""R78: independent exact-original evidence, no private source disclosure."""
import json
from pathlib import Path
import unittest

E = (Path(__file__).resolve().parents[1] /
     "research/v309-source-recovery/original-method-gaps-r78.json")

class OriginalGapEvidenceTests(unittest.TestCase):
    def test_original_partition_and_strict_nonclaims(self):
        e = json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(e["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(e["original_method_instructions"], 697)
        self.assertEqual(e["original_static_writes"], 78)
        self.assertEqual(e["original_explicit_branches"], 120)
        self.assertEqual(e["original_exception_handler_entries"], 44)
        self.assertEqual(e["original_local_exception_handler_entries"], 42)
        self.assertEqual(e["original_outer_io_exception_handler_entries"], 2)
        self.assertEqual(560 + 42 + 95, 697)
        self.assertEqual(e["original_instructions_within_42_protected_regions"],560)
        self.assertEqual(e["original_local_catch_entry_instructions"],42)
        self.assertEqual(e["original_instructions_outside_local_protection_and_catch_entry"],95)
        self.assertEqual(48 + 42 + 5, 95)
        self.assertEqual(e["original_putstatic_writes_inside_42_local_protected_regions"]+
                         e["original_putstatic_writes_outside_local_protected_regions"],78)
        self.assertEqual(sum(int(k)*v for k,v in
                             e["original_source_region_length_histogram"].items()),560)
        self.assertEqual(sum(e["original_source_region_length_histogram"].values()),42)
        for k in (
            "generic_R77_R78_original_private_source_site_replays_completed",
            "complete_697_instruction_recompiled_source_candidate_verified",
            "whole_original_44_handler_compiled_candidate_parity",
            "complete_client_runtime_equivalence_certified",
            "original_private_identifiers_or_literal_keys_published",
        ):
            self.assertFalse(e[k], k)

if __name__ == "__main__":
    unittest.main()
