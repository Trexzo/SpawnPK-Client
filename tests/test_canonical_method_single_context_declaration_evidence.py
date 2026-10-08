from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.canonical_method_single_context_declaration_evidence import (
    build_canonical_method_single_context_declaration_evidence,
)


class CanonicalMethodSingleContextDeclarationEvidenceTests(unittest.TestCase):
    def _context_report(self):
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
                "input_global_class_topology_guard_rejected": 1,
                "candidate_fields": 0,
                "remaining_without_context_proof": 1,
                "canonical_method_context_missing": 0,
                "canonical_method_context_mismatch": 0,
                "canonical_method_context_nonunique": 0,
                "insufficient_independent_context_witness": 1,
                "missing_two_sided_canonical_anchor": 0,
                "canonical_anchor_identity_mismatch": 0,
                "declaration_interval_length_mismatch": 0,
                "declaration_interval_shape_mismatch": 0,
                "target_interval_offset_mismatch": 0,
                "target_declaration_signature_not_unique": 0,
            },
            "candidates": [],
            "rejected": [
                {
                    "relationship_id": "MEMREL_TEST",
                    "logical_class_id": "CLIENT_CLASS_A",
                    "old_owner": "rs/A",
                    "new_owner": "rs/B",
                    "reason": "insufficient_independent_context_witness",
                    "base_global_usage_outcome": (
                        "global_class_topology_guard_rejected"
                    ),
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
                }
            ],
        }

    def _run(
        self,
        *,
        context_report=None,
        paired_fields=True,
        old_descriptor="I",
        new_descriptor="I",
        old_aliases=None,
        new_aliases=None,
    ):
        context_report = context_report or self._context_report()
        old_paired = (
            {
                ("rs/A", "left", "I"): "LEFT",
                ("rs/A", "right", "I"): "RIGHT",
            }
            if paired_fields
            else {}
        )
        new_paired = (
            {
                ("rs/B", "left", "I"): "LEFT",
                ("rs/B", "right", "I"): "RIGHT",
            }
            if paired_fields
            else {}
        )

        def table(_jar, *, owner):
            if owner == "rs/A":
                return [
                    {"name": "left", "descriptor": "I", "access": 1, "attributes": []},
                    {
                        "name": "x",
                        "descriptor": old_descriptor,
                        "access": 1,
                        "attributes": [],
                    },
                    {"name": "right", "descriptor": "I", "access": 1, "attributes": []},
                ]
            return [
                {"name": "left", "descriptor": "I", "access": 1, "attributes": []},
                {
                    "name": "x",
                    "descriptor": new_descriptor,
                    "access": 1,
                    "attributes": [],
                },
                {"name": "right", "descriptor": "I", "access": 1, "attributes": []},
            ]

        with (
            patch(
                "spk_recovery.canonical_method_single_context_declaration_evidence."
                "build_canonical_method_field_context_evidence",
                return_value=copy.deepcopy(context_report),
            ),
            patch(
                "spk_recovery.canonical_method_single_context_declaration_evidence."
                "_unresolved_reviews",
                return_value={
                    "MEMREL_TEST": {
                        "strategy": "stable_symbol",
                        "old": {
                            "name": "x",
                            "descriptor": old_descriptor,
                            "access": 1,
                        },
                        "new": {
                            "name": "x",
                            "descriptor": new_descriptor,
                            "access": 1,
                        },
                    }
                },
            ),
            patch(
                "spk_recovery.canonical_method_single_context_declaration_evidence."
                "_paired_field_maps",
                return_value=(old_paired, new_paired),
            ),
            patch(
                "spk_recovery.canonical_method_single_context_declaration_evidence."
                "_aliases",
                side_effect=[
                    old_aliases or {},
                    new_aliases or {},
                ],
            ),
            patch(
                "spk_recovery.canonical_method_single_context_declaration_evidence."
                "_jar_field_table",
                side_effect=table,
            ),
        ):
            return build_canonical_method_single_context_declaration_evidence(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                {"report_id": "GLOBAL_TEST"},
                context_report,
            )

    def test_single_unique_context_plus_exact_declaration_is_candidate(self):
        out = self._run()
        self.assertEqual(out["summary"]["candidate_fields"], 1)
        self.assertEqual(
            out["candidates"][0]["strategy"],
            "canonical_method_single_unique_local_context_and_"
            "canonical_anchor_declaration_interval_exact",
        )
        self.assertEqual(out["candidates"][0]["method_id"], "M1")
        self.assertEqual(out["candidates"][0]["context_digest"], "a" * 64)

    def test_missing_two_sided_anchor_stays_unresolved(self):
        out = self._run(paired_fields=False)
        self.assertEqual(out["summary"]["candidate_fields"], 0)
        self.assertEqual(
            out["summary"]["missing_two_sided_canonical_anchor"],
            1,
        )

    def test_declaration_shape_mismatch_stays_unresolved(self):
        out = self._run(new_descriptor="J")
        self.assertEqual(out["summary"]["candidate_fields"], 0)
        self.assertEqual(
            out["summary"]["declaration_interval_shape_mismatch"],
            1,
        )

    def test_canonical_class_descriptor_rename_is_normalized(self):
        out = self._run(
            old_descriptor="Lrs/old/A;",
            new_descriptor="Lrs/new/B;",
            old_aliases={"rs/old/A": "CLIENT_CLASS_TARGET"},
            new_aliases={"rs/new/B": "CLIENT_CLASS_TARGET"},
        )
        self.assertEqual(out["summary"]["candidate_fields"], 1)

    def test_repeated_observations_of_one_context_are_candidate(self):
        report = self._context_report()
        row = report["rejected"][0]
        row["observations"] = 2
        row["method_witnesses"][0]["count"] = 2
        row["method_witnesses"][0]["contexts"][0][1] = 2
        out = self._run(context_report=report)
        self.assertEqual(out["summary"]["candidate_fields"], 1)
        self.assertEqual(out["candidates"][0]["observations"], 2)

    def test_multiple_distinct_contexts_do_not_enter_single_context_lane(self):
        report = self._context_report()
        row = report["rejected"][0]
        row["observations"] = 2
        row["distinct_contexts"] = 2
        row["method_witnesses"][0]["count"] = 2
        row["method_witnesses"][0]["contexts"] = [
            ["a" * 64, 1],
            ["b" * 64, 1],
        ]
        out = self._run(context_report=report)
        self.assertEqual(out["summary"]["candidate_fields"], 0)
        self.assertEqual(
            out["summary"]["single_context_shape_mismatch"],
            1,
        )

    def test_only_insufficient_witness_rows_enter_frontier(self):
        report = self._context_report()
        report["rejected"].append(
            {
                "relationship_id": "OTHER",
                "reason": "canonical_method_context_nonunique",
            }
        )
        report["summary"]["input_global_class_topology_guard_rejected"] = 2
        report["summary"]["remaining_without_context_proof"] = 2
        report["summary"]["canonical_method_context_nonunique"] = 1
        out = self._run(context_report=report)
        self.assertEqual(out["summary"]["input_insufficient_witness_reviews"], 1)

    def test_inputs_are_not_mutated(self):
        report = self._context_report()
        before = copy.deepcopy(report)
        self._run(context_report=report)
        self.assertEqual(report, before)


if __name__ == "__main__":
    unittest.main()
