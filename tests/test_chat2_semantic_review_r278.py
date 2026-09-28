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
    ("CLIENT_CLASS_000215", "rs/gui/b/a/f"),
    ("CLIENT_CLASS_000216", "rs/gui/b/a/g"),
    ("CLIENT_CLASS_000217", "rs/gui/b/a/h"),
    ("CLIENT_CLASS_000218", "rs/gui/b/a/i"),
    ("CLIENT_CLASS_000219", "rs/gui/b/a/j"),
    ("CLIENT_CLASS_000220", "rs/gui/b/a/k"),
    ("CLIENT_CLASS_000221", "rs/gui/b/a/l"),
    ("CLIENT_CLASS_000222", "rs/gui/b/a/m"),
    ("CLIENT_CLASS_000235", "rs/gui/b/a/z"),
]


def _class_lineage():
    classes = []
    for logical_id, internal_name in CLASS_COORDS:
        classes.append({
            "logical_id": logical_id,
            "semantic_name": None,
            "semantic_status": "UNKNOWN",
            "semantic_confidence": 0.0,
            "lineage": [{
                "build_id": "v308",
                "internal_name": internal_name,
                "entry_path": internal_name + ".class",
                "entry_sha256": "b" * 64,
                "structural_sha256": "c" * 64,
                "relation": "BASELINE",
                "confidence": 1.0,
                "provenance": [{
                    "authority": "EXACT_CURRENT_CLIENT",
                    "source": "chat2-r278-fixture",
                }],
            }],
            "semantic_provenance": [],
        })
    return {
        "schema_version": 1,
        "namespace": "spawnpk-client",
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": "v308",
        "builds": [{
            "build_id": "v308",
            "build_number": 308,
            "sha256": SHA,
            "source_name": "client(6).jar",
            "authority": "EXACT_CURRENT_CLIENT",
        }],
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


class Chat2SemanticReviewR278Tests(unittest.TestCase):
    def test_r278_resolves_deterministically(self):
        candidates = _load("mappings/candidates/v308.semantic.chat2.r278.json")
        expected = _load("mappings/candidates/v308.semantic-review.chat2.r278.json")
        actual = resolve_semantic_candidates(
            _class_lineage(), _member_lineage(), candidates
        )
        self.assertEqual(actual["proposal_count"], 9)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(actual["review_id"], "SEMREVIEW_6802ABD5B5A7B7C30CF7")
        self.assertEqual(actual, expected)

    def test_r278_expected_stable_ids(self):
        review = _load("mappings/candidates/v308.semantic-review.chat2.r278.json")
        self.assertEqual(
            {row["proposed_name"]: row["stable_id"] for row in review["proposals"]},
            {
                "LoadoutSelectionListCellRenderer": "CLIENT_CLASS_000215",
                "CreateLoadoutButton": "CLIENT_CLASS_000216",
                "OpenCreateLoadoutAction": "CLIENT_CLASS_000217",
                "CreateLoadoutAction": "CLIENT_CLASS_000218",
                "LoadoutIconListCellRenderer": "CLIENT_CLASS_000219",
                "LoadoutSelectionComboBox": "CLIENT_CLASS_000220",
                "LoadoutSelectionPopupListener": "CLIENT_CLASS_000221",
                "LoadoutSelectionAction": "CLIENT_CLASS_000222",
                "LoadoutPropertiesCloseAction": "CLIENT_CLASS_000235",
            },
        )

    def test_r278_names_and_owners_do_not_overlap_any_prior_review(self):
        current = _load("mappings/candidates/v308.semantic-review.chat2.r278.json")
        names = {row["proposed_name"] for row in current["proposals"]}
        owners = {row["source_coordinate"]["owner"] for row in current["proposals"]}
        prior_names = set()
        prior_owners = set()
        for batch in range(2, 278):
            path = (
                ROOT / "mappings" / "candidates"
                / f"v308.semantic-review.chat2.r{batch}.json"
            )
            if not path.is_file():
                continue
            prior = json.loads(path.read_text(encoding="utf-8"))
            prior_names.update(
                row["proposed_name"] for row in prior["proposals"]
                if row["target_kind"] == "class"
            )
            prior_owners.update(
                row["source_coordinate"]["owner"]
                for row in prior["proposals"]
                if row["target_kind"] == "class"
            )
        self.assertTrue(names.isdisjoint(prior_names))
        self.assertTrue(owners.isdisjoint(prior_owners))


if __name__ == "__main__":
    unittest.main()
