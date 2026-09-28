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
    ("CLIENT_CLASS_000083", "rs/cache/a/a"),
    ("CLIENT_CLASS_000084", "rs/cache/a/b"),
    ("CLIENT_CLASS_000087", "rs/cache/b/a/a"),
    ("CLIENT_CLASS_000088", "rs/cache/b/a/b"),
    ("CLIENT_CLASS_000089", "rs/cache/b/a/c"),
    ("CLIENT_CLASS_000090", "rs/cache/b/a/d"),
    ("CLIENT_CLASS_000091", "rs/cache/b/b"),
    ("CLIENT_CLASS_000092", "rs/cache/b/c"),
    ("CLIENT_CLASS_000093", "rs/cache/b/d"),
    ("CLIENT_CLASS_000094", "rs/cache/b/e"),
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
                                "source": "chat2-r23-fixture",
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


class Chat2SemanticReviewR23Tests(unittest.TestCase):
    def test_r23_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r23.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r23.json"
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
            "SEMREVIEW_A7557C36D92989848D7C",
        )
        self.assertEqual(actual, expected)

    def test_r23_expected_stable_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r23.json"
        )
        by_name = {
            row["proposed_name"]: row["stable_id"]
            for row in review["proposals"]
        }
        self.assertEqual(
            by_name,
            {
                "ClientProgressFileDownloader":
                    "CLIENT_CLASS_000083",
                "FileDownloader":
                    "CLIENT_CLASS_000084",
                "CacheUpdater":
                    "CLIENT_CLASS_000087",
                "ClientUpdater":
                    "CLIENT_CLASS_000088",
                "ConfigUpdater":
                    "CLIENT_CLASS_000089",
                "SpriteUpdater":
                    "CLIENT_CLASS_000090",
                "AssetUpdateError":
                    "CLIENT_CLASS_000091",
                "AssetUpdateManager":
                    "CLIENT_CLASS_000092",
                "AssetUpdater":
                    "CLIENT_CLASS_000093",
                "AssetVersion":
                    "CLIENT_CLASS_000094",
            },
        )

    def test_r23_names_do_not_overlap_prior_reviews(self):
        r23 = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r23.json"
        )
        r23_names = {
            row["proposed_name"]
            for row in r23["proposals"]
        }

        prior_names = set()
        for batch in range(2, 23):
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

        self.assertTrue(r23_names.isdisjoint(prior_names))


if __name__ == "__main__":
    unittest.main()
