import copy
from pathlib import Path
import json
import unittest

from spk_recovery.semantic_review import (
    accept_semantic_proposals,
    resolve_semantic_candidates,
)
from spk_recovery.semantic_review_authority import (
    SemanticReviewAuthorityError,
    build_semantic_review_authority_registry,
    validate_semantic_review_authority_registry,
    verify_accepted_semantic_lineage,
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
            }
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
                "evidence": [
                    {"family": "literal", "detail": "example controller"}
                ],
                "note": "class authority",
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
                "evidence": [
                    {"family": "field-use", "detail": "reward index"}
                ],
                "note": "field authority",
            },
        ],
    }


def _accepted_fixture():
    classes = _class_lineage()
    members = _member_lineage()
    review = resolve_semantic_candidates(
        classes,
        members,
        _candidate_set(),
    )
    acceptance = {
        "schema_version": 1,
        "kind": "semantic_acceptance_spec",
        "review_id": review["review_id"],
        "accept": [
            row["proposal_id"]
            for row in review["proposals"]
        ],
    }
    out_classes, out_members, _ = accept_semantic_proposals(
        classes,
        members,
        review,
        acceptance,
    )
    return out_classes, out_members, review, acceptance


class SemanticReviewAuthorityTests(unittest.TestCase):
    def test_registry_authenticates_accepted_lineage_and_confidence(self):
        classes, members, review, acceptance = _accepted_fixture()
        registry = build_semantic_review_authority_registry(
            [
                {
                    "review_set": review,
                    "acceptance_spec": acceptance,
                }
            ]
        )

        summary = verify_accepted_semantic_lineage(
            classes,
            members,
            registry,
        )

        self.assertTrue(
            registry["registry_id"].startswith("SEMREGAUTH_")
        )
        self.assertEqual(summary["accepted_records"], 2)
        self.assertEqual(summary["accepted_class_records"], 1)
        self.assertEqual(summary["accepted_member_records"], 1)
        self.assertEqual(summary["verified_provenance_rows"], 2)
        self.assertEqual(
            summary["used_review_ids"],
            [review["review_id"]],
        )

    def test_stale_review_id_after_confidence_drift_is_rejected(self):
        _, _, review, acceptance = _accepted_fixture()
        drifted = copy.deepcopy(review)
        drifted["proposals"][0]["confidence"] = 0.5

        with self.assertRaises(SemanticReviewAuthorityError):
            build_semantic_review_authority_registry(
                [
                    {
                        "review_set": drifted,
                        "acceptance_spec": acceptance,
                    }
                ]
            )

    def test_unaccepted_lineage_proposal_is_rejected(self):
        classes, members, review, acceptance = _accepted_fixture()
        class_proposal = next(
            row
            for row in review["proposals"]
            if row["target_kind"] == "class"
        )
        partial_acceptance = copy.deepcopy(acceptance)
        partial_acceptance["accept"] = [
            class_proposal["proposal_id"]
        ]
        registry = build_semantic_review_authority_registry(
            [
                {
                    "review_set": review,
                    "acceptance_spec": partial_acceptance,
                }
            ]
        )

        with self.assertRaises(SemanticReviewAuthorityError):
            verify_accepted_semantic_lineage(
                classes,
                members,
                registry,
            )

    def test_persisted_confidence_must_match_trusted_proposal(self):
        classes, members, review, acceptance = _accepted_fixture()
        classes["classes"][0]["semantic_confidence"] = 0.5
        registry = build_semantic_review_authority_registry(
            [
                {
                    "review_set": review,
                    "acceptance_spec": acceptance,
                }
            ]
        )

        with self.assertRaises(SemanticReviewAuthorityError):
            verify_accepted_semantic_lineage(
                classes,
                members,
                registry,
            )

    def test_provenance_evidence_must_match_trusted_proposal(self):
        classes, members, review, acceptance = _accepted_fixture()
        classes["classes"][0]["semantic_provenance"][0][
            "evidence"
        ] = []
        registry = build_semantic_review_authority_registry(
            [
                {
                    "review_set": review,
                    "acceptance_spec": acceptance,
                }
            ]
        )

        with self.assertRaises(SemanticReviewAuthorityError):
            verify_accepted_semantic_lineage(
                classes,
                members,
                registry,
            )

    def test_duplicate_review_authority_is_rejected(self):
        _, _, review, acceptance = _accepted_fixture()
        entry = {
            "review_set": review,
            "acceptance_spec": acceptance,
        }

        with self.assertRaises(SemanticReviewAuthorityError):
            build_semantic_review_authority_registry(
                [entry, copy.deepcopy(entry)]
            )

    def test_unresolved_review_cannot_be_trusted(self):
        _, _, review, acceptance = _accepted_fixture()
        review = copy.deepcopy(review)
        review["unresolved"] = [{"reason": "missing_target"}]

        with self.assertRaises(SemanticReviewAuthorityError):
            build_semantic_review_authority_registry(
                [
                    {
                        "review_set": review,
                        "acceptance_spec": acceptance,
                    }
                ]
            )

    def test_real_v308_r2_review_and_acceptance_form_valid_registry(self):
        root = Path(__file__).resolve().parents[1]
        review = json.loads(
            (
                root
                / "mappings"
                / "candidates"
                / "v308.semantic-review.chat2.r2.json"
            ).read_text(encoding="utf-8")
        )
        acceptance = json.loads(
            (
                root
                / "mappings"
                / "v308.semantic.acceptance.json"
            ).read_text(encoding="utf-8")
        )

        registry = build_semantic_review_authority_registry(
            [
                {
                    "review_set": review,
                    "acceptance_spec": acceptance,
                }
            ]
        )
        summary = validate_semantic_review_authority_registry(
            registry
        )

        self.assertEqual(
            summary["review_ids"],
            ["SEMREVIEW_DD69CD752A6E46181BAC"],
        )
        self.assertEqual(summary["accepted_proposal_count"], 39)


if __name__ == "__main__":
    unittest.main()
