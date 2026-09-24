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
    ("CLIENT_CLASS_001069", "rs/ui/components/g"),
    ("CLIENT_CLASS_001070", "rs/ui/components/g$a"),
    ("CLIENT_CLASS_001071", "rs/ui/components/g$b"),
    ("CLIENT_CLASS_001072", "rs/ui/components/g$c"),
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
                                "source": "chat2-r167-fixture",
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
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class Chat2SemanticReviewR167Tests(unittest.TestCase):
    def test_r167_resolves_deterministically(self):
        candidates = _load("mappings/candidates/v308.semantic.chat2.r167.json")
        expected = _load("mappings/candidates/v308.semantic-review.chat2.r167.json")
        actual = resolve_semantic_candidates(
            _class_lineage(), _member_lineage(), candidates
        )
        self.assertEqual(actual["proposal_count"], 4)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(actual["review_id"], "SEMREVIEW_EF8E4FF6B73AA76704F7")
        self.assertEqual(actual, expected)

    def test_r167_expected_stable_ids(self):
        review = _load("mappings/candidates/v308.semantic-review.chat2.r167.json")
        self.assertEqual(
            {row["proposed_name"]: row["stable_id"] for row in review["proposals"]},
            {
                "DragAndDropReorderPane": "CLIENT_CLASS_001069",
                "DragAndDropReorderLayoutManager": "CLIENT_CLASS_001070",
                "DragAndDropReorderMouseHandler": "CLIENT_CLASS_001071",
                "DragAndDropReorderListener": "CLIENT_CLASS_001072",
            },
        )

    def test_r167_name_and_owner_do_not_overlap_prior_reviews(self):
        current = _load("mappings/candidates/v308.semantic-review.chat2.r167.json")
        names = {row["proposed_name"] for row in current["proposals"]}
        owners = {row["source_coordinate"]["owner"] for row in current["proposals"]}

        prior_names = set()
        prior_owners = set()
        for batch in range(2, 167):
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
