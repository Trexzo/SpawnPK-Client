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
class ExactLocalPowerShellTests(unittest.TestCase):
    def test_source_m1_output_root_is_case_sensitive_before_children(self):
        repo = Path(__file__).resolve().parents[1]
        script = (
            repo / "scripts" / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        ).read_text(encoding="utf-8")
        prepare = script.index(
            "Enable-CaseSensitiveWorkspace -Path $OutDir"
        )
        children = script.index(
            '$BootstrapReadableDir = Join-Path $OutDir "bootstrap-readable"'
        )
        self.assertLess(prepare, children)
        self.assertNotIn(
            "Enable-CaseSensitiveWorkspace -Path $CollisionWorkspace",
            script,
        )

    def test_source_m1_exact_local_runner_parses(self):
        repo = Path(__file__).resolve().parents[1]
        script = repo / "scripts" / "Invoke-SourceM1ExactLocalAcceptance.ps1"
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


    def test_external_oracle_frontier_is_opt_in_and_precedes_blocked_exit(self):
        repo = Path(__file__).resolve().parents[1]
        script = (
            repo / "scripts" / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "[string]$ExternalOracleReport",
            script,
        )
        self.assertIn(
            '$BootstrapClassRemapPlan = Join-Path $BootstrapReadableDir "class-remap-plan.json"',
            script,
        )
        condition = script.index(
            'if (-not [string]::IsNullOrWhiteSpace($ExternalOracleReport))'
        )
        diagnostic = script.index(
            '$PrivateDiagnostic = Join-Path $ReleaseDir "javac-diagnostic-private.json"'
        )
        invoke = script.index(
            'Invoke-PyChecked "INTERSECT EXTERNAL ORACLE WITH JAVAC FRONTIER"'
        )
        blocked_exit = script.index(
            "    exit 3\n}",
            invoke,
        )
        self.assertLess(diagnostic, condition)
        self.assertLess(condition, invoke)
        self.assertLess(invoke, blocked_exit)
        self.assertIn(
            '"spk_recovery.external_oracle_frontier_cli"',
            script,
        )
        self.assertIn(
            '"--collision-plan"',
            script,
        )
        self.assertIn(
            '$BootstrapClassRemapPlan',
            script,
        )


if __name__ == "__main__":
    unittest.main()
