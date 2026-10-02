from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.release_verify import (
    RecoveryReleaseVerificationError,
    _load_json_authority,
    _private_mapping_sha256,
    verify_recovery_release,
)
from spk_recovery.release_verify_cli import _load as _verify_cli_load


def _release():
    return {
        "schema_version": 1,
        "kind": "recovery_release_manifest",
        "release_id": "RECOVERY_0123456789ABCDEF0123",
        "authority_sha256": hashlib.sha256(b"authority").hexdigest(),
        "readable_jar_sha256": hashlib.sha256(b"readable").hexdigest(),
        "final_source_tree_sha256": "c" * 64,
        "ready_for_release": True,
    }


def _tree_sha(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(root.rglob("*.java")):
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def _official_first_fixture(root: Path) -> dict:
    readable_sha = "b" * 64
    canonical_sha = "c" * 64

    overlay_root = root / "overlay-src"
    source = overlay_root / "app" / "Use.java"
    source.parent.mkdir(parents=True)
    source.write_text(
        "package app; public class Use {}\n",
        encoding="utf-8",
    )
    overlay_sha = _tree_sha(overlay_root)

    official = root / "official.jar"
    official.write_bytes(b"official dependency")
    official_sha = hashlib.sha256(
        official.read_bytes()
    ).hexdigest()

    replacement_id = "DEPREPLACE_" + "1" * 20
    reverse_id = "DEPREVERSE_" + "2" * 20
    overlay_id = "DEPSRCOVERLAY_" + "3" * 20

    overlay = {
        "schema_version": 1,
        "kind": "dependency_source_overlay_manifest",
        "overlay_id": overlay_id,
        "replacement_plan_id": replacement_id,
        "input_source_tree_sha256": canonical_sha,
        "output_source_tree_sha256": overlay_sha,
        "bundled_jar_sha256": readable_sha,
        "official_artifact_sha256": [official_sha],
    }
    overlay_path = root / "overlay.json"
    overlay_path.write_text(
        json.dumps(overlay) + "\n",
        encoding="utf-8",
    )

    replacement = {
        "schema_version": 1,
        "kind": "dependency_replacement_boundary_plan",
        "replacement_plan_id": replacement_id,
        "bundled_jar_sha256": readable_sha,
        "identifiers_included": True,
        "official_artifacts": [
            {
                "artifact": "official.jar",
                "sha256": official_sha,
                "multi_release_class_count": 0,
                "java_release": 9,
            }
        ],
    }
    replacement_path = root / "replacement.json"
    replacement_path.write_text(
        json.dumps(replacement) + "\n",
        encoding="utf-8",
    )

    reverse = {
        "schema_version": 1,
        "kind": "dependency_reverse_compile_transport_plan",
        "reverse_plan_id": reverse_id,
        "replacement_plan_id": replacement_id,
        "bundled_jar_sha256": readable_sha,
        "identifiers_included": True,
        "summary": {
            "ready_for_bytecode_restore": True,
        },
    }
    reverse_path = root / "reverse.json"
    reverse_path.write_text(
        json.dumps(reverse) + "\n",
        encoding="utf-8",
    )

    clean = {
        "readable_jar_sha256": readable_sha,
        "source_tree_sha256": canonical_sha,
        "compile_transport": {
            "mode": "official_first_restored",
            "overlay_id": overlay_id,
            "replacement_plan_id": replacement_id,
            "reverse_plan_id": reverse_id,
            "official_artifact_sha256": [official_sha],
        },
    }

    return {
        "clean": clean,
        "overlay_path": overlay_path,
        "overlay_root": overlay_root,
        "replacement_path": replacement_path,
        "reverse_path": reverse_path,
        "official": official,
    }


class ReleaseVerificationTests(unittest.TestCase):
    def test_release_authority_loaders_reject_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            nested = root / "nested.json"
            nested.write_text(
                '{"kind":"recovery_release_manifest","n":{"x":1,"x":2}}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                RecoveryReleaseVerificationError,
                "duplicate JSON key: 'x'",
            ):
                _load_json_authority(
                    nested,
                    label="release",
                    kind="recovery_release_manifest",
                )

            top = root / "top.json"
            top.write_text(
                '{"kind":"a","kind":"b"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                RecoveryReleaseVerificationError,
                "duplicate JSON key: 'kind'",
            ):
                _verify_cli_load(top)

    def test_exact_manifest_reproduction_passes(self):
        release = _release()
        with patch(
            "spk_recovery.release_verify.build_recovery_release_manifest",
            return_value=release.copy(),
        ):
            report = verify_recovery_release(
                release,
                {},
                {},
                {},
                {},
                {},
                {},
                {},
            )
        self.assertTrue(report["verified"])
        self.assertEqual(report["failed_required_check_count"], 0)
        self.assertEqual(
            report["checks"][0]["name"],
            "release_manifest_exact_reproduction",
        )

    def test_stale_manifest_reproduction_is_reported(self):
        release = _release()
        changed = release.copy()
        changed["release_id"] = "RECOVERY_FEDCBA98765432100123"
        with patch(
            "spk_recovery.release_verify.build_recovery_release_manifest",
            return_value=changed,
        ):
            report = verify_recovery_release(
                release,
                {},
                {},
                {},
                {},
                {},
                {},
                {},
            )
        self.assertFalse(report["verified"])
        self.assertEqual(report["failed_required_check_count"], 1)

    def test_collision_private_plan_provenance_passes(self):
        release = _release()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan_path = root / "collision-plan.json"
            plan = {
                "schema_version": 1,
                "kind": "class_package_namespace_collision_plan",
                "plan_id": "JNSPLAN_TEST",
                "collision_report_id": "JNSCOLLISION_TEST",
                "readable_jar_sha256": "b" * 64,
                "identifiers_included": True,
                "remaps": [],
            }
            plan_path.write_text(
                json.dumps(plan, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            plan_sha = hashlib.sha256(
                plan_path.read_bytes()
            ).hexdigest()

            recovered = {
                "collision_plan_id": "JNSPLAN_TEST",
                "collision_report_id": "JNSCOLLISION_TEST",
                "collision_transform_id": "COLLTRANS_TEST",
                "base_readable_jar_sha256": "b" * 64,
                "collision_mapping_sha256": _private_mapping_sha256(plan),
            }
            clean = {
                "readable_jar_sha256": "b" * 64,
                "compile_transport": {
                    "mode": "collision_derived_remap",
                    "collision_plan_id": "JNSPLAN_TEST",
                    "collision_plan_sha256": plan_sha,
                    "collision_report_id": "JNSCOLLISION_TEST",
                    "collision_transform_id": "COLLTRANS_TEST",
                },
            }

            with patch(
                "spk_recovery.release_verify.build_recovery_release_manifest",
                return_value=release.copy(),
            ):
                report = verify_recovery_release(
                    release,
                    {},
                    {},
                    {},
                    {},
                    recovered,
                    clean,
                    {},
                    private_collision_plan_path=plan_path,
                )

            self.assertTrue(report["verified"])
            names = {row["name"] for row in report["checks"]}
            self.assertIn("collision_private_plan_sha256", names)
            self.assertIn("collision_private_plan_id", names)
            self.assertIn("collision_private_plan_report_id", names)
            self.assertIn(
                "collision_private_plan_readable_sha256",
                names,
            )
            self.assertIn(
                "collision_private_mapping_sha256",
                names,
            )

    def test_collision_private_mapping_drift_is_rejected(self):
        release = _release()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan_path = root / "collision-plan.json"
            plan = {
                "schema_version": 1,
                "kind": "class_package_namespace_collision_plan",
                "plan_id": "JNSPLAN_TEST",
                "collision_report_id": "JNSCOLLISION_TEST",
                "readable_jar_sha256": "b" * 64,
                "identifiers_included": True,
                "remaps": [
                    {
                        "old_internal_name": "dep/A",
                        "new_internal_name": "dep/Recovered_A",
                    }
                ],
            }
            accepted_mapping = _private_mapping_sha256(plan)
            plan_path.write_text(
                json.dumps(plan, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            plan_sha = hashlib.sha256(
                plan_path.read_bytes()
            ).hexdigest()

            recovered = {
                "collision_plan_id": "JNSPLAN_TEST",
                "collision_report_id": "JNSCOLLISION_TEST",
                "collision_transform_id": "COLLTRANS_TEST",
                "base_readable_jar_sha256": "b" * 64,
                "collision_mapping_sha256": accepted_mapping,
            }
            clean = {
                "readable_jar_sha256": "b" * 64,
                "compile_transport": {
                    "mode": "collision_derived_remap",
                    "collision_plan_id": "JNSPLAN_TEST",
                    "collision_plan_sha256": plan_sha,
                    "collision_report_id": "JNSCOLLISION_TEST",
                    "collision_transform_id": "COLLTRANS_TEST",
                },
            }

            plan["remaps"][0]["new_internal_name"] = "dep/Recovered_B"
            plan_path.write_text(
                json.dumps(plan, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            clean["compile_transport"]["collision_plan_sha256"] = (
                hashlib.sha256(plan_path.read_bytes()).hexdigest()
            )

            with patch(
                "spk_recovery.release_verify.build_recovery_release_manifest",
                return_value=release.copy(),
            ):
                report = verify_recovery_release(
                    release,
                    {},
                    {},
                    {},
                    {},
                    recovered,
                    clean,
                    {},
                    private_collision_plan_path=plan_path,
                )

            self.assertFalse(report["verified"])
            failed = {
                row["name"]
                for row in report["checks"]
                if row["required"] and not row["passed"]
            }
            self.assertEqual(
                failed,
                {"collision_private_mapping_sha256"},
            )

    def test_collision_private_plan_byte_drift_is_rejected(self):
        release = _release()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan_path = root / "collision-plan.json"
            plan = {
                "schema_version": 1,
                "kind": "class_package_namespace_collision_plan",
                "plan_id": "JNSPLAN_TEST",
                "collision_report_id": "JNSCOLLISION_TEST",
                "readable_jar_sha256": "b" * 64,
                "identifiers_included": True,
            }
            plan_path.write_text(
                json.dumps(plan, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            accepted_sha = hashlib.sha256(
                plan_path.read_bytes()
            ).hexdigest()

            recovered = {
                "collision_plan_id": "JNSPLAN_TEST",
                "collision_report_id": "JNSCOLLISION_TEST",
                "collision_transform_id": "COLLTRANS_TEST",
                "base_readable_jar_sha256": "b" * 64,
            }
            clean = {
                "readable_jar_sha256": "b" * 64,
                "compile_transport": {
                    "mode": "collision_derived_remap",
                    "collision_plan_id": "JNSPLAN_TEST",
                    "collision_plan_sha256": accepted_sha,
                    "collision_report_id": "JNSCOLLISION_TEST",
                    "collision_transform_id": "COLLTRANS_TEST",
                },
            }

            plan["tamper"] = True
            plan_path.write_text(
                json.dumps(plan, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            with patch(
                "spk_recovery.release_verify.build_recovery_release_manifest",
                return_value=release.copy(),
            ):
                report = verify_recovery_release(
                    release,
                    {},
                    {},
                    {},
                    {},
                    recovered,
                    clean,
                    {},
                    private_collision_plan_path=plan_path,
                )

            self.assertFalse(report["verified"])
            failed = {
                row["name"]
                for row in report["checks"]
                if row["required"] and not row["passed"]
            }
            self.assertEqual(
                failed,
                {"collision_private_plan_sha256"},
            )

    def test_collision_release_requires_private_plan(self):
        release = _release()
        recovered = {
            "collision_plan_id": "JNSPLAN_TEST",
            "collision_report_id": "JNSCOLLISION_TEST",
            "collision_transform_id": "COLLTRANS_TEST",
            "base_readable_jar_sha256": "b" * 64,
        }
        clean = {
            "readable_jar_sha256": "b" * 64,
            "compile_transport": {
                "mode": "collision_derived_remap",
                "collision_plan_id": "JNSPLAN_TEST",
                "collision_plan_sha256": "a" * 64,
                "collision_report_id": "JNSCOLLISION_TEST",
                "collision_transform_id": "COLLTRANS_TEST",
            },
        }

        with patch(
            "spk_recovery.release_verify.build_recovery_release_manifest",
            return_value=release.copy(),
        ):
            report = verify_recovery_release(
                release,
                {},
                {},
                {},
                {},
                recovered,
                clean,
                {},
            )

        self.assertFalse(report["verified"])
        failed = {
            row["name"]
            for row in report["checks"]
            if row["required"] and not row["passed"]
        }
        self.assertEqual(
            failed,
            {"collision_private_plan_supplied"},
        )

    def test_optional_jar_pins_are_verified(self):
        release = _release()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            authority = root / "client.jar"
            readable = root / "readable.jar"
            authority.write_bytes(b"authority")
            readable.write_bytes(b"readable")

            with patch(
                "spk_recovery.release_verify.build_recovery_release_manifest",
                return_value=release.copy(),
            ):
                report = verify_recovery_release(
                    release,
                    {},
                    {},
                    {},
                    {},
                    {},
                    {},
                    {},
                    authority_jar=authority,
                    readable_jar=readable,
                )
            self.assertTrue(report["verified"])
            self.assertEqual(report["required_check_count"], 3)

            readable.write_bytes(b"drift")
            with patch(
                "spk_recovery.release_verify.build_recovery_release_manifest",
                return_value=release.copy(),
            ):
                drift = verify_recovery_release(
                    release,
                    {},
                    {},
                    {},
                    {},
                    {},
                    {},
                    {},
                    authority_jar=authority,
                    readable_jar=readable,
                )
            self.assertFalse(drift["verified"])
            failed = {
                row["name"]
                for row in drift["checks"]
                if not row["passed"]
            }
            self.assertEqual(failed, {"readable_jar_sha256"})

    def test_official_first_private_authority_passes(self):
        release = _release()
        with tempfile.TemporaryDirectory() as td:
            fx = _official_first_fixture(Path(td))
            with patch(
                "spk_recovery.release_verify.build_recovery_release_manifest",
                return_value=release.copy(),
            ):
                report = verify_recovery_release(
                    release,
                    {},
                    {},
                    {},
                    {},
                    {},
                    fx["clean"],
                    {},
                    official_overlay_manifest_path=fx["overlay_path"],
                    official_overlay_source_root=fx["overlay_root"],
                    private_dependency_replacement_plan_path=fx[
                        "replacement_path"
                    ],
                    private_dependency_reverse_plan_path=fx[
                        "reverse_path"
                    ],
                    official_artifacts=[fx["official"]],
                )

            self.assertTrue(report["verified"])
            names = {row["name"] for row in report["checks"]}
            self.assertIn("official_overlay_source_tree_sha256", names)
            self.assertIn(
                "official_private_reverse_bytecode_restore_ready",
                names,
            )
            self.assertIn("official_artifact_file_sha256", names)

    def test_official_first_requires_explicit_private_inputs(self):
        release = _release()
        with tempfile.TemporaryDirectory() as td:
            fx = _official_first_fixture(Path(td))
            with patch(
                "spk_recovery.release_verify.build_recovery_release_manifest",
                return_value=release.copy(),
            ):
                report = verify_recovery_release(
                    release,
                    {},
                    {},
                    {},
                    {},
                    {},
                    fx["clean"],
                    {},
                )

            self.assertFalse(report["verified"])
            failed = {
                row["name"]
                for row in report["checks"]
                if row["required"] and not row["passed"]
            }
            self.assertEqual(
                failed,
                {
                    "official_overlay_manifest_supplied",
                    "official_overlay_source_root_supplied",
                    "official_private_replacement_plan_supplied",
                    "official_private_reverse_plan_supplied",
                    "official_artifacts_supplied",
                },
            )

    def test_official_first_artifact_byte_drift_is_rejected(self):
        release = _release()
        with tempfile.TemporaryDirectory() as td:
            fx = _official_first_fixture(Path(td))
            fx["official"].write_bytes(b"drifted dependency")
            with patch(
                "spk_recovery.release_verify.build_recovery_release_manifest",
                return_value=release.copy(),
            ):
                report = verify_recovery_release(
                    release,
                    {},
                    {},
                    {},
                    {},
                    {},
                    fx["clean"],
                    {},
                    official_overlay_manifest_path=fx["overlay_path"],
                    official_overlay_source_root=fx["overlay_root"],
                    private_dependency_replacement_plan_path=fx[
                        "replacement_path"
                    ],
                    private_dependency_reverse_plan_path=fx[
                        "reverse_path"
                    ],
                    official_artifacts=[fx["official"]],
                )

            self.assertFalse(report["verified"])
            failed = {
                row["name"]
                for row in report["checks"]
                if row["required"] and not row["passed"]
            }
            self.assertEqual(
                failed,
                {"official_artifact_file_sha256"},
            )

    def test_official_first_inputs_rejected_for_legacy_transport(self):
        release = _release()
        with tempfile.TemporaryDirectory() as td:
            fx = _official_first_fixture(Path(td))
            clean = {
                "compile_transport": {
                    "mode": "legacy",
                }
            }
            with patch(
                "spk_recovery.release_verify.build_recovery_release_manifest",
                return_value=release.copy(),
            ):
                with self.assertRaisesRegex(
                    RecoveryReleaseVerificationError,
                    "require official_first_restored",
                ):
                    verify_recovery_release(
                        release,
                        {},
                        {},
                        {},
                        {},
                        {},
                        clean,
                        {},
                        official_overlay_manifest_path=fx[
                            "overlay_path"
                        ],
                    )



if __name__ == "__main__":
    unittest.main()
