import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates
SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]
CLASS_COORDS=[["CLIENT_CLASS_000087","rs/cache/b/a/a"],["CLIENT_CLASS_000089","rs/cache/b/a/c"],["CLIENT_CLASS_000090","rs/cache/b/a/d"],["CLIENT_CLASS_000092","rs/cache/b/c"],["CLIENT_CLASS_000093","rs/cache/b/d"],["CLIENT_CLASS_000094","rs/cache/b/e"]]
def _class_lineage():
    cs=[]
    for sid,owner in CLASS_COORDS:
        cs.append({"logical_id":sid,"semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,"lineage":[{"build_id":"v308","internal_name":owner,"entry_path":owner+".class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r353-fixture"}]}],"semantic_provenance":[]})
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308","builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],"classes":cs,"unresolved":[]}
def _member_lineage(): return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}
def _load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chat2SemanticReviewR353Tests(unittest.TestCase):
    def test_resolves(self):
        a=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r353.json")); e=_load("mappings/candidates/v308.semantic-review.chat2.r353.json")
        self.assertEqual(a["proposal_count"],6); self.assertEqual(a["unresolved"],[]); self.assertEqual(a["review_id"],"SEMREVIEW_BCB4AD69A3EE0D86ADFB"); self.assertEqual(a,e)
    def test_ids(self):
        r=_load("mappings/candidates/v308.semantic-review.chat2.r353.json"); self.assertEqual({x["proposed_name"]:x["stable_id"] for x in r["proposals"]},{"MainGameAssetUpdater":"CLIENT_CLASS_000087","ConfigAssetUpdater":"CLIENT_CLASS_000089","SpriteAssetUpdater":"CLIENT_CLASS_000090","AssetUpdateManager":"CLIENT_CLASS_000092","AssetUpdater":"CLIENT_CLASS_000093","AssetVersion":"CLIENT_CLASS_000094"})
    def test_no_prior_overlap(self):
        cur=_load("mappings/candidates/v308.semantic-review.chat2.r353.json"); names={x["proposed_name"] for x in cur["proposals"]}; owners={x["source_coordinate"]["owner"] for x in cur["proposals"]}; ids={x["stable_id"] for x in cur["proposals"]}
        pn=set();po=set();pi=set()
        for n in range(2,353):
            p=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{n}.json"
            if not p.is_file(): continue
            o=json.loads(p.read_text())
            pn|={x["proposed_name"] for x in o["proposals"] if x["target_kind"]=="class"};po|={x["source_coordinate"]["owner"] for x in o["proposals"] if x["target_kind"]=="class"};pi|={x["stable_id"] for x in o["proposals"] if x["target_kind"]=="class"}
        self.assertTrue(names.isdisjoint(pn));self.assertTrue(owners.isdisjoint(po));self.assertTrue(ids.isdisjoint(pi))
if __name__=="__main__": unittest.main()
