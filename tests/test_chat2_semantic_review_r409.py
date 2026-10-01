import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates
SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"; ROOT=Path(__file__).resolve().parents[1]
CLASS_COORDS=[("CLIENT_CLASS_000510","rs/l/s"),("CLIENT_CLASS_000511","rs/l/t")]
def _class_lineage():
 c=[]
 for i,n in CLASS_COORDS:c.append({"logical_id":i,"semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,"lineage":[{"build_id":"v308","internal_name":n,"entry_path":n+".class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r409-fixture"}]}],"semantic_provenance":[]})
 return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308","builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],"classes":c,"unresolved":[]}
def _member_lineage():return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}
def _load(p):return json.loads((ROOT/p).read_text())
class T(unittest.TestCase):
 def test_review(self):
  a=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r409.json")); e=_load("mappings/candidates/v308.semantic-review.chat2.r409.json")
  self.assertEqual(a["review_id"],"SEMREVIEW_2BD69559828DBB565369"); self.assertEqual(a,e)
 def test_unique(self):
  cur=_load("mappings/candidates/v308.semantic-review.chat2.r409.json"); names={x["proposed_name"] for x in cur["proposals"]}; owners={x["source_coordinate"]["owner"] for x in cur["proposals"]}; ids={x["stable_id"] for x in cur["proposals"]}
  pn=set();po=set();pi=set()
  for n in range(2,409):
   p=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{n}.json"
   if p.is_file():
    d=json.loads(p.read_text())
    pn|={x["proposed_name"] for x in d["proposals"] if x["target_kind"]=="class"};po|={x["source_coordinate"]["owner"] for x in d["proposals"] if x["target_kind"]=="class"};pi|={x["stable_id"] for x in d["proposals"] if x["target_kind"]=="class"}
  self.assertTrue(names.isdisjoint(pn));self.assertTrue(owners.isdisjoint(po));self.assertTrue(ids.isdisjoint(pi))
