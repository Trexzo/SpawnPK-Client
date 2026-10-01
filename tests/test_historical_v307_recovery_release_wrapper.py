from __future__ import annotations

from pathlib import Path
import unittest


class HistoricalV307RecoveryReleaseWrapperTests(unittest.TestCase):
    def test_historical_runner_pins_v307_without_publication_milestone(self):
        repo = Path(__file__).resolve().parents[1]
        script = (
            repo
            / "scripts"
            / "Invoke-HistoricalV307RecoveryRelease.ps1"
        )
        text = script.read_text(encoding="utf-8")

        self.assertIn(
            "fixtures\\v307-v308-source-regeneration.json",
            text,
        )
        self.assertIn('"--build-id",\n    "v307"', text)
        self.assertIn(
            "spk_recovery.release_workspace_orchestrator_cli",
            text,
        )
        self.assertIn(
            "spk_recovery.release_verify_cli",
            text,
        )
        self.assertIn(
            "spk_recovery.namespace_collision_plan_cli",
            text,
        )
        self.assertIn(
            "spk_recovery.collision_bytecode_remap_cli",
            text,
        )
        self.assertIn(
            "spk_recovery.source_workspace_cli",
            text,
        )
        self.assertIn(
            "HISTORICAL v307 RECOVERY RELEASE - PASS",
            text,
        )

        # Historical proof must stop before the v308-only publication gate.
        self.assertNotIn("source_milestone_cli", text)
        self.assertNotIn("SOURCE-MILESTONE.json", text)

    def test_historical_runner_checks_exact_binary_and_decompiler_authority(self):
        repo = Path(__file__).resolve().parents[1]
        text = (
            repo
            / "scripts"
            / "Invoke-HistoricalV307RecoveryRelease.ps1"
        ).read_text(encoding="utf-8")

        for pointer in (
            'old_client_sha256 = "/old/client_sha256"',
            'decompiler_sha256 = "/decompiler_authority/sha256"',
            'decompiler_size_bytes = "/decompiler_authority/size_bytes"',
            'sha256 = "/sha256"',
        ):
            self.assertIn(pointer, text)

        self.assertIn(
            "Exact historical v307 SHA mismatch",
            text,
        )
        self.assertIn("Exact Procyon SHA mismatch", text)
        self.assertIn("Exact Procyon size mismatch", text)
        self.assertIn(
            "Historical source index is not bound to exact v307",
            text,
        )

    def test_historical_runner_verifies_release_manifest_before_pass(self):
        repo = Path(__file__).resolve().parents[1]
        text = (
            repo
            / "scripts"
            / "Invoke-HistoricalV307RecoveryRelease.ps1"
        ).read_text(encoding="utf-8")

        for marker in (
            'build_id = "/build_id"',
            'authority_sha256 = "/authority_sha256"',
            'release_id = "/release_id"',
            'ready_for_release = "/ready_for_release"',
            'final_source_tree_sha256 = "/final_source_tree_sha256"',
            'verified = "/verified"',
        ):
            self.assertIn(marker, text)

        self.assertIn(
            "Historical release verification failed.",
            text,
        )
        self.assertIn(
            "Historical release verification linkage mismatch.",
            text,
        )


if __name__ == "__main__":
    unittest.main()
