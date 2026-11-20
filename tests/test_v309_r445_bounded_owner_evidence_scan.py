"""R445: bounded, stable read-only owner TEMP discovery.

Only fabricated local TEMP files and invented Store bytes. Explicitly
tests enumeration, large-file, time-of-check/time-of-use, symlink and
unchanged R444 receipt semantics on Windows/Ubuntu.
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
from tools.r444 import scan_owner_r421_artifacts as r445

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r444/scan_owner_r421_artifacts.py"


class R445BoundedOwnerDiscovery(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="R445-Fabricated-")
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.r421 = self.temp / r445.PARENT / r445.R421
        self.source = self.r421 / "Source-Candidate-R421" / "source"
        self.classes = self.r421 / "R421-Compiled-Classes"
        self.store_java = self.source / r425.STORE
        self.store_class = self.classes / r425.EXPECTED_CHANGED_EXISTING_CLASS
        self.store_java.parent.mkdir(parents=True)
        self.store_class.parent.mkdir(parents=True)
        self.store_java.write_bytes(b"invented R445 Java Store")
        self.store_class.write_bytes(b"invented R445 class, not JVM bytecode")
        self.existing_patches = [
            patch.object(r425, "PINNED_R421_STORE_SHA",
                         sha256(self.store_java.read_bytes()).hexdigest()),
            patch.object(r425, "PINNED_R421_STORE_CLASS",
                         sha256(self.store_class.read_bytes()).hexdigest()),
            patch.object(r425, "BASELINE_SOURCE_COUNT", 1),
            patch.object(r425, "BASELINE_CLASS_COUNT", 1),
        ]
        for p in self.existing_patches:
            p.start()
            self.addCleanup(p.stop)

    def scan(self):
        return r445.scan_owner_temp(self.temp)

    def test_01_small_read_only_owner_temp_baseline_still_works(self):
        before_java = self.store_java.read_bytes()
        before_class = self.store_class.read_bytes()
        result = self.scan()
        self.assertTrue(result["original_store_source_pin_matches"])
        self.assertTrue(result["original_store_class_pin_matches"])
        self.assertEqual(result["original_source_count_observed"], 1)
        self.assertEqual(result["original_class_count_observed"], 1)
        self.assertFalse(result["source_class_inventory_independently_approved"])
        self.assertFalse(result["release_authorized"])
        self.assertEqual(self.store_java.read_bytes(), before_java)
        self.assertEqual(self.store_class.read_bytes(), before_class)

    def test_02_top_level_temp_enumeration_has_actual_cap(self):
        for i in range(4):
            (self.temp / f"unrelated-user-file-{i}").write_bytes(b"x")
        with patch.object(r445, "MAX_TEMP_TOP_LEVEL_ENTRIES", 3):
            with self.assertRaisesRegex(
                    r445.Refused, "R445_TEMP_TOP_LEVEL_LISTING_TOO_LARGE"):
                self.scan()

    def test_03_isolated_parent_enumeration_has_actual_cap(self):
        base = self.temp / r445.PARENT
        for i in range(3):
            (base / f"unrelated-metadata-{i}.txt").write_bytes(b"x")
        with patch.object(r445, "MAX_TEMP_TOP_LEVEL_ENTRIES", 2):
            with self.assertRaisesRegex(
                    r445.Refused, "R445_ISOLATED_ROOT_LISTING_TOO_LARGE"):
                self.scan()

    def test_04_source_directory_member_enumeration_is_bounded(self):
        for i in range(4):
            (self.source / f"Fabricated{i}.java").write_bytes(b"test")
        with patch.object(r445, "MAX_SOURCE_CLASS_TREE_ENTRIES", 3):
            with self.assertRaisesRegex(
                    r445.Refused, "R445_SOURCE_CLASS_DIRECTORY_ENTRY_LIMIT"):
                self.scan()

    def test_05_total_source_class_entries_have_independent_limit(self):
        (self.source / "a").mkdir()
        (self.source / "b").mkdir()
        (self.source / "a/one.txt").write_bytes(b"a")
        (self.source / "b/two.txt").write_bytes(b"b")
        with patch.object(r445, "MAX_SOURCE_CLASS_TREE_ENTRIES", 3):
            with self.assertRaisesRegex(
                    r445.Refused, "R445_SOURCE_CLASS_TREE_ENTRY_LIMIT"):
                self.scan()

    def test_06_total_source_class_directory_count_bounded(self):
        (self.source / "p0").mkdir()
        (self.source / "p1").mkdir()
        with patch.object(r445, "MAX_SOURCE_CLASS_DIRECTORIES", 2):
            with self.assertRaisesRegex(
                    r445.Refused, "R445_SOURCE_CLASS_DIR_BUDGET_EXCEEDED"):
                self.scan()

    def test_07_source_class_depth_budget_bounded(self):
        (self.source / "deep").mkdir()
        (self.source / "deep/more").mkdir()
        with patch.object(r445, "MAX_SOURCE_CLASS_DEPTH", 1):
            with self.assertRaisesRegex(
                    r445.Refused, "R445_SOURCE_CLASS_DEPTH_OR_ALIAS_REFUSED"):
                self.scan()

    def test_08_large_original_store_not_read_or_implicitly_trusted(self):
        self.store_java.write_bytes(b"Q" * 256)
        with patch.object(r445, "MAX_STORE_BYTES", 64):
            with self.assertRaisesRegex(
                    r445.Refused, "R445_STORE_PIN_FILE_TOO_LARGE"):
                self.scan()

    def test_09_original_store_changed_before_fd_open_refused(self):
        original_open = r445.os.open
        def raced_open(path, flags, *args, **kwargs):
            self.store_java.write_bytes(b"R445 changed before fd open, more")
            return original_open(path, flags, *args, **kwargs)
        with patch.object(r445.os, "open", side_effect=raced_open):
            with self.assertRaisesRegex(
                    r445.Refused, "R445_FILE_IDENTITY_CHANGED_BEFORE_READ"):
                r445.exact_store_pin_matches(
                    self.store_java, r425.PINNED_R421_STORE_SHA)

    def test_10_original_store_changed_during_fd_read_refused(self):
        original_read = r445.os.read
        changed = [False]
        def raced_read(fd, amount):
            chunk = original_read(fd, amount)
            if not changed[0]:
                changed[0] = True
                self.store_java.write_bytes(b"R445 changed during read and grew")
            return chunk
        with patch.object(r445.os, "read", side_effect=raced_read):
            with self.assertRaisesRegex(
                    r445.Refused, "R445_FILE_IDENTITY_CHANGED_DURING_READ"):
                r445.exact_store_pin_matches(
                    self.store_java, r425.PINNED_R421_STORE_SHA)
        self.assertTrue(changed[0])

    def test_11_replaced_original_store_symlink_not_read(self):
        outside = self.temp / "not-owned.txt"
        outside.write_bytes(b"never read external user data")
        self.store_java.unlink()
        try:
            self.store_java.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Unprivileged symlink creation unavailable")
        self.assertIsNone(r445.exact_store_pin_matches(
            self.store_java, r425.PINNED_R421_STORE_SHA))
        with self.assertRaisesRegex(
                r445.Refused, "R444_SOURCE_CLASS_TREE_LINK_OR_NONDIR_REFUSED"):
            self.scan()

    def test_12_historical_candidate_directory_iteration_bounded(self):
        for i in range(4):
            (self.r421 / f"R421-candidate-{i}.json").write_bytes(b"{}")
        with patch.object(r445, "MAX_SCANNED_ENTRIES", 2):
            with self.assertRaisesRegex(
                    r445.Refused, "R445_HISTORICAL_DIRECTORY_LISTING_TOO_LARGE"):
                self.scan()

    def test_13_bounded_json_candidate_keeps_R442_shape_only(self):
        path = self.r421 / "R421-source-inventory.json"
        payload = {
            "schema": r442.SCHEMA,
            "archive_id": "R421-Fabricated-NotApproved",
            "source_inventory": {
                r425.STORE.as_posix(): r425.PINNED_R421_STORE_SHA},
            "class_inventory": {
                r425.EXPECTED_CHANGED_EXISTING_CLASS:
                    r425.PINNED_R421_STORE_CLASS},
            "dependency_sha256": {
                "R239_filtered.jar": "c"*64, "R218.jar": "d"*64},
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        result = self.scan()
        self.assertEqual(result["possible_r442_manifest_shapes_found"], 1)
        self.assertFalse(result["possible_reference_sha_independently_approved"])
        self.assertFalse(result["source_class_inventory_independently_approved"])
        self.assertFalse(result["owner_private_compile_executed"])

    def test_14_modified_candidate_json_is_not_scored_as_valid(self):
        path = self.r421 / "R421-source-inventory.json"
        path.write_bytes(b'{"schema":"foo"}')
        self.assertEqual(self.scan()["possible_r442_manifest_shapes_found"], 0)
        path.write_bytes(b"x" * 4096)
        with patch.object(r445, "MAX_JSON_BYTES", 1024):
            self.assertEqual(self.scan()["possible_r442_manifest_shapes_found"], 0)

    def test_15_no_new_private_data_or_unbounded_stdlib_calls(self):
        source = inspect.getsource(r445)
        self.assertNotIn("sorted(temp.iterdir())", source)
        self.assertNotIn("sorted(base.iterdir())", source)
        self.assertNotIn("os.walk(", source)
        self.assertNotIn("r425.hash_file(path)", source)
        self.assertIn("read_bounded_regular", source)
        self.assertIn('getattr(os, "O_NOFOLLOW", 0)', source)
        for phrase in ("subprocess.", "write_bytes(", "write_text(", "unlink(",
                       "shutil.rmtree(", "os.remove(", "--approve",
                       "--release"):
            self.assertNotIn(phrase, source)
        self.assertIn('"release_authorized": False', source)

    def test_16_public_discovery_cli_stays_explicitly_read_only(self):
        empty = self.temp / "blank"
        empty.mkdir()
        env = os.environ.copy()
        for key in ("TMPDIR", "TMP", "TEMP"):
            env[key] = str(empty)
        result = subprocess.run(
            [sys.executable, "-B", str(CLI), "--owner-read-only-evidence-audit"],
            env=env, capture_output=True, text=True, check=False, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertFalse(receipt["owner_isolated_r421_root_present"])
        self.assertFalse(receipt["release_authorized"])
        self.assertNotIn(str(empty), result.stdout)


if __name__ == "__main__":
    unittest.main()
