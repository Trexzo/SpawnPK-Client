"""R82: exact-original method aggregate evidence cannot certify parity."""
import json
from pathlib import Path
import unittest
E=Path(__file__).resolve().parents[1]/"research/v309-source-recovery/original-save-writer-patterns-r82.json"

class OriginalSaveWriterEvidenceTests(unittest.TestCase):
    def test_bounded_original_writer_types_and_nonclaims(self):
        e=json.loads(E.read_text(encoding="utf-8"))
        self.assertEqual(e["stable_owner_id"],"CLIENT_CLASS_000167")
        self.assertEqual(e["original_private_static_save_method_jvm_instructions"],364)
        self.assertEqual(e["original_invokedynamic_sites"],46)
        self.assertEqual(e["original_invokevirtual_sites"],102)
        self.assertEqual(e["original_BufferedWriter_write_calls"],47)
        self.assertEqual(e["original_BufferedWriter_newLine_calls"],48)
        self.assertEqual(e["original_bounded_source_forms_total"],42)
        self.assertEqual(e["original_exact_simple_field_concat_write_newline_regions"]+
                         e["original_exact_enum_name_concat_write_newline_regions"],42)
        self.assertEqual(e["original_direct_writer_boolean_field_sources"]+
                         e["original_direct_writer_integer_field_sources"]+
                         e["original_direct_writer_String_field_sources"],41)
        self.assertEqual(42+e["other_write_calls_not_reconstructed"],47)
        self.assertTrue(e["exact_original_method_opcode_counts_independently_readonly_verified"])
        for key in ("generic_R82_cli_replayed_on_private_original_jar",
                    "complete_364_op_original_save_method_java_compiled",
                    "all_original_bootstrap_and_operand_candidate_parity_passed",
                    "original_filesystem_write_copy_delete_side_effect_parity_passed",
                    "full_client_runtime_equivalence_certified",
                    "original_private_keys_member_names_or_binary_published"):
            self.assertFalse(e[key],key)

if __name__=="__main__":
    unittest.main()
