from pathlib import Path
import unittest
from unittest.mock import patch

from spk_recovery.update_member_intelligence import (
    UpdateMemberIntelligenceError,
    build_audited_canonical_member_identity_workspace,
    build_canonical_member_identity_candidates,
)


OLD_SHA = "1" * 64
NEW_SHA = "2" * 64
OLD_ENTRY_SHA = "a" * 64
NEW_ENTRY_SHA = "b" * 64
OLD_STRUCT = "c" * 64
NEW_STRUCT = "d" * 64


def _class_lineage():
    return {
        "schema_version": 1,
        "namespace": "spawnpk-client",
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": "v308",
        "builds": [
            {
                "build_id": "v308",
                "build_number": 308,
                "sha256": OLD_SHA,
                "source_name": "old.jar",
                "authority": "EXACT_CURRENT_CLIENT",
            },
            {
                "build_id": "v309",
                "build_number": 309,
                "sha256": NEW_SHA,
                "source_name": "new.jar",
                "authority": "CROSS_BUILD",
            },
        ],
        "classes": [
            {
                "logical_id": "CLIENT_CLASS_000001",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/a",
                        "entry_path": "rs/a.class",
                        "entry_sha256": OLD_ENTRY_SHA,
                        "structural_sha256": OLD_STRUCT,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    },
                    {
                        "build_id": "v309",
                        "internal_name": "rs/z",
                        "entry_path": "rs/z.class",
                        "entry_sha256": NEW_ENTRY_SHA,
                        "structural_sha256": NEW_STRUCT,
                        "relation": "STRUCTURAL",
                        "confidence": 0.995,
                        "provenance": [],
                    },
                ],
                "semantic_provenance": [],
            }
        ],
        "unresolved": [],
    }


def _index(*, old):
    if old:
        return {
            "sha256": OLD_SHA,
            "entries": {
                "rs/a.class": {
                    "sha256": OLD_ENTRY_SHA,
                    "size": 10,
                }
            },
            "classes": {
                "rs/a.class": {
                    "internal_name": "rs/a",
                    "structural_sha256": OLD_STRUCT,
                    "fields": [
                        {
                            "name": "a",
                            "descriptor": "I",
                            "access": 2,
                            "attributes": [],
                        }
                    ],
                    "methods": [
                        {
                            "name": "a",
                            "descriptor": "()V",
                            "access": 1,
                            "attributes": ["Code"],
                            "code_length": 8,
                        }
                    ],
                }
            },
        }
    return {
        "sha256": NEW_SHA,
        "entries": {
            "rs/z.class": {
                "sha256": NEW_ENTRY_SHA,
                "size": 11,
            }
        },
        "classes": {
            "rs/z.class": {
                "internal_name": "rs/z",
                "structural_sha256": NEW_STRUCT,
                "fields": [
                    {
                        "name": "b",
                        "descriptor": "I",
                        "access": 2,
                        "attributes": [],
                    }
                ],
                "methods": [
                    {
                        "name": "b",
                        "descriptor": "()V",
                        "access": 1,
                        "attributes": ["Code"],
                        "code_length": 8,
                    }
                ],
            }
        },
    }


class UpdateMemberIntelligenceTests(unittest.TestCase):
    def test_uses_canonical_class_pair_as_member_authority(self):
        out = build_canonical_member_identity_candidates(
            _class_lineage(),
            _index(old=True),
            _index(old=False),
            old_build_id="v308",
            new_build_id="v309",
        )
        self.assertFalse(out["canonical"])
        self.assertEqual(
            out["kind"],
            "member_identity_candidates",
        )
        self.assertEqual(
            out["class_authority"],
            "canonical_lineage",
        )
        self.assertEqual(
            out["summary"]["canonical_class_pairs"],
            1,
        )
        self.assertEqual(
            out["summary"]["method_matched"],
            1,
        )
        self.assertEqual(
            out["summary"]["field_matched"],
            1,
        )
        cls = out["classes"][0]
        self.assertEqual(
            cls["class_strategy"],
            "canonical_lineage",
        )
        self.assertEqual(
            cls["methods"]["relationships"][0]["strategy"],
            "structural_unique",
        )
        self.assertEqual(
            cls["fields"]["relationships"][0]["strategy"],
            "structural_unique",
        )


    @patch(
        "spk_recovery.update_member_intelligence."
        "audit_member_identity_candidate_set"
    )
    def test_audited_workspace_surfaces_field_conflicts(
        self,
        audit,
    ):
        audit.return_value = {
            "schema_version": 1,
            "kind": "field_relationship_position_audit_set",
            "canonical": False,
            "old_sha256": OLD_SHA,
            "new_sha256": NEW_SHA,
            "min_observations": 2,
            "class_audits": 1,
            "exact_position_matches": 1,
            "conflict_count": 1,
            "classes": [],
        }

        out = build_audited_canonical_member_identity_workspace(
            _class_lineage(),
            _index(old=True),
            _index(old=False),
            Path("old.jar"),
            Path("new.jar"),
            old_build_id="v308",
            new_build_id="v309",
        )

        self.assertEqual(
            out["kind"],
            "audited_member_identity_workspace",
        )
        self.assertFalse(out["canonical"])
        self.assertEqual(
            out["summary"]["gross_field_candidates"],
            1,
        )
        self.assertEqual(
            out["summary"]["field_position_conflicts"],
            1,
        )
        self.assertEqual(
            out["summary"][
                "conflict_free_field_candidates_lower_bound"
            ],
            0,
        )
        self.assertTrue(
            out["summary"][
                "field_identity_requires_reconciliation"
            ]
        )

    def test_exact_index_sha_is_bound_to_canonical_build(self):
        new_index = _index(old=False)
        new_index["sha256"] = "9" * 64
        with self.assertRaises(UpdateMemberIntelligenceError):
            build_canonical_member_identity_candidates(
                _class_lineage(),
                _index(old=True),
                new_index,
                old_build_id="v308",
                new_build_id="v309",
            )

    def test_canonical_entry_hash_is_reverified(self):
        new_index = _index(old=False)
        new_index["entries"]["rs/z.class"]["sha256"] = "e" * 64
        with self.assertRaises(UpdateMemberIntelligenceError):
            build_canonical_member_identity_candidates(
                _class_lineage(),
                _index(old=True),
                new_index,
                old_build_id="v308",
                new_build_id="v309",
            )

    def test_class_present_in_only_one_build_is_skipped(self):
        lineage = _class_lineage()
        lineage["classes"].append(
            {
                "logical_id": "CLIENT_CLASS_000002",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v309",
                        "internal_name": "rs/new",
                        "entry_path": "rs/new.class",
                        "entry_sha256": "e" * 64,
                        "structural_sha256": "f" * 64,
                        "relation": "MANUAL",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            }
        )
        out = build_canonical_member_identity_candidates(
            lineage,
            _index(old=True),
            _index(old=False),
            old_build_id="v308",
            new_build_id="v309",
        )
        self.assertEqual(
            out["summary"]["canonical_classes_skipped"],
            1,
        )
        self.assertEqual(
            out["skipped_classes"][0]["reason"],
            "canonical_class_missing_in_one_build",
        )


if __name__ == "__main__":
    unittest.main()
