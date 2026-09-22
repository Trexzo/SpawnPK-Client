from __future__ import annotations

import copy
import unittest

from spk_recovery.update_finalize import (
    UpdateFinalizeError,
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
                "semantic_name": "ExampleController",
                "semantic_status": "ACCEPTED",
                "semantic_confidence": 0.99,
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
                "semantic_name": "value",
                "semantic_status": "ACCEPTED",
                "semantic_confidence": 0.97,
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
            },
            {
                "member_id": "CLIENT_METHOD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "method",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/a",
                        "name": "a",
                        "descriptor": "()V",
                        "access": 2,
                        "code_length": 5,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    },
                    {
                        "build_id": "v309",
                        "owner_internal_name": "rs/b",
                        "name": "c",
                        "descriptor": "()V",
                        "access": 2,
                        "code_length": 5,
                        "relation": "STRUCTURAL",
                        "confidence": 0.99,
                        "provenance": [],
                    },
                ],
                "semantic_provenance": [],
            },
        ],
        "unresolved": [],
    }


def _index():
    return {
        "sha256": "2" * 64,
        "summary": {
            "class_parse_error_count": 0,
        },
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
                    },
                    {
                        "name": "c",
                        "descriptor": "()V",
                        "access": 2,
                        "code_length": 5,
                    },
                ],
            }
        },
    }


def _intake():
    return {
        "schema_version": 1,
        "kind": "update_intake_report",
        "migration_id": "MIGRATION_" + "A" * 20,
        "new_build_id": "v309",
        "new_sha256": "2" * 64,
        "scope_prefix": "rs/",
    }


class UpdateFinalizeTests(unittest.TestCase):
    def test_complete_target_coverage_is_ready(self):
        report = build_authority_candidate_report(
            _class_lineage(),
            _member_lineage(),
            _index(),
            _intake(),
            build_id="v309",
        )

        self.assertTrue(report["ready_for_authority"])
        self.assertEqual(report["summary"]["class_coverage_percent"], 100.0)
        self.assertEqual(report["summary"]["member_coverage_percent"], 100.0)
        self.assertEqual(report["summary"]["target_classes"], 1)
        self.assertEqual(report["summary"]["target_fields"], 1)
        self.assertEqual(report["summary"]["target_methods"], 1)
        self.assertEqual(
            report["summary"]["accepted_semantic_classes_carried"],
            1,
        )
        self.assertEqual(
            report["summary"]["accepted_semantic_members_carried"],
            1,
        )
        self.assertEqual(report["blockers"], [])

    def test_missing_target_member_blocks_finalization(self):
        members = _member_lineage()
        members["members"][1]["lineage"] = [
            members["members"][1]["lineage"][0]
        ]
        members["unresolved"].append(
            {
                "old_build_id": "v308",
                "new_build_id": "v309",
                "kind": "member_unmatched_new",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "member_kind": "method",
                "candidate": {
                    "name": "c",
                    "descriptor": "()V",
                },
            }
        )

        report = build_authority_candidate_report(
            _class_lineage(),
            members,
            _index(),
            _intake(),
            build_id="v309",
        )

        self.assertFalse(report["ready_for_authority"])
        self.assertEqual(len(report["missing_members"]), 1)
        kinds = {row["kind"] for row in report["blockers"]}
        self.assertIn("missing_canonical_members", kinds)
        self.assertIn("member_unresolved_blockers", kinds)

    def test_old_removal_items_are_informational_only(self):
        classes = _class_lineage()
        members = _member_lineage()
        classes["unresolved"].append(
            {
                "old_build_id": "v308",
                "new_build_id": "v309",
                "kind": "unmatched_old",
                "candidate": "rs/removed.class",
            }
        )
        members["unresolved"].append(
            {
                "old_build_id": "v308",
                "new_build_id": "v309",
                "kind": "member_unmatched_old",
                "candidate": {
                    "name": "removed",
                    "descriptor": "()V",
                },
            }
        )

        report = build_authority_candidate_report(
            classes,
            members,
            _index(),
            _intake(),
            build_id="v309",
        )

        self.assertTrue(report["ready_for_authority"])
        self.assertEqual(
            report["summary"]["informational_removed_class_items"],
            1,
        )
        self.assertEqual(
            report["summary"]["informational_removed_member_items"],
            1,
        )

    def test_exact_target_sha_is_required(self):
        index = _index()
        index["sha256"] = "9" * 64
        with self.assertRaises(UpdateFinalizeError):
            build_authority_candidate_report(
                _class_lineage(),
                _member_lineage(),
                index,
                _intake(),
                build_id="v309",
            )

    def test_report_id_is_deterministic(self):
        a = build_authority_candidate_report(
            _class_lineage(),
            _member_lineage(),
            _index(),
            _intake(),
            build_id="v309",
        )
        b = build_authority_candidate_report(
            _class_lineage(),
            _member_lineage(),
            _index(),
            _intake(),
            build_id="v309",
        )
        self.assertEqual(a["report_id"], b["report_id"])


    def test_member_identity_review_blocks_authority(self):
        members = _member_lineage()
        members["unresolved"].append(
            {
                "old_build_id": "v308",
                "new_build_id": "v309",
                "kind": "member_identity_review",
                "member_kind": "field",
                "candidate": {
                    "old": {
                        "name": "bI",
                        "descriptor": "I",
                    },
                    "new": {
                        "name": "bI",
                        "descriptor": "I",
                    },
                    "strategy": "stable_symbol",
                },
                "source": "member_identity_candidates",
                "reason": (
                    "field relationship requires review because the enclosing "
                    "class changed and there is no exact matched-method "
                    "access-position evidence"
                ),
            }
        )

        report = build_authority_candidate_report(
            _class_lineage(),
            members,
            _index(),
            _intake(),
            build_id="v309",
        )

        self.assertFalse(report["ready_for_authority"])
        self.assertEqual(
            report["summary"]["blocking_unresolved_members"],
            1,
        )
        self.assertEqual(
            report["blocking_member_unresolved"][0]["kind"],
            "member_identity_review",
        )
        self.assertIn(
            "member_unresolved_blockers",
            {row["kind"] for row in report["blockers"]},
        )


if __name__ == "__main__":
    unittest.main()
