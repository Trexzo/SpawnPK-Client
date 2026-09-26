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
    ("CLIENT_CLASS_000002", "rs/A/a"),
    ("CLIENT_CLASS_000003", "rs/A/a$a"),
    ("CLIENT_CLASS_000004", "rs/A/a$b"),
    ("CLIENT_CLASS_000530", "rs/n/a/a/d"),
    ("CLIENT_CLASS_000832", "rs/runelite/a/p"),
    ("CLIENT_CLASS_000891", "rs/s/c/e"),
    ("CLIENT_CLASS_000892", "rs/s/c/e$a"),
    ("CLIENT_CLASS_000907", "rs/s/f/a"),
    ("CLIENT_CLASS_000912", "rs/s/f/f"),
    ("CLIENT_CLASS_001018", "rs/ui/a/b"),
    ("CLIENT_CLASS_001025", "rs/ui/a/i"),
    ("CLIENT_CLASS_001103", "rs/ui/l$a"),
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
                                "source": "chat2-r19-fixture",
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


class Chat2SemanticReviewR19Tests(unittest.TestCase):
    def test_r19_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r19.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r19.json"
        )

        actual = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )

        self.assertEqual(actual["proposal_count"], 12)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(
            actual["review_id"],
            "SEMREVIEW_402B4C2AA42205916457",
        )
        self.assertEqual(actual, expected)

    def test_r19_expected_stable_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r19.json"
        )
        by_name = {
            row["proposed_name"]: row["stable_id"]
            for row in review["proposals"]
        }
        self.assertEqual(
            by_name,
            {
                "AssetIconManager": "CLIENT_CLASS_000002",
                "AssetIconItemKey": "CLIENT_CLASS_000003",
                "AssetIconSpriteKey": "CLIENT_CLASS_000004",
                "DropDownOption": "CLIENT_CLASS_000530",
                "WorldPoint": "CLIENT_CLASS_000832",
                "DevToolsWidgetOverlay": "CLIENT_CLASS_000891",
                "DevToolsWidgetDisplay": "CLIENT_CLASS_000892",
                "ColorTileMarker": "CLIENT_CLASS_000907",
                "GroundMarkerPoint": "CLIENT_CLASS_000912",
                "CounterInfoBox": "CLIENT_CLASS_001018",
                "StatusInfoBox": "CLIENT_CLASS_001025",
                "NavigationButtonBuilder": "CLIENT_CLASS_001103",
            },
        )

    def test_r19_names_do_not_overlap_prior_reviews(self):
        r19 = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r19.json"
        )
        r19_names = {
            row["proposed_name"]
            for row in r19["proposals"]
        }

        prior_names = set()
        for batch in range(2, 19):
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

        self.assertTrue(r19_names.isdisjoint(prior_names))


if __name__ == "__main__":
    unittest.main()
