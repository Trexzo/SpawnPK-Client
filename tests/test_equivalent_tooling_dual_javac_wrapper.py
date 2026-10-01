from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import unittest


class EquivalentToolingDualJavacWrapperTests(unittest.TestCase):
    def script_text(self) -> str:
        root = Path(__file__).resolve().parents[1]
        return (
            root
            / "scripts"
            / "Invoke-EquivalentToolingV307V308JavacBacktest.ps1"
        ).read_text(encoding="utf-8")

    def test_composes_both_exact_runners_and_comparator(self):
        text = self.script_text()
        self.assertIn(
            "Invoke-HistoricalV307FullBacktest.ps1",
            text,
        )
        self.assertIn(
            "Invoke-SourceM1ExactLocalAcceptance.ps1",
            text,
        )
        self.assertIn(
            "Invoke-CrossVersionJavacFrontier.ps1",
            text,
        )
        self.assertIn(
            "RUN EXACT v307 HISTORICAL BACKTEST",
            text,
        )
        self.assertIn(
            "RUN EXACT v308 SOURCE M1 ACCEPTANCE",
            text,
        )
        self.assertIn(
            "COMPARE SAME-COMMIT v307-v308 FRONTIERS",
            text,
        )

    def test_freezes_single_exact_main_across_both_runs(self):
        text = self.script_text()
        self.assertIn("git -C $Repo fetch origin main", text)
        self.assertIn("Local HEAD is not exact origin/main", text)
        self.assertIn("TOOLING_COMMIT=$Head", text)
        self.assertIn(
            "git clone --bare --no-hardlinks $Repo $FrozenOrigin",
            text,
        )
        self.assertIn(
            "git clone --no-hardlinks --single-branch --branch main",
            text,
        )
        self.assertIn("Assert-FrozenToolingRepo", text)
        self.assertIn("FROZEN_TOOLING_COMMIT=$Head", text)
        self.assertIn("FROZEN_TOOLING_REPO=$FrozenRepo", text)
        self.assertIn("LIVE_MAIN_ADVANCED=true", text)
        self.assertIn("LATEST_ORIGIN_MAIN=", text)
        self.assertNotIn(
            "Recovery tooling authority changed after v307 run",
            text,
        )
        self.assertNotIn(
            "Recovery tooling authority changed after v308 run",
            text,
        )
        self.assertIn(
            "v307 binding tooling commit drifted",
            text,
        )
        self.assertIn(
            "v308 binding tooling commit drifted",
            text,
        )

    @unittest.skipUnless(shutil.which("git"), "git required")
    def test_frozen_bare_origin_survives_source_main_advancing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            bare = root / "frozen.git"
            frozen = root / "frozen"

            subprocess.run(
                ["git", "init", "-b", "main", str(source)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(source), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(source), "config", "user.name", "Test"],
                check=True,
            )
            (source / "marker.txt").write_text("captured\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(source), "add", "marker.txt"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(source), "commit", "-m", "captured"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            captured = subprocess.check_output(
                ["git", "-C", str(source), "rev-parse", "HEAD"],
                text=True,
            ).strip()

            subprocess.run(
                ["git", "clone", "--bare", "--no-hardlinks", str(source), str(bare)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(bare), "update-ref", "refs/heads/main", captured],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(bare), "symbolic-ref", "HEAD", "refs/heads/main"],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--no-hardlinks",
                    "--single-branch",
                    "--branch",
                    "main",
                    str(bare),
                    str(frozen),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            (source / "marker.txt").write_text("advanced\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(source), "add", "marker.txt"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(source), "commit", "-m", "advanced"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            advanced = subprocess.check_output(
                ["git", "-C", str(source), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            self.assertNotEqual(captured, advanced)

            subprocess.run(
                ["git", "-C", str(frozen), "fetch", "origin", "main"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            frozen_head = subprocess.check_output(
                ["git", "-C", str(frozen), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            frozen_remote = subprocess.check_output(
                ["git", "-C", str(frozen), "rev-parse", "origin/main"],
                text=True,
            ).strip()

            self.assertEqual(frozen_head, captured)
            self.assertEqual(frozen_remote, captured)

    def test_frozen_snapshot_cleanup_is_normal_exit_only(self):
        text = self.script_text()
        self.assertIn("Remove-FrozenToolingSnapshot", text)
        self.assertIn("FROZEN_TOOLING_CLEANED=", text)
        self.assertIn("FROZEN_TOOLING_CLEANUP_FAILED=", text)
        self.assertIn(
            "unexpected failure preserves the frozen snapshot for diagnosis",
            text,
        )

    def test_blocked_children_still_feed_comparator(self):
        text = self.script_text()
        self.assertIn(
            "$Exit -ne 0 -and $Exit -ne 3",
            text,
        )
        self.assertIn(
            "EQUIVALENT_TOOLING_V307_V308_BLOCKED_AT_SOURCE_FRONTIER",
            text,
        )
        self.assertIn(
            "EQUIVALENT_TOOLING_RECOVERY_RELEASES_READY=false",
            text,
        )
        self.assertIn(
            "$V307Exit -eq 0 -and $V308Exit -eq 0",
            text,
        )
        self.assertIn("exit 3", text)

    def test_generates_missing_success_path_bindings(self):
        text = self.script_text()
        self.assertIn(
            "spk_recovery.javac_build_binding_cli",
            text,
        )
        self.assertIn(
            "Ensure-JavacBuildBinding",
            text,
        )
        self.assertIn(
            "GENERATED_JAVAC_BUILD_BINDING=",
            text,
        )
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

    def test_requires_private_binding_evidence_from_each_run(self):
        text = self.script_text()
        for marker in (
            "javac-diagnostic-private.json",
            "rebuild\\clean-rebuild.json",
            "javac-build-binding.json",
            "V307_BINDING_ID=",
            "V308_BINDING_ID=",
            "V307_FRONTIER=",
            "V308_FRONTIER=",
            "SHARED_ERRORS=",
            "EXACT_FRONTIER_EQUAL=",
            "REPORT_ID=",
        ):
            self.assertIn(marker, text)

    def test_preserves_previous_outputs(self):
        text = self.script_text()
        self.assertIn("Backup-NonEmptyDirectory", text)
        self.assertIn('".bak-"', text)
        self.assertIn("PREVIOUS_OUTPUT_BACKED_UP=", text)
        self.assertIn(
            "Backup-NonEmptyDirectory -Path $V307Out",
            text,
        )
        self.assertIn(
            "Backup-NonEmptyDirectory -Path $V308Out",
            text,
        )
        self.assertIn(
            "Backup-NonEmptyDirectory -Path $CompareOut",
            text,
        )

    def test_does_not_take_semantic_or_source_repair_ownership(self):
        text = self.script_text()
        self.assertNotIn("semantic_proposal", text)
        self.assertNotIn("source_milestone_cli", text)
        self.assertNotIn("source_rewrite_plan_cli", text)

    @unittest.skipUnless(
        os.name == "nt" and shutil.which("powershell.exe"),
        "Windows PowerShell required",
    )
    def test_wrapper_parses_in_windows_powershell(self):
        root = Path(__file__).resolve().parents[1]
        script = (
            root
            / "scripts"
            / "Invoke-EquivalentToolingV307V308JavacBacktest.ps1"
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


if __name__ == "__main__":
    unittest.main()
