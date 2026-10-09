from __future__ import annotations

from collections import Counter
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import spk_recovery.v309_cp_whole_archive_rival_research as rival


class PrivateIndexReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.old = root / "exact-v308.jar"
        self.new = root / "exact-v309.jar"
        self.paths = []
        with ZipFile(self.old, "w") as a, ZipFile(self.new, "w") as b:
            for i in range(8):
                old_path = f"rs/SyntheticOld{i}.class"
                new_path = f"rs/SyntheticNew{i}.class"
                a.writestr(old_path, bytes((i, 11)))
                b.writestr(new_path, bytes((i, 22)))
                self.paths.append((old_path, new_path))
        old_sha, new_sha = rival.sha256_file(self.old), rival.sha256_file(self.new)
        self.frontier = {
            "kind": "v309_recovery_frontier",
            "state": "ACCEPTED_INCOMPLETE",
            "report_id": "FRONTIER_EXACT",
            "frontier": {"unresolved": 143},
            "exact_clients": {"v308_sha256": old_sha, "v309_sha256": new_sha},
        }
        self.global_report = {
            "kind": "global_field_usage_identity_candidates",
            "canonical": False, "report_id": "GLOBAL_EXACT",
            "old_sha256": old_sha, "new_sha256": new_sha,
            "summary": {"descriptor_identity_guard_rejected": 26},
            "review_outcomes": [{} for _ in range(143)],
        }
        self.lineage = {
            "builds": [
                {"build_id": "v308", "sha256": old_sha},
                {"build_id": "v309", "sha256": new_sha},
            ],
            "classes": [
                {"logical_id": f"CLIENT_CLASS_{i + 1:06d}",
                 "lineage": [
                     {"build_id": "v308", "entry_path": self.paths[i][0]}
                 ]}
                for i in range(8)
            ],
        }
        self.deps = {
            "summary": {"blocking_old_class_identities": 8,
                        "blocked_fields": 26},
            "class_dependencies": [
                {"old_canonical_class_id": f"CLIENT_CLASS_{i + 1:06d}",
                 "blocked_fields": (5 if i == 0 else 3),
                 "new_raw_descriptors": ["L" + self.paths[i][1][:-6] + ";"]}
                for i in range(8)
            ],
        }
        # Seven groups x three + one x five = 26.
        self.pair = {
            "kind": "v309_cp_method_referent_pairwise_research",
            "canonical": False, "state":
                "CP_REFERENT_PAIRWISE_NO_CLASS_OR_MEMBER_IDENTITY_ACCEPTED",
            "old_sha256": old_sha, "new_sha256": new_sha,
            "frontier_id": self.frontier["report_id"],
            "global_report_id": self.global_report["report_id"],
            "summary": {
                "reviewed_descriptor_class_pairs": 8,
                "input_blocked_field_relationships": 26,
                "unique_cp_method_research_matches": 0,
                "class_identities_accepted": 0,
                "member_identities_accepted": 0,
                "accepted_frontier_unresolved": 143,
            },
            "rows": [
                {"old_canonical_class_id": f"CLIENT_CLASS_{i + 1:06d}",
                 "blocked_fields": (5 if i == 0 else 3),
                 "unique_cp_semantic_method_matches": 0,
                 "accepted_class_identifications": 0,
                 "accepted_member_identifications": 0}
                for i in range(8)
            ],
        }
        self.pair["report_id"] = (
            "V309CPPAIR_" + rival._digest(self.pair)[:20].upper()
        )
        self.old_index = {"old": True}
        self.new_index = {"new": True}

    def shapes(self, index, version, sha):
        self.assertEqual(sha,
                         self.frontier["exact_clients"][version + "_sha256"])
        return {
            path[0 if version == "v308" else 1]: Counter({(1, "()V", 1): 3})
            for path in self.paths
        }

    def mocked_profile(self, raw):
        self.assertEqual(len(raw), 2)
        i, ver = raw
        old = ver == 11
        self.assertIn(ver, (11, 22))
        return {
            "internal_name": self.paths[i][0 if old else 1][:-6],
            "methods": [],
            "bootstrap_methods": [],
        }

    def common_patches(self):
        from contextlib import ExitStack
        stack = ExitStack()
        stack.enter_context(patch.object(rival, "validate_lineage"))
        stack.enter_context(patch.object(
            rival, "build_descriptor_class_dependency_report",
            return_value=self.deps))
        stack.enter_context(patch.object(rival, "_indexed_shapes",
                                         side_effect=self.shapes))
        stack.enter_context(patch.object(
            rival, "profile_class_field_accesses",
            side_effect=self.mocked_profile))
        return stack

    def test_reused_and_standalone_evidence_produce_identical_report_id(self):
        with self.common_patches():
            with patch.object(rival, "index_jar",
                              side_effect=[self.old_index, self.new_index]) as index:
                with patch.object(rival, "build_v309_cp_method_research",
                                  return_value=self.pair) as build:
                    standalone = rival.build_v309_cp_rival_witness(
                        self.frontier, self.global_report, self.lineage,
                        self.old, self.new)
                    self.assertEqual(index.call_count, 2)
                    self.assertEqual(build.call_count, 1)
            with patch.object(rival, "index_jar",
                              side_effect=AssertionError("unwanted duplicate index")):
                with patch.object(rival, "build_v309_cp_method_research",
                                  side_effect=AssertionError("unwanted second CP pair")):
                    cached = rival.build_v309_cp_rival_witness(
                        self.frontier, self.global_report, self.lineage,
                        self.old, self.new,
                        precomputed_old_index=self.old_index,
                        precomputed_new_index=self.new_index,
                        precomputed_pairwise=self.pair)
        self.assertEqual(standalone, cached)
        self.assertEqual(standalone["report_id"], cached["report_id"])
        self.assertEqual(standalone["summary"]["examined_descriptor_classes"], 8)
        self.assertEqual(standalone["summary"]["blocked_field_relationships_preserved"], 26)
        self.assertEqual(standalone["summary"]["class_identities_accepted"], 0)
        self.assertTrue(all(
            r["state"] == "PROPOSED_PAIR_INSUFFICIENT_WITNESSES"
            for r in cached["rows"]
        ))

    def test_only_one_reused_index_is_fatal(self):
        with self.assertRaisesRegex(rival.V309CpRivalWitnessError, "both original"):
            rival.build_v309_cp_rival_witness(
                self.frontier, self.global_report, self.lineage,
                self.old, self.new, precomputed_old_index={})

    def test_reused_pair_full_body_id_mismatch_refused(self):
        tampered = copy.deepcopy(self.pair)
        tampered["summary"]["reviewed_descriptor_class_pairs"] = 7
        with patch.object(rival, "validate_lineage"):
            with self.assertRaisesRegex(
                rival.V309CpRivalWitnessError, "full-body provenance",
            ):
                rival.build_v309_cp_rival_witness(
                    self.frontier, self.global_report, self.lineage,
                    self.old, self.new, precomputed_pairwise=tampered)

    def test_forged_cp_parent_reassigned_class_group_is_rejected(self):
        tampered = copy.deepcopy(self.pair)
        tampered["rows"][1]["old_canonical_class_id"] = (
            tampered["rows"][0]["old_canonical_class_id"]
        )
        tampered["report_id"] = "V309CPPAIR_" + rival._digest(
            {k: v for k, v in tampered.items() if k != "report_id"}
        )[:20].upper()
        with self.common_patches():
            with self.assertRaisesRegex(
                rival.V309CpRivalWitnessError, "class/field group proof drift",
            ):
                rival.build_v309_cp_rival_witness(
                    self.frontier, self.global_report, self.lineage,
                    self.old, self.new,
                    precomputed_old_index=self.old_index,
                    precomputed_new_index=self.new_index,
                    precomputed_pairwise=tampered,
                )

    def test_forged_cp_parent_witness_total_is_rejected(self):
        tampered = copy.deepcopy(self.pair)
        tampered["rows"][0]["unique_cp_semantic_method_matches"] = 1
        tampered["report_id"] = "V309CPPAIR_" + rival._digest(
            {k: v for k, v in tampered.items() if k != "report_id"}
        )[:20].upper()
        with self.common_patches():
            with self.assertRaisesRegex(
                rival.V309CpRivalWitnessError, "count conservation drift",
            ):
                rival.build_v309_cp_rival_witness(
                    self.frontier, self.global_report, self.lineage,
                    self.old, self.new,
                    precomputed_old_index=self.old_index,
                    precomputed_new_index=self.new_index,
                    precomputed_pairwise=tampered,
                )

    def test_reused_pair_mixed_original_build_shas_refused(self):
        broken = copy.deepcopy(self.pair)
        broken["old_sha256"] = "f" * 64
        broken["report_id"] = "V309CPPAIR_" + rival._digest(
            {k: v for k, v in broken.items() if k != "report_id"}
        )[:20].upper()
        with patch.object(rival, "validate_lineage"):
            with self.assertRaisesRegex(
                rival.V309CpRivalWitnessError, "full-body provenance",
            ):
                rival.build_v309_cp_rival_witness(
                    self.frontier, self.global_report, self.lineage,
                    self.old, self.new, precomputed_pairwise=broken)

    def test_reused_incomplete_class_index_refused(self):
        with patch.object(rival, "validate_lineage"):
            with patch.object(
                rival, "index_jar",
                side_effect=AssertionError("must not generate hidden replacement"),
            ):
                with self.assertRaisesRegex(
                    rival.V309CpRivalWitnessError, "complete class index",
                ):
                    rival.build_v309_cp_rival_witness(
                        self.frontier, self.global_report, self.lineage,
                        self.old, self.new,
                        precomputed_pairwise=self.pair,
                        precomputed_old_index={
                            "sha256": self.frontier["exact_clients"]["v308_sha256"],
                            "summary": {"class_count": 1,
                                        "class_parse_error_count": 0},
                            "classes": {},
                        },
                        precomputed_new_index={})

    def test_original_private_jar_sha_changes_are_not_ignored(self):
        self.old.write_bytes(self.old.read_bytes() + b"changed")
        with patch.object(rival, "validate_lineage"):
            with self.assertRaisesRegex(
                rival.V309CpRivalWitnessError, "exact JAR/lineage SHA drift",
            ):
                rival.build_v309_cp_rival_witness(
                    self.frontier, self.global_report, self.lineage,
                    self.old, self.new, precomputed_pairwise=self.pair)


if __name__ == "__main__":
    unittest.main()
