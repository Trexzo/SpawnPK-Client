from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.release_orchestrator import (
    ExistingAuthorityReleaseError,
    build_existing_authority_release,
)


def _inputs(root: Path):
    source_jar = root / "client.jar"
    source_jar.write_bytes(b"jar")
    decompiler = root / "decompiler.jar"
    decompiler.write_bytes(b"tool")
    return source_jar, decompiler


def _readable(status="complete"):
    return {
        "schema_version": 1,
        "kind": "readable_client_build_manifest",
        "manifest_id": "READABLE_TEST",
        "build_id": "v308",
        "status": status,
        "verification_pass": status == "complete",
        "output_sha256": "b" * 64 if status == "complete" else None,
        "blocker": (
            None
            if status == "complete"
            else {"code": "member_review_required"}
        ),
    }


def _recovered():
    return {
        "schema_version": 1,
        "kind": "recovered_source_workspace_manifest",
        "workspace_id": "SRCWS_TEST",
        "build_id": "v308",
        "source_authority_sha256": "a" * 64,
        "readable_jar_sha256": "b" * 64,
        "namespace_id": "SEMNS_TEST",
        "source_tree_sha256": "c" * 64,
    }


def _readiness():
    return {
        "schema_version": 1,
        "kind": "source_readiness_report",
        "audit_id": "SRCREADY_TEST",
    }


def _build_authority():
    return {
        "schema_version": 1,
        "kind": "build_authority_manifest",
        "authority_id": "BUILDAUTH_TEST",
    }


def _clean(status="complete"):
    return {
        "schema_version": 1,
        "kind": "clean_project_rebuild_report",
        "rebuild_id": "CLEANBUILD_TEST",
        "status": status,
        "clean_project_build": status == "complete",
        "diagnostic": "compile problem" if status != "complete" else "",
    }


def _roundtrip():
    return {
        "schema_version": 1,
        "kind": "round_trip_verification_report",
        "verification_id": "ROUNDTRIP_TEST",
    }


def _release(ready=True):
    return {
        "schema_version": 1,
        "kind": "recovery_release_manifest",
        "release_id": "RECOVERY_TEST",
        "ready_for_release": ready,
        "blockers": [] if ready else [{"reason": "roundtrip"}],
    }


