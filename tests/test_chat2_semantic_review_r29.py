import json
from pathlib import Path
import unittest

from spk_recovery.semantic_review import resolve_semantic_candidates


SHA = (
    "854f26ff9f134b0317572e7ac1688e6f"
    "40a231d5a4c66f8db5d655b7f45ce7c6"
)
ROOT = Path(__file__).resolve().parents[1]

CLASS_COORDS = [
    ("CLIENT_CLASS_000743", "rs/q/a"),
    ("CLIENT_CLASS_001115", "rs/x/a"),
    ("CLIENT_CLASS_001116", "rs/x/b"),
    ("CLIENT_CLASS_001119", "rs/x/e"),
    ("CLIENT_CLASS_001120", "rs/x/f"),
]


def _class_lineage():
    classes = []
    for logical_id, internal_name in CLASS_COORDS:
        classes.append(
            {
                "logical_id": logical_id,
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": internal_name,
                        "entry_path": internal_name + ".class",
                        "entry_sha256": "b" * 64,
                        "structural_sha256": "c" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [
                            {
                                "authority": "EXACT_CURRENT_CLIENT",
                                "source": "chat2-r29-fixture",
                            }
                        ],
                    }
                ],
                "semantic_provenance": [],
            }
        )
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
        "classes": classes,
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
    return json.loads(
        (ROOT / relative).read_text(encoding="utf-8")
    )


class Chat2SemanticReviewR29Tests(unittest.TestCase):
    def test_r29_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r29.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r29.json"
        )

        actual = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )

        self.assertEqual(actual["proposal_count"], 5)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(
            actual["review_id"],
            "SEMREVIEW_058934E269FB8E9BAFBF",
        )
        self.assertEqual(actual, expected)

    def test_r29_expected_stable_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r29.json"
        )
        by_name = {
            row["proposed_name"]: row["stable_id"]
            for row in review["proposals"]
        }
        self.assertEqual(
            by_name,
            {
                "IsaacCipher": "CLIENT_CLASS_000743",
                "BZip2Decompressor": "CLIENT_CLASS_001115",
                "BZip2State": "CLIENT_CLASS_001116",
                "Stream": "CLIENT_CLASS_001119",
                "StreamLoader": "CLIENT_CLASS_001120",
            },
        )

    def test_r29_names_do_not_overlap_prior_reviews(self):
        r29 = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r29.json"
        )
        r29_names = {
            row["proposed_name"]
            for row in r29["proposals"]
        }

        prior_names = set()
        for batch in range(2, 29):
            path = (
                ROOT
                / "mappings"
                / "candidates"
                / f"v308.semantic-review.chat2.r{batch}.json"
            )
            if not path.is_file():
                continue
            review = json.loads(path.read_text(encoding="utf-8"))
            prior_names.update(
                row["proposed_name"]
                for row in review["proposals"]
            )

        self.assertTrue(r29_names.isdisjoint(prior_names))


if __name__ == "__main__":
    unittest.main()
