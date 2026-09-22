from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.field_relationship_audit import (
    audit_field_relationships_by_exact_positions,
    audit_member_identity_candidate_set,
    reconcile_field_relationships_by_exact_positions,
    reconcile_member_identity_candidate_set_by_exact_positions,
)


def _profile(owner, fields, methods):
    return {
        "internal_name": owner,
        "fields": fields,
        "methods": methods,
    }


def _member_record():
    return {
        "old_owner": "rs/example.class",
        "new_owner": "rs/example.class",
        "methods": {
            "relationships": [
                {
                    "relationship_id": "M1",
                    "old": {
                        "name": "a",
                        "descriptor": "()V",
                    },
                    "new": {
                        "name": "a",
                        "descriptor": "()V",
                    },
                }
            ]
        },
        "fields": {
            "relationships": [
                {
                    "relationship_id": "F_STABLE",
                    "strategy": "stable_symbol",
                    "old": {
                        "name": "bI",
                        "descriptor": "I",
                    },
                    "new": {
                        "name": "bI",
                        "descriptor": "I",
                    },
                }
            ]
        },
    }


class FieldRelationshipAuditTests(unittest.TestCase):
    def test_detects_stable_symbol_shift_conflict(self):
        old = _profile(
            "rs/example",
            [
                {"name": "bG", "descriptor": "I", "access": 9},
                {"name": "bH", "descriptor": "I", "access": 9},
                {"name": "bI", "descriptor": "I", "access": 9},
            ],
            [
                {
                    "name": "a",
                    "descriptor": "()V",
                    "field_accesses": [
                        {
                            "owner": "rs/example",
                            "name": "bG",
                            "descriptor": "I",
                            "operation": "getstatic",
                            "offset": 0,
                        },
                        {
                            "owner": "rs/example",
                            "name": "bI",
                            "descriptor": "I",
                            "operation": "getstatic",
                            "offset": 3,
                        },
                        {
                            "owner": "rs/example",
                            "name": "bI",
                            "descriptor": "I",
                            "operation": "putstatic",
                            "offset": 12,
                        },
                    ],
                }
            ],
        )
        new = _profile(
            "rs/example",
            [
                {"name": "bI", "descriptor": "I", "access": 9},
                {"name": "bJ", "descriptor": "I", "access": 9},
                {"name": "bK", "descriptor": "I", "access": 9},
            ],
            [
                {
                    "name": "a",
                    "descriptor": "()V",
                    "field_accesses": [
                        {
                            "owner": "rs/example",
                            "name": "bI",
                            "descriptor": "I",
                            "operation": "getstatic",
                            "offset": 0,
                        },
                        {
                            "owner": "rs/example",
                            "name": "bK",
                            "descriptor": "I",
                            "operation": "getstatic",
                            "offset": 3,
                        },
                        {
                            "owner": "rs/example",
                            "name": "bK",
                            "descriptor": "I",
                            "operation": "putstatic",
                            "offset": 12,
                        },
                    ],
                }
            ],
        )

        out = audit_field_relationships_by_exact_positions(
            old,
            new,
            _member_record(),
            old_type_aliases={},
            new_type_aliases={},
            min_observations=2,
        )

        self.assertEqual(out["conflict_count"], 1)
        conflict = out["conflicts"][0]
        self.assertEqual(
            conflict["relationship_id"],
            "F_STABLE",
        )
        self.assertEqual(
            conflict["current_new"]["name"],
            "bI",
        )
        self.assertEqual(
            conflict["exact_context_new"]["name"],
            "bK",
        )

    def test_does_not_flag_when_current_relation_agrees(self):
        record = _member_record()
        record["fields"]["relationships"][0]["new"]["name"] = "bK"

        old = _profile(
            "rs/example",
            [{"name": "bI", "descriptor": "I", "access": 9}],
            [{
                "name": "a",
                "descriptor": "()V",
                "field_accesses": [
                    {
                        "owner": "rs/example",
                        "name": "bI",
                        "descriptor": "I",
                        "operation": "getstatic",
                        "offset": 3,
                    },
                    {
                        "owner": "rs/example",
                        "name": "bI",
                        "descriptor": "I",
                        "operation": "putstatic",
                        "offset": 12,
                    },
                ],
            }],
        )
        new = _profile(
            "rs/example",
            [{"name": "bK", "descriptor": "I", "access": 9}],
            [{
                "name": "a",
                "descriptor": "()V",
                "field_accesses": [
                    {
                        "owner": "rs/example",
                        "name": "bK",
                        "descriptor": "I",
                        "operation": "getstatic",
                        "offset": 3,
                    },
                    {
                        "owner": "rs/example",
                        "name": "bK",
                        "descriptor": "I",
                        "operation": "putstatic",
                        "offset": 12,
                    },
                ],
            }],
        )

        out = audit_field_relationships_by_exact_positions(
            old,
            new,
            record,
            old_type_aliases={},
            new_type_aliases={},
            min_observations=2,
        )
        self.assertEqual(out["conflict_count"], 0)
        self.assertEqual(out["exact_position_matches"], 1)




    def test_candidate_set_reconciliation_recomputes_field_totals(self):
        record = _member_record()
        record["fields"]["summary"] = {
            "old_count": 2,
            "new_count": 2,
            "matched": 1,
            "unmatched_old": 1,
            "unmatched_new": 1,
        }
        record["fields"]["unmatched_old"] = [
            {"name": "bG", "descriptor": "I", "access": 9},
        ]
        record["fields"]["unmatched_new"] = [
            {"name": "bK", "descriptor": "I", "access": 9},
        ]
        candidates = {
            "schema_version": 1,
            "kind": "member_identity_candidates",
            "canonical": False,
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "summary": {
                "method_matched": 1,
                "field_old": 2,
                "field_new": 2,
                "field_matched": 1,
            },
            "classes": [record],
            "skipped_classes": [],
        }
        audit_set = {
            "schema_version": 1,
            "kind": "field_relationship_position_audit_set",
            "canonical": False,
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "min_observations": 2,
            "exact_position_matches": 2,
            "conflict_count": 1,
            "classes": [
                {
                    "schema_version": 1,
                    "kind": "field_relationship_position_audit",
                    "canonical": False,
                    "old_owner": "rs/example.class",
                    "new_owner": "rs/example.class",
                    "matches": [
                        {
                            "old": {"name": "bG", "descriptor": "I"},
                            "new": {"name": "bI", "descriptor": "I"},
                            "score": 0.9995,
                            "observations": 2,
                        },
                        {
                            "old": {"name": "bI", "descriptor": "I"},
                            "new": {"name": "bK", "descriptor": "I"},
                            "score": 0.9995,
                            "observations": 5,
                        },
                    ],
                    "conflicts": [],
                }
            ],
        }

        out = (
            reconcile_member_identity_candidate_set_by_exact_positions(
                candidates,
                audit_set,
            )
        )
        self.assertEqual(
            out["kind"],
            "reconciled_member_identity_candidates",
        )
        self.assertEqual(out["summary"]["field_matched"], 2)
        self.assertEqual(out["summary"]["field_unmatched_old"], 0)
        self.assertEqual(out["summary"]["field_unmatched_new"], 0)
        self.assertEqual(out["summary"]["field_coverage"], 1.0)
        self.assertEqual(
            out["reconciliation"]["relationships_dropped"],
            1,
        )
        self.assertEqual(
            out["reconciliation"]["relationships_added"],
            2,
        )

    @patch(
        "spk_recovery.field_relationship_audit.sha256_file"
    )
    @patch(
        "spk_recovery.field_relationship_audit.profile_jar_class"
    )
    def test_candidate_set_audit_binds_hashes_and_profiles(
        self,
        profile,
        sha,
    ):
        sha.side_effect = ["1" * 64, "2" * 64]

        old_profile = _profile(
            "rs/example",
            [{"name": "bI", "descriptor": "I", "access": 9}],
            [{
                "name": "a",
                "descriptor": "()V",
                "field_accesses": [
                    {
                        "owner": "rs/example",
                        "name": "bI",
                        "descriptor": "I",
                        "operation": "getstatic",
                        "offset": 3,
                    },
                    {
                        "owner": "rs/example",
                        "name": "bI",
                        "descriptor": "I",
                        "operation": "putstatic",
                        "offset": 12,
                    },
                ],
            }],
        )
        new_profile = _profile(
            "rs/example",
            [{"name": "bK", "descriptor": "I", "access": 9}],
            [{
                "name": "a",
                "descriptor": "()V",
                "field_accesses": [
                    {
                        "owner": "rs/example",
                        "name": "bK",
                        "descriptor": "I",
                        "operation": "getstatic",
                        "offset": 3,
                    },
                    {
                        "owner": "rs/example",
                        "name": "bK",
                        "descriptor": "I",
                        "operation": "putstatic",
                        "offset": 12,
                    },
                ],
            }],
        )
        profile.side_effect = [old_profile, new_profile]

        record = _member_record()
        candidates = {
            "schema_version": 1,
            "kind": "member_identity_candidates",
            "canonical": False,
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "classes": [record],
        }

        out = audit_member_identity_candidate_set(
            Path("old.jar"),
            Path("new.jar"),
            candidates,
            min_observations=2,
        )
        self.assertEqual(out["exact_position_matches"], 1)
        self.assertEqual(out["conflict_count"], 1)
        self.assertEqual(out["class_audits"], 1)

    def test_reconciliation_drops_conflict_and_overlays_exact(self):
        record = _member_record()
        record["fields"]["unmatched_old"] = [
            {"name": "bG", "descriptor": "I", "access": 9},
        ]
        record["fields"]["unmatched_new"] = [
            {"name": "bK", "descriptor": "I", "access": 9},
        ]
        audit = {
            "schema_version": 1,
            "kind": "field_relationship_position_audit",
            "canonical": False,
            "matches": [
                {
                    "old": {"name": "bG", "descriptor": "I"},
                    "new": {"name": "bI", "descriptor": "I"},
                    "score": 0.9995,
                    "observations": 2,
                },
                {
                    "old": {"name": "bI", "descriptor": "I"},
                    "new": {"name": "bK", "descriptor": "I"},
                    "score": 0.9995,
                    "observations": 5,
                },
            ],
        }

        out = reconcile_field_relationships_by_exact_positions(
            record,
            audit,
        )

        self.assertEqual(
            out["summary"]["dropped_conflicting"],
            1,
        )
        self.assertEqual(
            out["summary"]["exact_position_added"],
            2,
        )
        self.assertEqual(
            out["summary"]["unmatched_old"],
            0,
        )
        self.assertEqual(
            out["summary"]["unmatched_new"],
            0,
        )
        pairs = {
            (
                row["old"]["name"],
                row["new"]["name"],
            )
            for row in out["relationships"]
        }
        self.assertEqual(
            pairs,
            {("bG", "bI"), ("bI", "bK")},
        )

    def test_requires_minimum_observations(self):
        old = _profile(
            "rs/example",
            [{"name": "bI", "descriptor": "I", "access": 9}],
            [{
                "name": "a",
                "descriptor": "()V",
                "field_accesses": [{
                    "owner": "rs/example",
                    "name": "bI",
                    "descriptor": "I",
                    "operation": "getstatic",
                    "offset": 3,
                }],
            }],
        )
        new = _profile(
            "rs/example",
            [{"name": "bK", "descriptor": "I", "access": 9}],
            [{
                "name": "a",
                "descriptor": "()V",
                "field_accesses": [{
                    "owner": "rs/example",
                    "name": "bK",
                    "descriptor": "I",
                    "operation": "getstatic",
                    "offset": 3,
                }],
            }],
        )

        out = audit_field_relationships_by_exact_positions(
            old,
            new,
            _member_record(),
            old_type_aliases={},
            new_type_aliases={},
            min_observations=2,
        )
        self.assertEqual(out["exact_position_matches"], 0)
        self.assertEqual(out["conflict_count"], 0)


if __name__ == "__main__":
    unittest.main()
