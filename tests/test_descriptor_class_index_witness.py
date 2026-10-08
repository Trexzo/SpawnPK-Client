from __future__ import annotations

import copy
import unittest

from spk_recovery.descriptor_class_index_witness import (
    build_descriptor_class_index_witness,
)
from spk_recovery.lineage import seed_lineage


def _fixtures():
    old = {
        "source_name": "v308.jar",
        "sha256": "a" * 64,
        "entries": {
            "rs/a.class": {"sha256": "1" * 64},
            "rs/z.class": {"sha256": "2" * 64},
        },
        "classes": {
            "rs/a.class": {
                "internal_name": "rs/a",
                "structural_sha256": "3" * 64,
            },
            "rs/z.class": {
                "internal_name": "rs/z",
                "structural_sha256": "4" * 64,
            },
        },
    }
    new = {
        "source_name": "v309.jar",
        "sha256": "b" * 64,
        "entries": {
            "rs/b.class": {"sha256": "1" * 64},
            "rs/c.class": {"sha256": "5" * 64},
        },
        "classes": {
            "rs/b.class": {
                "internal_name": "rs/b",
                "structural_sha256": "3" * 64,
            },
            "rs/c.class": {
                "internal_name": "rs/c",
                "structural_sha256": "6" * 64,
            },
        },
    }
    lineage = seed_lineage(
        old,
        build_id="v308",
        build_number=308,
        authority="EXACT_HISTORICAL_CLIENT",
    )
    lineage["builds"].append({
        "build_id": "v309",
        "build_number": 309,
        "sha256": "b" * 64,
        "source_name": "v309.jar",
        "authority": "RESEARCH",
    })
    group = {
        "old_canonical_class_id": "CLIENT_CLASS_000001",
        "state": "UNPROVEN_NEW_CLASS_IDENTITY",
        "relationship_ids": ["MEMREL_001", "MEMREL_002"],
        "blocked_fields": 2,
        "old_raw_descriptors": ["Lrs/a;"],
        "new_raw_descriptors": ["Lrs/b;"],
        "descriptor_renamed_count": 2,
        "owner_renamed_count": 1,
    }
    dep = {
        "schema_version": 1,
        "kind": "v309_descriptor_class_dependency_research_queue",
        "state": "RESEARCH_ONLY_NO_IDENTITIES_ACCEPTED",
        "old_build_id": "v308",
        "new_build_id": "v309",
        "summary": {
            "blocking_old_class_identities": 1,
            "blocked_fields": 2,
        },
        "class_dependencies": [group],
    }
    return dep, lineage, old, new


class DescriptorClassIndexWitnessTests(unittest.TestCase):
    def test_unique_exact_class_sha_produces_review_only_candidate(self):
        args = _fixtures()
        result = build_descriptor_class_index_witness(*args)
        self.assertEqual(result["summary"]["candidate_classes"], 1)
        self.assertEqual(result["summary"]["candidate_fields_blocked"], 2)
        self.assertEqual(result["summary"]["still_blocked_fields"], 0)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["strategy"], "globally_unique_exact_entry_sha256")
        self.assertEqual(candidate["proposed_new_class"], "rs/b")
        self.assertEqual(candidate["classification"], "RESEARCH_CANDIDATE_NOT_ACCEPTED")
        self.assertFalse(result["canonical"])
        self.assertEqual(build_descriptor_class_index_witness(*args), result)

    def test_unique_structural_hash_is_distinct_research_strategy(self):
        dep, lineage, old, new = _fixtures()
        new["entries"]["rs/b.class"]["sha256"] = "9" * 64
        result = build_descriptor_class_index_witness(dep, lineage, old, new)
        self.assertEqual(result["summary"]["candidate_classes"], 1)
        self.assertEqual(
            result["candidates"][0]["strategy"],
            "globally_unique_structural_sha256_research",
        )

    def test_unrelated_new_class_has_no_identity_proof(self):
        dep, lineage, old, new = _fixtures()
        new["entries"]["rs/b.class"]["sha256"] = "9" * 64
        new["classes"]["rs/b.class"]["structural_sha256"] = "8" * 64
        result = build_descriptor_class_index_witness(dep, lineage, old, new)
        self.assertEqual(result["summary"]["candidate_classes"], 0)
        self.assertEqual(
            result["rejected"][0]["reason"],
            "no_independent_global_index_identity_witness",
        )

    def test_same_raw_descriptor_never_counts_as_evidence(self):
        dep, lineage, old, new = _fixtures()
        dep["class_dependencies"][0]["new_raw_descriptors"] = ["Lrs/a;"]
        new["entries"]["rs/a.class"] = new["entries"].pop("rs/b.class")
        new["classes"]["rs/a.class"] = new["classes"].pop("rs/b.class")
        new["classes"]["rs/a.class"]["internal_name"] = "rs/a"
        new["entries"]["rs/a.class"]["sha256"] = "9" * 64
        new["classes"]["rs/a.class"]["structural_sha256"] = "8" * 64
        result = build_descriptor_class_index_witness(dep, lineage, old, new)
        self.assertEqual(result["summary"]["candidate_classes"], 0)

    def test_global_collision_defeats_byte_witness(self):
        dep, lineage, old, new = _fixtures()
        new["entries"]["rs/c.class"]["sha256"] = "1" * 64
        new["classes"]["rs/b.class"]["structural_sha256"] = "8" * 64
        result = build_descriptor_class_index_witness(dep, lineage, old, new)
        self.assertEqual(result["summary"]["candidate_classes"], 0)

    def test_witness_disagreeing_with_descriptor_is_rejected(self):
        dep, lineage, old, new = _fixtures()
        new["entries"]["rs/b.class"]["sha256"] = "9" * 64
        new["classes"]["rs/b.class"]["structural_sha256"] = "8" * 64
        new["entries"]["rs/c.class"]["sha256"] = "1" * 64
        new["classes"]["rs/c.class"]["structural_sha256"] = "3" * 64
        result = build_descriptor_class_index_witness(dep, lineage, old, new)
        self.assertEqual(
            result["rejected"][0]["reason"],
            "independent_witness_disagrees_with_field_descriptor",
        )

    def test_already_paired_canonical_class_is_not_accepted_again(self):
        dep, lineage, old, new = _fixtures()
        lineage["classes"][0]["lineage"].append({
            "build_id": "v309",
            "internal_name": "rs/b",
            "entry_path": "rs/b.class",
            "entry_sha256": "1" * 64,
            "structural_sha256": "3" * 64,
            "relation": "STRUCTURAL",
            "confidence": 0.9,
            "provenance": [{"authority": "RESEARCH", "source": "fixture"}],
        })
        result = build_descriptor_class_index_witness(dep, lineage, old, new)
        self.assertEqual(
            result["rejected"][0]["reason"],
            "class_already_paired_requires_replay",
        )

    def test_cross_build_index_binding_is_fail_closed(self):
        dep, lineage, old, new = _fixtures()
        new["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SHA-256 differs"):
            build_descriptor_class_index_witness(dep, lineage, old, new)

    def test_raw_baseline_mismatch_is_fail_closed(self):
        dep, lineage, old, new = _fixtures()
        dep["class_dependencies"][0]["old_raw_descriptors"] = ["Lrs/other;"]
        with self.assertRaisesRegex(ValueError, "binding drift"):
            build_descriptor_class_index_witness(dep, lineage, old, new)


if __name__ == "__main__":
    unittest.main()
