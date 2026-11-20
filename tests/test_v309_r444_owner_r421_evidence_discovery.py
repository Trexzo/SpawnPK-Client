"""R444: synthetic, read-only discovery of historical owner TEMP artifacts.

All paths are under temporary test directories and no private SpawnPK,
loot-history, journal or client files are touched. No background processes.
"""
from __future__ import annotations

from hashlib import sha256
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r442 import verify_prior_r421_manifest as r442
from tools.r444 import scan_owner_r421_artifacts as r444

CLI = Path(__file__).resolve().parents[1] / "tools/r444/scan_owner_r421_artifacts.py"


class R444PrivateEvidenceDiscovery(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="R444-Synthetic-")
        self.addCleanup(self.work.cleanup)
        self.temp = Path(self.work.name)
        self.root = self.temp / r444.PARENT / r444.R421
        self.sources = self.root / "Source-Candidate-R421" / "source"
        self.classes = self.root / "R421-Compiled-Classes"
        (self.sources / r425.STORE).parent.mkdir(parents=True)
        (self.classes / r425.EXPECTED_CHANGED_EXISTING_CLASS).parent.mkdir(
            parents=True)
        self.source_store = self.sources / r425.STORE
        self.class_store = self.classes / r425.EXPECTED_CHANGED_EXISTING_CLASS
        self.source_store.write_bytes(b"R444 invented Java, not real SpawnPK")
        self.class_store.write_bytes(b"R444 invented class, not bytecode")
        (self.sources / "rs/Fabricated.java").write_bytes(b"public class Fabricated {}")
        (self.classes / "rs/Fabricated.class").write_bytes(b"fake")
        self.pins = [
            patch.object(r425, "PINNED_R421_STORE_SHA",
                         sha256(self.source_store.read_bytes()).hexdigest()),
            patch.object(r425, "PINNED_R421_STORE_CLASS",
                         sha256(self.class_store.read_bytes()).hexdigest()),
            patch.object(r425, "BASELINE_SOURCE_COUNT", 2),
            patch.object(r425, "BASELINE_CLASS_COUNT", 2),
        ]
        for item in self.pins:
            item.start()
            self.addCleanup(item.stop)

    def scan(self):
        return r444.scan_owner_temp(self.temp)

    def make_candidate(self):
        target = self.root / "R421-source-class-inventory.json"
        payload = {
            "schema": r442.SCHEMA,
            "archive_id": "R421-Synthetic-Historical-Example",
            "source_inventory": {
                r425.STORE.as_posix(): r425.PINNED_R421_STORE_SHA,
                "rs/Fabricated.java": "a"*64,
            },
            "class_inventory": {
                r425.EXPECTED_CHANGED_EXISTING_CLASS:
                    r425.PINNED_R421_STORE_CLASS,
                "rs/Fabricated.class": "b"*64,
            },
            "dependency_sha256": {
                "R239_filtered.jar": "c"*64, "R218.jar": "d"*64,
            },
        }
        target.write_text(json.dumps(payload), encoding="utf-8")
        return target

    def test_01_only_known_original_owner_temp_root_is_scanned(self):
        report = self.scan()
        self.assertTrue(report["owner_isolated_r421_root_present"])
        self.assertTrue(report["original_source_root_present"])
        self.assertTrue(report["original_class_root_present"])
        self.assertEqual(report["original_source_count_observed"], 2)
        self.assertEqual(report["original_class_count_observed"], 2)
        self.assertTrue(report["original_store_source_pin_matches"])
        self.assertTrue(report["original_store_class_pin_matches"])
        self.assertEqual(report["reference_artifact_candidates_found"], 0)
        self.assertEqual(report["historical_candidate_roots_scanned"], 1)

    def test_02_missing_root_reports_missing_not_false_verification(self):
        empty = self.temp / "empty"
        empty.mkdir()
        report = r444.scan_owner_temp(empty)
        self.assertFalse(report["owner_isolated_r421_root_present"])
        self.assertIsNone(report["original_store_source_pin_matches"])
        self.assertIsNone(report["original_source_count_observed"])
        self.assertEqual(report["historical_candidate_roots_scanned"], 0)
        self.assertFalse(report["source_class_inventory_independently_approved"])

    def test_03_old_store_pin_mismatch_is_not_promoted(self):
        self.source_store.write_bytes(b"changed invented owner source")
        self.assertFalse(self.scan()["original_store_source_pin_matches"])
        self.assertFalse(self.scan()["source_class_inventory_independently_approved"])

    def test_04_candidate_shape_is_diagnostic_only(self):
        target = self.make_candidate()
        before = target.read_bytes()
        report = self.scan()
        self.assertEqual(report["possible_r442_manifest_shapes_found"], 1)
        self.assertEqual(report["reference_artifact_candidates_found"], 1)
        self.assertFalse(report["possible_reference_sha_independently_approved"])
        self.assertFalse(report["source_class_inventory_independently_approved"])
        self.assertFalse(report["release_authorized"])
        self.assertFalse(report["merge_authorized"])
        self.assertEqual(target.read_bytes(), before)

    def test_05_invalid_manifest_schema_does_not_count_as_possible_r421(self):
        target = self.make_candidate()
        data = json.loads(target.read_text(encoding="utf-8"))
        data["schema"] = "R315-only"
        target.write_text(json.dumps(data), encoding="utf-8")
        report = self.scan()
        self.assertEqual(report["possible_r442_manifest_shapes_found"], 0)
        self.assertEqual(report["reference_artifact_candidates_found"], 1)

    def test_06_missing_compiled_store_pin_refuses_candidate_shape(self):
        target = self.make_candidate()
        data = json.loads(target.read_text(encoding="utf-8"))
        data["class_inventory"][r425.EXPECTED_CHANGED_EXISTING_CLASS] = "0"*64
        target.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(self.scan()["possible_r442_manifest_shapes_found"], 0)

    def test_07_receipts_detected_without_reading_or_believing_them(self):
        candidate = self.temp / "R424-Private-Candidate-R425-synthetic"
        candidate.mkdir()
        for name in r444.RECEIPT_NAMES:
            (candidate / name).write_bytes(b'{"forged":true}')
        report = self.scan()
        self.assertEqual(report["r425_receipts_found"], 1)
        self.assertEqual(report["r432_receipts_found"], 1)
        self.assertEqual(report["historical_candidate_roots_scanned"], 2)
        self.assertFalse(report["owner_private_compile_executed"])
        self.assertFalse(report["release_authorized"])

    def test_08_candidate_names_outside_scoped_roots_are_not_scanned(self):
        outside = self.temp / "unrelated-user-live-session"
        outside.mkdir()
        (outside / "R421-private-inventory.json").write_text(
            "should not be looked at", encoding="utf-8")
        report = self.scan()
        self.assertEqual(report["reference_artifact_candidates_found"], 0)

    def test_09_source_class_tree_symlink_is_rejected(self):
        unrelated = self.temp / "external"
        unrelated.mkdir()
        link = self.sources / "rs" / "escape"
        try:
            link.symlink_to(unrelated, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Unprivileged symlink creation unavailable")
        with self.assertRaisesRegex(
                r444.Refused, "R444_SOURCE_CLASS_TREE_LINK_OR_NONDIR_REFUSED"):
            self.scan()

    def test_10_historical_candidate_link_is_not_traversed(self):
        outside = self.temp / "external"
        outside.mkdir()
        link = self.root / "historic"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Unprivileged symlink creation unavailable")
        with self.assertRaisesRegex(
                r444.Refused, "R444_HISTORICAL_CANDIDATE_NONREGULAR_REFUSED"):
            self.scan()

    def test_11_too_many_candidates_fail_closed(self):
        for i in range(r444.MAX_CANDIDATE_DIRS + 1):
            (self.temp / f"R424-Private-Candidate-R425-{i}").mkdir()
        with self.assertRaisesRegex(
                r444.Refused, "R444_TOO_MANY_HISTORICAL_CANDIDATES"):
            self.scan()

    def test_12_candidate_json_size_limit_avoids_unbounded_read(self):
        path = self.root / "R421-manifest.json"
        path.write_bytes(b"x" * (r444.MAX_JSON_BYTES + 1))
        report = self.scan()
        self.assertEqual(report["reference_artifact_candidates_found"], 1)
        self.assertEqual(report["possible_r442_manifest_shapes_found"], 0)

    def test_13_report_never_exposes_private_paths_or_raw_sha(self):
        self.make_candidate()
        report = self.scan()
        text = json.dumps(report, sort_keys=True)
        self.assertNotIn(str(self.temp), text)
        self.assertNotIn(r425.STORE.as_posix(), text)
        self.assertNotIn(r425.PINNED_R421_STORE_SHA, text)
        self.assertNotIn(r425.PINNED_R421_STORE_CLASS, text)
        for key in ("release_authorized", "merge_authorized",
                    "client_started", "history_accessed",
                    "candidate_created", "owner_private_compile_executed"):
            self.assertIs(report[key], False)

    def test_14_real_python_cli_without_owner_workspace(self):
        isolated = self.temp / "cli"
        isolated.mkdir()
        env = dict(os.environ)
        for name in ("TMPDIR", "TEMP", "TMP"):
            env[name] = str(isolated)
        proc = subprocess.run([
            sys.executable, "-B", str(CLI), "--owner-read-only-evidence-audit"
        ], capture_output=True, text=True, timeout=15, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        data = json.loads(proc.stdout)
        self.assertFalse(data["owner_isolated_r421_root_present"])
        self.assertFalse(data["source_class_inventory_independently_approved"])
        self.assertFalse(data["release_authorized"])
        self.assertNotIn(str(isolated), proc.stdout)

    def test_15_required_explicit_audit_flag(self):
        env = dict(os.environ)
        proc = subprocess.run([
            sys.executable, "-B", str(CLI)
        ], capture_output=True, text=True, timeout=15, env=env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("R444_OWNER_TEMP_EVIDENCE_SCAN_COMPLETE", proc.stdout)

    def test_16_no_remote_execution_or_filesystem_mutation_in_scanner(self):
        source = inspect.getsource(r444)
        for forbidden in ("subprocess.", "Popen(", "write_text(", "write_bytes(",
                          ".unlink(", ".mkdir(", ".rmdir(", "os.remove(",
                          "shutil.rmtree(", "--approve", "--install"):
            self.assertNotIn(forbidden, source)
        self.assertIn('"source_class_inventory_independently_approved": False',
                      source)
        self.assertIn('"release_authorized": False', source)


if __name__ == "__main__":
    unittest.main()
