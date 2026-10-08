from __future__ import annotations

import copy
import unittest

from spk_recovery.descriptor_class_verified_replay import (
    build_descriptor_class_verified_replay,
    DescriptorClassVerifiedReplayError,
)
from spk_recovery.lineage import seed_lineage


def _inputs():
    old = {
        "sha256": "a" * 64,
        "source_name": "v308.jar",
        "entries": {"rs/a.class": {"sha256": "1" * 64}},
        "classes": {
            "rs/a.class": {
                "internal_name": "rs/a", "structural_sha256": "3" * 64,
            },
        },
    }
    new = {
        "sha256": "b" * 64,
        "source_name": "v309.jar",
        "entries": {"rs/b.class": {"sha256": "1" * 64}},
        "classes": {
            "rs/b.class": {
                "internal_name": "rs/b", "structural_sha256": "3" * 64,
            },
        },
    }
    lineage = seed_lineage(
        old, build_id="v308", build_number=308, authority="EXACT_HISTORICAL_CLIENT",
    )
    lineage["builds"].append({
        "build_id": "v309", "build_number": 309, "sha256": "b" * 64,
        "source_name": "v309.jar", "authority": "RESEARCH",
    })
    blocker = {
        "relationship_id": "MEMREL_A",
        "old_owner": "rs/x",
        "new_owner": "rs/y",
        "old_descriptor": "Lrs/a;",
        "new_descriptor": "Lrs/b;",
        "old_descriptor_identity": "L@CLIENT_CLASS_000001;",
        "new_descriptor_identity": "Lrs/?;",
        "reason": "canonical_descriptor_identity_changed",
    }
    report = {
        "schema_version": 1,
        "kind": "global_field_usage_identity_candidates",
        "canonical": False,
        "report_id": "GLOBAL_TEST",
        "old_build_id": "v308",
        "new_build_id": "v309",
        "old_sha256": "a" * 64,
        "new_sha256": "b" * 64,
        "summary": {"descriptor_identity_guard_rejected": 1},
        "descriptor_identity_rejections": [blocker],
        "review_outcomes": [{"outcome": "descriptor_identity_guard_rejected", **blocker}],
    }
    return report, lineage, old, new


class DescriptorClassVerifiedReplayTests(unittest.TestCase):
    def test_independent_global_evidence_generates_research_only_candidate(self):
        args = _inputs()
        report = build_descriptor_class_verified_replay(*args)
        self.assertEqual(report, build_descriptor_class_verified_replay(*args))
        self.assertFalse(report["canonical"])
        self.assertEqual(report["state"], "NO_CLASS_OR_MEMBER_IDENTITY_ACCEPTED")
        self.assertEqual(report["summary"]["candidate_classes"], 1)
        self.assertEqual(report["summary"]["candidate_fields_blocked"], 1)
        self.assertEqual(report["summary"]["rejected_classes"], 0)
        self.assertEqual(report["candidates"][0]["proposed_new_class"], "rs/b")
        self.assertEqual(
            report["candidates"][0]["classification"],
            "RESEARCH_CANDIDATE_NOT_ACCEPTED",
        )

    def test_global_build_sha_mismatch_rejected(self):
        args = list(_inputs())
        args[0]["new_sha256"] = "0" * 64
        with self.assertRaises(DescriptorClassVerifiedReplayError):
            build_descriptor_class_verified_replay(*args)

    def test_wrong_build_direction_rejected(self):
        args = list(_inputs())
        args[0]["old_build_id"] = "v307"
        with self.assertRaises(DescriptorClassVerifiedReplayError):
            build_descriptor_class_verified_replay(*args)

    def test_tampered_descriptor_rejection_cannot_be_replayed(self):
        args = list(_inputs())
        args[0]["descriptor_identity_rejections"][0]["new_descriptor"] = "Lrs/evil;"
        with self.assertRaises(ValueError):
            build_descriptor_class_verified_replay(*args)

    def test_same_class_name_but_different_index_proof_is_rejected(self):
        args = list(_inputs())
        args[2]["entries"]["rs/b.class"]["sha256"] = "9" * 64
        args[2]["classes"]["rs/b.class"]["structural_sha256"] = "8" * 64
        report = build_descriptor_class_verified_replay(*args)
        self.assertEqual(report["summary"]["candidate_classes"], 0)
        self.assertEqual(report["summary"]["still_blocked_fields"], 1)

    def test_bogus_global_review_outcome_cannot_supply_acceptance(self):
        args = list(_inputs())
        args[0]["review_outcomes"][0]["relationship_id"] = "FORGED"
        with self.assertRaises(ValueError):
            build_descriptor_class_verified_replay(*args)


if __name__ == "__main__":
    unittest.main()
