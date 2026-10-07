from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.raw_source_exact_declaration_evidence import (
    RawSourceExactDeclarationEvidenceError,
    build_raw_source_exact_declaration_evidence,
)


class RawSourceExactDeclarationEvidenceTests(unittest.TestCase):
    @staticmethod
    def _field(name, descriptor="I", access=1):
        return {
            "name": name,
            "descriptor": descriptor,
            "access": access,
            "attributes": [],
        }

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
                    "reason": "raw_source_guard_rejected",
                    "old_global_source_class_topology": [
                        {
                            "source_class": "RAW:thirdparty/Caller",
                            "operation": "getstatic",
                            "count": 2,
                        }
                    ],
                    "new_global_source_class_topology": [
                        {
                            "source_class": "RAW:thirdparty/Caller",
                            "operation": "getstatic",
                            "count": 2,
                        }
                    ],
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
    def _raw_profile(sha="a" * 64, size=123):
        return {
            "source_class": "RAW:thirdparty/Caller",
            "internal_name": "thirdparty/Caller",
            "entry": "thirdparty/Caller.class",
            "sha256": sha,
            "byte_length": size,
        }

    def _run(
        self,
        *,
        base=None,
        original=None,
        old_fields=None,
        new_fields=None,
        old_paired=None,
        new_paired=None,
        raw_side_effect=None,
    ):
        base = base or self._base()
        original = original or self._original()
        old_fields = old_fields or [
            self._field("left"),
            self._field("x"),
            self._field("right"),
        ]
        new_fields = new_fields or [
            self._field("left"),
            self._field("x"),
            self._field("right"),
        ]
        old_paired = old_paired or {
            ("rs/A", "left", "I"): "CLIENT_FIELD_LEFT",
            ("rs/A", "right", "I"): "CLIENT_FIELD_RIGHT",
        }
        new_paired = new_paired or {
            ("rs/B", "left", "I"): "CLIENT_FIELD_LEFT",
            ("rs/B", "right", "I"): "CLIENT_FIELD_RIGHT",
        }

        def field_table(_jar, *, owner):
            if owner == "rs/A":
                return copy.deepcopy(old_fields)
            if owner == "rs/B":
                return copy.deepcopy(new_fields)
            raise AssertionError(owner)

        if raw_side_effect is None:
            raw_side_effect = [
                self._raw_profile(),
                self._raw_profile(),
            ]

        with (
            patch(
                "spk_recovery.raw_source_exact_declaration_evidence."
                "build_empty_field_declaration_evidence",
                return_value=copy.deepcopy(base),
            ),
            patch(
                "spk_recovery.raw_source_exact_declaration_evidence."
                "_unresolved_reviews",
                return_value={"MEMREL_TEST": copy.deepcopy(original)},
            ),
            patch(
                "spk_recovery.raw_source_exact_declaration_evidence."
                "_paired_field_maps",
                return_value=(old_paired, new_paired),
            ),
            patch(
                "spk_recovery.raw_source_exact_declaration_evidence."
                "_aliases",
                side_effect=[{}, {}],
            ),
            patch(
                "spk_recovery.raw_source_exact_declaration_evidence."
                "_jar_field_table",
                side_effect=field_table,
            ),
            patch(
                "spk_recovery.raw_source_exact_declaration_evidence."
                "_raw_class_profile",
                side_effect=raw_side_effect,
            ),
        ):
            return build_raw_source_exact_declaration_evidence(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                {"report_id": "GLOBALFIELDUSE_TEST"},
            )

    def test_exact_raw_class_bytes_and_interval_become_candidate(self):
        report = self._run()

        self.assertFalse(report["canonical"])
        self.assertEqual(
            report["summary"]["input_raw_source_guard_reviews"],
            1,
        )
        self.assertEqual(report["summary"]["candidate_fields"], 1)
        self.assertEqual(
            report["summary"]["remaining_without_raw_source_exact_proof"],
            0,
        )
        candidate = report["candidates"][0]
        self.assertEqual(
            candidate["strategy"],
            "exact_raw_source_class_bytes_and_"
            "canonical_anchor_declaration_interval",
        )
        self.assertEqual(candidate["confidence"], "INFERRED_HIGH")
        self.assertEqual(candidate["score"], 0.999)
        self.assertTrue(candidate["supports_existing_review"])
        self.assertEqual(len(candidate["raw_source_classes"]), 1)
        self.assertEqual(
            candidate["raw_source_classes"][0]["sha256"],
            "a" * 64,
        )

    def test_raw_source_topology_must_match(self):
        base = self._base()
        base["rejected"][0][
            "new_global_source_class_topology"
        ][0]["count"] = 3

        report = self._run(base=base)

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["raw_source_topology_mismatch"],
            1,
        )

    def test_missing_raw_class_is_rejected(self):
        report = self._run(
            raw_side_effect=[
                None,
                self._raw_profile(),
            ]
        )

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["raw_source_class_missing"],
            1,
        )

    def test_raw_class_byte_mismatch_is_rejected(self):
        report = self._run(
            raw_side_effect=[
                self._raw_profile("a" * 64),
                self._raw_profile("b" * 64),
            ]
        )

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["raw_source_class_bytes_mismatch"],
            1,
        )

    def test_missing_two_sided_anchor_is_rejected(self):
        report = self._run(
            old_paired={
                ("rs/A", "left", "I"): "CLIENT_FIELD_LEFT",
            },
            new_paired={
                ("rs/B", "left", "I"): "CLIENT_FIELD_LEFT",
            },
        )

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["missing_two_sided_canonical_anchor"],
            1,
        )

    def test_anchor_identity_mismatch_is_rejected(self):
        report = self._run(
            old_paired={
                ("rs/A", "left", "I"): "CLIENT_FIELD_LEFT",
                ("rs/A", "right", "I"): "CLIENT_FIELD_RIGHT",
            },
            new_paired={
                ("rs/B", "left", "I"): "CLIENT_FIELD_OTHER",
                ("rs/B", "right", "I"): "CLIENT_FIELD_RIGHT",
            },
        )

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["canonical_anchor_identity_mismatch"],
            1,
        )

    def test_declaration_interval_shape_must_match(self):
        report = self._run(
            old_fields=[
                self._field("left"),
                self._field("x"),
                self._field("oldNeighbor"),
                self._field("right"),
            ],
            new_fields=[
                self._field("left"),
                self._field("x"),
                self._field("newNeighbor"),
                self._field("right"),
            ],
        )

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["declaration_interval_shape_mismatch"],
            1,
        )

    def test_only_raw_guard_rows_enter_frontier(self):
        base = self._base()
        base["rejected"].append(
            {
                "relationship_id": "MEMREL_SHAPE",
                "logical_class_id": "CLIENT_CLASS_A",
                "old_owner": "rs/A",
                "new_owner": "rs/B",
                "reason": "declaration_interval_shape_mismatch",
            }
        )

        report = self._run(base=base)

        self.assertEqual(
            report["summary"]["input_raw_source_guard_reviews"],
            1,
        )
        self.assertEqual(report["summary"]["candidate_fields"], 1)

    def test_raw_rejection_without_raw_source_refuses(self):
        base = self._base()
        base["rejected"][0][
            "old_global_source_class_topology"
        ][0]["source_class"] = "CLIENT_CLASS_CALLER"
        base["rejected"][0][
            "new_global_source_class_topology"
        ][0]["source_class"] = "CLIENT_CLASS_CALLER"

        with self.assertRaisesRegex(
            RawSourceExactDeclarationEvidenceError,
            "contains no RAW source",
        ):
            self._run(base=base, raw_side_effect=[])

    def test_inputs_are_not_mutated(self):
        base = self._base()
        original = self._original()
        base_before = copy.deepcopy(base)
        original_before = copy.deepcopy(original)

        self._run(
            base=base,
            original=original,
        )

        self.assertEqual(base, base_before)
        self.assertEqual(original, original_before)


if __name__ == "__main__":
    unittest.main()
