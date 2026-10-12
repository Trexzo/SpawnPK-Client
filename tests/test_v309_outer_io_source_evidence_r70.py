"""R70 original IOException source envelope evidence; real method still incomplete."""
import json
from pathlib import Path
import unittest

DATA = Path(__file__).resolve().parents[1] / "research/v309-source-recovery/outer-io-exception-envelope-r70.json"

class V309OuterIoSourceEvidenceTests(unittest.TestCase):
    def test_exact_two_io_regions_and_unverified_middle(self):
        e = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertEqual(e["schema_version"], 1)
        self.assertEqual(e["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(e["original_large_method_instructions"], 697)
        self.assertEqual(e["original_io_exception_table_entries"], 2)
        self.assertEqual(e["original_io_first_protected_range"], [3, 21])
        self.assertEqual(e["original_io_second_protected_range"], [22, 1605])
        self.assertEqual(e["original_io_shared_handler_bytecode_offset"], 1608)
        self.assertEqual(e["original_io_handler_code_opcode_sequence"],
                         ["astore_0", "aload_0", "invokevirtual", "return"])
        self.assertEqual(e["original_io_exception_virtual_method"],
                         "java/io/IOException.printStackTrace:()V")
        self.assertTrue(e["original_io_final_normal_goto_skips_exception_handler"])
        self.assertTrue(e["synthetic_java9_source_outer_try_split_reproduces_two_exception_ranges"])
        for key in ("real_v309_generic_R70_private_CLI_replay_verified",
                    "complete_697_instruction_original_java_source_compiled",
                    "original_42_internal_Exception_protected_blocks_all_recovered",
                    "all_helper_implementations_and_side_effects_equivalent",
                    "runtime_equivalence_certified",
                    "private_client_source_or_binary_or_literal_published"):
            self.assertFalse(e[key])

if __name__ == "__main__":
    unittest.main()
