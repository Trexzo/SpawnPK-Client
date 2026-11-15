"""Standalone R417 crash/interruption tests using invented TEMP-only history.

No private Java, actual player data or game process is involved.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.r417 import restart_ack_model as m


class R417SyntheticTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="r417-fabricated-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.before = (
            b'{"version":1,"records":[{"title":"Synthetic old","subtitle":"",'
            b'"type":"NPC","kills":1,"timestamp":10,"items":[]}]}'
        )
        self.after = m.synth_history()
        self.history(self.after)
        self.marker(self.before, self.after)

    def history(self, data: bytes | None):
        path = self.root / m.HISTORY
        if path.exists() or path.is_symlink():
            path.unlink()
        if data is not None:
            path.write_bytes(data)

    def marker(self, before: bytes | None, after: bytes):
        (self.root / m.INTENT).write_bytes(m.synth_intent(before, after))

    def ack(self):
        snap = m.inspect(self.root)
        self.assertEqual(snap.state, m.COMMITTED)
        return m.publish_ack(self.root, snap, adoption_confirmed=True)

    def ack_bytes(self) -> bytes:
        return (self.root / m.ACK).read_bytes()

    def fake_ack(self, payload: bytes):
        (self.root / m.ACK).write_bytes(payload)

    def child_interrupt(self, phase: str) -> int:
        code = (
            "import os,sys\n"
            "from pathlib import Path\n"
            "from tools.r417 import restart_ack_model as m\n"
            "d=Path(sys.argv[1]); stage=sys.argv[2]\n"
            "e=m.inspect(d)\n"
            "assert e.state==m.COMMITTED, e\n"
            "m.publish_ack(d,e,adoption_confirmed=True,"
            "after_step=lambda s: os._exit(71) if s==stage else None)\n"
            "os._exit(72)\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code, str(self.root), phase],
            cwd=str(Path(__file__).resolve().parents[1]), timeout=20,
            capture_output=True, text=True,
        )
        return proc.returncode

    def test_01_initial_committed_is_not_adopted(self):
        self.assertEqual(m.inspect(self.root).state, m.COMMITTED)

    def test_02_no_automatic_ack(self):
        for _ in range(3):
            self.assertEqual(m.inspect(self.root).state, m.COMMITTED)
        self.assertFalse((self.root / m.ACK).exists())

    def test_03_explicit_ack_publishes(self):
        self.assertEqual(self.ack(), m.ACKED)
        self.assertEqual(m.inspect(self.root).state, m.ACKED)

    def test_04_ack_preserves_original_intent(self):
        original = (self.root / m.INTENT).read_bytes()
        self.ack()
        self.assertEqual((self.root / m.INTENT).read_bytes(), original)

    def test_05_ack_preserves_history(self):
        original = (self.root / m.HISTORY).read_bytes()
        self.ack()
        self.assertEqual((self.root / m.HISTORY).read_bytes(), original)

    def test_06_ack_does_not_admit_writes(self):
        self.ack()
        self.assertFalse(m.ordinary_writer_permitted(self.root))

    def test_07_preack_does_not_admit_writes(self):
        self.assertFalse(m.ordinary_writer_permitted(self.root))

    def test_08_ack_without_adoption_refused(self):
        snap = m.inspect(self.root)
        self.assertEqual(m.publish_ack(self.root, snap), "REFUSED_NO_ADOPTION")
        self.assertFalse((self.root / m.ACK_TMP).exists())

    def test_09_bad_evidence_state_refused(self):
        evidence = m.Evidence(m.QUARANTINED)
        self.assertEqual(m.publish_ack(self.root, evidence, adoption_confirmed=True),
                         "REFUSED_NO_ADOPTION")

    def test_10_stale_evidence_after_history_edit(self):
        original = m.inspect(self.root)
        self.history(b'{"version":1,"records":[{"oops":true}]}')
        self.assertEqual(m.publish_ack(self.root, original, adoption_confirmed=True),
                         "REFUSED_CHANGED_EVIDENCE")

    def test_11_stale_evidence_after_marker_edit(self):
        original = m.inspect(self.root)
        (self.root / m.INTENT).write_bytes(b"not valid")
        self.assertEqual(m.publish_ack(self.root, original, adoption_confirmed=True),
                         "REFUSED_CHANGED_EVIDENCE")

    def test_12_aborted_not_acknowledgeable(self):
        self.history(self.before)
        self.assertEqual(m.inspect(self.root).state, m.ABORTED)
        self.assertEqual(m.publish_ack(self.root, m.inspect(self.root), adoption_confirmed=True),
                         "REFUSED_NO_ADOPTION")

    def test_13_ack_with_aborted_image_quarantined(self):
        self.ack()
        self.history(self.before)
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_14_changed_postack_history_quarantined(self):
        self.ack()
        self.history(self.after + b"x")
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_15_missing_postack_history_quarantined(self):
        self.ack()
        self.history(None)
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_16_changed_postack_intent_quarantined(self):
        self.ack()
        (self.root / m.INTENT).write_text("changed", encoding="utf-8")
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_17_missing_intent_with_ack_quarantined(self):
        self.ack()
        (self.root / m.INTENT).unlink()
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_18_both_markers_missing_none(self):
        (self.root / m.INTENT).unlink()
        self.assertEqual(m.inspect(self.root).state, m.NONE)

    def test_19_only_ack_stage_quarantined(self):
        (self.root / m.INTENT).unlink()
        (self.root / m.ACK_TMP).write_bytes(b"incomplete")
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_20_orphan_history_stage_quarantined(self):
        (self.root / m.HISTORY_TMP).write_bytes(b"incomplete")
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_21_orphan_intent_stage_quarantined(self):
        (self.root / m.INTENT_TMP).write_bytes(b"incomplete")
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_22_ack_stage_directory_quarantined(self):
        (self.root / m.ACK_TMP).mkdir()
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_23_ack_temp_plus_final_quarantined(self):
        self.ack()
        (self.root / m.ACK_TMP).write_bytes(b"extra")
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_24_bad_ack_serial_quarantined(self):
        self.ack()
        self.fake_ack(self.ack_bytes().replace(b"serial=1\n", b"serial=2\n"))
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_25_bad_ack_nonce_quarantined(self):
        self.ack()
        self.fake_ack(self.ack_bytes().replace(b"00000000-0000-4000-8000-000000000001",
                                               b"00000000-0000-4000-8000-000000000002"))
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_26_bad_ack_after_digest_quarantined(self):
        self.ack()
        self.fake_ack(self.ack_bytes().replace(m._hash(self.after).encode("ascii"),
                                               b"f" * 64))
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_27_bad_ack_status_quarantined(self):
        self.ack()
        self.fake_ack(self.ack_bytes().replace(b"acked=1\n", b"acked=0\n"))
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_28_extra_ack_field_quarantined(self):
        self.ack()
        self.fake_ack(self.ack_bytes() + b"extra=1\n")
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_29_truncated_ack_quarantined(self):
        self.ack()
        self.fake_ack(self.ack_bytes()[:45])
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_30_oversized_ack_quarantined(self):
        self.ack()
        self.fake_ack(self.ack_bytes() + b"x" * 520)
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_31_noncanonical_history_quarantined(self):
        payload = b'{ "version": 1, "records": [] }'
        self.history(payload)
        self.marker(self.before, payload)
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_32_wrong_schema_history_quarantined(self):
        payload = b'{"version":1,"records":[{"bad":true}]}'
        self.history(payload)
        self.marker(self.before, payload)
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_33_child_crash_after_ack_temp_fsync(self):
        self.assertEqual(self.child_interrupt("ACK_TEMP_FORCED"), 71)
        self.assertTrue((self.root / m.ACK_TMP).exists())
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_34_child_crash_after_ack_link(self):
        self.assertEqual(self.child_interrupt("ACK_FINAL_LINKED"), 71)
        self.assertTrue((self.root / m.ACK).exists())
        self.assertTrue((self.root / m.ACK_TMP).exists())
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_35_child_crash_after_ack_temp_removed(self):
        self.assertEqual(self.child_interrupt("ACK_TEMP_REMOVED"), 71)
        self.assertEqual(m.inspect(self.root).state, m.ACKED)
        self.assertFalse(m.ordinary_writer_permitted(self.root))

    def test_36_ack_idempotency_fences_duplicate(self):
        snap = m.inspect(self.root)
        self.ack()
        self.assertEqual(m.publish_ack(self.root, snap, adoption_confirmed=True),
                         "REFUSED_CHANGED_EVIDENCE")
        self.assertEqual(m.inspect(self.root).state, m.ACKED)

    def test_37_changed_history_while_ack_staged(self):
        snap = m.inspect(self.root)
        def interrupt(stage):
            if stage == "ACK_TEMP_FORCED":
                self.history(self.before)
        self.assertEqual(m.publish_ack(self.root, snap,
                                      adoption_confirmed=True, after_step=interrupt),
                         "REFUSED_CHANGED_EVIDENCE_AFTER_STAGE")
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)
        self.assertFalse((self.root / m.ACK).exists())

    def test_38_changed_intent_while_ack_staged(self):
        snap = m.inspect(self.root)
        def interrupt(stage):
            if stage == "ACK_TEMP_FORCED":
                (self.root / m.INTENT).write_bytes(b"changed")
        self.assertEqual(m.publish_ack(self.root, snap,
                                      adoption_confirmed=True, after_step=interrupt),
                         "REFUSED_CHANGED_EVIDENCE_AFTER_STAGE")
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_39_read_only_inspection_preserves_file_metadata(self):
        def state():
            return {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}
        original = state()
        for _ in range(5):
            self.assertEqual(m.inspect(self.root).state, m.COMMITTED)
        self.assertEqual(state(), original)

    def test_40_postack_restart_from_new_python_process(self):
        self.ack()
        code = ("from pathlib import Path;import sys;"
                "from tools.r417 import restart_ack_model as m;"
                "print(m.inspect(Path(sys.argv[1])).state)")
        p = subprocess.run([sys.executable, "-c", code, str(self.root)],
                           cwd=str(Path(__file__).resolve().parents[1]),
                           capture_output=True, text=True, timeout=20)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), m.ACKED)

    def test_41_symlink_ack_refused(self):
        self.ack()
        path = self.root / m.ACK
        target = self.root / "ack-source"
        target.write_bytes(path.read_bytes())
        path.unlink()
        try:
            path.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_42_symlink_history_refused(self):
        path = self.root / m.HISTORY
        target = self.root / "history-source"
        target.write_bytes(path.read_bytes())
        path.unlink()
        try:
            path.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_43_symlink_marker_refused(self):
        path = self.root / m.INTENT
        target = self.root / "intent-source"
        target.write_bytes(path.read_bytes())
        path.unlink()
        try:
            path.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        self.assertEqual(m.inspect(self.root).state, m.QUARANTINED)

    def test_44_after_ack_evidence_cannot_unblock_normal_saves(self):
        self.ack()
        for _ in range(10):
            self.assertEqual(m.inspect(self.root).state, m.ACKED)
            self.assertFalse(m.ordinary_writer_permitted(self.root))


if __name__ == "__main__":
    unittest.main()
