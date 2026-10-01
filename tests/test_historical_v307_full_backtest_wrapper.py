from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import unittest


class HistoricalV307FullBacktestWrapperTests(unittest.TestCase):
    def _script(self) -> Path:
        repo = Path(__file__).resolve().parents[1]
        return repo / "scripts" / "Invoke-HistoricalV307FullBacktest.ps1"

    def _text(self) -> str:
        return self._script().read_text(encoding="utf-8")

    def test_composes_safety_before_recovery_release(self):
        text = self._text()
        prep = text.index("Prepare-HistoricalV307MemberSafety.ps1")
        release = text.index("Invoke-HistoricalV307RecoveryRelease.ps1")
        self.assertLess(prep, release)

        stage1 = text.index(
            "STAGE 1: PREPARE EXACT v307 MEMBER-SAFETY AUTHORITY"
        )
        stage2 = text.index(
            "STAGE 2: RUN MODERN HISTORICAL v307 RECOVERY RELEASE"
        )
        self.assertLess(stage1, stage2)

    def test_defaults_to_known_exact_private_authority_paths(self):
        text = self._text()
        self.assertIn(
            "SpawnPK-Local-Backups\\client(6)-before-854F-6232BAE20684.jar",
            text,
        )
        self.assertIn(
            "gpt_output2\\_archive_2026-09-27\\SpawnPK\\SpawnPK-R8N-Private",
            text,
        )
        self.assertIn(
            "authority\\member-safety.accepted.json",
            text,
        )
        self.assertIn(
            "tools\\procyon-decompiler-0.6.0.jar",
            text,
        )

    def test_preserves_shared_frontier_blocked_exit(self):
        text = self._text()
        self.assertIn('if ($ReleaseExit -eq 3)', text)
        self.assertIn(
            "HISTORICAL_V307_BACKTEST_BLOCKED_AT_SHARED_SOURCE_FRONTIER",
            text,
        )
        self.assertIn("SAFETY_AUTHORITY_PASS=true", text)
        self.assertIn("RECOVERY_RELEASE_PASS=false", text)
        self.assertIn("exit 3", text)

    def test_final_pass_requires_release_ready_v307(self):
        text = self._text()
        self.assertIn('"build_id=/build_id"', text)
        self.assertIn('"ready=/ready_for_release"', text)
        self.assertIn(
            'if ([string]$Final.build_id -ne "v307")',
            text,
        )
        self.assertIn('if ($Final.ready -ne $true)', text)
        self.assertIn(
            "HISTORICAL v307 FULL RECOVERY BACKTEST - PASS",
            text,
        )

    def test_does_not_invoke_publication_milestone(self):
        text = self._text()
        self.assertNotIn("source_milestone_cli", text)
        self.assertNotIn("SOURCE-MILESTONE.json", text)
        self.assertNotIn("publication bundle", text.lower())

    @unittest.skipUnless(
        os.name == "nt" and shutil.which("powershell.exe"),
        "Windows PowerShell required",
    )
    def test_full_backtest_wrapper_parses_in_windows_powershell(self):
        script = self._script()
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
