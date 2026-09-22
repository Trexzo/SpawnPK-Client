import unittest

from spk_recovery.semantic_dossier import (
    build_semantic_dossiers,
    classify_semantic_literal,
)


def _index():
    return {
        "sha256": "a" * 64,
        "classes": {
            "rs/a.class": {
                "internal_name": "rs/a",
                "literal_strings": [
                    "Collection Log",
                    "drops/collection",
                    "SHARED_TOKEN",
                    "Line 1",
                ],
                "numeric_constants": [
                    54302,
                    54303,
                    2,
                ],
            },
            "rs/b.class": {
                "internal_name": "rs/b",
                "literal_strings": [
                    "SHARED_TOKEN",
                    "Common label",
                ],
                "numeric_constants": [],
            },
            "other/c.class": {
                "internal_name": "other/c",
                "literal_strings": [
                    "Outside scope",
                ],
                "numeric_constants": [],
            },
        },
    }


class SemanticDossierTests(unittest.TestCase):
    def test_literal_classification_is_descriptive(self):
        self.assertEqual(
            classify_semantic_literal(
                "orbs/adventure_orb"
            ),
            "resource_path",
        )
        self.assertEqual(
            classify_semantic_literal(
                "BEGIN_ADVENTURE"
            ),
            "control_token",
        )
        self.assertEqual(
            classify_semantic_literal(
                "::adventurebook"
            ),
            "command",
        )
        self.assertEqual(
            classify_semantic_literal(
                "Adventure Book"
            ),
            "ui_text",
        )
        self.assertIsNone(
            classify_semantic_literal("Line 1")
        )

    def test_unique_anchor_outscores_shared_anchor(self):
        out = build_semantic_dossiers(
            _index(),
            max_document_frequency=8,
        )
        by_path = {
            row["entry_path"]: row
            for row in out["dossiers"]
        }
        a = by_path["rs/a.class"]
        b = by_path["rs/b.class"]
        self.assertGreater(
            a["semantic_score"],
            b["semantic_score"],
        )
        self.assertGreater(
            a["unique_anchor_count"],
            0,
        )

    def test_widget_constants_are_evidence_only(self):
        out = build_semantic_dossiers(_index())
        first = next(
            row
            for row in out["dossiers"]
            if row["entry_path"] == "rs/a.class"
        )
        self.assertEqual(
            first["likely_widget_constants"],
            [54302, 54303],
        )

    def test_scope_and_output_are_noncanonical(self):
        out = build_semantic_dossiers(_index())
        self.assertFalse(out["canonical"])
        self.assertEqual(
            out["kind"],
            "semantic_dossiers",
        )
        self.assertEqual(
            out["summary"]["scoped_class_count"],
            2,
        )
        self.assertTrue(
            all(
                row["entry_path"].startswith("rs/")
                for row in out["dossiers"]
            )
        )

    def test_output_order_is_deterministic(self):
        first = build_semantic_dossiers(_index())
        second = build_semantic_dossiers(_index())
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
