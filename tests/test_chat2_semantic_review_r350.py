import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates
SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]
CLASS_COORDS=[("CLIENT_CLASS_001122","rs/y/a"),("CLIENT_CLASS_001123","rs/y/b"),("CLIENT_CLASS_001124","rs/y/c")]
def _class_lineage():
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308","builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],"classes":[{"logical_id":sid,"semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,"lineage":[{"build_id":"v308","internal_name":owner,"entry_path":owner+".class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r350-fixture"}]}],"semantic_provenance":[]} for sid,owner in CLASS_COORDS],"unresolved":[]}
def _member_lineage(): return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}
def _load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chat2SemanticReviewR350Tests(unittest.TestCase):
    def test_r350_resolves_deterministically(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r350.json")); expected=_load("mappings/candidates/v308.semantic-review.chat2.r350.json")
        self.assertEqual(actual["proposal_count"],3); self.assertEqual(actual["unresolved"],[]); self.assertEqual(actual["review_id"],"SEMREVIEW_0C940EC4C68D5DDC6CF0"); self.assertEqual(actual,expected)
    def test_r350_expected_ids(self):
        r=_load("mappings/candidates/v308.semantic-review.chat2.r350.json")
        self.assertEqual({x["proposed_name"]:x["stable_id"] for x in r["proposals"]},{"Schedule":"CLIENT_CLASS_001122","ScheduledMethod":"CLIENT_CLASS_001123","Scheduler":"CLIENT_CLASS_001124"})
if __name__=="__main__": unittest.main()
