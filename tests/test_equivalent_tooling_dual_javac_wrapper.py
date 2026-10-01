from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import unittest


class EquivalentToolingDualJavacWrapperTests(unittest.TestCase):
    def script_text(self) -> str:
        root = Path(__file__).resolve().parents[1]
        return (
            root
            / "scripts"
            / "Invoke-EquivalentToolingV307V308JavacBacktest.ps1"
        ).read_text(encoding="utf-8")

    def test_composes_both_exact_runners_and_comparator(self):
        text = self.script_text()
        self.assertIn(
            "Invoke-HistoricalV307FullBacktest.ps1",
            text,
        )
        self.assertIn(
            "Invoke-SourceM1ExactLocalAcceptance.ps1",
            text,
        )
        self.assertIn(
            "Invoke-CrossVersionJavacFrontier.ps1",
            text,
        )
        self.assertIn(
            "RUN EXACT v307 HISTORICAL BACKTEST",
            text,
        )
        self.assertIn(
            "RUN EXACT v308 SOURCE M1 ACCEPTANCE",
            text,
        )
        self.assertIn(
            "COMPARE SAME-COMMIT v307-v308 FRONTIERS",
            text,
        )

    def test_pins_single_exact_main_across_both_runs(self):
        text = self.script_text()
        self.assertIn("git -C $Repo fetch origin main", text)
        self.assertIn("Local HEAD is not exact origin/main", text)
        self.assertIn("TOOLING_COMMIT=$Head", text)
        self.assertIn(
            "Recovery tooling authority changed after v307 run",
            text,
        )
        self.assertIn(
            "Recovery tooling authority changed after v308 run",
            text,
        )
        self.assertIn(
            "v307 binding tooling commit drifted",
            text,
        )
        self.assertIn(
            "v308 binding tooling commit drifted",
            text,
        )

    def test_blocked_children_still_feed_comparator(self):
        text = self.script_text()
        self.assertIn(
            "$Exit -ne 0 -and $Exit -ne 3",
            text,
        )
        self.assertIn(
            "EQUIVALENT_TOOLING_V307_V308_BLOCKED_AT_SOURCE_FRONTIER",
            text,
        )
        self.assertIn(
            "EQUIVALENT_TOOLING_RECOVERY_RELEASES_READY=false",
            text,
        )
        self.assertIn(
            "$V307Exit -eq 0 -and $V308Exit -eq 0",
            text,
        )
        self.assertIn("exit 3", text)

    def test_generates_missing_success_path_bindings(self):
        text = self.script_text()
        self.assertIn(
            "spk_recovery.javac_build_binding_cli",
            text,
        )
        self.assertIn(
            "Ensure-JavacBuildBinding",
            text,
        )
        self.assertIn(
            "GENERATED_JAVAC_BUILD_BINDING=",
            text,
        )
        self.assertIn(
            "6232bae206846a4ba8d09766a2dee886"
            "b69016066a3f50f83b201bf705f93662",
            text,
        )
        self.assertIn(
            "854f26ff9f134b0317572e7ac1688e6f"
            "40a231d5a4c66f8db5d655b7f45ce7c6",
            text,
        )

    def test_requires_private_binding_evidence_from_each_run(self):
        text = self.script_text()
        for marker in (
            "javac-diagnostic-private.json",
            "rebuild\\clean-rebuild.json",
            "javac-build-binding.json",
            "V307_BINDING_ID=",
            "V308_BINDING_ID=",
            "V307_FRONTIER=",
            "V308_FRONTIER=",
            "SHARED_ERRORS=",
            "EXACT_FRONTIER_EQUAL=",
            "REPORT_ID=",
        ):
            self.assertIn(marker, text)

    def test_preserves_previous_outputs(self):
        text = self.script_text()
        self.assertIn("Backup-NonEmptyDirectory", text)
        self.assertIn('".bak-"', text)
        self.assertIn("PREVIOUS_OUTPUT_BACKED_UP=", text)
        self.assertIn(
            "Backup-NonEmptyDirectory -Path $V307Out",
            text,
        )
        self.assertIn(
            "Backup-NonEmptyDirectory -Path $V308Out",
            text,
        )
        self.assertIn(
            "Backup-NonEmptyDirectory -Path $CompareOut",
            text,
        )

    def test_does_not_take_semantic_or_source_repair_ownership(self):
        text = self.script_text()
        self.assertNotIn("semantic_proposal", text)
        self.assertNotIn("source_milestone_cli", text)
        self.assertNotIn("source_rewrite_plan_cli", text)

    @unittest.skipUnless(
        os.name == "nt" and shutil.which("powershell.exe"),
        "Windows PowerShell required",
    )
    def test_wrapper_parses_in_windows_powershell(self):
        root = Path(__file__).resolve().parents[1]
        script = (
            root
            / "scripts"
            / "Invoke-EquivalentToolingV307V308JavacBacktest.ps1"
        )
        literal = str(script).replace("'", "''")
        command = (
            "$tokens=$null; $errors=$null; "
            "[System.Management.Automation.Language.Parser]::ParseFile("
            f"'{literal}', [ref]$tokens, [ref]$errors) | Out-Null; "
            "if ($errors.Count -ne 0) { "
            "$errors | ForEach-Object { Write-Error $_.Message }; exit 1 "
            "}; exit 0"
        )
        proc = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            proc.stdout + proc.stderr,
        )


if __name__ == "__main__":
    unittest.main()
