from __future__ import annotations

import copy
import unittest

from spk_recovery.member_promotion import (
    NewMemberPromotionError,
    promote_new_members,
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
                "member_id": "CLIENT_FIELD_000004",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "field",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/a",
                        "name": "oldField",
                        "descriptor": "I",
                        "access": 2,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            },
            {
                "member_id": "CLIENT_METHOD_000009",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "method",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/a",
                        "name": "oldMethod",
                        "descriptor": "()V",
                        "access": 2,
                        "code_length": 3,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            },
        ],
        "unresolved": [
            {
                "old_build_id": "v308",
                "new_build_id": "v309",
                "kind": "member_unmatched_new",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "member_kind": "field",
                "candidate": {
                    "name": "newField",
                    "descriptor": "J",
                    "access": 2,
                    "code_length": None,
                },
                "source": "member_identity_candidates",
            },
            {
                "old_build_id": "v308",
                "new_build_id": "v309",
                "kind": "member_unmatched_new",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "member_kind": "method",
                "candidate": {
                    "name": "newMethod",
                    "descriptor": "(I)V",
                    "access": 1,
                    "code_length": 7,
                },
                "source": "member_identity_candidates",
            },
        ],
    }


def _index():
    return {
        "sha256": "2" * 64,
        "classes": {
            "rs/b.class": {
                "fields": [
                    {
                        "name": "newField",
                        "descriptor": "J",
                        "access": 2,
                    }
                ],
                "methods": [
                    {
                        "name": "newMethod",
                        "descriptor": "(I)V",
                        "access": 1,
                        "code_length": 7,
                    },
                    {
                        "name": "<init>",
                        "descriptor": "()V",
                        "access": 1,
                        "code_length": 5,
                    },
                ],
            }
        },
    }


def _spec():
    return {
        "schema_version": 1,
        "kind": "new_member_promotion_spec",
        "build_id": "v309",
        "authority": "RESEARCH",
        "note": "Reviewed exact v309 additions.",
        "members": [
            {
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "method",
                "name": "newMethod",
                "descriptor": "(I)V",
            },
            {
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "field",
                "name": "newField",
                "descriptor": "J",
            },
        ],
    }


class MemberPromotionTests(unittest.TestCase):
    def test_promotes_reviewed_members_with_independent_id_sequences(self):
        out, summary = promote_new_members(
            _class_lineage(),
            _member_lineage(),
            _index(),
            _spec(),
        )

        new_records = [
            row
            for row in out["members"]
            if row["member_id"] in {
                "CLIENT_FIELD_000005",
                "CLIENT_METHOD_000010",
            }
        ]
        self.assertEqual(len(new_records), 2)
        self.assertEqual(summary["promoted_new_members"], 2)
        self.assertEqual(summary["promoted_new_fields"], 1)
        self.assertEqual(summary["promoted_new_methods"], 1)
        self.assertEqual(summary["unresolved_removed"], 2)
        self.assertEqual(out["unresolved"], [])
        for record in new_records:
            self.assertEqual(record["semantic_status"], "UNKNOWN")
            self.assertIsNone(record["semantic_name"])
            self.assertEqual(record["lineage"][0]["build_id"], "v309")
            self.assertEqual(record["lineage"][0]["relation"], "MANUAL")

    def test_batch_order_is_deterministic(self):
        spec_a = _spec()
        spec_b = copy.deepcopy(spec_a)
        spec_b["members"] = list(reversed(spec_b["members"]))

        a, _ = promote_new_members(
            _class_lineage(),
            _member_lineage(),
            _index(),
            spec_a,
        )
        b, _ = promote_new_members(
            _class_lineage(),
            _member_lineage(),
            _index(),
            spec_b,
        )
        self.assertEqual(a, b)

    def test_coordinate_must_be_unmatched_new(self):
        lineage = _member_lineage()
        lineage["unresolved"] = []
        with self.assertRaises(NewMemberPromotionError):
            promote_new_members(
                _class_lineage(),
                lineage,
                _index(),
                _spec(),
            )

    def test_constructor_promotion_is_rejected(self):
        spec = _spec()
        spec["members"] = [
            {
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "method",
                "name": "<init>",
                "descriptor": "()V",
            }
        ]
        with self.assertRaises(NewMemberPromotionError):
            promote_new_members(
                _class_lineage(),
                _member_lineage(),
                _index(),
                spec,
            )

    def test_target_index_sha_is_bound_to_canonical_build(self):
        index = _index()
        index["sha256"] = "9" * 64
        with self.assertRaises(NewMemberPromotionError):
            promote_new_members(
                _class_lineage(),
                _member_lineage(),
                index,
                _spec(),
            )


if __name__ == "__main__":
    unittest.main()
