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
    ("CLIENT_CLASS_000203", "rs/gui/a/a"),
    ("CLIENT_CLASS_000903", "rs/s/e/d"),
    ("CLIENT_CLASS_000908", "rs/s/f/b"),
    ("CLIENT_CLASS_000910", "rs/s/f/d"),
    ("CLIENT_CLASS_000927", "rs/s/l/b"),
    ("CLIENT_CLASS_000928", "rs/s/l/c"),
    ("CLIENT_CLASS_000935", "rs/s/n/a"),
    ("CLIENT_CLASS_000936", "rs/s/n/b"),
    ("CLIENT_CLASS_000945", "rs/s/o/e"),
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
                                "source": "chat2-r9-fixture",
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


class Chat2SemanticReviewR9Tests(unittest.TestCase):
    def test_plugin_batch_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r9.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r9.json"
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
            "SEMREVIEW_45033AF6496AE782988D",
        )
        self.assertEqual(actual, expected)

    def test_plugin_batch_expected_pair_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r9.json"
        )
        by_name = {
            row["proposed_name"]: row
            for row in review["proposals"]
        }

        expected = {
            "GroundMarkersConfig": "CLIENT_CLASS_000908",
            "GroundMarkersPlugin": "CLIENT_CLASS_000910",
            "MenuEntrySwapperConfig": "CLIENT_CLASS_000927",
            "MenuEntrySwapperPlugin": "CLIENT_CLASS_000928",
            "NotificationAlertsConfig": "CLIENT_CLASS_000935",
            "NotificationAlertsPlugin": "CLIENT_CLASS_000936",
            "NpcIndicatorsPlugin": "CLIENT_CLASS_000945",
            "GpuConfig": "CLIENT_CLASS_000903",
            "GpuSettingsPanel": "CLIENT_CLASS_000203",
        }
        for name, stable_id in expected.items():
            self.assertEqual(
                by_name[name]["stable_id"],
                stable_id,
            )

    def test_plugin_batch_names_do_not_collide_with_prior_batches(self):
        prior_names = set()
        for suffix in (
            "r2", "r3", "r4", "r5",
            "r6", "r7", "r8",
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
                "v308.semantic-review.chat2.r9.json"
            )["proposals"]
        }

        self.assertEqual(len(current_names), 9)
        self.assertTrue(prior_names.isdisjoint(current_names))


if __name__ == "__main__":
    unittest.main()
