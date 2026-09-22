import unittest

from spk_recovery.confidence import MatchThresholds
from spk_recovery.matcher import match_classes


def _class(
    fp,
    *,
    strings=None,
    numbers=None,
    fields=None,
    methods=None,
    access=1,
    major=53,
    super_name="java/lang/Object",
    interfaces=None,
):
    fields = fields or []
    methods = methods or []
    return {
        "internal_name": "ignored",
        "major": major,
        "minor": 0,
        "access": access,
        "super_name": super_name,
        "interfaces": interfaces or [],
        "field_count": len(fields),
        "method_count": len(methods),
        "fields": fields,
        "methods": methods,
        "literal_strings": strings or [],
        "numeric_constants": numbers or [],
        "structural_sha256": fp,
    }


def _index(tag, classes, entry_meta=None):
    entry_meta = entry_meta or {}
    entries = {}
    for path in classes:
        meta = entry_meta.get(path, {})
        entries[path] = {
            "sha256": meta.get("sha256", f"{tag}-{path}"),
            "size": meta.get("size", 100),
        }
    return {"sha256": tag, "classes": classes, "entries": entries}


class MatcherTests(unittest.TestCase):
    def test_exact_hash_transfer_wins(self):
        old = _index(
            "old",
            {"rs/a.class": _class("old-fp")},
            {"rs/a.class": {"sha256": "same"}},
        )
        new = _index(
            "new",
            {"rs/a.class": _class("new-fp")},
            {"rs/a.class": {"sha256": "same"}},
        )
        report = match_classes(old, new)
        self.assertEqual(report["summary"]["exact_sha256"], 1)
        self.assertEqual(report["matches"][0]["strategy"], "exact_sha256")

    def test_unique_structural_move(self):
        old = _index("old", {"rs/a.class": _class("fp-1")})
        new = _index("new", {"rs/x.class": _class("fp-1")})
        report = match_classes(old, new)
        self.assertEqual(report["summary"]["structural_unique"], 1)
        self.assertEqual(
            (report["matches"][0]["old"], report["matches"][0]["new"]),
            ("rs/a.class", "rs/x.class"),
        )

    def test_weighted_changed_class_can_match(self):
        fields = [
            {
                "access": 2,
                "name": "a",
                "descriptor": "I",
                "attributes": [],
            }
        ]
        old_methods = [
            {
                "access": 1,
                "name": "a",
                "descriptor": "(II)V",
                "attributes": ["Code"],
                "code_length": 40,
            },
            {
                "access": 1,
                "name": "b",
                "descriptor": "()I",
                "attributes": ["Code"],
                "code_length": 18,
            },
        ]
        new_methods = [
            {
                "access": 1,
                "name": "q",
                "descriptor": "(II)V",
                "attributes": ["Code"],
                "code_length": 42,
            },
            {
                "access": 1,
                "name": "z",
                "descriptor": "()I",
                "attributes": ["Code"],
                "code_length": 18,
            },
        ]
        old = _index(
            "old",
            {
                "rs/a.class": _class(
                    "fp-old",
                    strings=["Adventure book", "Claim"],
                    numbers=[185, 42],
                    fields=fields,
                    methods=old_methods,
                )
            },
            {"rs/a.class": {"size": 1000}},
        )
        new = _index(
            "new",
            {
                "rs/z.class": _class(
                    "fp-new",
                    strings=["Adventure book", "Claim"],
                    numbers=[185, 42],
                    fields=fields,
                    methods=new_methods,
                )
            },
            {"rs/z.class": {"size": 1010}},
        )
        report = match_classes(
            old,
            new,
            thresholds=MatchThresholds(
                minimum_score=0.75,
                minimum_margin=0.05,
            ),
        )
        self.assertEqual(report["summary"]["weighted_mutual_best"], 1)
        self.assertEqual(
            report["matches"][0]["strategy"],
            "weighted_mutual_best",
        )

    def test_tie_stays_ambiguous(self):
        fields = [
            {
                "access": 2,
                "name": "a",
                "descriptor": "I",
                "attributes": [],
            }
        ]
        methods = [
            {
                "access": 1,
                "name": "a",
                "descriptor": "()V",
                "attributes": ["Code"],
                "code_length": 10,
            }
        ]
        old = _index(
            "old",
            {
                "rs/a.class": _class(
                    "old",
                    strings=["same"],
                    numbers=[7],
                    fields=fields,
                    methods=methods,
                )
            },
        )
        new = _index(
            "new",
            {
                "rs/x.class": _class(
                    "x",
                    strings=["same"],
                    numbers=[7],
                    fields=fields,
                    methods=methods,
                ),
                "rs/y.class": _class(
                    "y",
                    strings=["same"],
                    numbers=[7],
                    fields=fields,
                    methods=methods,
                ),
            },
        )
        report = match_classes(
            old,
            new,
            thresholds=MatchThresholds(
                minimum_score=0.80,
                minimum_margin=0.05,
            ),
        )
        self.assertEqual(report["summary"]["weighted_mutual_best"], 0)
        self.assertEqual(report["summary"]["ambiguous"], 1)
        self.assertIn("rs/a.class", report["unmatched_old"])




    def test_package_anchor_requires_strong_structural_support(self):
        old_classes = {}
        new_classes = {}
        for i in range(5):
            old_classes[f"rs/m/a{i}.class"] = _class(f"anchor-{i}")
            new_classes[f"rs/l/a{i}.class"] = _class(f"anchor-{i}")

        fields = [
            {
                "access": 2,
                "name": "a",
                "descriptor": "I",
                "attributes": [],
            }
        ]
        old_classes["rs/m/target.class"] = _class(
            "old-target",
            fields=fields,
        )
        new_classes["rs/l/target.class"] = _class(
            "new-target",
            fields=fields,
        )

        report = match_classes(
            _index("old", old_classes),
            _index("new", new_classes),
        )
        package_matches = [
            m
            for m in report["matches"]
            if m["strategy"] == "package_anchor"
        ]
        self.assertEqual(len(package_matches), 1)
        self.assertEqual(
            (
                package_matches[0]["old"],
                package_matches[0]["new"],
            ),
            ("rs/m/target.class", "rs/l/target.class"),
        )
        self.assertEqual(
            package_matches[0]["evidence"]["package_anchor"]["support"],
            5,
        )

    def test_package_anchor_does_not_fire_below_support_floor(self):
        old_classes = {}
        new_classes = {}
        for i in range(4):
            old_classes[f"rs/m/a{i}.class"] = _class(f"anchor-{i}")
            new_classes[f"rs/l/a{i}.class"] = _class(f"anchor-{i}")

        fields = [
            {
                "access": 2,
                "name": "a",
                "descriptor": "I",
                "attributes": [],
            }
        ]
        old_classes["rs/m/target.class"] = _class(
            "old-target",
            fields=fields,
        )
        new_classes["rs/l/target.class"] = _class(
            "new-target",
            fields=fields,
        )

        report = match_classes(
            _index("old", old_classes),
            _index("new", new_classes),
        )
        self.assertEqual(
            report["summary"]["package_anchor"],
            0,
        )
        self.assertIn(
            "rs/m/target.class",
            report["unmatched_old"],
        )

if __name__ == "__main__":
    unittest.main()
