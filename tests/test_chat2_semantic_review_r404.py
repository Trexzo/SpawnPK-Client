import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates
SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]
CLASS_COORDS=[["CLIENT_CLASS_000205","rs/gui/b/a"],["CLIENT_CLASS_000206","rs/gui/b/a$a"],["CLIENT_CLASS_000239","rs/gui/b/b/c"],["CLIENT_CLASS_000240","rs/gui/b/b/d"],["CLIENT_CLASS_000241","rs/gui/b/b/e"],["CLIENT_CLASS_000242","rs/gui/b/c"],["CLIENT_CLASS_000243","rs/gui/b/c/a"],["CLIENT_CLASS_000244","rs/gui/b/c/b"],["CLIENT_CLASS_000245","rs/gui/b/c/c"],["CLIENT_CLASS_000250","rs/gui/b/h"]]
def _class_lineage():
    classes=[]
    for logical_id, internal_name in CLASS_COORDS:
        classes.append({"logical_id":logical_id,"semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,"lineage":[{"build_id":"v308","internal_name":internal_name,"entry_path":internal_name+".class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r404-fixture"}]}],"semantic_provenance":[]})
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308","builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],"classes":classes,"unresolved":[]}
def _member_lineage(): return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}
def _load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Chat2SemanticReviewR404Tests(unittest.TestCase):
    def test_r404_resolves_deterministically(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r404.json")); expected=_load("mappings/candidates/v308.semantic-review.chat2.r404.json")
        self.assertEqual(actual["proposal_count"],10); self.assertEqual(actual["unresolved"],[]); self.assertEqual(actual["review_id"],"SEMREVIEW_35EACC9BFA2DE859EEC5"); self.assertEqual(actual,expected)
    def test_r404_expected_stable_ids(self):
        review=_load("mappings/candidates/v308.semantic-review.chat2.r404.json"); self.assertEqual({r["proposed_name"]:r["stable_id"] for r in review["proposals"]},{"Loadout":"CLIENT_CLASS_000205","Spellbook":"CLIENT_CLASS_000206","LoadoutSerializer":"CLIENT_CLASS_000239","LoadoutStore":"CLIENT_CLASS_000240","LoadoutVersion":"CLIENT_CLASS_000241","LoadoutList":"CLIENT_CLASS_000242","DefaultLoadout":"CLIENT_CLASS_000243","EquipmentPanel":"CLIENT_CLASS_000244","EquipmentSlot":"CLIENT_CLASS_000245","LoadoutsPanel":"CLIENT_CLASS_000250"})
    def test_r404_names_owners_and_ids_do_not_overlap_prior_reviews(self):
        current=_load("mappings/candidates/v308.semantic-review.chat2.r404.json"); names={r["proposed_name"] for r in current["proposals"]}; owners={r["source_coordinate"]["owner"] for r in current["proposals"]}; stable_ids={r["stable_id"] for r in current["proposals"]}
        pn=set(); po=set(); ps=set()
        for batch in range(2,404):
            p=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{batch}.json"
            if not p.is_file(): continue
            prior=json.loads(p.read_text(encoding="utf-8")); pn.update(r["proposed_name"] for r in prior["proposals"] if r["target_kind"]=="class"); po.update(r["source_coordinate"]["owner"] for r in prior["proposals"] if r["target_kind"]=="class"); ps.update(r["stable_id"] for r in prior["proposals"] if r["target_kind"]=="class")
        self.assertTrue(names.isdisjoint(pn)); self.assertTrue(owners.isdisjoint(po)); self.assertTrue(stable_ids.isdisjoint(ps))
if __name__=="__main__": unittest.main()
