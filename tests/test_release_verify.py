from pathlib import Path
import hashlib
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

    def test_collision_release_requires_matching_private_plan(self):
        release = _release()
        recovered = {
            "collision_plan_id": "JNSPLAN_123",
            "collision_report_id": "JNSCOLLISION_456",
            "collision_transform_id": "JNSTRANSFORM_789",
            "base_readable_jar_sha256": "a" * 64,
        }

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan = root / "private-plan.json"
            plan.write_text(
                (
                    "{\n"
                    '  "schema_version": 1,\n'
                    '  "kind": "class_package_namespace_collision_plan",\n'
                    '  "plan_id": "JNSPLAN_123",\n'
                    '  "collision_report_id": "JNSCOLLISION_456",\n'
                    '  "readable_jar_sha256": "' + ("a" * 64) + '"\n'
                    "}\n"
                ),
                encoding="utf-8",
            )
            sha = hashlib.sha256(plan.read_bytes()).hexdigest()
            clean = {
                "compile_transport": {
                    "collision_plan_id": "JNSPLAN_123",
                    "collision_report_id": "JNSCOLLISION_456",
                    "collision_transform_id": "JNSTRANSFORM_789",
                    "private_collision_plan_sha256": sha,
                }
            }

            with patch(
                "spk_recovery.release_verify.build_recovery_release_manifest",
                return_value=release.copy(),
            ):
                missing = verify_recovery_release(
                    release, {}, {}, {}, {}, recovered, clean, {}
                )
                matched = verify_recovery_release(
                    release,
                    {},
                    {},
                    {},
                    {},
                    recovered,
                    clean,
                    {},
                    private_collision_plan_path=plan,
                )

            self.assertFalse(missing["verified"])
            self.assertTrue(matched["verified"])
            names = {
                row["name"]: row["passed"]
                for row in matched["checks"]
            }
            self.assertTrue(names["private_collision_plan_sha256"])
            self.assertTrue(names["clean_collision_transform_id"])

            plan.write_text(
                plan.read_text(encoding="utf-8").replace(
                    "JNSPLAN_123",
                    "JNSPLAN_WRONG",
                ),
                encoding="utf-8",
            )
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
                    recovered,
                    clean,
                    {},
                    private_collision_plan_path=plan,
                )
            self.assertFalse(drift["verified"])
            failed = {
                row["name"]
                for row in drift["checks"]
                if not row["passed"]
            }
            self.assertIn("private_collision_plan_id", failed)
            self.assertIn("private_collision_plan_sha256", failed)

    def test_legacy_release_rejects_unexpected_private_collision_plan(self):
        release = _release()
        with tempfile.TemporaryDirectory() as td:
            plan = Path(td) / "plan.json"
            plan.write_text("{}\n", encoding="utf-8")
            with patch(
                "spk_recovery.release_verify.build_recovery_release_manifest",
                return_value=release.copy(),
            ):
                with self.assertRaisesRegex(
                    Exception,
                    "non-collision-derived release",
                ):
                    verify_recovery_release(
                        release,
                        {},
                        {},
                        {},
                        {},
                        {},
                        {},
                        {},
                        private_collision_plan_path=plan,
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
