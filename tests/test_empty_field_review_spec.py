from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.empty_field_review_spec import (
    EmptyFieldReviewSpecError,
    build_empty_field_review_spec,
)


class EmptyFieldReviewSpecTests(unittest.TestCase):
    def _candidate(self, relationship_id="MEMREL_TEST_1", name="x"):
        return {
            "relationship_id": relationship_id,
            "logical_class_id": "CLIENT_CLASS_A",
            "old_owner": "rs/A",
            "new_owner": "rs/B",
            "old": {
                "name": name,
                "descriptor": "I",
                "access": 1,
            },
            "new": {
                "name": name,
                "descriptor": "I",
                "access": 1,
            },
            "strategy": "canonical_anchor_declaration_interval_exact",
            "confidence": "INFERRED_HIGH",
            "score": 0.99,
            "supports_existing_review": True,
            "left_anchor_member_id": "CLIENT_FIELD_LEFT",
            "right_anchor_member_id": "CLIENT_FIELD_RIGHT",
            "old_field_ordinal": 2,
            "new_field_ordinal": 2,
            "interval_offset": 0,
            "interval_length": 1,
            "interval_digest": "a" * 64,
            "global_source_class_topology": [
                {
                    "source_class": "CLIENT_CLASS_SOURCE",
                    "operation": "getfield",
                    "count": 2,
                }
            ],
            "global_observations": 2,
        }

    def _report(self):
        return {
            "schema_version": 1,
            "kind": "empty_field_declaration_identity_candidates",
            "canonical": False,
            "report_id": "EMPTYFIELDDECL_TEST",
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": "3" * 64,
            "global_usage_report_id": "GLOBALFIELDUSE_TEST",
            "summary": {
                "input_empty_both_reviews": 1,
                "candidate_fields": 1,
                "remaining_without_declaration_proof": 0,
                "raw_source_guard_rejected": 0,
                "global_class_topology_guard_rejected": 0,
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

    def _build(self, report=None):
        report = report or self._report()
        with patch(
            "spk_recovery.empty_field_review_spec."
            "build_empty_field_declaration_evidence",
            return_value=copy.deepcopy(report),
        ):
            return build_empty_field_review_spec(
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
            "strategy=canonical_anchor_declaration_interval_exact",
            spec["evidence"],
        )
        self.assertTrue(
            any(
                value.startswith("report_digest_sha256=")
                for value in spec["evidence"]
            )
        )

    def test_json_equivalent_tuple_list_recomputation_is_accepted(self):
        report = self._report()
        report["summary"]["input_empty_both_reviews"] = 2
        report["summary"]["candidate_fields"] = 1
        report["summary"]["remaining_without_declaration_proof"] = 1
        report["summary"]["missing_two_sided_canonical_anchor"] = 1
        report["rejected"] = [
            {
                "relationship_id": "MEMREL_REJECTED",
                "logical_class_id": "CLIENT_CLASS_A",
                "old_owner": "rs/A",
                "new_owner": "rs/B",
                "reason": "missing_two_sided_canonical_anchor",
                "old_left": ["CLIENT_FIELD_LEFT", 1],
                "old_right": None,
                "new_left": ["CLIENT_FIELD_LEFT", 1],
                "new_right": None,
            }
        ]
        recomputed = copy.deepcopy(report)
        recomputed["rejected"][0]["old_left"] = (
            "CLIENT_FIELD_LEFT",
            1,
        )
        recomputed["rejected"][0]["new_left"] = (
            "CLIENT_FIELD_LEFT",
            1,
        )

        with patch(
            "spk_recovery.empty_field_review_spec."
            "build_empty_field_declaration_evidence",
            return_value=recomputed,
        ):
            spec = build_empty_field_review_spec(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                {"report_id": "GLOBALFIELDUSE_TEST"},
                report,
            )

        self.assertEqual(
            spec["relationship_ids"],
            ["MEMREL_TEST_1"],
        )

    def test_supplied_report_must_equal_exact_jar_recomputation(self):
        report = self._report()
        recomputed = copy.deepcopy(report)
        recomputed["candidates"][0]["interval_digest"] = "b" * 64

        with patch(
            "spk_recovery.empty_field_review_spec."
            "build_empty_field_declaration_evidence",
            return_value=recomputed,
        ):
            with self.assertRaisesRegex(
                EmptyFieldReviewSpecError,
                "does not equal exact-JAR recomputation",
            ):
                build_empty_field_review_spec(
                    {},
                    {},
                    {},
                    {},
                    Path("old.jar"),
                    Path("new.jar"),
                    {},
                    report,
                )

    def test_candidate_and_rejection_accounting_must_balance(self):
        report = self._report()
        report["summary"]["remaining_without_declaration_proof"] = 1
        with self.assertRaisesRegex(
            EmptyFieldReviewSpecError,
            "candidate\+remaining",
        ):
            self._build(report)

    def test_rejection_reason_accounting_must_balance(self):
        report = self._report()
        report["summary"]["candidate_fields"] = 0
        report["summary"]["remaining_without_declaration_proof"] = 1
        report["candidates"] = []
        report["rejected"] = [
            {
                "relationship_id": "MEMREL_REJECTED",
                "reason": "missing_two_sided_canonical_anchor",
            }
        ]
        with self.assertRaisesRegex(
            EmptyFieldReviewSpecError,
            "rejection reason accounting",
        ):
            self._build(report)

    def test_duplicate_target_coordinate_is_refused(self):
        report = self._report()
        report["summary"]["input_empty_both_reviews"] = 2
        report["summary"]["candidate_fields"] = 2
        report["candidates"].append(
            self._candidate(
                relationship_id="MEMREL_TEST_2",
                name="x",
            )
        )
        with self.assertRaisesRegex(
            EmptyFieldReviewSpecError,
            "duplicate old coordinate",
        ):
            self._build(report)

    def test_raw_source_topology_is_refused(self):
        report = self._report()
        report["candidates"][0]["global_source_class_topology"][0][
            "source_class"
        ] = "RAW:rs/X"
        with self.assertRaisesRegex(
            EmptyFieldReviewSpecError,
            "topology\[0\] is invalid",
        ):
            self._build(report)

    def test_global_observation_count_must_match_topology(self):
        report = self._report()
        report["candidates"][0]["global_observations"] = 3
        with self.assertRaisesRegex(
            EmptyFieldReviewSpecError,
            "observation count does not match",
        ):
            self._build(report)

    def test_anchor_ids_must_be_two_distinct_members(self):
        report = self._report()
        report["candidates"][0]["right_anchor_member_id"] = (
            "CLIENT_FIELD_LEFT"
        )
        with self.assertRaisesRegex(
            EmptyFieldReviewSpecError,
            "anchor/interval evidence is invalid",
        ):
            self._build(report)

    def test_interval_offset_must_be_inside_interval(self):
        report = self._report()
        report["candidates"][0]["interval_offset"] = 1
        with self.assertRaisesRegex(
            EmptyFieldReviewSpecError,
            "anchor/interval evidence is invalid",
        ):
            self._build(report)

    def test_wrong_strategy_is_refused(self):
        report = self._report()
        report["candidates"][0]["strategy"] = "stable_symbol"
        with self.assertRaisesRegex(
            EmptyFieldReviewSpecError,
            "not trusted declaration review evidence",
        ):
            self._build(report)

    def test_empty_candidate_set_is_not_reviewable(self):
        report = self._report()
        report["summary"]["input_empty_both_reviews"] = 1
        report["summary"]["candidate_fields"] = 0
        report["summary"]["remaining_without_declaration_proof"] = 1
        report["summary"]["missing_two_sided_canonical_anchor"] = 1
        report["candidates"] = []
        report["rejected"] = [
            {
                "relationship_id": "MEMREL_TEST_1",
                "reason": "missing_two_sided_canonical_anchor",
            }
        ]
        with self.assertRaisesRegex(
            EmptyFieldReviewSpecError,
            "no reviewable candidates",
        ):
            self._build(report)


if __name__ == "__main__":
    unittest.main()
