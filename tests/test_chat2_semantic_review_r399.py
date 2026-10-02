import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates

SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]
CLASS_COORDS=[["CLIENT_CLASS_000145","rs/e/a"],["CLIENT_CLASS_000146","rs/e/b"],["CLIENT_CLASS_000148","rs/e/d"],["CLIENT_CLASS_000149","rs/e/e"],["CLIENT_CLASS_000150","rs/e/f"],["CLIENT_CLASS_000151","rs/e/g"],["CLIENT_CLASS_000153","rs/e/i"],["CLIENT_CLASS_000156","rs/e/l"],["CLIENT_CLASS_000159","rs/e/o"],["CLIENT_CLASS_000160","rs/e/p"],["CLIENT_CLASS_000161","rs/e/q"]]

def _class_lineage():
    classes=[]
    for logical_id, internal_name in CLASS_COORDS:
        classes.append({"logical_id":logical_id,"semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,"lineage":[{"build_id":"v308","internal_name":internal_name,"entry_path":internal_name+".class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r399-fixture"}]}],"semantic_provenance":[]})
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308","builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],"classes":classes,"unresolved":[]}

def _member_lineage():
    return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}

def _load(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

class Chat2SemanticReviewR399Tests(unittest.TestCase):
    def test_r399_resolves_deterministically(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r399.json"))
        expected=_load("mappings/candidates/v308.semantic-review.chat2.r399.json")
        self.assertEqual(actual["proposal_count"],11)
        self.assertEqual(actual["unresolved"],[])
        self.assertEqual(actual["review_id"],"SEMREVIEW_53EE5FBF1CEB1A7A1FB2")
        self.assertEqual(actual,expected)

    def test_r399_expected_stable_ids(self):
        review=_load("mappings/candidates/v308.semantic-review.chat2.r399.json")
        self.assertEqual({r["proposed_name"]:r["stable_id"] for r in review["proposals"]},{"Alpha":"CLIENT_CLASS_000145","Config":"CLIENT_CLASS_000146","ConfigDescriptor":"CLIENT_CLASS_000148","ConfigGroup":"CLIENT_CLASS_000149","ConfigInvocationHandler":"CLIENT_CLASS_000150","ConfigItem":"CLIENT_CLASS_000151","ConfigManager":"CLIENT_CLASS_000153","ConfigSection":"CLIENT_CLASS_000156","Range":"CLIENT_CLASS_000159","RequestFocusType":"CLIENT_CLASS_000160","Units":"CLIENT_CLASS_000161"})

    def test_r399_names_owners_and_ids_do_not_overlap_prior_reviews(self):
        current=_load("mappings/candidates/v308.semantic-review.chat2.r399.json")
        names={r["proposed_name"] for r in current["proposals"]}
        owners={r["source_coordinate"]["owner"] for r in current["proposals"]}
        stable_ids={r["stable_id"] for r in current["proposals"]}
        prior_names=set(); prior_owners=set(); prior_stable_ids=set()
        for batch in range(2,399):
            p=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{batch}.json"
            if not p.is_file(): continue
            prior=json.loads(p.read_text(encoding="utf-8"))
            prior_names.update(r["proposed_name"] for r in prior["proposals"] if r["target_kind"]=="class")
            prior_owners.update(r["source_coordinate"]["owner"] for r in prior["proposals"] if r["target_kind"]=="class")
            prior_stable_ids.update(r["stable_id"] for r in prior["proposals"] if r["target_kind"]=="class")
        self.assertTrue(names.isdisjoint(prior_names))
        self.assertTrue(owners.isdisjoint(prior_owners))
        self.assertTrue(stable_ids.isdisjoint(prior_stable_ids))

if __name__=="__main__":
    unittest.main()
