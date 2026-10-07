from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.canonical_method_field_context_review_spec import (
    CanonicalMethodFieldContextReviewSpecError,
    build_canonical_method_field_context_review_spec,
)


class CanonicalMethodFieldContextReviewSpecTests(unittest.TestCase):
    def _candidate(self):
        return {
            "relationship_id": "MEMREL_TEST",
            "old_owner": "rs/A",
            "new_owner": "rs/B",
            "old": {"name": "x", "descriptor": "I"},
            "new": {"name": "y", "descriptor": "I"},
            "strategy": (
                "canonical_method_unique_local_context_and_"
                "canonical_anchor_declaration_interval_exact"
            ),
            "supports_existing_review": True,
            "confidence": "INFERRED_HIGH",
            "score": 0.9994,
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
            "left_anchor_member_id": "LEFT",
            "right_anchor_member_id": "RIGHT",
            "interval_digest": "c" * 64,
            "interval_length": 1,
            "interval_offset": 0,
            "old_field_ordinal": 1,
            "new_field_ordinal": 1,
            "base_global_usage_report_id": "GLOBAL_TEST",
            "base_global_usage_outcome": (
                "global_class_topology_guard_rejected"
            ),
        }

    def _report(self):
        return {
            "schema_version": 1,
            "kind": "canonical_method_field_context_identity_candidates",
            "canonical": False,
            "report_id": "METHODCTX_TEST",
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": "3" * 64,
            "base_global_usage_report_id": "GLOBAL_TEST",
            "base_global_usage_report_digest": "4" * 64,
            "summary": {
                "input_global_class_topology_guard_rejected": 2,
                "candidate_fields": 1,
                "remaining_without_context_proof": 1,
                "canonical_method_context_missing": 0,
                "canonical_method_context_mismatch": 1,
                "canonical_method_context_nonunique": 0,
                "insufficient_independent_context_witness": 0,
                "missing_two_sided_canonical_anchor": 0,
                "canonical_anchor_identity_mismatch": 0,
                "declaration_interval_length_mismatch": 0,
                "declaration_interval_shape_mismatch": 0,
                "target_interval_offset_mismatch": 0,
                "target_declaration_signature_not_unique": 0,
            },
            "candidates": [self._candidate()],
            "rejected": [
                {
                    "relationship_id": "MEMREL_REJECTED",
                    "reason": "canonical_method_context_mismatch",
                    "base_global_usage_outcome": (
                        "global_class_topology_guard_rejected"
                    ),
                }
            ],
        }

    def _build(self, report=None, *, recomputed=None):
        report = report or self._report()
        recomputed = copy.deepcopy(report) if recomputed is None else recomputed
        with patch(
            "spk_recovery.canonical_method_field_context_review_spec."
            "build_canonical_method_field_context_evidence",
            return_value=recomputed,
        ):
            return build_canonical_method_field_context_review_spec(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                {"report_id": "GLOBAL_TEST"},
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
        recomputed["candidates"][0]["interval_digest"] = "d" * 64
        with self.assertRaisesRegex(
            CanonicalMethodFieldContextReviewSpecError,
            "does not equal exact-JAR recomputation",
        ):
            self._build(report, recomputed=recomputed)

    def test_candidate_remaining_accounting_must_balance(self):
        report = self._report()
        report["summary"]["remaining_without_context_proof"] = 2
        with self.assertRaisesRegex(
            CanonicalMethodFieldContextReviewSpecError,
            "candidate\+remaining",
        ):
            self._build(report)

    def test_candidate_cannot_overlap_rejected(self):
        report = self._report()
        report["rejected"][0]["relationship_id"] = "MEMREL_TEST"
        with self.assertRaisesRegex(
            CanonicalMethodFieldContextReviewSpecError,
            "overlapping",
        ):
            self._build(report)

    def test_context_digest_must_be_hex(self):
        report = self._report()
        report["candidates"][0]["method_witnesses"][0][
            "contexts"
        ][0][0] = "z" * 64
        with self.assertRaisesRegex(
            CanonicalMethodFieldContextReviewSpecError,
            "not hex",
        ):
            self._build(report)

    def test_context_counts_must_equal_witness_count(self):
        report = self._report()
        report["candidates"][0]["method_witnesses"][0]["count"] = 2
        with self.assertRaisesRegex(
            CanonicalMethodFieldContextReviewSpecError,
            "context count drift",
        ):
            self._build(report)

    def test_witness_summary_drift_is_refused(self):
        report = self._report()
        report["candidates"][0]["observations"] = 3
        with self.assertRaisesRegex(
            CanonicalMethodFieldContextReviewSpecError,
            "witness summary drift",
        ):
            self._build(report)

    def test_insufficient_independent_witness_is_refused(self):
        report = self._report()
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
            CanonicalMethodFieldContextReviewSpecError,
            "insufficient independent witness",
        ):
            self._build(report)

    def test_base_global_veto_must_be_preserved(self):
        report = self._report()
        report["candidates"][0][
            "base_global_usage_outcome"
        ] = "candidate"
        with self.assertRaisesRegex(
            CanonicalMethodFieldContextReviewSpecError,
            "not trusted method-context evidence",
        ):
            self._build(report)

    def test_invalid_interval_is_refused(self):
        report = self._report()
        report["candidates"][0]["interval_offset"] = 1
        with self.assertRaisesRegex(
            CanonicalMethodFieldContextReviewSpecError,
            "invalid anchor/interval",
        ):
            self._build(report)

    def test_rejected_reason_accounting_is_checked(self):
        report = self._report()
        report["summary"]["canonical_method_context_mismatch"] = 0
        report["summary"]["canonical_method_context_missing"] = 1
        with self.assertRaisesRegex(
            CanonicalMethodFieldContextReviewSpecError,
            "rejected detail accounting mismatch",
        ):
            self._build(report)

    def test_empty_candidate_set_is_not_reviewable(self):
        report = self._report()
        report["summary"].update(
            {
                "candidate_fields": 0,
                "remaining_without_context_proof": 2,
                "canonical_method_context_mismatch": 2,
            }
        )
        report["candidates"] = []
        report["rejected"].append(
            {
                "relationship_id": "MEMREL_REJECTED_2",
                "reason": "canonical_method_context_mismatch",
                "base_global_usage_outcome": (
                    "global_class_topology_guard_rejected"
                ),
            }
        )
        with self.assertRaisesRegex(
            CanonicalMethodFieldContextReviewSpecError,
            "no reviewable candidates",
        ):
            self._build(report)


if __name__ == "__main__":
    unittest.main()