class ExistingAuthorityReleaseTests(unittest.TestCase):
    def test_readable_block_stops_downstream_pipeline(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_jar, decompiler = _inputs(root)
            with (
                patch(
                    "spk_recovery.release_orchestrator.build_readable_client",
                    return_value=_readable("blocked"),
                ) as readable,
                patch(
                    "spk_recovery.release_orchestrator.build_source_workspace"
                ) as source,
            ):
                report = build_existing_authority_release(
                    source_jar,
                    {},
                    {},
                    {},
                    decompiler,
                    expected_decompiler_sha256="1" * 64,
                    engine="cfr",
                    build_id="v308",
                    out_dir=root / "out",
                    source_safe_fallback=True,
                    fallback_package="recovered/test/fallback",
                )

            self.assertFalse(report["ready_for_release"])
            self.assertEqual(report["terminal_stage"], "readable_build")
            self.assertEqual(report["status"], "blocked")
            readable.assert_called_once()
            self.assertTrue(
                readable.call_args.kwargs["source_safe_fallback"]
            )
            self.assertEqual(
                readable.call_args.kwargs["fallback_package"],
                "recovered/test/fallback",
            )
            source.assert_not_called()
            self.assertTrue((root / "out" / "release-run.json").is_file())

    def test_clean_rebuild_block_stops_before_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_jar, decompiler = _inputs(root)
            out = root / "out"

            def readable_side_effect(*args, **kwargs):
                target = kwargs["out_dir"]
                target.mkdir(parents=True, exist_ok=True)
                (target / "readable-client.jar").write_bytes(b"readable")
                return _readable()

            def source_side_effect(*args, **kwargs):
                target = kwargs["out_dir"]
                (target / "src").mkdir(parents=True, exist_ok=True)
                return _recovered()

            with (
                patch(
                    "spk_recovery.release_orchestrator.build_readable_client",
                    side_effect=readable_side_effect,
                ),
                patch(
                    "spk_recovery.release_orchestrator.build_source_workspace",
                    side_effect=source_side_effect,
                ),
                patch(
                    "spk_recovery.release_orchestrator.audit_source_workspace",
                    return_value=_readiness(),
                ),
                patch(
                    "spk_recovery.release_orchestrator.write_source_readiness_report"
                ),
                patch(
                    "spk_recovery.release_orchestrator.build_build_authority",
                    return_value=_build_authority(),
                ),
                patch(
                    "spk_recovery.release_orchestrator.write_build_authority"
                ),
                patch(
                    "spk_recovery.release_orchestrator.clean_project_rebuild",
                    return_value=_clean("compile_failed"),
                ),
                patch(
                    "spk_recovery.release_orchestrator.verify_clean_round_trip"
                ) as roundtrip,
            ):
                report = build_existing_authority_release(
                    source_jar,
                    {},
                    {},
                    {},
                    decompiler,
                    expected_decompiler_sha256="1" * 64,
                    engine="cfr",
                    build_id="v308",
                    out_dir=out,
                )

            self.assertFalse(report["ready_for_release"])
            self.assertEqual(report["terminal_stage"], "clean_rebuild")
            roundtrip.assert_not_called()

    def test_complete_path_reaches_release_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_jar, decompiler = _inputs(root)
            out = root / "out"

            def readable_side_effect(*args, **kwargs):
                target = kwargs["out_dir"]
                target.mkdir(parents=True, exist_ok=True)
                (target / "readable-client.jar").write_bytes(b"readable")
                return _readable()

            def source_side_effect(*args, **kwargs):
                target = kwargs["out_dir"]
                (target / "src").mkdir(parents=True, exist_ok=True)
                return _recovered()

            def rebuild_side_effect(*args, **kwargs):
                target = kwargs["out_dir"]
                target.mkdir(parents=True, exist_ok=True)
                (target / "rebuilt-client.jar").write_bytes(b"rebuilt")
                return _clean()

            with (
                patch(
                    "spk_recovery.release_orchestrator.build_readable_client",
                    side_effect=readable_side_effect,
                ),
                patch(
                    "spk_recovery.release_orchestrator.build_source_workspace",
                    side_effect=source_side_effect,
                ),
                patch(
                    "spk_recovery.release_orchestrator.audit_source_workspace",
                    return_value=_readiness(),
                ),
                patch(
                    "spk_recovery.release_orchestrator.write_source_readiness_report"
                ),
                patch(
                    "spk_recovery.release_orchestrator.build_build_authority",
                    return_value=_build_authority(),
                ),
                patch(
                    "spk_recovery.release_orchestrator.write_build_authority"
                ),
                patch(
                    "spk_recovery.release_orchestrator.clean_project_rebuild",
                    side_effect=rebuild_side_effect,
                ),
                patch(
                    "spk_recovery.release_orchestrator.verify_clean_round_trip",
                    return_value=_roundtrip(),
                ),
                patch(
                    "spk_recovery.release_orchestrator.write_roundtrip_report"
                ),
                patch(
                    "spk_recovery.release_orchestrator.build_recovery_release_manifest",
                    return_value=_release(True),
                ) as release,
                patch(
                    "spk_recovery.release_orchestrator.write_recovery_release_manifest"
                ),
            ):
                report = build_existing_authority_release(
                    source_jar,
                    {},
                    {},
                    {},
                    decompiler,
                    expected_decompiler_sha256="1" * 64,
                    engine="cfr",
                    build_id="v308",
                    out_dir=out,
                )

            self.assertTrue(report["ready_for_release"])
            self.assertEqual(report["status"], "complete")
            self.assertEqual(report["terminal_stage"], "release_manifest")
            self.assertEqual(report["release_id"], "RECOVERY_TEST")
            release.assert_called_once()

    def test_nonempty_output_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_jar, decompiler = _inputs(root)
            out = root / "out"
            out.mkdir()
            (out / "existing.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(ExistingAuthorityReleaseError):
                build_existing_authority_release(
                    source_jar,
                    {},
                    {},
                    {},
                    decompiler,
                    expected_decompiler_sha256="1" * 64,
                    engine="cfr",
                    build_id="v308",
                    out_dir=out,
                )


if __name__ == "__main__":
    unittest.main()
