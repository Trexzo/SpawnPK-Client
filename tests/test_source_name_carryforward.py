import copy
import unittest

from spk_recovery.source_name_carryforward import (
    carry_forward_source_names,
)


OLD_SHA = "a" * 64
NEW_SHA = "b" * 64


def _class_entry(build, internal, entry_sha, structural):
    return {
        "build_id": build,
        "internal_name": internal,
        "entry_path": internal + ".class",
        "entry_sha256": entry_sha,
        "structural_sha256": structural,
        "relation": "BASELINE" if build == "v308" else "STRUCTURAL",
        "confidence": 1.0 if build == "v308" else 0.99,
        "provenance": [],
    }


def _class_lineage(cross_build=True):
    builds = [
        {
            "build_id": "v308",
            "build_number": 308,
            "sha256": OLD_SHA,
            "source_name": "old.jar",
            "authority": "EXACT_CURRENT_CLIENT",
        }
    ]
    lineage = [
        _class_entry("v308", "rs/A", "1" * 64, "2" * 64)
    ]
    if cross_build:
        builds.append(
            {
                "build_id": "v309",
                "build_number": 309,
                "sha256": NEW_SHA,
                "source_name": "new.jar",
                "authority": "EXACT_CURRENT_CLIENT",
            }
        )
        lineage.append(
            _class_entry("v309", "rs/B", "3" * 64, "4" * 64)
        )
    return {
        "schema_version": 1,
        "namespace": "spawnpk-client",
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": "v308",
        "builds": builds,
        "classes": [
            {
                "logical_id": "CLIENT_CLASS_000001",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": lineage,
                "semantic_provenance": [],
            }
        ],
        "unresolved": [],
    }


def _member_entry(build, owner, name):
    return {
        "build_id": build,
        "owner_internal_name": owner,
        "name": name,
        "descriptor": "(I)V",
        "access": 1,
        "code_length": 7,
        "relation": "BASELINE" if build == "v308" else "STRUCTURAL",
        "confidence": 1.0 if build == "v308" else 0.99,
        "provenance": [],
    }


def _member_lineage(cross_build=True):
    rows = [_member_entry("v308", "rs/A", "a")]
    if cross_build:
        rows.append(_member_entry("v309", "rs/B", "b"))
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": OLD_SHA,
        "members": [
            {
                "member_id": "CLIENT_METHOD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "method",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": rows,
                "semantic_provenance": [],
            }
        ],
        "unresolved": [],
    }


def _inventory(
    *,
    inventory_id,
    build,
    authority,
    symbol_id,
    source_method_id,
    current_name,
):
    return {
        "schema_version": 1,
        "kind": "source_symbol_inventory",
        "inventory_id": inventory_id,
        "workspace_id": "SRCWS_" + build,
        "build_id": build,
        "source_authority_sha256": authority,
        "readable_jar_sha256": "c" * 64,
        "namespace_id": "SEMNS_TEST",
        "source_tree_sha256": (
            "d" * 64 if build == "v308" else "e" * 64
        ),
        "target_package": "recovered/spawnpk/client",
        "summary": {},
        "methods": [
            {
                "source_file": "rs/A.java",
                "owner_internal_name": (
                    "rs/A" if build == "v308" else "rs/B"
                ),
                "name": ("a" if build == "v308" else "b"),
                "arity": 1,
                "start": 10,
                "end": 50,
                "source_method_id": source_method_id,
                "owner_logical_id": "CLIENT_CLASS_000001",
                "canonical_method_id": "CLIENT_METHOD_000001",
                "canonical_match_candidates": [
                    "CLIENT_METHOD_000001"
                ],
            }
        ],
        "symbols": [
            {
                "source_symbol_id": symbol_id,
                "source_method_id": source_method_id,
                "canonical_method_id": "CLIENT_METHOD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "source_file": "rs/A.java",
                "owner_internal_name": (
                    "rs/A" if build == "v308" else "rs/B"
                ),
                "method_name": (
                    "a" if build == "v308" else "b"
                ),
                "method_arity": 1,
                "kind": "parameter",
                "ordinal": 0,
                "current_name": current_name,
                "declared_type": "int",
                "start": 20,
                "end": 25,
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "semantic_provenance": [],
            }
        ],
        "orphan_variables": [],
    }


def _previous_plan(old_inventory):
    return {
        "schema_version": 1,
        "kind": "source_rename_plan",
        "plan_id": "SRCPLAN_0123456789ABCDEF0123",
        "inventory_id": old_inventory["inventory_id"],
        "review_id": "SRCREVIEW_0123456789ABCDEF0123",
        "workspace_id": old_inventory["workspace_id"],
        "build_id": old_inventory["build_id"],
        "source_tree_sha256": old_inventory[
            "source_tree_sha256"
        ],
        "accepted_proposal_count": 1,
        "renames": [
            {
                "proposal_id": "SRCPROP_0123456789ABCDEF0123",
                "source_symbol_id": old_inventory["symbols"][0][
                    "source_symbol_id"
                ],
                "source_method_id": old_inventory["symbols"][0][
                    "source_method_id"
                ],
                "canonical_method_id": "CLIENT_METHOD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "source_file": "rs/A.java",
                "owner_internal_name": "rs/A",
                "method_name": "a",
                "method_arity": 1,
                "kind": "parameter",
                "ordinal": 0,
                "declaration_start": 20,
                "declaration_end": 25,
                "current_name": "var1",
                "new_name": "itemId",
                "declared_type": "int",
                "confidence": 0.92,
                "evidence": [
                    {
                        "family": "dataflow",
                        "detail": "previously reviewed evidence",
                    }
                ],
                "acceptance_note": "reviewed",
            }
        ],
    }


