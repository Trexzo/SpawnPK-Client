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
    ("CLIENT_CLASS_000250", "rs/gui/b/h"),
    ("CLIENT_CLASS_000413", "rs/l/e/a/o"),
    ("CLIENT_CLASS_000452", "rs/l/f/a/c/c"),
    ("CLIENT_CLASS_000560", "rs/n/c/N"),
    ("CLIENT_CLASS_000572", "rs/n/c/Z"),
    ("CLIENT_CLASS_000580", "rs/n/c/aE"),
    ("CLIENT_CLASS_000585", "rs/n/c/aJ"),
    ("CLIENT_CLASS_000586", "rs/n/c/aK"),
    ("CLIENT_CLASS_000598", "rs/n/c/aW"),
    ("CLIENT_CLASS_000613", "rs/n/c/al"),
    ("CLIENT_CLASS_000623", "rs/n/c/as"),
    ("CLIENT_CLASS_000624", "rs/n/c/at"),
    ("CLIENT_CLASS_000625", "rs/n/c/au"),
    ("CLIENT_CLASS_000634", "rs/n/c/b/a"),
    ("CLIENT_CLASS_000652", "rs/n/c/d/b"),
    ("CLIENT_CLASS_000653", "rs/n/c/d/c"),
    ("CLIENT_CLASS_000655", "rs/n/c/d/e"),
    ("CLIENT_CLASS_000670", "rs/n/c/q"),
    ("CLIENT_CLASS_000674", "rs/n/c/u"),
    ("CLIENT_CLASS_000676", "rs/n/c/w"),
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
                                "source": "chat2-r3-fixture",
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


class Chat2SemanticReviewR3Tests(unittest.TestCase):
    def test_second_exact_v308_batch_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r3.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r3.json"
        )

        actual = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )

        self.assertEqual(actual["proposal_count"], 20)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(
            actual["review_id"],
            "SEMREVIEW_1948F58DF9A849992F1A",
        )
        self.assertEqual(actual, expected)

    def test_second_batch_uses_expected_exact_v308_stable_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r3.json"
        )
        by_name = {
            row["proposed_name"]: row
            for row in review["proposals"]
        }

        self.assertEqual(
            by_name["MarketplaceInterface"]["stable_id"],
            "CLIENT_CLASS_000623",
        )
        self.assertEqual(
            by_name["AfflictionTomesInterface"]["stable_id"],
            "CLIENT_CLASS_000655",
        )
        self.assertEqual(
            by_name["BountyHunterOverlay"]["stable_id"],
            "CLIENT_CLASS_000452",
        )
        self.assertEqual(
            by_name["LoadoutFolderPanel"]["stable_id"],
            "CLIENT_CLASS_000250",
        )

    def test_second_batch_does_not_reuse_r2_semantic_names(self):
        r2 = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r2.json"
        )
        r3 = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r3.json"
        )

        r2_names = {
            row["proposed_name"]
            for row in r2["proposals"]
        }
        r3_names = {
            row["proposed_name"]
            for row in r3["proposals"]
        }

        self.assertEqual(len(r3_names), 20)
        self.assertTrue(r2_names.isdisjoint(r3_names))


if __name__ == "__main__":
    unittest.main()
