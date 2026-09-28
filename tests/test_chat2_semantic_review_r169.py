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
    ("CLIENT_CLASS_000835", "rs/runelite/events/ChatMessage"),
    ("CLIENT_CLASS_000836", "rs/runelite/events/ClientShutdown"),
    ("CLIENT_CLASS_000837", "rs/runelite/events/ClientStartUp"),
    ("CLIENT_CLASS_000838", "rs/runelite/events/ConfigChanged"),
    ("CLIENT_CLASS_000839", "rs/runelite/events/EntityInteraction"),
    ("CLIENT_CLASS_000840", "rs/runelite/events/FocusChanged"),
    ("CLIENT_CLASS_000841", "rs/runelite/events/GameStateChanged"),
    ("CLIENT_CLASS_000842", "rs/runelite/events/MenuBuild"),
    ("CLIENT_CLASS_000843", "rs/runelite/events/MenuHover"),
    ("CLIENT_CLASS_000844", "rs/runelite/events/MenuOpened"),
    ("CLIENT_CLASS_000845", "rs/runelite/events/NavigationButtonAdded"),
    ("CLIENT_CLASS_000846", "rs/runelite/events/NavigationButtonRemoved"),
    ("CLIENT_CLASS_000847", "rs/runelite/events/NotificationFired"),
    ("CLIENT_CLASS_000848", "rs/runelite/events/NpcSpawned"),
    ("CLIENT_CLASS_000849", "rs/runelite/events/ObjectInteraction"),
    ("CLIENT_CLASS_000850", "rs/runelite/events/PluginChanged"),
    ("CLIENT_CLASS_000851", "rs/runelite/events/PrivateChatMessage"),
    ("CLIENT_CLASS_000852", "rs/runelite/events/SkillLevelChanged"),
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
                                "source": "chat2-r169-fixture",
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


class Chat2SemanticReviewR169Tests(unittest.TestCase):
    def test_r169_resolves_deterministically(self):
        candidates = _load("mappings/candidates/v308.semantic.chat2.r169.json")
        expected = _load("mappings/candidates/v308.semantic-review.chat2.r169.json")
        actual = resolve_semantic_candidates(_class_lineage(), _member_lineage(), candidates)
        self.assertEqual(actual["proposal_count"], 18)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(actual["review_id"], "SEMREVIEW_8BF377A25B58438FF825")
        self.assertEqual(actual, expected)

    def test_r169_expected_contiguous_event_api(self):
        review = _load("mappings/candidates/v308.semantic-review.chat2.r169.json")
        expected = dict(CLASS_COORDS)
        actual = {row["stable_id"]: row["source_coordinate"]["owner"] for row in review["proposals"]}
        self.assertEqual(actual, expected)
        self.assertTrue(all(row["confidence"] == 1.0 for row in review["proposals"]))

    def test_r169_name_and_owner_do_not_overlap_prior_reviews(self):
        current = _load("mappings/candidates/v308.semantic-review.chat2.r169.json")
        names = {row["proposed_name"] for row in current["proposals"]}
        owners = {row["source_coordinate"]["owner"] for row in current["proposals"]}

        prior_names = set()
        prior_owners = set()
        for batch in range(2, 169):
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
