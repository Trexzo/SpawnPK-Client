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
    ("CLIENT_CLASS_000145", "rs/e/a"),
    ("CLIENT_CLASS_000146", "rs/e/b"),
    ("CLIENT_CLASS_000148", "rs/e/d"),
    ("CLIENT_CLASS_000149", "rs/e/e"),
    ("CLIENT_CLASS_000150", "rs/e/f"),
    ("CLIENT_CLASS_000151", "rs/e/g"),
    ("CLIENT_CLASS_000153", "rs/e/i"),
    ("CLIENT_CLASS_000154", "rs/e/j"),
    ("CLIENT_CLASS_000156", "rs/e/l"),
    ("CLIENT_CLASS_000158", "rs/e/n"),
    ("CLIENT_CLASS_000159", "rs/e/o"),
    ("CLIENT_CLASS_000160", "rs/e/p"),
    ("CLIENT_CLASS_000161", "rs/e/q"),
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
                                "source": "chat2-r16-fixture",
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


class Chat2SemanticReviewR16Tests(unittest.TestCase):
    def test_r16_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r16.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r16.json"
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
            "SEMREVIEW_EA07D515D935757E2910",
        )
        self.assertEqual(actual, expected)

    def test_r16_expected_stable_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r16.json"
        )
        by_name = {
            row["proposed_name"]: row["stable_id"]
            for row in review["proposals"]
        }
        self.assertEqual(
            by_name,
            {
                "Alpha": "CLIENT_CLASS_000145",
                "Config": "CLIENT_CLASS_000146",
                "ConfigDescriptor": "CLIENT_CLASS_000148",
                "ConfigGroup": "CLIENT_CLASS_000149",
                "ConfigInvocationHandler": "CLIENT_CLASS_000150",
                "ConfigItem": "CLIENT_CLASS_000151",
                "ConfigManager": "CLIENT_CLASS_000153",
                "ConfigObject": "CLIENT_CLASS_000154",
                "ConfigSection": "CLIENT_CLASS_000156",
                "FlashNotification": "CLIENT_CLASS_000158",
                "Range": "CLIENT_CLASS_000159",
                "RequestFocusType": "CLIENT_CLASS_000160",
                "Units": "CLIENT_CLASS_000161",
            },
        )

    def test_r16_names_do_not_overlap_prior_reviews(self):
        r16 = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r16.json"
        )
        r16_names = {
            row["proposed_name"]
            for row in r16["proposals"]
        }

        prior_names = set()
        for batch in range(2, 16):
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

        self.assertTrue(r16_names.isdisjoint(prior_names))


if __name__ == "__main__":
    unittest.main()
