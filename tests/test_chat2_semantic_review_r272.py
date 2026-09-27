import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates

SHA=("854f26ff9f134b0317572e7ac1688e6f""40a231d5a4c66f8db5d655b7f45ce7c6")
ROOT=Path(__file__).resolve().parents[1]

def _class_lineage():
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308","builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],"classes":[{"logical_id":"CLIENT_CLASS_000579","semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,"lineage":[{"build_id":"v308","internal_name":"rs/n/c/aD","entry_path":"rs/n/c/aD.class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r272-fixture"}]}],"semantic_provenance":[]}],"unresolved":[]}

def _member_lineage():
    return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}

def _load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

class Chat2SemanticReviewR272Tests(unittest.TestCase):
    def test_r272_resolves_deterministically(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r272.json"))
        expected=_load("mappings/candidates/v308.semantic-review.chat2.r272.json")
        self.assertEqual(actual["proposal_count"],1); self.assertEqual(actual["unresolved"],[])
        self.assertEqual(actual["review_id"],"SEMREVIEW_59DEAFF041FEDA761388"); self.assertEqual(actual,expected)

    def test_r272_expected_stable_id(self):
        p=_load("mappings/candidates/v308.semantic-review.chat2.r272.json")["proposals"][0]
        self.assertEqual((p["proposed_name"],p["stable_id"]),("BloodFountainPerkTreeInterface","CLIENT_CLASS_000579"))

    def test_r272_owner_and_name_do_not_overlap_prior_reviews(self):
        p=_load("mappings/candidates/v308.semantic-review.chat2.r272.json")["proposals"][0]
        owners=set(); names=set()
        for batch in range(2,272):
            path=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{batch}.json"
            if not path.is_file(): continue
            for row in json.loads(path.read_text(encoding="utf-8"))["proposals"]:
                if row["target_kind"]=="class":
                    owners.add(row["source_coordinate"]["owner"]); names.add(row["proposed_name"])
        self.assertNotIn(p["source_coordinate"]["owner"],owners); self.assertNotIn(p["proposed_name"],names)

if __name__=="__main__": unittest.main()
