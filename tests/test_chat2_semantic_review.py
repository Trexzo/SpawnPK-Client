import json
from pathlib import Path
import unittest

from spk_recovery.semantic_review import (
    resolve_semantic_candidates,
)


SHA = (
    "854f26ff9f134b0317572e7ac1688e6f"
    "40a231d5a4c66f8db5d655b7f45ce7c6"
)
ROOT = Path(__file__).resolve().parents[1]


CLASS_COORDS = [
    ("CLIENT_CLASS_000029", "rs/Client"),
    ("CLIENT_CLASS_000297", "rs/i/b"),
    ("CLIENT_CLASS_000552", "rs/n/c/G"),
    ("CLIENT_CLASS_000561", "rs/n/c/O"),
    ("CLIENT_CLASS_000567", "rs/n/c/U"),
    ("CLIENT_CLASS_000568", "rs/n/c/V"),
    ("CLIENT_CLASS_000573", "rs/n/c/a"),
    ("CLIENT_CLASS_000578", "rs/n/c/aC"),
    ("CLIENT_CLASS_000579", "rs/n/c/aD"),
    ("CLIENT_CLASS_000582", "rs/n/c/aG"),
    ("CLIENT_CLASS_000583", "rs/n/c/aH"),
    ("CLIENT_CLASS_000584", "rs/n/c/aI"),
    ("CLIENT_CLASS_000587", "rs/n/c/aL"),
    ("CLIENT_CLASS_000599", "rs/n/c/aX"),
    ("CLIENT_CLASS_000600", "rs/n/c/aY"),
    ("CLIENT_CLASS_000603", "rs/n/c/ab"),
    ("CLIENT_CLASS_000605", "rs/n/c/ad"),
    ("CLIENT_CLASS_000614", "rs/n/c/am"),
    ("CLIENT_CLASS_000617", "rs/n/c/ap"),
    ("CLIENT_CLASS_000626", "rs/n/c/av"),
    ("CLIENT_CLASS_000627", "rs/n/c/aw"),
    ("CLIENT_CLASS_000632", "rs/n/c/b"),
    ("CLIENT_CLASS_000640", "rs/n/c/c"),
    ("CLIENT_CLASS_000643", "rs/n/c/c/a"),
    ("CLIENT_CLASS_000661", "rs/n/c/h"),
    ("CLIENT_CLASS_000662", "rs/n/c/i"),
    ("CLIENT_CLASS_000665", "rs/n/c/l"),
    ("CLIENT_CLASS_000666", "rs/n/c/m"),
    ("CLIENT_CLASS_000668", "rs/n/c/o"),
    ("CLIENT_CLASS_000669", "rs/n/c/p"),
    ("CLIENT_CLASS_000672", "rs/n/c/s"),
    ("CLIENT_CLASS_000675", "rs/n/c/v"),
    ("CLIENT_CLASS_000679", "rs/n/c/z"),
]

MEMBER_COORDS = [
    (
        "CLIENT_FIELD_000156",
        "CLIENT_CLASS_000029",
        "field",
        "rs/Client",
        "P",
        "I",
    ),
    (
        "CLIENT_METHOD_000298",
        "CLIENT_CLASS_000029",
        "method",
        "rs/Client",
        "a",
        "(J)V",
    ),
    (
        "CLIENT_METHOD_000473",
        "CLIENT_CLASS_000029",
        "method",
        "rs/Client",
        "f",
        "(J)V",
    ),
    (
        "CLIENT_METHOD_000491",
        "CLIENT_CLASS_000029",
        "method",
        "rs/Client",
        "h",
        "(J)V",
    ),
    (
        "CLIENT_METHOD_000498",
        "CLIENT_CLASS_000029",
        "method",
        "rs/Client",
        "i",
        "(J)V",
    ),
    (
        "CLIENT_FIELD_002923",
        "CLIENT_CLASS_000297",
        "field",
        "rs/i/b",
        "f",
        "Lrs/l/F;",
    ),
    (
        "CLIENT_FIELD_002924",
        "CLIENT_CLASS_000297",
        "field",
        "rs/i/b",
        "g",
        "Lrs/l/F;",
    ),
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
                                "source": "chat2-r2c2-fixture",
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
    members = []
    for (
        member_id,
        owner_id,
        kind,
        owner,
        name,
        descriptor,
    ) in MEMBER_COORDS:
        entry = {
            "build_id": "v308",
            "owner_internal_name": owner,
            "name": name,
            "descriptor": descriptor,
            "access": 1,
            "relation": "BASELINE",
            "confidence": 1.0,
            "provenance": [],
        }
        if kind == "method":
            entry["code_length"] = 1
        members.append(
            {
                "member_id": member_id,
                "owner_logical_id": owner_id,
                "kind": kind,
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [entry],
                "semantic_provenance": [],
            }
        )
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": SHA,
        "members": members,
        "unresolved": [],
    }


def _load(relative):
    return json.loads(
        (ROOT / relative).read_text(encoding="utf-8")
    )


class Chat2SemanticReviewIntegrationTests(unittest.TestCase):
    def test_exact_v308_candidates_resolve_through_r2c2(self):
        candidates = _load(
            "mappings/candidates/"
            "v308.semantic.chat2.r2.json"
        )
        expected = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r2.json"
        )

        actual = resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            candidates,
        )

        self.assertEqual(actual["proposal_count"], 39)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(
            actual["review_id"],
            "SEMREVIEW_DD69CD752A6E46181BAC",
        )
        self.assertEqual(actual, expected)

    def test_resolved_review_uses_canonical_r2c_ids(self):
        review = _load(
            "mappings/candidates/"
            "v308.semantic-review.chat2.r2.json"
        )
        by_name = {
            row["proposed_name"]: row
            for row in review["proposals"]
        }

        self.assertEqual(
            by_name["addFriend"]["stable_id"],
            "CLIENT_METHOD_000298",
        )
        self.assertEqual(
            by_name["loginRewardContainerIndex"][
                "stable_id"
            ],
            "CLIENT_FIELD_000156",
        )
        self.assertEqual(
            by_name["AdventureOrbRenderer"]["stable_id"],
            "CLIENT_CLASS_000297",
        )


if __name__ == "__main__":
    unittest.main()
