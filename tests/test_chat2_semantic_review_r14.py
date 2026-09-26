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
    ("CLIENT_CLASS_000867", "rs/s/b/g"),
    ("CLIENT_CLASS_000883", "rs/s/b/w"),
    ("CLIENT_CLASS_000884", "rs/s/b/x"),
    ("CLIENT_CLASS_000925", "rs/s/k/a"),
    ("CLIENT_CLASS_000929", "rs/s/m/a"),
    ("CLIENT_CLASS_000930", "rs/s/m/b"),
    ("CLIENT_CLASS_000931", "rs/s/m/c"),
    ("CLIENT_CLASS_000932", "rs/s/m/d"),
    ("CLIENT_CLASS_000934", "rs/s/m/f"),
    ("CLIENT_CLASS_000937", "rs/s/n/c"),
    ("CLIENT_CLASS_000964", "rs/s/t/b"),
    ("CLIENT_CLASS_000966", "rs/s/t/d"),
    ("CLIENT_CLASS_000975", "rs/s/t/m"),
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
                                "source": "chat2-r14-fixture",
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


class Chat2SemanticReviewR14Tests(unittest.TestCase):
    def test_r14_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r14.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r14.json"
        )

        actual = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )

        self.assertEqual(actual["proposal_count"], 13)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(
            actual["review_id"],
            "SEMREVIEW_10B38C13D2C28216E473",
        )
        self.assertEqual(actual, expected)

    def test_r14_expected_stable_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r14.json"
        )
        by_name = {
            row["proposed_name"]: row
            for row in review["proposals"]
        }

        expected = {
            "ConfigurationPlugin": "CLIENT_CLASS_000867",
            "PluginConfigurationRootPanel": "CLIENT_CLASS_000883",
            "IntegerConfigFormatter": "CLIENT_CLASS_000884",
            "LoadoutsPlugin": "CLIENT_CLASS_000925",
            "NotesConfig": "CLIENT_CLASS_000929",
            "NotesPanel": "CLIENT_CLASS_000930",
            "NotesUndoAction": "CLIENT_CLASS_000931",
            "NotesRedoAction": "CLIENT_CLASS_000932",
            "NotesPlugin": "CLIENT_CLASS_000934",
            "DesktopNotificationService": "CLIENT_CLASS_000937",
            "TradingPostCurrency": "CLIENT_CLASS_000964",
            "TradingPostListingPanel": "CLIENT_CLASS_000966",
            "TradingPostSearchResultPanel": "CLIENT_CLASS_000975",
        }
        self.assertEqual(
            {
                name: row["stable_id"]
                for name, row in by_name.items()
            },
            expected,
        )

    def test_r14_names_do_not_overlap_prior_reviews(self):
        r14 = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r14.json"
        )
        r14_names = {
            row["proposed_name"]
            for row in r14["proposals"]
        }
        self.assertEqual(len(r14_names), 13)

        prior_names = set()
        for batch in range(2, 14):
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

        self.assertTrue(r14_names.isdisjoint(prior_names))


if __name__ == "__main__":
    unittest.main()
