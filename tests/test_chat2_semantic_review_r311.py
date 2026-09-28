import json
from pathlib import Path
import unittest
from spk_recovery.semantic_review import resolve_semantic_candidates

SHA="854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
ROOT=Path(__file__).resolve().parents[1]
CLASS_COORDS=[("CLIENT_CLASS_000375","rs/l/b/a/b/b")]

def _class_lineage():
    classes=[]
    for logical_id, internal_name in CLASS_COORDS:
        classes.append({
            "logical_id":logical_id,
            "semantic_name":None,
            "semantic_status":"UNKNOWN",
            "semantic_confidence":0.0,
            "lineage":[{
                "build_id":"v308",
                "internal_name":internal_name,
                "entry_path":internal_name+".class",
                "entry_sha256":"b"*64,
                "structural_sha256":"c"*64,
                "relation":"BASELINE",
                "confidence":1.0,
                "provenance":[{"authority":"EXACT_CURRENT_CLIENT","source":"chat2-r311-fixture"}],
            }],
            "semantic_provenance":[],
        })
    return {
        "schema_version":1,
        "namespace":"spawnpk-client",
        "id_format":"CLIENT_CLASS_%06d",
        "baseline_build_id":"v308",
        "builds":[{"build_id":"v308","build_number":308,"sha256":SHA,"source_name":"client(6).jar","authority":"EXACT_CURRENT_CLIENT"}],
        "classes":classes,
        "unresolved":[],
    }

def _member_lineage():
    return {
        "schema_version":1,
        "kind":"member_lineage",
        "class_namespace":"spawnpk-client",
        "baseline_build_id":"v308",
        "source_sha256":SHA,
        "members":[],
        "unresolved":[],
    }

def _load(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

class Chat2SemanticReviewR311Tests(unittest.TestCase):
    def test_r311_resolves_deterministically(self):
        actual=resolve_semantic_candidates(
            _class_lineage(),
            _member_lineage(),
            _load("mappings/candidates/v308.semantic.chat2.r311.json"),
        )
        expected=_load("mappings/candidates/v308.semantic-review.chat2.r311.json")
        self.assertEqual(actual["proposal_count"],1)
        self.assertEqual(actual["unresolved"],[])
        self.assertEqual(actual["review_id"],"SEMREVIEW_9DC3AC6C4324AD9D5A37")
        self.assertEqual(actual,expected)

    def test_r311_expected_stable_id(self):
        review=_load("mappings/candidates/v308.semantic-review.chat2.r311.json")
        self.assertEqual(
            {r["proposed_name"]:r["stable_id"] for r in review["proposals"]},
            {"TextureDebugConfigLoader":"CLIENT_CLASS_000375"},
        )

    def test_r311_name_owner_and_stable_id_do_not_overlap_prior_reviews(self):
        current=_load("mappings/candidates/v308.semantic-review.chat2.r311.json")
        row=current["proposals"][0]
        names={row["proposed_name"]}
        owners={row["source_coordinate"]["owner"]}
        stable_ids={row["stable_id"]}

        prior_names=set()
        prior_owners=set()
        prior_stable_ids=set()
        for batch in range(2,311):
            p=ROOT/"mappings"/"candidates"/f"v308.semantic-review.chat2.r{batch}.json"
            if not p.is_file():
                continue
            prior=json.loads(p.read_text(encoding="utf-8"))
            for proposal in prior.get("proposals",[]):
                if proposal.get("target_kind")!="class":
                    continue
                prior_names.add(proposal["proposed_name"])
                prior_owners.add(proposal["source_coordinate"]["owner"])
                prior_stable_ids.add(proposal["stable_id"])

        self.assertTrue(names.isdisjoint(prior_names))
        self.assertTrue(owners.isdisjoint(prior_owners))
        self.assertTrue(stable_ids.isdisjoint(prior_stable_ids))

if __name__=="__main__":
    unittest.main()
