"""R430 public R415-R417 protocol compatibility and deny-only integration tests.

All fixtures are invented and constrained to R430-Synthetic-* direct TEMP
children. No recovered private client, real loot history or client JAR is
read, written or executed. This validates the existing R417 *public model*,
NOT its uninspected owner-private actual Store implementation.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

from tools.r417 import restart_ack_model as legacy
from tools.r430.inspect_existing_journal_readonly import (
    Gate, Refused, inspect_only, snapshot, synthetic_root,
    EXPERIMENTAL_LEDGER,
)

CLI = Path(__file__).resolve().parents[1] / (
    "tools/r430/inspect_existing_journal_readonly.py"
)

class R430ExistingProtocolBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(
            prefix="R430-Synthetic-", dir=tempfile.gettempdir())
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.history = self.root / legacy.HISTORY
        self.intent = self.root / legacy.INTENT
        self.ack = self.root / legacy.ACK
        self.canonical = legacy.synth_history()
        self.before = b'{"version":1,"records":[{"title":"synthetic","subtitle":"","type":"OTHER","kills":0,"timestamp":1,"items":[]}]}'
        self.assertTrue(legacy._valid_json_exact(self.canonical))
        self.assertTrue(legacy._valid_json_exact(self.before))

    def expect(self, status: str, state: str):
        before = snapshot(self.root)
        observed = inspect_only(self.root)
        self.assertEqual(observed.status, status)
        self.assertEqual(observed.classifier_state, state)
        for field in (
            "writer_authorized", "delete_authorized",
            "marker_cleanup_authorized", "client_executed",
            "private_source_inspected",
        ):
            self.assertFalse(getattr(observed, field), field)
        self.assertEqual(snapshot(self.root), before)
        return observed

    def committed(self):
        self.history.write_bytes(self.canonical)
        self.intent.write_bytes(legacy.synth_intent(self.before, self.canonical))

    def acknowledged(self):
        self.committed()
        observed = legacy.inspect(self.root)
        self.assertEqual(observed.state, legacy.COMMITTED)
        self.ack.write_bytes(
            (f"v=1\nserial={observed.serial}\nnonce={observed.nonce}\n"
             f"after={observed.history_sha}\nacked=1\n").encode("ascii"))
        self.assertEqual(legacy.inspect(self.root).state, legacy.ACKED)

    def call_cli(self, root=None):
        proc = subprocess.run(
            [sys.executable, str(CLI), "--synthetic-temp-root",
             str(self.root if root is None else root)],
            capture_output=True, text=True, timeout=15)
        return proc

    def test_01_no_evidence_still_does_not_authorize_write(self):
        self.expect("R430_NO_EVIDENCE_OWNER_LEASE_AND_STAGE_GATES_STILL_REQUIRED",
                    legacy.NONE)

    def test_02_existing_canonical_history_without_sidecar_not_permission(self):
        self.history.write_bytes(self.canonical)
        self.expect("R430_NO_EVIDENCE_OWNER_LEASE_AND_STAGE_GATES_STILL_REQUIRED",
                    legacy.NONE)

    def test_03_committed_intent_fences_further_writes(self):
        self.committed()
        self.expect("R430_COMMITTED_UNACKED_FENCED", legacy.COMMITTED)

    def test_04_aborted_before_replace_still_fenced(self):
        self.history.write_bytes(self.before)
        self.intent.write_bytes(legacy.synth_intent(self.before, self.canonical))
        self.expect("R430_ABORTED_BEFORE_REPLACE_FENCED", legacy.ABORTED)

    def test_05_matching_ack_still_fenced(self):
        self.acknowledged()
        self.expect("R430_ACK_RECORDED_BUT_STILL_FENCED", legacy.ACKED)

    def test_06_ack_without_intent_quarantined(self):
        self.ack.write_bytes(b"orphan synthetic ACK")
        self.expect("R430_QUARANTINED", legacy.QUARANTINED)

    def test_07_wrong_ack_nonce_quarantined(self):
        self.acknowledged()
        content = self.ack.read_text()
        self.ack.write_text(content.replace(
            "00000000-0000-4000-8000-000000000001",
            "00000000-0000-4000-8000-000000000002"))
        self.expect("R430_QUARANTINED", legacy.QUARANTINED)

    def test_08_staged_intent_refused(self):
        self.committed()
        (self.root / legacy.INTENT_TMP).write_bytes(b"orphan fabricated intent")
        self.expect("R430_QUARANTINED", legacy.QUARANTINED)

    def test_09_staged_ack_refused(self):
        self.acknowledged()
        (self.root / legacy.ACK_TMP).write_bytes(b"orphan fabricated ack")
        self.expect("R430_QUARANTINED", legacy.QUARANTINED)

    def test_10_staged_history_refused(self):
        self.history.write_bytes(self.canonical)
        (self.root / legacy.HISTORY_TMP).write_bytes(b"orphan fabricated history")
        self.expect("R430_QUARANTINED", legacy.QUARANTINED)

    def test_11_mismatched_after_digest_quarantined(self):
        self.committed()
        self.history.write_bytes(b'{"version":1,"records":[1]}')
        self.expect("R430_QUARANTINED", legacy.QUARANTINED)

    def test_12_invalid_json_schema_quarantined_even_when_digest_matches(self):
        invalid = b'{"version":1,"records":[1]}'
        self.history.write_bytes(invalid)
        self.intent.write_bytes(legacy.synth_intent(self.before, invalid))
        self.expect("R430_QUARANTINED", legacy.QUARANTINED)

    def test_13_noncanonical_json_quarantined_even_when_digest_matches(self):
        invalid = b'{"version": 1, "records": []}'
        self.history.write_bytes(invalid)
        self.intent.write_bytes(legacy.synth_intent(self.before, invalid))
        self.expect("R430_QUARANTINED", legacy.QUARANTINED)

    def test_14_corrupted_marker_refused(self):
        self.committed()
        self.intent.write_bytes(b"not the v1 R415 sidecar")
        self.expect("R430_QUARANTINED", legacy.QUARANTINED)

    def test_15_oversize_history_refused_before_read(self):
        self.history.write_bytes(b"x")
        with self.history.open("r+b") as fp:
            fp.truncate(64 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(Refused, "R430_OVERSIZE_EVIDENCE"):
            inspect_only(self.root)

    def test_16_symlink_intent_quarantined(self):
        self.history.write_bytes(self.canonical)
        target = self.root / "outside.txt"
        target.write_bytes(b"not a real intent")
        try:
            self.intent.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.expect("R430_QUARANTINED", legacy.QUARANTINED)
        self.assertEqual(target.read_bytes(), b"not a real intent")

    def test_17_dangling_symlink_ack_quarantined(self):
        try:
            self.ack.symlink_to(self.root / "missing")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.expect("R430_QUARANTINED", legacy.QUARANTINED)

    def test_18_experimental_r429_ledger_refused_even_without_old_markers(self):
        (self.root / EXPERIMENTAL_LEDGER).write_bytes(b"fabricated R429 extra ledger")
        self.expect("R430_EXPERIMENTAL_LEDGER_PRESENT_FENCED", legacy.NONE)

    def test_19_experimental_r429_ledger_refused_with_valid_ack(self):
        self.acknowledged()
        (self.root / EXPERIMENTAL_LEDGER).write_bytes(b"synthetic extra ledger")
        self.expect("R430_EXPERIMENTAL_LEDGER_PRESENT_FENCED", legacy.ACKED)

    def test_20_pre_post_observation_mismatch_refused(self):
        self.committed()
        real_inspect = legacy.inspect
        calls = [0]
        def changed(root):
            calls[0] += 1
            result = real_inspect(root)
            if calls[0] == 1:
                (self.root / EXPERIMENTAL_LEDGER).write_bytes(b"new evidence")
            return result
        with patch.object(legacy, "inspect", side_effect=changed):
            with self.assertRaisesRegex(Refused, "R430_EVIDENCE_DRIFT"):
                inspect_only(self.root)

    def test_21_different_consecutive_classifications_refused(self):
        self.committed()
        with patch.object(legacy, "inspect", side_effect=[
            legacy.Evidence(legacy.COMMITTED),
            legacy.Evidence(legacy.QUARANTINED),
        ]):
            with self.assertRaisesRegex(Refused, "R430_INCONSISTENT"):
                inspect_only(self.root)

    def test_22_cli_process_returns_only_deny_fields(self):
        self.committed()
        proc = self.call_cli()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "R430_COMMITTED_UNACKED_FENCED")
        self.assertFalse(data["writer_authorized"])
        self.assertFalse(data["delete_authorized"])
        self.assertFalse(data["marker_cleanup_authorized"])

    def test_23_cli_refuses_root_outside_synthetic_temp(self):
        proc = self.call_cli(Path(tempfile.gettempdir()))
        self.assertEqual(proc.returncode, 2)
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "R430_REFUSED")
        self.assertFalse(data["writer_authorized"])

    def test_24_cli_refuses_symlink_synthetic_root(self):
        target = Path(tempfile.gettempdir()) / (
            "R430-Synthetic-Alias-" + uuid.uuid4().hex)
        try:
            target.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.addCleanup(target.unlink)
        proc = self.call_cli(target)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)["status"], "R430_REFUSED")

    def test_25_inspector_does_not_create_any_files(self):
        self.committed()
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.expect("R430_COMMITTED_UNACKED_FENCED", legacy.COMMITTED)
        after = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.assertEqual(before, after)

    def test_26_experimental_ledger_does_not_become_ack(self):
        (self.root / EXPERIMENTAL_LEDGER).write_bytes(b"confirmed-invented")
        self.assertEqual(legacy.inspect(self.root).state, legacy.NONE)
        observed = inspect_only(self.root)
        self.assertFalse(observed.writer_authorized)
        self.assertEqual(observed.status, "R430_EXPERIMENTAL_LEDGER_PRESENT_FENCED")

if __name__ == "__main__":
    unittest.main()
