from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from spk_recovery.descriptor_class_dependencies import (
    build_descriptor_class_dependency_report,
)


GLOBAL = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "v309-field-recovery"
    / "global-field-usage.json"
)


class DescriptorClassDependenciesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = json.loads(GLOBAL.read_text(encoding="utf-8"))

    def test_exact_tracked_dependency_frontier(self) -> None:
        result = build_descriptor_class_dependency_report(self.source)
        self.assertEqual(result["state"], "RESEARCH_ONLY_NO_IDENTITIES_ACCEPTED")
        self.assertEqual(
            result["summary"],
            {
                "blocked_fields": 26,
                "blocking_old_class_identities": 8,
                "raw_descriptors_renamed": 5,
                "field_owners_renamed": 9,
            },
        )
        self.assertEqual(
            [(x["old_canonical_class_id"], x["blocked_fields"])
             for x in result["class_dependencies"]],
            [
                ("CLIENT_CLASS_000029", 14),
                ("CLIENT_CLASS_001096", 4),
                ("CLIENT_CLASS_000028", 2),
                ("CLIENT_CLASS_000966", 2),
                ("CLIENT_CLASS_000131", 1),
                ("CLIENT_CLASS_000486", 1),
                ("CLIENT_CLASS_000943", 1),
                ("CLIENT_CLASS_000965", 1),
            ],
        )
        self.assertEqual(
            sum(x["blocked_fields"] for x in result["class_dependencies"]), 26
        )
        self.assertEqual(result, build_descriptor_class_dependency_report(self.source))
        self.assertEqual(result["source_report_id"], self.source["report_id"])

    def test_rejects_unproven_new_class_claim(self) -> None:
        source = copy.deepcopy(self.source)
        source["descriptor_identity_rejections"][0]["new_descriptor_identity"] = (
            "L@CLIENT_CLASS_000028;"
        )
        with self.assertRaises(ValueError):
            build_descriptor_class_dependency_report(source)

    def test_rejects_summary_drift(self) -> None:
        source = copy.deepcopy(self.source)
        source["summary"]["descriptor_identity_guard_rejected"] = 25
        with self.assertRaises(ValueError):
            build_descriptor_class_dependency_report(source)

    def test_rejects_outcome_mismatch(self) -> None:
        source = copy.deepcopy(self.source)
        row = next(
            x for x in source["review_outcomes"]
            if x.get("outcome") == "descriptor_identity_guard_rejected"
        )
        row["new_owner"] = "incorrect/unproven"
        with self.assertRaises(ValueError):
            build_descriptor_class_dependency_report(source)

    def test_rejects_duplicate_relationship(self) -> None:
        source = copy.deepcopy(self.source)
        source["descriptor_identity_rejections"][1]["relationship_id"] = (
            source["descriptor_identity_rejections"][0]["relationship_id"]
        )
        with self.assertRaises(ValueError):
            build_descriptor_class_dependency_report(source)

    def test_rejects_wrong_report_kind(self) -> None:
        source = copy.deepcopy(self.source)
        source["kind"] = "reviewed_member_identity_acceptance_spec"
        with self.assertRaises(ValueError):
            build_descriptor_class_dependency_report(source)


if __name__ == "__main__":
    unittest.main()
