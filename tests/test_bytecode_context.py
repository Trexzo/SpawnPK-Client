import unittest

from spk_recovery.bytecode_context import (
    _instruction_length,
    match_unresolved_fields_by_usage,
)


class BytecodeContextTests(unittest.TestCase):
    def test_instruction_lengths_cover_field_and_switch_shapes(self):
        self.assertEqual(
            _instruction_length(bytes([0xB4, 0x00, 0x01]), 0),
            3,
        )
        self.assertEqual(
            _instruction_length(bytes([0x10, 0x7F]), 0),
            2,
        )

    def test_unique_matched_method_usage_recovers_field(self):
        old_profile = {
            "internal_name": "rs/a",
            "methods": [
                {
                    "name": "a",
                    "descriptor": "()V",
                    "field_accesses": [
                        {
                            "operation": "getfield",
                            "owner": "rs/a",
                            "name": "b",
                            "descriptor": "I",
                        },
                        {
                            "operation": "putfield",
                            "owner": "rs/a",
                            "name": "b",
                            "descriptor": "I",
                        },
                    ],
                }
            ],
        }
        new_profile = {
            "internal_name": "rs/z",
            "methods": [
                {
                    "name": "q",
                    "descriptor": "()V",
                    "field_accesses": [
                        {
                            "operation": "getfield",
                            "owner": "rs/z",
                            "name": "x",
                            "descriptor": "I",
                        },
                        {
                            "operation": "putfield",
                            "owner": "rs/z",
                            "name": "x",
                            "descriptor": "I",
                        },
                    ],
                }
            ],
        }
        member_record = {
            "old_owner": "rs/a.class",
            "new_owner": "rs/z.class",
            "methods": {
                "relationships": [
                    {
                        "relationship_id": "MEMREL_ONE",
                        "old": {
                            "name": "a",
                            "descriptor": "()V",
                        },
                        "new": {
                            "name": "q",
                            "descriptor": "()V",
                        },
                    }
                ]
            },
            "fields": {
                "unmatched_old": [
                    {
                        "name": "b",
                        "descriptor": "I",
                        "access": 2,
                    }
                ],
                "unmatched_new": [
                    {
                        "name": "x",
                        "descriptor": "I",
                        "access": 2,
                    }
                ],
            },
        }
        out = match_unresolved_fields_by_usage(
            old_profile,
            new_profile,
            member_record,
            old_type_aliases={},
            new_type_aliases={},
        )
        self.assertEqual(out["matched"], 1)
        self.assertEqual(
            out["relationships"][0]["old"]["name"],
            "b",
        )
        self.assertEqual(
            out["relationships"][0]["new"]["name"],
            "x",
        )

    def test_ambiguous_same_usage_is_not_guessed(self):
        old_profile = {
            "internal_name": "rs/a",
            "methods": [
                {
                    "name": "a",
                    "descriptor": "()V",
                    "field_accesses": [
                        {
                            "operation": "getfield",
                            "owner": "rs/a",
                            "name": "b",
                            "descriptor": "I",
                        },
                        {
                            "operation": "getfield",
                            "owner": "rs/a",
                            "name": "c",
                            "descriptor": "I",
                        },
                    ],
                }
            ],
        }
        new_profile = {
            "internal_name": "rs/z",
            "methods": [
                {
                    "name": "q",
                    "descriptor": "()V",
                    "field_accesses": [
                        {
                            "operation": "getfield",
                            "owner": "rs/z",
                            "name": "x",
                            "descriptor": "I",
                        },
                        {
                            "operation": "getfield",
                            "owner": "rs/z",
                            "name": "y",
                            "descriptor": "I",
                        },
                    ],
                }
            ],
        }
        member_record = {
            "methods": {
                "relationships": [
                    {
                        "relationship_id": "MEMREL_ONE",
                        "old": {
                            "name": "a",
                            "descriptor": "()V",
                        },
                        "new": {
                            "name": "q",
                            "descriptor": "()V",
                        },
                    }
                ]
            },
            "fields": {
                "unmatched_old": [
                    {"name": "b", "descriptor": "I", "access": 2},
                    {"name": "c", "descriptor": "I", "access": 2},
                ],
                "unmatched_new": [
                    {"name": "x", "descriptor": "I", "access": 2},
                    {"name": "y", "descriptor": "I", "access": 2},
                ],
            },
        }
        out = match_unresolved_fields_by_usage(
            old_profile,
            new_profile,
            member_record,
            old_type_aliases={},
            new_type_aliases={},
        )
        self.assertEqual(out["matched"], 0)


if __name__ == "__main__":
    unittest.main()
