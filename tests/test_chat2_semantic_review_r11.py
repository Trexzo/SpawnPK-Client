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
    ("CLIENT_CLASS_000393", "rs/l/d/c"),
    ("CLIENT_CLASS_000438", "rs/l/e/q"),
    ("CLIENT_CLASS_000439", "rs/l/e/q$a"),
    ("CLIENT_CLASS_000913", "rs/s/g"),
    ("CLIENT_CLASS_000974", "rs/s/t/l"),
    ("CLIENT_CLASS_001022", "rs/ui/a/f"),
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
                                "source": "chat2-r11-fixture",
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


class Chat2SemanticReviewR11Tests(unittest.TestCase):
    def test_infrastructure_batch_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r11.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r11.json"
        )

        actual = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )

        self.assertEqual(actual["proposal_count"], 6)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(
            actual["review_id"],
            "SEMREVIEW_688BC62BD168440903CD",
        )
        self.assertEqual(actual, expected)

    def test_infrastructure_batch_expected_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r11.json"
        )
        by_name = {
            row["proposed_name"]: row
            for row in review["proposals"]
        }

        expected = {
            "PluginManager": "CLIENT_CLASS_000913",
            "InfoBoxManager": "CLIENT_CLASS_001022",
            "TradingPostSearchPanel": "CLIENT_CLASS_000974",
            "LoginScreen": "CLIENT_CLASS_000393",
            "StatusTimer": "CLIENT_CLASS_000438",
            "StatusTimerType": "CLIENT_CLASS_000439",
        }
        for name, stable_id in expected.items():
            self.assertEqual(
                by_name[name]["stable_id"],
                stable_id,
            )

    def test_infrastructure_names_do_not_collide_with_prior_batches(self):
        prior_names = set()
        for suffix in (
            "r2", "r3", "r4", "r5", "r6",
            "r7", "r8", "r9", "r10",
        ):
            prior_names.update(
                row["proposed_name"]
                for row in _load(
                    "mappings/candidates/"
                    f"v308.semantic-review.chat2.{suffix}.json"
                )["proposals"]
            )

        current_names = {
            row["proposed_name"]
            for row in _load(
                "mappings/candidates/"
                "v308.semantic-review.chat2.r11.json"
            )["proposals"]
        }

        self.assertEqual(len(current_names), 6)
        self.assertTrue(prior_names.isdisjoint(current_names))


if __name__ == "__main__":
    unittest.main()
