from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(
    os.name == "nt" and shutil.which("powershell.exe"),
    "Windows PowerShell required",
)
class ExternalOraclePowerShellTests(unittest.TestCase):
    def test_external_oracle_runner_parses(self):
        repo = Path(__file__).resolve().parents[1]
        script = (
            repo
            / "scripts"
            / "Invoke-ExternalReadableV308Oracle.ps1"
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

    def test_runner_builds_non_rs_capsule_before_external_compile(self):
        repo = Path(__file__).resolve().parents[1]
        script = (
            repo
            / "scripts"
            / "Invoke-ExternalReadableV308Oracle.ps1"
        ).read_text(encoding="utf-8")

        capsule = script.index(
            'Invoke-Checked "BUILD NON-RS DEPENDENCY CAPSULE"'
        )
        copy = script.index(
            'Copy-Item -LiteralPath $Capsule -Destination $Vendored'
        )
        compile_step = script.index(
            'Invoke-Checked "COMPILE EXTERNAL READABLE TREE"'
        )
        oracle = script.index(
            'Invoke-Checked "CORRELATE EXTERNAL TREE AGAINST EXACT v308"'
        )
        self.assertLess(capsule, copy)
        self.assertLess(copy, compile_step)
        self.assertLess(compile_step, oracle)
        self.assertIn(
            'PROJECT_BINARY_FALLBACK=0',
            script,
        )


if __name__ == "__main__":
    unittest.main()
