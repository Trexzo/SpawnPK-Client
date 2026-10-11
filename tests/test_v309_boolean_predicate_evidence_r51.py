"""R51 original-v309 aggregate source-form evidence stays non-authoritative."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


_EVIDENCE = (Path(__file__).resolve().parents[1] /
             "research/v309-source-recovery/boolean-predicate-source-r51.json")


class BooleanPredicateEvidenceTests(unittest.TestCase):
    def test_two_recovered_jvm_expression_forms_but_not_source_equivalence(self):
        data = json.loads(_EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["owner_stable_id"], "CLIENT_CLASS_000167")
        self.assertEqual(len(data["original_client_jar_sha256"]), 64)
        self.assertEqual(data["original_branch_join_shapes"], 2)
        self.assertEqual([x["kind"] for x in data["original_predicate_form_shapes"]],
                         ["reference_identity_equality", "boolean_negation"])
        self.assertEqual(data["original_predicate_form_shapes"][0]
                         ["referenced_static_field_count"], 2)
        self.assertTrue(data["original_predicate_form_shapes"][0]
                        ["field_reference_descriptors_identical"])
        self.assertEqual(data["original_predicate_form_shapes"][1]
                         ["source_field_descriptor"], "Z")
        self.assertTrue(data["observed_on_exact_original_using_read_only_javap"])
        self.assertTrue(data["synthetic_java9_javac_expression_opcode_shape_reproduced"])
        self.assertEqual(len(data["private_jvm_derived_source_fragment_sha256"]), 64)
        self.assertFalse(data["source_fragment_published"])
        for veto in (
            "original_private_source_recompiled_against_full_dependencies",
            "github_r51_cli_replayed_against_private_original_candidate_pair",
            "original_candidate_method_bytecode_parity_verified_by_r51",
            "original_complete_clinit_order_reconstructed",
            "original_java_source_equivalence_certified",
            "original_runtime_equivalence_certified",
            "canonical_owner_and_field_identity_accepted",
        ):
            self.assertFalse(data[veto])

    def test_private_jvm_names_do_not_escape_into_public_evidence(self):
        data = json.loads(_EVIDENCE.read_text(encoding="utf-8"))
        self.assertNotIn("private_source_rows", data)
        self.assertNotIn("private_java_fragment", data)
        self.assertEqual(
            set(data["original_predicate_form_shapes"][0]),
            {"kind", "referenced_static_field_count",
             "field_reference_descriptors_identical", "source_expression_semantics"},
        )


if __name__ == "__main__":
    unittest.main()
