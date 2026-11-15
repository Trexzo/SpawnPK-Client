"""R418: 22 invented real-TEMP Java cooperative lock tests; never real client."""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
MODEL = HERE / "fixtures" / "r418" / "R418SingleWriterModel.java"
MAIN = "R418SingleWriterModel"
LOCK = "synthetic-loot-history.writer.lock"


class R418CooperativeLeaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac") or not shutil.which("java"):
            raise RuntimeError("R418 Java 11+ JDK required")
        cls.classes_temp = tempfile.TemporaryDirectory(prefix="r418-classes-")
        cls.classes = Path(cls.classes_temp.name)
        p = subprocess.run(
            ["javac", "--release", "11", "-d", str(cls.classes), str(MODEL)],
            capture_output=True, text=True, timeout=45)
        if p.returncode:
            raise RuntimeError(p.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.classes_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="r418-fabricated-history-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def java(self, command, directory=None):
        return ["java", "-cp", str(self.classes), MAIN, command,
                str(self.root if directory is None else directory)]

    def call(self, command, directory=None):
        return subprocess.run(self.java(command, directory), capture_output=True,
                              text=True, timeout=15)

    def hold(self, directory=None):
        p = subprocess.Popen(self.java("hold", directory), stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, bufsize=1)
        line = p.stdout.readline().strip()
        self.addCleanup(lambda: self.end(p))
        return p, line

    @staticmethod
    def end(p):
        if p.poll() is None:
            p.kill()
            p.wait(timeout=10)
        for stream in (p.stdin, p.stdout, p.stderr):
            if stream:
                stream.close()

    def test_01_jvm_token_and_overlap_checks(self):
        p = self.call("selftest")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("cases=18", p.stdout)

    def test_02_uncontested_lock_acquired(self):
        p = self.call("try")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("ACQUIRED", p.stdout)
        self.assertIn("RELEASED", p.stdout)

    def test_03_other_process_denied(self):
        holder, line = self.hold()
        self.assertTrue(line.startswith("ACQUIRED "))
        self.assertEqual(self.call("try").stdout.strip(), "REFUSED")

    def test_04_released_lock_reacquired(self):
        holder, line = self.hold()
        self.assertTrue(line.startswith("ACQUIRED"))
        holder.stdin.write("\n")
        holder.stdin.flush()
        self.assertEqual(holder.wait(timeout=10), 0)
        self.assertTrue((self.root / LOCK).is_file())
        self.assertIn("ACQUIRED", self.call("try").stdout)

    def test_05_crashed_holder_reacquired(self):
        p = self.call("crash")
        self.assertEqual(p.returncode, 77)
        self.assertTrue((self.root / LOCK).is_file())
        self.assertIn("ACQUIRED", self.call("try").stdout)

    def test_06_crash_retains_intent(self):
        path = self.root / "loot-history.delete.intent"
        path.write_bytes(b"fabricated-intent")
        self.call("crash")
        self.assertEqual(path.read_bytes(), b"fabricated-intent")

    def test_07_different_directories_are_independent(self):
        other = self.root / "other"
        other.mkdir()
        holder, line = self.hold()
        self.assertTrue(line.startswith("ACQUIRED"))
        self.assertIn("ACQUIRED", self.call("try", other).stdout)

    def test_08_absent_directory_refused_without_creation(self):
        absent = self.root / "missing"
        self.assertEqual(self.call("try", absent).stdout.strip(), "REFUSED")
        self.assertFalse(absent.exists())

    def test_09_file_not_directory_refused(self):
        bad = self.root / "not-directory"
        bad.write_bytes(b"test")
        self.assertEqual(self.call("try", bad).stdout.strip(), "REFUSED")

    def test_10_lock_path_directory_refused(self):
        (self.root / LOCK).mkdir()
        self.assertEqual(self.call("try").stdout.strip(), "REFUSED")

    def test_11_inert_lock_file_not_false_busy(self):
        (self.root / LOCK).write_bytes(b"inert")
        self.assertIn("ACQUIRED", self.call("try").stdout)

    def test_12_existing_file_not_truncated(self):
        value = b"synthetic" * 200
        (self.root / LOCK).write_bytes(value)
        self.call("try")
        self.assertEqual((self.root / LOCK).read_bytes(), value)

    def test_13_unlocked_file_presence_is_not_owner(self):
        (self.root / LOCK).touch()
        self.assertIn("ACQUIRED", self.call("try").stdout)

    def test_14_two_simultaneous_holders_exclusive(self):
        a, line_a = self.hold()
        b, line_b = self.hold()
        self.assertTrue(line_a.startswith("ACQUIRED"))
        self.assertEqual(line_b, "REFUSED")
        self.assertIsNone(a.poll())

    def test_15_distinct_process_sessions_have_distinct_tokens(self):
        x, y = self.call("try"), self.call("try")
        self.assertEqual(x.returncode, 0)
        self.assertEqual(y.returncode, 0)
        self.assertNotEqual(x.stdout.splitlines()[0], y.stdout.splitlines()[0])

    def test_16_intent_and_ack_untouched(self):
        intent = self.root / "loot-history.delete.intent"
        ack = self.root / "loot-history.delete.ack"
        intent.write_bytes(b"fake-intent")
        ack.write_bytes(b"fake-ack")
        self.call("try")
        self.assertEqual(intent.read_bytes(), b"fake-intent")
        self.assertEqual(ack.read_bytes(), b"fake-ack")

    def test_17_unresolved_history_stage_untouched(self):
        p = self.root / "loot-history.json.tmp"
        p.write_bytes(b"unresolved")
        self.call("try")
        self.assertEqual(p.read_bytes(), b"unresolved")

    def test_18_no_history_generated_by_lease(self):
        self.call("try")
        self.assertFalse((self.root / "loot-history.json").exists())

    def test_19_lock_file_persists_across_sessions(self):
        for _ in range(5):
            self.assertIn("ACQUIRED", self.call("try").stdout)
        self.assertTrue((self.root / LOCK).is_file())

    def test_20_symlink_lock_path_refused(self):
        target = self.root / "target"
        target.write_bytes(b"fake")
        try:
            (self.root / LOCK).symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        self.assertEqual(self.call("try").stdout.strip(), "REFUSED")

    def test_21_symlink_root_refused(self):
        target = self.root / "real-directory"
        target.mkdir()
        link = self.root / "alias"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        self.assertEqual(self.call("try", link).stdout.strip(), "REFUSED")

    def test_22_crash_revokes_previous_session(self):
        crashed = self.call("crash")
        self.assertEqual(crashed.returncode, 77)
        prior_token = crashed.stdout.splitlines()[0]
        new_token = self.call("try").stdout.splitlines()[0]
        self.assertNotEqual(prior_token, new_token)


if __name__ == "__main__":
    unittest.main()
