from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from spk_recovery.source_m1_lineage_rederive import (
    EXPECTED_REVIEW_ID,
    EXPECTED_V308_SHA256,
    HISTORICAL_MEMBER_ANCHORS,
    SourceM1LineageRederiveError,
    _accepted_lineage_projection,
    _proposal_projection,
    rederive_v308_lineage,
)


class SourceM1LineageRederiveTests(unittest.TestCase):
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
                root / "mappings" / "v308.semantic.acceptance.json"
            ).read_text(encoding="utf-8")
        )

    def test_committed_r2_authority_is_complete_39_row_projection(self):
        projection = _proposal_projection(
            self.review,
            self.acceptance,
        )

        self.assertEqual(self.review["review_id"], EXPECTED_REVIEW_ID)
        self.assertEqual(self.review["source_sha256"], EXPECTED_V308_SHA256)
        self.assertEqual(len(projection), 39)
        self.assertEqual(
            {row["proposal_id"] for row in projection},
            set(self.acceptance["accept"]),
        )
        self.assertEqual(
            sum(row["target_kind"] == "class" for row in projection),
            32,
        )
        self.assertEqual(
            sum(row["target_kind"] != "class" for row in projection),
            7,
        )

    def test_historical_member_anchors_are_locked(self):
        self.assertEqual(
            HISTORICAL_MEMBER_ANCHORS[
                ("rs/Client", "do", "[Lrs/a/k;")
            ],
            "CLIENT_FIELD_000367",
        )
        self.assertEqual(
            HISTORICAL_MEMBER_ANCHORS[
                ("rs/Client", "if", "Ljava/util/Map;")
            ],
            "CLIENT_FIELD_000552",
        )
        self.assertEqual(
            HISTORICAL_MEMBER_ANCHORS[
                ("rs/n/c/d/a", "do", "Lrs/n/d/c;")
            ],
            "CLIENT_FIELD_005256",
        )

    def test_wrong_index_authority_fails_before_rederivation(self):
        with self.assertRaisesRegex(
            SourceM1LineageRederiveError,
            "not bound to exact v308",
        ):
            rederive_v308_lineage(
                {"sha256": "0" * 64},
                self.review,
                self.acceptance,
            )

    def test_acceptance_must_cover_complete_r2_review(self):
        partial = copy.deepcopy(self.acceptance)
        partial["accept"] = partial["accept"][:-1]
        with self.assertRaisesRegex(
            SourceM1LineageRederiveError,
            "must contain 39 proposals",
        ):
            _proposal_projection(self.review, partial)

    def test_lineage_projection_preserves_review_shape(self):
        proposal = _proposal_projection(
            self.review,
            self.acceptance,
        )[0]
        provenance = {
            "proposal_id": proposal["proposal_id"],
            "review_id": EXPECTED_REVIEW_ID,
            "source_build": proposal["source_build"],
            "source_sha256": proposal["source_sha256"],
            "source_coordinate": copy.deepcopy(
                proposal["source_coordinate"]
            ),
            "evidence": copy.deepcopy(proposal["evidence"]),
            "note": proposal["note"],
        }

        if proposal["target_kind"] == "class":
            classes = {
                "classes": [
                    {
                        "logical_id": proposal["stable_id"],
                        "semantic_status": "ACCEPTED",
                        "semantic_name": proposal["semantic_name"],
                        "semantic_confidence": proposal[
                            "semantic_confidence"
                        ],
                        "semantic_provenance": [provenance],
                    }
                ]
            }
            members = {"members": []}
        else:
            classes = {"classes": []}
            members = {
                "members": [
                    {
                        "member_id": proposal["stable_id"],
                        "owner_logical_id": proposal[
                            "owner_logical_id"
                        ],
                        "kind": proposal["target_kind"],
                        "semantic_status": "ACCEPTED",
                        "semantic_name": proposal["semantic_name"],
                        "semantic_confidence": proposal[
                            "semantic_confidence"
                        ],
                        "semantic_provenance": [provenance],
                    }
                ]
            }

        self.assertEqual(
            _accepted_lineage_projection(classes, members),
            [proposal],
        )


if __name__ == "__main__":
    unittest.main()
