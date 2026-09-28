import unittest

from spk_recovery.semantic_candidates import (
    SemanticCandidateError,
    make_semantic_candidate,
    merge_semantic_candidates,
    score_semantic_evidence,
)


SHA = "a" * 64


class SemanticCandidateTests(unittest.TestCase):
    def test_independent_evidence_increases_score(self):
        one = score_semantic_evidence(
            [{"family": "exact_packet_behavior"}]
        )
        two = score_semantic_evidence(
            [
                {"family": "exact_packet_behavior"},
                {"family": "exact_literal_role"},
            ]
        )
        self.assertGreater(two, one)
        self.assertLess(two, 1.0)

    def test_duplicate_evidence_family_does_not_stack(self):
        one = score_semantic_evidence(
            [{"family": "exact_literal_role"}]
        )
        duplicated = score_semantic_evidence(
            [
                {"family": "exact_literal_role"},
                {"family": "exact_literal_role"},
            ]
        )
        self.assertEqual(one, duplicated)

    def test_candidate_is_research_only(self):
        candidate = make_semantic_candidate(
            target={
                "kind": "method",
                "owner": "rs/Client",
                "name": "a",
                "descriptor": "(J)V",
            },
            proposed_name="addFriend",
            evidence=[
                {"family": "exact_packet_behavior"},
                {"family": "exact_literal_role"},
            ],
            source_build="v308",
            source_sha256=SHA,
        )
        self.assertFalse(candidate["canonical"])
        self.assertEqual(candidate["status"], "CANDIDATE")

    def test_invalid_identifier_is_rejected(self):
        with self.assertRaises(SemanticCandidateError):
            make_semantic_candidate(
                target={
                    "kind": "field",
                    "owner": "rs/Client",
                    "name": "P",
                    "descriptor": "I",
                },
                proposed_name="not valid",
                evidence=[{"family": "exact_field_flow"}],
                source_build="v308",
                source_sha256=SHA,
            )

    def test_conflicting_proposals_are_exposed(self):
        target = {
            "kind": "field",
            "owner": "rs/Client",
            "name": "P",
            "descriptor": "I",
        }
        a = make_semantic_candidate(
            target=target,
            proposed_name="loginRewardContainerIndex",
            evidence=[{"family": "exact_field_flow"}],
            source_build="v308",
            source_sha256=SHA,
        )
        b = make_semantic_candidate(
            target=target,
            proposed_name="dailyRewardIndex",
            evidence=[{"family": "nearby_string"}],
            source_build="v308",
            source_sha256=SHA,
        )
        merged = merge_semantic_candidates([a, b])
        self.assertEqual(len(merged["conflicts"]), 1)
        self.assertEqual(len(merged["candidates"]), 2)


if __name__ == "__main__":
    unittest.main()
