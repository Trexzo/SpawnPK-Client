import json
from pathlib import Path
import unittest

from spk_recovery.semantic_review import resolve_semantic_candidates


SHA = (
    "854f26ff9f134b0317572e7ac1688e6f"
    "40a231d5a4c66f8db5d655b7f45ce7c6"
)
ROOT = Path(__file__).resolve().parents[1]


def _class_lineage():
    rows = [
        ("CLIENT_CLASS_000571", "rs/n/c/Y"),
        ("CLIENT_CLASS_000602", "rs/n/c/aa"),
    ]
    classes = []
    for logical_id, internal_name in rows:
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
                                "source": "chat2-r8-fixture",
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


class Chat2SemanticReviewR8Tests(unittest.TestCase):
    def test_gameframe_batch_resolves_deterministically(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r8.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r8.json"
        )

        actual = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )

        self.assertEqual(actual["proposal_count"], 2)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(
            actual["review_id"],
            "SEMREVIEW_EEC5926DB7B003A5F9CE",
        )
        self.assertEqual(actual, expected)

    def test_gameframe_exact_root_join_is_bound_to_stable_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r8.json"
        )
        by_name = {
            row["proposed_name"]: row
            for row in review["proposals"]
        }

        self.assertEqual(
            by_name["GameframeNavigationInterface"]["stable_id"],
            "CLIENT_CLASS_000571",
        )
        self.assertEqual(
            by_name["AccountInformationInterface"]["stable_id"],
            "CLIENT_CLASS_000602",
        )

    def test_gameframe_batch_names_do_not_collide_with_prior_batches(self):
        prior_names = set()
        for suffix in ("r2", "r3", "r4", "r5", "r6", "r7"):
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
                "v308.semantic-review.chat2.r8.json"
            )["proposals"]
        }

        self.assertEqual(len(current_names), 2)
        self.assertTrue(prior_names.isdisjoint(current_names))


if __name__ == "__main__":
    unittest.main()
