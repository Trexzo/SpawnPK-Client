from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.canonical_method_single_context_declaration_review_spec import (
    CanonicalMethodSingleContextDeclarationReviewSpecError,
    build_canonical_method_single_context_declaration_review_spec,
)


class CanonicalMethodSingleContextDeclarationReviewSpecTests(unittest.TestCase):
    def _candidate(self):
        return {
            "relationship_id": "MEMREL_TEST",
            "logical_class_id": "CLIENT_CLASS_A",
            "old_owner": "rs/A",
            "new_owner": "rs/B",
            "old": {"name": "x", "descriptor": "I", "access": 1},
            "new": {"name": "y", "descriptor": "I", "access": 1},
            "strategy": (
                "canonical_method_single_unique_local_context_and_"
                "canonical_anchor_declaration_interval_exact"
            ),
            "confidence": "INFERRED_HIGH",
            "score": 0.9992,
            "supports_existing_review": True,
            "canonical_methods": 1,
            "observations": 1,
            "distinct_contexts": 1,
            "method_witnesses": [
                {
                    "method_id": "M1",
                    "operation": "getfield",
                    "count": 1,
                    "contexts": [["a" * 64, 1]],
                }
            ],
            "method_id": "M1",
            "operation": "getfield",
            "context_digest": "a" * 64,
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
            "base_context_reason": "insufficient_independent_context_witness",
            "base_global_usage_report_id": "GLOBAL_TEST",
        }

    def _report(self):
        return {
            "schema_version": 1,
            "kind": (
                "canonical_method_single_context_declaration_"
                "identity_candidates"
            ),
            "canonical": False,
            "report_id": "SINGLECTXDECL_TEST",
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
                "input_insufficient_witness_reviews": 2,
                "candidate_fields": 1,
                "remaining_without_declaration_proof": 1,
                "single_context_shape_mismatch": 0,
                "missing_two_sided_canonical_anchor": 1,
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
                    "logical_class_id": "CLIENT_CLASS_B",
                    "old_owner": "rs/C",
                    "new_owner": "rs/D",
                    "reason": "missing_two_sided_canonical_anchor",
                    "base_context_reason": (
                        "insufficient_independent_context_witness"
                    ),
                }
            ],
        }

    def _build(self, report=None, *, recomputed=None):
        report = report or self._report()
        recomputed = copy.deepcopy(report) if recomputed is None else recomputed
        with patch(
            "spk_recovery.canonical_method_single_context_declaration_review_spec."
            "build_canonical_method_single_context_declaration_evidence",
            return_value=recomputed,
        ):
            return build_canonical_method_single_context_declaration_review_spec(
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
        recomputed["candidates"][0]["interval_digest"] = "e" * 64
        with self.assertRaisesRegex(
            CanonicalMethodSingleContextDeclarationReviewSpecError,
            "does not equal exact-JAR recomputation",
        ):
            self._build(report, recomputed=recomputed)

    def test_wrong_score_is_refused(self):
        report = self._report()
        report["candidates"][0]["score"] = 0.5
        with self.assertRaisesRegex(
            CanonicalMethodSingleContextDeclarationReviewSpecError,
            "not trusted",
        ):
            self._build(report)

    def test_context_digest_must_be_hex(self):
        report = self._report()
        candidate = report["candidates"][0]
        candidate["context_digest"] = "z" * 64
        candidate["method_witnesses"][0]["contexts"][0][0] = "z" * 64
        with self.assertRaisesRegex(
            CanonicalMethodSingleContextDeclarationReviewSpecError,
            "not hex",
        ):
            self._build(report)

    def test_witness_detail_drift_is_refused(self):
        report = self._report()
        report["candidates"][0]["method_id"] = "M2"
        with self.assertRaisesRegex(
            CanonicalMethodSingleContextDeclarationReviewSpecError,
            "witness detail drift",
        ):
            self._build(report)

    def test_repeated_observations_of_one_context_are_reviewable(self):
        report = self._report()
        candidate = report["candidates"][0]
        candidate["observations"] = 2
        candidate["method_witnesses"][0]["count"] = 2
        candidate["method_witnesses"][0]["contexts"][0][1] = 2
        spec = self._build(report)
        self.assertEqual(spec["relationship_ids"], ["MEMREL_TEST"])

    def test_invalid_interval_is_refused(self):
        report = self._report()
        report["candidates"][0]["interval_offset"] = 1
        with self.assertRaisesRegex(
            CanonicalMethodSingleContextDeclarationReviewSpecError,
            "invalid declaration interval",
        ):
            self._build(report)

    def test_rejected_reason_accounting_is_checked(self):
        report = self._report()
        report["summary"]["missing_two_sided_canonical_anchor"] = 0
        report["summary"]["single_context_shape_mismatch"] = 1
        with self.assertRaisesRegex(
            CanonicalMethodSingleContextDeclarationReviewSpecError,
            "rejected detail accounting mismatch",
        ):
            self._build(report)

    def test_empty_candidate_set_is_not_reviewable(self):
        report = self._report()
        report["summary"]["candidate_fields"] = 0
        report["summary"]["remaining_without_declaration_proof"] = 2
        report["summary"]["missing_two_sided_canonical_anchor"] = 2
        report["candidates"] = []
        report["rejected"].append(
            {
                "relationship_id": "MEMREL_REJECTED_2",
                "logical_class_id": "CLIENT_CLASS_C",
                "old_owner": "rs/E",
                "new_owner": "rs/F",
                "reason": "missing_two_sided_canonical_anchor",
                "base_context_reason": (
                    "insufficient_independent_context_witness"
                ),
            }
        )
        with self.assertRaisesRegex(
            CanonicalMethodSingleContextDeclarationReviewSpecError,
            "no reviewable candidates",
        ):
            self._build(report)


if __name__ == "__main__":
    unittest.main()
