from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from spk_recovery.descriptor_class_dependencies import build_descriptor_class_dependency_report
from spk_recovery.v309_changed_class_literal_witness import (
    V309LiteralClassWitnessError,
    build_v309_changed_class_literal_witness,
)


ROOT = Path(__file__).resolve().parents[1] / "research" / "v309-field-recovery"


class V309ChangedClassLiteralWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.global_report = json.loads((ROOT / "global-field-usage.json").read_text(encoding="utf-8"))
        cls.lineage = json.loads((ROOT / "class-lineage.json").read_text(encoding="utf-8"))
        dep = build_descriptor_class_dependency_report(cls.global_report)
        cls.groups = dep["class_dependencies"]
        cls.assertable = {g["old_canonical_class_id"]: g for g in cls.groups}
        old_classes, new_classes, old_entries, new_entries = {}, {}, {}, {}
        cls.old_paths = {}
        cls.new_paths = {}
        cls.anchor_groups = {}
        for i, group in enumerate(cls.groups):
            cid = group["old_canonical_class_id"]
            lineage = next(x for x in cls.lineage["classes"] if x["logical_id"] == cid)
            old = next(x for x in lineage["lineage"] if x["build_id"] == "v308")
            old_path = old["entry_path"]
            new_path = group["new_raw_descriptors"][0][1:-1] + ".class"
            # Synthetic globally unique String literals. Only one class group
            # gets four anchors; no private JAR content is used by this test.
            literals = [
                f"synthetic-only-class-{cid}-unique-literal-{n}"
                for n in range(4)
            ] if cid == "CLIENT_CLASS_000029" else []
            cls.old_paths[cid], cls.new_paths[cid] = old_path, new_path
            cls.anchor_groups[cid] = literals
            old_classes[old_path] = {
                "internal_name": old_path[:-6],
                "structural_sha256": old["structural_sha256"],
                "literal_strings": literals,
            }
            new_classes[new_path] = {
                "internal_name": new_path[:-6],
                "structural_sha256": "d" * 64,
                "literal_strings": literals,
            }
            old_entries[old_path] = {"sha256": old["entry_sha256"]}
            new_entries[new_path] = {"sha256": hashlib.sha256(
                ("synthetic-new-" + cid).encode("utf-8")
            ).hexdigest()}
        for build, classes, entries, expected in (
            ("v308", old_classes, old_entries, 10472),
            ("v309", new_classes, new_entries, 10502),
        ):
            for i in range(expected - len(classes)):
                path = f"synthetic-{build}/filler-{i:05}.class"
                classes[path] = {
                    "internal_name": path[:-6],
                    "structural_sha256": "a" * 64,
                    "literal_strings": [],
                }
                entries[path] = {"sha256": "b" * 64}
        cls.old_index = {
            "sha256": cls.global_report["old_sha256"],
            "classes": old_classes, "entries": old_entries,
            "summary": {"class_count": 10472, "class_parse_error_count": 0},
        }
        cls.new_index = {
            "sha256": cls.global_report["new_sha256"],
            "classes": new_classes, "entries": new_entries,
            "summary": {"class_count": 10502, "class_parse_error_count": 0},
        }

    def run_witness(self, old=None, new=None):
        return build_v309_changed_class_literal_witness(
            self.global_report,
            self.lineage,
            self.old_index if old is None else old,
            self.new_index if new is None else new,
        )

    def test_exact_pinned_synthetic_index_candidates_are_research_only(self):
        report = self.run_witness()
        self.assertEqual(report, self.run_witness())
        self.assertFalse(report["canonical"])
        self.assertEqual(report["summary"]["candidate_classes"], 1)
        self.assertEqual(report["summary"]["rejected_classes"], 7)
        self.assertEqual(report["summary"]["candidate_blocked_fields"], 14)
        self.assertEqual(report["summary"]["remaining_blocked_fields"], 12)
        self.assertEqual(report["summary"]["accepted_unresolved_fields"], 143)
        self.assertEqual(report["summary"]["canonical_identities_accepted"], 0)
        candidate = report["candidates"][0]
        self.assertEqual(candidate["old_canonical_class_id"], "CLIENT_CLASS_000029")
        self.assertEqual(candidate["matching_anchor_count"], 4)
        self.assertEqual(candidate["classification"], "RESEARCH_CANDIDATE_NOT_ACCEPTED")
        self.assertEqual(candidate["competing_anchor_count"], 0)
        self.assertNotIn(self.anchor_groups["CLIENT_CLASS_000029"][0], json.dumps(report))

    def test_rival_new_class_literal_veto_even_if_main_pair_has_three(self):
        index = copy.deepcopy(self.new_index)
        cid = "CLIENT_CLASS_000029"
        stolen = self.anchor_groups[cid][0]
        index["classes"][self.new_paths[cid]]["literal_strings"].remove(stolen)
        index["classes"]["synthetic-v309/filler-00000.class"]["literal_strings"] = [stolen]
        result = self.run_witness(new=index)
        rejection = next(r for r in result["rejected"] if r["old_canonical_class_id"] == cid)
        self.assertEqual(rejection["reason"], "conflicting_new_class_unique_literal_witness")
        self.assertEqual(rejection["matching_anchor_count"], 3)
        self.assertEqual(rejection["competing_anchor_count"], 1)

    def test_archive_wide_uniqueness_not_just_paired_class_equality(self):
        index = copy.deepcopy(self.old_index)
        cid = "CLIENT_CLASS_000029"
        stolen = self.anchor_groups[cid][0]
        index["classes"]["synthetic-v308/filler-00000.class"]["literal_strings"] = [stolen]
        result = self.run_witness(old=index)
        self.assertEqual(result["candidates"][0]["matching_anchor_count"], 3)

    def test_changed_jar_fingerprint_rejected(self):
        index = dict(self.new_index)
        index["sha256"] = "0" * 64
        with self.assertRaisesRegex(V309LiteralClassWitnessError, "SHA mismatch"):
            self.run_witness(new=index)

    def test_incomplete_index_fails_closed_before_report(self):
        index = copy.deepcopy(self.new_index)
        index["classes"].pop("synthetic-v309/filler-00000.class")
        with self.assertRaisesRegex(V309LiteralClassWitnessError, "complete pinned"):
            self.run_witness(new=index)

    def test_unparsed_class_fails_closed(self):
        index = dict(self.old_index)
        index["summary"] = dict(index["summary"], class_parse_error_count=1)
        with self.assertRaisesRegex(V309LiteralClassWitnessError, "parse-error-free"):
            self.run_witness(old=index)

    def test_changed_original_old_entry_hash_fails_closed(self):
        index = copy.deepcopy(self.old_index)
        cid = "CLIENT_CLASS_000029"
        index["entries"][self.old_paths[cid]]["sha256"] = "0" * 64
        with self.assertRaisesRegex(V309LiteralClassWitnessError, "old class proof"):
            self.run_witness(old=index)

    def test_no_canonical_acceptance_even_with_many_unique_anchors(self):
        report = self.run_witness()
        assert all(c["classification"] == "RESEARCH_CANDIDATE_NOT_ACCEPTED"
                   for c in report["candidates"])
        self.assertNotIn("accepted_class_ids", report)
        self.assertNotIn("authority", report)
        self.assertEqual(len(report["candidates"]) + len(report["rejected"]), 8)


if __name__ == "__main__":
    unittest.main()
