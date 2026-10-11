"""R46 original v309 mutable scalar declaration proof remains research-only."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "research" / "v309-source-recovery"
R46 = ROOT / "mutable-scalar-declarations-r46.json"
R37 = ROOT / "frontier.json"
R41 = ROOT / "field-declaration-gap-r41.json"


class V309MutableScalarDeclarationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(R46.read_text(encoding="utf-8"))
        cls.frontier = json.loads(R37.read_text(encoding="utf-8"))
        cls.r41 = json.loads(R41.read_text(encoding="utf-8"))

    def test_original_jar_and_owner_have_unchanged_authority(self):
        d = self.data
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["original_client_jar_sha256"],
                         self.frontier["original_client_jar_sha256"])
        self.assertEqual(d["stable_owner_id"], self.frontier["owner_stable_id"])
        for k in (
            "prior_private_combined_r45_candidate_class_sha256",
            "expanded_private_java_source_sha256",
            "expanded_private_compiled_class_sha256",
            "expanded_private_compiled_jar_sha256",
        ):
            self.assertRegex(d[k], r"\A[0-9a-f]{64}\Z")

    def test_exact_declaration_accounting(self):
        d = self.data
        self.assertEqual(d["compiler_release"], 9)
        self.assertEqual(d["original_declared_fields"], 126)
        self.assertEqual(d["previous_candidate_field_declarations"], 38)
        self.assertEqual(d["newly_staged_mutable_scalar_declarations"], 77)
        self.assertEqual(d["recovered_declaration_type_counts"],
                         {"boolean": 69, "int": 6, "string": 2})
        self.assertEqual(sum(d["recovered_declaration_type_counts"].values()), 77)
        self.assertEqual(d["candidate_field_declarations_after"], 115)
        self.assertEqual(d["candidate_fields_with_exact_original_jvm_metadata_after"], 115)
        self.assertEqual(d["original_field_declarations_still_missing"], 11)
        self.assertEqual(
            d["candidate_field_declarations_after"]
            + d["original_field_declarations_still_missing"],
            d["original_declared_fields"],
        )
        self.assertEqual(
            d["previous_candidate_field_declarations"]
            + d["newly_staged_mutable_scalar_declarations"],
            d["candidate_field_declarations_after"],
        )
        self.assertEqual(d["remaining_missing_field_type_counts"],
                         {"string": 5, "project_defined_reference": 6})
        self.assertEqual(d["remaining_missing_project_defined_mutable_fields"], 5)
        self.assertEqual(d["remaining_missing_project_defined_final_fields"], 1)
        self.assertEqual(d["remaining_missing_dynamic_final_string_fields"], 5)

    def test_existing_method_bodies_unmodified_but_runtime_unverified(self):
        d = self.data
        self.assertEqual(d["candidate_method_declarations_before"], 8)
        self.assertEqual(d["candidate_method_declarations_after"], 8)
        self.assertEqual(d["candidate_method_disassemblies_unchanged"], 8)
        for k in (
            "original_mutable_scalar_clinit_initializers_reconstructed",
            "original_clinit_full_method_equivalence_certified",
            "three_substantive_original_method_bodies_recovered",
            "full_class_runtime_semantic_equivalence_certified",
            "source_equivalence_certified", "canonical_identity_accepted",
            "original_binary_modified",
            "private_augmented_java_or_classfile_published",
            "github_R46_cli_replayed_against_exact_original",
        ):
            self.assertIs(d[k], False, k)

    def test_private_source_identifiers_never_committed(self):
        s = R46.read_text(encoding="utf-8")
        for item in (
            "rs/f/a", "rs.f.a", '"field_name"', '"field_descriptor"',
            '"source_code"', "public static boolean ai;",
            '"original_clinit_code"', '"original_field_values"',
        ):
            self.assertNotIn(item, s)


if __name__ == "__main__":
    unittest.main()
