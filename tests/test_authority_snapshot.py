from __future__ import annotations

import copy
import unittest

from spk_recovery.authority_snapshot import (
    AuthoritySnapshotError,
    promote_authority_snapshot,
)
from spk_recovery.update_finalize import (
    build_authority_candidate_report,
)


def _class_lineage():
    return {
        "schema_version": 1,
        "namespace": "spawnpk-client",
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": "v308",
        "builds": [
            {
                "build_id": "v308",
                "build_number": 308,
                "sha256": "1" * 64,
                "source_name": "old.jar",
                "authority": "EXACT_CURRENT_CLIENT",
            },
            {
                "build_id": "v309",
                "build_number": 309,
                "sha256": "2" * 64,
                "source_name": "new.jar",
                "authority": "CROSS_BUILD",
            },
        ],
        "classes": [
            {
                "logical_id": "CLIENT_CLASS_000001",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/a",
                        "entry_path": "rs/a.class",
                        "entry_sha256": "a" * 64,
                        "structural_sha256": "b" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    },
                    {
                        "build_id": "v309",
                        "internal_name": "rs/b",
                        "entry_path": "rs/b.class",
                        "entry_sha256": "c" * 64,
                        "structural_sha256": "b" * 64,
                        "relation": "STRUCTURAL",
                        "confidence": 0.995,
                        "provenance": [],
                    },
                ],
                "semantic_provenance": [],
            }
        ],
        "unresolved": [],
    }


def _member_lineage():
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": "1" * 64,
        "members": [
            {
                "member_id": "CLIENT_FIELD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "field",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/a",
                        "name": "x",
                        "descriptor": "I",
                        "access": 2,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    },
                    {
                        "build_id": "v309",
                        "owner_internal_name": "rs/b",
                        "name": "y",
                        "descriptor": "I",
                        "access": 2,
                        "relation": "STRUCTURAL",
                        "confidence": 0.99,
                        "provenance": [],
                    },
                ],
                "semantic_provenance": [],
            }
        ],
        "unresolved": [],
    }


def _index():
    return {
        "sha256": "2" * 64,
        "summary": {"class_parse_error_count": 0},
        "classes": {
            "rs/b.class": {
                "internal_name": "rs/b",
                "fields": [
                    {
                        "name": "y",
                        "descriptor": "I",
                        "access": 2,
                    }
                ],
                "methods": [
                    {
                        "name": "<init>",
                        "descriptor": "()V",
                        "access": 1,
                        "code_length": 4,
                    }
                ],
            }
        },
    }


def _intake():
    return {
        "schema_version": 1,
        "kind": "update_intake_report",
        "migration_id": "MIGRATION_" + "A" * 20,
        "old_build_id": "v308",
        "new_build_id": "v309",
        "old_sha256": "1" * 64,
        "new_sha256": "2" * 64,
        "scope_prefix": "rs/",
    }


def _candidate():
    return build_authority_candidate_report(
        _class_lineage(),
        _member_lineage(),
        _index(),
        _intake(),
        build_id="v309",
    )


class AuthoritySnapshotTests(unittest.TestCase):
    def test_complete_candidate_promotes_deterministically(self):
        a = promote_authority_snapshot(
            _class_lineage(),
            _member_lineage(),
            _index(),
            _intake(),
            _candidate(),
            build_id="v309",
        )
        b = promote_authority_snapshot(
            _class_lineage(),
            _member_lineage(),
            _index(),
            _intake(),
            _candidate(),
            build_id="v309",
        )

        self.assertEqual(a, b)
        self.assertTrue(a["authority_id"].startswith("AUTHORITY_"))
        self.assertEqual(a["state"], "EXACT_CURRENT_CLIENT")
        self.assertEqual(a["build_id"], "v309")
        self.assertEqual(a["build_number"], 309)
        self.assertEqual(a["sha256"], "2" * 64)
        self.assertEqual(a["previous_build_id"], "v308")
        self.assertEqual(a["previous_sha256"], "1" * 64)

    def test_tampered_candidate_report_is_rejected(self):
        candidate = _candidate()
        candidate["summary"]["target_classes"] = 999

        with self.assertRaises(AuthoritySnapshotError):
            promote_authority_snapshot(
                _class_lineage(),
                _member_lineage(),
                _index(),
                _intake(),
                candidate,
                build_id="v309",
            )

    def test_blocked_candidate_cannot_promote(self):
        members = _member_lineage()
        members["members"][0]["lineage"] = [
            members["members"][0]["lineage"][0]
        ]
        members["unresolved"].append(
            {
                "old_build_id": "v308",
                "new_build_id": "v309",
                "kind": "member_unmatched_new",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "member_kind": "field",
                "candidate": {
                    "name": "y",
                    "descriptor": "I",
                },
            }
        )
        candidate = build_authority_candidate_report(
            _class_lineage(),
            members,
            _index(),
            _intake(),
            build_id="v309",
        )
        self.assertFalse(candidate["ready_for_authority"])

        with self.assertRaises(AuthoritySnapshotError):
            promote_authority_snapshot(
                _class_lineage(),
                members,
                _index(),
                _intake(),
                candidate,
                build_id="v309",
            )


if __name__ == "__main__":
    unittest.main()
