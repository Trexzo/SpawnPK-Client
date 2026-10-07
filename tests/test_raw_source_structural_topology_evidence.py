from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.raw_source_structural_topology_evidence import (
    build_raw_source_structural_topology_evidence,
)


class RawSourceStructuralTopologyEvidenceTests(unittest.TestCase):
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
            "report_id": "RAWSOURCEDECL_BASE",
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
                    "reason": "raw_source_topology_mismatch",
                    "old_global_source_class_topology": [
                        {
                            "source_class": "RAW:thirdparty/OldCaller",
                            "operation": "getstatic",
                            "count": 2,
                        }
                    ],
                    "new_global_source_class_topology": [
                        {
                            "source_class": "RAW:thirdparty/NewCaller",
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

    def _indexes(
        self,
        *,
        old_struct="s" * 64,
        new_struct="s" * 64,
        old_sha="a" * 64,
        new_sha="b" * 64,
        duplicate_old_struct=False,
    ):
        old_classes = {
            "thirdparty/OldCaller.class": {
                "internal_name": "thirdparty/OldCaller",
                "structural_sha256": old_struct,
            },
        }
        old_entries = {
            "thirdparty/OldCaller.class": {
                "sha256": old_sha,
            },
        }
        if duplicate_old_struct:
            old_classes["thirdparty/Other.class"] = {
                "internal_name": "thirdparty/Other",
                "structural_sha256": old_struct,
            }
            old_entries["thirdparty/Other.class"] = {
                "sha256": "c" * 64,
            }

        return (
            {
                "classes": old_classes,
                "entries": old_entries,
            },
            {
                "classes": {
                    "thirdparty/NewCaller.class": {
                        "internal_name": "thirdparty/NewCaller",
                        "structural_sha256": new_struct,
                    },
                },
                "entries": {
                    "thirdparty/NewCaller.class": {
                        "sha256": new_sha,
                    },
                },
            },
        )

    def _run(
        self,
        *,
        base=None,
        original=None,
        old_fields=None,
        new_fields=None,
        old_paired=None,
        new_paired=None,
        old_index=None,
        new_index=None,
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
        if old_index is None or new_index is None:
            old_index, new_index = self._indexes()

        def field_table(_jar, *, owner):
            if owner == "rs/A":
                return copy.deepcopy(old_fields)
            if owner == "rs/B":
                return copy.deepcopy(new_fields)
            raise AssertionError(owner)

        with (
            patch(
                "spk_recovery.raw_source_structural_topology_evidence."
                "build_raw_source_exact_declaration_evidence",
                return_value=copy.deepcopy(base),
            ),
            patch(
                "spk_recovery.raw_source_structural_topology_evidence."
                "_unresolved_reviews",
                return_value={"MEMREL_TEST": copy.deepcopy(original)},
            ),
            patch(
                "spk_recovery.raw_source_structural_topology_evidence."
                "_paired_field_maps",
                return_value=(old_paired, new_paired),
            ),
            patch(
                "spk_recovery.raw_source_structural_topology_evidence."
                "_aliases",
                side_effect=[{}, {}],
            ),
            patch(
                "spk_recovery.raw_source_structural_topology_evidence."
                "_jar_field_table",
                side_effect=field_table,
            ),
        ):
            return build_raw_source_structural_topology_evidence(
                {},
                {},
                old_index,
                new_index,
                Path("old.jar"),
                Path("new.jar"),
                {"report_id": "GLOBALFIELDUSE_TEST"},
            )

    def test_unique_structural_identity_normalizes_topology(self):
        report = self._run()

        self.assertFalse(report["canonical"])
        self.assertEqual(
            report["summary"]["input_raw_source_topology_mismatches"],
            1,
        )
        self.assertEqual(report["summary"]["candidate_fields"], 1)
        candidate = report["candidates"][0]
        self.assertEqual(
            candidate["strategy"],
            "globally_unique_raw_source_identity_and_"
            "canonical_anchor_declaration_interval_exact",
        )
        self.assertEqual(candidate["confidence"], "INFERRED_HIGH")
        self.assertEqual(candidate["score"], 0.999)
        self.assertTrue(candidate["supports_existing_review"])
        self.assertEqual(
            candidate["raw_source_identity_proofs"][0]["strategy"],
            "structural_sha256_unique_global",
        )

    def test_unique_exact_sha_identity_is_preferred(self):
        old_index, new_index = self._indexes(
            old_sha="a" * 64,
            new_sha="a" * 64,
        )

        report = self._run(
            old_index=old_index,
            new_index=new_index,
        )

        self.assertEqual(report["summary"]["candidate_fields"], 1)
        self.assertEqual(
            report["candidates"][0][
                "raw_source_identity_proofs"
            ][0]["strategy"],
            "exact_sha256_unique_global",
        )

    def test_nonunique_structural_identity_is_rejected(self):
        old_index, new_index = self._indexes(
            duplicate_old_struct=True,
        )

        report = self._run(
            old_index=old_index,
            new_index=new_index,
        )

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["raw_source_identity_unproven"],
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

    def test_canonical_sources_are_preserved_in_normalization(self):
        base = self._base()
        base["rejected"][0][
            "old_global_source_class_topology"
        ].append(
            {
                "source_class": "CLIENT_CLASS_CALLER",
                "operation": "putstatic",
                "count": 1,
            }
        )
        base["rejected"][0][
            "new_global_source_class_topology"
        ].append(
            {
                "source_class": "CLIENT_CLASS_CALLER",
                "operation": "putstatic",
                "count": 1,
            }
        )

        report = self._run(base=base)

        self.assertEqual(report["summary"]["candidate_fields"], 1)
        topology = report["candidates"][0][
            "normalized_global_source_class_topology"
        ]
        self.assertTrue(
            any(
                row["source_identity"]
                == "CANON:CLIENT_CLASS_CALLER"
                for row in topology
            )
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

    def test_only_raw_topology_mismatch_rows_enter_frontier(self):
        base = self._base()
        base["rejected"].append(
            {
                "relationship_id": "MEMREL_OTHER",
                "logical_class_id": "CLIENT_CLASS_A",
                "old_owner": "rs/A",
                "new_owner": "rs/B",
                "reason": "raw_source_class_bytes_mismatch",
            }
        )

        report = self._run(base=base)

        self.assertEqual(
            report["summary"]["input_raw_source_topology_mismatches"],
            1,
        )
        self.assertEqual(report["summary"]["candidate_fields"], 1)

    def test_inputs_are_not_mutated(self):
        base = self._base()
        original = self._original()
        old_index, new_index = self._indexes()
        before = copy.deepcopy(
            (base, original, old_index, new_index)
        )

        self._run(
            base=base,
            original=original,
            old_index=old_index,
            new_index=new_index,
        )

        self.assertEqual(
            (base, original, old_index, new_index),
            before,
        )


if __name__ == "__main__":
    unittest.main()
