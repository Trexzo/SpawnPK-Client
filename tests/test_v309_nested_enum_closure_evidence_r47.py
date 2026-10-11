"""R47 exact-private enum-source frontier aggregate, no proprietary artifacts."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "research" / "v309-source-recovery"
DOC = ROOT / "nested-enum-closure-r47.json"
R37 = ROOT / "frontier.json"


class V309NestedEnumRecoveryClosureEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DOC.read_text(encoding="utf-8"))
        cls.frontier = json.loads(R37.read_text(encoding="utf-8"))

    def test_pinned_original_v309_and_stable_owner(self):
        d = self.data
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["pinned_original_v309_jar_sha256"],
                         self.frontier["original_client_jar_sha256"])
        self.assertEqual(d["owner_stable_id"], self.frontier["owner_stable_id"])
        for key in ("pinned_previous_v308_jar_sha256",
                    "private_R46_candidate_jar_sha256"):
            self.assertRegex(d[key], r"\A[0-9a-f]{64}\Z")

    def test_six_missing_references_four_identical_enum_classfiles(self):
        d = self.data
        self.assertEqual(d["original_field_declarations"], 126)
        self.assertEqual(d["private_candidate_field_declarations"], 115)
        self.assertEqual(d["original_fields_absent_from_candidate"], 11)
        self.assertEqual(
            d["private_candidate_field_declarations"]
            + d["original_fields_absent_from_candidate"],
            d["original_field_declarations"],
        )
        self.assertEqual(d["absent_fields_with_nested_enum_types"], 6)
        self.assertEqual(d["distinct_original_nested_enum_classfiles"], 4)
        self.assertEqual(d["nested_enum_classfiles_byte_identical_v308_v309"], 4)
        self.assertEqual(d["distinct_nested_enum_source_name_collisions_with_parent"], 1)
        self.assertEqual(d["nested_enum_field_reference_multiplicity"], [1, 1, 1, 3])
        self.assertEqual(sum(d["nested_enum_field_reference_multiplicity"]), 6)
        fingerprints = d["original_nested_enum_class_sha256"]
        self.assertEqual(len(fingerprints), 4)
        self.assertEqual(len(set(fingerprints)), 4)
        for digest in fingerprints:
            self.assertRegex(digest, r"\A[0-9a-f]{64}\Z")

    def test_provenance_does_not_imply_java_source_recovered(self):
        d = self.data
        for key in (
            "original_nested_enum_java_source_recovered",
            "original_nested_enum_classfile_bytes_published",
            "original_class_direct_field_reference_descriptors_published",
            "original_nested_enum_binary_to_source_mapping_accepted",
            "github_R47_cli_executed_against_private_original",
            "original_client_binary_modified",
            "client_runtime_equivalence_certified",
            "source_equivalence_certified",
        ):
            self.assertIs(d[key], False, key)
        self.assertTrue(d["no_real_nested_enum_source_compilation_claimed"])

    def test_public_record_omits_private_nested_type_names(self):
        body = DOC.read_text(encoding="utf-8")
        for private in (
            "rs/f/a", "rs.f.a", "rs/f/a$", '"field_name"',
            '"descriptor"', '"source_code"', '"classfile_bytes"',
            "public enum a", "private static final ",
        ):
            self.assertNotIn(private, body)


if __name__ == "__main__":
    unittest.main()
