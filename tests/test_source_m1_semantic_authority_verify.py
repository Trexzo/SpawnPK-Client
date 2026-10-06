from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from spk_recovery.source_m1_semantic_authority_verify import (
    EXPECTED_REVIEW_ID,
    EXPECTED_V308_SHA256,
    SourceM1SemanticAuthorityError,
    verify_v308_semantic_review_authority,
)


def _hex(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _provenance(proposal: dict) -> dict:
    return {
        "proposal_id": proposal["proposal_id"],
        "review_id": EXPECTED_REVIEW_ID,
        "source_build": proposal["source_build"],
        "source_sha256": proposal["source_sha256"],
        "source_coordinate": copy.deepcopy(
            proposal["source_coordinate"]
        ),
        "evidence": copy.deepcopy(proposal["evidence"]),
        "note": proposal.get("note"),
    }


def _real_r2_lineage(review: dict, acceptance: dict):
    accepted = set(acceptance["accept"])
    proposals = [
        row
        for row in review["proposals"]
        if row["proposal_id"] in accepted
    ]
    class_proposals = {
        row["stable_id"]: row
        for row in proposals
        if row["target_kind"] == "class"
    }
    member_proposals = [
        row
        for row in proposals
        if row["target_kind"] != "class"
    ]

    owner_names = {
        stable_id: row["source_coordinate"]["owner"]
        for stable_id, row in class_proposals.items()
    }
    for row in member_proposals:
        owner_id = row["owner_logical_id"]
        owner = row["source_coordinate"]["owner"]
        prior = owner_names.get(owner_id)
        if prior is not None:
            assert prior == owner
        owner_names[owner_id] = owner

    classes = []
    for logical_id, owner in sorted(owner_names.items()):
        proposal = class_proposals.get(logical_id)
        accepted_class = proposal is not None
        classes.append(
            {
                "logical_id": logical_id,
                "semantic_name": (
                    proposal["proposed_name"]
                    if accepted_class
                    else None
                ),
                "semantic_status": (
                    "ACCEPTED" if accepted_class else "UNKNOWN"
                ),
                "semantic_confidence": (
                    proposal["confidence"] if accepted_class else 0.0
                ),
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": owner,
                        "entry_path": owner + ".class",
                        "entry_sha256": _hex("entry:" + owner),
                        "structural_sha256": _hex(
                            "structural:" + owner
                        ),
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": (
                    [_provenance(proposal)]
                    if accepted_class
                    else []
                ),
            }
        )

    members = []
    for proposal in sorted(
        member_proposals,
        key=lambda row: row["stable_id"],
    ):
        coordinate = proposal["source_coordinate"]
        members.append(
            {
                "member_id": proposal["stable_id"],
                "owner_logical_id": proposal["owner_logical_id"],
                "kind": proposal["target_kind"],
                "semantic_name": proposal["proposed_name"],
                "semantic_status": "ACCEPTED",
                "semantic_confidence": proposal["confidence"],
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": coordinate["owner"],
                        "name": coordinate["name"],
                        "descriptor": coordinate["descriptor"],
                        "access": 1,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [
                    _provenance(proposal)
                ],
            }
        )

    class_lineage = {
        "schema_version": 1,
        "namespace": "spawnpk-client",
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": "v308",
        "builds": [
            {
                "build_id": "v308",
                "build_number": 308,
                "sha256": EXPECTED_V308_SHA256,
                "source_name": "client.jar",
                "authority": "EXACT_CURRENT_CLIENT",
            }
        ],
        "classes": classes,
        "unresolved": [],
    }
    member_lineage = {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": EXPECTED_V308_SHA256,
        "members": members,
        "unresolved": [],
    }
    return class_lineage, member_lineage


class SourceM1SemanticAuthorityVerifyTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.review = json.loads(
            (
                root
                / "mappings"
                / "candidates"
                / "v308.semantic-review.chat2.r2.json"
            ).read_text(encoding="utf-8")
        )
        self.acceptance = json.loads(
            (
                root
                / "mappings"
                / "v308.semantic.acceptance.json"
            ).read_text(encoding="utf-8")
        )
        self.classes, self.members = _real_r2_lineage(
            self.review,
            self.acceptance,
        )

    def test_real_r2_authority_authenticates_all_39_accepted_rows(self):
        proof = verify_v308_semantic_review_authority(
            self.classes,
            self.members,
            self.review,
            self.acceptance,
        )

        self.assertTrue(proof["verified"])
        self.assertTrue(
            proof["verification_id"].startswith("SOURCESEMAUTH_")
        )
        self.assertEqual(proof["review_id"], EXPECTED_REVIEW_ID)
        self.assertEqual(proof["trusted_review_count"], 1)
        self.assertEqual(
            proof["trusted_accepted_proposal_count"],
            39,
        )
        self.assertEqual(proof["accepted_class_records"], 32)
        self.assertEqual(proof["accepted_member_records"], 7)
        self.assertEqual(proof["accepted_records"], 39)
        self.assertEqual(proof["verified_provenance_rows"], 39)
        self.assertEqual(
            proof["used_review_ids"],
            [EXPECTED_REVIEW_ID],
        )

    def test_semantic_confidence_drift_is_rejected(self):
        classes = copy.deepcopy(self.classes)
        accepted = next(
            row
            for row in classes["classes"]
            if row["semantic_status"] == "ACCEPTED"
        )
        accepted["semantic_confidence"] = 0.5

        with self.assertRaises(SourceM1SemanticAuthorityError):
            verify_v308_semantic_review_authority(
                classes,
                self.members,
                self.review,
                self.acceptance,
            )

    def test_missing_accepted_row_is_rejected(self):
        classes = copy.deepcopy(self.classes)
        accepted = next(
            row
            for row in classes["classes"]
            if row["semantic_status"] == "ACCEPTED"
        )
        accepted["semantic_name"] = None
        accepted["semantic_status"] = "UNKNOWN"
        accepted["semantic_confidence"] = 0.0
        accepted["semantic_provenance"] = []

        with self.assertRaisesRegex(
            SourceM1SemanticAuthorityError,
            "accepted_class_records",
        ):
            verify_v308_semantic_review_authority(
                classes,
                self.members,
                self.review,
                self.acceptance,
            )

    def test_wrong_v308_authority_is_rejected(self):
        classes = copy.deepcopy(self.classes)
        classes["builds"][0]["sha256"] = "0" * 64

        with self.assertRaisesRegex(
            SourceM1SemanticAuthorityError,
            "not bound to exact v308",
        ):
            verify_v308_semantic_review_authority(
                classes,
                self.members,
                self.review,
                self.acceptance,
            )


if __name__ == "__main__":
    unittest.main()
