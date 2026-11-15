"""R419 invented TEMP-only lease lifecycle tests, JDK 21 compiling Java 11 model.

These are not tests of the private recovered client or a Swing runtime.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
R418 = ROOT / "tests/fixtures/r418/R418SingleWriterModel.java"
R419 = ROOT / "tests/fixtures/r419/R419LeaseLifecycleSynthetic.java"


class R419LifecycleSyntheticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("java") or not shutil.which("javac"):
            raise RuntimeError("JDK 11+ unavailable")
        cls.compiled = tempfile.TemporaryDirectory(prefix="r419-synth-classes-")
        cls.dir = Path(cls.compiled.name)
        result = subprocess.run(
            ["javac", "--release", "11", "-d", str(cls.dir), str(R418), str(R419)],
            capture_output=True, text=True, timeout=50)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.compiled.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="r419-synth-temp-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_java(self, main="R419LeaseLifecycleSynthetic",
                 arg="selftest", directory=None):
        return subprocess.run(["java", "-cp", str(self.dir), main, arg,
                               str(self.root if directory is None else directory)],
                              capture_output=True, text=True, timeout=25)

    def test_01_java_lease_lifecycle_all_assertions(self):
        result = self.run_java()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("R419_SYNTHETIC_LIFECYCLE_PASS assertions=", result.stdout)

    def test_02_restart_model_is_repeatable(self):
        self.assertEqual(self.run_java().returncode, 0)
        self.assertEqual(self.run_java().returncode, 0)

    def test_03_no_history_generated(self):
        self.run_java()
        self.assertFalse((self.root / "loot-history.json").exists())

    def test_04_no_ack_or_intent_generated(self):
        self.run_java()
        self.assertFalse((self.root / "loot-history.delete.intent").exists())
        self.assertFalse((self.root / "loot-history.delete.ack").exists())

    def test_05_lockfile_persists_after_model_stops(self):
        self.assertEqual(self.run_java().returncode, 0)
        self.assertTrue((self.root / "synthetic-loot-history.writer.lock").is_file())

    def test_06_lockfile_presence_is_not_live_ownership(self):
        self.run_java()
        result = self.run_java("R418SingleWriterModel", "try")
        self.assertIn("ACQUIRED", result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_07_orphan_history_stage_is_preserved(self):
        p = self.root / "loot-history.json.tmp"
        p.write_bytes(b"fabricated-unresolved-stage")
        self.run_java()
        self.assertEqual(p.read_bytes(), b"fabricated-unresolved-stage")

    def test_08_orphan_intent_is_preserved(self):
        p = self.root / "loot-history.delete.intent"
        p.write_bytes(b"fabricated-intent")
        self.run_java()
        self.assertEqual(p.read_bytes(), b"fabricated-intent")

    def test_09_orphan_ack_is_preserved(self):
        p = self.root / "loot-history.delete.ack"
        p.write_bytes(b"fabricated-ack")
        self.run_java()
        self.assertEqual(p.read_bytes(), b"fabricated-ack")

    def test_10_missing_directory_does_not_create_it(self):
        p = self.root / "not-created"
        result = self.run_java(directory=p)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(p.exists())

    def test_11_existing_lock_directory_fails_closed(self):
        (self.root / "synthetic-loot-history.writer.lock").mkdir()
        self.assertNotEqual(self.run_java().returncode, 0)

    def test_12_two_independent_temp_paths(self):
        other = self.root / "second-directory"
        other.mkdir()
        a = self.run_java()
        b = self.run_java(directory=other)
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(b.returncode, 0, b.stderr)

    def test_13_retired_worker_does_not_prevent_next_run(self):
        for _ in range(4):
            result = self.run_java()
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_14_no_user_records_or_live_files_loaded(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        result = self.run_java()
        self.assertEqual(result.returncode, 0)
        for name, value in before.items():
            if name != "synthetic-loot-history.writer.lock":
                self.assertEqual((self.root / name).read_bytes(), value)


if __name__ == "__main__":
    unittest.main()
