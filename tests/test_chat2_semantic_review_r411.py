import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates
SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]
CLASS_COORDS=[["CLIENT_CLASS_000087","rs/cache/b/a/a"],["CLIENT_CLASS_000089","rs/cache/b/a/c"],["CLIENT_CLASS_000090","rs/cache/b/a/d"],["CLIENT_CLASS_000091","rs/cache/b/b"],["CLIENT_CLASS_000092","rs/cache/b/c"],["CLIENT_CLASS_000093","rs/cache/b/d"],["CLIENT_CLASS_000094","rs/cache/b/e"],["CLIENT_CLASS_000095","rs/cache/b/f"]]
def _class_lineage():
    classes=[]
    for logical_id, internal_name in CLASS_COORDS:
        classes.append({"logical_id":logical_id,"semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,
        "lineage":[{"build_id":"v308","internal_name":internal_name,"entry_path":internal_name+".class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r411-fixture"}]}],"semantic_provenance":[]})
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308","builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],"classes":classes,"unresolved":[]}
def _member_lineage(): return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}
def _load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chat2SemanticReviewR411Tests(unittest.TestCase):
    def test_r411_resolves_deterministically(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r411.json")); expected=_load("mappings/candidates/v308.semantic-review.chat2.r411.json")
        self.assertEqual(actual["proposal_count"],8); self.assertEqual(actual["unresolved"],[]); self.assertEqual(actual["review_id"],"SEMREVIEW_2895E054E58758F44CC2"); self.assertEqual(actual,expected)
    def test_r411_expected_stable_ids(self):
        review=_load("mappings/candidates/v308.semantic-review.chat2.r411.json"); self.assertEqual({r["proposed_name"]:r["stable_id"] for r in review["proposals"]},{"CacheUpdater":"CLIENT_CLASS_000087","ConfigUpdater":"CLIENT_CLASS_000089","SpriteUpdater":"CLIENT_CLASS_000090","AssetUpdateError":"CLIENT_CLASS_000091","AssetUpdateManager":"CLIENT_CLASS_000092","AssetUpdater":"CLIENT_CLASS_000093","AssetVersionTracker":"CLIENT_CLASS_000094","UpdateConnectionHelpLinkListener":"CLIENT_CLASS_000095"})
if __name__=="__main__": unittest.main()
