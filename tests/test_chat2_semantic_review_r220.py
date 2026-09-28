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
    ("CLIENT_CLASS_000810", "rs/runelite/a/b"),
    ("CLIENT_CLASS_000813", "rs/runelite/a/e"),
    ("CLIENT_CLASS_000814", "rs/runelite/a/f"),
    ("CLIENT_CLASS_000816", "rs/runelite/a/h"),
    ("CLIENT_CLASS_000817", "rs/runelite/a/i"),
    ("CLIENT_CLASS_000825", "rs/runelite/a/l"),
    ("CLIENT_CLASS_000826", "rs/runelite/a/l$a"),
    ("CLIENT_CLASS_000827", "rs/runelite/a/m"),
    ("CLIENT_CLASS_000828", "rs/runelite/a/m$a"),
    ("CLIENT_CLASS_000829", "rs/runelite/a/m$b"),
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
                        "provenance": [{"authority": "EXACT_CURRENT_CLIENT", "source": "chat2-r220-fixture"}],
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
        "builds": [{"build_id": "v308", "build_number": 308, "sha256": SHA, "source_name": "client(6).jar", "authority": "EXACT_CURRENT_CLIENT"}],
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
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class Chat2SemanticReviewR220Tests(unittest.TestCase):
    def test_r220_resolves_deterministically(self):
        candidates = _load("mappings/candidates/v308.semantic.chat2.r220.json")
        expected = _load("mappings/candidates/v308.semantic-review.chat2.r220.json")
        actual = resolve_semantic_candidates(_class_lineage(), _member_lineage(), candidates)
        self.assertEqual(actual["proposal_count"], 10)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(actual["review_id"], "SEMREVIEW_EA7F7B04B71D7BC455B6")
        self.assertEqual(actual, expected)

    def test_r220_expected_stable_ids(self):
        review = _load("mappings/candidates/v308.semantic-review.chat2.r220.json")
        self.assertEqual(
            {row["proposed_name"]: row["stable_id"] for row in review["proposals"]},
            {"Constants": "CLIENT_CLASS_000810", "Jarvis": "CLIENT_CLASS_000813", "LocalPoint": "CLIENT_CLASS_000814", "Perspective": "CLIENT_CLASS_000816", "Point": "CLIENT_CLASS_000817", "Shapes": "CLIENT_CLASS_000825", "ShapeIterator": "CLIENT_CLASS_000826", "SimplePolygon": "CLIENT_CLASS_000827", "SimpleIterator": "CLIENT_CLASS_000828", "TransformIterator": "CLIENT_CLASS_000829"},
        )

    def test_r220_name_and_owner_do_not_overlap_prior_reviews(self):
        current = _load("mappings/candidates/v308.semantic-review.chat2.r220.json")
        names = {row["proposed_name"] for row in current["proposals"]}
        owners = {row["source_coordinate"]["owner"] for row in current["proposals"]}
        prior_names = set()
        prior_owners = set()
        for batch in range(2, 220):
            path = ROOT / "mappings" / "candidates" / f"v308.semantic-review.chat2.r{batch}.json"
            if not path.is_file():
                continue
            prior = json.loads(path.read_text(encoding="utf-8"))
            prior_names.update(row["proposed_name"] for row in prior["proposals"])
            prior_owners.update(
                row["source_coordinate"]["owner"]
                for row in prior["proposals"]
                if row["target_kind"] == "class"
            )
        self.assertTrue(names.isdisjoint(prior_names))
        self.assertTrue(owners.isdisjoint(prior_owners))


if __name__ == "__main__":
    unittest.main()
