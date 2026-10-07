from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.boundary_field_review_spec import (
    BoundaryFieldReviewSpecError,
    build_boundary_field_review_spec,
)


class BoundaryFieldReviewSpecTests(unittest.TestCase):
    def _candidate(
        self,
        relationship_id="MEMREL_TEST_1",
        *,
        old_name="x",
        new_name="x",
        block_kind="prefix_block_exact",
    ):
        return {
            "relationship_id": relationship_id,
            "logical_class_id": "CLIENT_CLASS_A",
            "old_owner": "rs/A",
            "new_owner": "rs/B",
            "old": {
                "name": old_name,
                "descriptor": "I",
                "access": 1,
            },
            "new": {
                "name": new_name,
                "descriptor": "I",
                "access": 1,
            },
            "strategy": "canonical_boundary_block_declaration_exact",
            "confidence": "INFERRED_HIGH",
            "score": 0.995,
            "supports_existing_review": True,
            "block_kind": block_kind,
            "anchor_member_id": (
                None
                if block_kind == "whole_class_exact"
                else "CLIENT_FIELD_ANCHOR"
            ),
            "block_length": 1,
            "target_offset": 0,
            "block_digest": "a" * 64,
            "target_signature_digest": "b" * 64,
            "base_declaration_report_id": "EMPTYFIELDDECL_BASE",
        }

    def _report(self):
        return {
            "schema_version": 1,
            "kind": "boundary_field_block_identity_candidates",
            "canonical": False,
            "report_id": "BOUNDARYFIELDBLOCK_TEST",
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": "3" * 64,
            "global_usage_report_id": "GLOBALFIELDUSE_TEST",
            "base_declaration_report_id": "EMPTYFIELDDECL_BASE",
            "base_declaration_report_digest": "4" * 64,
            "summary": {
                "input_missing_anchor_reviews": 2,
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
            "candidates": [self._candidate()],
            "rejected": [
                {
                    "relationship_id": "MEMREL_REJECTED",
                    "logical_class_id": "CLIENT_CLASS_A",
                    "old_owner": "rs/A",
                    "new_owner": "rs/B",
                    "reason": "block_shape_mismatch",
                }
            ],
        }

    def _build(self, report=None, *, recomputed=None):
        report = report or self._report()
        if recomputed is None:
            recomputed = copy.deepcopy(report)
        with patch(
            "spk_recovery.boundary_field_review_spec."
            "build_boundary_field_block_evidence",
            return_value=recomputed,
        ):
            return build_boundary_field_review_spec(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                {"report_id": "GLOBALFIELDUSE_TEST"},
                report,
            )

    def test_exact_recomputed_report_emits_review_spec(self):
        spec = self._build()
        self.assertEqual(
            spec["kind"],
            "reviewed_member_identity_acceptance_spec",
        )
        self.assertEqual(
            spec["relationship_ids"],
            ["MEMREL_TEST_1"],
        )
        self.assertIn(
            "strategy=canonical_boundary_block_declaration_exact",
            spec["evidence"],
        )

    def test_json_equivalent_tuple_list_recomputation_is_accepted(self):
        report = self._report()
        report["rejected"][0]["old_block"] = [
            ["I", 1],
        ]
        recomputed = copy.deepcopy(report)
        recomputed["rejected"][0]["old_block"] = [
            ("I", 1),
        ]

        spec = self._build(report, recomputed=recomputed)
        self.assertEqual(
            spec["relationship_ids"],
            ["MEMREL_TEST_1"],
        )

    def test_changed_recomputation_is_refused(self):
        report = self._report()
        recomputed = copy.deepcopy(report)
        recomputed["candidates"][0]["block_digest"] = "c" * 64
        with self.assertRaisesRegex(
            BoundaryFieldReviewSpecError,
            "does not equal exact-JAR recomputation",
        ):
            self._build(report, recomputed=recomputed)

    def test_candidate_and_remaining_accounting_must_balance(self):
        report = self._report()
        report["summary"]["remaining_without_boundary_block_proof"] = 2
        with self.assertRaisesRegex(
            BoundaryFieldReviewSpecError,
            "candidate\+remaining",
        ):
            self._build(report)

    def test_mode_accounting_must_balance(self):
        report = self._report()
        report["summary"]["prefix_block_exact"] = 0
        with self.assertRaisesRegex(
            BoundaryFieldReviewSpecError,
            "candidate mode accounting",
        ):
            self._build(report)

    def test_rejection_detail_must_match_summary(self):
        report = self._report()
        report["rejected"][0]["reason"] = "block_length_mismatch"
        with self.assertRaisesRegex(
            BoundaryFieldReviewSpecError,
            "rejected detail accounting mismatch",
        ):
            self._build(report)

    def test_candidate_cannot_overlap_rejected_relationship(self):
        report = self._report()
        report["rejected"][0]["relationship_id"] = "MEMREL_TEST_1"
        with self.assertRaisesRegex(
            BoundaryFieldReviewSpecError,
            "overlapping relationship_id",
        ):
            self._build(report)

    def test_duplicate_candidate_target_coordinate_is_refused(self):
        report = self._report()
        report["summary"].update(
            {
                "input_missing_anchor_reviews": 3,
                "candidate_fields": 2,
                "prefix_block_exact": 2,
            }
        )
        report["candidates"].append(
            self._candidate(
                "MEMREL_TEST_2",
                old_name="x",
                new_name="x",
            )
        )
        with self.assertRaisesRegex(
            BoundaryFieldReviewSpecError,
            "duplicate old coordinate",
        ):
            self._build(report)

    def test_whole_class_candidate_must_not_carry_anchor(self):
        report = self._report()
        report["summary"].update(
            {
                "prefix_block_exact": 0,
                "whole_class_exact": 1,
            }
        )
        report["candidates"][0]["block_kind"] = "whole_class_exact"
        report["candidates"][0]["anchor_member_id"] = "CLIENT_FIELD_BAD"
        with self.assertRaisesRegex(
            BoundaryFieldReviewSpecError,
            "whole-class proof must not have anchor",
        ):
            self._build(report)

    def test_prefix_candidate_requires_canonical_anchor(self):
        report = self._report()
        report["candidates"][0]["anchor_member_id"] = None
        with self.assertRaisesRegex(
            BoundaryFieldReviewSpecError,
            "boundary block lacks canonical anchor",
        ):
            self._build(report)

    def test_target_offset_must_be_inside_block(self):
        report = self._report()
        report["candidates"][0]["target_offset"] = 1
        with self.assertRaisesRegex(
            BoundaryFieldReviewSpecError,
            "boundary block evidence is invalid",
        ):
            self._build(report)

    def test_candidate_base_declaration_report_must_match(self):
        report = self._report()
        report["candidates"][0][
            "base_declaration_report_id"
        ] = "EMPTYFIELDDECL_OTHER"
        with self.assertRaisesRegex(
            BoundaryFieldReviewSpecError,
            "base declaration report drift",
        ):
            self._build(report)

    def test_empty_candidate_set_is_not_reviewable(self):
        report = self._report()
        report["summary"].update(
            {
                "input_missing_anchor_reviews": 1,
                "candidate_fields": 0,
                "remaining_without_boundary_block_proof": 1,
                "prefix_block_exact": 0,
            }
        )
        report["candidates"] = []
        with self.assertRaisesRegex(
            BoundaryFieldReviewSpecError,
            "no reviewable candidates",
        ):
            self._build(report)


if __name__ == "__main__":
    unittest.main()
