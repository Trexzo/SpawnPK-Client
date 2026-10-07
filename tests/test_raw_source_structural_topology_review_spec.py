from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.raw_source_structural_topology_review_spec import (
    RawSourceStructuralTopologyReviewSpecError,
    build_raw_source_structural_topology_review_spec,
)


class RawSourceStructuralTopologyReviewSpecTests(unittest.TestCase):
    def _proof(
        self,
        *,
        strategy="structural_sha256_unique_global",
        value="a" * 64,
    ):
        return {
            "identity_token": f"{strategy}:{value}",
            "strategy": strategy,
            "old_source_class": "RAW:thirdparty/OldCaller",
            "new_source_class": "RAW:thirdparty/NewCaller",
            "old_entry": "thirdparty/OldCaller.class",
            "new_entry": "thirdparty/NewCaller.class",
            "old_entry_sha256": (
                value
                if strategy == "exact_sha256_unique_global"
                else "1" * 64
            ),
            "new_entry_sha256": (
                value
                if strategy == "exact_sha256_unique_global"
                else "2" * 64
            ),
            "old_structural_sha256": (
                value
                if strategy == "structural_sha256_unique_global"
                else "3" * 64
            ),
            "new_structural_sha256": (
                value
                if strategy == "structural_sha256_unique_global"
                else "4" * 64
            ),
        }

    def _candidate(self, relationship_id="MEMREL_TEST"):
        proof = self._proof()
        return {
            "relationship_id": relationship_id,
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
                "globally_unique_raw_source_identity_and_"
                "canonical_anchor_declaration_interval_exact"
            ),
            "confidence": "INFERRED_HIGH",
            "score": 0.999,
            "supports_existing_review": True,
            "raw_source_identity_proofs": [proof],
            "normalized_global_source_class_topology": [
                {
                    "source_identity": proof["identity_token"],
                    "operation": "getstatic",
                    "count": 2,
                },
                {
                    "source_identity": "CANON:CLIENT_CLASS_CALLER",
                    "operation": "putstatic",
                    "count": 1,
                },
            ],
            "left_anchor_member_id": "CLIENT_FIELD_LEFT",
            "right_anchor_member_id": "CLIENT_FIELD_RIGHT",
            "old_field_ordinal": 1,
            "new_field_ordinal": 1,
            "interval_offset": 0,
            "interval_length": 1,
            "interval_digest": "5" * 64,
            "base_raw_source_report_id": "RAWSOURCEDECL_BASE",
        }

    def _report(self):
        return {
            "schema_version": 1,
            "kind": (
                "raw_source_structural_topology_"
                "declaration_identity_candidates"
            ),
            "canonical": False,
            "report_id": "RAWSOURCETOPO_TEST",
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": "3" * 64,
            "global_usage_report_id": "GLOBALFIELDUSE_TEST",
            "base_raw_source_report_id": "RAWSOURCEDECL_BASE",
            "base_raw_source_report_digest": "4" * 64,
            "summary": {
                "input_raw_source_topology_mismatches": 2,
                "candidate_fields": 1,
                "remaining_without_structural_topology_proof": 1,
                "unique_exact_sha_source_identities_used": 0,
                "unique_structural_source_identities_used": 1,
                "raw_source_identity_unproven": 1,
                "normalized_source_topology_mismatch": 0,
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
                    "logical_class_id": "CLIENT_CLASS_A",
                    "old_owner": "rs/A",
                    "new_owner": "rs/B",
                    "reason": "raw_source_identity_unproven",
                }
            ],
        }

    def _build(self, report=None, *, recomputed=None):
        report = report or self._report()
        if recomputed is None:
            recomputed = copy.deepcopy(report)
        with patch(
            "spk_recovery.raw_source_structural_topology_review_spec."
            "build_raw_source_structural_topology_evidence",
            return_value=recomputed,
        ):
            return build_raw_source_structural_topology_review_spec(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                {"report_id": "GLOBALFIELDUSE_TEST"},
                report,
            )

    def test_exact_recomputation_emits_review_spec(self):
        spec = self._build()

        self.assertEqual(
            spec["kind"],
            "reviewed_member_identity_acceptance_spec",
        )
        self.assertEqual(spec["relationship_ids"], ["MEMREL_TEST"])
        self.assertIn(
            (
                "strategy=globally_unique_raw_source_identity_and_"
                "canonical_anchor_declaration_interval_exact"
            ),
            spec["evidence"],
        )

    def test_changed_recomputation_is_refused(self):
        report = self._report()
        recomputed = copy.deepcopy(report)
        recomputed["candidates"][0]["interval_digest"] = "6" * 64

        with self.assertRaisesRegex(
            RawSourceStructuralTopologyReviewSpecError,
            "does not equal exact-JAR recomputation",
        ):
            self._build(report, recomputed=recomputed)

    def test_candidate_remaining_accounting_must_balance(self):
        report = self._report()
        report["summary"][
            "remaining_without_structural_topology_proof"
        ] = 2

        with self.assertRaisesRegex(
            RawSourceStructuralTopologyReviewSpecError,
            "candidate\+remaining",
        ):
            self._build(report)

    def test_rejection_reason_detail_must_match_summary(self):
        report = self._report()
        report["rejected"][0]["reason"] = (
            "normalized_source_topology_mismatch"
        )

        with self.assertRaisesRegex(
            RawSourceStructuralTopologyReviewSpecError,
            "rejected detail accounting mismatch",
        ):
            self._build(report)

    def test_candidate_cannot_overlap_rejected_relationship(self):
        report = self._report()
        report["rejected"][0]["relationship_id"] = "MEMREL_TEST"

        with self.assertRaisesRegex(
            RawSourceStructuralTopologyReviewSpecError,
            "overlapping relationship_id",
        ):
            self._build(report)

    def test_proof_token_must_bind_structural_digest(self):
        report = self._report()
        proof = report["candidates"][0][
            "raw_source_identity_proofs"
        ][0]
        proof["identity_token"] = (
            "structural_sha256_unique_global:" + "b" * 64
        )

        with self.assertRaisesRegex(
            RawSourceStructuralTopologyReviewSpecError,
            "proof token does not bind",
        ):
            self._build(report)

    def test_exact_sha_proof_requires_equal_entry_sha(self):
        report = self._report()
        proof = self._proof(
            strategy="exact_sha256_unique_global",
            value="a" * 64,
        )
        proof["new_entry_sha256"] = "b" * 64
        report["candidates"][0][
            "raw_source_identity_proofs"
        ] = [proof]
        report["candidates"][0][
            "normalized_global_source_class_topology"
        ][0]["source_identity"] = proof["identity_token"]
        report["summary"][
            "unique_structural_source_identities_used"
        ] = 0
        report["summary"][
            "unique_exact_sha_source_identities_used"
        ] = 1

        with self.assertRaisesRegex(
            RawSourceStructuralTopologyReviewSpecError,
            "exact-SHA proof has SHA drift",
        ):
            self._build(report)

    def test_normalized_topology_requires_proven_raw_identity(self):
        report = self._report()
        report["candidates"][0][
            "normalized_global_source_class_topology"
        ][0]["source_identity"] = (
            "structural_sha256_unique_global:" + "f" * 64
        )

        with self.assertRaisesRegex(
            RawSourceStructuralTopologyReviewSpecError,
            "topology identity lacks RAW proof",
        ):
            self._build(report)

    def test_duplicate_candidate_coordinate_is_refused(self):
        report = self._report()
        report["summary"].update(
            {
                "input_raw_source_topology_mismatches": 3,
                "candidate_fields": 2,
            }
        )
        second = self._candidate("MEMREL_TEST_2")
        report["candidates"].append(second)

        with self.assertRaisesRegex(
            RawSourceStructuralTopologyReviewSpecError,
            "duplicate old coordinate",
        ):
            self._build(report)

    def test_anchor_interval_evidence_must_be_valid(self):
        report = self._report()
        report["candidates"][0]["interval_offset"] = 1

        with self.assertRaisesRegex(
            RawSourceStructuralTopologyReviewSpecError,
            "anchor/interval evidence is invalid",
        ):
            self._build(report)

    def test_base_raw_source_report_must_match(self):
        report = self._report()
        report["candidates"][0][
            "base_raw_source_report_id"
        ] = "RAWSOURCEDECL_OTHER"

        with self.assertRaisesRegex(
            RawSourceStructuralTopologyReviewSpecError,
            "base RAW-source report drift",
        ):
            self._build(report)

    def test_identity_summary_counts_include_rejected_rows(self):
        report = self._report()
        proof = self._proof(
            strategy="exact_sha256_unique_global",
            value="d" * 64,
        )
        report["rejected"][0].update(
            {
                "reason": "normalized_source_topology_mismatch",
                "raw_source_identity_proofs": [proof],
            }
        )
        report["summary"].update(
            {
                "raw_source_identity_unproven": 0,
                "normalized_source_topology_mismatch": 1,
                "unique_exact_sha_source_identities_used": 1,
            }
        )

        spec = self._build(report)

        self.assertEqual(spec["relationship_ids"], ["MEMREL_TEST"])
        self.assertIn(
            "unique_exact_sha_source_identities_used=1",
            spec["evidence"],
        )

    def test_identity_summary_count_drift_is_refused(self):
        report = self._report()
        report["summary"][
            "unique_structural_source_identities_used"
        ] = 2

        with self.assertRaisesRegex(
            RawSourceStructuralTopologyReviewSpecError,
            "structural identity accounting mismatch",
        ):
            self._build(report)

    def test_empty_candidate_set_is_not_reviewable(self):
        report = self._report()
        report["summary"].update(
            {
                "candidate_fields": 0,
                "remaining_without_structural_topology_proof": 2,
                "raw_source_identity_unproven": 2,
                "unique_structural_source_identities_used": 0,
            }
        )
        report["candidates"] = []
        report["rejected"].append(
            {
                "relationship_id": "MEMREL_REJECTED_2",
                "logical_class_id": "CLIENT_CLASS_A",
                "old_owner": "rs/A",
                "new_owner": "rs/B",
                "reason": "raw_source_identity_unproven",
            }
        )

        with self.assertRaisesRegex(
            RawSourceStructuralTopologyReviewSpecError,
            "no reviewable candidates",
        ):
            self._build(report)


if __name__ == "__main__":
    unittest.main()
