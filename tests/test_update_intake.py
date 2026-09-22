from __future__ import annotations

import unittest
from unittest.mock import patch

from spk_recovery.update_intake import (
    UpdateIntakeError,
    build_update_intake,
)


def _index(sha: str) -> dict:
    return {
        "sha256": sha,
        "entries": {
            "rs/a.class": {"sha256": "1" * 64, "size": 10},
            "rs/b.class": {"sha256": "2" * 64, "size": 20},
        },
        "classes": {
            "rs/a.class": {
                "internal_name": "rs/a",
                "structural_sha256": "a" * 64,
                "major": 53,
                "minor": 0,
                "access": 1,
                "fields": [],
                "methods": [],
                "literal_strings": [],
                "numeric_constants": [],
            },
            "rs/b.class": {
                "internal_name": "rs/b",
                "structural_sha256": "b" * 64,
                "major": 53,
                "minor": 0,
                "access": 1,
                "fields": [],
                "methods": [],
                "literal_strings": [],
                "numeric_constants": [],
            },
        },
    }


class UpdateIntakeTests(unittest.TestCase):
    def test_exact_and_structural_reuse_stay_out_of_review_queue(self):
        old = _index("1" * 64)
        new = _index("2" * 64)
        matcher = {
            "summary": {
                "old_class_count": 2,
                "new_class_count": 2,
                "matched": 2,
                "exact_sha256": 1,
                "structural_unique": 1,
                "package_anchor": 0,
                "weighted_mutual_best": 0,
                "ambiguous": 0,
                "unmatched_old": 0,
                "unmatched_new": 0,
            },
            "matches": [
                {
                    "old": "rs/a.class",
                    "new": "rs/a.class",
                    "strategy": "exact_sha256",
                    "score": 1.0,
                    "confidence": "EXACT",
                },
                {
                    "old": "rs/b.class",
                    "new": "rs/c.class",
                    "strategy": "structural_unique",
                    "score": 0.995,
                    "confidence": "CROSS_BUILD",
                },
            ],
            "ambiguous": [],
            "unmatched_old": [],
            "unmatched_new": [],
            "package_anchors": {},
        }
        diff = {
            "summary": {
                "exact_unchanged_entries": 1,
                "changed_same_path_entries": 0,
                "added_entries": 1,
                "removed_entries": 1,
                "unique_structural_class_moves": 1,
                "ambiguous_structural_groups": 0,
            },
            "changed_same_path": [],
        }

        with (
            patch("spk_recovery.update_intake.match_classes", return_value=matcher),
            patch("spk_recovery.update_intake.diff_indexes", return_value=diff),
        ):
            report = build_update_intake(
                old,
                new,
                old_build_id="v307",
                new_build_id="v308",
            )

        self.assertEqual(report["summary"]["matched_classes"], 2)
        self.assertEqual(
            report["summary"]["class_identity_reuse_percent"],
            100.0,
        )
        self.assertEqual(report["analysis_queue"], [])
        self.assertEqual(
            report["classifications"]["byte_identical_same_path"],
            1,
        )
        self.assertEqual(
            report["classifications"]["structurally_equivalent_moved"],
            1,
        )

    def test_inferred_ambiguous_and_unmatched_stay_in_review_queue(self):
        old = _index("3" * 64)
        new = _index("4" * 64)
        matcher = {
            "summary": {
                "old_class_count": 4,
                "new_class_count": 4,
                "matched": 2,
                "exact_sha256": 0,
                "structural_unique": 0,
                "package_anchor": 1,
                "weighted_mutual_best": 1,
                "ambiguous": 1,
                "unmatched_old": 1,
                "unmatched_new": 1,
            },
            "matches": [
                {
                    "old": "rs/a.class",
                    "new": "rs/c.class",
                    "strategy": "package_anchor",
                    "score": 0.95,
                    "confidence": "INFERRED_HIGH",
                },
                {
                    "old": "rs/b.class",
                    "new": "rs/d.class",
                    "strategy": "weighted_mutual_best",
                    "score": 0.91,
                    "confidence": "INFERRED_MEDIUM",
                },
            ],
            "ambiguous": [
                {
                    "old": "rs/e.class",
                    "reason": "weighted_match_not_decisive",
                    "candidates": [{"new": "rs/f.class", "score": 0.9}],
                }
            ],
            "unmatched_old": ["rs/g.class"],
            "unmatched_new": ["rs/h.class"],
            "package_anchors": {},
        }
        diff = {
            "summary": {
                "exact_unchanged_entries": 0,
                "changed_same_path_entries": 0,
                "added_entries": 0,
                "removed_entries": 0,
                "unique_structural_class_moves": 0,
                "ambiguous_structural_groups": 0,
            },
            "changed_same_path": [],
        }

        with (
            patch("spk_recovery.update_intake.match_classes", return_value=matcher),
            patch("spk_recovery.update_intake.diff_indexes", return_value=diff),
        ):
            report = build_update_intake(
                old,
                new,
                old_build_id="old",
                new_build_id="new",
            )

        kinds = {item["kind"] for item in report["analysis_queue"]}
        self.assertEqual(
            kinds,
            {
                "class_identity_review",
                "ambiguous_class_identity",
                "unmatched_old_class",
                "unmatched_new_class",
            },
        )
        self.assertEqual(report["summary"]["analysis_queue_items"], 5)

    def test_build_ids_must_differ(self):
        with self.assertRaises(UpdateIntakeError):
            build_update_intake(
                _index("5" * 64),
                _index("6" * 64),
                old_build_id="v308",
                new_build_id="v308",
            )

    def test_migration_id_is_deterministic(self):
        old = _index("7" * 64)
        new = _index("8" * 64)
        matcher = {
            "summary": {
                "old_class_count": 0,
                "new_class_count": 0,
                "matched": 0,
                "exact_sha256": 0,
                "structural_unique": 0,
                "package_anchor": 0,
                "weighted_mutual_best": 0,
                "ambiguous": 0,
                "unmatched_old": 0,
                "unmatched_new": 0,
            },
            "matches": [],
            "ambiguous": [],
            "unmatched_old": [],
            "unmatched_new": [],
            "package_anchors": {},
        }
        diff = {"summary": {}, "changed_same_path": []}
        with (
            patch("spk_recovery.update_intake.match_classes", return_value=matcher),
            patch("spk_recovery.update_intake.diff_indexes", return_value=diff),
        ):
            a = build_update_intake(
                old,
                new,
                old_build_id="v308",
                new_build_id="v309",
            )
            b = build_update_intake(
                old,
                new,
                old_build_id="v308",
                new_build_id="v309",
            )
        self.assertEqual(a["migration_id"], b["migration_id"])


if __name__ == "__main__":
    unittest.main()
