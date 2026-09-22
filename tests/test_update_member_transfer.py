from __future__ import annotations

import copy
import unittest

from spk_recovery.update_member_transfer import (
    UpdateMemberTransferError,
    transfer_member_identity_candidates,
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
                    }
                ],
                "semantic_provenance": [],
            },
            {
                "member_id": "CLIENT_METHOD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "method",
                "semantic_name": "runTask",
                "semantic_status": "ACCEPTED",
                "semantic_confidence": 0.98,
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
                    }
                ],
                "semantic_provenance": [],
            },
        ],
        "unresolved": [],
    }


def _indexes():
    old = {
        "sha256": "1" * 64,
        "classes": {
            "rs/a.class": {
                "fields": [
                    {
                        "name": "x",
                        "descriptor": "I",
                        "access": 2,
                    }
                ],
                "methods": [
                    {
                        "name": "a",
                        "descriptor": "()V",
                        "access": 2,
                        "code_length": 5,
                    }
                ],
            }
        },
    }
    new = {
        "sha256": "2" * 64,
        "classes": {
            "rs/b.class": {
                "fields": [
                    {
                        "name": "y",
                        "descriptor": "I",
                        "access": 2,
                    }
                ],
                "methods": [
                    {
                        "name": "c",
                        "descriptor": "()V",
                        "access": 2,
                        "code_length": 5,
                    }
                ],
            }
        },
    }
    return old, new


def _candidates(
    field_strategy="exact_matched_method_access_positions",
    class_strategy="structural_unique",
):
    return {
        "schema_version": 1,
        "kind": "member_identity_candidates",
        "canonical": False,
        "old_sha256": "1" * 64,
        "new_sha256": "2" * 64,
        "summary": {},
        "classes": [
            {
                "old_owner": "rs/a.class",
                "new_owner": "rs/b.class",
                "class_strategy": class_strategy,
                "class_score": 0.995,
                "fields": {
                    "relationships": [
                        {
                            "relationship_id": "MEMREL_FIELD",
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
                            "strategy": field_strategy,
                            "score": 0.97,
                            "confidence": "INFERRED_HIGH",
                            "evidence": {},
                        }
                    ],
                    "unmatched_old": [],
                    "unmatched_new": [],
                },
                "methods": {
                    "relationships": [
                        {
                            "relationship_id": "MEMREL_METHOD",
                            "kind": "method",
                            "old_owner": "rs/a.class",
                            "new_owner": "rs/b.class",
                            "old": {
                                "name": "a",
                                "descriptor": "()V",
                                "access": 2,
                                "code_length": 5,
                            },
                            "new": {
                                "name": "c",
                                "descriptor": "()V",
                                "access": 2,
                                "code_length": 5,
                            },
                            "strategy": "stable_symbol",
                            "score": 0.999,
                            "confidence": "CROSS_BUILD",
                            "evidence": {},
                        }
                    ],
                    "unmatched_old": [],
                    "unmatched_new": [],
                },
            }
        ],
        "skipped_classes": [],
    }


class UpdateMemberTransferTests(unittest.TestCase):
    def test_trusted_relations_append_to_same_stable_ids(self):
        old, new = _indexes()
        out, summary = transfer_member_identity_candidates(
            _class_lineage(),
            _member_lineage(),
            old,
            new,
            _candidates(),
            old_build_id="v308",
            new_build_id="v309",
        )

        self.assertEqual(summary["applied_member_relationships"], 2)
        self.assertEqual(summary["review_only_relationships"], 0)

        by_id = {
            row["member_id"]: row
            for row in out["members"]
        }
        field = by_id["CLIENT_FIELD_000001"]
        method = by_id["CLIENT_METHOD_000001"]

        self.assertEqual(field["semantic_name"], "value")
        self.assertEqual(field["semantic_status"], "ACCEPTED")
        self.assertEqual(field["lineage"][1]["build_id"], "v309")
        self.assertEqual(field["lineage"][1]["name"], "y")

        self.assertEqual(method["semantic_name"], "runTask")
        self.assertEqual(method["lineage"][1]["name"], "c")

    def test_weak_structural_field_relationship_is_withheld(self):
        old, new = _indexes()
        out, summary = transfer_member_identity_candidates(
            _class_lineage(),
            _member_lineage(),
            old,
            new,
            _candidates(field_strategy="structural_unique"),
            old_build_id="v308",
            new_build_id="v309",
        )

        self.assertEqual(summary["applied_member_relationships"], 1)
        self.assertEqual(summary["review_only_relationships"], 1)
        field = next(
            row
            for row in out["members"]
            if row["member_id"] == "CLIENT_FIELD_000001"
        )
        self.assertEqual(len(field["lineage"]), 1)
        self.assertTrue(
            any(
                row.get("kind") == "member_identity_review"
                and row.get("member_kind") == "field"
                for row in out["unresolved"]
            )
        )

    def test_byte_identical_class_allows_same_symbol_field(self):
        old, new = _indexes()
        new["classes"]["rs/b.class"]["fields"][0]["name"] = "x"
        candidates = _candidates(
            field_strategy="stable_symbol",
            class_strategy="exact_sha256",
        )
        candidates["classes"][0]["fields"]["relationships"][0][
            "new"
        ]["name"] = "x"

        out, summary = transfer_member_identity_candidates(
            _class_lineage(),
            _member_lineage(),
            old,
            new,
            candidates,
            old_build_id="v308",
            new_build_id="v309",
        )

        self.assertEqual(summary["applied_member_relationships"], 2)
        field = next(
            row
            for row in out["members"]
            if row["member_id"] == "CLIENT_FIELD_000001"
        )
        self.assertEqual(field["lineage"][1]["name"], "x")

    def test_untrusted_strategy_remains_unresolved(self):
        old, new = _indexes()
        out, summary = transfer_member_identity_candidates(
            _class_lineage(),
            _member_lineage(),
            old,
            new,
            _candidates(field_strategy="field_usage_unique"),
            old_build_id="v308",
            new_build_id="v309",
        )

        self.assertEqual(summary["applied_member_relationships"], 1)
        self.assertEqual(summary["review_only_relationships"], 1)
        self.assertTrue(
            any(
                row.get("kind") == "member_identity_review"
                for row in out["unresolved"]
            )
        )

    def test_candidate_sha_is_bound_to_exact_indexes(self):
        old, new = _indexes()
        candidates = _candidates()
        candidates["new_sha256"] = "9" * 64

        with self.assertRaises(UpdateMemberTransferError):
            transfer_member_identity_candidates(
                _class_lineage(),
                _member_lineage(),
                old,
                new,
                candidates,
                old_build_id="v308",
                new_build_id="v309",
            )

    def test_owner_must_be_same_canonical_class(self):
        old, new = _indexes()
        lineage = _class_lineage()
        second = copy.deepcopy(lineage["classes"][0])
        second["logical_id"] = "CLIENT_CLASS_000002"
        second["lineage"] = [
            copy.deepcopy(lineage["classes"][0]["lineage"][1])
        ]
        lineage["classes"][0]["lineage"] = [
            lineage["classes"][0]["lineage"][0]
        ]
        lineage["classes"].append(second)

        with self.assertRaises(UpdateMemberTransferError):
            transfer_member_identity_candidates(
                lineage,
                _member_lineage(),
                old,
                new,
                _candidates(),
                old_build_id="v308",
                new_build_id="v309",
            )


if __name__ == "__main__":
    unittest.main()
