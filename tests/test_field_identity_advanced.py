import unittest

from spk_recovery.field_identity_advanced import (
    AdvancedFieldIdentityError,
    match_constant_values,
    match_unique_contexts,
    remove_resolved_fields,
    select_dominant_alignment_votes,
)


class AdvancedFieldIdentityTests(unittest.TestCase):
    def test_exact_constant_value_matches_without_order(self):
        old = [
            {
                "name": "a",
                "descriptor": "I",
                "access": 26,
                "constant_value": ("I", 32),
            },
            {
                "name": "b",
                "descriptor": "I",
                "access": 26,
                "constant_value": ("I", 20),
            },
        ]
        new = [
            {
                "name": "y",
                "descriptor": "I",
                "access": 26,
                "constant_value": ("I", 20),
            },
            {
                "name": "x",
                "descriptor": "I",
                "access": 26,
                "constant_value": ("I", 32),
            },
        ]
        out = match_constant_values(
            old,
            new,
            old_aliases={},
            new_aliases={},
        )
        self.assertEqual(
            {(row["old"]["name"], row["new"]["name"]) for row in out},
            {("a", "x"), ("b", "y")},
        )

    def test_duplicate_constant_is_left_unresolved(self):
        old = [
            {
                "name": "a",
                "descriptor": "I",
                "access": 26,
                "constant_value": ("I", 1),
            },
            {
                "name": "b",
                "descriptor": "I",
                "access": 26,
                "constant_value": ("I", 1),
            },
        ]
        new = [
            {
                "name": "x",
                "descriptor": "I",
                "access": 26,
                "constant_value": ("I", 1),
            },
            {
                "name": "y",
                "descriptor": "I",
                "access": 26,
                "constant_value": ("I", 1),
            },
        ]
        self.assertEqual(
            match_constant_values(
                old,
                new,
                old_aliases={},
                new_aliases={},
            ),
            [],
        )

    def test_unique_normalized_context_matches(self):
        old = [
            {"name": "a", "descriptor": "I", "access": 2},
            {"name": "b", "descriptor": "I", "access": 2},
        ]
        new = [
            {"name": "x", "descriptor": "I", "access": 2},
            {"name": "y", "descriptor": "I", "access": 2},
        ]
        out = match_unique_contexts(
            old,
            new,
            old_contexts={
                ("a", "I"): ("METHOD_1", "getfield"),
                ("b", "I"): ("METHOD_2", "putfield"),
            },
            new_contexts={
                ("x", "I"): ("METHOD_2", "putfield"),
                ("y", "I"): ("METHOD_1", "getfield"),
            },
            old_aliases={},
            new_aliases={},
            strategy="instruction_neighborhood",
            score=0.99,
        )
        self.assertEqual(
            {(row["old"]["name"], row["new"]["name"]) for row in out},
            {("a", "y"), ("b", "x")},
        )

    def test_alignment_votes_require_two_way_dominance(self):
        out = select_dominant_alignment_votes(
            [
                {"old": "a", "new": "x", "count": 5},
                {"old": "a", "new": "y", "count": 1},
                {"old": "b", "new": "y", "count": 4},
                {"old": "b", "new": "x", "count": 1},
            ]
        )
        self.assertEqual(
            {(row["old"], row["new"]) for row in out},
            {("a", "x"), ("b", "y")},
        )

    def test_alignment_vote_tie_is_not_promoted(self):
        out = select_dominant_alignment_votes(
            [
                {"old": "a", "new": "x", "count": 2},
                {"old": "a", "new": "y", "count": 2},
            ]
        )
        self.assertEqual(out, [])

    def test_invalid_alignment_threshold_is_rejected(self):
        with self.assertRaises(AdvancedFieldIdentityError):
            select_dominant_alignment_votes(
                [],
                min_outbound_dominance=1.1,
            )

    def test_remove_resolved_fields_is_coordinate_based(self):
        fields = [
            {"name": "a", "descriptor": "I"},
            {"name": "b", "descriptor": "J"},
        ]
        matches = [
            {
                "old": {"name": "a", "descriptor": "I"},
                "new": {"name": "x", "descriptor": "I"},
            }
        ]
        self.assertEqual(
            remove_resolved_fields(
                fields,
                matches,
                side="old",
            ),
            [{"name": "b", "descriptor": "J"}],
        )


if __name__ == "__main__":
    unittest.main()
