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
    ("CLIENT_CLASS_000550", "rs/n/c/E"),
    ("CLIENT_CLASS_000559", "rs/n/c/M"),
    ("CLIENT_CLASS_000563", "rs/n/c/Q"),
    ("CLIENT_CLASS_000590", "rs/n/c/aO"),
    ("CLIENT_CLASS_000596", "rs/n/c/aU"),
    ("CLIENT_CLASS_000606", "rs/n/c/ae"),
    ("CLIENT_CLASS_000607", "rs/n/c/af"),
    ("CLIENT_CLASS_000611", "rs/n/c/aj"),
    ("CLIENT_CLASS_000650", "rs/n/c/d"),
    ("CLIENT_CLASS_000660", "rs/n/c/g"),
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
                                "source": "chat2-r6-fixture",
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


class Chat2SemanticReviewR6Tests(unittest.TestCase):
    def test_fourth_ui_batch_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r6.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r6.json"
        )

        actual = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )

        self.assertEqual(actual["proposal_count"], 10)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(
            actual["review_id"],
            "SEMREVIEW_3E29870ADC1A4856A558",
        )
        self.assertEqual(actual, expected)

    def test_fourth_ui_batch_uses_expected_stable_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r6.json"
        )
        by_name = {
            row["proposed_name"]: row
            for row in review["proposals"]
        }

        expected = {
            "FeaturesToolsInterface": "CLIENT_CLASS_000611",
            "ItemSpawnSearchInterface": "CLIENT_CLASS_000607",
            "VotePointShopInterface": "CLIENT_CLASS_000606",
            "DuelTypeSelectionInterface": "CLIENT_CLASS_000550",
            "StandardCombatSpellsInterface": "CLIENT_CLASS_000660",
            "AdventureBookInterfacePacketHandler": "CLIENT_CLASS_000650",
        }
        for name, stable_id in expected.items():
            self.assertEqual(
                by_name[name]["stable_id"],
                stable_id,
            )

    def test_fourth_ui_batch_names_do_not_collide_with_prior_batches(self):
        prior = []
        for suffix in ("r2", "r3", "r4", "r5"):
            prior.extend(
                _load(
                    "mappings/candidates/"
                    f"v308.semantic-review.chat2.{suffix}.json"
                )["proposals"]
            )

        current = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r6.json"
        )["proposals"]

        prior_names = {
            row["proposed_name"]
            for row in prior
        }
        current_names = {
            row["proposed_name"]
            for row in current
        }

        self.assertEqual(len(current_names), 10)
        self.assertTrue(prior_names.isdisjoint(current_names))
        self.assertNotIn("ChapterRewardClaimInterface", current_names)


if __name__ == "__main__":
    unittest.main()
