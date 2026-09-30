import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates
SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]
def _class_lineage():
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308",
      "builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],
      "classes":[{"logical_id":"CLIENT_CLASS_000080","semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,
        "lineage":[{"build_id":"v308","internal_name":"rs/c/a/a","entry_path":"rs/c/a/a.class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r410-fixture"}]}],
        "semantic_provenance":[]}],"unresolved":[]}
def _member_lineage():
    return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}
def _load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chat2SemanticReviewR410Tests(unittest.TestCase):
    def test_r410_resolves_deterministically(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r410.json"))
        expected=_load("mappings/candidates/v308.semantic-review.chat2.r410.json")
        self.assertEqual(actual["proposal_count"],1); self.assertEqual(actual["unresolved"],[])
        self.assertEqual(actual["review_id"],"SEMREVIEW_1ABDCE274ED42667B0B0"); self.assertEqual(actual,expected)
    def test_r410_expected_stable_id(self):
        review=_load("mappings/candidates/v308.semantic-review.chat2.r410.json")
        self.assertEqual({r["proposed_name"]:r["stable_id"] for r in review["proposals"]},{"OldSchoolItemDefinitionOverrides":"CLIENT_CLASS_000080"})
if __name__=="__main__": unittest.main()
