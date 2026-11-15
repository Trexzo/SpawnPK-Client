"""R420 fabricated negative controls for exact private retry verifier.

Does not include, compile or execute recovered Java source.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from tools.r420.audit_private_bounded_retry import Refused, audit, check_contract

BEFORE = """
class SyntheticPlugin {
 void loadHistory() {
    if (!restoreStore.r419ActivateOwner()) return;
    if (generation != r395HistoryGeneration) return;
    restoreStore.deleteStale();
    restoreStore.loadForMerge();
 }
}
"""
AFTER = """
class SyntheticPlugin {
 private boolean r420AcquireRestoreLeaseWithBoundedRetry(
     LootHistoryStore restoreStore, long generation) {
    if (SwingUtilities.isEventDispatchThread()) {
        return false;
    }
    final long[] retryDelayMillis = {0L, 75L, 150L, 300L, 450L};
    for (long delay : retryDelayMillis) {
        if (delay != 0L) {
            try {
                Thread.sleep(delay);
            } catch (InterruptedException canceled) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
        if (Thread.currentThread().isInterrupted()) { return false; }
        synchronized (r395HistoryGate) {
            if (generation != r395HistoryGeneration ||
                !r399AcceptingDrops || instance != this ||
                historyStore != restoreStore) {
                return false;
            }
        }
        if (restoreStore.r419ActivateOwner()) { return true; }
    }
    return false;
 }
 void loadHistory() {
    if (!r420AcquireRestoreLeaseWithBoundedRetry(restoreStore, generation)) return;
    if (generation != r395HistoryGeneration) return;
    restoreStore.deleteStale();
    restoreStore.loadForMerge();
 }
}
"""

class R420PinnedRetryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="r420-audit-synthetic-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.prev_src = root/"old-src"
        self.next_src = root/"new-src"
        self.prev_classes = root/"old-classes"
        self.next_classes = root/"new-classes"
        for directory in (self.prev_src, self.next_src,
                          self.prev_classes, self.next_classes):
            directory.mkdir()
        self.plugin = "rs/plugins/loottracker/LootTrackerPlugin.java"
        self.store = "rs/plugins/loottracker/LootHistoryStore.java"
        self.classname = "rs/plugins/loottracker/LootTrackerPlugin.class"
        self.storeclass = "rs/plugins/loottracker/LootHistoryStore.class"
        self.write(self.prev_src,self.plugin,BEFORE)
        self.write(self.next_src,self.plugin,AFTER)
        self.write(self.prev_src,self.store,"unchanged-synthetic-store")
        self.write(self.next_src,self.store,"unchanged-synthetic-store")
        self.write(self.prev_classes,self.classname,"old-synthetic-class")
        self.write(self.next_classes,self.classname,"new-synthetic-class")
        self.write(self.prev_classes,self.storeclass,"unchanged-store-class")
        self.write(self.next_classes,self.storeclass,"unchanged-store-class")

    @staticmethod
    def write(root,name,text):
        path = root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding="utf-8")

    def audit(self,**kw):
        args = dict(prior_src=self.prev_src,candidate_src=self.next_src,
                    prior_cls=self.prev_classes,candidate_cls=self.next_classes,
                    source_count=2,class_count=2,
                    prior_sha=sha256((self.prev_src/self.plugin).read_bytes()).hexdigest(),
                    candidate_sha=sha256((self.next_src/self.plugin).read_bytes()).hexdigest())
        args.update(kw)
        return audit(**args)

    def bad(self,old,new):
        changed = AFTER.replace(old,new)
        self.assertNotEqual(changed, AFTER)
        with self.assertRaises(Refused):
            check_contract(BEFORE,changed)

    def test_01_good_shape(self):
        self.assertTrue(check_contract(BEFORE,AFTER)["retry_background_only"])

    def test_02_good_inventory(self):
        self.assertEqual(self.audit()["status"],
                         "R420_PRIVATE_BOUNDED_RETRY_STATIC_GATE_PASS")

    def test_03_missing_edt_guard(self):
        self.bad("if (SwingUtilities.isEventDispatchThread())", "if (false)")

    def test_04_backoff_expanded(self):
        self.bad("450L", "9000L")

    def test_05_unbounded_while_loop(self):
        self.bad("for (long delay : retryDelayMillis)", "while (true)")

    def test_06_sleep_removed(self):
        self.bad("Thread.sleep(delay)", "Thread.yield()")

    def test_07_sleep_moved_under_history_gate(self):
        self.bad("synchronized (r395HistoryGate) {",
                 "synchronized (r395HistoryGate) { Thread.sleep(delay);")

    def test_08_no_interrupt_flag_restoration(self):
        self.bad("Thread.currentThread().interrupt();", "Thread.interrupted();")

    def test_09_ignore_existing_interrupt_flag(self):
        self.bad("if (Thread.currentThread().isInterrupted())", "if (false)")

    def test_10_no_session_epoch_check(self):
        self.bad("generation != r395HistoryGeneration ||", "false ||")

    def test_11_accept_when_plugin_stopped(self):
        self.bad("!r399AcceptingDrops", "false")

    def test_12_different_instance_admission(self):
        self.bad("instance != this", "false")

    def test_13_different_store_admission(self):
        self.bad("historyStore != restoreStore", "false")

    def test_14_no_lease_try(self):
        self.bad("restoreStore.r419ActivateOwner()", "true")

    def test_15_two_lease_acquisitions_per_attempt(self):
        self.bad("if (restoreStore.r419ActivateOwner())",
                 "restoreStore.r419ActivateOwner(); if (restoreStore.r419ActivateOwner())")

    def test_16_old_single_try_remains(self):
        self.bad("if (!r420AcquireRestoreLeaseWithBoundedRetry(restoreStore, generation)) return;",
                 "if (!restoreStore.r419ActivateOwner()) return;")

    def test_17_duplicate_helper_invocation(self):
        self.bad("if (!r420AcquireRestoreLeaseWithBoundedRetry(restoreStore, generation)) return;",
                 "r420AcquireRestoreLeaseWithBoundedRetry(restoreStore, generation);"
                 " if (!r420AcquireRestoreLeaseWithBoundedRetry(restoreStore, generation)) return;")

    def test_18_cleanup_before_retry(self):
        self.bad("if (!r420AcquireRestoreLeaseWithBoundedRetry(restoreStore, generation)) return;",
                 "restoreStore.deleteStale();"
                 "if (!r420AcquireRestoreLeaseWithBoundedRetry(restoreStore, generation)) return;")

    def test_19_delete_side_effect_in_helper(self):
        self.bad("if (restoreStore.r419ActivateOwner())",
                 "Files.delete(history); if (restoreStore.r419ActivateOwner())")

    def test_20_edt_invokewait_inside_helper(self):
        self.bad("Thread.sleep(delay)", "SwingUtilities.invokeAndWait(r); Thread.sleep(delay)")

    def test_21_old_parent_already_contains_method(self):
        with self.assertRaises(Refused):
            check_contract(BEFORE+"r420AcquireRestoreLeaseWithBoundedRetry()", AFTER)

    def test_22_wrong_prior_source_pin(self):
        with self.assertRaises(Refused):
            self.audit(prior_sha="a"*64)

    def test_23_wrong_candidate_source_pin(self):
        with self.assertRaises(Refused):
            self.audit(candidate_sha="f"*64)

    def test_24_changed_store_source_refused(self):
        self.write(self.next_src,self.store,"changed-store")
        with self.assertRaises(Refused):
            self.audit()

    def test_25_extra_class_delta_refused(self):
        self.write(self.next_classes,self.storeclass,"changed-store-class")
        with self.assertRaises(Refused):
            self.audit()

    def test_26_missing_class_refused(self):
        (self.next_classes/self.classname).unlink()
        with self.assertRaises(Refused):
            self.audit()

    def test_27_added_source_refused(self):
        self.write(self.next_src,"Unrelated.java","new")
        with self.assertRaises(Refused):
            self.audit()

    def test_28_changed_paths_pin_not_sha256(self):
        with self.assertRaises(Refused):
            self.audit(prior_sha="bad")


if __name__ == "__main__":
    unittest.main()
