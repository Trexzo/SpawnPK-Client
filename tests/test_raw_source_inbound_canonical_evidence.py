from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.raw_source_inbound_canonical_evidence import (
    _global_inbound_identity_proofs,
    _profile_key,
    _scan_inbound_profiles,
    build_raw_source_inbound_canonical_evidence,
)


class _FakeArchive:
    def __init__(self, entries):
        self.entries = entries

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def namelist(self):
        return list(self.entries)

    def read(self, name):
        return self.entries[name]


class RawSourceInboundCanonicalEvidenceTests(unittest.TestCase):
    @staticmethod
    def _field(name, descriptor="I", access=1):
        return {
            "name": name,
            "descriptor": descriptor,
            "access": access,
            "attributes": [],
        }

    def _previous(self):
        return {
            "report_id": "RAWREFTOPO_BASE",
            "canonical": False,
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": "3" * 64,
            "global_usage_report_id": "GLOBAL_TEST",
            "candidates": [],
            "rejected": [
                {
                    "relationship_id": "MEMREL_TEST",
                    "reason": "canonical_reference_identity_unproven",
                }
            ],
        }

    def _structural(self):
        return {
            "report_id": "RAWSOURCETOPO_BASE",
            "canonical": False,
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": "3" * 64,
            "global_usage_report_id": "GLOBAL_TEST",
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
        strategy = "canonical_method_inbound_topology_unique_global"
        digest = "a" * 64
        return {
            "identity_token": f"{strategy}:{digest}",
            "strategy": strategy,
            "old_source_class": "RAW:raw/OldCaller",
            "new_source_class": "RAW:raw/NewCaller",
            "inbound_topology_digest": digest,
            "old_profile": {
                "canonical_source_classes": [["CLIENT_CLASS_X", 1]],
                "canonical_source_method_events": [
                    ["CLIENT_METHOD_1", "type:new", 1],
                    ["CLIENT_METHOD_2", "invoke:invokevirtual:(I)V", 1],
                ],
                "canonical_source_class_ids": ["CLIENT_CLASS_X"],
                "canonical_source_method_ids": [
                    "CLIENT_METHOD_1",
                    "CLIENT_METHOD_2",
                ],
                "method_event_count": 2,
            },
            "new_profile": {
                "canonical_source_classes": [["CLIENT_CLASS_X", 1]],
                "canonical_source_method_events": [
                    ["CLIENT_METHOD_1", "type:new", 1],
                    ["CLIENT_METHOD_2", "invoke:invokevirtual:(I)V", 1],
                ],
                "canonical_source_class_ids": ["CLIENT_CLASS_X"],
                "canonical_source_method_ids": [
                    "CLIENT_METHOD_1",
                    "CLIENT_METHOD_2",
                ],
                "method_event_count": 2,
            },
        }

    def _run(
        self,
        *,
        proof_maps=True,
        structural=None,
        old_fields=None,
        new_fields=None,
        old_paired=None,
        new_paired=None,
    ):
        previous = self._previous()
        structural = structural or self._structural()
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
                    "canonical_method_inbound_topology_unique_global": 1,
                    "canonical_class_method_inbound_topology_unique_global": 0,
                },
            )
        else:
            global_proofs = (
                {},
                {},
                {
                    "canonical_method_inbound_topology_unique_global": 0,
                    "canonical_class_method_inbound_topology_unique_global": 0,
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
                "spk_recovery.raw_source_inbound_canonical_evidence."
                "build_raw_source_canonical_reference_evidence",
                return_value=copy.deepcopy(previous),
            ),
            patch(
                "spk_recovery.raw_source_inbound_canonical_evidence."
                "build_raw_source_structural_topology_evidence",
                return_value=copy.deepcopy(structural),
            ),
            patch(
                "spk_recovery.raw_source_inbound_canonical_evidence._aliases",
                side_effect=[{}, {}],
            ),
            patch(
                "spk_recovery.raw_source_inbound_canonical_evidence."
                "_paired_method_maps",
                return_value=({}, {}, 0),
            ),
            patch(
                "spk_recovery.raw_source_inbound_canonical_evidence."
                "_global_inbound_identity_proofs",
                return_value=global_proofs,
            ),
            patch(
                "spk_recovery.raw_source_inbound_canonical_evidence."
                "_unresolved_reviews",
                return_value={"MEMREL_TEST": self._original()},
            ),
            patch(
                "spk_recovery.raw_source_inbound_canonical_evidence."
                "_paired_field_maps",
                return_value=(old_paired, new_paired),
            ),
            patch(
                "spk_recovery.raw_source_inbound_canonical_evidence."
                "_jar_field_table",
                side_effect=field_table,
            ),
        ):
            return build_raw_source_inbound_canonical_evidence(
                {},
                {},
                {},
                {},
                Path("old.jar"),
                Path("new.jar"),
                {"report_id": "GLOBAL_TEST"},
            )

    def test_method_inbound_key_requires_two_canonical_methods(self):
        weak = {
            "canonical_source_classes": [["C1", 1]],
            "canonical_source_method_events": [
                ["M1", "type:new", 2],
                ["M1", "invoke:invokevirtual:()V", 1],
            ],
        }
        self.assertIsNone(
            _profile_key(
                weak,
                mode="canonical_method_inbound_topology",
            )
        )

        strong = copy.deepcopy(weak)
        strong["canonical_source_method_events"].append(
            ["M2", "type:checkcast", 1]
        )
        self.assertIsNotNone(
            _profile_key(
                strong,
                mode="canonical_method_inbound_topology",
            )
        )

    def test_combined_key_requires_three_source_identities(self):
        weak = {
            "canonical_source_classes": [["C1", 1]],
            "canonical_source_method_events": [
                ["M1", "type:new", 1],
            ],
        }
        self.assertIsNone(
            _profile_key(
                weak,
                mode="canonical_class_method_inbound_topology",
            )
        )
        strong = copy.deepcopy(weak)
        strong["canonical_source_classes"].append(["C2", 1])
        self.assertIsNotNone(
            _profile_key(
                strong,
                mode="canonical_class_method_inbound_topology",
            )
        )

    def test_global_collision_refuses_inbound_identity(self):
        shared = {
            "canonical_source_classes": [["C1", 1]],
            "canonical_source_method_events": [
                ["M1", "type:new", 1],
                ["M2", "type:checkcast", 1],
            ],
        }
        with patch(
            "spk_recovery.raw_source_inbound_canonical_evidence."
            "_scan_inbound_profiles",
            side_effect=[
                {
                    "raw/A": copy.deepcopy(shared),
                    "raw/B": copy.deepcopy(shared),
                },
                {"raw/C": copy.deepcopy(shared)},
            ],
        ):
            old, new, counts = _global_inbound_identity_proofs(
                Path("old.jar"),
                Path("new.jar"),
                old_aliases={},
                new_aliases={},
                old_method_maps={},
                new_method_maps={},
            )

        self.assertEqual(old, {})
        self.assertEqual(new, {})
        self.assertEqual(sum(counts.values()), 0)

    def test_unique_method_inbound_identity_is_installed(self):
        profile = {
            "canonical_source_classes": [],
            "canonical_source_method_events": [
                ["M1", "type:new", 1],
                ["M2", "type:checkcast", 1],
            ],
        }
        with patch(
            "spk_recovery.raw_source_inbound_canonical_evidence."
            "_scan_inbound_profiles",
            side_effect=[
                {"raw/Old": copy.deepcopy(profile)},
                {"raw/New": copy.deepcopy(profile)},
            ],
        ):
            old, new, counts = _global_inbound_identity_proofs(
                Path("old.jar"),
                Path("new.jar"),
                old_aliases={},
                new_aliases={},
                old_method_maps={},
                new_method_maps={},
            )

        self.assertIn("raw/Old", old)
        self.assertIn("raw/New", new)
        self.assertEqual(
            counts["canonical_method_inbound_topology_unique_global"],
            1,
        )

    def test_scan_ignores_referenced_raw_member_names(self):
        method_profile_old = {
            "internal_name": "rs/Source",
            "methods": [
                {
                    "name": "a",
                    "descriptor": "()V",
                    "instructions": [],
                    "field_accesses": [
                        {
                            "owner": "raw/Target",
                            "name": "oldFieldName",
                            "descriptor": "Ljava/lang/String;",
                            "operation": "getfield",
                        }
                    ],
                    "method_invocations": [
                        {
                            "owner": "raw/Target",
                            "name": "oldMethodName",
                            "descriptor": "(Ljava/lang/String;)V",
                            "operation": "invokevirtual",
                        }
                    ],
                }
            ],
        }
        method_profile_new = copy.deepcopy(method_profile_old)
        method_profile_new["methods"][0]["field_accesses"][0][
            "name"
        ] = "renamedField"
        method_profile_new["methods"][0]["method_invocations"][0][
            "name"
        ] = "renamedMethod"

        cp = {
            "internal_name": "rs/Source",
            "class_references": ["raw/Target"],
            "member_references": [],
        }

        def one_scan(profile):
            with (
                patch(
                    "spk_recovery.raw_source_inbound_canonical_evidence."
                    "zipfile.ZipFile",
                    return_value=_FakeArchive(
                        {"rs/Source.class": b"x"}
                    ),
                ),
                patch(
                    "spk_recovery.raw_source_inbound_canonical_evidence."
                    "profile_class_constant_pool_references",
                    return_value=cp,
                ),
                patch(
                    "spk_recovery.raw_source_inbound_canonical_evidence."
                    "profile_class_field_accesses",
                    return_value=profile,
                ),
            ):
                return _scan_inbound_profiles(
                    Path("x.jar"),
                    class_aliases={
                        "rs/Source": "CLIENT_CLASS_SOURCE"
                    },
                    method_maps={
                        "rs/Source": {
                            ("a", "()V"): "CLIENT_METHOD_SOURCE"
                        }
                    },
                )

        self.assertEqual(
            one_scan(method_profile_old)["raw/Target"],
            one_scan(method_profile_new)["raw/Target"],
        )

    def test_scan_collapses_reference_names_in_descriptors(self):
        profile = {
            "internal_name": "rs/Source",
            "methods": [
                {
                    "name": "a",
                    "descriptor": "()V",
                    "instructions": [],
                    "field_accesses": [],
                    "method_invocations": [
                        {
                            "owner": "raw/Target",
                            "name": "x",
                            "descriptor": "(Lold/Name;)Lother/X;",
                            "operation": "invokevirtual",
                        }
                    ],
                }
            ],
        }
        cp = {
            "internal_name": "rs/Source",
            "class_references": [],
            "member_references": [],
        }
        with (
            patch(
                "spk_recovery.raw_source_inbound_canonical_evidence."
                "zipfile.ZipFile",
                return_value=_FakeArchive(
                    {"rs/Source.class": b"x"}
                ),
            ),
            patch(
                "spk_recovery.raw_source_inbound_canonical_evidence."
                "profile_class_constant_pool_references",
                return_value=cp,
            ),
            patch(
                "spk_recovery.raw_source_inbound_canonical_evidence."
                "profile_class_field_accesses",
                return_value=profile,
            ),
        ):
            result = _scan_inbound_profiles(
                Path("x.jar"),
                class_aliases={"rs/Source": "C"},
                method_maps={
                    "rs/Source": {("a", "()V"): "M"}
                },
            )

        event = result["raw/Target"][
            "canonical_source_method_events"
        ][0]
        self.assertEqual(
            event[1],
            "invoke:invokevirtual:(L;)L;",
        )

    def test_proven_inbound_identity_can_reach_candidate(self):
        report = self._run()
        self.assertEqual(report["summary"]["candidate_fields"], 1)
        self.assertEqual(
            report["summary"]["remaining_without_inbound_canonical_proof"],
            0,
        )

    def test_unproven_inbound_identity_stays_rejected(self):
        report = self._run(proof_maps=False)
        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["inbound_canonical_identity_unproven"],
            1,
        )

    def test_normalized_source_topology_still_must_match(self):
        structural = self._structural()
        structural["rejected"][0][
            "new_global_source_class_topology"
        ][0]["count"] = 3
        report = self._run(structural=structural)
        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["normalized_source_topology_mismatch"],
            1,
        )

    def test_missing_anchor_is_still_rejected(self):
        report = self._run(
            old_paired={
                ("rs/A", "left", "I"): "CLIENT_FIELD_LEFT"
            },
            new_paired={
                ("rs/B", "left", "I"): "CLIENT_FIELD_LEFT"
            },
        )
        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["missing_two_sided_canonical_anchor"],
            1,
        )

    def test_only_previous_identity_unproven_ids_enter_frontier(self):
        structural = self._structural()
        structural["rejected"].append(
            {
                "relationship_id": "MEMREL_OTHER",
                "logical_class_id": "CLIENT_CLASS_A",
                "old_owner": "rs/A",
                "new_owner": "rs/B",
                "reason": "raw_source_identity_unproven",
                "old_global_source_class_topology": [],
                "new_global_source_class_topology": [],
            }
        )
        report = self._run(structural=structural)
        self.assertEqual(
            report["summary"][
                "input_canonical_reference_identity_unproven"
            ],
            1,
        )

    def test_inputs_are_not_mutated(self):
        structural = self._structural()
        before = copy.deepcopy(structural)
        self._run(structural=structural)
        self.assertEqual(structural, before)


if __name__ == "__main__":
    unittest.main()
