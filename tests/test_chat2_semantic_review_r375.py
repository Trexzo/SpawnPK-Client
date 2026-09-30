import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates

SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]
CLASS_COORDS=[["CLIENT_CLASS_000210","rs/gui/b/a/a"],["CLIENT_CLASS_000211","rs/gui/b/a/b"],["CLIENT_CLASS_000212","rs/gui/b/a/c"],["CLIENT_CLASS_000213","rs/gui/b/a/d"],["CLIENT_CLASS_000214","rs/gui/b/a/e"],["CLIENT_CLASS_000216","rs/gui/b/a/g"],["CLIENT_CLASS_000217","rs/gui/b/a/h"],["CLIENT_CLASS_000218","rs/gui/b/a/i"],["CLIENT_CLASS_000219","rs/gui/b/a/j"],["CLIENT_CLASS_000234","rs/gui/b/a/y"],["CLIENT_CLASS_000235","rs/gui/b/a/z"]]

def _class_lineage():
    classes=[]
    for logical_id,internal_name in CLASS_COORDS:
        classes.append({"logical_id":logical_id,"semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,"lineage":[{"build_id":"v308","internal_name":internal_name,"entry_path":internal_name+".class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r375-fixture"}]}],"semantic_provenance":[]})
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308","builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],"classes":classes,"unresolved":[]}

def _member_lineage():
    return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}

def _load(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

class Chat2SemanticReviewR375Tests(unittest.TestCase):
    def test_r375_resolves_deterministically(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r375.json"))
        expected=_load("mappings/candidates/v308.semantic-review.chat2.r375.json")
        self.assertEqual(actual["proposal_count"],11)
        self.assertEqual(actual["unresolved"],[])
        self.assertEqual(actual["review_id"],"SEMREVIEW_413065558FE8CA44F4EB")
        self.assertEqual(actual,expected)

    def test_r375_expected_stable_ids(self):
        review=_load("mappings/candidates/v308.semantic-review.chat2.r375.json")
        self.assertEqual({r["proposed_name"]:r["stable_id"] for r in review["proposals"]},{"LoadoutCloneButtonFactory":"CLIENT_CLASS_000210","LoadoutCloneAction":"CLIENT_CLASS_000211","LoadoutCloneConfirmAction":"CLIENT_CLASS_000212","LoadoutCloneCancelAction":"CLIENT_CLASS_000213","LoadoutColorListCellRenderer":"CLIENT_CLASS_000214","LoadoutCreateButton":"CLIENT_CLASS_000216","LoadoutCreateAction":"CLIENT_CLASS_000217","LoadoutCreateCommitAction":"CLIENT_CLASS_000218","LoadoutIconListCellRenderer":"CLIENT_CLASS_000219","LoadoutEditorWindow":"CLIENT_CLASS_000234","LoadoutEditorCloseAction":"CLIENT_CLASS_000235"})

    def test_r375_names_owners_and_ids_do_not_overlap_prior_reviews(self):
        current=_load("mappings/candidates/v308.semantic-review.chat2.r375.json")
        names={r["proposed_name"] for r in current["proposals"]}
        owners={r["source_coordinate"]["owner"] for r in current["proposals"]}
        stable_ids={r["stable_id"] for r in current["proposals"]}
        pn=set(); po=set(); ps=set()
        for batch in range(2,375):
            p=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{batch}.json"
            if not p.is_file(): continue
            prior=json.loads(p.read_text(encoding="utf-8"))
            pn.update(r["proposed_name"] for r in prior["proposals"] if r["target_kind"]=="class")
            po.update(r["source_coordinate"]["owner"] for r in prior["proposals"] if r["target_kind"]=="class")
            ps.update(r["stable_id"] for r in prior["proposals"] if r["target_kind"]=="class")
        self.assertTrue(names.isdisjoint(pn))
        self.assertTrue(owners.isdisjoint(po))
        self.assertTrue(stable_ids.isdisjoint(ps))

if __name__=="__main__":
    unittest.main()
