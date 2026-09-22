import copy
import unittest

from spk_recovery.roundtrip_verify import compare_project_classes


def _class(*, code_length=5, literal="x", field_desc="I"):
    return {
        "internal_name": "rs/A",
        "major": 53,
        "minor": 0,
        "access": 1,
        "super_name": "java/lang/Object",
        "interfaces": [],
        "fields": [
            {
                "access": 1,
                "name": "value",
                "descriptor": field_desc,
                "attributes": [],
            }
        ],
        "methods": [
            {
                "access": 1,
                "name": "run",
                "descriptor": "()V",
                "attributes": ["Code"],
                "code_length": code_length,
            }
        ],
        "literal_strings": [literal],
        "numeric_constants": [7],
        "structural_sha256": "same" if code_length == 5 else "changed",
    }


def _index(cls, *, entry_sha="a"):
    return {
        "entries": {
            "rs/A.class": {
                "sha256": entry_sha * 64,
            }
        },
        "classes": {
            "rs/A.class": cls,
        },
    }


class RoundTripCompareTests(unittest.TestCase):
    def test_byte_identical_wins(self):
        a = _index(_class(), entry_sha="a")
        b = copy.deepcopy(a)
        out = compare_project_classes(a, b, prefixes=["rs/"])
        self.assertEqual(out["summary"]["byte_identical"], 1)
        self.assertEqual(out["summary"]["blockers"], 0)

    def test_codegen_only_variance_is_not_semantic_surface_drift(self):
        a = _index(_class(code_length=5), entry_sha="a")
        b = _index(_class(code_length=8), entry_sha="b")
        out = compare_project_classes(a, b, prefixes=["rs/"])
        self.assertEqual(out["summary"]["codegen_variance_only"], 1)
        self.assertEqual(out["summary"]["semantic_surface_drift"], 0)
        self.assertEqual(out["summary"]["blockers"], 0)

    def test_literal_change_blocks_candidate(self):
        a = _index(_class(literal="before"), entry_sha="a")
        b = _index(_class(literal="after"), entry_sha="b")
        out = compare_project_classes(a, b, prefixes=["rs/"])
        self.assertEqual(out["summary"]["semantic_surface_drift"], 1)
        self.assertEqual(out["summary"]["blockers"], 1)
        self.assertIn("literal_strings", out["classes"][0]["differences"])

    def test_member_signature_change_blocks_candidate(self):
        a = _index(_class(field_desc="I"), entry_sha="a")
        b = _index(_class(field_desc="J"), entry_sha="b")
        out = compare_project_classes(a, b, prefixes=["rs/"])
        self.assertEqual(out["summary"]["semantic_surface_drift"], 1)
        self.assertIn("fields", out["classes"][0]["differences"])

    def test_missing_and_unexpected_classes_block(self):
        a = _index(_class(), entry_sha="a")
        b = {
            "entries": {
                "rs/B.class": {"sha256": "b" * 64},
            },
            "classes": {
                "rs/B.class": {
                    **_class(),
                    "internal_name": "rs/B",
                },
            },
        }
        out = compare_project_classes(a, b, prefixes=["rs/"])
        self.assertEqual(out["summary"]["missing"], 1)
        self.assertEqual(out["summary"]["unexpected"], 1)
        self.assertEqual(out["summary"]["blockers"], 2)


if __name__ == "__main__":
    unittest.main()
