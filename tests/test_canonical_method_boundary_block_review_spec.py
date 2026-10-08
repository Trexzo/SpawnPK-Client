from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.canonical_method_boundary_block_review_spec import (
    CanonicalMethodBoundaryBlockReviewSpecError,
    _digest,
    build_canonical_method_boundary_block_review_spec,
)


class CanonicalMethodBoundaryBlockReviewSpecTests(unittest.TestCase):
    def _global(self):
        return {"report_id": "GLOBAL_TEST"}

    def _context(self):
        return {
            "schema_version": 1,
            "report_id": "METHODCTX_TEST",
            "kind": "canonical_method_field_context_identity_candidates",
            "canonical": False,
        }

    def _candidate(self, context):
        return {
            "relationship_id": "MEMREL_TEST",
            "old_owner": "rs/A",
            "new_owner": "rs/B",
            "old": {"name": "x", "descriptor": "I"},
            "new": {"name": "y", "descriptor": "I"},
            "strategy": (
                "canonical_method_unique_local_context_and_"
                "boundary_block_declaration_exact"
            ),
            "supports_existing_review": True,
            "confidence": "INFERRED_HIGH",
            "score": 0.9995,
            "canonical_methods": 2,
            "observations": 2,
            "distinct_contexts": 2,
            "method_witnesses": [
                {
                    "method_id": "M1",
                    "operation": "getfield",
                    "count": 1,
                    "contexts": [["a" * 64, 1]],
                },
                {
                    "method_id": "M2",
                    "operation": "putfield",
                    "count": 1,
                    "contexts": [["b" * 64, 1]],
                },
            ],
            "block_kind": "prefix_block_exact",
            "anchor_member_id": "ANCHOR",
            "block_length": 2,
            "target_offset": 0,
            "block_digest": "c" * 64,
            "target_signature_digest": "d" * 64,
            "base_context_report_id": "METHODCTX_TEST",
            "base_context_report_digest": _digest(context),
            "base_context_reason": "missing_two_sided_canonical_anchor",
            "base_global_usage_report_id": "GLOBAL_TEST",
        }

    def _report(self):
        context = self._context()
        return context, {
            "schema_version": 1,
            "kind": "canonical_method_boundary_block_identity_candidates",
            "canonical": False,
            "report_id": "METHODBOUNDARY_TEST",
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": "3" * 64,
            "base_global_usage_report_id": "GLOBAL_TEST",
            "base_global_usage_report_digest": _digest(self._global()),
            "base_context_report_id": "METHODCTX_TEST",
            "base_context_report_digest": _digest(context),
            "summary": {
                "input_context_missing_anchor_reviews": 2,
                "candidate_fields": 1,
                "remaining_without_boundary_block_proof": 1,
                "prefix_block_exact": 1,
                "suffix_block_exact": 0,
                "whole_class_exact": 0,
                "boundary_symmetry_mismatch": 0,
                "single_anchor_identity_mismatch": 0,
                "block_length_mismatch": 0,
                "block_shape_mismatch": 1,
                "target_offset_mismatch": 0,
                "target_signature_not_unique": 0,
            },
            "candidates": [self._candidate(context)],
            "rejected": [
                {
                    "relationship_id": "MEMREL_REJECTED",
                    "reason": "block_shape_mismatch",
                    "base_context_reason": (
                        "missing_two_sided_canonical_anchor"
                    ),
                }
            ],
        }

    def _build(self, report=None, *, context=None, recomputed=None):
        default_context, default_report = self._report()
        context = context or default_context
        report = report or default_report
        recomputed = copy.deepcopy(report) if recomputed is None else recomputed
        with patch(
            "spk_recovery.canonical_method_boundary_block_review_spec."
            "build_canonical_method_boundary_block_evidence",
            return_value=recomputed,
        ):
            return build_canonical_method_boundary_block_review_spec(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                self._global(),
                context,
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
        context, report = self._report()
        recomputed = copy.deepcopy(report)
        recomputed["candidates"][0]["block_digest"] = "e" * 64
        with self.assertRaisesRegex(
            CanonicalMethodBoundaryBlockReviewSpecError,
            "does not equal exact-JAR recomputation",
        ):
            self._build(
                report,
                context=context,
                recomputed=recomputed,
            )

    def test_candidate_remaining_accounting_must_balance(self):
        context, report = self._report()
        report["summary"]["remaining_without_boundary_block_proof"] = 2
        with self.assertRaisesRegex(
            CanonicalMethodBoundaryBlockReviewSpecError,
            "candidate\+remaining",
        ):
            self._build(report, context=context)

    def test_candidate_cannot_overlap_rejected(self):
        context, report = self._report()
        report["rejected"][0]["relationship_id"] = "MEMREL_TEST"
        with self.assertRaisesRegex(
            CanonicalMethodBoundaryBlockReviewSpecError,
            "overlapping",
        ):
            self._build(report, context=context)

    def test_witness_summary_drift_is_refused(self):
        context, report = self._report()
        report["candidates"][0]["observations"] = 3
        with self.assertRaisesRegex(
            CanonicalMethodBoundaryBlockReviewSpecError,
            "witness summary drift",
        ):
            self._build(report, context=context)

    def test_insufficient_independent_witness_is_refused(self):
        context, report = self._report()
        candidate = report["candidates"][0]
        candidate["method_witnesses"] = [
            {
                "method_id": "M1",
                "operation": "getfield",
                "count": 1,
                "contexts": [["a" * 64, 1]],
            }
        ]
        candidate["canonical_methods"] = 1
        candidate["observations"] = 1
        candidate["distinct_contexts"] = 1
        with self.assertRaisesRegex(
            CanonicalMethodBoundaryBlockReviewSpecError,
            "insufficient independent witness",
        ):
            self._build(report, context=context)

    def test_invalid_boundary_mode_is_refused(self):
        context, report = self._report()
        report["candidates"][0]["block_kind"] = "loose"
        with self.assertRaisesRegex(
            CanonicalMethodBoundaryBlockReviewSpecError,
            "invalid boundary block evidence",
        ):
            self._build(report, context=context)

    def test_whole_class_cannot_carry_anchor(self):
        context, report = self._report()
        candidate = report["candidates"][0]
        candidate["block_kind"] = "whole_class_exact"
        report["summary"]["prefix_block_exact"] = 0
        report["summary"]["whole_class_exact"] = 1
        with self.assertRaisesRegex(
            CanonicalMethodBoundaryBlockReviewSpecError,
            "whole-class proof cannot carry anchor",
        ):
            self._build(report, context=context)

    def test_block_digest_must_be_hex(self):
        context, report = self._report()
        report["candidates"][0]["block_digest"] = "z" * 64
        with self.assertRaisesRegex(
            CanonicalMethodBoundaryBlockReviewSpecError,
            "not hex",
        ):
            self._build(report, context=context)

    def test_rejected_reason_accounting_is_checked(self):
        context, report = self._report()
        report["summary"]["block_shape_mismatch"] = 0
        report["summary"]["block_length_mismatch"] = 1
        with self.assertRaisesRegex(
            CanonicalMethodBoundaryBlockReviewSpecError,
            "rejected detail accounting mismatch",
        ):
            self._build(report, context=context)

    def test_base_context_digest_is_bound(self):
        context, report = self._report()
        report["base_context_report_digest"] = "f" * 64
        report["candidates"][0]["base_context_report_digest"] = "f" * 64
        with self.assertRaisesRegex(
            CanonicalMethodBoundaryBlockReviewSpecError,
            "base context report digest drift",
        ):
            self._build(report, context=context)

    def test_empty_candidate_set_is_not_reviewable(self):
        context, report = self._report()
        report["summary"].update(
            {
                "candidate_fields": 0,
                "remaining_without_boundary_block_proof": 2,
                "prefix_block_exact": 0,
                "block_shape_mismatch": 2,
            }
        )
        report["candidates"] = []
        report["rejected"].append(
            {
                "relationship_id": "MEMREL_REJECTED_2",
                "reason": "block_shape_mismatch",
                "base_context_reason": (
                    "missing_two_sided_canonical_anchor"
                ),
            }
        )
        with self.assertRaisesRegex(
            CanonicalMethodBoundaryBlockReviewSpecError,
            "no reviewable candidates",
        ):
            self._build(report, context=context)


if __name__ == "__main__":
    unittest.main()
