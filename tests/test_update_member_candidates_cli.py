import unittest

from spk_recovery.update_member_candidates_cli import (
    UpdateMemberCandidatesError,
    build_update_member_candidates,
)


class UpdateMemberCandidatesCliTests(unittest.TestCase):
    def test_rejects_migration_id_drift(self):
        intake = {
            "schema_version": 1,
            "kind": "update_intake_report",
            "migration_id": "MIGRATION_TEST",
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "scope_prefix": "rs/",
        }
        with self.assertRaises(UpdateMemberCandidatesError):
            build_update_member_candidates(
                {"sha256": "1" * 64},
                {"sha256": "2" * 64},
                intake,
                old_build_id="v308",
                new_build_id="v309",
                expected_migration_id="MIGRATION_OTHER",
            )


if __name__ == "__main__":
    unittest.main()
