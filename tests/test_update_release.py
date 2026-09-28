from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.update_release import migrate_update_to_release
from spk_recovery.update_release_cli import (
    main as update_release_cli_main,
)


def _write(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class UpdateReleaseTests(unittest.TestCase):
    def test_blocked_migration_never_promotes_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with (
                patch(
                    "spk_recovery.update_release.migrate_update",
                    return_value={
                        "workspace_id": "MIGWORK_TEST",
                        "ready_for_authority": False,
                        "focused_analysis_items": 2,
                        "authority_report_id": "AUTHCAND_TEST",
                    },
                ),
                patch(
                    "spk_recovery.update_release.promote_authority_snapshot"
                ) as promote,
            ):
                report = migrate_update_to_release(
                    {},
                    {},
                    root / "new.jar",
                    {},
                    {},
                    root / "decompiler.jar",
                    expected_decompiler_sha256="a" * 64,
                    engine="cfr",
                    old_build_id="v308",
                    new_build_id="v309",
                    new_build_number=309,
                    out_dir=root / "out",
                )

            self.assertFalse(report["ready_for_release"])
            self.assertEqual(report["terminal_stage"], "migration")
            promote.assert_not_called()

    def test_semantic_carryforward_block_stops_release(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "out"
            migration_dir = out / "migration"

            def migrate(*args, **kwargs):
                _write(migration_dir / "new-index.json", {"sha256": "b" * 64})
                _write(migration_dir / "migration-report.json", {"kind": "update_intake_report"})
                _write(migration_dir / "class-lineage.json", {"classes": []})
                _write(migration_dir / "member-lineage.json", {"members": []})
                _write(migration_dir / "authority-candidate.json", {"ready_for_authority": True})
                return {
                    "workspace_id": "MIGWORK_TEST",
                    "ready_for_authority": True,
                    "focused_analysis_items": 0,
                    "authority_report_id": "AUTHCAND_TEST",
                }

            with (
                patch(
                    "spk_recovery.update_release.migrate_update",
                    side_effect=migrate,
                ),
                patch(
                    "spk_recovery.update_release.promote_authority_snapshot",
                    return_value={"authority_id": "AUTHORITY_NEW"},
                ),
                patch(
                    "spk_recovery.update_release.write_authority_snapshot"
                ),
                patch(
                    "spk_recovery.update_release.build_semantic_carryforward",
                    return_value=(
                        {
                            "report_id": "SEMCARRY_TEST",
                            "ready_for_readable_build": False,
                            "summary": {"blocked": 1},
                        },
                        {},
                        {},
                        {},
                    ),
                ),
                patch(
                    "spk_recovery.update_release.write_semantic_json"
                ),
                patch(
                    "spk_recovery.update_release.build_existing_authority_release"
                ) as release,
            ):
                report = migrate_update_to_release(
                    {},
                    {},
                    root / "new.jar",
                    {},
                    {},
                    root / "decompiler.jar",
                    expected_decompiler_sha256="a" * 64,
                    engine="cfr",
                    old_build_id="v308",
                    new_build_id="v309",
                    new_build_number=309,
                    out_dir=out,
                )

            self.assertFalse(report["ready_for_release"])
            self.assertEqual(
                report["terminal_stage"],
                "semantic_carryforward",
            )
            release.assert_not_called()

    def test_ready_update_enters_existing_authority_release(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "out"
            migration_dir = out / "migration"

            def migrate(*args, **kwargs):
                _write(migration_dir / "new-index.json", {"sha256": "b" * 64})
                _write(migration_dir / "migration-report.json", {"kind": "update_intake_report"})
                _write(migration_dir / "class-lineage.json", {"classes": []})
                _write(migration_dir / "member-lineage.json", {"members": []})
                _write(migration_dir / "authority-candidate.json", {"ready_for_authority": True})
                return {
                    "workspace_id": "MIGWORK_TEST",
                    "ready_for_authority": True,
                    "focused_analysis_items": 0,
                    "authority_report_id": "AUTHCAND_TEST",
                }

            with (
                patch(
                    "spk_recovery.update_release.migrate_update",
                    side_effect=migrate,
                ),
                patch(
                    "spk_recovery.update_release.promote_authority_snapshot",
                    return_value={"authority_id": "AUTHORITY_NEW"},
                ),
                patch(
                    "spk_recovery.update_release.write_authority_snapshot"
                ),
                patch(
                    "spk_recovery.update_release.build_semantic_carryforward",
                    return_value=(
                        {
                            "report_id": "SEMCARRY_TEST",
                            "ready_for_readable_build": True,
                            "summary": {},
                        },
                        {},
                        {},
                        {},
                    ),
                ),
                patch(
                    "spk_recovery.update_release.write_semantic_json"
                ),
                patch(
                    "spk_recovery.update_release.build_existing_authority_release",
                    return_value={
                        "run_id": "RELEASE_RUN_TEST",
                        "ready_for_release": True,
                        "release_id": "RECOVERY_TEST",
                        "blocker": None,
                    },
                ) as release,
            ):
                report = migrate_update_to_release(
                    {},
                    {},
                    root / "new.jar",
                    {},
                    {},
                    root / "decompiler.jar",
                    expected_decompiler_sha256="a" * 64,
                    engine="cfr",
                    old_build_id="v308",
                    new_build_id="v309",
                    new_build_number=309,
                    out_dir=out,
                    source_safe_fallback=True,
                    fallback_name_prefix="Safe_",
                    project_source_only=True,
                    official_first_restored=True,
                    official_overlay_manifest_path=root / "overlay.json",
                    official_overlay_source_root=root / "overlay-src",
                    private_dependency_replacement_plan_path=(
                        root / "replacement.json"
                    ),
                    private_dependency_reverse_plan_path=(
                        root / "reverse.json"
                    ),
                    official_artifacts=[
                        root / "official-a.jar",
                        root / "official-b.jar",
                    ],
                )

            self.assertTrue(report["ready_for_release"])
            self.assertEqual(report["terminal_stage"], "release")
            self.assertEqual(report["release_id"], "RECOVERY_TEST")
            release.assert_called_once()
            self.assertTrue(
                release.call_args.kwargs["source_safe_fallback"]
            )
            self.assertEqual(
                release.call_args.kwargs["fallback_name_prefix"],
                "Safe_",
            )
            self.assertTrue(
                release.call_args.kwargs["project_source_only"]
            )
            self.assertTrue(
                release.call_args.kwargs["official_first_restored"]
            )
            self.assertEqual(
                release.call_args.kwargs[
                    "official_overlay_manifest_path"
                ],
                root / "overlay.json",
            )
            self.assertEqual(
                release.call_args.kwargs[
                    "official_overlay_source_root"
                ],
                root / "overlay-src",
            )
            self.assertEqual(
                release.call_args.kwargs[
                    "private_dependency_replacement_plan_path"
                ],
                root / "replacement.json",
            )
            self.assertEqual(
                release.call_args.kwargs[
                    "private_dependency_reverse_plan_path"
                ],
                root / "reverse.json",
            )
            self.assertEqual(
                release.call_args.kwargs["official_artifacts"],
                [root / "official-a.jar", root / "official-b.jar"],
            )

    def test_update_release_cli_forwards_official_first_inputs(self):
        argv = [
            "old-index.json",
            "old-authority.json",
            "new.jar",
            "classes.json",
            "members.json",
            "decompiler.jar",
            "--decompiler-sha256",
            "a" * 64,
            "--engine",
            "cfr",
            "--old-build-id",
            "v308",
            "--new-build-id",
            "v309",
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
                "spk_recovery.update_release_cli._load",
                return_value={},
            ),
            patch(
                "spk_recovery.update_release_cli.load_lineage",
                return_value={},
            ),
            patch(
                "spk_recovery.update_release_cli.load_member_lineage",
                return_value={},
            ),
            patch(
                "spk_recovery.update_release_cli.migrate_update_to_release",
                return_value={
                    "run_id": "UPDATEREL_TEST",
                    "status": "complete",
                    "ready_for_release": True,
                    "terminal_stage": "release",
                },
            ) as migrate,
        ):
            code = update_release_cli_main(argv)

        self.assertEqual(code, 0)
        kwargs = migrate.call_args.kwargs
        self.assertTrue(kwargs["project_source_only"])
        self.assertTrue(kwargs["official_first_restored"])
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


if __name__ == "__main__":
    unittest.main()
