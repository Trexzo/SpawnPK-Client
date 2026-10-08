from __future__ import annotations

import unittest

from spk_recovery.canonical_method_boundary_block_evidence import (
    CanonicalMethodBoundaryBlockEvidenceError,
    _prove_boundary_block,
    _witness_stats,
)


def field(name: str, descriptor: str = "I", access: int = 1):
    return {
        "name": name,
        "descriptor": descriptor,
        "access": access,
        "attributes": [],
    }


class CanonicalMethodBoundaryBlockEvidenceTests(unittest.TestCase):
    def prove(
        self,
        old_fields,
        new_fields,
        old_paired,
        new_paired,
        old_pos,
        new_pos,
    ):
        return _prove_boundary_block(
            old_fields=old_fields,
            new_fields=new_fields,
            old_paired=old_paired,
            new_paired=new_paired,
            old_aliases={},
            new_aliases={},
            old_owner="old/C",
            new_owner="new/C",
            old_index_pos=old_pos,
            new_index_pos=new_pos,
        )

    def test_prefix_block_exact(self):
        old_fields = [field("target"), field("anchor")]
        new_fields = [field("target"), field("anchor")]
        old_paired = {("old/C", "anchor", "I"): "MEM_A"}
        new_paired = {("new/C", "anchor", "I"): "MEM_A"}

        ok, proof = self.prove(
            old_fields, new_fields, old_paired, new_paired, 0, 0
        )

        self.assertTrue(ok)
        self.assertEqual(proof["block_kind"], "prefix_block_exact")
        self.assertEqual(proof["anchor_member_id"], "MEM_A")
        self.assertEqual(proof["block_length"], 1)
        self.assertEqual(proof["target_offset"], 0)

    def test_suffix_block_exact(self):
        old_fields = [field("anchor"), field("target")]
        new_fields = [field("anchor"), field("target")]
        old_paired = {("old/C", "anchor", "I"): "MEM_A"}
        new_paired = {("new/C", "anchor", "I"): "MEM_A"}

        ok, proof = self.prove(
            old_fields, new_fields, old_paired, new_paired, 1, 1
        )

        self.assertTrue(ok)
        self.assertEqual(proof["block_kind"], "suffix_block_exact")
        self.assertEqual(proof["anchor_member_id"], "MEM_A")

    def test_whole_class_exact(self):
        ok, proof = self.prove(
            [field("target")],
            [field("target")],
            {},
            {},
            0,
            0,
        )

        self.assertTrue(ok)
        self.assertEqual(proof["block_kind"], "whole_class_exact")
        self.assertIsNone(proof["anchor_member_id"])

    def test_boundary_symmetry_mismatch_refused(self):
        old_fields = [field("target"), field("anchor")]
        new_fields = [field("target"), field("anchor")]
        old_paired = {("old/C", "anchor", "I"): "MEM_A"}

        ok, proof = self.prove(
            old_fields, new_fields, old_paired, {}, 0, 0
        )

        self.assertFalse(ok)
        self.assertEqual(proof["reason"], "boundary_symmetry_mismatch")

    def test_single_anchor_identity_mismatch_refused(self):
        old_fields = [field("target"), field("anchor")]
        new_fields = [field("target"), field("anchor")]
        old_paired = {("old/C", "anchor", "I"): "MEM_A"}
        new_paired = {("new/C", "anchor", "I"): "MEM_B"}

        ok, proof = self.prove(
            old_fields, new_fields, old_paired, new_paired, 0, 0
        )

        self.assertFalse(ok)
        self.assertEqual(
            proof["reason"],
            "single_anchor_identity_mismatch",
        )

    def test_block_length_mismatch_refused(self):
        old_fields = [field("target"), field("anchor")]
        new_fields = [
            field("target"),
            field("extra"),
            field("anchor"),
        ]
        old_paired = {("old/C", "anchor", "I"): "MEM_A"}
        new_paired = {("new/C", "anchor", "I"): "MEM_A"}

        ok, proof = self.prove(
            old_fields, new_fields, old_paired, new_paired, 0, 0
        )

        self.assertFalse(ok)
        self.assertEqual(proof["reason"], "block_length_mismatch")

    def test_block_shape_mismatch_refused(self):
        ok, proof = self.prove(
            [field("old_target")],
            [field("new_target")],
            {},
            {},
            0,
            0,
        )

        self.assertFalse(ok)
        self.assertEqual(proof["reason"], "block_shape_mismatch")

    def test_target_offset_mismatch_refused(self):
        fields = [field("a"), field("b")]

        ok, proof = self.prove(
            fields,
            fields,
            {},
            {},
            0,
            1,
        )

        self.assertFalse(ok)
        self.assertEqual(proof["reason"], "target_offset_mismatch")

    def test_target_signature_must_be_unique(self):
        fields = [field("same"), field("same")]

        ok, proof = self.prove(
            fields,
            fields,
            {},
            {},
            0,
            0,
        )

        self.assertFalse(ok)
        self.assertEqual(
            proof["reason"],
            "target_signature_not_unique",
        )

    def test_witness_stats_require_strong_well_formed_rows(self):
        rows = [
            {
                "method_id": "MEM_M1",
                "operation": "getfield",
                "count": 1,
                "contexts": [["a" * 64, 1]],
            },
            {
                "method_id": "MEM_M2",
                "operation": "putfield",
                "count": 2,
                "contexts": [["b" * 64, 2]],
            },
        ]

        self.assertEqual(
            _witness_stats("REL", rows),
            (2, 3, 2),
        )

    def test_witness_stats_refuse_count_drift(self):
        rows = [
            {
                "method_id": "MEM_M1",
                "operation": "getfield",
                "count": 2,
                "contexts": [["a" * 64, 1]],
            }
        ]

        with self.assertRaises(
            CanonicalMethodBoundaryBlockEvidenceError
        ):
            _witness_stats("REL", rows)


if __name__ == "__main__":
    unittest.main()
