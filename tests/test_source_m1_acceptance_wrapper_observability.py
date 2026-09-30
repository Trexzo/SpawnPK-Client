from __future__ import annotations

from pathlib import Path
import unittest


class SourceM1AcceptanceWrapperObservabilityTests(unittest.TestCase):
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

        for marker in (
            "SOURCE_NORMALIZATION_ID=",
            "SOURCE_NORMALIZATION_ACTIONS=",
            "SAME_PACKAGE_SHADOW_METHODS=",
            "SAME_PACKAGE_SHADOW_REFERENCES=",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
