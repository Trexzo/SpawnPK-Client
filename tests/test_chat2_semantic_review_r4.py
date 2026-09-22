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
    ("CLIENT_CLASS_000855", "rs/s/a/a"),
    ("CLIENT_CLASS_000887", "rs/s/c/a"),
    ("CLIENT_CLASS_000897", "rs/s/d/a"),
    ("CLIENT_CLASS_000918", "rs/s/h/b"),
    ("CLIENT_CLASS_000919", "rs/s/i/a"),
    ("CLIENT_CLASS_000922", "rs/s/j/a"),
    ("CLIENT_CLASS_000944", "rs/s/o/d"),
    ("CLIENT_CLASS_000958", "rs/s/r/a"),
    ("CLIENT_CLASS_000961", "rs/s/s/a"),
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
                                "source": "chat2-r4-fixture",
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


class Chat2SemanticReviewR4Tests(unittest.TestCase):
    def test_config_batch_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r4.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r4.json"
        )

        actual = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )

        self.assertEqual(actual["proposal_count"], 9)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(
            actual["review_id"],
            "SEMREVIEW_0D067AB471D25E575699",
        )
        self.assertEqual(actual, expected)

    def test_config_batch_uses_expected_stable_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r4.json"
        )
        by_name = {
            row["proposed_name"]: row
            for row in review["proposals"]
        }

        self.assertEqual(
            by_name["EntityHiderConfig"]["stable_id"],
            "CLIENT_CLASS_000897",
        )
        self.assertEqual(
            by_name["KeyRemappingConfig"]["stable_id"],
            "CLIENT_CLASS_000922",
        )
        self.assertEqual(
            by_name["NpcHighlightConfig"]["stable_id"],
            "CLIENT_CLASS_000944",
        )
        self.assertEqual(
            by_name["TileIndicatorConfig"]["stable_id"],
            "CLIENT_CLASS_000958",
        )

    def test_config_batch_names_do_not_collide_with_prior_batches(self):
        prior = []
        for relative in (
            "mappings/candidates/"
            "v308.semantic-review.chat2.r2.json",
            "mappings/candidates/"
            "v308.semantic-review.chat2.r3.json",
        ):
            prior.extend(_load(relative)["proposals"])

        current = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r4.json"
        )["proposals"]

        prior_names = {
            row["proposed_name"]
            for row in prior
        }
        current_names = {
            row["proposed_name"]
            for row in current
        }

        self.assertEqual(len(current_names), 9)
        self.assertTrue(prior_names.isdisjoint(current_names))


if __name__ == "__main__":
    unittest.main()
