"""R42 aggregate original v309 ConstantValue facts; never publish literals."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
R41 = ROOT / "research" / "v309-source-recovery" / "field-declaration-gap-r41.json"
R42 = ROOT / "research" / "v309-source-recovery" / "exact-constantvalue-r42.json"


class V309ExactLiteralEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r41 = json.loads(R41.read_text(encoding="utf-8"))
        cls.data = json.loads(R42.read_text(encoding="utf-8"))

    def test_sha_pins_and_total_final_declaration_accounting(self):
        d, original = self.data, self.r41
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["stable_owner_id"], original["stable_class_id"])
        self.assertEqual(d["original_client_sha256"],
                         original["original_client_jar_sha256"])
        self.assertEqual(d["candidate_class_sha256"],
                         original["private_candidate_class_sha256"])
        self.assertEqual(d["missing_static_final_fields"],
                         original["missing_final_fields"])
        self.assertEqual(d["missing_static_final_fields_with_constantvalue"],
                         original["missing_final_fields_with_constantvalue"])
        self.assertEqual(d["missing_static_final_fields_without_constantvalue"],
                         original["missing_final_fields_without_constantvalue"])
        self.assertEqual(d["shared_final_modifier_mismatch_without_constantvalue"], 1)

    def test_jvm_constant_kind_and_java_field_type_counts(self):
        d = self.data
        self.assertEqual(d["exact_constantvalue_declaration_type_counts"],
                         {"boolean": 28, "int": 4, "string": 1})
        self.assertEqual(sum(d["exact_constantvalue_declaration_type_counts"].values()), 33)
        self.assertEqual(d["original_constantvalue_attribute_kind_counts"],
                         {"jvm_integer": 32, "jvm_string": 1})
        self.assertEqual(sum(d["original_constantvalue_attribute_kind_counts"].values()), 33)
        self.assertEqual(d["missing_static_final_fields_without_constantvalue"], 7)

    def test_isolated_private_literal_proof_never_claims_complete_source(self):
        d = self.data
        self.assertTrue(d["literal_source_staging_requires_exact_pinned_JAR_replay"])
        self.assertTrue(d["literal_source_replay_executed_for_original_client"])
        self.assertFalse(d["github_r42_helper_replayed_against_exact_original"])
        proof = d["private_exact_original_literal_replay"]
        self.assertEqual(proof["emitted_constant_field_declaration_count"], 33)
        self.assertEqual(proof["exact_original_to_recompiled_constantvalue_matches"], 33)
        self.assertEqual(
            (proof["boolean_field_matches"],
             proof["integer_field_matches"],
             proof["string_field_matches"]), (28, 4, 1),
        )
        self.assertEqual(proof["java_release"], 9)
        self.assertTrue(proof["isolated_literal_only_class_not_original_replacement"])
        self.assertTrue(proof["private_original_source_and_literals_not_uploaded"])
        for key in ("private_literal_source_sha256", "private_compiled_class_sha256"):
            self.assertRegex(proof[key], r"\A[0-9a-f]{64}\Z")
        for key in (
            "original_literals_published",
            "initializer_semantics_of_nonconstant_fields_recovered",
            "class_initializer_recovered",
            "full_java_class_recompiled_from_all_fields",
            "canonical_identity_accepted",
            "source_equivalence_certified",
        ):
            self.assertIs(d[key], False, key)

    def test_private_augmented_r24_java_reduces_real_missing_fields(self):
        proof = self.data["private_r24_source_augmentation"]
        self.assertEqual(proof["original_field_declarations"], 126)
        self.assertEqual(proof["candidate_fields_before"], 4)
        self.assertEqual(proof["candidate_fields_after"], 37)
        self.assertEqual(proof["original_fields_remaining_missing"], 89)
        self.assertEqual(proof["fields_with_exact_original_metadata_after"], 36)
        self.assertEqual(proof["fields_with_known_metadata_mismatch_after"], 1)
        self.assertEqual(proof["exact_original_constantvalue_attributes_in_augmented_class"], 33)
        self.assertEqual(proof["candidate_method_declarations_before"], 8)
        self.assertEqual(proof["candidate_method_declarations_after"], 8)
        self.assertEqual(proof["disassembly_opcode_sequences_unchanged"], 8)
        self.assertEqual(proof["disassembly_resolved_operands_unchanged"], 8)
        self.assertEqual(
            proof["candidate_fields_after"] - proof["candidate_fields_before"],
            proof["exact_original_constantvalue_attributes_in_augmented_class"],
        )
        self.assertEqual(
            proof["original_field_declarations"] - proof["candidate_fields_after"],
            proof["original_fields_remaining_missing"],
        )
        for key in ("classfile_sha256", "complete_private_candidate_jar_sha256",
                    "private_augmented_java_source_sha256"):
            self.assertRegex(proof[key], r"\A[0-9a-f]{64}\Z")
        for key in (
            "strict_r31_runtime_or_source_equivalence_recertified",
            "missing_nonconstant_initializers_still_reconstructed",
            "three_substantive_missing_methods_recovered",
            "augmented_proprietary_java_published",
            "original_client_binary_modified",
        ):
            self.assertIs(proof[key], False, key)

    def test_no_raw_original_constant_values_or_source_names(self):
        content = R42.read_text(encoding="utf-8")
        for sensitive in ("rs/f/a", "rs.f.a", '"field_name"',
                          '"constant_values"', "public static final",
                          "www.spawnpk.org", '"raw_field_descriptor"'):
            self.assertNotIn(sensitive, content)


if __name__ == "__main__":
    unittest.main()
