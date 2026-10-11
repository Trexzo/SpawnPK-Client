"""R54 tracked original-v309 conditional concat source evidence guards."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

_PATH = (Path(__file__).resolve().parents[1] /
         "research/v309-source-recovery/conditional-concat-string-source-r54.json")


class V309ConditionalConcatEvidenceTests(unittest.TestCase):
    def test_two_original_conditional_strings_and_one_outstanding(self):
        d = json.loads(_PATH.read_text(encoding="utf-8"))
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(d["original_nonconstant_static_final_string_count"], 5)
        self.assertEqual(d["original_conditional_enum_reference_choose_string_concat_final_fields"], 2)
        self.assertEqual(d["exact_original_conditional_branch_opcode"], "if_acmpne")
        self.assertEqual(d["original_conditional_branch_string_constant_count_per_site"], 2)
        self.assertEqual(d["original_invokedynamic_bootstrap_factory"],
                         "StringConcatFactory.makeConcatWithConstants")
        self.assertEqual(d["original_invokedynamic_recipe_dynamic_argument_markers"], 1)
        self.assertEqual(d["original_invokedynamic_recipe_constant_argument_markers"], 0)
        self.assertTrue(d["both_original_sites_use_identical_exact_invokedynamic_recipe"])
        self.assertTrue(d["no_unexpected_incoming_branch_targets_or_handlers_over_fragments"])
        self.assertEqual(d["remaining_string_final_expressions_after_combining_r53_r54"], 1)
        self.assertTrue(d["remaining_original_final_string_involves_external_static_string_method_and_invokedynamic"])
        self.assertEqual(len(d["independently_reconstructed_private_source_fragment_sha256"]), 64)
        for veto in (
            "github_r54_cli_replayed_against_private_original_client",
            "java_compilation_of_original_expression_fragment_certified",
            "bootstrap_execution_runtime_equivalence_certified",
            "nested_enum_original_class_source_equivalence_certified",
            "complete_original_static_initializer_recovered",
            "canonical_member_identity_accepted",
            "original_client_jar_private_strings_or_java_published",
        ):
            self.assertFalse(d[veto], veto)


if __name__ == "__main__":
    unittest.main()
