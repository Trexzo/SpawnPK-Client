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
    ("CLIENT_CLASS_001028", "rs/ui/b/a"),
    ("CLIENT_CLASS_001029", "rs/ui/b/b"),
    ("CLIENT_CLASS_001030", "rs/ui/b/b$a"),
    ("CLIENT_CLASS_001031", "rs/ui/b/b$b"),
]


def _class_lineage():
    classes=[]
    for logical_id, internal_name in CLASS_COORDS:
        classes.append({
            "logical_id":logical_id,
            "semantic_name":None,
            "semantic_status":"UNKNOWN",
            "semantic_confidence":0.0,
            "lineage":[{
                "build_id":"v308",
                "internal_name":internal_name,
                "entry_path":internal_name + ".class",
                "entry_sha256":"b"*64,
                "structural_sha256":"c"*64,
                "relation":"BASELINE",
                "confidence":1.0,
                "provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r231-fixture"}],
            }],
            "semantic_provenance":[],
        })
    return {
        "schema_version":1,
        "namespace":"spawnpk-client",
        "id_format":"CLIENT_CLASS_%06d",
        "baseline_build_id":"v308",
        "builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],
        "classes":classes,
        "unresolved":[],
    }


def _member_lineage():
    return {
        "schema_version":1,
        "kind":"member_lineage",
        "class_namespace":"spawnpk-client",
        "baseline_build_id":"v308",
        "source_sha256":SHA,
        "members":[],
        "unresolved":[],
    }


def _load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class Chat2SemanticReviewR231Tests(unittest.TestCase):
    def test_r231_resolves_deterministically(self):
        actual=resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            _load("mappings/candidates/v308.semantic.chat2.r231.json"),
        )
        expected=_load("mappings/candidates/v308.semantic-review.chat2.r231.json")
        self.assertEqual(actual["proposal_count"],4)
        self.assertEqual(actual["unresolved"],[])
        self.assertEqual(actual["review_id"],"SEMREVIEW_0E29D2E6D57B3D6291EE")
        self.assertEqual(actual,expected)

    def test_r231_expected_stable_ids(self):
        review=_load("mappings/candidates/v308.semantic-review.chat2.r231.json")
        self.assertEqual(
            {row["proposed_name"]:row["stable_id"] for row in review["proposals"]},
            {
                "IntBlockBuffer":"CLIENT_CLASS_001028",
                "ModelOutlineRenderer":"CLIENT_CLASS_001029",
                "PixelDistanceDelta":"CLIENT_CLASS_001030",
                "PixelDistanceGroupIndex":"CLIENT_CLASS_001031",
            },
        )

    def test_r231_name_and_owner_do_not_overlap_prior_reviews(self):
        current=_load("mappings/candidates/v308.semantic-review.chat2.r231.json")
        names={r["proposed_name"] for r in current["proposals"]}
        owners={r["source_coordinate"]["owner"] for r in current["proposals"]}
        prior_names=set(); prior_owners=set()
        for batch in range(2,231):
            path=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{batch}.json"
            if not path.is_file(): continue
            prior=json.loads(path.read_text(encoding="utf-8"))
            prior_names.update(r["proposed_name"] for r in prior["proposals"])
            prior_owners.update(r["source_coordinate"]["owner"] for r in prior["proposals"] if r["target_kind"]=="class")
        self.assertTrue(names.isdisjoint(prior_names))
        self.assertTrue(owners.isdisjoint(prior_owners))


if __name__=="__main__":
    unittest.main()
