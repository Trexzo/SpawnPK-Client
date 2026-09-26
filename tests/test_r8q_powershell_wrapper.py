from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


class R8QPowerShellWrapperTests(unittest.TestCase):
    def test_wrapper_pins_exact_authorities(self):
        root = Path(__file__).resolve().parents[1]
        script = root / "scripts" / "Invoke-R8QExactSourceEntryGate.ps1"
        text = script.read_text(encoding="utf-8")

        self.assertIn(
            'JCLASSPLAN_1D1CFBBE48CDC80F8E8C',
            text,
        )
        self.assertIn(
            'e12e4f917ba2c48ea306e3b4d4cc19c58c5e23cd4f5c33f4ae339ea6fce53c99',
            text,
        )
        self.assertIn(
            'aaf38eb4fef38f30625746833c88e7461de7b2deeb79994a3169967f71ea1227',
            text,
        )
        self.assertIn(
            'core/r8q-javac-source-entry-isolation',
            text,
        )
        self.assertIn(
            'spk_recovery.r8q_source_entry_gate_cli',
            text,
        )

    @unittest.skipUnless(
        shutil.which("pwsh"),
        "PowerShell parser unavailable",
    )
    def test_wrapper_parses_with_powershell_ast(self):
        root = Path(__file__).resolve().parents[1]
        script = root / "scripts" / "Invoke-R8QExactSourceEntryGate.ps1"

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
            ["pwsh", "-NoProfile", "-Command", command],
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
