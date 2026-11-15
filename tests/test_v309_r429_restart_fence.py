"""R429 fabricated TEMP-only durable-intent and restart-quarantine regressions.

Public Java11 test fixture exclusively: no private recovered game classes,
no actual player loot history, no profile, and no v312 installation access.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "fixtures/r429/R429SyntheticRestartFence.java"
MAIN = "rs.plugins.loottracker.R429SyntheticRestartFence"
LEDGER = "R429-synthetic-intent.ledger"
MARKERS = [
    "loot-history.json.tmp",
    "loot-history.delete.intent",
    "loot-history.delete.intent.tmp",
    "loot-history.delete.ack",
    "loot-history.delete.ack.tmp",
]


class R429RestartEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiled_tmp = tempfile.TemporaryDirectory(prefix="r429-classes-")
        cls.classes = Path(cls.compiled_tmp.name)
        process = subprocess.run(
            ["javac", "--release", "11", "-proc:none", "-d",
             str(cls.classes), str(SOURCE)],
            text=True, capture_output=True, timeout=45)
        if process.returncode:
            raise RuntimeError(process.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.compiled_tmp.cleanup()

    def setUp(self):
        self.scratch_tmp = tempfile.TemporaryDirectory(
            prefix="R429-Synthetic-", dir=tempfile.gettempdir())
        self.addCleanup(self.scratch_tmp.cleanup)
        self.scratch = Path(self.scratch_tmp.name)
        self.journal = self.scratch / LEDGER
        self.id = str(uuid.uuid4())

    def command(self, mode, identifier=None, root=None):
        command = [
            "java", "-Xmx128m", "-Djava.awt.headless=true",
            "-Djava.io.tmpdir=" + tempfile.gettempdir(),
            "-cp", str(self.classes), MAIN,
            mode, str(root if root is not None else self.scratch)
        ]
        if identifier is not None:
            command.append(identifier)
        return command

    def run_fence(self, mode, identifier=None, root=None):
        return subprocess.run(
            self.command(mode, identifier, root),
            text=True, capture_output=True, timeout=20)

    def ok(self, mode, identifier=None, contains=None):
        p = self.run_fence(mode, identifier)
        self.assertEqual(p.returncode, 0, p.stdout + "\n" + p.stderr)
        if contains is not None:
            self.assertIn(contains, p.stdout)
        return p

    def refuse(self, mode, identifier=None, contains="R429_REFUSED"):
        p = self.run_fence(mode, identifier)
        self.assertEqual(p.returncode, 2, p.stdout + "\n" + p.stderr)
        self.assertIn(contains, p.stdout)
        return p

    def initialize(self):
        self.ok("init", contains="R429_INITIALIZED R429_STATE=EMPTY")
        self.assertEqual(self.journal.stat().st_size, 256)

    def test_01_uninitialized_refuses_without_creating_ledger(self):
        self.refuse("status")
        self.assertFalse(self.journal.exists())

    def test_02_explicit_init_fixed_size_and_empty(self):
        self.initialize()
        self.ok("status", contains="R429_STATE=EMPTY SEQ=1")

    def test_03_duplicate_initialization_refuses_without_overwrite(self):
        self.initialize()
        before = self.journal.read_bytes()
        self.refuse("init")
        self.assertEqual(self.journal.read_bytes(), before)

    def test_04_begin_persists_pending_across_new_jvm(self):
        self.initialize()
        self.ok("begin", self.id, "R429_STATE=PENDING SEQ=2")
        self.ok("status", contains="R429_STATE=PENDING SEQ=2")
        self.assertIn(self.id, self.run_fence("status").stdout)

    def test_05_second_different_id_rejected_after_pending(self):
        self.initialize()
        self.ok("begin", self.id)
        self.refuse("begin", str(uuid.uuid4()),
                    "R429_PERSISTED_UNRESOLVED_EVIDENCE")

    def test_06_identical_id_does_not_retry_pending(self):
        self.initialize()
        self.ok("begin", self.id)
        self.refuse("begin", self.id,
                    "R429_PERSISTED_UNRESOLVED_EVIDENCE")

    def test_07_crash_after_forced_intent_retains_pending(self):
        self.initialize()
        p = self.run_fence("crash", self.id)
        self.assertEqual(p.returncode, 77, p.stdout + "\n" + p.stderr)
        self.assertIn("R429_SYNTHETIC_INTENT_FORCED_BEFORE_CRASH", p.stdout)
        self.ok("status", contains="R429_STATE=PENDING SEQ=2")
        self.refuse("begin", str(uuid.uuid4()),
                    "R429_PERSISTED_UNRESOLVED_EVIDENCE")

    def test_08_synthetic_proof_keeps_evidence_and_restart_fence(self):
        self.initialize()
        self.ok("begin", self.id)
        self.ok("seal", self.id, "R429_STATE=CONFIRMED SEQ=3")
        self.ok("status", contains="R429_STATE=CONFIRMED SEQ=3")
        self.refuse("begin", str(uuid.uuid4()),
                    "R429_PERSISTED_UNRESOLVED_EVIDENCE")

    def test_09_wrong_proof_uuid_refused_and_pending_unchanged(self):
        self.initialize()
        self.ok("begin", self.id)
        self.refuse("seal", str(uuid.uuid4()),
                    "R429_PROOF_NOT_MATCHING_PENDING_INTENT")
        self.ok("status", contains="R429_STATE=PENDING")

    def test_10_proof_without_intent_refused(self):
        self.initialize()
        self.refuse("seal", self.id, "R429_PROOF_NOT_MATCHING_PENDING_INTENT")

    def test_11_duplicate_proof_refused_and_sealed_evidence_retained(self):
        self.initialize()
        self.ok("begin", self.id)
        self.ok("seal", self.id)
        self.refuse("seal", self.id, "R429_PROOF_NOT_MATCHING_PENDING_INTENT")
        self.ok("status", contains="R429_STATE=CONFIRMED")

    def test_12_empty_operation_uuid_refused(self):
        self.initialize()
        self.refuse("begin", str(uuid.UUID(int=0)), "R429_INVALID_OPERATION_ID")
        self.ok("status", contains="R429_STATE=EMPTY")

    def test_13_missing_legacy_journal_evidence_preserved(self):
        for marker in MARKERS:
            with self.subTest(marker=marker):
                new = self.scratch / marker
                new.write_text("fabricated-do-not-delete", encoding="utf-8")
                self.refuse("init", contains="R429_UNRESOLVED_EXISTING_DELETE_EVIDENCE")
                self.assertEqual(new.read_text(), "fabricated-do-not-delete")
                self.assertFalse(self.journal.exists())
                new.unlink()

    def test_14_existing_marker_prevents_begin_without_mutation(self):
        self.initialize()
        original = self.journal.read_bytes()
        p = self.scratch / MARKERS[1]
        p.write_text("synthetic-intent", encoding="utf-8")
        self.refuse("begin", self.id,
                    "R429_UNRESOLVED_EXISTING_DELETE_EVIDENCE")
        self.assertEqual(self.journal.read_bytes(), original)
        self.assertEqual(p.read_text(), "synthetic-intent")

    def test_15_corrupted_pending_slot_refuses_not_fallback_to_empty(self):
        self.initialize()
        self.ok("begin", self.id)
        with self.journal.open("r+b") as handle:
            handle.seek(128 + 30)
            handle.write(b"\xfe")
        self.refuse("status", contains="R429_CORRUPT_OR_UNKNOWN_SLOT")
        self.refuse("begin", str(uuid.uuid4()),
                    "R429_CORRUPT_OR_UNKNOWN_SLOT")

    def test_16_truncated_ledger_refuses(self):
        self.initialize()
        with self.journal.open("r+b") as handle:
            handle.truncate(129)
        self.refuse("status", contains="R429_LEDGER_UNEXPECTED_SIZE")

    def test_17_unexpected_padding_bytes_refuse(self):
        self.initialize()
        with self.journal.open("r+b") as handle:
            handle.seek(100)
            handle.write(b"\x01")
        self.refuse("status", contains="R429_UNEXPECTED_TRAILING_BYTES")

    def test_18_competing_live_jvm_lock_refused_then_released(self):
        self.initialize()
        process = subprocess.Popen(
            self.command("hold"),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1)
        def cleanup():
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
        self.addCleanup(cleanup)
        self.assertEqual(process.stdout.readline().strip(),
                         "R429_SYNTHETIC_LOCK_HELD")
        self.refuse("begin", self.id, contains="R429_BUSY_LOCK")
        process.stdin.write("\n")
        process.stdin.flush()
        self.assertEqual(process.wait(timeout=7), 0)
        self.ok("begin", self.id, contains="R429_STATE=PENDING")

    def test_19_unrelated_canonical_history_is_untouched(self):
        history = self.scratch / "loot-history.json"
        history.write_bytes(b'{"fabricated":true}')
        before = history.read_bytes()
        self.initialize()
        self.ok("begin", self.id)
        self.ok("seal", self.id)
        self.assertEqual(history.read_bytes(), before)

    def test_20_non_synthetic_parent_refused(self):
        p = self.run_fence("status", root=Path(tempfile.gettempdir()))
        self.assertEqual(p.returncode, 2)
        self.assertIn("R429_ROOT_NOT_DIRECT_SYNTHETIC_TEMP", p.stdout)

    def test_21_symlink_root_refused_if_supported(self):
        link = Path(tempfile.gettempdir()) / (
            "R429-Synthetic-Link-" + uuid.uuid4().hex)
        try:
            link.symlink_to(self.scratch, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        self.addCleanup(link.unlink)
        p = self.run_fence("status", root=link)
        self.assertEqual(p.returncode, 2)
        self.assertIn("R429_UNSAFE_ANCESTOR", p.stdout)

    def test_22_symlink_ledger_refused_if_supported(self):
        outside = self.scratch / "outside"
        outside.write_text("do-not-touch", encoding="utf-8")
        try:
            self.journal.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        self.refuse("status", contains="R429_LEDGER_NOT_REGULAR_NOFOLLOW")
        self.assertEqual(outside.read_text(), "do-not-touch")

    def test_23_symlink_prior_marker_refuses_even_if_dangling(self):
        external = self.scratch / "missing-target"
        marker = self.scratch / MARKERS[0]
        try:
            marker.symlink_to(external)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        self.refuse("init", contains="R429_UNRESOLVED_EXISTING_DELETE_EVIDENCE")
        self.assertTrue(marker.is_symlink())

    def test_24_out_of_scope_java_source_has_no_private_client_access(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("import rs.", text)
        self.assertNotIn("LootHistoryStore", text)
        self.assertNotIn("LootTrackerPlugin", text)
        self.assertNotIn("client.jar", text)
        self.assertIn('startsWith("R429-Synthetic-")', text)

    def test_25_no_automatic_cleanup_or_unsafe_reset(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("Files.delete(", text)
        self.assertNotIn("Files.deleteIfExists(", text)
        self.assertNotIn("deleteOnExit(", text)
        self.assertNotIn("shutdownNow(", text)
        self.assertNotIn('"reset".equals(mode)', text)

    def test_26_file_forced_before_reporting_pending(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("channel.force(true)", text)
        self.assertIn("R429_WRITE_VERIFICATION_FAILED", text)
        self.assertIn("R429_PERSISTED_UNRESOLVED_EVIDENCE", text)


if __name__ == "__main__":
    unittest.main()
