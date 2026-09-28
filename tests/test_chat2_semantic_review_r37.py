import json
from pathlib import Path
import unittest

from spk_recovery.semantic_review import resolve_semantic_candidates


SHA = (
    "854f26ff9f134b0317572e7ac1688e6f"
    "40a231d5a4c66f8db5d655b7f45ce7c6"
)
ROOT = Path(__file__).resolve().parents[1]


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
                "source_name": "client(6).jar",
                "authority": "EXACT_CURRENT_CLIENT",
            }
        ],
        "classes": [
            {
                "logical_id": "CLIENT_CLASS_000046",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/S",
                        "entry_path": "rs/S.class",
                        "entry_sha256": "b" * 64,
                        "structural_sha256": "c" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [
                            {
                                "authority": "EXACT_CURRENT_CLIENT",
                                "source": "chat2-r37-fixture",
                            }
                        ],
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
        "members": [],
        "unresolved": [],
    }


def _load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class Chat2SemanticReviewR37Tests(unittest.TestCase):
    def test_r37_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/v308.semantic.chat2.r37.json"
        )
        expected = _load(
            "mappings/candidates/v308.semantic-review.chat2.r37.json"
        )
        actual = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )
        self.assertEqual(actual["proposal_count"], 1)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(
            actual["review_id"],
            "SEMREVIEW_DFC7E83B997CD7A18622",
        )
        self.assertEqual(actual, expected)

    def test_r37_expected_stable_id(self):
        review = _load(
            "mappings/candidates/v308.semantic-review.chat2.r37.json"
        )
        self.assertEqual(
            {
                row["proposed_name"]: row["stable_id"]
                for row in review["proposals"]
            },
            {"VertexNormalBuffer": "CLIENT_CLASS_000046"},
        )

    def test_r37_name_and_owner_do_not_overlap_prior_reviews(self):
        r37 = _load(
            "mappings/candidates/v308.semantic-review.chat2.r37.json"
        )
        names = {row["proposed_name"] for row in r37["proposals"]}
        owners = {
            row["source_coordinate"]["owner"]
            for row in r37["proposals"]
        }

        prior_names = set()
        prior_owners = set()
        for batch in range(2, 37):
            path = (
                ROOT
                / "mappings"
                / "candidates"
                / f"v308.semantic-review.chat2.r{batch}.json"
            )
            if not path.is_file():
                continue
            prior = json.loads(path.read_text(encoding="utf-8"))
            prior_names.update(
                row["proposed_name"]
                for row in prior["proposals"]
            )
            prior_owners.update(
                row["source_coordinate"]["owner"]
                for row in prior["proposals"]
                if row["target_kind"] == "class"
            )

        self.assertTrue(names.isdisjoint(prior_names))
        self.assertTrue(owners.isdisjoint(prior_owners))


if __name__ == "__main__":
    unittest.main()
