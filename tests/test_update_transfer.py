from __future__ import annotations

import unittest

from spk_recovery.update_transfer import (
    UpdateTransferError,
    _trusted_match_report,
    _validate_intake_binding,
)


class UpdateTransferTests(unittest.TestCase):
    def test_only_exact_and_unique_structural_auto_transfer(self):
        matcher = {
            "schema_version": 1,
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "scope_prefix": "rs/",
            "summary": {},
            "matches": [
                {
                    "old": "rs/a.class",
                    "new": "rs/a.class",
                    "strategy": "exact_sha256",
                    "score": 1.0,
                    "confidence": "EXACT",
                    "evidence": {},
                },
                {
                    "old": "rs/b.class",
                    "new": "rs/c.class",
                    "strategy": "structural_unique",
                    "score": 0.995,
                    "confidence": "CROSS_BUILD",
                    "evidence": {},
                },
                {
                    "old": "rs/d.class",
                    "new": "rs/e.class",
                    "strategy": "package_anchor",
                    "score": 0.96,
                    "confidence": "INFERRED_HIGH",
                    "evidence": {"package_anchor": {}},
                },
                {
                    "old": "rs/f.class",
                    "new": "rs/g.class",
                    "strategy": "weighted_mutual_best",
                    "score": 0.92,
                    "confidence": "INFERRED_MEDIUM",
                    "evidence": {},
                },
            ],
            "ambiguous": [{"old": "rs/h.class"}],
            "unmatched_old": ["rs/i.class"],
            "unmatched_new": ["rs/j.class"],
        }

        filtered, summary = _trusted_match_report(matcher)
        self.assertEqual(
            [m["strategy"] for m in filtered["matches"]],
            ["exact_sha256", "structural_unique"],
        )
        self.assertEqual(summary["trusted_exact"], 1)
        self.assertEqual(summary["trusted_structural"], 1)
        self.assertEqual(summary["review_only_matches"], 2)
        self.assertEqual(len(filtered["ambiguous"]), 3)

    def test_intake_binding_is_exact(self):
        old_index = {"sha256": "1" * 64}
        new_index = {"sha256": "2" * 64}
        report = {
            "schema_version": 1,
            "kind": "update_intake_report",
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
        }
        _validate_intake_binding(
            report,
            old_index,
            new_index,
            old_build_id="v308",
            new_build_id="v309",
        )

        changed = dict(report)
        changed["new_sha256"] = "3" * 64
        with self.assertRaises(UpdateTransferError):
            _validate_intake_binding(
                changed,
                old_index,
                new_index,
                old_build_id="v308",
                new_build_id="v309",
            )

    def test_intake_build_ids_are_bound(self):
        report = {
            "schema_version": 1,
            "kind": "update_intake_report",
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
        }
        with self.assertRaises(UpdateTransferError):
            _validate_intake_binding(
                report,
                {"sha256": "1" * 64},
                {"sha256": "2" * 64},
                old_build_id="v307",
                new_build_id="v309",
            )


if __name__ == "__main__":
    unittest.main()
