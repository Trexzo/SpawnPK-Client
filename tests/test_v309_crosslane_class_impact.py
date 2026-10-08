from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from spk_recovery.v309_crosslane_class_impact import (
    V309CrossLaneImpactError,
    build_v309_crosslane_class_impact,
)


REPORT_PATH = (
    Path(__file__).resolve().parents[1]
    / "research" / "v309-field-recovery" / "global-field-usage.json"
)


class V309CrossLaneClassImpactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.global_report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    def test_tracked_143_field_crosslane_priorities_are_deterministic(self):
        result = build_v309_crosslane_class_impact(self.global_report)
        self.assertEqual(result, build_v309_crosslane_class_impact(self.global_report))
        self.assertFalse(result["canonical"])
        self.assertEqual(
            result["state"], "HYPOTHETICAL_NORMALIZATION_NOT_CLASS_IDENTITY_PROOF"
        )
        self.assertEqual(result["summary"]["accepted_unresolved_fields"], 143)
        self.assertEqual(result["summary"]["descriptor_blocked_fields"], 26)
        self.assertEqual(result["summary"]["descriptor_dependent_class_hypotheses"], 8)
        self.assertEqual(result["summary"]["topology_guard_blocked_fields"], 48)
        self.assertEqual(
            result["summary"]["topology_rows_equal_only_after_all_eight_hypotheses"], 34,
        )
        self.assertEqual(
            result["summary"]["topology_rows_still_not_equal_under_all_hypotheses"], 14,
        )
        self.assertTrue(result["summary"]["no_class_or_member_identities_accepted"])

    def test_client_priority_has_14_descriptor_and_31_topology_but_no_identity(self):
        report = build_v309_crosslane_class_impact(self.global_report)
        top = report["class_hypotheses"][0]
        self.assertEqual(top["old_canonical_class_id"], "CLIENT_CLASS_000029")
        self.assertEqual(top["hypothetical_new_source_class"], "RAW:rs/Client")
        self.assertEqual(top["descriptor_blocked_fields"], 14)
        self.assertEqual(top["topology_rows_with_both_labels"], 39)
        self.assertEqual(top["topology_rows_equal_after_this_alias_only"], 31)
        self.assertEqual(top["combined_research_priority_rows"], 45)
        self.assertEqual(len(top["affected_topology_relationship_ids"]), 31)
        self.assertEqual(
            top["state"], "UNPROVEN_DESCRIPTOR_DERIVED_ALIAS_FOR_RESEARCH_ONLY"
        )

    def test_all_8_hypotheses_retained_without_canonical_promotion(self):
        report = build_v309_crosslane_class_impact(self.global_report)
        ids = [row["old_canonical_class_id"] for row in report["class_hypotheses"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 8)
        self.assertEqual(sum(g["descriptor_blocked_fields"] for g in report["class_hypotheses"]), 26)
        self.assertNotIn("accepted_class_identities", report)

    def test_duplicate_review_outcome_refused(self):
        value = copy.deepcopy(self.global_report)
        value["review_outcomes"][1]["relationship_id"] = (
            value["review_outcomes"][0]["relationship_id"]
        )
        with self.assertRaisesRegex(V309CrossLaneImpactError, "duplicate"):
            build_v309_crosslane_class_impact(value)

    def test_wrong_global_report_kind_refused(self):
        value = copy.deepcopy(self.global_report)
        value["kind"] = "accepted_canonical_mappings"
        with self.assertRaises(V309CrossLaneImpactError):
            build_v309_crosslane_class_impact(value)

    def test_descriptor_identity_assertion_refused(self):
        value = copy.deepcopy(self.global_report)
        value["descriptor_identity_rejections"][0]["new_descriptor_identity"] = (
            "L@CLIENT_CLASS_000028;"
        )
        with self.assertRaises(ValueError):
            build_v309_crosslane_class_impact(value)

    def test_wrong_topology_summary_refused(self):
        value = copy.deepcopy(self.global_report)
        value["summary"]["global_class_topology_guard_rejected"] = 47
        with self.assertRaises(V309CrossLaneImpactError):
            build_v309_crosslane_class_impact(value)

    def test_duplicate_topology_count_refused(self):
        value = copy.deepcopy(self.global_report)
        row = next(x for x in value["review_outcomes"]
                   if x["outcome"] == "global_class_topology_guard_rejected")
        row["old_global_source_class_topology"].append(
            copy.deepcopy(row["old_global_source_class_topology"][0])
        )
        with self.assertRaisesRegex(V309CrossLaneImpactError, "duplicate topology"):
            build_v309_crosslane_class_impact(value)


if __name__ == "__main__":
    unittest.main()
