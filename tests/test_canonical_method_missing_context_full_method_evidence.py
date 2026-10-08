from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.canonical_method_missing_context_full_method_evidence import (
    _full_method_tokens,
    _full_method_unique,
    build_canonical_method_missing_context_full_method_evidence,
)


def ins(mnemonic, **extra):
    return {"mnemonic": mnemonic, **extra}


class _FakeCache:
    def __init__(self, methods):
        self.methods = methods

    def method(self, coord):
        return copy.deepcopy(self.methods[coord])

    def close(self):
        pass


class CanonicalMethodMissingContextFullMethodEvidenceTests(unittest.TestCase):
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
            "summary": {},
            "candidates": [],
            "rejected": [
                {
                    "relationship_id": "MEMREL_TEST",
                    "logical_class_id": "CLIENT_CLASS_A",
                    "old_owner": "rs/A",
                    "new_owner": "rs/B",
                    "reason": "canonical_method_context_missing",
                    "base_global_usage_outcome": (
                        "global_class_topology_guard_rejected"
                    ),
                    "method_id": "M1",
                    "operation": "getstatic",
                    "expected_count": 1,
                    "old_context_count": 0,
                    "new_context_count": 0,
                }
            ],
        }

    def _method(self, owner, name):
        return {
            "name": name,
            "descriptor": "()I",
            "instructions": [
                ins(
                    "getstatic",
                    owner=owner,
                    name="x",
                    descriptor="I",
                ),
                ins("ireturn"),
            ],
            "field_accesses": [
                {
                    "owner": owner,
                    "name": "x",
                    "descriptor": "I",
                    "operation": "getstatic",
                }
            ],
        }

    def _run(self, *, new_return="ireturn", paired=True):
        report = self._context_report()
        old_method = self._method("rs/A", "a")
        new_method = self._method("rs/B", "b")
        new_method["instructions"][-1]["mnemonic"] = new_return
        old_paired = (
            {
                ("rs/A", "left", "I"): "LEFT",
                ("rs/A", "right", "I"): "RIGHT",
            }
            if paired else {}
        )
        new_paired = (
            {
                ("rs/B", "left", "I"): "LEFT",
                ("rs/B", "right", "I"): "RIGHT",
            }
            if paired else {}
        )

        def table(_jar, *, owner):
            return [
                {"name": "left", "descriptor": "I", "access": 1, "attributes": []},
                {"name": "x", "descriptor": "I", "access": 1, "attributes": []},
                {"name": "right", "descriptor": "I", "access": 1, "attributes": []},
            ]

        with (
            patch(
                "spk_recovery.canonical_method_missing_context_full_method_evidence."
                "build_canonical_method_field_context_evidence",
                return_value=copy.deepcopy(report),
            ),
            patch(
                "spk_recovery.canonical_method_missing_context_full_method_evidence."
                "_paired_method_maps",
                return_value=(
                    {"old/S": {("a", "()I"): "M1"}},
                    {"new/S": {("b", "()I"): "M1"}},
                    1,
                ),
            ),
            patch(
                "spk_recovery.canonical_method_missing_context_full_method_evidence."
                "_paired_member_maps",
                return_value=({}, {}),
            ),
            patch(
                "spk_recovery.canonical_method_missing_context_full_method_evidence."
                "_paired_class_aliases",
                return_value=({}, {}),
            ),
            patch(
                "spk_recovery.canonical_method_missing_context_full_method_evidence."
                "_paired_field_maps",
                return_value=(old_paired, new_paired),
            ),
            patch(
                "spk_recovery.canonical_method_missing_context_full_method_evidence."
                "_aliases",
                side_effect=[{}, {}],
            ),
            patch(
                "spk_recovery.canonical_method_missing_context_full_method_evidence."
                "_unresolved_reviews",
                return_value={
                    "MEMREL_TEST": {
                        "strategy": "stable_symbol",
                        "old": {"name": "x", "descriptor": "I", "access": 1},
                        "new": {"name": "x", "descriptor": "I", "access": 1},
                    }
                },
            ),
            patch(
                "spk_recovery.canonical_method_missing_context_full_method_evidence."
                "_jar_field_table",
                side_effect=table,
            ),
            patch(
                "spk_recovery.canonical_method_missing_context_full_method_evidence."
                "_ProfileCache",
                side_effect=[
                    _FakeCache({("old/S", "a", "()I"): old_method}),
                    _FakeCache({("new/S", "b", "()I"): new_method}),
                ],
            ),
        ):
            return build_canonical_method_missing_context_full_method_evidence(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                {"report_id": "GLOBAL_TEST"},
                report,
            )

    def test_short_method_reaches_candidate(self):
        out = self._run()
        self.assertEqual(out["summary"]["candidate_fields"], 1)
        self.assertEqual(
            out["candidates"][0]["strategy"],
            "canonical_method_full_normalized_fingerprint_and_"
            "canonical_anchor_declaration_interval_exact",
        )

    def test_full_method_mismatch_is_rejected(self):
        out = self._run(new_return="areturn")
        self.assertEqual(out["summary"]["candidate_fields"], 0)
        self.assertEqual(
            out["summary"]["full_method_fingerprint_mismatch"],
            1,
        )

    def test_missing_anchors_stays_unresolved(self):
        out = self._run(paired=False)
        self.assertEqual(out["summary"]["candidate_fields"], 0)
        self.assertEqual(
            out["summary"]["missing_two_sided_canonical_anchor"],
            1,
        )

    def test_competitor_with_same_full_fingerprint_is_nonunique(self):
        method = {
            "instructions": [
                ins("getstatic", owner="rs/A", name="x", descriptor="I"),
                ins("getstatic", owner="rs/A", name="z", descriptor="I"),
            ],
            "field_accesses": [
                {
                    "owner": "rs/A", "name": "x", "descriptor": "I",
                    "operation": "getstatic",
                },
                {
                    "owner": "rs/A", "name": "z", "descriptor": "I",
                    "operation": "getstatic",
                },
            ],
        }
        target = ("rs/A", "x", "I")
        tokens = _full_method_tokens(
            method,
            target=target,
            operation="getstatic",
            expected_count=1,
            member_map={},
            class_aliases={},
        )
        self.assertIsNotNone(tokens)
        self.assertTrue(
            _full_method_unique(
                method,
                target=target,
                operation="getstatic",
                expected_count=1,
                target_tokens=tokens,
                member_map={},
                class_aliases={},
            )
        )

    def test_inputs_are_not_mutated(self):
        report = self._context_report()
        before = copy.deepcopy(report)
        with patch(
            "spk_recovery.canonical_method_missing_context_full_method_evidence."
            "build_canonical_method_field_context_evidence",
            return_value=copy.deepcopy(report),
        ):
            self.assertEqual(report, before)


    def test_full_method_rejects_malformed_instruction_rows(self):
        method = self._method("rs/A", "a")
        method["instructions"].insert(1, None)
        self.assertIsNone(
            _full_method_tokens(
                method,
                target=("rs/A", "x", "I"),
                operation="getstatic",
                expected_count=1,
                member_map={},
                class_aliases={},
            )
        )


if __name__ == "__main__":
    unittest.main()
