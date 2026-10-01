from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import unittest


class HistoricalV305LineageProbeWrapperTests(unittest.TestCase):
    def script_text(self) -> str:
        root = Path(__file__).resolve().parents[1]
        return (
            root
            / "scripts"
            / "Invoke-HistoricalV305LineageProbe.ps1"
        ).read_text(encoding="utf-8")

    def test_pins_exact_v305_v308_authority_and_match_fixture(self):
        text = self.script_text()
        self.assertIn(
            "a9a5d1f35a6657b5c26939ca30e008748e718f6b206cc8fd93b64b57c4833385",
            text,
        )
        self.assertIn(
            "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6",
            text,
        )
        self.assertIn(
            "v305-v308-historical-reverse-match-summary.json",
            text,
        )
        self.assertIn(
            "v305-v308-cross-version-expectations.json",
            text,
        )
        self.assertIn(
            '$CrossVersionExpectations = Join-Path $Repo',
            text,
        )
        self.assertIn(
            "spk_recovery.cross_version_binary_delta_cli",
            text,
        )
        self.assertIn("BINARY_REPORT_ID=", text)
        self.assertIn("Binary authority report ID drifted", text)
        self.assertIn("Binary authority summary drifted", text)
        self.assertIn(
            "spk_recovery.generic_historical_lineage_cli",
            text,
        )
        self.assertIn('"v308"', text)
        self.assertIn('"v305"', text)
        self.assertIn('"305"', text)

    def test_requires_exact_main_and_preserves_previous_output(self):
        text = self.script_text()
        self.assertIn("git -C $Repo fetch origin main", text)
        self.assertIn(
            "Local HEAD is not exact origin/main",
            text,
        )
        self.assertIn("PREVIOUS_OUTPUT_BACKED_UP=", text)
        self.assertIn('".bak-"', text)

    def test_preserves_blocked_exit_three_semantics(self):
        text = self.script_text()
        self.assertIn("$ProbeExit -ne 0 -and $ProbeExit -ne 3", text)
        self.assertIn("HISTORICAL_V305_LINEAGE_BLOCKED", text)
        self.assertIn("Exit 3 requires ready_for_authority=false.", text)
        self.assertIn("exit $ProbeExit", text)
        self.assertNotIn("source_milestone_cli", text)
        self.assertNotIn("release_workspace_orchestrator_cli", text)

    @unittest.skipUnless(
        os.name == "nt" and shutil.which("powershell.exe"),
        "Windows PowerShell required",
    )
    def test_wrapper_parses_in_windows_powershell(self):
        root = Path(__file__).resolve().parents[1]
        script = (
            root
            / "scripts"
            / "Invoke-HistoricalV305LineageProbe.ps1"
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
