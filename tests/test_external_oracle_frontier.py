from __future__ import annotations

import unittest

from spk_recovery.external_oracle_frontier import (
    ExternalOracleFrontierError,
    build_external_oracle_frontier,
)


SHA = "8" * 64


def _diagnostic():
    return {
        "schema_version": 1,
        "kind": "javac_diagnostic_classification_report",
        "report_id": "JAVACDIAG_" + "A" * 20,
        "frontier_id": "JAVACFRONTIER_" + "B" * 20,
        "identifiers_included": True,
        "diagnostics": [
            {
                "source_path": (
                    "C:\\work\\src\\rs\\ReadableA.java"
                ),
                "category": "cannot_find_symbol",
            },
            {
                "source_path": (
                    "C:\\work\\src\\rs\\ReadableA.java"
                ),
                "category": "incompatible_types",
            },
            {
                "source_path": (
                    "/tmp/work/src/rs/Recovered_Blocker.java"
                ),
                "category": "cannot_be_dereferenced",
            },
            {
                "source_path": (
                    "/tmp/work/src/rs/unmatched.java"
                ),
                "category": "other",
            },
        ],
    }


def _oracle():
    return {
        "schema_version": 1,
        "kind": "external_readable_v308_structural_oracle",
        "oracle_id": "EXTORACLE_" + "C" * 20,
        "corpus_id": "EXTCORPUS_" + "D" * 20,
        "research_only": True,
        "source_authority": False,
        "semantic_authority": False,
        "source_mutation_allowed": False,
        "exact_v308": {
            "sha256": SHA,
        },
        "candidates": [
            {
                "external_entry": (
                    "rs/model/ReadableA.class"
                ),
                "external_internal_name": (
                    "rs/model/ReadableA"
                ),
                "external_simple_name": "ReadableA",
                "exact_v308_entry": "rs/a.class",
                "strategy": "structural_unique",
                "evidence_tier": "strong",
                "score": 0.99,
                "confidence": "high",
            },
            {
                "external_entry": (
                    "rs/model/ReadableB.class"
                ),
                "external_internal_name": (
                    "rs/model/ReadableB"
                ),
                "external_simple_name": "ReadableB",
                "exact_v308_entry": "rs/b.class",
                "strategy": "weighted_mutual_best",
                "evidence_tier": "inferred",
                "score": 0.92,
                "confidence": "high",
            },
            {
                "external_entry": (
                    "rs/model/Nested.class"
                ),
                "external_internal_name": (
                    "rs/model/Nested"
                ),
                "external_simple_name": "Nested",
                "exact_v308_entry": "rs/c$1.class",
                "strategy": "structural_unique",
                "evidence_tier": "strong",
                "score": 0.99,
                "confidence": "high",
            },
        ],
    }


def _class_plan():
    return {
        "schema_version": 1,
        "kind": "remap_plan",
        "build_id": "v308",
        "source_sha256": SHA,
        "classes": [
            {
                "source_internal_name": "rs/a",
                "target_internal_name": "rs/ReadableA",
            },
            {
                "source_internal_name": "rs/b",
                "target_internal_name": "rs/Blocker",
            },
        ],
    }


def _collision_plan():
    return {
        "schema_version": 1,
        "kind": "class_package_namespace_collision_plan",
        "plan_id": "JNSPLAN_" + "E" * 20,
        "identifiers_included": True,
        "summary": {
            "plan_eliminates_all_collisions": True,
            "post_collision_edge_count": 0,
        },
        "remaps": [
            {
                "old_internal_name": "rs/Blocker",
                "new_internal_name": "rs/Recovered_Blocker",
            }
        ],
    }


class ExternalOracleFrontierTests(unittest.TestCase):
    def test_maps_through_semantic_and_collision_remaps(self):
        report = build_external_oracle_frontier(
            private_diagnostic=_diagnostic(),
            external_oracle=_oracle(),
            class_remap_plan=_class_plan(),
            collision_plan=_collision_plan(),
        )

        self.assertTrue(report["research_only"])
        self.assertFalse(
            report["source_mutation_allowed"]
        )
        self.assertFalse(
            report["semantic_acceptance_allowed"]
        )
        self.assertEqual(
            report["summary"]["failing_source_units"],
            3,
        )
        self.assertEqual(
            report["summary"]["matched_source_units"],
            2,
        )
        self.assertEqual(
            report["summary"]["strong_source_units"],
            1,
        )
        self.assertEqual(
            report["summary"]["inferred_source_units"],
            1,
        )
        self.assertEqual(
            report["summary"]["unmatched_source_units"],
            1,
        )
        self.assertEqual(
            report["summary"][
                "nested_oracle_candidates_skipped"
            ],
            1,
        )

        strong = report["matches"][0]
        self.assertEqual(
            strong["source_unit"],
            "rs/ReadableA",
        )
        self.assertEqual(strong["error_count"], 2)
        self.assertEqual(
            strong["categories"],
            {
                "cannot_find_symbol": 1,
                "incompatible_types": 1,
            },
        )
        inferred = report["matches"][1]
        self.assertEqual(
            inferred["source_unit"],
            "rs/Recovered_Blocker",
        )
        self.assertEqual(
            inferred["evidence_tier"],
            "inferred",
        )

    def test_rejects_public_redacted_javac_report(self):
        diagnostic = _diagnostic()
        diagnostic["identifiers_included"] = False
        with self.assertRaisesRegex(
            ExternalOracleFrontierError,
            "identifier-bearing",
        ):
            build_external_oracle_frontier(
                private_diagnostic=diagnostic,
                external_oracle=_oracle(),
                class_remap_plan=_class_plan(),
                collision_plan=_collision_plan(),
            )

    def test_rejects_authority_drift(self):
        plan = _class_plan()
        plan["source_sha256"] = "9" * 64
        with self.assertRaisesRegex(
            ExternalOracleFrontierError,
            "authority does not match",
        ):
            build_external_oracle_frontier(
                private_diagnostic=_diagnostic(),
                external_oracle=_oracle(),
                class_remap_plan=plan,
                collision_plan=_collision_plan(),
            )


if __name__ == "__main__":
    unittest.main()
