from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import unittest


class SourceM1LoggedExactLocalWrapperTests(unittest.TestCase):
    def setUp(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        self.wrapper = (
            repo
            / "scripts"
            / "Invoke-SourceM1ExactLocalAcceptanceLogged.ps1"
        )

    def test_preserves_child_exit_and_tolerates_native_stderr_records(self):
        text = self.wrapper.read_text(encoding="utf-8")

        self.assertIn(
            'Join-Path $Repo "scripts\\Invoke-SourceM1ExactLocalAcceptance.ps1"',
            text,
        )
        self.assertIn(
            '$PreviousErrorActionPreference = $ErrorActionPreference',
            text,
        )
        continue_pos = text.index('$ErrorActionPreference = "Continue"')
        child_pos = text.index("& powershell.exe")
        restore_pos = text.index(
            "$ErrorActionPreference = $PreviousErrorActionPreference"
        )
        self.assertLess(continue_pos, child_pos)
        self.assertLess(child_pos, restore_pos)

        self.assertIn("2>&1 | Tee-Object -FilePath $LogPath", text)
        self.assertIn("$Exit = $LASTEXITCODE", text)
        self.assertIn("if ($Exit -eq 3)", text)
        self.assertIn("SOURCE_M1_MEASURED_FRONTIER_READY", text)
        self.assertIn("exit 3", text)
        self.assertIn("elseif ($Exit -eq 0)", text)
        self.assertIn("SOURCE_M1_EXACT_LOCAL_PASS", text)
        self.assertIn("exit $Exit", text)

    def test_surfaces_new_focused_source_context(self):
        text = self.wrapper.read_text(encoding="utf-8")

        self.assertIn("'^SRCCTX:'", text)
        self.assertIn("OsrsMapDependencyScanner\\.java", text)
        self.assertIn("Recovered_CLIENT_CLASS_000109\\.java", text)
        self.assertIn("'^JAVAC_FRONTIER_ID='", text)
        self.assertIn("'^JAVAC_TOTAL_ERRORS='", text)
        self.assertIn("'^SOURCE_NORMALIZATION_ACTIONS='", text)

    @unittest.skipUnless(
        os.name == "nt" and shutil.which("powershell.exe"),
        "Windows PowerShell required",
    )
    def test_wrapper_parses_in_windows_powershell(self):
        literal = str(self.wrapper).replace("'", "''")
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
