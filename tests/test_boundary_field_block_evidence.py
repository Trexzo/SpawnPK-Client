from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.boundary_field_block_evidence import (
    build_boundary_field_block_evidence,
)


class BoundaryFieldBlockEvidenceTests(unittest.TestCase):
    def _base(self):
        return {
            "report_id": "EMPTYFIELDDECL_BASE",
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": "3" * 64,
            "global_usage_report_id": "GLOBALFIELDUSE_TEST",
            "rejected": [
                {
                    "relationship_id": "MEMREL_TEST",
                    "logical_class_id": "CLIENT_CLASS_A",
                    "old_owner": "rs/A",
                    "new_owner": "rs/B",
                    "reason": "missing_two_sided_canonical_anchor",
                }
            ],
        }

    def _original(self):
        return {
            "strategy": "stable_symbol",
            "relationship_id": "MEMREL_TEST",
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
        }

    @staticmethod
    def _field(name, descriptor="I", access=1):
        return {
            "name": name,
            "descriptor": descriptor,
            "access": access,
            "attributes": [],
        }

    def _run(
        self,
        old_fields,
        new_fields,
        old_paired,
        new_paired,
        *,
        base=None,
        original=None,
    ):
        base = base or self._base()
        original = original or self._original()

        def field_table(_jar, *, owner):
            if owner == "rs/A":
                return copy.deepcopy(old_fields)
            if owner == "rs/B":
                return copy.deepcopy(new_fields)
            raise AssertionError(owner)

        with (
            patch(
                "spk_recovery.boundary_field_block_evidence."
                "build_empty_field_declaration_evidence",
                return_value=copy.deepcopy(base),
            ),
            patch(
                "spk_recovery.boundary_field_block_evidence."
                "_unresolved_reviews",
                return_value={"MEMREL_TEST": copy.deepcopy(original)},
            ),
            patch(
                "spk_recovery.boundary_field_block_evidence."
                "_paired_field_maps",
                return_value=(old_paired, new_paired),
            ),
            patch(
                "spk_recovery.boundary_field_block_evidence._aliases",
                side_effect=[{}, {}],
            ),
            patch(
                "spk_recovery.boundary_field_block_evidence."
                "_jar_field_table",
                side_effect=field_table,
            ),
        ):
            return build_boundary_field_block_evidence(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                {"report_id": "GLOBALFIELDUSE_TEST"},
            )

    def test_exact_prefix_block_becomes_research_candidate(self):
        old_fields = [self._field("x"), self._field("anchor")]
        new_fields = [self._field("x"), self._field("anchor")]
        old_paired = {
            ("rs/A", "anchor", "I"): "CLIENT_FIELD_ANCHOR"
        }
        new_paired = {
            ("rs/B", "anchor", "I"): "CLIENT_FIELD_ANCHOR"
        }

        report = self._run(
            old_fields,
            new_fields,
            old_paired,
            new_paired,
        )

        self.assertFalse(report["canonical"])
        self.assertEqual(report["summary"]["candidate_fields"], 1)
        self.assertEqual(report["summary"]["prefix_block_exact"], 1)
        self.assertEqual(
            report["candidates"][0]["strategy"],
            "canonical_boundary_block_declaration_exact",
        )
        self.assertEqual(
            report["candidates"][0]["anchor_member_id"],
            "CLIENT_FIELD_ANCHOR",
        )
        self.assertEqual(report["candidates"][0]["target_offset"], 0)
        self.assertTrue(
            report["candidates"][0]["supports_existing_review"]
        )

    def test_exact_suffix_block_becomes_research_candidate(self):
        old_fields = [self._field("anchor"), self._field("x")]
        new_fields = [self._field("anchor"), self._field("x")]
        old_paired = {
            ("rs/A", "anchor", "I"): "CLIENT_FIELD_ANCHOR"
        }
        new_paired = {
            ("rs/B", "anchor", "I"): "CLIENT_FIELD_ANCHOR"
        }

        report = self._run(
            old_fields,
            new_fields,
            old_paired,
            new_paired,
        )

        self.assertEqual(report["summary"]["candidate_fields"], 1)
        self.assertEqual(report["summary"]["suffix_block_exact"], 1)
        self.assertEqual(
            report["candidates"][0]["block_kind"],
            "suffix_block_exact",
        )

    def test_exact_whole_class_becomes_research_candidate(self):
        report = self._run(
            [self._field("x")],
            [self._field("x")],
            {},
            {},
        )

        self.assertEqual(report["summary"]["candidate_fields"], 1)
        self.assertEqual(report["summary"]["whole_class_exact"], 1)
        self.assertIsNone(
            report["candidates"][0]["anchor_member_id"]
        )

    def test_asymmetric_boundary_state_is_rejected(self):
        old_fields = [self._field("x"), self._field("anchor")]
        new_fields = [self._field("anchor"), self._field("x")]
        old_paired = {
            ("rs/A", "anchor", "I"): "CLIENT_FIELD_ANCHOR"
        }
        new_paired = {
            ("rs/B", "anchor", "I"): "CLIENT_FIELD_ANCHOR"
        }

        report = self._run(
            old_fields,
            new_fields,
            old_paired,
            new_paired,
        )

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["boundary_symmetry_mismatch"],
            1,
        )

    def test_single_anchor_identity_mismatch_is_rejected(self):
        old_fields = [self._field("x"), self._field("anchor")]
        new_fields = [self._field("x"), self._field("anchor")]
        old_paired = {
            ("rs/A", "anchor", "I"): "CLIENT_FIELD_OLD"
        }
        new_paired = {
            ("rs/B", "anchor", "I"): "CLIENT_FIELD_NEW"
        }

        report = self._run(
            old_fields,
            new_fields,
            old_paired,
            new_paired,
        )

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["single_anchor_identity_mismatch"],
            1,
        )

    def test_complete_boundary_block_shape_must_match(self):
        old_fields = [
            self._field("x"),
            self._field("oldOnly"),
            self._field("anchor"),
        ]
        new_fields = [
            self._field("x"),
            self._field("newOnly"),
            self._field("anchor"),
        ]
        old_paired = {
            ("rs/A", "anchor", "I"): "CLIENT_FIELD_ANCHOR"
        }
        new_paired = {
            ("rs/B", "anchor", "I"): "CLIENT_FIELD_ANCHOR"
        }

        report = self._run(
            old_fields,
            new_fields,
            old_paired,
            new_paired,
        )

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["block_shape_mismatch"],
            1,
        )

    def test_complete_boundary_block_length_must_match(self):
        old_fields = [self._field("x"), self._field("anchor")]
        new_fields = [
            self._field("x"),
            self._field("extra"),
            self._field("anchor"),
        ]
        old_paired = {
            ("rs/A", "anchor", "I"): "CLIENT_FIELD_ANCHOR"
        }
        new_paired = {
            ("rs/B", "anchor", "I"): "CLIENT_FIELD_ANCHOR"
        }

        report = self._run(
            old_fields,
            new_fields,
            old_paired,
            new_paired,
        )

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["block_length_mismatch"],
            1,
        )

    def test_only_missing_anchor_rows_enter_boundary_frontier(self):
        base = self._base()
        base["rejected"].append(
            {
                "relationship_id": "MEMREL_RAW",
                "logical_class_id": "CLIENT_CLASS_A",
                "old_owner": "rs/A",
                "new_owner": "rs/B",
                "reason": "raw_source_guard_rejected",
            }
        )

        report = self._run(
            [self._field("x")],
            [self._field("x")],
            {},
            {},
            base=base,
        )

        self.assertEqual(
            report["summary"]["input_missing_anchor_reviews"],
            1,
        )
        self.assertEqual(report["summary"]["candidate_fields"], 1)

    def test_inputs_are_not_mutated(self):
        base = self._base()
        original = self._original()
        base_before = copy.deepcopy(base)
        original_before = copy.deepcopy(original)

        self._run(
            [self._field("x")],
            [self._field("x")],
            {},
            {},
            base=base,
            original=original,
        )

        self.assertEqual(base, base_before)
        self.assertEqual(original, original_before)


if __name__ == "__main__":
    unittest.main()
