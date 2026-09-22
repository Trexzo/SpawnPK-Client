import unittest

from spk_recovery.semantic_opportunity import (
    build_semantic_opportunity_report,
)


SHA = "a" * 64


def _class_record(
    logical_id,
    name,
    *,
    status="UNKNOWN",
    semantic_name=None,
):
    return {
        "logical_id": logical_id,
        "semantic_name": semantic_name,
        "semantic_status": status,
        "semantic_confidence": (
            0.9 if semantic_name else 0.0
        ),
        "lineage": [
            {
                "build_id": "v308",
                "internal_name": name,
                "entry_path": name + ".class",
                "entry_sha256": "b" * 64,
                "structural_sha256": "c" * 64,
                "relation": "BASELINE",
                "confidence": 1.0,
                "provenance": [
                    {
                        "authority": "EXACT_CURRENT_CLIENT",
                        "source": "test",
                    }
                ],
            }
        ],
        "semantic_provenance": [],
    }


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
                "sha256": SHA,
                "source_name": "client.jar",
                "authority": "EXACT_CURRENT_CLIENT",
            }
        ],
        "classes": [
            _class_record(
                "CLIENT_CLASS_000001",
                "rs/a",
            ),
            _class_record(
                "CLIENT_CLASS_000002",
                "rs/b",
                status="ACCEPTED",
                semantic_name="ExistingClass",
            ),
        ],
        "unresolved": [],
    }


def _member_lineage():
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": SHA,
        "members": [
            {
                "member_id": "CLIENT_FIELD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "field",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/a",
                        "name": "x",
                        "descriptor": "I",
                        "access": 1,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            },
            {
                "member_id": "CLIENT_METHOD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "method",
                "semantic_name": "doThing",
                "semantic_status": "ACCEPTED",
                "semantic_confidence": 0.9,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/a",
                        "name": "a",
                        "descriptor": "()V",
                        "access": 1,
                        "code_length": 1,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            },
        ],
        "unresolved": [],
    }


def _proposal(
    proposal_id,
    kind,
    stable_id,
    proposed_name,
    *,
    owner_logical_id,
):
    return {
        "proposal_id": proposal_id,
        "target_kind": kind,
        "stable_id": stable_id,
        "owner_logical_id": owner_logical_id,
        "source_build": "v308",
        "source_sha256": SHA,
        "source_coordinate": {},
        "proposed_name": proposed_name,
        "confidence": 0.95,
        "evidence": [
            {"family": "exact_literal_role"},
        ],
        "note": None,
    }


def _review():
    proposals = [
        _proposal(
            "SEMPROP_1",
            "class",
            "CLIENT_CLASS_000001",
            "ReadableA",
            owner_logical_id="CLIENT_CLASS_000001",
        ),
        _proposal(
            "SEMPROP_2",
            "class",
            "CLIENT_CLASS_000002",
            "ExistingClass",
            owner_logical_id="CLIENT_CLASS_000002",
        ),
        _proposal(
            "SEMPROP_3",
            "field",
            "CLIENT_FIELD_000001",
            "count",
            owner_logical_id="CLIENT_CLASS_000001",
        ),
        _proposal(
            "SEMPROP_4",
            "method",
            "CLIENT_METHOD_000001",
            "otherThing",
            owner_logical_id="CLIENT_CLASS_000001",
        ),
    ]
    return {
        "schema_version": 1,
        "kind": "semantic_review_set",
        "canonical": False,
        "source_build": "v308",
        "source_sha256": SHA,
        "proposal_count": len(proposals),
        "review_id": "SEMREVIEW_TEST",
        "proposals": proposals,
        "unresolved": [],
    }


class SemanticOpportunityTests(unittest.TestCase):
    def test_review_overlay_never_mutates_canonical_state(self):
        classes = _class_lineage()
        members = _member_lineage()

        report = build_semantic_opportunity_report(
            classes,
            members,
            _review(),
            build_id="v308",
        )

        self.assertFalse(report["canonical"])
        self.assertEqual(
            report["summary"]["reviewed_proposals"],
            4,
        )
        self.assertEqual(
            report["summary"]["reviewed_unknown_targets"],
            2,
        )
        self.assertEqual(
            report["summary"][
                "already_accepted_same_name"
            ],
            1,
        )
        self.assertEqual(
            report["summary"]["accepted_name_conflicts"],
            1,
        )
        self.assertIsNone(
            classes["classes"][0]["semantic_name"]
        )
        self.assertIsNone(
            members["members"][0]["semantic_name"]
        )

    def test_unknown_reviewed_targets_raise_planning_coverage(self):
        report = build_semantic_opportunity_report(
            _class_lineage(),
            _member_lineage(),
            _review(),
            build_id="v308",
        )

        self.assertEqual(
            report["by_kind"]["class"][
                "reviewed_unknown_targets"
            ],
            1,
        )
        self.assertEqual(
            report["by_kind"]["field"][
                "reviewed_unknown_targets"
            ],
            1,
        )
        self.assertEqual(
            report["by_kind"]["class"][
                "reviewed_or_canonical_known_percent"
            ],
            100.0,
        )
        self.assertEqual(
            report["by_kind"]["field"][
                "reviewed_or_canonical_known_percent"
            ],
            100.0,
        )

    def test_evidence_families_are_accounted(self):
        report = build_semantic_opportunity_report(
            _class_lineage(),
            _member_lineage(),
            _review(),
            build_id="v308",
        )
        self.assertEqual(
            report["evidence_families"][
                "exact_literal_role"
            ],
            4,
        )


if __name__ == "__main__":
    unittest.main()
