import unittest

from spk_recovery.lineage import seed_lineage
from spk_recovery.member_semantic_bridge import (
    build_member_remap_proposals,
)
from spk_recovery.semantic_candidates import (
    make_semantic_candidate,
)


SHA = "a" * 64


def _lineage():
    index = {
        "source_name": "client.jar",
        "sha256": SHA,
        "entries": {
            "rs/Client.class": {"sha256": "1" * 64},
        },
        "classes": {
            "rs/Client.class": {
                "internal_name": "rs/Client",
                "structural_sha256": "2" * 64,
            }
        },
    }
    return seed_lineage(
        index,
        build_id="v308",
        build_number=308,
        authority="EXACT_CURRENT_CLIENT",
    )


def _candidate(kind, name, descriptor, proposed):
    return make_semantic_candidate(
        target={
            "kind": kind,
            "owner": "rs/Client",
            "name": name,
            "descriptor": descriptor,
        },
        proposed_name=proposed,
        evidence=[
            {"family": "exact_packet_behavior"}
            if kind == "method"
            else {"family": "exact_field_flow"}
        ],
        source_build="v308",
        source_sha256=SHA,
    )


class MemberSemanticBridgeTests(unittest.TestCase):
    def test_output_is_research_only(self):
        semantic = {
            "schema_version": 1,
            "kind": "semantic_candidate_set",
            "canonical": False,
            "candidates": [
                _candidate("method", "a", "(J)V", "addFriend"),
            ],
        }
        out = build_member_remap_proposals(
            _lineage(),
            semantic,
            build_id="v308",
        )
        self.assertEqual(
            out["kind"],
            "member_remap_proposals",
        )
        self.assertFalse(out["canonical"])

    def test_resolves_owner_logical_id_and_exact_member_key(self):
        semantic = {
            "schema_version": 1,
            "kind": "semantic_candidate_set",
            "canonical": False,
            "candidates": [
                _candidate("field", "P", "I", "rewardIndex"),
            ],
        }
        out = build_member_remap_proposals(
            _lineage(),
            semantic,
            build_id="v308",
        )
        row = out["proposals"][0]
        self.assertEqual(
            row["owner_logical_id"],
            "CLIENT_CLASS_000001",
        )
        self.assertEqual(row["source_name"], "P")
        self.assertEqual(row["source_descriptor"], "I")
        self.assertEqual(row["proposed_name"], "rewardIndex")

    def test_class_candidate_is_not_exported(self):
        cls = make_semantic_candidate(
            target={
                "kind": "class",
                "owner": "rs/Client",
                "name": None,
                "descriptor": None,
            },
            proposed_name="GameClient",
            evidence=[{"family": "exact_literal_role"}],
            source_build="v308",
            source_sha256=SHA,
        )
        semantic = {
            "schema_version": 1,
            "kind": "semantic_candidate_set",
            "canonical": False,
            "candidates": [cls],
        }
        out = build_member_remap_proposals(
            _lineage(),
            semantic,
            build_id="v308",
        )
        self.assertEqual(out["proposal_count"], 0)


if __name__ == "__main__":
    unittest.main()