def _class_delta(delta="structurally_equivalent"):
    return {
        "schema_version": 1,
        "kind": "class_delta_report",
        "old_sha256": OLD_SHA,
        "new_sha256": NEW_SHA,
        "summary": {},
        "classes": [
            {
                "old": "rs/A.class",
                "new": "rs/B.class",
                "delta": delta,
            }
        ],
        "ambiguous": [],
        "unmatched_old": [],
        "unmatched_new": [],
    }


def _member_delta(delta="member_only_obfuscation_rename"):
    return {
        "schema_version": 1,
        "kind": "member_delta_report",
        "old_sha256": OLD_SHA,
        "new_sha256": NEW_SHA,
        "summary": {},
        "members": [
            {
                "kind": "method",
                "old_owner": "rs/A.class",
                "new_owner": "rs/B.class",
                "old": {
                    "name": "a",
                    "descriptor": "(I)V",
                },
                "new": {
                    "name": "b",
                    "descriptor": "(I)V",
                },
                "delta": delta,
            }
        ],
        "new_member_candidates": [],
        "removed_member_candidates": [],
        "skipped_classes": [],
    }


class SourceNameCarryForwardTests(unittest.TestCase):
    def test_same_build_regeneration_reanchors_to_new_source_symbol(self):
        old = _inventory(
            inventory_id="SRCINV_OLD",
            build="v308",
            authority=OLD_SHA,
            symbol_id="SRC_PARAM_OLD",
            source_method_id="SRC_METHOD_OLD",
            current_name="var1",
        )
        new = _inventory(
            inventory_id="SRCINV_NEW",
            build="v308",
            authority=OLD_SHA,
            symbol_id="SRC_PARAM_NEW",
            source_method_id="SRC_METHOD_NEW",
            current_name="var9",
        )
        report, candidates, review, acceptance, plan = (
            carry_forward_source_names(
                _previous_plan(old),
                old,
                new,
                _class_lineage(cross_build=False),
                _member_lineage(cross_build=False),
            )
        )
        self.assertTrue(report["full_carryforward_ready"])
        self.assertEqual(
            report["summary"]["carried_to_new_symbol"],
            1,
        )
        self.assertEqual(
            candidates["candidates"][0]["source_symbol_id"],
            "SRC_PARAM_NEW",
        )
        self.assertEqual(
            plan["renames"][0]["new_name"],
            "itemId",
        )
        self.assertIsNotNone(acceptance)
        self.assertEqual(
            review["summary"]["reviewable_proposals"],
            1,
        )

    def test_cross_build_obfuscation_only_delta_carries(self):
        old = _inventory(
            inventory_id="SRCINV_OLD",
            build="v308",
            authority=OLD_SHA,
            symbol_id="SRC_PARAM_OLD",
            source_method_id="SRC_METHOD_OLD",
            current_name="var1",
        )
        new = _inventory(
            inventory_id="SRCINV_NEW",
            build="v309",
            authority=NEW_SHA,
            symbol_id="SRC_PARAM_NEW",
            source_method_id="SRC_METHOD_NEW",
            current_name="arg0",
        )
        report, _, _, _, plan = carry_forward_source_names(
            _previous_plan(old),
            old,
            new,
            _class_lineage(),
            _member_lineage(),
            class_delta_report=_class_delta(),
            member_delta_report=_member_delta(),
        )
        self.assertTrue(report["full_carryforward_ready"])
        self.assertEqual(
            report["carried"][0]["carry_mode"],
            "cross_build_stable_delta",
        )
        self.assertEqual(
            plan["renames"][0]["source_symbol_id"],
            "SRC_PARAM_NEW",
        )

    def test_modified_method_is_blocked_for_fresh_review(self):
        old = _inventory(
            inventory_id="SRCINV_OLD",
            build="v308",
            authority=OLD_SHA,
            symbol_id="SRC_PARAM_OLD",
            source_method_id="SRC_METHOD_OLD",
            current_name="var1",
        )
        new = _inventory(
            inventory_id="SRCINV_NEW",
            build="v309",
            authority=NEW_SHA,
            symbol_id="SRC_PARAM_NEW",
            source_method_id="SRC_METHOD_NEW",
            current_name="arg0",
        )
        report, candidates, review, acceptance, plan = (
            carry_forward_source_names(
                _previous_plan(old),
                old,
                new,
                _class_lineage(),
                _member_lineage(),
                class_delta_report=_class_delta(),
                member_delta_report=_member_delta(
                    delta="modified_member"
                ),
            )
        )
        self.assertFalse(report["full_carryforward_ready"])
        self.assertEqual(
            report["summary"]["blocked_for_review"],
            1,
        )
        self.assertEqual(
            report["blocked"][0]["reason"],
            "method_modified_or_unproven",
        )
        self.assertEqual(candidates["candidates"], [])
        self.assertEqual(review["proposals"], [])
        self.assertIsNone(acceptance)
        self.assertIsNone(plan)


if __name__ == "__main__":
    unittest.main()
