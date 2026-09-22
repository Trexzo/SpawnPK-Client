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
