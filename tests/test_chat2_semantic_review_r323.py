import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates

SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]
CLASS_COORDS=[["CLIENT_CLASS_000687","rs/o/a/a/a/a"],["CLIENT_CLASS_000688","rs/o/a/a/a/b"],["CLIENT_CLASS_000694","rs/o/a/a/a/h"],["CLIENT_CLASS_000695","rs/o/a/a/a/i"],["CLIENT_CLASS_000696","rs/o/a/a/a/j"],["CLIENT_CLASS_000697","rs/o/a/a/a/k"],["CLIENT_CLASS_000699","rs/o/a/a/a/m"],["CLIENT_CLASS_000726","rs/o/a/a/a/N"],["CLIENT_CLASS_000736","rs/o/a/a/a/X"]]

def _class_lineage():
    classes=[]
    for logical_id, internal_name in CLASS_COORDS:
        classes.append({"logical_id":logical_id,"semantic_name":None,"semantic_status":"UNKNOWN","semantic_confidence":0.0,"lineage":[{"build_id":"v308","internal_name":internal_name,"entry_path":internal_name+".class","entry_sha256":"b"*64,"structural_sha256":"c"*64,"relation":"BASELINE","confidence":1.0,"provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r323-fixture"}]}],"semantic_provenance":[]})
    return {"schema_version":1,"namespace":"spawnpk-client","id_format":"CLIENT_CLASS_%06d","baseline_build_id":"v308","builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],"classes":classes,"unresolved":[]}

def _member_lineage():
    return {"schema_version":1,"kind":"member_lineage","class_namespace":"spawnpk-client","baseline_build_id":"v308","source_sha256":SHA,"members":[],"unresolved":[]}

def _load(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

class Chat2SemanticReviewR323Tests(unittest.TestCase):
    def test_r323_resolves_deterministically(self):
        actual=resolve_semantic_candidates(_class_lineage(),_member_lineage(),_load("mappings/candidates/v308.semantic.chat2.r323.json"))
        expected=_load("mappings/candidates/v308.semantic-review.chat2.r323.json")
        self.assertEqual(actual["proposal_count"],9)
        self.assertEqual(actual["unresolved"],[])
        self.assertEqual(actual["review_id"],"SEMREVIEW_85E6A073A076C0863B8B")
        self.assertEqual(actual,expected)

    def test_r323_expected_stable_ids(self):
        review=_load("mappings/candidates/v308.semantic-review.chat2.r323.json")
        self.assertEqual({r["proposed_name"]:r["stable_id"] for r in review["proposals"]},{"AddFriendPacket":"CLIENT_CLASS_000687","AddIgnorePacket":"CLIENT_CLASS_000688","WidgetActionPacket":"CLIENT_CLASS_000694","CloseInterfacePacket":"CLIENT_CLASS_000695","RemoveFriendPacket":"CLIENT_CLASS_000696","RemoveIgnorePacket":"CLIENT_CLASS_000697","AmountInputPacket":"CLIENT_CLASS_000699","ObjectOption1Packet":"CLIENT_CLASS_000726","InventoryMovePacket":"CLIENT_CLASS_000736"})

    def test_r323_names_owners_and_ids_do_not_overlap_prior_reviews(self):
        current=_load("mappings/candidates/v308.semantic-review.chat2.r323.json")
        names={r["proposed_name"] for r in current["proposals"]}
        owners={r["source_coordinate"]["owner"] for r in current["proposals"]}
        stable_ids={r["stable_id"] for r in current["proposals"]}
        prior_names=set(); prior_owners=set(); prior_stable_ids=set()
        for batch in range(2,323):
            p=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{batch}.json"
            if not p.is_file(): continue
            prior=json.loads(p.read_text(encoding="utf-8"))
            prior_names.update(r["proposed_name"] for r in prior["proposals"] if r["target_kind"]=="class")
            prior_owners.update(r["source_coordinate"]["owner"] for r in prior["proposals"] if r["target_kind"]=="class")
            prior_stable_ids.update(r["stable_id"] for r in prior["proposals"] if r["target_kind"]=="class")
        self.assertTrue(names.isdisjoint(prior_names))
        self.assertTrue(owners.isdisjoint(prior_owners))
        self.assertTrue(stable_ids.isdisjoint(prior_stable_ids))

if __name__=="__main__":
    unittest.main()
