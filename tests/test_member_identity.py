import unittest

from spk_recovery.member_identity import (
    build_member_identity_candidates,
    match_members_in_class,
)


def _method(name, descriptor, code_length, access=1):
    return {
        "name": name,
        "descriptor": descriptor,
        "access": access,
        "attributes": ["Code"],
        "code_length": code_length,
    }


def _field(name, descriptor, access=2):
    return {
        "name": name,
        "descriptor": descriptor,
        "access": access,
        "attributes": [],
    }


def _class(methods=None, fields=None):
    return {
        "methods": methods or [],
        "fields": fields or [],
    }


class MemberIdentityTests(unittest.TestCase):
    def test_stable_method_symbol_transfers(self):
        old = _class(methods=[_method("a", "(Lrs/a;)V", 20)])
        new = _class(methods=[_method("a", "(Lrs/z;)V", 20)])
        out = match_members_in_class(
            "rs/a.class",
            old,
            "rs/z.class",
            new,
            kind="methods",
        )
        self.assertEqual(out["summary"]["matched"], 1)
        self.assertEqual(
            out["relationships"][0]["strategy"],
            "stable_symbol",
        )

    def test_renamed_method_uses_unique_structure(self):
        old = _class(methods=[_method("a", "(II)V", 41)])
        new = _class(methods=[_method("q", "(II)V", 41)])
        out = match_members_in_class(
            "rs/a.class",
            old,
            "rs/z.class",
            new,
            kind="methods",
        )
        self.assertEqual(out["summary"]["matched"], 1)
        self.assertEqual(out["summary"]["renamed"], 1)
        self.assertEqual(
            out["relationships"][0]["strategy"],
            "structural_unique",
        )

    def test_ambiguous_methods_are_not_guessed(self):
        old = _class(
            methods=[
                _method("a", "()V", 10),
                _method("b", "()V", 10),
            ]
        )
        new = _class(
            methods=[
                _method("x", "()V", 10),
                _method("y", "()V", 10),
            ]
        )
        out = match_members_in_class(
            "rs/a.class",
            old,
            "rs/z.class",
            new,
            kind="methods",
        )
        self.assertEqual(out["summary"]["matched"], 0)
        self.assertEqual(out["summary"]["unmatched_old"], 2)
        self.assertEqual(out["summary"]["unmatched_new"], 2)

    def test_constructors_are_excluded(self):
        old = _class(
            methods=[
                _method("<init>", "()V", 5),
                _method("a", "()V", 10),
            ]
        )
        new = _class(
            methods=[
                _method("<init>", "()V", 5),
                _method("a", "()V", 10),
            ]
        )
        out = match_members_in_class(
            "rs/a.class",
            old,
            "rs/a.class",
            new,
            kind="methods",
        )
        self.assertEqual(out["summary"]["old_count"], 1)
        self.assertEqual(out["summary"]["matched"], 1)

    def test_renamed_field_uses_unique_structure(self):
        old = _class(fields=[_field("a", "Lrs/a;")])
        new = _class(fields=[_field("q", "Lrs/z;")])
        out = match_members_in_class(
            "rs/a.class",
            old,
            "rs/z.class",
            new,
            kind="fields",
        )
        self.assertEqual(out["summary"]["matched"], 1)
        self.assertEqual(out["summary"]["renamed"], 1)
        self.assertEqual(
            out["relationships"][0]["strategy"],
            "structural_unique",
        )

    def test_external_reference_overloads_remain_distinct(self):
        old = _class(
            methods=[
                _method("a", "(Ljava/lang/String;)V", 6),
                _method("a", "(Ljava/awt/Color;)V", 6),
            ]
        )
        new = _class(
            methods=[
                _method("a", "(Ljava/lang/String;)V", 6),
                _method("a", "(Ljava/awt/Color;)V", 6),
            ]
        )
        out = match_members_in_class(
            "rs/ui/a.class",
            old,
            "rs/ui/a.class",
            new,
            kind="methods",
        )
        self.assertEqual(out["summary"]["matched"], 2)
        self.assertEqual(out["summary"]["unmatched_old"], 0)

    def test_known_rs_type_lineage_disambiguates_overloads(self):
        old = {
            "sha256": "a",
            "classes": {
                "rs/owner.class": _class(
                    methods=[
                        _method("a", "(Lrs/typeA;)V", 6),
                        _method("a", "(Lrs/typeB;)V", 6),
                    ]
                ),
                "rs/typeA.class": _class(),
                "rs/typeB.class": _class(),
            },
        }
        new = {
            "sha256": "b",
            "classes": {
                "rs/newOwner.class": _class(
                    methods=[
                        _method("a", "(Lrs/x;)V", 6),
                        _method("a", "(Lrs/y;)V", 6),
                    ]
                ),
                "rs/x.class": _class(),
                "rs/y.class": _class(),
            },
        }
        report = {
            "matches": [
                {
                    "old": "rs/owner.class",
                    "new": "rs/newOwner.class",
                    "strategy": "structural_unique",
                    "score": 0.995,
                },
                {
                    "old": "rs/typeA.class",
                    "new": "rs/x.class",
                    "strategy": "structural_unique",
                    "score": 0.995,
                },
                {
                    "old": "rs/typeB.class",
                    "new": "rs/y.class",
                    "strategy": "structural_unique",
                    "score": 0.995,
                },
            ]
        }
        out = build_member_identity_candidates(old, new, report)
        owner = next(
            row
            for row in out["classes"]
            if row["old_owner"] == "rs/owner.class"
        )
        self.assertEqual(owner["methods"]["summary"]["matched"], 2)
        self.assertEqual(owner["methods"]["summary"]["unmatched_old"], 0)

    def test_research_only_class_strategy_is_skipped(self):
        old = {
            "sha256": "a",
            "classes": {
                "rs/a.class": _class(
                    methods=[_method("a", "()V", 10)]
                )
            },
        }
        new = {
            "sha256": "b",
            "classes": {
                "rs/b.class": _class(
                    methods=[_method("a", "()V", 10)]
                )
            },
        }
        report = {
            "matches": [
                {
                    "old": "rs/a.class",
                    "new": "rs/b.class",
                    "strategy": "package_anchor",
                    "score": 0.9,
                }
            ]
        }
        out = build_member_identity_candidates(old, new, report)
        self.assertEqual(out["summary"]["class_pairs"], 0)
        self.assertEqual(len(out["skipped_classes"]), 1)


if __name__ == "__main__":
    unittest.main()
