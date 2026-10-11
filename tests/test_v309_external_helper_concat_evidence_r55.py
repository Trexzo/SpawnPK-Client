"""R55 exact original-v309 source form evidence remains research-only."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

_P = (Path(__file__).resolve().parents[1] /
      "research/v309-source-recovery/external-helper-concat-final-r55.json")


class ExternalHelperV309EvidenceTests(unittest.TestCase):
    def test_fifth_final_string_expression_form_is_measured_not_certified(self):
        r = json.loads(_P.read_text(encoding="utf-8"))
        self.assertEqual(r["schema_version"], 1)
        self.assertEqual(r["stable_owner_id"], "CLIENT_CLASS_000167")
        self.assertEqual(r["original_nonconstant_static_final_string_fields"], 5)
        self.assertEqual(r["exact_original_invokestatic_external_helper_invokedynamic_putstatic_sites"], 1)
        self.assertEqual(r["original_external_helper_descriptor"], "()Ljava/lang/String;")
        self.assertTrue(r["exact_external_class_and_declared_static_method_confirmed"])
        self.assertEqual(r["original_bootstrap_string_dynamic_markers"], 1)
        self.assertEqual(r["original_bootstrap_string_constant_markers"], 0)
        self.assertEqual(len(r["single_original_source_form_private_fragment_sha256"]), 64)
        self.assertEqual(r["combined_r53_enum_helper_static_string_forms"], 2)
        self.assertEqual(r["combined_r54_conditional_string_concat_forms"], 2)
        self.assertEqual(r["combined_r55_external_helper_concat_forms"], 1)
        self.assertEqual(r["combined_five_string_local_source_forms_accounted_for"], 5)
        for key in (
            "original_external_helper_method_body_reconstructed",
            "original_external_helper_side_effects_verified",
            "github_r55_cli_run_on_private_original",
            "all_five_string_forms_compiled_and_bytecode_parity_certified",
            "complete_original_clinit_interleaving_and_side_effects_recovered",
            "source_equivalence_certified",
            "runtime_equivalence_certified",
            "canonical_original_class_member_identities_accepted",
            "private_original_client_literals_or_java_published",
        ):
            self.assertFalse(r[key], key)


if __name__ == "__main__":
    unittest.main()
