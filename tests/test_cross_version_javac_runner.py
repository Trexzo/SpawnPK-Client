from __future__ import annotations

from pathlib import Path
import unittest


class CrossVersionJavacRunnerTests(unittest.TestCase):
    def test_runner_is_redacted_and_bound_to_exact_main(self):
        repo = Path(__file__).resolve().parents[1]
        path = (
            repo
            / "scripts"
            / "Invoke-CrossVersionJavacFrontier.ps1"
        )
        text = path.read_text(encoding="utf-8")

        self.assertIn(
            "spk_recovery.cross_version_javac_frontier_cli",
            text,
        )
        self.assertIn(
            "SpawnPK-Historical-v307-Backtest"
            "\\recovery-release\\release"
            "\\javac-diagnostic-private.json",
            text,
        )
        self.assertIn(
            "SpawnPK-SourceM1-Exact"
            "\\release\\javac-diagnostic-private.json",
            text,
        )
        self.assertIn("git -C $Repo fetch origin main", text)
        self.assertIn(
            "Local HEAD is not exact origin/main",
            text,
        )
        self.assertNotIn('"--include-identifiers"', text)
        self.assertIn(
            "Refusing unexpected identifier-bearing cross-version report.",
            text,
        )
        self.assertIn(
            "CROSS-VERSION JAVAC FRONTIER COMPARISON - PASS",
            text,
        )

    def test_runner_surfaces_overlap_metrics(self):
        repo = Path(__file__).resolve().parents[1]
        text = (
            repo
            / "scripts"
            / "Invoke-CrossVersionJavacFrontier.ps1"
        ).read_text(encoding="utf-8")

        for marker in (
            "REPORT_ID=",
            "V307_FRONTIER=",
            "V308_FRONTIER=",
            "SHARED_ERRORS=",
            "V307_ONLY_ERRORS=",
            "V308_ONLY_ERRORS=",
            "SHARED_PERCENT_OF_V307=",
            "SHARED_PERCENT_OF_V308=",
            "SHARED_AFFECTED_FILES=",
            "EXACT_FRONTIER_EQUAL=",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
