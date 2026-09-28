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
    ("CLIENT_CLASS_000007", "rs/A/d"),
    ("CLIENT_CLASS_000008", "rs/A/e"),
    ("CLIENT_CLASS_000010", "rs/A/g"),
    ("CLIENT_CLASS_000011", "rs/A/h"),
    ("CLIENT_CLASS_000012", "rs/A/i"),
    ("CLIENT_CLASS_000013", "rs/A/j"),
    ("CLIENT_CLASS_000015", "rs/A/l"),
    ("CLIENT_CLASS_000016", "rs/A/m"),
    ("CLIENT_CLASS_000019", "rs/A/p"),
    ("CLIENT_CLASS_000020", "rs/A/q"),
    ("CLIENT_CLASS_000021", "rs/A/q$a"),
    ("CLIENT_CLASS_000022", "rs/A/q$b"),
    ("CLIENT_CLASS_000023", "rs/A/r"),
    ("CLIENT_CLASS_000024", "rs/A/s"),
    ("CLIENT_CLASS_000025", "rs/A/t"),
    ("CLIENT_CLASS_000026", "rs/A/u"),
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
                                "source": "chat2-r20-fixture",
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


class Chat2SemanticReviewR20Tests(unittest.TestCase):
    def test_r20_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r20.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r20.json"
        )

        actual = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )

        self.assertEqual(actual["proposal_count"], 16)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(
            actual["review_id"],
            "SEMREVIEW_E6BE3592C064143A3007",
        )
        self.assertEqual(actual, expected)

    def test_r20_expected_stable_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r20.json"
        )
        by_name = {
            row["proposed_name"]: row["stable_id"]
            for row in review["proposals"]
        }
        self.assertEqual(
            by_name,
            {
                "AsyncBufferedImage": "CLIENT_CLASS_000007",
                "CallableExceptionLogger": "CLIENT_CLASS_000008",
                "ColorUtil": "CLIENT_CLASS_000010",
                "ExecutorServiceExceptionLogger": "CLIENT_CLASS_000011",
                "HotkeyListener": "CLIENT_CLASS_000012",
                "ImageUtil": "CLIENT_CLASS_000013",
                "LinkBrowser": "CLIENT_CLASS_000015",
                "MacOSPopupFactory": "CLIENT_CLASS_000016",
                "QuantityFormatter": "CLIENT_CLASS_000019",
                "ReflectUtil": "CLIENT_CLASS_000020",
                "ReflectUtilPrivateLookupHelper": "CLIENT_CLASS_000021",
                "ReflectUtilPrivateLookupableClassLoader": "CLIENT_CLASS_000022",
                "RunnableExceptionLogger": "CLIENT_CLASS_000023",
                "Text": "CLIENT_CLASS_000024",
                "WildcardMatcher": "CLIENT_CLASS_000025",
                "WinUtil": "CLIENT_CLASS_000026",
            },
        )

    def test_r20_names_do_not_overlap_prior_reviews(self):
        r20 = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r20.json"
        )
        r20_names = {
            row["proposed_name"]
            for row in r20["proposals"]
        }

        prior_names = set()
        for batch in range(2, 20):
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

        self.assertTrue(r20_names.isdisjoint(prior_names))


if __name__ == "__main__":
    unittest.main()
