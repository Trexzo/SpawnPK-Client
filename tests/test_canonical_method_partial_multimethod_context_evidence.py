from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.canonical_method_partial_multimethod_context_evidence import (
    build_canonical_method_partial_multimethod_context_evidence,
)


class _FakeCache:
    def __init__(self, methods):
        self.methods = methods

    def method(self, coord):
        return copy.deepcopy(self.methods[coord])

    def close(self):
        pass


class PartialMultimethodContextEvidenceTests(unittest.TestCase):
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
                "canonical_method_context_missing": 1,
                "canonical_method_context_mismatch": 0,
                "canonical_method_context_nonunique": 0,
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
                    "reason": "canonical_method_context_missing",
                    "base_global_usage_outcome": "global_class_topology_guard_rejected",
                    "method_id": "M2",
                    "operation": "getstatic",
                    "expected_count": 1,
                    "old_context_count": 0,
                    "new_context_count": 0,
                }
            ],
        }

    def _global_report(self):
        return {
            "review_outcomes": [
                {
                    "relationship_id": "MEMREL_TEST",
                    "outcome": "global_class_topology_guard_rejected",
                    "canonical_method_topology": [
                        {"member_id": "M1", "operation": "getstatic", "count": 1},
                        {"member_id": "M2", "operation": "getstatic", "count": 1},
                        {"member_id": "M3", "operation": "getstatic", "count": 1},
                    ],
                }
            ]
        }

    def _run(self, *, one_sided=False, nonunique=False):
        context = self._context_report()
        global_report = self._global_report()

        old_methods = {
            ("old/S1", "a", "()V"): {"id": "M1", "side": "old"},
            ("old/S2", "b", "()V"): {"id": "M2", "side": "old"},
            ("old/S3", "c", "()V"): {"id": "M3", "side": "old"},
        }
        new_methods = {
            ("new/S1", "d", "()V"): {"id": "M1", "side": "new"},
            ("new/S2", "e", "()V"): {"id": "M2", "side": "new"},
            ("new/S3", "f", "()V"): {"id": "M3", "side": "new"},
        }

        def contexts(method, **_kwargs):
            mid = method["id"]
            if mid == "M2":
                if one_sided and method["side"] == "new":
                    return Counter({"c" * 64: 1})
                return Counter()
            return Counter({("a" if mid == "M1" else "b") * 64: 1})

        def unique(method, **_kwargs):
            return not (nonunique and method["id"] == "M3")

        def table(_jar, *, owner):
            return [
                {"name": "left", "descriptor": "I", "access": 1, "attributes": []},
                {"name": "x", "descriptor": "I", "access": 9, "attributes": []},
                {"name": "right", "descriptor": "I", "access": 1, "attributes": []},
            ]

        with (
            patch(
                "spk_recovery.canonical_method_partial_multimethod_context_evidence."
                "build_canonical_method_field_context_evidence",
                return_value=copy.deepcopy(context),
            ),
            patch(
                "spk_recovery.canonical_method_partial_multimethod_context_evidence."
                "_unresolved_reviews",
                return_value={
                    "MEMREL_TEST": {
                        "strategy": "stable_symbol",
                        "old": {"name": "x", "descriptor": "I", "access": 9},
                        "new": {"name": "x", "descriptor": "I", "access": 9},
                    }
                },
            ),
            patch(
                "spk_recovery.canonical_method_partial_multimethod_context_evidence."
                "_paired_method_maps",
                return_value=(
                    {
                        "old/S1": {("a", "()V"): "M1"},
                        "old/S2": {("b", "()V"): "M2"},
                        "old/S3": {("c", "()V"): "M3"},
                    },
                    {
                        "new/S1": {("d", "()V"): "M1"},
                        "new/S2": {("e", "()V"): "M2"},
                        "new/S3": {("f", "()V"): "M3"},
                    },
                    3,
                ),
            ),
            patch(
                "spk_recovery.canonical_method_partial_multimethod_context_evidence."
                "_paired_member_maps",
                return_value=({}, {}),
            ),
            patch(
                "spk_recovery.canonical_method_partial_multimethod_context_evidence."
                "_paired_class_aliases",
                return_value=({}, {}),
            ),
            patch(
                "spk_recovery.canonical_method_partial_multimethod_context_evidence."
                "_paired_field_maps",
                return_value=(
                    {
                        ("rs/A", "left", "I"): "LEFT",
                        ("rs/A", "right", "I"): "RIGHT",
                    },
                    {
                        ("rs/B", "left", "I"): "LEFT",
                        ("rs/B", "right", "I"): "RIGHT",
                    },
                ),
            ),
            patch(
                "spk_recovery.canonical_method_partial_multimethod_context_evidence."
                "_aliases",
                side_effect=[{}, {}],
            ),
            patch(
                "spk_recovery.canonical_method_partial_multimethod_context_evidence."
                "_jar_field_table",
                side_effect=table,
            ),
            patch(
                "spk_recovery.canonical_method_partial_multimethod_context_evidence."
                "_ProfileCache",
                side_effect=[
                    _FakeCache(old_methods),
                    _FakeCache(new_methods),
                ],
            ),
            patch(
                "spk_recovery.canonical_method_partial_multimethod_context_evidence."
                "_context_multiset",
                side_effect=contexts,
            ),
            patch(
                "spk_recovery.canonical_method_partial_multimethod_context_evidence."
                "_context_unique_in_method",
                side_effect=unique,
            ),
        ):
            return build_canonical_method_partial_multimethod_context_evidence(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                global_report,
                context,
            )

    def test_symmetric_missing_with_two_surviving_methods_is_candidate(self):
        out = self._run()
        self.assertEqual(out["summary"]["candidate_fields"], 1)
        candidate = out["candidates"][0]
        self.assertEqual(candidate["canonical_methods"], 2)
        self.assertEqual(len(candidate["symmetric_unavailable_methods"]), 1)

    def test_one_sided_context_loss_is_rejected(self):
        out = self._run(one_sided=True)
        self.assertEqual(out["summary"]["candidate_fields"], 0)
        self.assertEqual(
            out["summary"]["partial_context_observation_count_mismatch"],
            1,
        )

    def test_nonunique_surviving_context_is_rejected(self):
        out = self._run(nonunique=True)
        self.assertEqual(out["summary"]["candidate_fields"], 0)
        self.assertEqual(out["summary"]["partial_context_nonunique"], 1)


if __name__ == "__main__":
    unittest.main()
