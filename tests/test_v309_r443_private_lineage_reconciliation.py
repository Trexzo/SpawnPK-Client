"""R443 publicly runnable invented R315 -> R421 private lineage diagnostics.

Only fabricated manifests and sandbox directories. No original private Java,
real owner dependencies, game, history, or deletion receipts.
"""
from __future__ import annotations

from hashlib import sha256
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r442 import verify_prior_r421_manifest as r442
from tools.r443 import compare_r315_r421_references as r443

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r443/compare_r315_r421_references.py"


class R443InventedLineage(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(prefix="R443-Invented-")
        self.addCleanup(self.t.cleanup)
        self.dir = Path(self.t.name)
        self.r315_path = self.dir / "older-R315-private-reference.json"
        self.r421_path = self.dir / "later-R421-private-reference.json"
        self.r315_java = {
            "source/" + r425.STORE.as_posix(): {
                "sha256": "f"*64, "size": 700},
            "source/rs/Unrelated.java": {
                "sha256": "a"*64, "size": 21},
        }
        self.r315 = {
            "archive_sha256": "e"*64,
            "classification": "owner-private; do not publish to public repository",
            "jar_files": {
                "bin/R311_SOURCE_BUILT_CLASS_ONLY.jar": {
                    "sha256": "9"*64, "size": 999},
                "dependencies/R239_filtered.jar": {
                    "sha256": "c"*64, "size": 64},
                "dependencies/R218.jar": {
                    "sha256": "d"*64, "size": 32},
            },
            "java_count": 2,
            "java_tree_sha256": "b"*64,
            "source_files": self.r315_java,
            "target_branch": "synthetic/test",
            "target_private_repository": "synthetic/does-not-exist",
        }
        self.r421_java = {
            r425.STORE.as_posix(): r425.PINNED_R421_STORE_SHA,
            "rs/Unrelated.java": "a"*64,
        }
        self.r421 = {
            "schema": r442.SCHEMA,
            "archive_id": "R421-Synthetic-Recheck-Only",
            "source_inventory": self.r421_java,
            "class_inventory": {
                r425.EXPECTED_CHANGED_EXISTING_CLASS:
                    r425.PINNED_R421_STORE_CLASS,
                "rs/Unrelated.class": "1"*64,
            },
            "dependency_sha256": {
                "R239_filtered.jar": "c"*64,
                "R218.jar": "d"*64,
            },
        }
        self.patch1 = patch.object(r425, "BASELINE_SOURCE_COUNT", 2)
        self.patch2 = patch.object(r425, "BASELINE_CLASS_COUNT", 2)
        self.patch1.start()
        self.patch2.start()
        self.addCleanup(self.patch2.stop)
        self.addCleanup(self.patch1.stop)

    def create_r315(self, source=None) -> str:
        doc = self.r315 if source is None else source
        self.r315_path.write_text(
            json.dumps(doc, sort_keys=True) + "\n", encoding="utf-8")
        return sha256(self.r315_path.read_bytes()).hexdigest()

    def create_r421(self, source=None) -> str:
        doc = self.r421 if source is None else source
        self.r421_path.write_text(
            json.dumps(doc, sort_keys=True) + "\n", encoding="utf-8")
        return sha256(self.r421_path.read_bytes()).hexdigest()

    def compare(self):
        return r443.compare_r315_to_approved_r421(
            self.r315_path, self.create_r315(),
            self.r421_path, self.create_r421(),
        )

    def test_01_r315_only_reports_true_limitations(self):
        a = self.create_r315()
        result = r443.compare_r315_to_approved_r421(self.r315_path, a)
        self.assertEqual(result["status"],
                         "R443_R315_ONLY_R421_REFERENCE_STILL_MISSING")
        self.assertEqual(result["r315_source_count"], 2)
        self.assertFalse(result["r315_compiled_class_inventory_available"])
        self.assertFalse(result["r421_reference_present"])
        self.assertFalse(result["r315_to_r421_source_diff_computed"])
        self.assertFalse(result["ready_for_private_compile"])
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["independent_manifest_custody_proven_by_tool"])

    def test_02_two_verified_invented_snapshots_give_aggregate_source_diff(self):
        result = self.compare()
        self.assertEqual(result["status"], "R443_APPROVED_REFERENCE_SOURCE_DIFF_ONLY")
        self.assertEqual(result["source_unchanged_path_count"], 1)
        self.assertEqual(result["source_changed_path_count"], 1)
        self.assertEqual(result["source_added_path_count"], 0)
        self.assertEqual(result["source_removed_path_count"], 0)
        self.assertTrue(result["dependency_hashes_match_between_snapshots"])
        self.assertFalse(result["r315_to_r421_compiled_class_diff_computed"])
        self.assertFalse(result["ready_for_private_compile"])
        self.assertFalse(result["owner_private_r425_r432_executed"])

    def test_03_same_source_count_different_path_is_not_hidden(self):
        self.r421_java.pop("rs/Unrelated.java")
        self.r421_java["rs/Renamed.java"] = "a"*64
        result = self.compare()
        self.assertEqual(result["source_unchanged_path_count"], 0)
        self.assertEqual(result["source_changed_path_count"], 1)
        self.assertEqual(result["source_added_path_count"], 1)
        self.assertEqual(result["source_removed_path_count"], 1)

    def test_04_dependency_drift_cannot_be_silently_ignored(self):
        self.r421["dependency_sha256"]["R218.jar"] = "9"*64
        result = self.compare()
        self.assertFalse(result["dependency_hashes_match_between_snapshots"])
        self.assertFalse(result["ready_for_private_compile"])

    def test_05_r315_raw_manifest_must_match_preapproved_bytes(self):
        approved = self.create_r315()
        self.r315_java["source/rs/Unrelated.java"]["sha256"] = "0"*64
        self.create_r315()
        with self.assertRaisesRegex(
                r443.Refused, "R443_R315_REFERENCE_SHA_MISMATCH"):
            r443.compare_r315_to_approved_r421(self.r315_path, approved)

    def test_06_missing_or_invalid_r315_approved_sha_refused(self):
        self.create_r315()
        for value in (None, "", "X"*64, "a"*63):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                        r443.Refused, "R443_R315_APPROVED_SHA_REQUIRED"):
                    r443.compare_r315_to_approved_r421(self.r315_path, value)

    def test_07_r421_manifest_and_approved_sha_must_be_paired(self):
        approved = self.create_r315()
        for path, digest in ((self.r421_path, None), (None, "a"*64)):
            with self.subTest(path=path, digest=digest):
                with self.assertRaisesRegex(
                        r443.Refused, "R443_R421_MANIFEST_AND_APPROVED_SHA_BOTH_REQUIRED"):
                    r443.compare_r315_to_approved_r421(
                        self.r315_path, approved, path, digest)

    def test_08_unapproved_r421_cannot_establish_comparison(self):
        approved315 = self.create_r315()
        self.create_r421()
        with self.assertRaisesRegex(
                r443.Refused, "R443_R421_REFERENCE_NOT_ACCEPTED"):
            r443.compare_r315_to_approved_r421(
                self.r315_path, approved315, self.r421_path, "0"*64)

    def test_09_r315_requires_expected_source_count(self):
        self.r315_java.pop("source/rs/Unrelated.java")
        self.r315["java_count"] = 1
        with self.assertRaisesRegex(r443.Refused, "R443_R315_SOURCE_COUNT_DRIFT"):
            r443.compare_r315_to_approved_r421(
                self.r315_path, self.create_r315())

    def test_10_r315_does_not_fake_compiled_class_inventory(self):
        self.r315["class_files"] = {
            r425.EXPECTED_CHANGED_EXISTING_CLASS: "a"*64}
        with self.assertRaisesRegex(r443.Refused,
                                    "R443_R315_UNEXPECTED_CLASS_INVENTORY"):
            r443.compare_r315_to_approved_r421(
                self.r315_path, self.create_r315())

    def test_11_r315_path_traversal_and_case_collision_are_refused(self):
        for bad in ("source/../Secret.java", "source/rs\\Bad.java",
                    "source//Bad.java", "source/rs/./Bad.java",
                    "../source/Secret.java", "/source/Absolute.java"):
            with self.subTest(path=bad):
                self.r315["source_files"] = {
                    "source/" + r425.STORE.as_posix(): {
                        "sha256": "f"*64, "size": 700},
                    bad: {"sha256": "a"*64, "size": 21},
                }
                with self.assertRaisesRegex(r443.Refused,
                                            "R443_R315_SOURCE_"):
                    r443.compare_r315_to_approved_r421(
                        self.r315_path, self.create_r315())
        self.r315["source_files"] = {
            "source/" + r425.STORE.as_posix(): {
                "sha256": "f"*64, "size": 700},
            "source/rs/TEST.java": {"sha256": "a"*64, "size": 21},
            "source/rs/test.java": {"sha256": "b"*64, "size": 21},
        }
        with patch.object(r425, "BASELINE_SOURCE_COUNT", 3):
            self.r315["java_count"] = 3
            with self.assertRaisesRegex(r443.Refused, "R443_R315_SOURCE_CASE_COLLISION"):
                r443.compare_r315_to_approved_r421(
                    self.r315_path, self.create_r315())

    def test_12_r315_duplicate_json_key_is_refused(self):
        self.r315_path.write_text(
            '{"source_files":{},"source_files":{},"java_count":2}',
            encoding="utf-8")
        observed = sha256(self.r315_path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(r443.Refused, "R443_R315_DUPLICATE_JSON_KEY"):
            r443.compare_r315_to_approved_r421(self.r315_path, observed)

    def test_13_original_store_and_jar_presence_required(self):
        self.r315_java.pop("source/" + r425.STORE.as_posix())
        self.r315_java["source/rs/Other.java"] = {"sha256": "0"*64, "size": 1}
        with self.assertRaisesRegex(r443.Refused, "R443_R315_SOURCE_STORE_MISSING"):
            r443.compare_r315_to_approved_r421(
                self.r315_path, self.create_r315())
        self.r315["source_files"] = {
            "source/" + r425.STORE.as_posix(): {"sha256": "f"*64, "size": 700},
            "source/rs/Unrelated.java": {"sha256": "a"*64, "size": 21},
        }
        self.r315["jar_files"].pop("dependencies/R218.jar")
        with self.assertRaisesRegex(r443.Refused, "R443_R315_DEPENDENCY_REFERENCES_MISSING"):
            r443.compare_r315_to_approved_r421(
                self.r315_path, self.create_r315())

    def test_14_actual_cli_with_full_invented_1277_source_1394_class_counts(self):
        src = {
            "source/" + r425.STORE.as_posix(): {
                "sha256": "f"*64, "size": 100}
        }
        src.update({
            f"source/rs/invented/F{i:04d}.java": {
                "sha256": "a"*64, "size": 5}
            for i in range(1276)
        })
        cls = {
            r425.EXPECTED_CHANGED_EXISTING_CLASS:
                r425.PINNED_R421_STORE_CLASS
        }
        cls.update({f"rs/invented/F{i:04d}.class": "b"*64
                    for i in range(1393)})
        self.r315["java_count"] = 1277
        self.r315["source_files"] = src
        approved315 = self.create_r315()
        self.r421["source_inventory"] = {
            "rs/invented/F{:04d}.java".format(i): "a"*64
            for i in range(1276)
        }
        self.r421["source_inventory"][r425.STORE.as_posix()] = (
            r425.PINNED_R421_STORE_SHA)
        self.r421["class_inventory"] = cls
        approved421 = self.create_r421()
        original = self.r315_path.read_bytes()
        proc = subprocess.run([
            sys.executable, "-B", str(CLI),
            "--r315-manifest", str(self.r315_path),
            "--approved-r315-manifest-sha256", approved315,
            "--r421-manifest", str(self.r421_path),
            "--approved-r421-manifest-sha256", approved421,
        ], capture_output=True, text=True, timeout=25, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        report = json.loads(proc.stdout)
        self.assertEqual(report["r315_source_count"], 1277)
        self.assertEqual(report["r421_source_count"], 1277)
        self.assertEqual(report["r421_compiled_class_count"], 1394)
        self.assertEqual(report["source_changed_path_count"], 1)
        self.assertEqual(report["source_unchanged_path_count"], 1276)
        self.assertFalse(report["r315_to_r421_compiled_class_diff_computed"])
        self.assertFalse(report["ready_for_private_compile"])
        self.assertNotIn(str(self.dir), proc.stdout)
        self.assertNotIn(r425.STORE.as_posix(), proc.stdout)
        self.assertEqual(original, self.r315_path.read_bytes())

    def test_15_report_cannot_promote_r315_to_private_approval(self):
        report = self.compare()
        for flag in (
            "r315_compiled_class_inventory_available",
            "r421_original_class_history_proven_by_r315",
            "independent_manifest_custody_proven_by_tool",
            "owner_private_r425_r432_executed",
            "ready_for_private_compile", "release_authorized",
            "merge_authorized",
        ):
            with self.subTest(flag=flag):
                self.assertIs(report[flag], False)

    def test_16_public_tool_has_no_write_or_self_approval(self):
        source = inspect.getsource(r443)
        for token in ("write_text(", "write_bytes(", "unlink(",
                      "shutil.copy", "subprocess.run(", "--skip",
                      "--override-sha", "--release"):
            self.assertNotIn(token, source)
        self.assertIn("read_sha_pinned_regular_json", source)
        self.assertIn("r442.read_approved_manifest", source)
        self.assertIn('"ready_for_private_compile": False', source)


if __name__ == "__main__":
    unittest.main()
