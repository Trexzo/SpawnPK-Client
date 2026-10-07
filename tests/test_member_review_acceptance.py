from __future__ import annotations

import copy
import unittest

from spk_recovery.member_review_acceptance import (
    ReviewedMemberIdentityError,
    accept_reviewed_member_identities,
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
                    }
                ],
                "semantic_provenance": [],
            }
        ],
        "unresolved": [
            {
                "old_build_id": "v308",
                "new_build_id": "v309",
                "kind": "member_identity_review",
                "member_kind": "field",
                "source": "member_identity_candidates",
                "candidate": {
                    "relationship_id": "MEMREL_TEST_1",
                    "kind": "field",
                    "old_owner": "rs/a.class",
                    "new_owner": "rs/b.class",
                    "old": {
                        "name": "x",
                        "descriptor": "I",
                        "access": 2,
                    },
                    "new": {
                        "name": "y",
                        "descriptor": "I",
                        "access": 2,
                    },
                    "strategy": "structural_unique",
                    "score": 0.995,
                },
            }
        ],
    }


def _old_index():
    return {
        "sha256": "1" * 64,
        "classes": {
            "rs/a.class": {
                "fields": [
                    {
                        "name": "x",
                        "descriptor": "I",
                        "access": 2,
                    }
                ]
            }
        },
    }


def _new_index():
    return {
        "sha256": "2" * 64,
        "classes": {
            "rs/b.class": {
                "fields": [
                    {
                        "name": "y",
                        "descriptor": "I",
                        "access": 2,
                    }
                ]
            }
        },
    }


def _spec():
    return {
        "schema_version": 1,
        "kind": "reviewed_member_identity_acceptance_spec",
        "old_build_id": "v308",
        "new_build_id": "v309",
        "old_sha256": "1" * 64,
        "new_sha256": "2" * 64,
        "note": "Explicitly reviewed against independent field evidence.",
        "evidence": [
            "research/field-review.json#MEMREL_TEST_1",
        ],
        "relationship_ids": ["MEMREL_TEST_1"],
    }


class ReviewedMemberIdentityTests(unittest.TestCase):
    def test_accepts_exact_existing_unresolved_field_relation(self):
        original = _member_lineage()
        snapshot = copy.deepcopy(original)

        out, summary = accept_reviewed_member_identities(
            _class_lineage(),
            original,
            _old_index(),
            _new_index(),
            _spec(),
        )

        self.assertEqual(original, snapshot)
        self.assertEqual(summary["accepted_reviewed_fields"], 1)
        self.assertEqual(summary["unresolved_removed"], 1)
        self.assertEqual(out["unresolved"], [])
        relation = out["members"][0]["lineage"][-1]
        self.assertEqual(relation["build_id"], "v309")
        self.assertEqual(relation["owner_internal_name"], "rs/b")
        self.assertEqual(relation["name"], "y")
        self.assertEqual(relation["descriptor"], "I")
        self.assertEqual(relation["relation"], "MANUAL")
        self.assertEqual(
            relation["provenance"][0]["source"],
            "MEMREL_TEST_1",
        )

    def test_relationship_must_already_be_unresolved(self):
        spec = _spec()
        spec["relationship_ids"] = ["MEMREL_OTHER"]
        with self.assertRaises(ReviewedMemberIdentityError):
            accept_reviewed_member_identities(
                _class_lineage(),
                _member_lineage(),
                _old_index(),
                _new_index(),
                spec,
            )

    def test_sha_binding_drift_is_refused(self):
        spec = _spec()
        spec["new_sha256"] = "9" * 64
        with self.assertRaises(ReviewedMemberIdentityError):
            accept_reviewed_member_identities(
                _class_lineage(),
                _member_lineage(),
                _old_index(),
                _new_index(),
                spec,
            )

    def test_target_owner_must_share_canonical_class(self):
        lineage = _member_lineage()
        lineage["unresolved"][0]["candidate"]["new_owner"] = "rs/z.class"
        with self.assertRaises(ReviewedMemberIdentityError):
            accept_reviewed_member_identities(
                _class_lineage(),
                lineage,
                _old_index(),
                _new_index(),
                _spec(),
            )


if __name__ == "__main__":
    unittest.main()
