from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.raw_source_inbound_canonical_review_spec import (
    RawSourceInboundCanonicalReviewSpecError,
    _digest,
    build_raw_source_inbound_canonical_review_spec,
)


class RawSourceInboundCanonicalReviewSpecTests(unittest.TestCase):
    def _proof(self):
        strategy = "canonical_method_inbound_topology_unique_global"
        profile = {
            "canonical_source_classes": [["CLIENT_CLASS_X", 1]],
            "canonical_source_method_events": [
                ["CLIENT_METHOD_1", "type:new", 1],
                ["CLIENT_METHOD_2", "invoke:invokevirtual:(I)V", 1],
            ],
        }
        key = (
            ("CLIENT_METHOD_1", "type:new", 1),
            (
                "CLIENT_METHOD_2",
                "invoke:invokevirtual:(I)V",
                1,
            ),
        )
        digest = _digest(
            {
                "strategy": strategy,
                "inbound_topology": key,
            }
        )
        return {
            "identity_token": f"{strategy}:{digest}",
            "strategy": strategy,
            "old_source_class": "RAW:raw/Old",
            "new_source_class": "RAW:raw/New",
            "inbound_topology_digest": digest,
            "old_profile": copy.deepcopy(profile),
            "new_profile": copy.deepcopy(profile),
        }

    def _candidate(self, relationship_id="MEMREL_TEST"):
        proof = self._proof()
        return {
            "relationship_id": relationship_id,
            "old_owner": "rs/A",
            "new_owner": "rs/B",
            "old": {"name": "x", "descriptor": "I"},
            "new": {"name": "x", "descriptor": "I"},
            "strategy": (
                "globally_unique_inbound_canonical_identity_and_"
                "canonical_anchor_declaration_interval_exact"
            ),
            "supports_existing_review": True,
            "confidence": "INFERRED_HIGH",
            "score": 0.9993,
            "raw_source_identity_proofs": [proof],
            "normalized_global_source_class_topology": [
                {
                    "source_identity": proof["identity_token"],
                    "operation": "getstatic",
                    "count": 2,
                }
            ],
            "left_anchor_member_id": "CLIENT_FIELD_LEFT",
            "right_anchor_member_id": "CLIENT_FIELD_RIGHT",
            "interval_digest": "a" * 64,
            "interval_length": 1,
            "interval_offset": 0,
            "old_field_ordinal": 1,
            "new_field_ordinal": 1,
            "base_canonical_reference_report_id": "RAWREF_BASE",
        }

    def _report(self):
        return {
            "schema_version": 1,
            "kind": (
                "raw_source_inbound_canonical_topology_"
                "declaration_identity_candidates"
            ),
            "canonical": False,
            "report_id": "RAWINBOUND_TEST",
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": "3" * 64,
            "global_usage_report_id": "GLOBAL_TEST",
            "base_canonical_reference_report_id": "RAWREF_BASE",
            "base_canonical_reference_report_digest": "4" * 64,
            "base_structural_topology_report_id": "RAWSOURCETOPO_BASE",
            "base_structural_topology_report_digest": "5" * 64,
            "summary": {
                "input_canonical_reference_identity_unproven": 2,
                "candidate_fields": 1,
                "remaining_without_inbound_canonical_proof": 1,
                "global_unique_method_inbound_identities": 1,
                "global_unique_class_method_inbound_identities": 0,
                "used_method_inbound_identities": 1,
                "used_class_method_inbound_identities": 0,
                "inbound_canonical_identity_unproven": 1,
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
                    "reason": "inbound_canonical_identity_unproven",
                }
            ],
        }

    def _build(self, report=None, *, recomputed=None):
        report = report or self._report()
        recomputed = (
            copy.deepcopy(report)
            if recomputed is None
            else recomputed
        )
        with patch(
            "spk_recovery.raw_source_inbound_canonical_review_spec."
            "build_raw_source_inbound_canonical_evidence",
            return_value=recomputed,
        ):
            return build_raw_source_inbound_canonical_review_spec(
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

    def test_changed_recomputation_is_refused(self):
        report = self._report()
        recomputed = copy.deepcopy(report)
        recomputed["candidates"][0]["interval_digest"] = "b" * 64
        with self.assertRaisesRegex(
            RawSourceInboundCanonicalReviewSpecError,
            "does not equal exact-JAR recomputation",
        ):
            self._build(report, recomputed=recomputed)

    def test_proof_profiles_must_match(self):
        report = self._report()
        report["candidates"][0][
            "raw_source_identity_proofs"
        ][0]["new_profile"]["canonical_source_method_events"][0][2] = 2
        with self.assertRaisesRegex(
            RawSourceInboundCanonicalReviewSpecError,
            "profile equality drift",
        ):
            self._build(report)

    def test_proof_token_must_bind_digest(self):
        report = self._report()
        report["candidates"][0][
            "raw_source_identity_proofs"
        ][0]["identity_token"] += "X"
        with self.assertRaisesRegex(
            RawSourceInboundCanonicalReviewSpecError,
            "proof token drift",
        ):
            self._build(report)

    def test_candidate_remaining_accounting_must_balance(self):
        report = self._report()
        report["summary"][
            "remaining_without_inbound_canonical_proof"
        ] = 2
        with self.assertRaisesRegex(
            RawSourceInboundCanonicalReviewSpecError,
            "candidate\+remaining",
        ):
            self._build(report)

    def test_candidate_cannot_overlap_rejected(self):
        report = self._report()
        report["rejected"][0]["relationship_id"] = "MEMREL_TEST"
        with self.assertRaisesRegex(
            RawSourceInboundCanonicalReviewSpecError,
            "overlapping",
        ):
            self._build(report)

    def test_normalized_topology_requires_proof_token(self):
        report = self._report()
        report["candidates"][0][
            "normalized_global_source_class_topology"
        ][0]["source_identity"] = (
            "canonical_method_inbound_topology_unique_global:"
            + "f" * 64
        )
        with self.assertRaisesRegex(
            RawSourceInboundCanonicalReviewSpecError,
            "lacks inbound proof",
        ):
            self._build(report)

    def test_invalid_interval_is_refused(self):
        report = self._report()
        report["candidates"][0]["interval_offset"] = 1
        with self.assertRaisesRegex(
            RawSourceInboundCanonicalReviewSpecError,
            "invalid anchor/interval",
        ):
            self._build(report)

    def test_base_canonical_reference_binding_is_checked(self):
        report = self._report()
        report["candidates"][0][
            "base_canonical_reference_report_id"
        ] = "RAWREF_OTHER"
        with self.assertRaisesRegex(
            RawSourceInboundCanonicalReviewSpecError,
            "base canonical-reference report drift",
        ):
            self._build(report)

    def test_used_identity_count_can_include_rejected_proof_row(self):
        report = self._report()
        proof = self._proof()
        proof["identity_token"] = (
            "canonical_method_inbound_topology_unique_global:"
            + "e" * 64
        )
        proof["inbound_topology_digest"] = "e" * 64

        # Make this second proof self-consistent with a distinct topology.
        profile = copy.deepcopy(proof["old_profile"])
        profile["canonical_source_method_events"][0][2] = 2
        proof["old_profile"] = profile
        proof["new_profile"] = copy.deepcopy(profile)
        key = (
            ("CLIENT_METHOD_1", "type:new", 2),
            (
                "CLIENT_METHOD_2",
                "invoke:invokevirtual:(I)V",
                1,
            ),
        )
        digest = _digest(
            {
                "strategy": proof["strategy"],
                "inbound_topology": key,
            }
        )
        proof["inbound_topology_digest"] = digest
        proof["identity_token"] = (
            f"{proof['strategy']}:{digest}"
        )

        report["rejected"][0].update(
            {
                "reason": "normalized_source_topology_mismatch",
                "raw_source_identity_proofs": [proof],
            }
        )
        report["summary"].update(
            {
                "global_unique_method_inbound_identities": 2,
                "used_method_inbound_identities": 2,
                "inbound_canonical_identity_unproven": 0,
                "normalized_source_topology_mismatch": 1,
            }
        )
        spec = self._build(report)
        self.assertEqual(spec["relationship_ids"], ["MEMREL_TEST"])

    def test_used_identity_count_drift_is_refused(self):
        report = self._report()
        report["summary"]["used_method_inbound_identities"] = 2
        report["summary"]["global_unique_method_inbound_identities"] = 2
        with self.assertRaisesRegex(
            RawSourceInboundCanonicalReviewSpecError,
            "used method-inbound identity accounting mismatch",
        ):
            self._build(report)

    def test_empty_candidate_set_is_not_reviewable(self):
        report = self._report()
        report["summary"].update(
            {
                "candidate_fields": 0,
                "remaining_without_inbound_canonical_proof": 2,
                "used_method_inbound_identities": 0,
                "inbound_canonical_identity_unproven": 2,
            }
        )
        report["candidates"] = []
        report["rejected"].append(
            {
                "relationship_id": "MEMREL_REJECTED_2",
                "reason": "inbound_canonical_identity_unproven",
            }
        )
        with self.assertRaisesRegex(
            RawSourceInboundCanonicalReviewSpecError,
            "no reviewable candidates",
        ):
            self._build(report)


if __name__ == "__main__":
    unittest.main()
