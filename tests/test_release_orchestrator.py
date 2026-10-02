from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.release_orchestrator import (
    ExistingAuthorityReleaseError,
    build_existing_authority_release,
    build_existing_authority_release_from_workspace,
)
from spk_recovery.release_orchestrator_cli import (
    main as release_cli_main,
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


def _official_clean():
    report = _clean()
    report["compile_transport"] = {
        "mode": "official_first_restored",
        "official_compile_id": "DEPOFFICIALCOMPILE_TEST",
        "overlay_id": "DEPSRCOVERLAY_TEST",
        "replacement_plan_id": "DEPREPLACE_TEST",
        "reverse_plan_id": "DEPREVERSE_TEST",
        "reverse_application_id": "DEPREVERSEAPPLY_TEST",
    }
    return report


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


class ExistingAuthorityReleaseWorkspaceTests(unittest.TestCase):
    def _derived_manifest(self):
        return {
            **_recovered(),
            "readable_jar_sha256": "f" * 64,
            "base_readable_jar_sha256": "b" * 64,
            "collision_transform_id": "COLLTRANS_TEST",
            "collision_plan_id": "COLLPLAN_TEST",
            "collision_report_id": "COLLREPORT_TEST",
            "collision_mapping_sha256": "d" * 64,
        }

    def test_incomplete_collision_derivation_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_jar, _decompiler = _inputs(root)
            source_root = root / "source"
            source_root.mkdir()
            plan = root / "plan.json"
            plan.write_text("{}\n", encoding="utf-8")

            manifest = self._derived_manifest()
            del manifest["collision_mapping_sha256"]

            with self.assertRaisesRegex(
                ExistingAuthorityReleaseError,
                "not complete collision-derived authority",
            ):
                build_existing_authority_release_from_workspace(
                    source_jar,
                    {},
                    {},
                    {},
                    manifest,
                    source_root,
                    plan,
                    build_id="v308",
                    out_dir=root / "out",
                )

    def test_base_readable_sha_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_jar, _decompiler = _inputs(root)
            source_root = root / "source"
            source_root.mkdir()
            plan = root / "plan.json"
            plan.write_text("{}\n", encoding="utf-8")
            manifest = self._derived_manifest()
            manifest["base_readable_jar_sha256"] = "0" * 64

            def readable_side_effect(*args, **kwargs):
                target = kwargs["out_dir"]
                target.mkdir(parents=True, exist_ok=True)
                (target / "readable-client.jar").write_bytes(
                    b"readable"
                )
                return _readable()

            with patch(
                "spk_recovery.release_orchestrator.build_readable_client",
                side_effect=readable_side_effect,
            ), self.assertRaisesRegex(
                ExistingAuthorityReleaseError,
                "base readable SHA-256",
            ):
                build_existing_authority_release_from_workspace(
                    source_jar,
                    {},
                    {},
                    {},
                    manifest,
                    source_root,
                    plan,
                    build_id="v308",
                    out_dir=root / "out",
                )

    def test_complete_collision_derived_path_reaches_release_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_jar, _decompiler = _inputs(root)
            source_root = root / "source"
            source_root.mkdir()
            (source_root / "A.java").write_text(
                "class A {}\n",
                encoding="utf-8",
            )
            plan = root / "plan.json"
            plan.write_text("{}\n", encoding="utf-8")
            manifest = self._derived_manifest()
            out = root / "out"

            def readable_side_effect(*args, **kwargs):
                target = kwargs["out_dir"]
                target.mkdir(parents=True, exist_ok=True)
                (target / "readable-client.jar").write_bytes(
                    b"readable"
                )
                return _readable()

            def rebuild_side_effect(*args, **kwargs):
                target = kwargs["out_dir"]
                target.mkdir(parents=True, exist_ok=True)
                (target / "rebuilt-client.jar").write_bytes(
                    b"rebuilt"
                )
                return _clean()

            with (
                patch(
                    "spk_recovery.release_orchestrator.build_readable_client",
                    side_effect=readable_side_effect,
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
                ) as clean,
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
                report = build_existing_authority_release_from_workspace(
                    source_jar,
                    {},
                    {},
                    {},
                    manifest,
                    source_root,
                    plan,
                    build_id="v308",
                    out_dir=out,
                    source_prefixes=["rs/"],
                )

            self.assertTrue(report["ready_for_release"])
            self.assertEqual(report["terminal_stage"], "release_manifest")
            self.assertEqual(
                report["stage_ids"]["collision_plan_id"],
                "COLLPLAN_TEST",
            )
            self.assertEqual(
                clean.call_args.kwargs[
                    "private_collision_plan_path"
                ],
                plan.resolve(),
            )
            self.assertEqual(
                clean.call_args.args[0],
                manifest,
            )
            release.assert_called_once()
            self.assertTrue(
                (
                    out
                    / "source-authority"
                    / "recovered-manifest.json"
                ).is_file()
            )


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
                    fallback_name_prefix="Safe_",
                )

            self.assertFalse(report["ready_for_release"])
            self.assertEqual(report["terminal_stage"], "readable_build")
            self.assertEqual(report["status"], "blocked")
            readable.assert_called_once()
            self.assertTrue(
                readable.call_args.kwargs["source_safe_fallback"]
            )
            self.assertEqual(
                readable.call_args.kwargs["fallback_name_prefix"],
                "Safe_",
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

    def test_official_first_transport_is_forwarded_and_recorded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_jar, decompiler = _inputs(root)
            out = root / "out"
            overlay_manifest = root / "overlay.json"
            overlay_root = root / "overlay"
            replacement = root / "replacement.json"
            reverse = root / "reverse.json"
            official = root / "official.jar"

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
                return _official_clean()

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
                ) as clean,
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
                ),
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
                    project_source_only=True,
                    official_first_restored=True,
                    official_overlay_manifest_path=overlay_manifest,
                    official_overlay_source_root=overlay_root,
                    private_dependency_replacement_plan_path=replacement,
                    private_dependency_reverse_plan_path=reverse,
                    official_artifacts=[official],
                )

            kwargs = clean.call_args.kwargs
            self.assertTrue(kwargs["official_first_restored"])
            self.assertEqual(
                kwargs["official_overlay_manifest_path"],
                overlay_manifest,
            )
            self.assertEqual(
                kwargs["official_overlay_source_root"],
                overlay_root,
            )
            self.assertEqual(
                kwargs["private_dependency_replacement_plan_path"],
                replacement,
            )
            self.assertEqual(
                kwargs["private_dependency_reverse_plan_path"],
                reverse,
            )
            self.assertEqual(kwargs["official_artifacts"], [official])
            self.assertEqual(
                report["stage_ids"]["official_compile_id"],
                "DEPOFFICIALCOMPILE_TEST",
            )
            self.assertEqual(
                report["stage_ids"]["dependency_reverse_application_id"],
                "DEPREVERSEAPPLY_TEST",
            )

    def test_official_first_requires_project_only_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_jar, decompiler = _inputs(root)

            with self.assertRaisesRegex(
                ExistingAuthorityReleaseError,
                "requires project_source_only",
            ):
                build_existing_authority_release(
                    source_jar,
                    {},
                    {},
                    {},
                    decompiler,
                    expected_decompiler_sha256="1" * 64,
                    engine="cfr",
                    build_id="v308",
                    out_dir=root / "out",
                    official_first_restored=True,
                )

    def test_release_cli_forwards_official_first_inputs(self):
        argv = [
            "client.jar",
            "index.json",
            "classes.json",
            "members.json",
            "decompiler.jar",
            "--decompiler-sha256",
            "1" * 64,
            "--engine",
            "cfr",
            "--build-id",
            "v308",
            "--project-source-only",
            "--official-first-restored",
            "--official-overlay-manifest",
            "overlay.json",
            "--official-overlay-source-root",
            "overlay-src",
            "--private-dependency-replacement-plan",
            "replacement.json",
            "--private-dependency-reverse-plan",
            "reverse.json",
            "--official-artifact",
            "official-a.jar",
            "--official-artifact",
            "official-b.jar",
            "--out-dir",
            "out",
        ]

        with (
            patch(
                "spk_recovery.release_orchestrator_cli._load",
                return_value={},
            ),
            patch(
                "spk_recovery.release_orchestrator_cli.load_lineage",
                return_value={},
            ),
            patch(
                "spk_recovery.release_orchestrator_cli.load_member_lineage",
                return_value={},
            ),
            patch(
                "spk_recovery.release_orchestrator_cli.build_existing_authority_release",
                return_value={
                    "run_id": "RELEASERUN_TEST",
                    "status": "complete",
                    "ready_for_release": True,
                    "terminal_stage": "release_manifest",
                },
            ) as build,
        ):
            code = release_cli_main(argv)

        self.assertEqual(code, 0)
        kwargs = build.call_args.kwargs
        self.assertTrue(kwargs["official_first_restored"])
        self.assertTrue(kwargs["project_source_only"])
        self.assertEqual(
            kwargs["official_overlay_manifest_path"],
            Path("overlay.json"),
        )
        self.assertEqual(
            kwargs["official_overlay_source_root"],
            Path("overlay-src"),
        )
        self.assertEqual(
            kwargs["private_dependency_replacement_plan_path"],
            Path("replacement.json"),
        )
        self.assertEqual(
            kwargs["private_dependency_reverse_plan_path"],
            Path("reverse.json"),
        )
        self.assertEqual(
            kwargs["official_artifacts"],
            [Path("official-a.jar"), Path("official-b.jar")],
        )

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
