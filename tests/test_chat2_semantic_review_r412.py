import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates
SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]
CLASS_COORDS=[["CLIENT_CLASS_000144","rs/e/a"],["CLIENT_CLASS_000145","rs/e/b"],["CLIENT_CLASS_000146","rs/e/c"],["CLIENT_CLASS_000147","rs/e/d"],["CLIENT_CLASS_000148","rs/e/e"],["CLIENT_CLASS_000149","rs/e/f"],["CLIENT_CLASS_000150","rs/e/g"],["CLIENT_CLASS_000151","rs/e/h"],["CLIENT_CLASS_000152","rs/e/i"],["CLIENT_CLASS_000154","rs/e/k"],["CLIENT_CLASS_000155","rs/e/l"],["CLIENT_CLASS_000156","rs/e/m"],["CLIENT_CLASS_000157","rs/e/n"],["CLIENT_CLASS_000158","rs/e/o"],["CLIENT_CLASS_000159","rs/e/p"],["CLIENT_CLASS_000160","rs/e/q"]]
def _class_lineage():
    classes=[]
    for logical_id, internal_name in CLASS_COORDS:
        classes.append({"logical_id":logical_id,"semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,"lineage":[{"build_id":"v308","internal_name":internal_name,"entry_path":internal_name+".class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r412-fixture"}]}],"semantic_provenance":[]})
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308","builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],"classes":classes,"unresolved":[]}
def _member_lineage(): return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}
def _load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chat2SemanticReviewR412Tests(unittest.TestCase):
    def test_r412_resolves_deterministically(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r412.json")); expected=_load("mappings/candidates/v308.semantic-review.chat2.r412.json")
        self.assertEqual(actual["proposal_count"],16); self.assertEqual(actual["unresolved"],[]); self.assertEqual(actual["review_id"],"SEMREVIEW_2037FA157B67E76D41D6"); self.assertEqual(actual,expected)
    def test_r412_expected_stable_ids(self):
        review=_load("mappings/candidates/v308.semantic-review.chat2.r412.json"); self.assertEqual({r["proposed_name"]:r["stable_id"] for r in review["proposals"]},{"Alpha":"CLIENT_CLASS_000144","Config":"CLIENT_CLASS_000145","ConfigStore":"CLIENT_CLASS_000146","ConfigDescriptor":"CLIENT_CLASS_000147","ConfigGroup":"CLIENT_CLASS_000148","ConfigInvocationHandler":"CLIENT_CLASS_000149","ConfigItem":"CLIENT_CLASS_000150","ConfigItemDescriptor":"CLIENT_CLASS_000151","ConfigManager":"CLIENT_CLASS_000152","ConfigProfile":"CLIENT_CLASS_000154","ConfigSection":"CLIENT_CLASS_000155","ConfigSectionDescriptor":"CLIENT_CLASS_000156","FlashNotification":"CLIENT_CLASS_000157","Range":"CLIENT_CLASS_000158","RequestFocusType":"CLIENT_CLASS_000159","Units":"CLIENT_CLASS_000160"})
    def test_r412_names_owners_and_ids_do_not_overlap_prior_reviews(self):
        current=_load("mappings/candidates/v308.semantic-review.chat2.r412.json"); names={r["proposed_name"] for r in current["proposals"]}; owners={r["source_coordinate"]["owner"] for r in current["proposals"]}; stable_ids={r["stable_id"] for r in current["proposals"]}
        pn=set(); po=set(); ps=set()
        for batch in range(2,412):
            p=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{batch}.json"
            if not p.is_file(): continue
            prior=json.loads(p.read_text(encoding="utf-8")); pn.update(r["proposed_name"] for r in prior["proposals"] if r["target_kind"]=="class"); po.update(r["source_coordinate"]["owner"] for r in prior["proposals"] if r["target_kind"]=="class"); ps.update(r["stable_id"] for r in prior["proposals"] if r["target_kind"]=="class")
        self.assertTrue(names.isdisjoint(pn)); self.assertTrue(owners.isdisjoint(po)); self.assertTrue(stable_ids.isdisjoint(ps))
if __name__=="__main__": unittest.main()
