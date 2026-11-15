"""R421 invented JVM no-follow path provenance and safe leaf-creation tests.

All directories are temp fixtures. Never use the user's actual cache or
recover any client data; this is NOT original-client runtime acceptance.
"""
from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "tests/fixtures/r421/R421CacheDirectoryModel.java"


class R421CacheDirectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_classes = tempfile.TemporaryDirectory(prefix="r421-javac-")
        cls.classes = Path(cls.tmp_classes.name)
        proc = subprocess.run(["javac", "--release", "11", "-d",
                               str(cls.classes), str(JAVA)],
                              capture_output=True, text=True, timeout=45)
        if proc.returncode:
            raise RuntimeError(proc.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.tmp_classes.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="r421-fake-cache-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def call(self, *args):
        proc = subprocess.run(["java", "-cp", str(self.classes),
                               "R421CacheDirectoryModel", *map(str, args)],
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.strip()

    def prepare(self, path):
        return self.call("prepare", path)

    def test_01_creates_single_leaf_in_existing_parent(self):
        self.assertEqual(self.prepare(self.root/"fresh"), "CREATED")
        self.assertTrue((self.root/"fresh").is_dir())

    def test_02_existing_directory_accepted_without_creation(self):
        p = self.root/"existing"
        p.mkdir()
        self.assertEqual(self.prepare(p), "EXISTING")

    def test_03_second_preparation_idempotent(self):
        p = self.root/"fresh"
        self.assertEqual(self.prepare(p), "CREATED")
        self.assertEqual(self.prepare(p), "EXISTING")

    def test_04_no_recursive_parent_creation(self):
        p = self.root/"missing"/"leaf"
        self.assertEqual(self.prepare(p), "REFUSED")
        self.assertFalse((self.root/"missing").exists())

    def test_05_refuses_existing_regular_leaf(self):
        p = self.root/"leaf-file"
        p.write_bytes(b"fabricated")
        self.assertEqual(self.prepare(p), "REFUSED")
        self.assertEqual(p.read_bytes(), b"fabricated")

    def test_06_refuses_existing_symlink_leaf(self):
        target = self.root/"target"
        target.mkdir()
        link = self.root/"alias"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation not permitted")
        self.assertEqual(self.prepare(link), "REFUSED")
        self.assertTrue(target.is_dir())

    def test_07_refuses_symlink_parent(self):
        target = self.root/"real"
        target.mkdir()
        link = self.root/"link"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation not permitted")
        self.assertEqual(self.prepare(link/"child"), "REFUSED")
        self.assertFalse((target/"child").exists())

    def test_08_refuses_regular_file_parent(self):
        parent = self.root/"file-parent"
        parent.write_bytes(b"unchanged")
        self.assertEqual(self.prepare(parent/"child"), "REFUSED")
        self.assertEqual(parent.read_bytes(), b"unchanged")

    def test_09_path_does_not_touch_fabricated_intent(self):
        marker = self.root/"loot-history.delete.intent"
        marker.write_bytes(b"fabricated-intent")
        self.assertEqual(self.prepare(self.root/"history"), "CREATED")
        self.assertEqual(marker.read_bytes(), b"fabricated-intent")

    def test_10_path_does_not_touch_fabricated_ack(self):
        marker = self.root/"loot-history.delete.ack"
        marker.write_bytes(b"fabricated-ack")
        self.assertEqual(self.prepare(self.root/"history"), "CREATED")
        self.assertEqual(marker.read_bytes(), b"fabricated-ack")

    def test_11_path_does_not_touch_existing_history(self):
        file = self.root/"loot-history.json"
        file.write_bytes(b"fake-history")
        self.assertEqual(self.prepare(self.root/"history"), "CREATED")
        self.assertEqual(file.read_bytes(), b"fake-history")

    def test_12_no_history_file_created_in_fresh_leaf(self):
        p = self.root/"new"
        self.assertEqual(self.prepare(p), "CREATED")
        self.assertEqual(list(p.iterdir()), [])

    def test_13_does_not_delete_existing_leaf_files(self):
        p = self.root/"existing"
        p.mkdir()
        (p/"keep.txt").write_text("keep")
        self.assertEqual(self.prepare(p), "EXISTING")
        self.assertEqual((p/"keep.txt").read_text(), "keep")

    def test_14_repeated_calls_do_not_create_temp_or_lock_files(self):
        p = self.root/"history"
        for _ in range(3):
            self.prepare(p)
        self.assertEqual(list(p.iterdir()), [])

    def test_15_parent_is_refused_when_removed(self):
        p = self.root/"missing"/"leaf"
        self.assertEqual(self.prepare(p), "REFUSED")

    def test_16_colliding_processes_preserve_single_directory(self):
        p = self.root/"parallel"
        cmd = ["java", "-cp", str(self.classes),
               "R421CacheDirectoryModel", "prepare", str(p)]
        jobs = [subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True) for _ in range(4)]
        outcomes = []
        for job in jobs:
            stdout, stderr = job.communicate(timeout=10)
            self.assertEqual(job.returncode, 0, stderr)
            outcomes.append(stdout.strip())
        self.assertIn("CREATED", outcomes)
        self.assertTrue(all(o in ("CREATED", "EXISTING", "REFUSED") for o in outcomes))
        self.assertTrue(p.is_dir())
        self.assertEqual(list(p.iterdir()), [])

    def test_17_derived_live_cache_path_matches_expected_formula(self):
        expected = str(self.root) + os.sep + ".spawnpk" + os.sep
        self.assertEqual(self.call("derive", self.root, "SpawnPK", "false", "false"),
                         expected)

    def test_18_derived_test_cache_suffix(self):
        expected = str(self.root) + os.sep + ".spawnpk-test" + os.sep
        self.assertEqual(self.call("derive", self.root, "SpawnPK", "true", "false"),
                         expected)

    def test_19_derived_second_client_cache_path(self):
        expected = str(self.root) + os.sep + ".runex" + os.sep
        self.assertEqual(self.call("derive", self.root, "Runex", "false", "false"),
                         expected)

    def test_20_relative_developer_cache_retains_old_shape(self):
        expected = "." + os.sep + "cache" + os.sep
        self.assertEqual(self.call("derive", self.root, "SpawnPK", "false", "true"),
                         expected)

    def test_21_derive_does_not_create_cache_directory(self):
        self.call("derive", self.root, "SpawnPK", "false", "false")
        self.assertFalse((self.root/".spawnpk").exists())

    def test_22_rejects_separator_in_cache_key(self):
        self.assertEqual(self.call("derive", self.root, "../evil", "false", "false"),
                         "REFUSED")

    def test_23_rejects_colon_in_cache_key(self):
        self.assertEqual(self.call("derive", self.root, "C:evil", "false", "false"),
                         "REFUSED")

    def test_24_rejects_blank_key(self):
        self.assertEqual(self.call("derive", self.root, "", "false", "false"),
                         "REFUSED")

    def test_25_rejects_missing_home(self):
        self.assertEqual(self.call("derive", "", "SpawnPK", "false", "false"),
                         "REFUSED")

    def test_26_no_fallback_to_current_working_directory(self):
        self.assertEqual(self.call("derive", "", "SpawnPK", "false", "false"),
                         "REFUSED")
        self.assertFalse((self.root/"loot-history.json").exists())

    def test_27_rejects_overlong_cache_key(self):
        self.assertEqual(self.call("derive", self.root, "x"*81, "false", "false"),
                         "REFUSED")

    def test_28_parent_leaf_existing_dir_with_dot_normalization(self):
        p = self.root/"history"
        p.mkdir()
        self.assertEqual(self.prepare(p/".."/"history"), "EXISTING")

    def test_29_creating_leaf_does_not_wipe_parent(self):
        existing = self.root/"retain"
        existing.write_bytes(b"existing")
        self.assertEqual(self.prepare(self.root/"new"), "CREATED")
        self.assertEqual(existing.read_bytes(), b"existing")

    def test_30_empty_parent_path_refused(self):
        self.assertEqual(self.prepare(self.root.anchor), "REFUSED")


if __name__ == "__main__":
    unittest.main()
