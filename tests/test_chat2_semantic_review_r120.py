import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates

SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]

def _class_lineage():
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308",
    "builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],
    "classes":[{"logical_id":"CLIENT_CLASS_000760","semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,
      "lineage":[{"build_id":"v308","internal_name":"rs/q/a/a/a/o","entry_path":"rs/q/a/a/a/o.class","entry_sha256":"b"*64,
      "structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,
      "provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r120-fixture"}]}],"semantic_provenance":[]}],"unresolved":[]}
def _member_lineage():
    return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}
def _load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

class Chat2SemanticReviewR120Tests(unittest.TestCase):
    def test_resolves(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r120.json"))
        expected=_load("mappings/candidates/v308.semantic-review.chat2.r120.json")
        self.assertEqual(actual["proposal_count"],1); self.assertEqual(actual["unresolved"],[])
        self.assertEqual(actual["review_id"],"SEMREVIEW_077E34656C4BB246BE21"); self.assertEqual(actual,expected)
    def test_id(self):
        r=_load("mappings/candidates/v308.semantic-review.chat2.r120.json")["proposals"][0]
        self.assertEqual(r["proposed_name"],"SentPrivateMessagePacketHandler")
        self.assertEqual(r["stable_id"],"CLIENT_CLASS_000760")
    def test_no_prior_overlap(self):
        current=_load("mappings/candidates/v308.semantic-review.chat2.r120.json")
        names={r["proposed_name"] for r in current["proposals"]}; owners={r["source_coordinate"]["owner"] for r in current["proposals"]}
        pn=set(); po=set()
        for batch in range(2,120):
            p=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{batch}.json"
            if not p.is_file(): continue
            prior=json.loads(p.read_text(encoding="utf-8"))
            pn.update(r["proposed_name"] for r in prior["proposals"])
            po.update(r["source_coordinate"]["owner"] for r in prior["proposals"] if r["target_kind"]=="class")
        self.assertTrue(names.isdisjoint(pn)); self.assertTrue(owners.isdisjoint(po))
if __name__=="__main__": unittest.main()
