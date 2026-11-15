"""R423 standalone no-follow legacy cleanup tests on invented TEMP paths only.

Compiles an independent Java 11 model; never executes recovered SpawnPK
classes, opens a real history directory or modifies a live client.
"""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent / "fixtures" / "r423"
CLASS = "R423NoFollowLegacyCleanup"

class R423SafeLegacyCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiled = tempfile.TemporaryDirectory(prefix="r423-classes-")
        proc = subprocess.run(
            ["javac", "--release", "11", "-d", cls.compiled.name,
             str(HERE / "R423NoFollowLegacyCleanup.java")],
            capture_output=True, text=True, timeout=45)
        if proc.returncode:
            raise RuntimeError(proc.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.compiled.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(
            prefix="R423-Synthetic-", dir=tempfile.gettempdir())
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.legacy = self.root / "loot-history"
        self.keys = self.root / "loot-keys-seen.txt"
        self.hist = self.root / "loot-history.json"

    def cmd(self, mode="clean", root=None):
        return ["java", "-Xmx128m", "-Djava.awt.headless=true",
                "-Djava.io.tmpdir=" + tempfile.gettempdir(),
                "-cp", self.compiled.name, CLASS, mode,
                str(self.root if root is None else root)]

    def run_model(self, mode="clean", root=None):
        return subprocess.run(self.cmd(mode, root), capture_output=True,
                              text=True, timeout=20)

    def expect(self, expected, mode="clean", root=None):
        p = self.run_model(mode, root)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(p.stdout.strip().startswith(expected + " "), p.stdout)
        return p.stdout.strip()

    def tree(self):
        self.legacy.mkdir()
        (self.legacy / "a.dat").write_bytes(b"a")
        (self.legacy / "nested").mkdir()
        (self.legacy / "nested" / "b.dat").write_bytes(b"b")

    def hold(self):
        p = subprocess.Popen(self.cmd("hold"), stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, bufsize=1)
        self.assertEqual(p.stdout.readline().strip(), "ACQUIRED")
        def stop():
            if p.poll() is None:
                p.kill()
                p.wait(timeout=5)
            for stream in (p.stdin, p.stdout, p.stderr):
                if stream:
                    stream.close()
        self.addCleanup(stop)
        return p

    def test_01_empty_nothing(self):
        self.expect("NOTHING")

    def test_02_old_keys_deleted_only(self):
        self.keys.write_text("retired")
        self.expect("CLEANED")
        self.assertFalse(self.keys.exists())

    def test_03_legacy_tree_deleted_only(self):
        self.tree()
        self.expect("CLEANED")
        self.assertFalse(self.legacy.exists())

    def test_04_tree_and_keys_deleted(self):
        self.tree()
        self.keys.write_text("keys")
        self.expect("CLEANED")
        self.assertFalse(self.legacy.exists())
        self.assertFalse(self.keys.exists())

    def test_05_canonical_history_preserved(self):
        self.tree()
        self.hist.write_bytes(b"canonical-history-test")
        self.expect("CLEANED")
        self.assertEqual(self.hist.read_bytes(), b"canonical-history-test")

    def test_06_unrelated_root_file_preserved(self):
        self.tree()
        sentinel = self.root / "keep.txt"
        sentinel.write_text("kept")
        self.expect("CLEANED")
        self.assertEqual(sentinel.read_text(), "kept")

    def test_07_dry_run_no_mutations(self):
        self.tree()
        self.keys.write_text("keys")
        self.expect("READY", "dry-run")
        self.assertTrue(self.legacy.exists())
        self.assertEqual(self.keys.read_text(), "keys")

    def test_08_no_owner_refused(self):
        self.tree()
        self.expect("REFUSED", "no-owner")
        self.assertTrue(self.legacy.exists())

    def test_09_competing_java_owner_refused(self):
        self.tree()
        self.hold()
        self.expect("REFUSED")
        self.assertTrue(self.legacy.exists())

    def test_10_release_then_retry(self):
        self.tree()
        p = self.hold()
        p.stdin.write("\n")
        p.stdin.flush()
        self.assertEqual(p.wait(timeout=5), 0)
        self.expect("CLEANED")
        self.assertFalse(self.legacy.exists())

    def test_11_crashed_owner_releases_lock(self):
        self.tree()
        p = self.run_model("crash")
        self.assertEqual(p.returncode, 77)
        self.expect("CLEANED")
        self.assertFalse(self.legacy.exists())

    def test_12_preserves_inert_lock_file(self):
        self.tree()
        self.expect("CLEANED")
        self.assertTrue((self.root / "loot-history.writer.lock").is_file())

    def test_13_refuse_symlink_child_directory(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "external.txt").write_text("DO NOT DELETE")
        self.legacy.mkdir()
        (self.legacy / "a.dat").write_text("keep")
        try:
            (self.legacy / "escape").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        self.expect("REFUSED")
        self.assertEqual((outside / "external.txt").read_text(), "DO NOT DELETE")
        self.assertEqual((self.legacy / "a.dat").read_text(), "keep")

    def test_14_refuse_symlink_child_file(self):
        outside = self.root / "outside.txt"
        outside.write_text("DO NOT DELETE")
        self.legacy.mkdir()
        try:
            (self.legacy / "escape.txt").symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        self.expect("REFUSED")
        self.assertEqual(outside.read_text(), "DO NOT DELETE")

    def test_15_refuse_legacy_root_symlink(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "sentinel").write_text("keep")
        try:
            self.legacy.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        self.expect("REFUSED")
        self.assertEqual((outside / "sentinel").read_text(), "keep")

    def test_16_refuse_symlink_seen_keys_before_tree_delete(self):
        self.tree()
        target = self.root / "target"
        target.write_text("keep")
        try:
            self.keys.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        self.expect("REFUSED")
        self.assertTrue(self.legacy.exists())
        self.assertEqual(target.read_text(), "keep")

    def test_17_regular_file_at_legacy_root_refused(self):
        self.legacy.write_text("not directory")
        self.expect("REFUSED")
        self.assertEqual(self.legacy.read_text(), "not directory")

    def test_18_directory_at_seen_keys_refused_before_mutating(self):
        self.tree()
        self.keys.mkdir()
        self.expect("REFUSED")
        self.assertTrue(self.legacy.exists())

    def test_19_stage_marker_refuses_before_mutating(self):
        self.tree()
        (self.root / "loot-history.json.tmp").write_text("orphan")
        self.expect("REFUSED")
        self.assertTrue(self.legacy.exists())

    def test_20_intent_marker_refuses_before_mutating(self):
        self.tree()
        (self.root / "loot-history.delete.intent").write_text("orphan")
        self.expect("REFUSED")
        self.assertTrue(self.legacy.exists())

    def test_21_ack_marker_refuses_before_mutating(self):
        self.tree()
        (self.root / "loot-history.delete.ack").write_text("orphan")
        self.expect("REFUSED")
        self.assertTrue(self.legacy.exists())

    def test_22_ack_stage_marker_refuses_before_mutating(self):
        self.tree()
        (self.root / "loot-history.delete.ack.tmp").write_text("orphan")
        self.expect("REFUSED")
        self.assertTrue(self.legacy.exists())

    def test_23_intent_stage_marker_refuses_before_mutating(self):
        self.tree()
        (self.root / "loot-history.delete.intent.tmp").write_text("orphan")
        self.expect("REFUSED")
        self.assertTrue(self.legacy.exists())

    def test_24_fault_before_first_keeps_tree(self):
        self.tree()
        result = self.expect("PARTIAL", "fault-before-first")
        self.assertIn("deleted=0", result)
        self.assertTrue(self.legacy.exists())

    def test_25_fault_after_one_reports_partial(self):
        self.tree()
        result = self.expect("PARTIAL", "fault-after-one")
        self.assertIn("deleted=1", result)
        self.assertTrue(self.legacy.exists())

    def test_26_interrupt_before_scan_preserves_tree(self):
        self.tree()
        result = self.expect("INTERRUPTED", "interrupt")
        self.assertIn("deleted=0", result)
        self.assertTrue(self.legacy.exists())

    def test_27_interrupt_after_one_stops_cleanup(self):
        self.tree()
        result = self.expect("INTERRUPTED", "cancel-after-one")
        self.assertIn("deleted=1", result)
        self.assertTrue(self.legacy.exists())

    def test_28_empty_legacy_directory_deleted(self):
        self.legacy.mkdir()
        self.expect("CLEANED")
        self.assertFalse(self.legacy.exists())

    def test_29_nested_directory_limit_refuses_no_mutations(self):
        cur = self.legacy
        cur.mkdir()
        for _ in range(20):
            cur = cur / "a"
            cur.mkdir()
        (cur / "sentinel").write_text("untouched")
        self.expect("REFUSED")
        self.assertEqual((cur / "sentinel").read_text(), "untouched")

    def test_30_oversized_sparse_file_refused(self):
        self.legacy.mkdir()
        p = self.legacy / "huge"
        with p.open("wb") as f:
            f.truncate(65 * 1024 * 1024)
        self.expect("REFUSED")
        self.assertEqual(p.stat().st_size, 65 * 1024 * 1024)

    def test_31_entry_limit_refuses_without_deletion(self):
        self.legacy.mkdir()
        for i in range(4100):
            (self.legacy / ("f%04d" % i)).touch()
        self.expect("REFUSED")
        self.assertEqual(len(list(self.legacy.iterdir())), 4100)

    def test_32_repeated_cleanup_is_idempotent(self):
        self.tree()
        self.expect("CLEANED")
        self.expect("NOTHING")

    def test_33_non_synthetic_root_refused(self):
        p = self.run_model(root=Path(tempfile.gettempdir()))
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("R423_REFUSED_NON_SYNTHETIC_ROOT", p.stderr)

    def test_34_symlink_synthetic_root_refused(self):
        link = Path(tempfile.gettempdir()) / "R423-Synthetic-Symlink-From-Test"
        if link.exists() or link.is_symlink():
            self.skipTest("symlink name exists")
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        try:
            p = self.run_model(root=link)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("R423_REFUSED_NON_SYNTHETIC_ROOT", p.stderr)
        finally:
            link.unlink()

    def test_35_no_parent_legacy_outside_root_touched(self):
        outside = self.root / "outside"
        outside.mkdir()
        sent = outside / "dont-delete"
        sent.write_text("safe")
        self.tree()
        self.expect("CLEANED")
        self.assertEqual(sent.read_text(), "safe")

    def test_36_marker_in_parent_blocks_even_with_no_tree(self):
        (self.root / "loot-history.delete.intent").write_bytes(b"pending")
        self.expect("REFUSED")

    def test_37_no_histories_generated_by_lock_only(self):
        self.expect("NOTHING")
        self.assertFalse(self.hist.exists())

    def test_38_nonlegacy_nested_root_file_untouched(self):
        self.tree()
        other = self.root / "different"
        other.mkdir()
        (other / "foo").write_text("safe")
        self.expect("CLEANED")
        self.assertEqual((other / "foo").read_text(), "safe")

    def test_39_seen_keys_special_type_optional(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("fifo unsupported")
        os.mkfifo(self.keys)
        self.tree()
        self.expect("REFUSED")
        self.assertTrue(self.legacy.exists())

    def test_40_lock_owner_does_not_unlink_own_lock_file(self):
        self.expect("NOTHING")
        p = self.root / "loot-history.writer.lock"
        self.assertTrue(p.is_file())
        self.expect("NOTHING")
        self.assertTrue(p.is_file())

    def test_41_marker_added_after_scan_stops_before_delete(self):
        self.tree()
        result = self.expect("PARTIAL", "journal-after-scan")
        self.assertIn("deleted=0", result)
        self.assertTrue(self.legacy.exists())
        self.assertEqual((self.root / "loot-history.delete.intent").read_bytes(),
                         b"fabricated-late-marker")

    def test_42_symlink_replacing_first_file_after_scan_is_refused(self):
        self.tree()
        sentinel = self.root / "sentinel.txt"
        sentinel.write_text("outside-preserved")
        probe = self.root / "link-probe"
        try:
            probe.symlink_to(sentinel)
            probe.unlink()
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        result = self.expect("PARTIAL", "replace-first-with-symlink")
        self.assertIn("deleted=0", result)
        self.assertEqual(sentinel.read_text(), "outside-preserved")
        self.assertTrue(self.legacy.exists())

if __name__ == "__main__":
    unittest.main()
