"""R85 original-JAR-independent observation recorded without parity inflation."""
import json
from pathlib import Path
import unittest
E=Path(__file__).resolve().parents[1]/"research/v309-source-recovery/original-save-364-partition-r85.json"

class OriginalSavePartitionEvidenceTests(unittest.TestCase):
    def test_original_364_op_partition_and_explicit_nonclaims(self):
        e=json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(e["stable_owner_id"],"CLIENT_CLASS_000167")
        self.assertEqual(e["original_save_jvm_instructions"],364)
        self.assertEqual(sum(e[k] for k in (
            "original_file_writer_constructor_prefix",
            "original_41_regular_six_op_writers",
            "original_one_regular_seven_op_enum_writer",
            "original_indexed_array_writer_loop",
            "original_three_list_filter_writers",
            "original_conditional_enum_writer",
            "original_post_array_standalone_newline_instructions",
            "original_file_copy_delete_close_and_exception_tail")),364)
        self.assertEqual(e["original_BufferedWriter_write_calls"],47)
        self.assertEqual(e["original_BufferedWriter_newLine_calls"],48)
        self.assertEqual(e["original_standalone_newline_at_bytecode_offsets"],[380,381])
        self.assertEqual(e["original_Exception_handler_table_entries"],1)
        self.assertTrue(e["exact_original_save_method_opcode_and_IO_boundaries_independently_inspected"])
        for key in ("generic_R82_to_R85_CLI_original_binary_replay_passed",
                    "complete_original_364_op_Java_method_compiled",
                    "all_candidate_operand_CFG_exception_parity_passed",
                    "original_runtime_equivalence_certified",
                    "original_private_members_keys_source_binary_uploaded"):
            self.assertFalse(e[key],key)

if __name__=="__main__":
    unittest.main()
