from __future__ import annotations

from pathlib import Path
import unittest


class HistoricalV307MemberSafetyPrepTests(unittest.TestCase):
    def _text(self) -> str:
        repo = Path(__file__).resolve().parents[1]
        return (
            repo
            / "scripts"
            / "Prepare-HistoricalV307MemberSafety.ps1"
        ).read_text(encoding="utf-8")

    def test_pins_exact_historical_fixture_pair(self):
        text = self._text()
        for marker in (
            "fixtures\\v307-v308-source-regeneration.json",
            'v307_sha256 = "/old/client_sha256"',
            'v308_sha256 = "/new/client_sha256"',
            "Exact v307 SHA mismatch",
            "Exact v308 SHA mismatch",
            "Supplied v308 index is not bound to exact v308",
        ):
            self.assertIn(marker, text)

    def test_generates_v307_index_and_checks_both_build_coverages(self):
        text = self._text()
        self.assertIn('"INDEX EXACT v307"', text)
        self.assertIn('"--expect-sha256"', text)
        self.assertIn('"CHECK v307 CANONICAL COVERAGE"', text)
        self.assertIn('"CHECK v308 CANONICAL COVERAGE"', text)
        self.assertGreaterEqual(
            text.count('"spk_recovery.coverage_cli"'),
            2,
        )

    def test_uses_exact_source_safe_namespace_plans(self):
        text = self._text()
        self.assertGreaterEqual(
            text.count('"spk_recovery.semantic_namespace_cli"'),
            2,
        )
        self.assertGreaterEqual(
            text.count('"--source-safe-fallback"'),
            2,
        )
        self.assertGreaterEqual(
            text.count('"Recovered_"'),
            2,
        )
        self.assertIn(
            'Join-Path $V307NamespaceDir "member-remap-plan.json"',
            text,
        )
        self.assertIn(
            'Join-Path $V308NamespaceDir "member-remap-plan.json"',
            text,
        )

    def test_reproduces_v308_review_before_carry_forward(self):
        text = self._text()
        validate_pos = text.index(
            'Invoke-PyChecked "REPRODUCE REVIEWED v308 SAFETY ACCEPTANCE"'
        )
        carry_pos = text.index(
            'Invoke-PyChecked "CARRY REVIEWED SAFETY TO EXACT v307"'
        )
        self.assertLess(validate_pos, carry_pos)
        self.assertIn(
            '"spk_recovery.member_safety_carryforward_cli"',
            text,
        )

    def test_validates_generated_v307_acceptance_after_transfer(self):
        text = self._text()
        carry_pos = text.index(
            'Invoke-PyChecked "CARRY REVIEWED SAFETY TO EXACT v307"'
        )
        validate_pos = text.index(
            'Invoke-PyChecked "VALIDATE GENERATED v307 SAFETY ACCEPTANCE"'
        )
        self.assertLess(carry_pos, validate_pos)
        self.assertIn(
            "V307_MEMBER_SAFETY_ACCEPTANCE=",
            text,
        )
        self.assertIn(
            "Invoke-HistoricalV307RecoveryRelease.ps1",
            text,
        )


if __name__ == "__main__":
    unittest.main()
