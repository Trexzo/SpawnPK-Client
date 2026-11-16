"""R431 full synthetic Java Store adapter + R427 async + R417 restart verification.

The test compiles *independently authored* Java, exercising a real Swing EDT
and a real cooperative OS FileLock, with only R431-Synthetic-* direct TEMP
files. It uses the existing public R417 classifier for cross-language
evidence checks. Absolutely NO owner-private recovered game source/classes,
live player history, JAR, account settings or v312 runtime is accessed.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import uuid

from tools.r417 import restart_ack_model as legacy

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[0]
JAVA = [
    BASE / "fixtures/r427/R427AsyncDeleteCoordinator.java",
    BASE / "fixtures/r431/R431SyntheticJournalStore.java",
    BASE / "fixtures/r431/R431JournalBoundAsyncHarness.java",
]
MAIN = "rs.plugins.loottracker.R431JournalBoundAsyncHarness"
ORIGINAL = (b'{"version":1,"records":[{"title":"synthetic",'
            b'"subtitle":"","type":"OTHER","kills":0,"timestamp":1,"items":[]}]}')
AFTER = b'{"version":1,"records":[]}'


class R431JournalBoundAsyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac") or not shutil.which("java"):
            raise RuntimeError("R431_REQUIRES_JDK11")
        cls.classes_holder = tempfile.TemporaryDirectory(prefix="R431-Compiled-Public-")
        cls.classes = Path(cls.classes_holder.name)
        cmd = [
            "javac", "--release", "11", "-proc:none",
            "-encoding", "UTF-8", "-d", str(cls.classes),
            *[str(path) for path in JAVA],
        ]
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(
                "R431_JAVA11_COMPILE_FAILED\n" + result.stderr[-3000:])

    @classmethod
    def tearDownClass(cls):
        cls.classes_holder.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="R431-Synthetic-", dir=tempfile.gettempdir())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.history = self.root / legacy.HISTORY
        self.intent = self.root / legacy.INTENT

    def cmd(self, mode: str, root: Path | None = None):
        return [
            "java", "-Xmx256m", "-Djava.awt.headless=true",
            "-Djava.io.tmpdir=" + tempfile.gettempdir(),
            "-cp", str(self.classes), MAIN, mode,
            str(self.root if root is None else root),
        ]

    def run_mode(self, mode: str):
        proc = subprocess.run(
            self.cmd(mode), capture_output=True, text=True, timeout=35)
        self.assertEqual(
            proc.returncode, 0,
            mode + " failed\nOUT:\n" + proc.stdout + "\nERR:\n" + proc.stderr)
        self.assertIn(
            "R431_" + mode.upper().replace("-", "_") + "_PASS",
            proc.stdout)
        return proc

    def inspect(self, expected: str):
        observed = legacy.inspect(self.root)
        self.assertEqual(observed.state, expected)
        self.assertFalse(legacy.ordinary_writer_permitted(self.root))
        return observed

    def prepare(self):
        self.history.write_bytes(ORIGINAL)
        self.assertTrue(legacy._valid_json_exact(ORIGINAL))

    def test_01_full_async_journal_pipeline_never_claims_adopted_success(self):
        self.run_mode("commit")
        self.assertEqual(self.history.read_bytes(), AFTER)
        self.assertTrue(self.intent.is_file())
        self.assertFalse((self.root / legacy.HISTORY_TMP).exists())
        self.assertFalse((self.root / legacy.INTENT_TMP).exists())
        self.inspect(legacy.COMMITTED)

    def test_02_restarted_java_store_refuses_further_deletion(self):
        self.run_mode("commit")
        before_history = self.history.read_bytes()
        before_intent = self.intent.read_bytes()
        self.run_mode("restart")
        self.assertEqual(self.history.read_bytes(), before_history)
        self.assertEqual(self.intent.read_bytes(), before_intent)
        self.inspect(legacy.COMMITTED)

    def test_03_shutdown_waits_for_inflight_r415_marker_and_lock(self):
        self.run_mode("close-drains")
        self.assertEqual(self.history.read_bytes(), ORIGINAL)
        self.assertTrue(self.intent.is_file())
        self.assertTrue((self.root / legacy.HISTORY_TMP).is_file())
        self.inspect(legacy.QUARANTINED)

    def test_04_fault_after_history_stage_fences_restart(self):
        self.run_mode("fault-after-stage")
        self.assertEqual(self.history.read_bytes(), ORIGINAL)
        self.assertTrue((self.root / legacy.HISTORY_TMP).is_file())
        self.inspect(legacy.QUARANTINED)

    def test_05_fault_after_intent_tmp_force_fences_restart(self):
        self.run_mode("fault-after-intent-temp")
        self.assertTrue((self.root / legacy.INTENT_TMP).is_file())
        self.assertEqual(self.history.read_bytes(), ORIGINAL)
        self.inspect(legacy.QUARANTINED)

    def test_06_fault_after_intent_hardlink_fences_restart(self):
        self.run_mode("fault-after-publish")
        self.assertTrue(self.intent.is_file())
        self.assertTrue((self.root / legacy.INTENT_TMP).is_file())
        self.assertEqual(self.history.read_bytes(), ORIGINAL)
        self.inspect(legacy.QUARANTINED)

    def test_07_fault_after_atomic_replace_persists_but_quarantines_ui(self):
        self.run_mode("fault-after-replace")
        self.assertEqual(self.history.read_bytes(), AFTER)
        self.assertTrue(self.intent.is_file())
        self.inspect(legacy.COMMITTED)

    def test_08_stale_session_before_persistence_does_not_create_intent(self):
        self.run_mode("cancel-before")
        self.assertEqual(self.history.read_bytes(), ORIGINAL)
        self.assertFalse(self.intent.exists())
        self.assertFalse((self.root / legacy.HISTORY_TMP).exists())
        self.inspect(legacy.NONE)

    def test_09_existing_ack_marker_blocks_first_write(self):
        self.run_mode("refuse-ack")
        self.assertEqual(self.history.read_bytes(), ORIGINAL)
        self.assertFalse(self.intent.exists())
        self.assertEqual((self.root / legacy.ACK).read_bytes(),
                         b"\x09\x09\x09")
        self.inspect(legacy.QUARANTINED)

    def test_10_clear_all_is_not_accidentally_enabled(self):
        self.run_mode("refuse-kind")
        self.assertEqual(self.history.read_bytes(), ORIGINAL)
        self.assertFalse(self.intent.exists())
        self.inspect(legacy.NONE)

    def test_11_existing_symlink_marker_cannot_delete_outside_sentinel(self):
        result = self.run_mode("refuse-symlink")
        if "R431_OPTIONAL_SYMLINK_UNAVAILABLE" in result.stdout:
            self.skipTest("Windows symlink privilege unavailable")
        self.assertEqual(
            (self.root / "synthetic-external-preserve.txt").read_bytes(),
            b"\x01\x02\x03")
        self.assertTrue(self.intent.is_symlink())
        self.inspect(legacy.QUARANTINED)

    def test_12_second_jvm_cannot_acquire_live_owner_filelock(self):
        self.prepare()
        process = subprocess.Popen(
            self.cmd("hold-owner"), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1)
        def cleanup():
            if process.poll() is None:
                process.kill()
                process.wait(timeout=7)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
        self.addCleanup(cleanup)
        self.assertEqual(process.stdout.readline().strip(),
                         "R431_SYNTHETIC_OWNER_LOCK_HELD")
        self.run_mode("probe-owner")
        self.assertEqual(self.history.read_bytes(), ORIGINAL)
        self.assertFalse(self.intent.exists())
        process.stdin.write("\n")
        process.stdin.flush()
        self.assertEqual(process.wait(timeout=7), 0)
        self.run_mode("commit")
        self.inspect(legacy.COMMITTED)

    def test_13_real_process_crash_releases_lease_without_clearing_evidence(self):
        self.prepare()
        holder = subprocess.Popen(
            self.cmd("hold-owner"), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1)
        def cleanup():
            if holder.poll() is None:
                holder.kill()
                holder.wait(timeout=7)
            for stream in (holder.stdin, holder.stdout, holder.stderr):
                if stream is not None:
                    stream.close()
        self.addCleanup(cleanup)
        self.assertEqual(holder.stdout.readline().strip(),
                         "R431_SYNTHETIC_OWNER_LOCK_HELD")
        holder.kill()
        self.assertNotEqual(holder.wait(timeout=7), 0)
        self.run_mode("commit")
        self.inspect(legacy.COMMITTED)

    def test_14_non_synthetic_path_refused_before_any_write(self):
        path = Path(tempfile.gettempdir())
        proc = subprocess.run(
            self.cmd("commit", path),
            capture_output=True, text=True, timeout=15)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("R431_REFUSED_NON_SYNTHETIC_TEMP",
                      proc.stderr + proc.stdout)

    def test_15_prototype_cannot_be_loaded_as_real_client(self):
        source = JAVA[1].read_text(encoding="utf-8")
        self.assertNotIn("import net.runelite", source)
        self.assertNotIn("LootHistoryStore", source)
        self.assertNotIn("LootTrackerPlugin", source)
        self.assertNotIn("client.jar", source)
        self.assertIn('startsWith("R431-Synthetic-")', source)

    def test_16_output_never_adopts_ack_or_unblocks_writes(self):
        source = JAVA[1].read_text(encoding="utf-8")
        self.assertNotIn("Files.deleteIfExists(", source)
        self.assertNotIn("Files.delete(root.resolve(INTENT))", source)
        self.assertNotIn("R429SyntheticRestartFence", source)
        self.assertIn("return R427AsyncDeleteCoordinator.Outcome.UNCERTAIN;",
                      source)
        self.assertNotIn("return R427AsyncDeleteCoordinator.Outcome.CONFIRMED;",
                         source)

    def test_17_journal_intent_uses_r415_expected_version_one_schema(self):
        self.run_mode("commit")
        raw = self.intent.read_bytes()
        parsed = legacy._parse_intent(raw)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed[0], "1")
        self.assertEqual(parsed[2], legacy._hash(ORIGINAL))
        self.assertEqual(parsed[3], legacy._hash(AFTER))

    def test_18_journal_marker_remains_after_actual_replaced_history(self):
        self.run_mode("commit")
        evidence = self.intent.read_bytes()
        # Rechecking classification does not remove the original marker.
        for _ in range(3):
            self.inspect(legacy.COMMITTED)
        self.assertEqual(self.intent.read_bytes(), evidence)

    def test_19_matching_synthetic_ack_still_cannot_authorize_replay(self):
        self.run_mode("commit")
        existing = self.inspect(legacy.COMMITTED)
        ack = (
            f"v=1\\nserial={existing.serial}\\nnonce={existing.nonce}\\n"
            f"after={existing.history_sha}\\nacked=1\\n"
        ).replace("\\n", "\n").encode("ascii")
        (self.root / legacy.ACK).write_bytes(ack)
        self.inspect(legacy.ACKED)
        before = (self.history.read_bytes(), self.intent.read_bytes(),
                  (self.root / legacy.ACK).read_bytes())
        self.run_mode("restart")
        after = (self.history.read_bytes(), self.intent.read_bytes(),
                 (self.root / legacy.ACK).read_bytes())
        self.assertEqual(before, after)
        self.inspect(legacy.ACKED)

    def test_20_legacy_confirmed_intent_never_becomes_second_transaction(self):
        self.run_mode("commit")
        marker = self.intent.read_bytes()
        for _ in range(2):
            self.run_mode("restart")
        self.assertEqual(self.intent.read_bytes(), marker)
        self.assertEqual(self.history.read_bytes(), AFTER)
        self.inspect(legacy.COMMITTED)

    def test_21_foreign_stage_created_after_prefight_never_overwritten(self):
        self.run_mode("foreign-stage-race")
        self.assertEqual(self.history.read_bytes(), ORIGINAL)
        self.assertEqual(
            (self.root / legacy.HISTORY_TMP).read_bytes(),
            b"R431-FOREIGN-DO-NOT-OVERWRITE")
        self.assertFalse(self.intent.exists())
        self.inspect(legacy.QUARANTINED)


if __name__ == "__main__":
    unittest.main()
