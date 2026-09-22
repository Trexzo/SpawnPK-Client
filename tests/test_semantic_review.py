import copy
import unittest

from spk_recovery.semantic_review import (
    SemanticReviewError,
    accept_semantic_proposals,
    resolve_semantic_candidates,
)


SHA = "a" * 64


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
                "sha256": SHA,
                "source_name": "client.jar",
                "authority": "EXACT_CURRENT_CLIENT",
            }
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
                        "internal_name": "rs/A",
                        "entry_path": "rs/A.class",
                        "entry_sha256": "b" * 64,
                        "structural_sha256": "c" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
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
        "source_sha256": SHA,
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
                        "owner_internal_name": "rs/A",
                        "name": "x",
                        "descriptor": "I",
                        "access": 1,
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
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/A",
                        "name": "a",
                        "descriptor": "(J)V",
                        "access": 1,
                        "code_length": 8,
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


def _candidate_set():
    return {
        "schema_version": 1,
        "kind": "semantic_candidate_set",
        "canonical": False,
        "source_build": "v308",
        "source_sha256": SHA,
        "candidates": [
            {
                "source_build": "v308",
                "source_sha256": SHA,
                "target": {
                    "kind": "class",
                    "owner": "rs/A",
                    "name": None,
                    "descriptor": None,
                },
                "proposed_name": "ExampleController",
                "confidence": 0.98,
                "evidence": [{"family": "literal", "detail": "example"}],
                "note": "test",
            },
            {
                "source_build": "v308",
                "source_sha256": SHA,
                "target": {
                    "kind": "field",
                    "owner": "rs/A",
                    "name": "x",
                    "descriptor": "I",
                },
                "proposed_name": "rewardIndex",
                "confidence": 0.95,
                "evidence": [],
            },
            {
                "source_build": "v308",
                "source_sha256": SHA,
                "target": {
                    "kind": "method",
                    "owner": "rs/A",
                    "name": "a",
                    "descriptor": "(J)V",
                },
                "proposed_name": "addFriend",
                "confidence": 0.99,
                "evidence": [],
            },
        ],
    }


class SemanticReviewTests(unittest.TestCase):
    def test_resolves_raw_coordinates_to_stable_ids(self):
        review = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            _candidate_set(),
        )
        self.assertEqual(review["proposal_count"], 3)
        by_kind = {
            row["target_kind"]: row
            for row in review["proposals"]
        }
        self.assertEqual(
            by_kind["class"]["stable_id"],
            "CLIENT_CLASS_000001",
        )
        self.assertEqual(
            by_kind["field"]["stable_id"],
            "CLIENT_FIELD_000001",
        )
        self.assertEqual(
            by_kind["method"]["stable_id"],
            "CLIENT_METHOD_000001",
        )
        self.assertTrue(review["review_id"].startswith("SEMREVIEW_"))

    def test_acceptance_is_explicit_and_selective(self):
        classes = _class_lineage()
        members = _member_lineage()
        review = resolve_semantic_candidates(
            classes,
            members,
            _candidate_set(),
        )
        method = next(
            row
            for row in review["proposals"]
            if row["target_kind"] == "method"
        )
        out_classes, out_members, summary = accept_semantic_proposals(
            classes,
            members,
            review,
            {
                "schema_version": 1,
                "kind": "semantic_acceptance_spec",
                "review_id": review["review_id"],
                "accept": [method["proposal_id"]],
            },
        )
        self.assertEqual(summary["accepted"], 1)
        self.assertEqual(
            out_members["members"][1]["semantic_name"],
            "addFriend",
        )
        self.assertEqual(
            out_members["members"][1]["semantic_status"],
            "ACCEPTED",
        )
        self.assertIsNone(
            out_classes["classes"][0]["semantic_name"],
        )

    def test_stale_review_id_is_rejected(self):
        review = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            _candidate_set(),
        )
        proposal = review["proposals"][0]
        with self.assertRaises(SemanticReviewError):
            accept_semantic_proposals(
                _class_lineage(),
                _member_lineage(),
                review,
                {
                    "schema_version": 1,
                    "kind": "semantic_acceptance_spec",
                    "review_id": "SEMREVIEW_STALE",
                    "accept": [proposal["proposal_id"]],
                },
            )

    def test_candidate_set_sha_must_match_canonical_build(self):
        candidates = copy.deepcopy(_candidate_set())
        candidates["source_sha256"] = "d" * 64
        with self.assertRaises(SemanticReviewError):
            resolve_semantic_candidates(
                _class_lineage(),
                _member_lineage(),
                candidates,
            )

    def test_unknown_coordinate_stays_unresolved(self):
        candidates = copy.deepcopy(_candidate_set())
        candidates["candidates"][2]["target"]["name"] = "missing"
        review = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )
        self.assertEqual(review["proposal_count"], 2)
        self.assertEqual(
            review["unresolved"][0]["reason"],
            "target_coordinate_not_canonical",
        )


if __name__ == "__main__":
    unittest.main()
