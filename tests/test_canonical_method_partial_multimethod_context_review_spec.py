from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.canonical_method_partial_multimethod_context_review_spec import (
    CanonicalMethodPartialMultimethodContextReviewSpecError,
    build_canonical_method_partial_multimethod_context_review_spec,
)


class PartialMultimethodContextReviewSpecTests(unittest.TestCase):
    def _candidate(self):
        return {
            "relationship_id": "MEMREL_TEST",
            "logical_class_id": "CLIENT_CLASS_A",
            "old_owner": "rs/A",
            "new_owner": "rs/B",
            "old": {"name": "x", "descriptor": "I", "access": 9},
            "new": {"name": "x", "descriptor": "I", "access": 9},
            "strategy": (
                "canonical_method_partial_multimethod_unique_context_and_"
                "canonical_anchor_declaration_interval_exact"
            ),
            "confidence": "INFERRED_HIGH",
            "score": 0.9993,
            "supports_existing_review": True,
            "canonical_methods": 2,
            "observations": 2,
            "distinct_contexts": 2,
            "method_witnesses": [
                {
                    "method_id": "M1",
                    "operation": "getstatic",
                    "count": 1,
                    "contexts": [["a" * 64, 1]],
                },
                {
                    "method_id": "M3",
                    "operation": "getstatic",
                    "count": 1,
                    "contexts": [["b" * 64, 1]],
                },
            ],
            "symmetric_unavailable_methods": [
                {
                    "method_id": "M2",
                    "operation": "getstatic",
                    "expected_count": 1,
                    "old_context_count": 0,
                    "new_context_count": 0,
                }
            ],
            "left_anchor_member_id": "LEFT",
            "right_anchor_member_id": "RIGHT",
            "old_field_ordinal": 1,
            "new_field_ordinal": 1,
            "interval_offset": 0,
            "interval_length": 1,
            "interval_digest": "c" * 64,
            "target_signature_digest": "d" * 64,
            "base_context_report_id": "METHODCTX_TEST",
            "base_context_report_digest": "e" * 64,
            "base_context_reason": "canonical_method_context_missing",
            "base_global_usage_report_id": "GLOBAL_TEST",
        }

    def _report(self):
        return {
            "schema_version": 1,
            "kind": "canonical_method_partial_multimethod_context_identity_candidates",
            "canonical": False,
            "report_id": "PARTIALMETHODCTX_TEST",
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
                "input_missing_context_reviews": 1,
                "candidate_fields": 1,
                "remaining_without_partial_context_proof": 0,
                "no_symmetric_unavailable_context": 0,
                "partial_context_observation_count_mismatch": 0,
                "partial_context_mismatch": 0,
                "partial_context_nonunique": 0,
                "insufficient_surviving_context_witness": 0,
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

    def _build(self, report=None, recomputed=None):
        report = report or self._report()
        recomputed = copy.deepcopy(report) if recomputed is None else recomputed
        with patch(
            "spk_recovery.canonical_method_partial_multimethod_context_review_spec."
            "build_canonical_method_partial_multimethod_context_evidence",
            return_value=recomputed,
        ):
            return build_canonical_method_partial_multimethod_context_review_spec(
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
        self.assertEqual(spec["relationship_ids"], ["MEMREL_TEST"])

    def test_one_sided_unavailable_detail_is_refused(self):
        report = self._report()
        report["candidates"][0]["symmetric_unavailable_methods"][0][
            "new_context_count"
        ] = 1
        with self.assertRaisesRegex(
            CanonicalMethodPartialMultimethodContextReviewSpecError,
            "unavailable",
        ):
            self._build(report)

    def test_surviving_witness_summary_drift_is_refused(self):
        report = self._report()
        report["candidates"][0]["canonical_methods"] = 1
        with self.assertRaisesRegex(
            CanonicalMethodPartialMultimethodContextReviewSpecError,
            "surviving witness summary drift",
        ):
            self._build(report)

    def test_recomputation_drift_is_refused(self):
        report = self._report()
        recomputed = copy.deepcopy(report)
        recomputed["candidates"][0]["interval_digest"] = "f" * 64
        with self.assertRaisesRegex(
            CanonicalMethodPartialMultimethodContextReviewSpecError,
            "does not equal exact-JAR recomputation",
        ):
            self._build(report, recomputed)


if __name__ == "__main__":
    unittest.main()
