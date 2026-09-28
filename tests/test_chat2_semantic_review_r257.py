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
    ("CLIENT_CLASS_001039", "rs/ui/components/a/b"),
    ("CLIENT_CLASS_001040", "rs/ui/components/a/c"),
    ("CLIENT_CLASS_001043", "rs/ui/components/a/f"),
    ("CLIENT_CLASS_001044", "rs/ui/components/a/g"),
    ("CLIENT_CLASS_001046", "rs/ui/components/a/i"),
    ("CLIENT_CLASS_001047", "rs/ui/components/a/j"),
    ("CLIENT_CLASS_001049", "rs/ui/components/a/l"),
    ("CLIENT_CLASS_001050", "rs/ui/components/a/m"),
    ("CLIENT_CLASS_001053", "rs/ui/components/a/p"),
    ("CLIENT_CLASS_001055", "rs/ui/components/a/r"),
    ("CLIENT_CLASS_001056", "rs/ui/components/a/s"),
    ("CLIENT_CLASS_001057", "rs/ui/components/a/t"),
    ("CLIENT_CLASS_001058", "rs/ui/components/a/u"),
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
                "provenance": [{"authority": "EXACT_CURRENT_CLIENT", "source": "chat2-r257-fixture"}],
            }],
            "semantic_provenance": [],
        })
    return {
        "schema_version": 1,
        "namespace": "spawnpk-client",
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": "v308",
        "builds": [{"build_id": "v308","build_number": 308,"sha256": SHA,"source_name": "client(6).jar","authority": "EXACT_CURRENT_CLIENT"}],
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


class Chat2SemanticReviewR257Tests(unittest.TestCase):
    def test_r257_resolves_deterministically(self):
        candidates = _load("mappings/candidates/v308.semantic.chat2.r257.json")
        expected = _load("mappings/candidates/v308.semantic-review.chat2.r257.json")
        actual = resolve_semantic_candidates(_class_lineage(), _member_lineage(), candidates)
        self.assertEqual(actual["proposal_count"], 13)
        self.assertEqual(actual["unresolved"], [])
        self.assertEqual(actual["review_id"], "SEMREVIEW_B852479D96D12B5DCBE2")
        self.assertEqual(actual, expected)

    def test_r257_expected_stable_ids(self):
        review = _load("mappings/candidates/v308.semantic-review.chat2.r257.json")
        self.assertEqual(
            {row["proposed_name"]: row["stable_id"] for row in review["proposals"]},
            {
                "ColorPanelDragListener": "CLIENT_CLASS_001039",
                "ColorPanelMouseListener": "CLIENT_CLASS_001040",
                "ColorValueDocumentFilter": "CLIENT_CLASS_001043",
                "ColorValueFocusListener": "CLIENT_CLASS_001044",
                "ColorValueSliderDragListener": "CLIENT_CLASS_001046",
                "ColorValueSliderMouseListener": "CLIENT_CLASS_001047",
                "HuePanelDragListener": "CLIENT_CLASS_001049",
                "HuePanelMouseListener": "CLIENT_CLASS_001050",
                "RecentColorClickListener": "CLIENT_CLASS_001053",
                "PreviewColorSelectListener": "CLIENT_CLASS_001055",
                "HexColorDocumentFilter": "CLIENT_CLASS_001056",
                "ColorPickerFocusListener": "CLIENT_CLASS_001057",
                "ColorPickerWindowCloseListener": "CLIENT_CLASS_001058",
            },
        )

    def test_r257_names_and_owners_do_not_overlap_prior_reviews(self):
        current = _load("mappings/candidates/v308.semantic-review.chat2.r257.json")
        names = {row["proposed_name"] for row in current["proposals"]}
        owners = {row["source_coordinate"]["owner"] for row in current["proposals"]}
        prior_names = set()
        prior_owners = set()
        for batch in range(2, 257):
            path = ROOT / "mappings" / "candidates" / f"v308.semantic-review.chat2.r{batch}.json"
            if not path.is_file():
                continue
            prior = json.loads(path.read_text(encoding="utf-8"))
            prior_names.update(row["proposed_name"] for row in prior["proposals"])
            prior_owners.update(row["source_coordinate"]["owner"] for row in prior["proposals"] if row["target_kind"] == "class")
        self.assertTrue(names.isdisjoint(prior_names))
        self.assertTrue(owners.isdisjoint(prior_owners))


if __name__ == "__main__":
    unittest.main()
