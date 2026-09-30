from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from spk_recovery.json_projection_cli import main, project


class JsonProjectionTests(unittest.TestCase):
    def test_case_distinct_source_keys_are_preserved(self):
        document = {
            "payload": {
                "D": 1,
                "d": 2,
            },
            "status": "complete",
        }

        result = project(
            document,
            required=[
                ("upper", "/payload/D"),
                ("lower", "/payload/d"),
                ("status", "/status"),
            ],
            optional=[],
        )

        self.assertEqual(
            result,
            {
                "upper": 1,
                "lower": 2,
                "status": "complete",
            },
        )

    def test_aliases_colliding_case_insensitively_are_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "collide case-insensitively",
        ):
            project(
                {"a": 1, "b": 2},
                required=[
                    ("Value", "/a"),
                    ("value", "/b"),
                ],
                optional=[],
            )

    def test_optional_missing_pointer_projects_null(self):
        result = project(
            {"status": "complete"},
            required=[("status", "/status")],
            optional=[("frontier", "/compiler/frontier")],
        )

        self.assertEqual(result["status"], "complete")
        self.assertIsNone(result["frontier"])

    def test_cli_projects_case_distinct_nested_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "authority.json"
            path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "D": 7,
                            "d": 8,
                        },
                        "verified": True,
                    }
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = main(
                    [
                        str(path),
                        "--field",
                        "upper=/summary/D",
                        "--field",
                        "lower=/summary/d",
                        "--field",
                        "verified=/verified",
                    ]
                )

            self.assertEqual(code, 0, stderr.getvalue())
            self.assertEqual(
                json.loads(stdout.getvalue()),
                {
                    "lower": 8,
                    "upper": 7,
                    "verified": True,
                },
            )

    def test_cli_validate_only_accepts_case_distinct_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "valid.json"
            path.write_text(
                '{"payload":{"D":1,"d":2}}',
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = main(
                    [
                        str(path),
                        "--validate-only",
                    ]
                )

            self.assertEqual(code, 0, stderr.getvalue())
            self.assertEqual(
                stdout.getvalue().strip(),
                "SPK_JSON_VALIDATION_PASS",
            )

    def test_cli_validate_only_rejects_field_projection_mix(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "valid.json"
            path.write_text(
                '{"status":"complete"}',
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = main(
                    [
                        str(path),
                        "--validate-only",
                        "--field",
                        "status=/status",
                    ]
                )

            self.assertEqual(code, 2)
            self.assertIn(
                "cannot be combined",
                stderr.getvalue(),
            )
    def test_cli_rejects_exact_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "duplicate.json"
            path.write_text(
                '{"value":1,"value":2}',
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = main(
                    [
                        str(path),
                        "--field",
                        "value=/value",
                    ]
                )

            self.assertEqual(code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn(
                "duplicate JSON key",
                stderr.getvalue(),
            )

    def test_source_m1_acceptance_never_deserializes_raw_json_in_powershell(self):
        repo = Path(__file__).resolve().parents[1]
        script = repo / "scripts" / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        text = script.read_text(encoding="utf-8")

        self.assertEqual(
            text.count("| ConvertFrom-Json"),
            1,
            "only the controlled projection helper may use ConvertFrom-Json",
        )
        self.assertIn(
            "spk_recovery.json_projection_cli",
            text,
        )
        for raw_path in (
            "$BootstrapReadableManifest",
            "$CollisionPlan",
            "$CollisionTransform",
            "$RecoveredManifest",
            "$RunPath",
            "$CleanPath",
            "$MilestoneManifest",
            "$MilestoneVerification",
            "$BundleVerification",
        ):
            self.assertNotIn(
                f"Get-Content -LiteralPath {raw_path} -Raw | ConvertFrom-Json",
                text,
            )

    @unittest.skipUnless(
        shutil.which("powershell.exe"),
        "Windows PowerShell parser is unavailable",
    )
    def test_source_m1_acceptance_parses_in_windows_powershell(self):
        repo = Path(__file__).resolve().parents[1]
        script = repo / "scripts" / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        command = (
            "$tokens=$null; $errors=$null; "
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "'" + str(script).replace("'", "''") + "', "
            "[ref]$tokens, [ref]$errors) | Out-Null; "
            "if ($errors.Count -ne 0) { "
            "$errors | ForEach-Object { Write-Error $_.Message }; exit 1 }; "
            "exit 0"
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
    def test_r8dep_acceptance_never_deserializes_raw_json_in_powershell(self):
        repo = Path(__file__).resolve().parents[1]
        script = repo / "scripts" / "Invoke-R8DEP38ExactLocalAcceptance.ps1"
        text = script.read_text(encoding="utf-8")

        self.assertEqual(
            text.count("| ConvertFrom-Json"),
            1,
            "only the controlled projection helper may use ConvertFrom-Json",
        )
        self.assertIn("--validate-only", text)
        self.assertIn("spk_recovery.json_projection_cli", text)
        for raw_path in (
            "$Out",
            "$RuntimeReadiness",
            "$ManifestPath",
        ):
            self.assertNotIn(
                f"Get-Content -LiteralPath {raw_path} -Raw | ConvertFrom-Json",
                text,
            )

    @unittest.skipUnless(
        shutil.which("powershell.exe"),
        "Windows PowerShell parser is unavailable",
    )
    def test_r8dep_acceptance_parses_in_windows_powershell(self):
        repo = Path(__file__).resolve().parents[1]
        script = repo / "scripts" / "Invoke-R8DEP38ExactLocalAcceptance.ps1"
        command = (
            "$tokens=$null; $errors=$null; "
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "'" + str(script).replace("'", "''") + "', "
            "[ref]$tokens, [ref]$errors) | Out-Null; "
            "if ($errors.Count -ne 0) { "
            "$errors | ForEach-Object { Write-Error $_.Message }; exit 1 }; "
            "exit 0"
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
    def test_cli_refuses_missing_required_pointer(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "missing.json"
            path.write_text(
                '{"status":"complete"}',
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = main(
                    [
                        str(path),
                        "--field",
                        "frontier=/compiler/frontier",
                    ]
                )

            self.assertEqual(code, 2)
            self.assertIn(
                "required JSON Pointer is missing",
                stderr.getvalue(),
            )


if __name__ == "__main__":
    unittest.main()
