"""R41 aggregate field declarations: pinned, internally consistent, no source."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
R41 = ROOT / "research" / "v309-source-recovery" / "field-declaration-gap-r41.json"
R37 = ROOT / "research" / "v309-source-recovery" / "frontier.json"


class ExactPrivateFieldDeclarationAggregateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(R41.read_text(encoding="utf-8"))
        cls.frontier = json.loads(R37.read_text(encoding="utf-8"))

    def test_pinned_record_agrees_with_existing_source_frontier(self):
        d, f = self.data, self.frontier
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["stable_class_id"], f["owner_stable_id"])
        self.assertEqual(
            d["original_client_jar_sha256"], f["original_client_jar_sha256"],
        )
        self.assertEqual(
            d["private_candidate_class_sha256"],
            f["private_candidate"]["compiled_class_sha256"],
        )
        for a, b in (
            ("original_declared_fields", "original_field_declarations"),
            ("candidate_declared_fields", "candidate_field_declarations"),
            ("missing_original_fields", "missing_original_field_declarations"),
            ("shared_fields", "shared_field_declarations"),
            ("shared_field_metadata_exact", "exact_field_declaration_metadata"),
            ("shared_field_metadata_different",
             "changed_field_declaration_metadata"),
        ):
            self.assertEqual(d[a], f["private_candidate"][b], a)

    def test_exact_modifier_gap_accounting(self):
        d = self.data
        self.assertEqual(d["original_static_fields"], 126)
        self.assertEqual(d["original_final_fields"], 41)
        self.assertEqual(d["candidate_static_fields"], 4)
        self.assertEqual(d["candidate_final_fields"], 0)
        self.assertEqual(d["missing_original_fields"], 122)
        self.assertEqual(d["missing_static_fields"], 122)
        self.assertEqual(d["missing_final_fields"], 40)
        self.assertEqual(d["missing_mutable_fields"], 82)
        self.assertEqual(
            d["missing_final_fields"] + d["missing_mutable_fields"],
            d["missing_original_fields"],
        )
        self.assertEqual(
            d["shared_field_metadata_exact"]
            + d["shared_field_metadata_different"],
            d["shared_fields"],
        )

    def test_only_some_missing_finals_have_literal_constant_evidence(self):
        d = self.data
        self.assertEqual(d["original_fields_with_constantvalue"], 33)
        self.assertEqual(d["original_final_fields_without_constantvalue"], 8)
        self.assertEqual(d["missing_final_fields_with_constantvalue"], 33)
        self.assertEqual(d["missing_final_fields_without_constantvalue"], 7)
        self.assertEqual(d["shared_final_modifier_mismatch_without_constantvalue"], 1)
        self.assertEqual(
            d["missing_final_fields_with_constantvalue"]
            + d["missing_final_fields_without_constantvalue"],
            d["missing_final_fields"],
        )
        self.assertEqual(
            d["original_fields_with_constantvalue"]
            + d["original_final_fields_without_constantvalue"],
            d["original_final_fields"],
        )

    def test_field_type_buckets_have_complete_inventories(self):
        d = self.data
        original, missing = d["original_field_type_counts"], d["missing_field_type_counts"]
        self.assertEqual(sum(original.values()), 126)
        self.assertEqual(sum(missing.values()), 122)
        self.assertEqual(original["boolean"] - missing["boolean"], 3)
        self.assertEqual(original["int_array"] - missing["int_array"], 1)
        for key in ("int", "java_lang_string", "java_lang_integer",
                    "project_defined_reference"):
            self.assertEqual(original[key], missing[key])

    def test_no_claims_of_recovered_initializers_or_canonical_mappings(self):
        claims = self.data["interpretation"]
        self.assertTrue(claims["reconstructable_declaration_shapes_from_JVM_metadata"])
        self.assertFalse(claims["missing_field_initializer_values_recovered"])
        self.assertFalse(claims["class_initializer_recovered"])
        self.assertFalse(claims["complete_compilable_source_recovered"])
        self.assertFalse(claims["current_strict_source_equivalence_certified"])
        self.assertFalse(claims["canonical_class_identity_accepted"])
        self.assertFalse(claims["private_original_field_names_published"])

    def test_original_private_coordinates_absent(self):
        content = R41.read_text(encoding="utf-8")
        for private in ("rs/f/a", "rs.f.a", '"field_name"',
                        '"source_code"', '"original_class_entry"',
                        "public static final boolean a;", "Base64"):
            self.assertNotIn(private, content)


if __name__ == "__main__":
    unittest.main()
