import unittest

from spk_recovery.lineage import seed_lineage
from spk_recovery.semantic_bridge import build_class_remap_proposals
from spk_recovery.semantic_candidates import make_semantic_candidate


SHA = "a" * 64


def _index():
    return {
        "source_name": "client.jar",
        "sha256": SHA,
        "entries": {
            "rs/a.class": {"sha256": "1" * 64},
            "rs/b.class": {"sha256": "2" * 64},
        },
        "classes": {
            "rs/a.class": {
                "internal_name": "rs/a",
                "structural_sha256": "3" * 64,
            },
            "rs/b.class": {
                "internal_name": "rs/b",
                "structural_sha256": "4" * 64,
            },
        },
    }


def _lineage():
    return seed_lineage(
        _index(),
        build_id="v308",
        build_number=308,
        authority="EXACT_CURRENT_CLIENT",
    )


def _class_candidate(owner="rs/a", name="ReadableA"):
    return make_semantic_candidate(
        target={
            "kind": "class",
            "owner": owner,
            "name": None,
            "descriptor": None,
        },
        proposed_name=name,
        evidence=[
            {"family": "exact_resource_role"},
            {"family": "exact_literal_role"},
        ],
        source_build="v308",
        source_sha256=SHA,
    )


class SemanticBridgeTests(unittest.TestCase):
    def test_output_is_not_authorized_remap_spec(self):
        semantic_set = {
            "schema_version": 1,
            "kind": "semantic_candidate_set",
            "canonical": False,
            "candidates": [_class_candidate()],
        }
        out = build_class_remap_proposals(
            _lineage(),
            semantic_set,
            build_id="v308",
        )
        self.assertEqual(
            out["kind"],
            "remap_spec_proposals",
        )
        self.assertFalse(out["canonical"])
        self.assertNotEqual(out["kind"], "remap_spec")

    def test_resolves_stable_logical_id(self):
        semantic_set = {
            "schema_version": 1,
            "kind": "semantic_candidate_set",
            "canonical": False,
            "candidates": [_class_candidate()],
        }
        out = build_class_remap_proposals(
            _lineage(),
            semantic_set,
            build_id="v308",
        )
        proposal = out["proposals"][0]
        self.assertEqual(
            proposal["logical_id"],
            "CLIENT_CLASS_000001",
        )
        self.assertEqual(
            proposal["proposed_target_internal_name"],
            "recovered/spawnpk/client/ReadableA",
        )

    def test_member_candidate_is_not_exported_as_class_remap(self):
        member = make_semantic_candidate(
            target={
                "kind": "method",
                "owner": "rs/a",
                "name": "a",
                "descriptor": "()V",
            },
            proposed_name="doThing",
            evidence=[{"family": "exact_packet_behavior"}],
            source_build="v308",
            source_sha256=SHA,
        )
        semantic_set = {
            "schema_version": 1,
            "kind": "semantic_candidate_set",
            "canonical": False,
            "candidates": [member],
        }
        out = build_class_remap_proposals(
            _lineage(),
            semantic_set,
            build_id="v308",
        )
        self.assertEqual(out["proposal_count"], 0)

    def test_unknown_owner_stays_unresolved(self):
        semantic_set = {
            "schema_version": 1,
            "kind": "semantic_candidate_set",
            "canonical": False,
            "candidates": [
                _class_candidate(
                    owner="rs/missing",
                    name="Missing",
                )
            ],
        }
        out = build_class_remap_proposals(
            _lineage(),
            semantic_set,
            build_id="v308",
        )
        self.assertEqual(out["proposal_count"], 0)
        self.assertEqual(
            out["unresolved"][0]["reason"],
            "class_owner_not_in_canonical_build",
        )


if __name__ == "__main__":
    unittest.main()
