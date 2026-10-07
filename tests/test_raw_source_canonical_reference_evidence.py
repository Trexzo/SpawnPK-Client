from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.raw_source_canonical_reference_evidence import (
    _global_reference_identity_proofs,
    _reference_profile,
    build_raw_source_canonical_reference_evidence,
)


class RawSourceCanonicalReferenceEvidenceTests(unittest.TestCase):
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
            "report_id": "RAWSOURCETOPO_BASE",
            "canonical": False,
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": "3" * 64,
            "global_usage_report_id": "GLOBALFIELDUSE_TEST",
            "candidates": [],
            "rejected": [
                {
                    "relationship_id": "MEMREL_TEST",
                    "logical_class_id": "CLIENT_CLASS_A",
                    "old_owner": "rs/A",
                    "new_owner": "rs/B",
                    "reason": "raw_source_identity_unproven",
                    "old_global_source_class_topology": [
                        {
                            "source_class": "RAW:raw/OldCaller",
                            "operation": "getstatic",
                            "count": 2,
                        }
                    ],
                    "new_global_source_class_topology": [
                        {
                            "source_class": "RAW:raw/NewCaller",
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
            "old": {"name": "x", "descriptor": "I", "access": 1},
            "new": {"name": "x", "descriptor": "I", "access": 1},
        }

    def _proof(self):
        strategy = "canonical_member_reference_topology_unique_global"
        digest = "a" * 64
        return {
            "identity_token": f"{strategy}:{digest}",
            "strategy": strategy,
            "old_source_class": "RAW:raw/OldCaller",
            "new_source_class": "RAW:raw/NewCaller",
            "reference_topology_digest": digest,
            "old_profile": {
                "canonical_class_ids": ["CLIENT_CLASS_X"],
                "canonical_member_refs": [
                    ["field:CLIENT_FIELD_1", 1],
                    ["method:CLIENT_METHOD_1", 1],
                ],
            },
            "new_profile": {
                "canonical_class_ids": ["CLIENT_CLASS_X"],
                "canonical_member_refs": [
                    ["field:CLIENT_FIELD_1", 1],
                    ["method:CLIENT_METHOD_1", 1],
                ],
            },
        }

    def _run(
        self,
        *,
        base=None,
        proof_maps=True,
        old_fields=None,
        new_fields=None,
        old_paired=None,
        new_paired=None,
    ):
        base = base or self._base()
        old_fields = old_fields or [
            self._field("left"),
            self._field("x"),
            self._field("right"),
        ]
        new_fields = new_fields or copy.deepcopy(old_fields)
        old_paired = old_paired or {
            ("rs/A", "left", "I"): "CLIENT_FIELD_LEFT",
            ("rs/A", "right", "I"): "CLIENT_FIELD_RIGHT",
        }
        new_paired = new_paired or {
            ("rs/B", "left", "I"): "CLIENT_FIELD_LEFT",
            ("rs/B", "right", "I"): "CLIENT_FIELD_RIGHT",
        }

        proof = self._proof()
        if proof_maps:
            global_proofs = (
                {"raw/OldCaller": proof},
                {"raw/NewCaller": proof},
                {
                    "canonical_member_reference_topology_unique_global": 1,
                    "canonical_class_member_reference_topology_unique_global": 0,
                },
            )
        else:
            global_proofs = (
                {},
                {},
                {
                    "canonical_member_reference_topology_unique_global": 0,
                    "canonical_class_member_reference_topology_unique_global": 0,
                },
            )

        def field_table(_jar, *, owner):
            if owner == "rs/A":
                return copy.deepcopy(old_fields)
            if owner == "rs/B":
                return copy.deepcopy(new_fields)
            raise AssertionError(owner)

        with (
            patch(
                "spk_recovery.raw_source_canonical_reference_evidence."
                "build_raw_source_structural_topology_evidence",
                return_value=copy.deepcopy(base),
            ),
            patch(
                "spk_recovery.raw_source_canonical_reference_evidence."
                "_paired_class_aliases",
                return_value=({}, {}),
            ),
            patch(
                "spk_recovery.raw_source_canonical_reference_evidence."
                "_paired_member_maps",
                return_value=({}, {}),
            ),
            patch(
                "spk_recovery.raw_source_canonical_reference_evidence."
                "_global_reference_identity_proofs",
                return_value=global_proofs,
            ),
            patch(
                "spk_recovery.raw_source_canonical_reference_evidence."
                "_unresolved_reviews",
                return_value={"MEMREL_TEST": self._original()},
            ),
            patch(
                "spk_recovery.raw_source_canonical_reference_evidence."
                "_paired_field_maps",
                return_value=(old_paired, new_paired),
            ),
            patch(
                "spk_recovery.raw_source_canonical_reference_evidence."
                "_aliases",
                side_effect=[{}, {}],
            ),
            patch(
                "spk_recovery.raw_source_canonical_reference_evidence."
                "_jar_field_table",
                side_effect=field_table,
            ),
        ):
            return build_raw_source_canonical_reference_evidence(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                {"report_id": "GLOBALFIELDUSE_TEST"},
            )

    def test_unique_member_reference_topology_proves_raw_identity(self):
        old_profiles = {
            "raw/Old": {
                "canonical_class_ids": ["C1"],
                "canonical_member_refs": [["field:F1", 1], ["method:M1", 1]],
            }
        }
        new_profiles = {
            "raw/New": {
                "canonical_class_ids": ["C2"],
                "canonical_member_refs": [["field:F1", 1], ["method:M1", 1]],
            }
        }
        with patch(
            "spk_recovery.raw_source_canonical_reference_evidence._scan_profiles",
            side_effect=[old_profiles, new_profiles],
        ):
            old, new, counts = _global_reference_identity_proofs(
                Path("old.jar"),
                Path("new.jar"),
                old_class_aliases={},
                new_class_aliases={},
                old_member_map={},
                new_member_map={},
            )

        self.assertIn("raw/Old", old)
        self.assertIn("raw/New", new)
        self.assertEqual(
            counts["canonical_member_reference_topology_unique_global"],
            1,
        )

    def test_collision_refuses_member_reference_identity(self):
        shared = {
            "canonical_class_ids": ["C1"],
            "canonical_member_refs": [["field:F1", 1], ["method:M1", 1]],
        }
        old_profiles = {
            "raw/Old1": copy.deepcopy(shared),
            "raw/Old2": copy.deepcopy(shared),
        }
        new_profiles = {"raw/New": copy.deepcopy(shared)}
        with patch(
            "spk_recovery.raw_source_canonical_reference_evidence._scan_profiles",
            side_effect=[old_profiles, new_profiles],
        ):
            old, new, counts = _global_reference_identity_proofs(
                Path("old.jar"),
                Path("new.jar"),
                old_class_aliases={},
                new_class_aliases={},
                old_member_map={},
                new_member_map={},
            )

        self.assertEqual(old, {})
        self.assertEqual(new, {})
        self.assertEqual(sum(counts.values()), 0)

    def test_combined_reference_topology_can_disambiguate(self):
        old_profiles = {
            "raw/Old1": {
                "canonical_class_ids": ["C1", "C2"],
                "canonical_member_refs": [["field:F1", 1]],
            },
            "raw/Old2": {
                "canonical_class_ids": ["C3", "C4"],
                "canonical_member_refs": [["field:F1", 1]],
            },
        }
        new_profiles = {
            "raw/New1": {
                "canonical_class_ids": ["C1", "C2"],
                "canonical_member_refs": [["field:F1", 1]],
            },
            "raw/New2": {
                "canonical_class_ids": ["C3", "C4"],
                "canonical_member_refs": [["field:F1", 1]],
            },
        }
        with patch(
            "spk_recovery.raw_source_canonical_reference_evidence._scan_profiles",
            side_effect=[old_profiles, new_profiles],
        ):
            old, new, counts = _global_reference_identity_proofs(
                Path("old.jar"),
                Path("new.jar"),
                old_class_aliases={},
                new_class_aliases={},
                old_member_map={},
                new_member_map={},
            )

        self.assertEqual(len(old), 2)
        self.assertEqual(len(new), 2)
        self.assertEqual(
            counts[
                "canonical_class_member_reference_topology_unique_global"
            ],
            2,
        )

    def test_interface_method_ref_maps_to_canonical_method(self):
        with patch(
            "spk_recovery.raw_source_canonical_reference_evidence."
            "profile_class_constant_pool_references",
            return_value={
                "internal_name": "raw/Caller",
                "class_references": ["rs/X"],
                "member_references": [
                    {
                        "kind": "interface_method",
                        "owner": "rs/X",
                        "name": "a",
                        "descriptor": "()V",
                    }
                ],
            },
        ):
            profile = _reference_profile(
                b"x",
                class_aliases={"rs/X": "CLIENT_CLASS_X"},
                member_map={
                    ("method", "rs/X", "a", "()V"): "CLIENT_METHOD_X"
                },
            )

        self.assertEqual(
            profile["canonical_member_refs"],
            [["interface_method:CLIENT_METHOD_X", 1]],
        )

    def test_proven_raw_identity_and_declaration_become_candidate(self):
        report = self._run()

        self.assertEqual(report["summary"]["candidate_fields"], 1)
        self.assertEqual(
            report["summary"]["remaining_without_canonical_reference_proof"],
            0,
        )
        self.assertEqual(
            report["candidates"][0]["strategy"],
            "globally_unique_canonical_reference_identity_and_"
            "canonical_anchor_declaration_interval_exact",
        )

    def test_unproven_reference_identity_remains_rejected(self):
        report = self._run(proof_maps=False)

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["canonical_reference_identity_unproven"],
            1,
        )

    def test_normalized_topology_must_match(self):
        base = self._base()
        base["rejected"][0][
            "new_global_source_class_topology"
        ][0]["count"] = 3

        report = self._run(base=base)

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["normalized_source_topology_mismatch"],
            1,
        )

    def test_missing_two_sided_anchor_is_rejected(self):
        report = self._run(
            old_paired={("rs/A", "left", "I"): "CLIENT_FIELD_LEFT"},
            new_paired={("rs/B", "left", "I"): "CLIENT_FIELD_LEFT"},
        )

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["missing_two_sided_canonical_anchor"],
            1,
        )

    def test_declaration_shape_must_match(self):
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

    def test_only_identity_unproven_rows_enter_frontier(self):
        base = self._base()
        base["rejected"].append(
            {
                "relationship_id": "MEMREL_OTHER",
                "reason": "normalized_source_topology_mismatch",
            }
        )
        report = self._run(base=base)
        self.assertEqual(
            report["summary"]["input_raw_source_identity_unproven"],
            1,
        )

    def test_inputs_are_not_mutated(self):
        base = self._base()
        before = copy.deepcopy(base)
        self._run(base=base)
        self.assertEqual(base, before)


if __name__ == "__main__":
    unittest.main()
