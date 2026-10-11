"""R49: fourth flat-dollar enum prototype is not real nested-class equivalence."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "research" / "v309-source-recovery"
R47 = ROOT / "nested-enum-closure-r47.json"
R49 = ROOT / "flat-enum-collision-r49.json"
THREE = ROOT / "nested-enum-source-parity-r49.json"


class FlatDollarNamedEnumCollisionEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = json.loads(R49.read_text(encoding="utf-8"))
        cls.previous = json.loads(R47.read_text(encoding="utf-8"))
        cls.three = json.loads(THREE.read_text(encoding="utf-8"))

    def test_original_binary_sha_reconciled_to_four_enum_frontier(self):
        d, p = self.proof, self.previous
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["original_client_jar_sha256"],
                         p["pinned_original_v309_jar_sha256"])
        self.assertEqual(d["owner_stable_id"], p["owner_stable_id"])
        self.assertIn(d["original_nested_enum_class_sha256"],
                      p["original_nested_enum_class_sha256"])
        for key in (
            "original_nested_enum_class_sha256",
            "private_flat_enum_source_sha256",
            "private_flat_compiled_class_sha256",
        ):
            self.assertRegex(d[key], r"\A[0-9a-f]{64}\Z")
        self.assertNotIn(d["original_nested_enum_class_sha256"],
                         [r["original_class_sha256"] for r in self.three["enum_candidates"]])

    def test_fourth_private_prototype_has_nine_instruction_sequences(self):
        d = self.proof
        self.assertEqual(d["java_compiler_release"], 9)
        self.assertEqual(d["original_enum_runtime_constants_reconstructed"], 2)
        self.assertEqual(d["original_enum_jvm_method_bodies"], 9)
        self.assertEqual(d["normalized_javap_opcode_and_resolved_operand_method_matches"], 9)
        self.assertEqual(d["original_generated_enum_constant_field_name_aliases_required"], 2)
        self.assertTrue(d["original_values_array_name_alias_required"])
        self.assertTrue(d["original_values_helper_method_name_alias_required"])

    def test_genuine_nested_source_identity_remains_unresolved(self):
        d = self.proof
        self.assertEqual(d["original_synthetic_accessors_with_different_source_access_flags"], 2)
        self.assertEqual(d["original_innerclasses_metadata_entries_for_this_nested_enum"], 1)
        self.assertEqual(d["flat_candidate_innerclasses_metadata_entries_for_this_enum"], 0)
        self.assertTrue(d["candidate_jvm_internal_class_name_matches_original"])
        for key in (
            "source_level_genuine_nested_declaration_constructed",
            "original_binary_field_identifiers_restored",
            "original_synthetic_accessor_flags_matched",
            "original_innerclasses_attribute_parity_verified",
            "enum_runtime_equivalence_certified",
            "canonical_enum_or_field_identity_accepted",
            "original_java_source_published",
            "github_r49_strict_parser_accepted_this_collision_workaround",
        ):
            self.assertIs(d[key], False, key)

    def test_no_original_obfuscated_identifiers_or_literals_published(self):
        source = R49.read_text(encoding="utf-8")
        for content in (
            "rs/f/a", "rs.f.a", '"enum_constant_name"',
            '"raw_constructor_arguments"', '"original_client_source"',
            "http://spawnpk.net", "public enum a$a",
        ):
            self.assertNotIn(content, source)


if __name__ == "__main__":
    unittest.main()
