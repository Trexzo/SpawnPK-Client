from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.canonical_method_nonunique_context_declaration_evidence import (
    build_canonical_method_nonunique_context_declaration_evidence,
)


class CanonicalMethodNonuniqueContextDeclarationEvidenceTests(unittest.TestCase):
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
                "canonical_method_context_nonunique": 1,
                "insufficient_independent_context_witness": 0,
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
                    "reason": "canonical_method_context_nonunique",
                    "base_global_usage_outcome": "global_class_topology_guard_rejected",
                    "method_id": "M1",
                    "operation": "putfield",
                    "old_unique": False,
                    "new_unique": False,
                    "contexts": [["a" * 64, 1]],
                }
            ],
        }

    def _run(self, *, paired_fields=True, new_name="x"):
        report = self._context_report()
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
                    {"name": "x", "descriptor": "I", "access": 1, "attributes": []},
                    {"name": "right", "descriptor": "I", "access": 1, "attributes": []},
                ]
            return [
                {"name": "left", "descriptor": "I", "access": 1, "attributes": []},
                {"name": new_name, "descriptor": "I", "access": 1, "attributes": []},
                {"name": "right", "descriptor": "I", "access": 1, "attributes": []},
            ]

        with (
            patch(
                "spk_recovery.canonical_method_nonunique_context_declaration_evidence."
                "build_canonical_method_field_context_evidence",
                return_value=copy.deepcopy(report),
            ),
            patch(
                "spk_recovery.canonical_method_nonunique_context_declaration_evidence."
                "_unresolved_reviews",
                return_value={
                    "MEMREL_TEST": {
                        "strategy": "stable_symbol",
                        "old": {"name": "x", "descriptor": "I", "access": 1},
                        "new": {"name": new_name, "descriptor": "I", "access": 1},
                    }
                },
            ),
            patch(
                "spk_recovery.canonical_method_nonunique_context_declaration_evidence."
                "_paired_field_maps",
                return_value=(old_paired, new_paired),
            ),
            patch(
                "spk_recovery.canonical_method_nonunique_context_declaration_evidence."
                "_aliases",
                side_effect=[{}, {}],
            ),
            patch(
                "spk_recovery.canonical_method_nonunique_context_declaration_evidence."
                "_jar_field_table",
                side_effect=table,
            ),
        ):
            return build_canonical_method_nonunique_context_declaration_evidence(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                {"report_id": "GLOBAL_TEST"},
                report,
            )

    def test_nonunique_context_plus_exact_declaration_is_candidate(self):
        out = self._run()
        self.assertEqual(out["summary"]["candidate_fields"], 1)
        self.assertEqual(
            out["candidates"][0]["strategy"],
            "canonical_method_nonunique_local_context_and_"
            "canonical_anchor_declaration_interval_exact",
        )

    def test_context_nonuniqueness_remains_explicit(self):
        out = self._run()
        candidate = out["candidates"][0]
        self.assertIs(candidate["old_unique"], False)
        self.assertIs(candidate["new_unique"], False)

    def test_missing_anchor_stays_unresolved(self):
        out = self._run(paired_fields=False)
        self.assertEqual(out["summary"]["candidate_fields"], 0)
        self.assertEqual(
            out["summary"]["missing_two_sided_canonical_anchor"],
            1,
        )

    def test_declaration_name_drift_stays_unresolved(self):
        out = self._run(new_name="y")
        self.assertEqual(out["summary"]["candidate_fields"], 0)
        self.assertEqual(
            out["summary"]["declaration_interval_shape_mismatch"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
