import unittest

from spk_recovery.candidate_carryforward import (
    CandidateCarryForwardError,
    project_candidate_carryforward,
)


def _class_entry(build_id, name):
    return {
        "build_id": build_id,
        "internal_name": name,
        "entry_path": name + ".class",
        "entry_sha256": "b" * 64,
        "structural_sha256": "c" * 64,
        "relation": "BASELINE" if build_id == "v308" else "STRUCTURAL",
        "confidence": 1.0,
        "provenance": [],
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
                "sha256": "a" * 64,
                "source_name": "old.jar",
                "authority": "EXACT_HISTORICAL_CLIENT",
            },
            {
                "build_id": "v309",
                "build_number": 309,
                "sha256": "d" * 64,
                "source_name": "new.jar",
                "authority": "EXACT_CURRENT_CLIENT",
            },
        ],
        "classes": [
            {
                "logical_id": "CLIENT_CLASS_000001",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    _class_entry("v308", "rs/a"),
                    _class_entry("v309", "rs/b"),
                ],
                "semantic_provenance": [],
            },
            {
                "logical_id": "CLIENT_CLASS_000002",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    _class_entry("v308", "rs/c"),
                ],
                "semantic_provenance": [],
            },
        ],
        "unresolved": [],
    }


def _member_lineage():
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": "a" * 64,
        "members": [
            {
                "member_id": "CLIENT_METHOD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "method",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/a",
                        "name": "a",
                        "descriptor": "()V",
                        "access": 1,
                        "code_length": 5,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    },
                    {
                        "build_id": "v309",
                        "owner_internal_name": "rs/b",
                        "name": "q",
                        "descriptor": "()V",
                        "access": 1,
                        "code_length": 5,
                        "relation": "STRUCTURAL",
                        "confidence": 0.99,
                        "provenance": [],
                    },
                ],
                "semantic_provenance": [],
            }
        ],
        "unresolved": [],
    }


def _review():
    return {
        "schema_version": 1,
        "kind": "semantic_review_set",
        "canonical": False,
        "source_build": "v308",
        "source_sha256": "a" * 64,
        "proposal_count": 3,
        "review_id": "SEMREVIEW_1234567890ABCDEF1234",
        "proposals": [
            {
                "proposal_id": "SEMPROP_A",
                "target_kind": "class",
                "stable_id": "CLIENT_CLASS_000001",
                "proposed_name": "CarriedInterface",
                "confidence": 0.96,
            },
            {
                "proposal_id": "SEMPROP_B",
                "target_kind": "class",
                "stable_id": "CLIENT_CLASS_000002",
                "proposed_name": "MissingInterface",
                "confidence": 0.96,
            },
            {
                "proposal_id": "SEMPROP_C",
                "target_kind": "method",
                "stable_id": "CLIENT_METHOD_000001",
                "proposed_name": "doThing",
                "confidence": 0.95,
            },
        ],
        "unresolved": [],
    }


class CandidateCarryForwardTests(unittest.TestCase):
    def test_candidate_identity_survival_is_classified_without_mutation(self):
        out = project_candidate_carryforward(
            _class_lineage(),
            _member_lineage(),
            _review(),
            old_build_id="v308",
            new_build_id="v309",
        )
        self.assertFalse(
            out["all_reviewed_candidates_have_new_identity"]
        )
        self.assertEqual(out["summary"]["candidate_carried"], 2)
        self.assertEqual(
            out["summary"]["candidate_blocked_missing_new_identity"],
            1,
        )
        self.assertEqual(out["summary"]["classes_carried"], 1)
        self.assertEqual(out["summary"]["classes_blocked"], 1)
        self.assertEqual(out["summary"]["methods_carried"], 1)

    def test_wrong_review_sha_is_rejected(self):
        review = _review()
        review["source_sha256"] = "f" * 64
        with self.assertRaises(CandidateCarryForwardError):
            project_candidate_carryforward(
                _class_lineage(),
                _member_lineage(),
                review,
                old_build_id="v308",
                new_build_id="v309",
            )

    def test_unresolved_review_is_rejected(self):
        review = _review()
        review["unresolved"] = [{"reason": "test"}]
        with self.assertRaises(CandidateCarryForwardError):
            project_candidate_carryforward(
                _class_lineage(),
                _member_lineage(),
                review,
                old_build_id="v308",
                new_build_id="v309",
            )


if __name__ == "__main__":
    unittest.main()
