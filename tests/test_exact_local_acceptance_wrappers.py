from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


class ExactLocalAcceptanceWrapperTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.dep = root / "scripts" / "Invoke-R8DEP38ExactLocalAcceptance.ps1"
        self.source = root / "scripts" / "Invoke-SourceM1ExactLocalAcceptance.ps1"

    def test_r8dep_wrapper_pins_exact_authority_and_full_apply_verify(self):
        text = self.dep.read_text(encoding="utf-8")
        self.assertIn(
            "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6",
            text,
        )
        self.assertIn(
            "e12e4f917ba2c48ea306e3b4d4cc19c58c5e23cd4f5c33f4ae339ea6fce53c99",
            text,
        )
        self.assertIn(
            "spk_recovery.dependency_runtime_substitution_plan_cli",
            text,
        )
        self.assertIn(
            "spk_recovery.dependency_runtime_substitution_apply_cli",
            text,
        )
        self.assertIn('"apply"', text)
        self.assertIn('"verify"', text)
        self.assertIn("--include-identifiers", text)
        self.assertIn("origin/main", text)
        self.assertTrue(all(ord(ch) < 128 for ch in text))

    def test_source_m1_wrapper_runs_current_main_release_and_publication_chain(self):
        text = self.source.read_text(encoding="utf-8")
        self.assertIn(
            "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6",
            text,
        )
        self.assertIn(
            "spk_recovery.release_workspace_orchestrator_cli",
            text,
        )
        self.assertIn(
            "spk_recovery.release_verify_cli",
            text,
        )
        self.assertIn(
            "spk_recovery.source_authority_artifact_cli",
            text,
        )
        self.assertIn(
            "spk_recovery.source_milestone_cli",
            text,
        )
        self.assertIn("SOURCE M1 EXACT LOCAL ACCEPTANCE - PASS", text)
        self.assertIn("SPK_SOURCE_M1_EXACT_LOCAL_BLOCKED", text)
        self.assertIn("--private-collision-plan", text)
        self.assertIn("--source-safe-fallback", text)
        self.assertIn("origin/main", text)
        self.assertTrue(all(ord(ch) < 128 for ch in text))

    def test_wrappers_parse_with_powershell_ast(self):
        shell = shutil.which("powershell.exe") or shutil.which("pwsh")
        if shell is None:
            self.skipTest("PowerShell parser unavailable")

        for script in (self.dep, self.source):
            escaped = str(script).replace("'", "''")
            command = (
                "$errors = $null; "
                "[System.Management.Automation.Language.Parser]::ParseFile("
                "'" + escaped + "', "
                "[ref]$null, [ref]$errors) | Out-Null; "
                "if ($errors.Count -ne 0) { "
                "$errors | ForEach-Object { Write-Error $_.Message }; "
                "exit 1 }; exit 0"
            )
            proc = subprocess.run(
                [shell, "-NoProfile", "-Command", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                proc.returncode,
                0,
                str(script) + "\n" + proc.stdout + proc.stderr,
            )


if __name__ == "__main__":
    unittest.main()
