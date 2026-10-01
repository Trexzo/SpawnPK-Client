from __future__ import annotations

from pathlib import Path
import os
import subprocess
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
        self.assertIn("COMPARATOR_COMMIT=", text)
        self.assertNotIn("AUTHORITY_COMMIT=", text)

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

    def test_windows_powershell_parser_accepts_runner(self):
        if os.name != "nt":
            self.skipTest("Windows PowerShell parser check")

        repo = Path(__file__).resolve().parents[1]
        script = (
            repo
            / "scripts"
            / "Invoke-CrossVersionJavacFrontier.ps1"
        )
        escaped = str(script).replace("'", "''")
        command = (
            "$tokens=$null; $errors=$null; "
            "[System.Management.Automation.Language.Parser]::ParseFile("
            f"'{escaped}', [ref]$tokens, [ref]$errors) | Out-Null; "
            "if ($errors.Count -ne 0) { "
            "$errors | ForEach-Object { Write-Error $_.Message }; exit 1 }"
        )
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=completed.stdout + completed.stderr,
        )


if __name__ == "__main__":
    unittest.main()
