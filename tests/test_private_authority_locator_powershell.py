from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


REQUIRED = (
    "v308-index.json",
    "class-lineage.accepted.json",
    "member-lineage.accepted.json",
    "member-safety.accepted.json",
)


@unittest.skipUnless(
    os.name == "nt" and shutil.which("powershell.exe"),
    "Windows PowerShell required",
)
class PrivateAuthorityLocatorPowerShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parents[1]
        self.script = (
            self.repo / "scripts" / "Find-SourceM1PrivateAuthority.ps1"
        )

    def run_locator(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.script),
                *args,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def write_set(
        self,
        authority: Path,
        *,
        suffix: str = "",
    ) -> dict[str, bytes]:
        authority.mkdir(parents=True, exist_ok=True)
        payloads: dict[str, bytes] = {}
        for index, name in enumerate(REQUIRED):
            payload = (
                '{"fixture":'
                + str(index)
                + ',"name":"'
                + name
                + '","suffix":"'
                + suffix
                + '"}\n'
            ).encode("utf-8")
            (authority / name).write_bytes(payload)
            payloads[name] = payload
        return payloads

    def test_locator_script_parses(self) -> None:
        literal = str(self.script).replace("'", "''")
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
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_directory_candidate_materializes_byte_identical_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            payloads = self.write_set(
                root / "SpawnPK-R8N-Private.bak-test" / "authority"
            )
            out = Path(temp) / "materialized"

            proc = self.run_locator(
                "-Roots",
                str(root),
                "-SkipArchives",
                "-MaterializeDir",
                str(out),
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn(
                "SOURCE_M1_PRIVATE_AUTHORITY_FOUND=1",
                proc.stdout,
            )
            self.assertIn(
                "SOURCE_M1_PRIVATE_AUTHORITY_MATERIALIZED=1",
                proc.stdout,
            )
            self.assertIn("AUTHORITY_SET_VARIANT_COUNT=1", proc.stdout)

            for name, expected in payloads.items():
                self.assertEqual((out / name).read_bytes(), expected)

    def test_zip_candidate_materializes_byte_identical_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            root.mkdir(parents=True)
            source = Path(temp) / "source" / "authority"
            payloads = self.write_set(source)
            archive = root / "SpawnPK-R8N-Private-backup.zip"

            with zipfile.ZipFile(
                archive,
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ) as handle:
                for name in REQUIRED:
                    handle.write(
                        source / name,
                        arcname=f"backup/authority/{name}",
                    )

            out = Path(temp) / "materialized"
            proc = self.run_locator(
                "-Roots",
                str(root),
                "-MaterializeDir",
                str(out),
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("AUTHORITY_CANDIDATE_1_KIND=zip", proc.stdout)
            self.assertIn(
                "SOURCE_M1_PRIVATE_AUTHORITY_MATERIALIZED=1",
                proc.stdout,
            )

            for name, expected in payloads.items():
                self.assertEqual((out / name).read_bytes(), expected)

    def test_conflicting_complete_sets_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            self.write_set(root / "one" / "authority", suffix="one")
            self.write_set(root / "two" / "authority", suffix="two")

            proc = self.run_locator(
                "-Roots",
                str(root),
                "-SkipArchives",
            )

            self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
            self.assertIn(
                "SOURCE_M1_PRIVATE_AUTHORITY_CONFLICT=1",
                proc.stdout,
            )
            self.assertIn("AUTHORITY_SET_VARIANT_COUNT=2", proc.stdout)

    def test_missing_complete_set_returns_blocked_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            root.mkdir(parents=True)

            proc = self.run_locator(
                "-Roots",
                str(root),
                "-SkipArchives",
            )

            self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
            self.assertIn(
                "SOURCE_M1_PRIVATE_AUTHORITY_NOT_FOUND=1",
                proc.stdout,
            )


if __name__ == "__main__":
    unittest.main()
