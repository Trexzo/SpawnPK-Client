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
            "spk_recovery.javac_build_binding_cli",
            text,
        )
        self.assertIn(
            "SpawnPK-Historical-v307-Backtest"
            "\\recovery-release\\release"
            "\\javac-diagnostic-private.json",
            text,
        )
        self.assertIn(
            "SpawnPK-Historical-v307-Backtest"
            "\\recovery-release\\release"
            "\\rebuild\\clean-rebuild.json",
            text,
        )
        self.assertIn(
            "SpawnPK-SourceM1-Exact"
            "\\release\\javac-diagnostic-private.json",
            text,
        )
        self.assertIn(
            "SpawnPK-SourceM1-Exact"
            "\\release\\rebuild\\clean-rebuild.json",
            text,
        )
        self.assertIn(
            "SpawnPK-Historical-v307-Backtest"
            "\\recovery-release\\release"
            "\\javac-build-binding.json",
            text,
        )
        self.assertIn(
            "SpawnPK-SourceM1-Exact"
            "\\release\\javac-build-binding.json",
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
        self.assertIn(
            "spk_recovery.cross_version_javac_checkpoint_cli",
            text,
        )
        self.assertIn(
            'v307-v308-javac-checkpoint.json',
            text,
        )
        self.assertIn(
            "XVERBIN_E56BD2FB8CCC172D6184",
            text,
        )
        self.assertIn(
            "Refusing unexpected identifier-bearing checkpoint.",
            text,
        )
        self.assertIn("CHECKPOINT_ID=", text)
        self.assertIn("CHECKPOINT=", text)
        self.assertIn(
            "spk_recovery.cross_version_javac_legacy_baseline_delta_cli",
            text,
        )
        self.assertIn(
            "spk_recovery.cross_version_javac_legacy_baseline_delta_verify_cli",
            text,
        )
        self.assertIn(
            "Legacy 350 baseline delta verification failed",
            text,
        )
        self.assertIn(
            "v307-v308-source-m1-exact-javac-parity-07ed6f9.json",
            text,
        )
        self.assertIn("legacy-350-to-current-delta.json", text)
        self.assertIn(
            "Refusing unexpected identifier-bearing legacy baseline delta.",
            text,
        )
        self.assertIn(
            "Legacy baseline delta does not bind the emitted checkpoint.",
            text,
        )
        self.assertIn("LEGACY_BASELINE_DELTA_ID=", text)
        self.assertIn("V307_ERRORS_DELTA_FROM_350=", text)
        self.assertIn("V308_ERRORS_DELTA_FROM_350=", text)
        self.assertIn("EXACT_FRONTIER_EQUALITY_TRANSITION=", text)
        self.assertIn("LEGACY_BASELINE_DELTA=", text)

    def test_runner_pins_build_and_binary_authority(self):
        repo = Path(__file__).resolve().parents[1]
        text = (
            repo
            / "scripts"
            / "Invoke-CrossVersionJavacFrontier.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "6232bae206846a4ba8d09766a2dee886"
            "b69016066a3f50f83b201bf705f93662",
            text,
        )
        self.assertIn(
            "854f26ff9f134b0317572e7ac1688e6f"
            "40a231d5a4c66f8db5d655b7f45ce7c6",
            text,
        )
        self.assertIn('--expected-build-id"', text)
        self.assertIn('"v307"', text)
        self.assertIn('"v308"', text)
        self.assertIn('"--tooling-commit"', text)
        self.assertIn(
            "Recovery tooling commit mismatch",
            text,
        )
        self.assertIn(
            "recorded javac build binding failed verification",
            text,
        )
        self.assertIn(
            "build binding does not match comparator input authority",
            text,
        )

    def test_runner_surfaces_overlap_and_build_authority(self):
        repo = Path(__file__).resolve().parents[1]
        text = (
            repo
            / "scripts"
            / "Invoke-CrossVersionJavacFrontier.ps1"
        ).read_text(encoding="utf-8")

        for marker in (
            "REPORT_ID=",
            "INPUT_TOOLING_COMMIT=",
            "V307_BINDING_ID=",
            "V308_BINDING_ID=",
            "V307_SOURCE_AUTHORITY=",
            "V308_SOURCE_AUTHORITY=",
            "V307_REBUILD_ID=",
            "V308_REBUILD_ID=",
            "V307_WORKSPACE_ID=",
            "V308_WORKSPACE_ID=",
            "V307_SOURCE_TREE_SHA256=",
            "V308_SOURCE_TREE_SHA256=",
            "V307_DIAGNOSTIC_REPORT_ID=",
            "V308_DIAGNOSTIC_REPORT_ID=",
            "V307_DIAGNOSTIC_INPUT_SHA256=",
            "V308_DIAGNOSTIC_INPUT_SHA256=",
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
