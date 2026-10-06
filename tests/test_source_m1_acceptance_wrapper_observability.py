from __future__ import annotations

from pathlib import Path
import unittest


class SourceM1AcceptanceWrapperObservabilityTests(unittest.TestCase):
    def test_prints_derived_intpredicate_capture_counts(self):
        repo = Path(__file__).resolve().parents[1]
        script = (
            repo
            / "scripts"
            / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        )
        text = script.read_text(encoding="utf-8")

        self.assertIn(
            'intpredicate_derived_local_capture_alias_action_count = '
            '"/normalization_summary/'
            'intpredicate_derived_local_capture_alias_action_count"',
            text,
        )
        self.assertIn(
            'intpredicate_derived_local_capture_alias_reference_count = '
            '"/normalization_summary/'
            'intpredicate_derived_local_capture_alias_reference_count"',
            text,
        )
        self.assertIn(
            "INTPREDICATE_DERIVED_LOCAL_CAPTURE_ALIAS_ACTIONS=",
            text,
        )
        self.assertIn(
            "INTPREDICATE_DERIVED_LOCAL_CAPTURE_ALIAS_REFERENCES=",
            text,
        )

    def test_prints_normalization_identity_and_same_package_shadow_counts(self):
        repo = Path(__file__).resolve().parents[1]
        script = (
            repo
            / "scripts"
            / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        )
        text = script.read_text(encoding="utf-8")

        self.assertIn(
            'normalization_id = "/normalization_id"',
            text,
        )
        self.assertIn(
            'normalization_action_count = '
            '"/normalization_summary/action_count"',
            text,
        )
        self.assertIn(
            'same_package_shadow_method_count = '
            '"/normalization_summary/'
            'shadowed_same_package_static_field_method_count"',
            text,
        )
        self.assertIn(
            'same_package_shadow_reference_count = '
            '"/normalization_summary/'
            'shadowed_same_package_static_field_reference_count"',
            text,
        )

        self.assertIn(
            "spk_recovery.javac_build_binding_cli",
            text,
        )
        self.assertIn('"--tooling-commit"', text)
        self.assertIn("javac_build_binding=", text)

        for marker in (
            "SOURCE_NORMALIZATION_ID=",
            "SOURCE_NORMALIZATION_ACTIONS=",
            "SAME_PACKAGE_SHADOW_METHODS=",
            "SAME_PACKAGE_SHADOW_REFERENCES=",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
