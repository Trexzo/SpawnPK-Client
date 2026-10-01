import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates

SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]

def _class_lineage():
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308","builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],"classes":[{"logical_id":"CLIENT_CLASS_000361","semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,"lineage":[{"build_id":"v308","internal_name":"rs/l/L","entry_path":"rs/l/L.class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r374-fixture"}]}],"semantic_provenance":[]}],"unresolved":[]}

def _member_lineage():
    return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}

def _load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

class Chat2SemanticReviewR374Tests(unittest.TestCase):
    def test_r374_resolves_deterministically(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r374.json"))
        expected=_load("mappings/candidates/v308.semantic-review.chat2.r374.json")
        self.assertEqual(actual["proposal_count"],1)
        self.assertEqual(actual["unresolved"],[])
        self.assertEqual(actual["review_id"],"SEMREVIEW_392BB83D0E7FE3166E21")
        self.assertEqual(actual,expected)

    def test_r374_identity(self):
        row=_load("mappings/candidates/v308.semantic-review.chat2.r374.json")["proposals"][0]
        self.assertEqual(row["stable_id"],"CLIENT_CLASS_000361")
        self.assertEqual(row["source_coordinate"]["owner"],"rs/l/L")
        self.assertEqual(row["proposed_name"],"SpriteHueShiftColorTransform")

    def test_r374_no_prior_collision(self):
        row=_load("mappings/candidates/v308.semantic-review.chat2.r374.json")["proposals"][0]
        for batch in range(2,374):
            p=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{batch}.json"
            if not p.is_file(): continue
            for prior in json.loads(p.read_text(encoding="utf-8")).get("proposals",[]):
                if prior.get("target_kind")!="class": continue
                self.assertNotEqual(prior.get("stable_id"),row["stable_id"])
                self.assertNotEqual(prior.get("source_coordinate",{}).get("owner"),row["source_coordinate"]["owner"])
                self.assertNotEqual(prior.get("proposed_name"),row["proposed_name"])

if __name__=="__main__": unittest.main()
