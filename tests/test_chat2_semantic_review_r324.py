import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates

SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]
CLASS_COORDS=[["CLIENT_CLASS_000689","rs/o/a/a/a/c"],["CLIENT_CLASS_000722","rs/o/a/a/a/J"],["CLIENT_CLASS_000723","rs/o/a/a/a/K"],["CLIENT_CLASS_000724","rs/o/a/a/a/L"],["CLIENT_CLASS_000725","rs/o/a/a/a/M"],["CLIENT_CLASS_000727","rs/o/a/a/a/O"],["CLIENT_CLASS_000728","rs/o/a/a/a/P"],["CLIENT_CLASS_000729","rs/o/a/a/a/Q"],["CLIENT_CLASS_000730","rs/o/a/a/a/R"]]

def _class_lineage():
    classes=[]
    for logical_id, internal_name in CLASS_COORDS:
        classes.append({"logical_id":logical_id,"semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,"lineage":[{"build_id":"v308","internal_name":internal_name,"entry_path":internal_name+".class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r324-fixture"}]}],"semantic_provenance":[]})
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308","builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],"classes":classes,"unresolved":[]}

def _member_lineage():
    return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}

def _load(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

class Chat2SemanticReviewR324Tests(unittest.TestCase):
    def test_r324_resolves_deterministically(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r324.json"))
        expected=_load("mappings/candidates/v308.semantic-review.chat2.r324.json")
        self.assertEqual(actual["proposal_count"],9)
        self.assertEqual(actual["unresolved"],[])
        self.assertEqual(actual["review_id"],"SEMREVIEW_2F4B75E92DEAA619E77F")
        self.assertEqual(actual,expected)

    def test_r324_expected_stable_ids(self):
        review=_load("mappings/candidates/v308.semantic-review.chat2.r324.json")
        self.assertEqual({r["proposed_name"]:r["stable_id"] for r in review["proposals"]},{"NpcOption2Packet":"CLIENT_CLASS_000689","NpcOption1Packet":"CLIENT_CLASS_000722","NpcOption3Packet":"CLIENT_CLASS_000723","NpcOption4Packet":"CLIENT_CLASS_000724","NpcOption5Packet":"CLIENT_CLASS_000725","ObjectOption2Packet":"CLIENT_CLASS_000727","ObjectOption3Packet":"CLIENT_CLASS_000728","ObjectOption4Packet":"CLIENT_CLASS_000729","ObjectOption5Packet":"CLIENT_CLASS_000730"})

    def test_r324_names_owners_and_ids_do_not_overlap_prior_reviews(self):
        current=_load("mappings/candidates/v308.semantic-review.chat2.r324.json")
        names={r["proposed_name"] for r in current["proposals"]}
        owners={r["source_coordinate"]["owner"] for r in current["proposals"]}
        stable_ids={r["stable_id"] for r in current["proposals"]}
        prior_names=set(); prior_owners=set(); prior_stable_ids=set()
        for batch in range(2,324):
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
