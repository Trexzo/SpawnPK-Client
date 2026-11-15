"""R420 real OS FileLock fault injection, all paths are invented TEMP folders.

JDK21 runs Java 11 source. No production client, history, credentials or actual
loot state is accessed, and no normal history write authorization is modeled.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
R418 = ROOT / "tests/fixtures/r418/R418SingleWriterModel.java"
R420 = ROOT / "tests/fixtures/r420/R420RetryFaultModel.java"


class R420FaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac") or not shutil.which("java"):
            raise RuntimeError("JDK 11 or later required")
        cls.classes_dir = tempfile.TemporaryDirectory(prefix="r420-synthetic-classes-")
        cls.classes = Path(cls.classes_dir.name)
        proc = subprocess.run(["javac", "--release", "11", "-d", str(cls.classes),
                               str(R418), str(R420)],
                              capture_output=True, text=True, timeout=40)
        if proc.returncode:
            raise RuntimeError(proc.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.classes_dir.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="r420-synthetic-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def command(self, action="probe", root=None, main="R420RetryFaultModel"):
        return ["java", "-cp", str(self.classes), main, action,
                str(self.root if root is None else root)]

    def run_java(self, action="probe", root=None, main="R420RetryFaultModel"):
        return subprocess.run(self.command(action, root, main),
                              capture_output=True, text=True, timeout=16)

    def hold(self):
        proc = subprocess.Popen(self.command("hold", main="R418SingleWriterModel"),
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, bufsize=1)
        first = proc.stdout.readline().strip()
        self.addCleanup(lambda: self.stop(proc))
        self.assertTrue(first.startswith("ACQUIRED "), first)
        return proc

    @staticmethod
    def stop(proc):
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream:
                stream.close()

    def release(self, proc):
        proc.stdin.write("\n")
        proc.stdin.flush()
        self.assertEqual(proc.wait(timeout=5), 0, proc.stderr.read())

    def async_retry(self):
        proc = subprocess.Popen(self.command("retry"), stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True)
        self.addCleanup(lambda: self.stop(proc))
        return proc

    def test_01_uncontended_first_attempt(self):
        p = self.run_java()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "ACQUIRED attempts=1")

    def test_02_busy_lock_exhausts_exact_five_attempts(self):
        holder = self.hold()
        t = time.monotonic()
        p = self.run_java("busy")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "BUSY attempts=5")
        self.assertGreaterEqual(time.monotonic() - t, 0.85)

    def test_03_lock_becomes_free_during_backoff(self):
        holder = self.hold()
        retry = self.async_retry()
        time.sleep(0.20)
        self.release(holder)
        stdout, stderr = retry.communicate(timeout=5)
        self.assertEqual(retry.returncode, 0, stderr)
        self.assertTrue(stdout.strip().startswith("ACQUIRED attempts="), stdout)

    def test_04_fast_release_acquires_earlier_attempt(self):
        holder = self.hold()
        retry = self.async_retry()
        time.sleep(0.10)
        self.release(holder)
        out, err = retry.communicate(timeout=5)
        self.assertEqual(retry.returncode, 0, err)
        self.assertTrue(out.strip().startswith("ACQUIRED attempts="), out)

    def test_05_after_timeout_new_attempt_can_acquire(self):
        holder = self.hold()
        self.assertEqual(self.run_java("busy").stdout.strip(), "BUSY attempts=5")
        self.release(holder)
        self.assertEqual(self.run_java().stdout.strip(), "ACQUIRED attempts=1")

    def test_06_invalidate_during_busy_retry(self):
        holder = self.hold()
        p = self.run_java("invalidate")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(p.stdout.startswith("STALE attempts="), p.stdout)
        self.assertEqual(self.run_java("busy").stdout.strip(), "BUSY attempts=5")

    def test_07_interrupted_retry_preserves_interrupt(self):
        holder = self.hold()
        p = self.run_java("interrupt")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(p.stdout.startswith("INTERRUPTED attempts="), p.stdout)

    def test_08_retry_never_blocks_swing_edt(self):
        holder = self.hold()
        t = time.monotonic()
        p = self.run_java("edt")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "EDT_REFUSED attempts=0")
        self.assertLess(time.monotonic() - t, 5)

    def test_09_edt_probe_does_not_create_lock_path(self):
        p = self.run_java("edt")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse((self.root / "synthetic-loot-history.writer.lock").exists())

    def test_10_blocked_write_reaper_waits_without_ui_join(self):
        p = self.run_java("held-write")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("HELD_WRITE_RELEASE_SAFE", p.stdout)

    def test_11_old_lock_file_not_active_lease(self):
        p = self.root / "synthetic-loot-history.writer.lock"
        p.write_bytes(b"synthetic old path")
        self.assertEqual(self.run_java().stdout.strip(), "ACQUIRED attempts=1")
        self.assertEqual(p.read_bytes(), b"synthetic old path")

    def test_12_dangling_symlink_lock_refused(self):
        path = self.root / "synthetic-loot-history.writer.lock"
        try:
            path.symlink_to(self.root / "missing-source")
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        self.assertEqual(self.run_java("busy").stdout.strip(), "BUSY attempts=5")

    def test_13_missing_parent_remains_absent(self):
        missing = self.root / "not-created"
        proc = self.run_java("fresh", missing)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "BUSY attempts=5")
        self.assertFalse(missing.exists())

    def test_14_non_directory_parent_refused(self):
        root = self.root / "bad-parent"
        root.write_bytes(b"fabricated")
        self.assertEqual(self.run_java("fresh", root).stdout.strip(), "BUSY attempts=5")

    def test_15_wrong_lock_file_type_refused(self):
        (self.root / "synthetic-loot-history.writer.lock").mkdir()
        self.assertEqual(self.run_java("busy").stdout.strip(), "BUSY attempts=5")

    def test_16_intent_ack_files_preserved_after_retry(self):
        before = {
            "loot-history.delete.intent": b"synthetic-intent",
            "loot-history.delete.ack": b"synthetic-ack",
            "loot-history.json.tmp": b"fabricated-stage",
        }
        for name, value in before.items():
            (self.root / name).write_bytes(value)
        self.assertEqual(self.run_java().returncode, 0)
        for name, value in before.items():
            self.assertEqual((self.root / name).read_bytes(), value)

    def test_17_absent_history_not_created_by_retry(self):
        self.assertEqual(self.run_java().returncode, 0)
        self.assertFalse((self.root / "loot-history.json").exists())

    def test_18_existing_history_never_modified(self):
        data = b'{"version":1,"records":[]}'
        path = self.root / "loot-history.json"
        path.write_bytes(data)
        before = hashlib.sha256(path.read_bytes()).digest()
        self.assertEqual(self.run_java().returncode, 0)
        self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)

    def test_19_crashed_holder_does_not_leave_live_lock(self):
        p = self.run_java("crash", main="R418SingleWriterModel")
        self.assertEqual(p.returncode, 77)
        self.assertTrue((self.root / "synthetic-loot-history.writer.lock").exists())
        self.assertEqual(self.run_java().stdout.strip(), "ACQUIRED attempts=1")

    def test_20_other_directory_available_while_one_busy(self):
        holder = self.hold()
        other = self.root / "other"
        other.mkdir()
        self.assertEqual(self.run_java(root=other).stdout.strip(), "ACQUIRED attempts=1")


if __name__ == "__main__":
    unittest.main()
