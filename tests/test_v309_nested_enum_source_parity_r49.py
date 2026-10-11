"""R49: exact original-v309 nested enum source research claims remain bounded."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "research" / "v309-source-recovery"
PROOF = ROOT / "nested-enum-source-parity-r49.json"
R47 = ROOT / "nested-enum-closure-r47.json"


class NestedEnumSourceV309PrivateAggregateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads(PROOF.read_text(encoding="utf-8"))
        cls.r47 = json.loads(R47.read_text(encoding="utf-8"))

    def test_original_jar_and_parent_identity_pins(self):
        d, a = self.evidence, self.r47
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["original_client_jar_sha256"],
                         a["pinned_original_v309_jar_sha256"])
        self.assertEqual(d["owner_stable_id"], a["owner_stable_id"])
        self.assertEqual(d["original_stable_nested_enum_class_count"],
                         a["distinct_original_nested_enum_classfiles"])
        self.assertEqual(
            d["remaining_nested_enum_source_with_parent_simple_name_collision"],
            a["distinct_nested_enum_source_name_collisions_with_parent"],
        )
        self.assertRegex(
            d["private_candidate_java_source_sha256"], r"\A[a-f0-9]{64}\Z",
        )

    def test_three_java9_candidate_classfiles_and_methods_are_consistent(self):
        d, r47 = self.evidence, self.r47
        rows = d["enum_candidates"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(d["source_candidate_nested_enum_class_count"], 3)
        self.assertEqual(d["recovered_enum_runtime_constant_records"], 14)
        self.assertEqual(sum(x["constant_count"] for x in rows), 14)
        self.assertEqual(
            sum(x["original_method_count"] for x in rows), 16,
        )
        self.assertEqual(
            sum(x["normalized_method_instruction_matches"] for x in rows), 16,
        )
        self.assertEqual(d["original_enum_methods_compared"], 16)
        self.assertEqual(
            d["normalized_original_vs_compiled_method_instruction_sequences_equal"],
            16,
        )
        for row in rows:
            self.assertIn(
                row["original_class_sha256"],
                r47["original_nested_enum_class_sha256"],
            )
            self.assertEqual(row["original_method_count"],
                             row["normalized_method_instruction_matches"])
            for key in ("original_class_sha256", "candidate_class_sha256"):
                self.assertRegex(row[key], r"\A[a-f0-9]{64}\Z")

    def test_verified_method_slices_do_not_accept_binary_field_aliases(self):
        d = self.evidence
        self.assertEqual(len(d["permitted_normalizations"]), 4)
        for key in (
            "original_enum_fields_exact_binary_names_recovered",
            "original_nested_enum_innerclasses_attribute_parity_verified",
            "original_enum_classfile_binary_equality_claimed",
            "source_equivalence_certified", "runtime_equivalence_certified",
            "canonical_class_or_field_identity_accepted",
            "public_original_client_source_published",
            "github_r49_parser_replayed_against_exact_original",
        ):
            self.assertIs(d[key], False, key)

    def test_private_names_and_enum_literal_constructor_values_not_published(self):
        body = PROOF.read_text(encoding="utf-8")
        for prohibited in (
            "rs/f/a", "rs.f.a", '"raw_field_name"',
            '"raw_constructor_literals"', '"original_disassembly"',
            '"original_enum_source"', '"original_jvm_member_descriptor"',
        ):
            self.assertNotIn(prohibited, body)


if __name__ == "__main__":
    unittest.main()
