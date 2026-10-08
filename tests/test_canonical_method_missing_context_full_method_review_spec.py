from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.canonical_method_missing_context_full_method_review_spec import (
    CanonicalMethodMissingContextFullMethodReviewSpecError,
    build_canonical_method_missing_context_full_method_review_spec,
)


class CanonicalMethodMissingContextFullMethodReviewSpecTests(unittest.TestCase):
    def _candidate(self):
        return {
            "relationship_id": "MEMREL_TEST",
            "logical_class_id": "CLIENT_CLASS_A",
            "old_owner": "rs/A",
            "new_owner": "rs/B",
            "old": {"name": "x", "descriptor": "I", "access": 1},
            "new": {"name": "x", "descriptor": "I", "access": 1},
            "strategy": (
                "canonical_method_full_normalized_fingerprint_and_"
                "canonical_anchor_declaration_interval_exact"
            ),
            "confidence": "INFERRED_HIGH",
            "score": 0.9993,
            "supports_existing_review": True,
            "method_id": "M1",
            "operation": "getstatic",
            "expected_count": 1,
            "full_method_instruction_count": 2,
            "full_method_fingerprint_digest": "a" * 64,
            "left_anchor_member_id": "LEFT",
            "right_anchor_member_id": "RIGHT",
            "old_field_ordinal": 1,
            "new_field_ordinal": 1,
            "interval_offset": 0,
            "interval_length": 1,
            "interval_digest": "b" * 64,
            "target_signature_digest": "c" * 64,
            "base_context_report_id": "METHODCTX_TEST",
            "base_context_report_digest": "d" * 64,
            "base_context_reason": "canonical_method_context_missing",
            "base_global_usage_report_id": "GLOBAL_TEST",
        }

    def _report(self):
        return {
            "schema_version": 1,
            "kind": (
                "canonical_method_missing_context_full_method_"
                "identity_candidates"
            ),
            "canonical": False,
            "report_id": "MISSINGCTXFULL_TEST",
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": "3" * 64,
            "base_global_usage_report_id": "GLOBAL_TEST",
            "base_global_usage_report_digest": "4" * 64,
            "base_context_report_id": "METHODCTX_TEST",
            "base_context_report_digest": "5" * 64,
            "summary": {
                "input_context_missing_reviews": 1,
                "candidate_fields": 1,
                "remaining_without_full_method_proof": 0,
                "missing_context_shape_mismatch": 0,
                "full_method_target_access_mismatch": 0,
                "full_method_fingerprint_mismatch": 0,
                "full_method_fingerprint_nonunique": 0,
                "missing_two_sided_canonical_anchor": 0,
                "canonical_anchor_identity_mismatch": 0,
                "declaration_interval_length_mismatch": 0,
                "declaration_interval_shape_mismatch": 0,
                "target_interval_offset_mismatch": 0,
                "target_declaration_signature_not_unique": 0,
            },
            "candidates": [self._candidate()],
            "rejected": [],
        }

    def _build(self, report=None, *, recomputed=None):
        report = report or self._report()
        recomputed = copy.deepcopy(report) if recomputed is None else recomputed
        with patch(
            "spk_recovery.canonical_method_missing_context_full_method_review_spec."
            "build_canonical_method_missing_context_full_method_evidence",
            return_value=recomputed,
        ):
            return build_canonical_method_missing_context_full_method_review_spec(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                {"report_id": "GLOBAL_TEST"},
                {"report_id": "METHODCTX_TEST"},
                report,
            )

    def test_exact_recomputation_emits_review_spec(self):
        spec = self._build()
        self.assertEqual(
            spec["kind"],
            "reviewed_member_identity_acceptance_spec",
        )
        self.assertEqual(spec["relationship_ids"], ["MEMREL_TEST"])

    def test_recomputation_drift_is_refused(self):
        report = self._report()
        recomputed = copy.deepcopy(report)
        recomputed["candidates"][0]["full_method_fingerprint_digest"] = "e" * 64
        with self.assertRaisesRegex(
            CanonicalMethodMissingContextFullMethodReviewSpecError,
            "does not equal exact-JAR recomputation",
        ):
            self._build(report, recomputed=recomputed)

    def test_wrong_score_is_refused(self):
        report = self._report()
        report["candidates"][0]["score"] = 0.5
        with self.assertRaisesRegex(
            CanonicalMethodMissingContextFullMethodReviewSpecError,
            "not trusted",
        ):
            self._build(report)

    def test_invalid_fingerprint_digest_is_refused(self):
        report = self._report()
        report["candidates"][0]["full_method_fingerprint_digest"] = "z" * 64
        with self.assertRaisesRegex(
            CanonicalMethodMissingContextFullMethodReviewSpecError,
            "not hex",
        ):
            self._build(report)

    def test_empty_candidate_set_is_not_reviewable(self):
        report = self._report()
        report["summary"]["candidate_fields"] = 0
        report["summary"]["remaining_without_full_method_proof"] = 1
        report["summary"]["full_method_fingerprint_mismatch"] = 1
        report["candidates"] = []
        report["rejected"] = [
            {
                "relationship_id": "MEMREL_TEST",
                "reason": "full_method_fingerprint_mismatch",
                "base_context_reason": "canonical_method_context_missing",
            }
        ]
        with self.assertRaisesRegex(
            CanonicalMethodMissingContextFullMethodReviewSpecError,
            "no reviewable candidates",
        ):
            self._build(report)


if __name__ == "__main__":
    unittest.main()
