"""R417 read-only exact-delta audit synthetic negative controls (no private Java)."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from tools.r417.audit_private_ack_fence import Refused, audit, verify_ack_guard

GOOD = """
enum R411StageState { CLEAR, UNSAFE }
R411StageState r411StageState()
{
    if (r417UnresolvedAckEvidence()) { return R411StageState.UNSAFE; }
    if (r414IntentState() != R414IntentState.NONE)
       return R411StageState.UNSAFE;
    return R411StageState.CLEAR;
}
private boolean r417UnresolvedAckEvidence()
{
    for (String name : new String[] {
        "loot-history.delete.ack",
        "loot-history.delete.ack.tmp"
    }) {
        try {
            Files.readAttributes(ack, BasicFileAttributes.class,
                LinkOption.NOFOLLOW_LINKS);
            return true;
        } catch (NoSuchFileException absent) {
        } catch (IOException | SecurityException unknown) {
            return true;
        }
    }
    return false;
}
void loadForMerge(){}
void saveWithReceipt(){}
void clearWithReceipt(){}
void deleteStale(){}
"""


class R417AckFenceAuditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="r417-audit-negative-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src_old = self.root / "previous_source"
        self.src_new = self.root / "candidate_source"
        self.cls_old = self.root / "previous_classes"
        self.cls_new = self.root / "candidate_classes"
        self.src = "rs/plugins/loottracker/LootHistoryStore.java"
        self.cls = "rs/plugins/loottracker/LootHistoryStore.class"
        for p in (self.src_old, self.src_new, self.cls_old, self.cls_new):
            p.mkdir()
        self.write(self.src_old, self.src, "old-private-placeholder")
        self.write(self.src_new, self.src, GOOD)
        self.write(self.cls_old, self.cls, "old-class")
        self.write(self.cls_new, self.cls, "new-class")
        self.prior_pin = self.sha(self.src_old / self.src)
        self.candidate_pin = self.sha(self.src_new / self.src)

    def write(self, root, relative, value):
        file = root / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(value, encoding="utf-8")

    def sha(self, file):
        return sha256(file.read_bytes()).hexdigest()

    def run_audit(self, **overrides):
        args = dict(prev_src=self.src_old, next_src=self.src_new,
                    prev_cls=self.cls_old, next_cls=self.cls_new,
                    expected_sources=1, expected_classes=1,
                    prior_sha=self.prior_pin, candidate_sha=self.candidate_pin)
        args.update(overrides)
        return audit(**args)

    def assertBad(self, code):
        with self.assertRaises(Refused):
            verify_ack_guard(code)

    def test_01_valid_inventory(self):
        self.assertEqual(self.run_audit()["status"],
                         "R417_PRIVATE_ACK_SIDECAR_ADMISSION_GATE_PASS")

    def test_02_valid_guard(self):
        self.assertTrue(verify_ack_guard(GOOD)["ack_marker_and_stage_fenced"])

    def test_03_missing_marker_name(self):
        self.assertBad(GOOD.replace('"loot-history.delete.ack",', '"other",'))

    def test_04_missing_stage_name(self):
        self.assertBad(GOOD.replace('"loot-history.delete.ack.tmp"', '"other.tmp"'))

    def test_05_ack_check_after_intent(self):
        self.assertBad(GOOD.replace(
            "if (r417UnresolvedAckEvidence()) { return R411StageState.UNSAFE; }\n"
            "    if (r414IntentState() != R414IntentState.NONE)",
            "if (r414IntentState() != R414IntentState.NONE)\n"
            "    if (r417UnresolvedAckEvidence()) { return R411StageState.UNSAFE; }"
        ))

    def test_06_missing_guard_invocation(self):
        self.assertBad(GOOD.replace("if (r417UnresolvedAckEvidence())", "if (false)"))

    def test_07_no_nofollow(self):
        self.assertBad(GOOD.replace("LinkOption.NOFOLLOW_LINKS", "LinkOption.FOLLOW_LINKS"))

    def test_08_missing_security_exception(self):
        self.assertBad(GOOD.replace("IOException | SecurityException", "IOException"))

    def test_09_missing_missingfile_handling(self):
        self.assertBad(GOOD.replace("NoSuchFileException absent", "IOException absent"))

    def test_10_delete_side_effect(self):
        self.assertBad(GOOD.replace("return false;", "Files.deleteIfExists(ack); return false;"))

    def test_11_move_side_effect(self):
        self.assertBad(GOOD.replace("return true;", "Files.move(ack, other); return true;"))

    def test_12_newoutput_side_effect(self):
        self.assertBad(GOOD.replace("return false;", "Files.newOutputStream(ack); return false;"))

    def test_13_guard_stub_in_comment_refused(self):
        self.assertBad(GOOD.replace(
            "if (r417UnresolvedAckEvidence()) { return R411StageState.UNSAFE; }",
            "// if (r417UnresolvedAckEvidence()) { return R411StageState.UNSAFE; }"
        ))

    def test_14_no_readattributes(self):
        self.assertBad(GOOD.replace("Files.readAttributes(", "Files.exists("))

    def test_15_missing_save_path(self):
        self.assertBad(GOOD.replace("void saveWithReceipt(){}", ""))

    def test_16_wrong_source_pin(self):
        with self.assertRaises(Refused):
            self.run_audit(candidate_sha="a" * 64)

    def test_17_invalid_pin(self):
        with self.assertRaises(Refused):
            self.run_audit(prior_sha="bad")

    def test_18_changed_extra_source(self):
        name = "Other.java"
        self.write(self.src_old, name, "old")
        self.write(self.src_new, name, "new")
        with self.assertRaises(Refused):
            self.run_audit(expected_sources=2)

    def test_19_added_class(self):
        self.write(self.cls_new, "Unexpected.class", "bad")
        with self.assertRaises(Refused):
            self.run_audit(expected_classes=2)

    def test_20_same_class_not_change(self):
        self.write(self.cls_new, self.cls, "old-class")
        with self.assertRaises(Refused):
            self.run_audit()

    def test_21_same_source_not_change(self):
        self.write(self.src_new, self.src, "old-private-placeholder")
        with self.assertRaises(Refused):
            self.run_audit()

    def test_22_mismatched_class_scope(self):
        self.write(self.cls_new, self.cls, "old-class")
        self.write(self.cls_new, "Different.class", "new-class")
        self.write(self.cls_old, "Different.class", "old-class")
        with self.assertRaises(Refused):
            self.run_audit(expected_classes=2)


if __name__ == "__main__":
    unittest.main()
