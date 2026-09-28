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
    ("CLIENT_CLASS_000551", "rs/n/c/F"),
    ("CLIENT_CLASS_000553", "rs/n/c/H"),
    ("CLIENT_CLASS_000555", "rs/n/c/J"),
    ("CLIENT_CLASS_000566", "rs/n/c/T"),
    ("CLIENT_CLASS_000581", "rs/n/c/aF"),
    ("CLIENT_CLASS_000594", "rs/n/c/aS"),
    ("CLIENT_CLASS_000601", "rs/n/c/aZ"),
    ("CLIENT_CLASS_000608", "rs/n/c/ag"),
    ("CLIENT_CLASS_000610", "rs/n/c/ai"),
    ("CLIENT_CLASS_000615", "rs/n/c/an"),
    ("CLIENT_CLASS_000616", "rs/n/c/ao"),
    ("CLIENT_CLASS_000621", "rs/n/c/aq"),
    ("CLIENT_CLASS_000631", "rs/n/c/az"),
    ("CLIENT_CLASS_000639", "rs/n/c/ba"),
    ("CLIENT_CLASS_000663", "rs/n/c/j"),
    ("CLIENT_CLASS_000664", "rs/n/c/k"),
    ("CLIENT_CLASS_000667", "rs/n/c/n"),
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
                                "source": "chat2-r5-fixture",
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


class Chat2SemanticReviewR5Tests(unittest.TestCase):
    def test_third_ui_batch_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r5.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r5.json"
        )

        actual = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )

        self.assertEqual(actual["proposal_count"], 17)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(
            actual["review_id"],
            "SEMREVIEW_C74696DD26C13B1CC8D4",
        )
        self.assertEqual(actual, expected)

    def test_third_ui_batch_uses_expected_stable_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r5.json"
        )
        by_name = {
            row["proposed_name"]: row
            for row in review["proposals"]
        }

        expected = {
            "ControlOptionsInterface": "CLIENT_CLASS_000610",
            "ItemsKeptOnDeathInterface": "CLIENT_CLASS_000608",
            "KnowledgebaseInterface": "CLIENT_CLASS_000639",
            "MonsterSpawnerInterface": "CLIENT_CLASS_000566",
            "BloodDiamondFuserInterface": "CLIENT_CLASS_000663",
            "BloodcoreTokenLotteryInterface": "CLIENT_CLASS_000667",
        }
        for name, stable_id in expected.items():
            self.assertEqual(
                by_name[name]["stable_id"],
                stable_id,
            )

    def test_third_ui_batch_names_do_not_collide_with_prior_batches(self):
        prior = []
        for relative in (
            "mappings/candidates/"
            "v308.semantic-review.chat2.r2.json",
            "mappings/candidates/"
            "v308.semantic-review.chat2.r3.json",
            "mappings/candidates/"
            "v308.semantic-review.chat2.r4.json",
        ):
            prior.extend(_load(relative)["proposals"])

        current = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r5.json"
        )["proposals"]

        prior_names = {
            row["proposed_name"]
            for row in prior
        }
        current_names = {
            row["proposed_name"]
            for row in current
        }

        self.assertEqual(len(current_names), 17)
        self.assertTrue(prior_names.isdisjoint(current_names))


if __name__ == "__main__":
    unittest.main()
