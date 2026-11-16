"""R430 fabricated negative controls for future SHA-pinned private-source guard.

No recovered private Java is present. Test-only fabricated Java text uses
the R417 structural auditor; the actual R421 SHA remains fixed in CLI.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from tools.r430.audit_private_existing_admission import (
    PRIVATE_SOURCE_SHA256, Refused, audit_source,
)

FAKE = '''
class LootHistoryStore {
    enum R411StageState { UNSAFE, CLEAR }
    enum R414IntentState { NONE }
    R414IntentState r414IntentState() { return R414IntentState.NONE; }
    R411StageState r411StageState() {
        if (r417UnresolvedAckEvidence()) {
            return R411StageState.UNSAFE;
        }
        if (r414IntentState() != R414IntentState.NONE)
            return R411StageState.UNSAFE;
        return R411StageState.CLEAR;
    }
    boolean r417UnresolvedAckEvidence() {
        try {
            Files.readAttributes(Path.of("loot-history.delete.ack"),
                BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            Files.readAttributes(Path.of("loot-history.delete.ack.tmp"),
                BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            return true;
        } catch (NoSuchFileException absent) {
            return false;
        } catch (IOException | SecurityException inaccessible) {
            return true;
        }
    }
    boolean r411RefuseUnresolvedStage(String why) { return true; }
    boolean r419ActivateOwner() { return false; }
    void r419CloseOwner() { }
    boolean r419WithOwner(Runnable action) { return false; }
    void loadForMerge() { }
    void saveWithReceipt() { }
    void clearWithReceipt() { }
    void deleteStale() { }
}
'''


class R430StaticPrivateGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="r430-source-negative-")
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "LootHistoryStore.java"
        self.file.write_text(FAKE, encoding="utf-8")

    def check(self, content=FAKE):
        self.file.write_text(content, encoding="utf-8")
        return audit_source(
            self.file, sha256(self.file.read_bytes()).hexdigest())

    def test_01_fake_source_guard_conformance_not_private(self):
        outcome = self.check()
        self.assertEqual(
            outcome["status"],
            "R430_OWNER_PRIVATE_SOURCE_READONLY_ADMISSION_AUDIT_PASS")
        self.assertFalse(outcome["writes_authorized"])
        self.assertFalse(outcome["delete_authorized"])
        self.assertFalse(outcome["marker_cleanup_authorized"])
        self.assertFalse(outcome["runtime_integration_verified"])

    def test_02_actual_source_pin_constant_retained(self):
        self.assertEqual(
            PRIVATE_SOURCE_SHA256,
            "0369e9b55e194ecfebfd754d15f66e6de84067634f16799a3c57c435b0616b29")

    def test_03_fake_wrong_digest_refused(self):
        with self.assertRaisesRegex(Refused, "SOURCE_SHA_PIN_MISMATCH"):
            audit_source(self.file, "0" * 64)

    def test_04_fake_malformed_digest_refused(self):
        with self.assertRaisesRegex(Refused, "SHA_FORMAT"):
            audit_source(self.file, "bad")

    def test_05_fake_wrong_filename_refused(self):
        other = self.file.parent / "Different.java"
        other.write_bytes(self.file.read_bytes())
        with self.assertRaisesRegex(Refused, "WRONG_OR_SYMLINK"):
            audit_source(other, sha256(other.read_bytes()).hexdigest())

    def test_06_fake_ack_tmp_symbol_removed_refused(self):
        changed = FAKE.replace('"loot-history.delete.ack.tmp"', '"different.tmp"')
        with self.assertRaisesRegex(Refused, "R417_ACK_GUARD_NOT_VERIFIED"):
            self.check(changed)

    def test_07_fake_nofollow_removed_refused(self):
        with self.assertRaisesRegex(Refused, "R417_ACK_GUARD_NOT_VERIFIED"):
            self.check(FAKE.replace("LinkOption.NOFOLLOW_LINKS", "LinkOption.values()[0]"))

    def test_08_fake_guard_order_reversed_refused(self):
        source = FAKE.replace(
            '''        if (r417UnresolvedAckEvidence()) {
            return R411StageState.UNSAFE;
        }
        if (r414IntentState() != R414IntentState.NONE)
            return R411StageState.UNSAFE;''',
            '''        if (r414IntentState() != R414IntentState.NONE)
            return R411StageState.UNSAFE;
        if (r417UnresolvedAckEvidence()) {
            return R411StageState.UNSAFE;
        }''')
        self.assertNotEqual(source, FAKE)
        with self.assertRaisesRegex(Refused, "R417_ACK_GUARD_NOT_VERIFIED"):
            self.check(source)

    def test_09_fake_guard_mutation_refused(self):
        source = FAKE.replace(
            "return true;\n        } catch (NoSuchFileException absent)",
            "Files.delete(Path.of(\"unsafe\")); return true;\n        } catch (NoSuchFileException absent)")
        with self.assertRaisesRegex(Refused, "R417_ACK_GUARD_NOT_VERIFIED"):
            self.check(source)

    def test_10_fake_r419_lease_symbol_missing_refused(self):
        with self.assertRaisesRegex(Refused, "MISSING_PRIVATE_ADMISSION_SYMBOL"):
            self.check(FAKE.replace("r419ActivateOwner", "differentOwner"))

    def test_11_source_bytes_unchanged_after_success(self):
        original = self.file.read_bytes()
        audit_source(self.file, sha256(original).hexdigest())
        self.assertEqual(self.file.read_bytes(), original)

    def test_12_fake_symlink_java_source_refused(self):
        link = self.file.parent / "link"
        try:
            link.symlink_to(self.file)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(Refused, "WRONG_OR_SYMLINK"):
            audit_source(link, sha256(self.file.read_bytes()).hexdigest())

if __name__ == "__main__":
    unittest.main()
