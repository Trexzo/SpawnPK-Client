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
    ("CLIENT_CLASS_000110", "rs/d/a"),
    ("CLIENT_CLASS_000113", "rs/d/d"),
    ("CLIENT_CLASS_000118", "rs/d/h"),
    ("CLIENT_CLASS_000121", "rs/d/j"),
    ("CLIENT_CLASS_000122", "rs/d/k"),
    ("CLIENT_CLASS_000131", "rs/d/r"),
    ("CLIENT_CLASS_000140", "rs/d/x"),
    ("CLIENT_CLASS_000141", "rs/d/y"),
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
                                "source": "chat2-r28-fixture",
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


class Chat2SemanticReviewR28Tests(unittest.TestCase):
    def test_r28_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r28.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r28.json"
        )

        actual = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )

        self.assertEqual(actual["proposal_count"], 8)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(
            actual["review_id"],
            "SEMREVIEW_4276DC989C3E027F83A1",
        )
        self.assertEqual(actual, expected)

    def test_r28_expected_stable_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r28.json"
        )
        by_name = {
            row["proposed_name"]: row["stable_id"]
            for row in review["proposals"]
        }
        self.assertEqual(
            by_name,
            {
                "SequenceDefinition": "CLIENT_CLASS_000110",
                "NpcDefinition": "CLIENT_CLASS_000113",
                "FloorDefinition": "CLIENT_CLASS_000118",
                "IdentityKitDefinition": "CLIENT_CLASS_000121",
                "ItemDefinition": "CLIENT_CLASS_000122",
                "ObjectDefinition": "CLIENT_CLASS_000131",
                "SpotAnimationDefinition": "CLIENT_CLASS_000140",
                "VarbitDefinition": "CLIENT_CLASS_000141",
            },
        )

    def test_r28_names_do_not_overlap_prior_reviews(self):
        r28 = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r28.json"
        )
        r28_names = {
            row["proposed_name"]
            for row in r28["proposals"]
        }

        prior_names = set()
        for batch in range(2, 28):
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

        self.assertTrue(r28_names.isdisjoint(prior_names))


if __name__ == "__main__":
    unittest.main()
