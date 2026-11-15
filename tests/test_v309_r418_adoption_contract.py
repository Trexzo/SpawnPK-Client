"""Invented R418 TEMP-only UI restore tests; not real client integration."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest

from tools.r417 import restart_ack_model as intent
from tools.r418.adoption_contract import Panel, normal_writes_admitted


def record(title="Synthetic", ts=7):
    return {"title": title, "subtitle": "", "type": "NPC", "kills": 1,
            "timestamp": ts, "items": [{"id": 3, "name": "Synthetic token",
            "quantity": 1, "price": 0, "hidden": False}]}


def canonical(rows):
    return json.dumps({"version": 1, "records": rows},
                      separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class R418AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="r418-fabricated-ui-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.before = canonical([record("Old")])
        self.after = canonical([record("Same title", 1), record("Same title", 2)])
        (self.root / intent.HISTORY).write_bytes(self.after)
        (self.root / intent.INTENT).write_bytes(intent.synth_intent(self.before, self.after))
        self.panel = Panel()
        self.panel.start("fabricated-owner-1")

    def stage(self):
        candidate = self.panel.stage(self.root)
        self.assertIsNotNone(candidate)
        return candidate

    def test_01_valid_committed_stages(self):
        self.assertEqual(len(self.stage().records), 2)

    def test_02_preserve_same_title_distinct_drops(self):
        c = self.stage()
        self.assertEqual(self.panel.apply(self.root, c, "fabricated-owner-1"),
                         "APPLIED_READ_ONLY_FENCED")
        self.assertEqual([r["timestamp"] for r in self.panel.records], [1, 2])

    def test_03_repeated_apply_never_duplicates(self):
        c = self.stage()
        self.panel.apply(self.root, c, "fabricated-owner-1")
        baseline = self.panel.snapshot()
        self.assertEqual(self.panel.apply(self.root, c, "fabricated-owner-1"),
                         "ALREADY_APPLIED")
        self.assertEqual(self.panel.snapshot(), baseline)

    def test_04_foreign_owner_refused(self):
        c = self.stage()
        initial = self.panel.snapshot()
        self.assertEqual(self.panel.apply(self.root, c, "foreign"), "REFUSED_OWNER")
        self.assertEqual(self.panel.snapshot(), initial)

    def test_05_stale_epoch_refused(self):
        c = self.stage()
        self.panel.start("new-session")
        initial = self.panel.snapshot()
        self.assertEqual(self.panel.apply(self.root, c, "new-session"),
                         "REFUSED_STALE_SESSION")
        self.assertEqual(self.panel.snapshot(), initial)

    def test_06_revoked_owner_refused(self):
        c = self.stage()
        self.panel.revoke()
        self.assertEqual(self.panel.apply(self.root, c, "fabricated-owner-1"),
                         "REFUSED_OWNER")
        self.assertIsNone(self.panel.stage(self.root))

    def test_07_changed_history_refused(self):
        c = self.stage()
        (self.root / intent.HISTORY).write_bytes(self.before)
        self.assertEqual(self.panel.apply(self.root, c, "fabricated-owner-1"),
                         "REFUSED_CHANGED_DISK")

    def test_08_changed_intent_refused(self):
        c = self.stage()
        (self.root / intent.INTENT).write_bytes(b"tampered")
        self.assertEqual(self.panel.apply(self.root, c, "fabricated-owner-1"),
                         "REFUSED_CHANGED_DISK")

    def test_09_unresolved_ack_stage_refused(self):
        c = self.stage()
        (self.root / intent.ACK_TMP).write_bytes(b"incomplete")
        self.assertEqual(self.panel.apply(self.root, c, "fabricated-owner-1"),
                         "REFUSED_CHANGED_DISK")

    def test_10_unresolved_history_stage_refused(self):
        c = self.stage()
        (self.root / intent.HISTORY_TMP).write_bytes(b"incomplete")
        self.assertEqual(self.panel.apply(self.root, c, "fabricated-owner-1"),
                         "REFUSED_CHANGED_DISK")

    def test_11_local_mutation_refuses_restore(self):
        c = self.stage()
        self.panel.pending_local_records = 1
        self.assertEqual(self.panel.apply(self.root, c, "fabricated-owner-1"),
                         "REFUSED_LOCAL_MUTATION")

    def test_12_new_process_ui_can_adopt_again(self):
        c = self.stage()
        self.panel.apply(self.root, c, "fabricated-owner-1")
        next_panel = Panel()
        next_panel.start("fabricated-new-process")
        next_candidate = next_panel.stage(self.root)
        self.assertEqual(next_panel.apply(self.root, next_candidate, "fabricated-new-process"),
                         "APPLIED_READ_ONLY_FENCED")
        self.assertEqual(next_panel.records, self.panel.records)

    def test_13_missing_intent_refused(self):
        (self.root / intent.INTENT).unlink()
        self.assertIsNone(self.panel.stage(self.root))

    def test_14_aborted_old_image_refused(self):
        (self.root / intent.HISTORY).write_bytes(self.before)
        self.assertIsNone(self.panel.stage(self.root))

    def test_15_never_alters_intent_or_history(self):
        c = self.stage()
        original = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.panel.apply(self.root, c, "fabricated-owner-1")
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_16_never_allows_normal_writes(self):
        c = self.stage()
        self.panel.apply(self.root, c, "fabricated-owner-1")
        self.assertFalse(normal_writes_admitted(self.panel))

    def test_17_malformed_but_digest_matching_rejected(self):
        bad = b'{"version":1,"records":[{"impossible":true}]}'
        (self.root / intent.HISTORY).write_bytes(bad)
        (self.root / intent.INTENT).write_bytes(intent.synth_intent(self.before, bad))
        self.assertIsNone(self.panel.stage(self.root))

    def test_18_acknowledged_history_remains_restoreable_not_writeable(self):
        state = intent.inspect(self.root)
        self.assertEqual(intent.publish_ack(self.root, state, adoption_confirmed=True),
                         intent.ACKED)
        candidate = self.stage()
        self.assertEqual(self.panel.apply(self.root, candidate, "fabricated-owner-1"),
                         "APPLIED_READ_ONLY_FENCED")
        self.assertFalse(normal_writes_admitted(self.panel))


if __name__ == "__main__":
    unittest.main()
