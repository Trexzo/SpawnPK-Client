"""R69 original-v309 JVM evidence and explicit unproven parity gates."""
import json
from pathlib import Path
import unittest

DATA = Path(__file__).resolve().parents[1] / "research/v309-source-recovery/properties-file-prefix-r69.json"

class OriginalV309PropertiesEvidenceTests(unittest.TestCase):
    def test_exact_prefix_and_remaining_gates(self):
        row = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertEqual(row["schema_version"], 1)
        self.assertEqual(row["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(row["original_large_method_total_JVM_instructions"], 697)
        self.assertEqual(row["original_opening_prefix_exact_JVM_instructions"], 24)
        self.assertEqual(len(row["original_prefix_opcode_shape"]), 24)
        self.assertEqual(row["original_properties_local_type"], "java/util/Properties")
        self.assertEqual(row["original_properties_local_store_count"], 1)
        self.assertEqual(row["original_properties_getProperty_one_String_arg_call_count"], 82)
        self.assertEqual(row["original_properties_getProperty_two_String_args_call_count"], 1)
        self.assertEqual(row["original_io_exception_table_regions"], 2)
        self.assertTrue(row["original_io_handler_both_regions_share_same_handler_target"])
        for field in ("original_io_handler_source_java_catch_construct_recovered",
                      "github_R69_original_jar_CLI_replayed_and_hash_checked",
                      "full_original_complex_method_compiled",
                      "original_helper_method_side_effects_certified",
                      "original_whole_client_source_or_runtime_equivalent",
                      "private_original_field_names_file_path_strings_or_jar_publicly_published"):
            self.assertFalse(row[field])

if __name__ == "__main__":
    unittest.main()
