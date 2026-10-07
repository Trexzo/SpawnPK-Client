from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.canonical_method_field_context_evidence import (
    _context_multiset,
    _context_unique_in_method,
    _instruction_token,
    build_canonical_method_field_context_evidence,
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


class CanonicalMethodFieldContextEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.target_old = ("rs/A", "x", "I")
        self.target_new = ("rs/B", "y", "I")

    def test_target_field_name_is_masked(self):
        old = _instruction_token(
            ins(
                "getfield",
                owner="rs/A",
                name="x",
                descriptor="I",
            ),
            target=self.target_old,
            member_map={},
            class_aliases={},
        )
        new = _instruction_token(
            ins(
                "getfield",
                owner="rs/B",
                name="y",
                descriptor="I",
            ),
            target=self.target_new,
            member_map={},
            class_aliases={},
        )
        self.assertEqual(old, new)

    def test_unpaired_neighbor_member_names_do_not_contribute(self):
        a = _instruction_token(
            ins(
                "invokevirtual",
                owner="raw/X",
                name="oldName",
                descriptor="(Ljava/lang/String;)V",
            ),
            target=self.target_old,
            member_map={},
            class_aliases={},
        )
        b = _instruction_token(
            ins(
                "invokevirtual",
                owner="raw/Y",
                name="newName",
                descriptor="(Lother/Z;)V",
            ),
            target=self.target_new,
            member_map={},
            class_aliases={},
        )
        self.assertEqual(a, b)

    def test_absolute_branch_offsets_do_not_contribute(self):
        a = _instruction_token(
            ins("ifne", branch_target_offset=100, offset=4),
            target=self.target_old,
            member_map={},
            class_aliases={},
        )
        b = _instruction_token(
            ins("ifne", branch_target_offset=900, offset=44),
            target=self.target_new,
            member_map={},
            class_aliases={},
        )
        self.assertEqual(a, b)

    def test_canonical_neighbor_member_id_does_contribute(self):
        row = ins(
            "getstatic",
            owner="rs/C",
            name="z",
            descriptor="I",
        )
        token = _instruction_token(
            row,
            target=self.target_old,
            member_map={
                ("field", "rs/C", "z", "I"): "CLIENT_FIELD_Z"
            },
            class_aliases={},
        )
        self.assertEqual(
            token,
            ["FIELD_CANON", "getstatic", "CLIENT_FIELD_Z"],
        )

    def test_raw_type_name_does_not_contribute(self):
        a = _instruction_token(
            ins("checkcast", type="old/A"),
            target=self.target_old,
            member_map={},
            class_aliases={},
        )
        b = _instruction_token(
            ins("checkcast", type="new/B"),
            target=self.target_new,
            member_map={},
            class_aliases={},
        )
        self.assertEqual(a, b)

    def test_context_multiset_matches_after_target_rename(self):
        old = {
            "instructions": [
                ins("aload", local_index=0),
                ins(
                    "getfield",
                    owner="rs/A",
                    name="x",
                    descriptor="I",
                ),
                ins("iconst_1", int_constant=1),
                ins("iadd"),
                ins("ireturn"),
            ],
            "field_accesses": [],
        }
        new = copy.deepcopy(old)
        new["instructions"][1].update(
            {"owner": "rs/B", "name": "y"}
        )
        old_ctx = _context_multiset(
            old,
            target=self.target_old,
            operation="getfield",
            member_map={},
            class_aliases={},
        )
        new_ctx = _context_multiset(
            new,
            target=self.target_new,
            operation="getfield",
            member_map={},
            class_aliases={},
        )
        self.assertEqual(old_ctx, new_ctx)
        self.assertEqual(sum(old_ctx.values()), 1)

    def test_competitor_with_identical_context_is_nonunique(self):
        method = {
            "instructions": [
                ins("aload", local_index=0),
                ins(
                    "getfield",
                    owner="rs/A",
                    name="x",
                    descriptor="I",
                ),
                ins("pop"),
                ins("aload", local_index=0),
                ins(
                    "getfield",
                    owner="rs/A",
                    name="z",
                    descriptor="I",
                ),
                ins("pop"),
            ],
            "field_accesses": [
                {
                    "owner": "rs/A",
                    "name": "x",
                    "descriptor": "I",
                    "operation": "getfield",
                },
                {
                    "owner": "rs/A",
                    "name": "z",
                    "descriptor": "I",
                    "operation": "getfield",
                },
            ],
        }
        target = ("rs/A", "x", "I")
        target_ctx = _context_multiset(
            method,
            target=target,
            operation="getfield",
            member_map={},
            class_aliases={},
            radius=1,
        )
        self.assertFalse(
            _context_unique_in_method(
                method,
                target=target,
                operation="getfield",
                target_context=target_ctx,
                member_map={},
                class_aliases={},
                radius=1,
            )
        )

    def _base_report(self):
        return {
            "schema_version": 1,
            "kind": "global_field_usage_identity_candidates",
            "canonical": False,
            "report_id": "GLOBAL_TEST",
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": "3" * 64,
            "summary": {},
            "candidates": [],
            "descriptor_identity_rejections": [],
            "review_outcomes": [
                {
                    "relationship_id": "MEMREL_TEST",
                    "logical_class_id": "CLIENT_CLASS_A",
                    "old_owner": "rs/A",
                    "new_owner": "rs/B",
                    "old": {
                        "name": "x",
                        "descriptor": "I",
                        "access": 1,
                    },
                    "new": {
                        "name": "y",
                        "descriptor": "I",
                        "access": 1,
                    },
                    "outcome": "global_class_topology_guard_rejected",
                    "canonical_method_topology": [
                        {
                            "member_id": "M1",
                            "operation": "getfield",
                            "count": 1,
                        },
                        {
                            "member_id": "M2",
                            "operation": "getfield",
                            "count": 1,
                        },
                    ],
                    "old_global_source_class_topology": [],
                    "new_global_source_class_topology": [],
                }
            ],
        }

    def _method(self, owner, name, *, marker):
        return {
            "name": name,
            "descriptor": "()I",
            "instructions": [
                ins("aload", local_index=0),
                ins(
                    "getfield",
                    owner=owner,
                    name="x" if owner == "rs/A" else "y",
                    descriptor="I",
                ),
                ins(f"iconst_{marker}", int_constant=marker),
                ins("iadd"),
                ins("ireturn"),
            ],
            "field_accesses": [
                {
                    "owner": owner,
                    "name": "x" if owner == "rs/A" else "y",
                    "descriptor": "I",
                    "operation": "getfield",
                }
            ],
        }

    def _run(
        self,
        *,
        report=None,
        method2_marker_new=2,
        paired_fields=True,
    ):
        report = report or self._base_report()
        old_methods = {
            ("old/S1", "a", "()I"): self._method(
                "rs/A", "a", marker=1
            ),
            ("old/S2", "b", "()I"): self._method(
                "rs/A", "b", marker=2
            ),
        }
        new_methods = {
            ("new/S1", "c", "()I"): self._method(
                "rs/B", "c", marker=1
            ),
            ("new/S2", "d", "()I"): self._method(
                "rs/B", "d", marker=method2_marker_new
            ),
        }
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
            name = "x" if owner == "rs/A" else "y"
            return [
                {"name": "left", "descriptor": "I", "access": 1, "attributes": []},
                {"name": name, "descriptor": "I", "access": 1, "attributes": []},
                {"name": "right", "descriptor": "I", "access": 1, "attributes": []},
            ]

        with (
            patch(
                "spk_recovery.canonical_method_field_context_evidence."
                "build_global_field_usage_evidence",
                return_value=copy.deepcopy(report),
            ),
            patch(
                "spk_recovery.canonical_method_field_context_evidence."
                "_paired_method_maps",
                return_value=(
                    {
                        "old/S1": {("a", "()I"): "M1"},
                        "old/S2": {("b", "()I"): "M2"},
                    },
                    {
                        "new/S1": {("c", "()I"): "M1"},
                        "new/S2": {("d", "()I"): "M2"},
                    },
                    2,
                ),
            ),
            patch(
                "spk_recovery.canonical_method_field_context_evidence."
                "_paired_member_maps",
                return_value=({}, {}),
            ),
            patch(
                "spk_recovery.canonical_method_field_context_evidence."
                "_paired_class_aliases",
                return_value=({}, {}),
            ),
            patch(
                "spk_recovery.canonical_method_field_context_evidence."
                "_aliases",
                side_effect=[{}, {}],
            ),
            patch(
                "spk_recovery.canonical_method_field_context_evidence."
                "_paired_field_maps",
                return_value=(old_paired, new_paired),
            ),
            patch(
                "spk_recovery.canonical_method_field_context_evidence."
                "_unresolved_reviews",
                return_value={
                    "MEMREL_TEST": {
                        "strategy": "stable_symbol",
                        "old": {
                            "name": "x",
                            "descriptor": "I",
                            "access": 1,
                        },
                        "new": {
                            "name": "y",
                            "descriptor": "I",
                            "access": 1,
                        },
                    }
                },
            ),
            patch(
                "spk_recovery.canonical_method_field_context_evidence."
                "_jar_field_table",
                side_effect=table,
            ),
            patch(
                "spk_recovery.canonical_method_field_context_evidence."
                "_ProfileCache",
                side_effect=[
                    _FakeCache(old_methods),
                    _FakeCache(new_methods),
                ],
            ),
        ):
            return build_canonical_method_field_context_evidence(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                report,
            )

    def test_two_canonical_methods_with_exact_context_reach_candidate(self):
        out = self._run()
        self.assertEqual(out["summary"]["candidate_fields"], 1)
        self.assertEqual(
            out["candidates"][0]["strategy"],
            "canonical_method_unique_local_context_and_"
            "canonical_anchor_declaration_interval_exact",
        )

    def test_context_mismatch_is_rejected(self):
        out = self._run(method2_marker_new=3)
        self.assertEqual(out["summary"]["candidate_fields"], 0)
        self.assertEqual(
            out["summary"]["canonical_method_context_mismatch"],
            1,
        )

    def test_missing_declaration_anchors_are_rejected(self):
        out = self._run(paired_fields=False)
        self.assertEqual(out["summary"]["candidate_fields"], 0)
        self.assertEqual(
            out["summary"]["missing_two_sided_canonical_anchor"],
            1,
        )

    def test_only_global_class_topology_rejects_enter_frontier(self):
        report = self._base_report()
        report["review_outcomes"].append(
            {
                "relationship_id": "OTHER",
                "outcome": "empty_both",
            }
        )
        out = self._run(report=report)
        self.assertEqual(
            out["summary"]["input_global_class_topology_guard_rejected"],
            1,
        )

    def test_inputs_are_not_mutated(self):
        report = self._base_report()
        before = copy.deepcopy(report)
        self._run(report=report)
        self.assertEqual(report, before)


if __name__ == "__main__":
    unittest.main()
