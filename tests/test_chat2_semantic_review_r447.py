import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates
SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]
CLASS_COORDS=[("CLIENT_CLASS_000592","rs/n/c/aQ")]
def _class_lineage():
    classes=[]
    for logical_id, internal_name in CLASS_COORDS:
        classes.append({"logical_id":logical_id,"semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,"lineage":[{"build_id":"v308","internal_name":internal_name,"entry_path":internal_name+".class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r447-fixture"}]}],"semantic_provenance":[]})
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308","builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],"classes":classes,"unresolved":[]}
def _member_lineage(): return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}
def _load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chat2SemanticReviewR447Tests(unittest.TestCase):
    def test_r447_resolves_deterministically(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r447.json")); expected=_load("mappings/candidates/v308.semantic-review.chat2.r447.json")
        self.assertEqual(actual["proposal_count"],1);self.assertEqual(actual["unresolved"],[]);self.assertEqual(actual["review_id"],"SEMREVIEW_E2D828CD52E864C46855");self.assertEqual(actual,expected)
    def test_r447_expected_stable_id(self):
        review=_load("mappings/candidates/v308.semantic-review.chat2.r447.json");self.assertEqual({x["proposed_name"]:x["stable_id"] for x in review["proposals"]},{"SkillsInterface":"CLIENT_CLASS_000592"})
    def test_r447_unique(self):
        current=_load("mappings/candidates/v308.semantic-review.chat2.r447.json");names={x["proposed_name"] for x in current["proposals"]};owners={x["source_coordinate"]["owner"] for x in current["proposals"]};ids={x["stable_id"] for x in current["proposals"]}
        pn=set();po=set();pi=set()
        for n in range(2,447):
            p=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{n}.json"
            if not p.is_file():continue
            d=json.loads(p.read_text(encoding="utf-8"));pn.update(x["proposed_name"] for x in d["proposals"] if x["target_kind"]=="class");po.update(x["source_coordinate"]["owner"] for x in d["proposals"] if x["target_kind"]=="class");pi.update(x["stable_id"] for x in d["proposals"] if x["target_kind"]=="class")
        self.assertTrue(names.isdisjoint(pn));self.assertTrue(owners.isdisjoint(po));self.assertTrue(ids.isdisjoint(pi))
if __name__=="__main__":unittest.main()
