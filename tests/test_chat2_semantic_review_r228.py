import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates

SHA=("854f26ff9f134b0317572e7ac1688e6f"
     "40a231d5a4c66f8db5d655b7f45ce7c6")
ROOT=Path(__file__).resolve().parents[1]
CLASS_COORDS=[
    ("CLIENT_CLASS_001020", "rs/ui/a/d"),
    ("CLIENT_CLASS_001059", "rs/ui/components/b"),
    ("CLIENT_CLASS_001068", "rs/ui/components/f"),
    ("CLIENT_CLASS_001074", "rs/ui/components/i"),
    ("CLIENT_CLASS_001084", "rs/ui/components/r"),
    ("CLIENT_CLASS_001089", "rs/ui/components/u"),
    ("CLIENT_CLASS_001090", "rs/ui/components/v"),
]

def _class_lineage():
    classes=[]
    for logical_id, internal_name in CLASS_COORDS:
        classes.append({"logical_id":logical_id,"semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,
            "lineage":[{"build_id":"v308","internal_name":internal_name,"entry_path":internal_name+".class",
                        "entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,
                        "provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r228-fixture"}]}],
            "semantic_provenance":[]})
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308",
            "builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],
            "classes":classes,"unresolved":[]}

def _member_lineage():
    return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client",
            "baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}

def _load(relative):
    return json.loads((ROOT/relative).read_text(encoding="utf-8"))

class Chat2SemanticReviewR228Tests(unittest.TestCase):
    def test_r228_resolves_deterministically(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r228.json"))
        expected=_load("mappings/candidates/v308.semantic-review.chat2.r228.json")
        self.assertEqual(actual["proposal_count"],7)
        self.assertEqual(actual["unresolved"],[])
        self.assertEqual(actual["review_id"],"SEMREVIEW_C1EFA86377CACA7467C3")
        self.assertEqual(actual,expected)

    def test_r228_expected_stable_ids(self):
        review=_load("mappings/candidates/v308.semantic-review.chat2.r228.json")
        self.assertEqual({r["proposed_name"]:r["stable_id"] for r in review["proposals"]},{"InfoBoxComponent": "CLIENT_CLASS_001020", "ColorJButton": "CLIENT_CLASS_001059", "DimmableJPanel": "CLIENT_CLASS_001068", "FlatTextField": "CLIENT_CLASS_001074", "MouseDragEventForwarder": "CLIENT_CLASS_001084", "PluginErrorPanel": "CLIENT_CLASS_001089", "ProgressBar": "CLIENT_CLASS_001090"})

    def test_r228_name_and_owner_do_not_overlap_prior_reviews(self):
        current=_load("mappings/candidates/v308.semantic-review.chat2.r228.json")
        names={r["proposed_name"] for r in current["proposals"]}
        owners={r["source_coordinate"]["owner"] for r in current["proposals"]}
        prior_names=set(); prior_owners=set()
        for batch in range(2,228):
            path=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{batch}.json"
            if not path.is_file(): continue
            prior=json.loads(path.read_text(encoding="utf-8"))
            prior_names.update(r["proposed_name"] for r in prior["proposals"])
            prior_owners.update(r["source_coordinate"]["owner"] for r in prior["proposals"] if r["target_kind"]=="class")
        self.assertTrue(names.isdisjoint(prior_names))
        self.assertTrue(owners.isdisjoint(prior_owners))

    def test_r228_r166_correction_is_present(self):
        r166=_load("mappings/candidates/v308.semantic-review.chat2.r166.json")
        self.assertEqual(r166["review_id"],"SEMREVIEW_9C381CF759C8D9528363")
        self.assertEqual(r166["proposals"][0]["proposal_id"],"SEMPROP_8C18220DA038113C69E2")
        self.assertEqual(r166["proposals"][0]["proposed_name"],"ThinProgressBar")

if __name__=="__main__":
    unittest.main()
