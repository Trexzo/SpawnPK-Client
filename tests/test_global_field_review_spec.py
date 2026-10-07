from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from spk_recovery.global_field_review_spec import (
    GlobalFieldReviewSpecError,
    _stable_digest,
    build_global_field_review_spec,
)


class GlobalFieldReviewSpecTests(unittest.TestCase):
    def _classes(self):
        return {
            "builds": [
                {"build_id": "v308", "sha256": "1" * 64},
                {"build_id": "v309", "sha256": "2" * 64},
            ],
            "classes": [
                {
                    "logical_id": "CLIENT_CLASS_A",
                    "lineage": [
                        {"build_id": "v308", "internal_name": "rs/A"},
                        {"build_id": "v309", "internal_name": "rs/B"},
                    ],
                }
            ],
        }

    def _members(self):
        return {
            "members": [],
            "unresolved": [
                {
                    "kind": "member_identity_review",
                    "member_kind": "field",
                    "source": "member_identity_candidates",
                    "old_build_id": "v308",
                    "new_build_id": "v309",
                    "candidate": {
                        "relationship_id": "MEMREL_TEST_1",
                        "strategy": "stable_symbol",
                        "old_owner": "rs/A.class",
                        "new_owner": "rs/B.class",
                        "old": {
                            "name": "x",
                            "descriptor": "I",
                            "access": 1,
                        },
                        "new": {
                            "name": "x",
                            "descriptor": "I",
                            "access": 1,
                        },
                    },
                }
            ],
        }

    def _old_index(self):
        return {
            "sha256": "1" * 64,
            "classes": {
                "rs/A.class": {
                    "fields": [
                        {
                            "name": "x",
                            "descriptor": "I",
                            "access": 1,
                        }
                    ]
                }
            },
        }

    def _new_index(self):
        return {
            "sha256": "2" * 64,
            "classes": {
                "rs/B.class": {
                    "fields": [
                        {
                            "name": "x",
                            "descriptor": "I",
                            "access": 1,
                        }
                    ]
                }
            },
        }

    def _report(self, members):
        return {
            "schema_version": 1,
            "kind": "global_field_usage_identity_candidates",
            "canonical": False,
            "report_id": "GLOBALFIELDUSE_TEST",
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": _stable_digest(members),
            "summary": {
                "input_stable_symbol_reviews": 1,
                "eligible_stable_symbol_reviews": 1,
                "descriptor_identity_guard_rejected": 0,
                "candidate_fields": 1,
                "remaining_without_global_topology_proof": 0,
            },
            "candidates": [
                {
                    "relationship_id": "MEMREL_TEST_1",
                    "logical_class_id": "CLIENT_CLASS_A",
                    "old_owner": "rs/A",
                    "new_owner": "rs/B",
                    "old": {
                        "name": "x",
                        "descriptor": "I",
                        "access": 1,
                    },
                    "new": {
                        "name": "x",
                        "descriptor": "I",
                        "access": 1,
                    },
                    "strategy": (
                        "canonical_method_and_global_class_usage_"
                        "topology_exact"
                    ),
                    "confidence": "INFERRED_HIGH",
                    "supports_existing_review": True,
                    "observations": 3,
                    "canonical_methods": 2,
                    "canonical_method_topology": [
                        {
                            "member_id": "CLIENT_METHOD_1",
                            "operation": "getfield",
                            "count": 2,
                        },
                        {
                            "member_id": "CLIENT_METHOD_2",
                            "operation": "putfield",
                            "count": 1,
                        },
                    ],
                    "global_source_class_topology": [
                        {
                            "source_class": "CLIENT_CLASS_C",
                            "operation": "getfield",
                            "count": 2,
                        },
                        {
                            "source_class": "CLIENT_CLASS_D",
                            "operation": "putfield",
                            "count": 1,
                        },
                    ],
                }
            ],
            "descriptor_identity_rejections": [],
        }

    def _build(self, report=None, members=None):
        members = members or self._members()
        report = report or self._report(members)
        with (
            patch(
                "spk_recovery.global_field_review_spec.validate_lineage"
            ),
            patch(
                "spk_recovery.global_field_review_spec.validate_member_lineage"
            ),
        ):
            return build_global_field_review_spec(
                self._classes(),
                members,
                self._old_index(),
                self._new_index(),
                report,
            )

    def test_builds_acceptance_spec_for_exact_existing_global_candidate(self):
        members = self._members()
        spec = self._build(
            report=self._report(members),
            members=members,
        )
        self.assertEqual(
            spec["kind"],
            "reviewed_member_identity_acceptance_spec",
        )
        self.assertEqual(
            spec["relationship_ids"],
            ["MEMREL_TEST_1"],
        )
        self.assertEqual(spec["old_build_id"], "v308")
        self.assertEqual(spec["new_build_id"], "v309")
        self.assertIn(
            "GLOBALFIELDUSE_TEST",
            spec["evidence"][0],
        )
        self.assertTrue(
            any(
                row.startswith("report_digest_sha256=")
                for row in spec["evidence"]
            )
        )

    def test_member_lineage_digest_drift_is_refused(self):
        members = self._members()
        report = self._report(members)
        report["member_lineage_digest"] = "9" * 64
        with self.assertRaisesRegex(
            GlobalFieldReviewSpecError,
            "member lineage digest",
        ):
            self._build(report=report, members=members)

    def test_candidate_coordinate_drift_from_unresolved_is_refused(self):
        members = self._members()
        report = self._report(members)
        report["candidates"][0]["new"]["name"] = "y"
        new_index = self._new_index()
        new_index["classes"]["rs/B.class"]["fields"].append(
            {"name": "y", "descriptor": "I", "access": 1}
        )
        with (
            patch(
                "spk_recovery.global_field_review_spec.validate_lineage"
            ),
            patch(
                "spk_recovery.global_field_review_spec.validate_member_lineage"
            ),
        ):
            with self.assertRaisesRegex(
                GlobalFieldReviewSpecError,
                "evidence coordinate differs",
            ):
                build_global_field_review_spec(
                    self._classes(),
                    members,
                    self._old_index(),
                    new_index,
                    report,
                )

    def test_raw_source_class_support_is_refused(self):
        members = self._members()
        report = self._report(members)
        report["candidates"][0]["global_source_class_topology"][0][
            "source_class"
        ] = "RAW:rs/unmapped"
        with self.assertRaisesRegex(
            GlobalFieldReviewSpecError,
            "RAW source class",
        ):
            self._build(report=report, members=members)

    def test_duplicate_candidate_target_coordinate_is_refused(self):
        members = self._members()
        second = copy.deepcopy(members["unresolved"][0])
        second["candidate"]["relationship_id"] = "MEMREL_TEST_2"
        second["candidate"]["old"]["name"] = "z"
        members["unresolved"].append(second)

        old_index = self._old_index()
        old_index["classes"]["rs/A.class"]["fields"].append(
            {"name": "z", "descriptor": "I", "access": 1}
        )

        report = self._report(members)
        report["summary"]["input_stable_symbol_reviews"] = 2
        report["summary"]["eligible_stable_symbol_reviews"] = 2
        report["summary"]["candidate_fields"] = 2
        report["candidates"].append(
            copy.deepcopy(report["candidates"][0])
        )
        report["candidates"][1]["relationship_id"] = "MEMREL_TEST_2"
        report["candidates"][1]["old"]["name"] = "z"

        with (
            patch(
                "spk_recovery.global_field_review_spec.validate_lineage"
            ),
            patch(
                "spk_recovery.global_field_review_spec.validate_member_lineage"
            ),
        ):
            with self.assertRaisesRegex(
                GlobalFieldReviewSpecError,
                "duplicate new candidate coordinate",
            ):
                build_global_field_review_spec(
                    self._classes(),
                    members,
                    old_index,
                    self._new_index(),
                    report,
                )

    def test_descriptor_veto_is_accounted_but_never_accepted(self):
        members = self._members()
        veto = copy.deepcopy(members["unresolved"][0])
        veto["candidate"]["relationship_id"] = "MEMREL_VETO"
        veto["candidate"]["old"]["name"] = "z"
        veto["candidate"]["new"]["name"] = "z"
        members["unresolved"].append(veto)

        report = self._report(members)
        report["summary"].update(
            {
                "input_stable_symbol_reviews": 2,
                "eligible_stable_symbol_reviews": 1,
                "descriptor_identity_guard_rejected": 1,
                "candidate_fields": 1,
                "remaining_without_global_topology_proof": 1,
            }
        )
        report["descriptor_identity_rejections"] = [
            {
                "relationship_id": "MEMREL_VETO",
                "reason": "canonical_descriptor_identity_changed",
            }
        ]

        spec = self._build(report=report, members=members)
        self.assertEqual(
            spec["relationship_ids"],
            ["MEMREL_TEST_1"],
        )
        self.assertTrue(
            any(
                row == "descriptor_identity_vetoes=1"
                for row in spec["evidence"]
            )
        )

    def test_frontier_accounting_drift_is_refused(self):
        members = self._members()
        report = self._report(members)
        report["summary"]["remaining_without_global_topology_proof"] = 1
        with self.assertRaisesRegex(
            GlobalFieldReviewSpecError,
            "candidate\+remaining",
        ):
            self._build(report=report, members=members)


if __name__ == "__main__":
    unittest.main()
