from __future__ import annotations

import unittest

from spk_recovery.delta_classify import (
    classify_class_deltas,
    classify_member_deltas,
)


def _class(
    *,
    structural="s",
    literal=None,
    numeric=None,
    methods=None,
    fields=None,
):
    return {
        "major": 53,
        "minor": 0,
        "access": 1,
        "super_name": "java/lang/Object",
        "interfaces": [],
        "attributes": [],
        "structural_sha256": structural,
        "literal_strings": list(literal or []),
        "numeric_constants": list(numeric or []),
        "fields": list(fields or []),
        "methods": list(methods or []),
    }


class DeltaClassifyTests(unittest.TestCase):
    def test_byte_identical(self):
        old = {
            "sha256": "1" * 64,
            "entries": {"rs/a.class": {"sha256": "a" * 64}},
            "classes": {"rs/a.class": _class(structural="x")},
        }
        new = {
            "sha256": "2" * 64,
            "entries": {"rs/a.class": {"sha256": "a" * 64}},
            "classes": {"rs/a.class": _class(structural="x")},
        }
        report = classify_class_deltas(
            old,
            new,
            {
                "matches": [
                    {
                        "old": "rs/a.class",
                        "new": "rs/a.class",
                        "strategy": "exact_sha256",
                        "score": 1.0,
                    }
                ],
                "ambiguous": [],
                "unmatched_old": [],
                "unmatched_new": [],
            },
        )
        self.assertEqual(report["classes"][0]["delta"], "byte_identical")

    def test_structurally_equivalent_move(self):
        old = {
            "entries": {"rs/a.class": {"sha256": "a" * 64}},
            "classes": {"rs/a.class": _class(structural="same")},
        }
        new = {
            "entries": {"rs/b.class": {"sha256": "b" * 64}},
            "classes": {"rs/b.class": _class(structural="same")},
        }
        row = classify_class_deltas(
            old,
            new,
            {
                "matches": [
                    {
                        "old": "rs/a.class",
                        "new": "rs/b.class",
                        "strategy": "structural_unique",
                        "score": 0.995,
                    }
                ],
                "ambiguous": [],
                "unmatched_old": [],
                "unmatched_new": [],
            },
        )["classes"][0]
        self.assertEqual(row["delta"], "structurally_equivalent")
        self.assertTrue(row["path_moved"])

    def test_constant_payload_candidate_is_conservative(self):
        method = {
            "name": "a",
            "descriptor": "()V",
            "access": 1,
            "code_length": 5,
            "attributes": ["Code"],
        }
        old = {
            "entries": {"rs/a.class": {"sha256": "a" * 64}},
            "classes": {
                "rs/a.class": _class(
                    structural="old",
                    numeric=[307],
                    methods=[method],
                )
            },
        }
        new = {
            "entries": {"rs/a.class": {"sha256": "b" * 64}},
            "classes": {
                "rs/a.class": _class(
                    structural="new",
                    numeric=[308],
                    methods=[method],
                )
            },
        }
        row = classify_class_deltas(
            old,
            new,
            {
                "matches": [
                    {
                        "old": "rs/a.class",
                        "new": "rs/a.class",
                        "strategy": "weighted_mutual_best",
                        "score": 0.99,
                    }
                ],
                "ambiguous": [],
                "unmatched_old": [],
                "unmatched_new": [],
            },
        )["classes"][0]
        self.assertEqual(row["delta"], "constant_payload_candidate")
        self.assertTrue(row["declarations_equal"])
        self.assertFalse(row["numeric_constants_equal"])

    def test_member_obfuscation_rename_and_modified_member(self):
        report = classify_member_deltas(
            {
                "old_sha256": "1" * 64,
                "new_sha256": "2" * 64,
                "classes": [
                    {
                        "old_owner": "rs/a.class",
                        "new_owner": "rs/b.class",
                        "fields": {
                            "relationships": [
                                {
                                    "old": {
                                        "name": "x",
                                        "descriptor": "Lrs/a;",
                                        "access": 2,
                                        "code_length": None,
                                    },
                                    "new": {
                                        "name": "y",
                                        "descriptor": "Lrs/b;",
                                        "access": 2,
                                        "code_length": None,
                                    },
                                    "strategy": "structural_unique",
                                    "score": 0.97,
                                }
                            ],
                            "unmatched_old": [{"name": "old", "descriptor": "I"}],
                            "unmatched_new": [{"name": "new", "descriptor": "I"}],
                        },
                        "methods": {
                            "relationships": [
                                {
                                    "old": {
                                        "name": "a",
                                        "descriptor": "()V",
                                        "access": 1,
                                        "code_length": 5,
                                    },
                                    "new": {
                                        "name": "a",
                                        "descriptor": "()V",
                                        "access": 1,
                                        "code_length": 9,
                                    },
                                    "strategy": "structural_unique",
                                    "score": 0.97,
                                }
                            ],
                            "unmatched_old": [],
                            "unmatched_new": [],
                        },
                    }
                ],
                "skipped_classes": [],
            }
        )
        by_kind = {row["kind"]: row for row in report["members"]}
        self.assertEqual(
            by_kind["field"]["delta"],
            "member_only_obfuscation_rename",
        )
        self.assertEqual(by_kind["method"]["delta"], "modified_member")
        self.assertEqual(report["summary"]["new_member_candidates"], 1)
        self.assertEqual(report["summary"]["removed_member_candidates"], 1)


if __name__ == "__main__":
    unittest.main()
