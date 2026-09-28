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
    ("CLIENT_CLASS_000557", "rs/n/c/K"),
    ("CLIENT_CLASS_000609", "rs/n/c/ah"),
    ("CLIENT_CLASS_000562", "rs/n/c/P"),
    ("CLIENT_CLASS_000569", "rs/n/c/W"),
    ("CLIENT_CLASS_000972", "rs/s/t/j"),
    ("CLIENT_CLASS_000622", "rs/n/c/ar"),
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
                                "source": "chat2-r127-fixture",
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


class Chat2SemanticReviewR127Tests(unittest.TestCase):
    def test_r127_resolves_deterministically(self):
        candidates = _load("mappings/candidates/v308.semantic.chat2.r127.json")
        expected = _load("mappings/candidates/v308.semantic-review.chat2.r127.json")
        actual = resolve_semantic_candidates(
            _class_lineage(), _member_lineage(), candidates
        )
        self.assertEqual(actual["proposal_count"], 6)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(actual["review_id"], "SEMREVIEW_EC7BF9DFB04042D59C6D")
        self.assertEqual(actual, expected)

    def test_r127_expected_stable_ids(self):
        review = _load("mappings/candidates/v308.semantic-review.chat2.r127.json")
        self.assertEqual(
            {row["proposed_name"]: row["stable_id"] for row in review["proposals"]},
            {
                "EventActivityViewerInterfacePacketHandler": "CLIENT_CLASS_000557",
                "ItemsKeptOnDeathInterfacePacketHandler": "CLIENT_CLASS_000609",
                "ActiveEventsInterfacePacketHandler": "CLIENT_CLASS_000562",
                "GamblingInterfacePacketHandler": "CLIENT_CLASS_000569",
                "TradingPostPacketHandler": "CLIENT_CLASS_000972",
                "MakeQuantityInterfacePacketHandler": "CLIENT_CLASS_000622",
            },
        )

    def test_r127_name_and_owner_do_not_overlap_prior_reviews(self):
        current = _load("mappings/candidates/v308.semantic-review.chat2.r127.json")
        names = {row["proposed_name"] for row in current["proposals"]}
        owners = {row["source_coordinate"]["owner"] for row in current["proposals"]}

        prior_names = set()
        prior_owners = set()
        for batch in range(2, 127):
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
