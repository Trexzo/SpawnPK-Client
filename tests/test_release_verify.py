from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.release_verify import verify_recovery_release


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


class ReleaseVerificationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
