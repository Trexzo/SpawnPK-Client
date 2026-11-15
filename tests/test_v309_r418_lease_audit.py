"""R418 public fabricated negative controls for read-only private lease auditor."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from tools.r418.audit_private_cooperative_lease import Refused, audit, check_structure

PRIOR = "class SyntheticPriorStore {}"
GOOD = """
class SyntheticStore {
 private static final String R418_WRITER_LOCK = "loot-history.writer.lock";
 static final class R418CooperativeLease {
   private final UUID ownerSession = UUID.randomUUID();
   private boolean released;
   synchronized boolean owns(UUID claimed) {
      return !released && lock.isValid() && ownerSession.equals(claimed);
   }
   synchronized boolean withOwner(UUID claimed, Runnable action) {
      if (!owns(claimed)) return false;
      action.run();
      return true;
   }
   public synchronized void close() throws IOException {
      released = true;
      lock.release();
      channel.close();
   }
 }
 R418CooperativeLease r418TryAcquireCooperativeLease() {
   try {
     Files.readAttributes(directory, BasicFileAttributes.class,
          LinkOption.NOFOLLOW_LINKS);
     options.add(StandardOpenOption.CREATE);
     options.add(StandardOpenOption.WRITE);
     options.add(LinkOption.NOFOLLOW_LINKS);
     FileChannel channel = FileChannel.open(lockPath, options);
     FileLock lock = null;
     try {
       lock = channel.tryLock();
     } catch (OverlappingFileLockException conflict) { return null; }
     if (lock == null || !lock.isValid()) return null;
     return new R418CooperativeLease();
   } catch (IOException | SecurityException trouble) { return null; }
   finally { channel.close(); }
 }
 void oldAdmission() {
   r417UnresolvedAckEvidence();
   if (r414IntentState() != R414IntentState.NONE) return;
 }
}
"""


class R418AuditorNegativeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="r418-auditor-synthetic-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.old_s = self.root / "old_sources"
        self.new_s = self.root / "new_sources"
        self.old_c = self.root / "old_classes"
        self.new_c = self.root / "new_classes"
        for p in (self.old_s, self.new_s, self.old_c, self.new_c):
            p.mkdir()
        self.src = "rs/plugins/loottracker/LootHistoryStore.java"
        self.cls = "rs/plugins/loottracker/LootHistoryStore.class"
        self.lease = "rs/plugins/loottracker/LootHistoryStore$R418CooperativeLease.class"
        self.write(self.old_s, self.src, PRIOR)
        self.write(self.new_s, self.src, GOOD)
        self.write(self.old_c, self.cls, "prior bytecode")
        self.write(self.new_c, self.cls, "candidate bytecode")
        self.write(self.new_c, self.lease, "new synthetic nested bytecode")

    @staticmethod
    def write(root, name, contents):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, "utf-8")

    def full_audit(self, **kwargs):
        expected = {
            "prior_sources": self.old_s, "candidate_sources": self.new_s,
            "prior_classes": self.old_c, "candidate_classes": self.new_c,
            "source_count": 1, "prior_class_count": 1,
            "prior_sha": sha256((self.old_s / self.src).read_bytes()).hexdigest(),
            "candidate_sha": sha256((self.new_s / self.src).read_bytes()).hexdigest(),
        }
        expected.update(kwargs)
        return audit(**expected)

    def bad(self, changed):
        with self.assertRaises(Refused):
            check_structure(changed, PRIOR)

    def test_01_valid_structure(self):
        self.assertTrue(check_structure(GOOD, PRIOR)["dormant_only"])

    def test_02_valid_pinned_inventory(self):
        self.assertEqual(self.full_audit()["status"],
                         "R418_PRIVATE_DORMANT_LEASE_STATIC_GATE_PASS")

    def test_03_wrong_lock_name(self):
        self.bad(GOOD.replace('"loot-history.writer.lock"', '"other.lock"'))

    def test_04_blocking_instead_of_trylock(self):
        self.bad(GOOD.replace("channel.tryLock()", "channel.lock()"))

    def test_05_follow_symlink(self):
        self.bad(GOOD.replace("LinkOption.NOFOLLOW_LINKS", "LinkOption.FOLLOW_LINKS"))

    def test_06_no_create_option(self):
        self.bad(GOOD.replace("StandardOpenOption.CREATE", "StandardOpenOption.READ"))

    def test_07_no_write_option(self):
        self.bad(GOOD.replace("StandardOpenOption.WRITE", "StandardOpenOption.READ"))

    def test_08_no_overlapping_lock_guard(self):
        self.bad(GOOD.replace("OverlappingFileLockException", "RuntimeException"))

    def test_09_no_io_exception_refusal(self):
        self.bad(GOOD.replace("IOException | SecurityException", "RuntimeException"))

    def test_10_missing_revoked_token_check(self):
        self.bad(GOOD.replace("!released && ", ""))

    def test_11_no_session_match(self):
        self.bad(GOOD.replace("ownerSession.equals(claimed)", "true"))

    def test_12_unsynchronized_action(self):
        self.bad(GOOD.replace("synchronized boolean withOwner", "boolean withOwner"))

    def test_13_action_before_session_guard(self):
        self.bad(GOOD.replace("if (!owns(claimed)) return false;\n      action.run();",
                              "action.run();\n      if (!owns(claimed)) return false;"))

    def test_14_wrong_release_order(self):
        self.bad(GOOD.replace("released = true;\n      lock.release();",
                              "lock.release();\n      released = true;"))

    def test_15_unlink_lock_file(self):
        self.bad(GOOD.replace("finally { channel.close(); }",
                              "finally { Files.delete(lockPath); channel.close(); }"))

    def test_16_unexpected_old_ack_fence_removal(self):
        self.bad(GOOD.replace("r417UnresolvedAckEvidence();", ""))

    def test_17_already_present_in_prior(self):
        with self.assertRaises(Refused):
            check_structure(GOOD, PRIOR + "\nr418TryAcquireCooperativeLease()")

    def test_18_prior_sha_mismatch(self):
        with self.assertRaises(Refused):
            self.full_audit(prior_sha="0" * 64)

    def test_19_candidate_sha_mismatch(self):
        with self.assertRaises(Refused):
            self.full_audit(candidate_sha="f" * 64)

    def test_20_extra_changed_source(self):
        self.write(self.old_s, "Other.java", "old")
        self.write(self.new_s, "Other.java", "new")
        with self.assertRaises(Refused):
            self.full_audit(source_count=2)

    def test_21_extra_nested_class(self):
        self.write(self.new_c, "Unexpected.class", "unrelated")
        with self.assertRaises(Refused):
            self.full_audit()

    def test_22_missing_nested_class(self):
        (self.new_c / self.lease).unlink()
        with self.assertRaises(Refused):
            self.full_audit()

    def test_23_class_already_changed_in_prior(self):
        self.write(self.new_c, self.cls, "prior bytecode")
        with self.assertRaises(Refused):
            self.full_audit()

    def test_24_invalid_pin_not_sha256(self):
        with self.assertRaises(Refused):
            self.full_audit(candidate_sha="bad")


if __name__ == "__main__":
    unittest.main()
