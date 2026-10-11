"""R43 original initializer aggregate must not imply recovered Java source."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "research" / "v309-source-recovery"
R43 = ROOT / "final-clinit-assignment-frontier-r43.json"
R41 = ROOT / "field-declaration-gap-r41.json"


class V309FinalClinitEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(R43.read_text(encoding="utf-8"))
        cls.r41 = json.loads(R41.read_text(encoding="utf-8"))

    def test_exact_input_fingerprints_and_existing_final_inventories(self):
        d, f = self.d, self.r41
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["original_owner_stable_id"], f["stable_class_id"])
        self.assertEqual(d["original_client_jar_sha256"], f["original_client_jar_sha256"])
        self.assertEqual(
            d["private_r24_compiled_candidate_class_sha256"],
            f["private_candidate_class_sha256"],
        )
        self.assertEqual(d["original_final_field_declarations"], f["original_final_fields"])
        self.assertEqual(d["original_final_fields_with_constantvalue"],
                         f["original_fields_with_constantvalue"])
        self.assertEqual(d["original_final_fields_without_constantvalue"],
                         f["original_final_fields_without_constantvalue"])

    def test_eight_write_sites_type_counts_and_r24_mismatch(self):
        d = self.d
        self.assertEqual(d["original_clinit_code_bytes"], 473)
        self.assertEqual(d["exact_original_final_field_clinit_putstatic_sites"], 8)
        self.assertEqual(d["original_final_field_with_no_constantvalue_write_count_each"], 1)
        self.assertEqual(d["type_counts"], {
            "string": 5, "int_array": 1,
            "boxed_integer": 1, "other_reference": 1,
        })
        self.assertEqual(sum(d["type_counts"].values()), 8)
        self.assertEqual(
            d["r24_candidate_status_counts"],
            {"missing": 7, "present_metadata_difference": 1,
             "present_same_metadata": 0},
        )
        self.assertEqual(sum(d["r24_candidate_status_counts"].values()), 8)

    def test_exact_store_site_is_not_source_equivalence(self):
        d = self.d
        self.assertEqual(d["source_expressions_reconstructed"], 0)
        for key in (
            "original_clinit_method_reconstructed",
            "source_equivalence_certified",
            "runtime_initializer_equivalence_certified",
            "canonical_identity_accepted", "original_client_binary_modified",
            "private_jvm_field_names_or_values_published",
            "github_r43_tool_replayed_against_private_original",
        ):
            self.assertIs(d[key], False, key)

    def test_no_original_field_names_or_expressions_published(self):
        body = R43.read_text(encoding="utf-8")
        for text in (
            "rs/f/a", "rs.f.a", '"field_name"', '"raw_method_descriptor"',
            '"original_assignment"', '"original_bytecode"',
            '"java_source"', '"original_constant_values"',
        ):
            self.assertNotIn(text, body)


if __name__ == "__main__":
    unittest.main()
