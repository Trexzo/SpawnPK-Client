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

    def test_r8dep_wrapper_self_bootstraps_full_runtime_authority(self):
        text = self.dep.read_text(encoding="utf-8")
        self.assertIn(
            "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6",
            text,
        )
        self.assertIn(
            "e12e4f917ba2c48ea306e3b4d4cc19c58c5e23cd4f5c33f4ae339ea6fce53c99",
            text,
        )

        stages = [
            "spk_recovery.dependency_reference_surface",
            "spk_recovery.dependency_remap_proof",
            "spk_recovery.dependency_retention",
            "spk_recovery.dependency_replacement_plan_cli",
            "spk_recovery.dependency_runtime_frontier_cli",
            "spk_recovery.dependency_runtime_closure_cli",
            "spk_recovery.dependency_runtime_resource_cli",
            "spk_recovery.dependency_runtime_dynamic_cli",
            "spk_recovery.dependency_runtime_dynamic_target_cli",
            "spk_recovery.dependency_runtime_augmented_closure_cli",
            "spk_recovery.dependency_runtime_dynamic_mapping_cli",
            "spk_recovery.dependency_runtime_dynamic_member_cli",
            "spk_recovery.dependency_replacement_extension_cli",
            "spk_recovery.dependency_runtime_extended_closure_cli",
            "spk_recovery.dependency_runtime_extended_resource_cli",
            "spk_recovery.dependency_runtime_readiness_cli",
            "spk_recovery.dependency_runtime_substitution_plan_cli",
            "spk_recovery.dependency_runtime_substitution_apply_cli",
        ]
        positions = [text.index(stage) for stage in stages]
        self.assertEqual(positions, sorted(positions))

        self.assertIn('"apply"', text)
        self.assertIn('"verify"', text)
        self.assertIn("--include-identifiers", text)
        self.assertIn("SPK_R8DEP_EXACT_LOCAL_BLOCKED", text)
        self.assertIn("runtime_dependency_substitution_ready", text)
        self.assertIn("service_provider_discovery_blocker_count", text)
        self.assertIn("native_dynamic_requirement_count", text)
        self.assertIn("R8DEP38 EXACT LOCAL ACCEPTANCE - PASS", text)
        self.assertIn("origin/main", text)
        self.assertTrue(all(ord(ch) < 128 for ch in text))

    def test_source_m1_wrapper_bootstraps_collision_authority_from_exact_v308(self):
        text = self.source.read_text(encoding="utf-8")
        self.assertIn(
            "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6",
            text,
        )
        self.assertIn(
            "821da96012fc69244fa1ea298c90455ee4e021434bc796d3b9546ab24601b779",
            text,
        )
        stages = [
            "spk_recovery.readable_build_cli",
            "spk_recovery.namespace_collision_plan_cli",
            "spk_recovery.collision_bytecode_remap_cli",
            "spk_recovery.source_workspace_cli",
            "spk_recovery.release_workspace_orchestrator_cli",
            "spk_recovery.release_verify_cli",
            "spk_recovery.source_authority_artifact_cli",
            "spk_recovery.source_milestone_cli",
        ]
        positions = [text.index(stage) for stage in stages]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("--collision-transform-report", text)
        self.assertIn("--include-identifiers", text)
        self.assertIn("--private-collision-plan", text)
        self.assertIn("--project-only", text)
        self.assertIn("--source-safe-fallback", text)
        self.assertIn("plan_eliminates_all_collisions", text)
        self.assertIn("post_collision_edge_count", text)
        self.assertIn("SOURCE M1 EXACT LOCAL ACCEPTANCE - PASS", text)
        self.assertIn("SPK_SOURCE_M1_EXACT_LOCAL_BLOCKED", text)
        self.assertIn("javac_frontier_id", text)
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
