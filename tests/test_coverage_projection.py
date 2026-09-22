import copy
import unittest

from spk_recovery.coverage_projection import (
    CoverageProjectionError,
    project_semantic_review_coverage,
)


def _fixtures():
    classes = {
        "schema_version": 1,
        "namespace": "spawnpk-client",
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": "v308",
        "builds": [{
            "build_id": "v308",
            "build_number": 308,
            "sha256": "a" * 64,
            "source_name": "client.jar",
            "authority": "EXACT_CURRENT_CLIENT",
        }],
        "classes": [{
            "logical_id": "CLIENT_CLASS_000001",
            "semantic_name": None,
            "semantic_status": "UNKNOWN",
            "semantic_confidence": 0.0,
            "lineage": [{
                "build_id": "v308",
                "internal_name": "rs/a",
                "entry_path": "rs/a.class",
                "entry_sha256": "b" * 64,
                "structural_sha256": "c" * 64,
                "relation": "BASELINE",
                "confidence": 1.0,
                "provenance": [],
            }],
            "semantic_provenance": [],
        }],
        "unresolved": [],
    }
    members = {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": "a" * 64,
        "members": [{
            "member_id": "CLIENT_FIELD_000001",
            "owner_logical_id": "CLIENT_CLASS_000001",
            "kind": "field",
            "semantic_name": None,
            "semantic_status": "UNKNOWN",
            "semantic_confidence": 0.0,
            "lineage": [{
                "build_id": "v308",
                "owner_internal_name": "rs/a",
                "name": "x",
                "descriptor": "I",
                "access": 2,
                "relation": "BASELINE",
                "confidence": 1.0,
                "provenance": [],
            }],
            "semantic_provenance": [],
        }],
        "unresolved": [],
    }
    review = {
        "schema_version": 1,
        "kind": "semantic_review_set",
        "canonical": False,
        "source_build": "v308",
        "source_sha256": "a" * 64,
        "proposal_count": 2,
        "review_id": "SEMREVIEW_1234567890ABCDEF1234",
        "proposals": [
            {
                "proposal_id": "SEMPROP_CLASS",
                "target_kind": "class",
                "stable_id": "CLIENT_CLASS_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "source_build": "v308",
                "source_sha256": "a" * 64,
                "source_coordinate": {
                    "owner": "rs/a",
                    "name": None,
                    "descriptor": None,
                },
                "proposed_name": "ExampleInterface",
                "confidence": 0.96,
                "evidence": [{
                    "family": "exact_literal_role",
                }],
                "note": None,
            },
            {
                "proposal_id": "SEMPROP_FIELD",
                "target_kind": "field",
                "stable_id": "CLIENT_FIELD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "source_build": "v308",
                "source_sha256": "a" * 64,
                "source_coordinate": {
                    "owner": "rs/a",
                    "name": "x",
                    "descriptor": "I",
                },
                "proposed_name": "value",
                "confidence": 0.91,
                "evidence": [{
                    "family": "exact_field_flow",
                }],
                "note": None,
            },
        ],
        "unresolved": [],
    }
    return classes, members, review


class CoverageProjectionTests(unittest.TestCase):
    def test_projection_adds_candidates_without_mutating_authority(self):
        classes, members, review = _fixtures()
        classes_before = copy.deepcopy(classes)
        members_before = copy.deepcopy(members)

        out = project_semantic_review_coverage(
            classes,
            members,
            review,
            build_id="v308",
        )

        self.assertEqual(classes, classes_before)
        self.assertEqual(members, members_before)
        self.assertFalse(out["canonical"])
        self.assertEqual(out["base"]["overall"]["candidate"], 0)
        self.assertEqual(out["projected"]["overall"]["candidate"], 2)
        self.assertEqual(
            out["projected"]["summary"]["classes"]["candidate"],
            1,
        )
        self.assertEqual(
            out["projected"]["summary"]["fields"]["candidate"],
            1,
        )
        self.assertEqual(
            out["projected"]["overall"]["accepted"],
            0,
        )

    def test_projection_refuses_conflict_with_accepted_name(self):
        classes, members, review = _fixtures()
        classes["classes"][0].update({
            "semantic_name": "AlreadyAccepted",
            "semantic_status": "ACCEPTED",
            "semantic_confidence": 1.0,
            "semantic_provenance": [{"source": "review"}],
        })

        with self.assertRaises(CoverageProjectionError):
            project_semantic_review_coverage(
                classes,
                members,
                review,
                build_id="v308",
            )

    def test_projection_refuses_unresolved_review(self):
        classes, members, review = _fixtures()
        review["unresolved"] = [{"reason": "test"}]

        with self.assertRaises(CoverageProjectionError):
            project_semantic_review_coverage(
                classes,
                members,
                review,
                build_id="v308",
            )


if __name__ == "__main__":
    unittest.main()
