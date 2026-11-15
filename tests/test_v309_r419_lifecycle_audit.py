"""R419 synthetic structural false-positive controls; no private Java published."""
from __future__ import annotations

import unittest
from tools.r419.audit_private_leased_lifecycle import Refused, check_source

STORE = """
class InventedStore {
 private volatile R418CooperativeLease r419Owner;
 boolean r419ActivateOwner() {
    if (r419Owner != null) { return false; }
    R418CooperativeLease admitted = r418TryAcquireCooperativeLease();
    r419Owner = admitted;
    return true;
 }
 void r419CloseOwner() {
    r419Owner = null;
    prior.close();
 }
 boolean r419WithOwner(Runnable operation) {
    return owner.withOwner(owner.sessionToken(), operation);
 }
 R411StageState r411StageState() {
    if (!r419OwnsLease()) { return R411StageState.UNSAFE; }
    r417UnresolvedAckEvidence();
    return R411StageState.CLEAR;
 }
 void deleteStale() {
    r419WithOwner(this::r419DeleteStaleLeased);
 }
 List loadForMerge() {
    r419WithOwner(() -> receipt.add(r419LoadForMergeLeased()));
    return null;
 }
 boolean r415SaveWithReceipt(Collection records, boolean confirmedDeletion) {
    if (!r419WithOwner(() -> r419SaveWithReceiptLeased(records, confirmedDeletion))) {
       R413WriteDisposition.FAILED_BEFORE_REPLACE;
    }
    return false;
 }
 boolean clearWithReceipt() {
    r419WithOwner(() -> receipt[0] = r419ClearWithReceiptLeased());
    return false;
 }
}
"""

PLUGIN = """
class InventedPlugin {
 void startUp() {
    historyStore = new LootHistoryStore();
 }
 void loadHistory() {
    Thread worker = new Thread(() -> {
       if (!restoreStore.r419ActivateOwner()) { return; }
       if (generation != r395HistoryGeneration) { return; }
       restoreStore.deleteStale();
       stored = restoreStore.loadForMerge();
       SwingUtilities.invokeLater(() -> {});
    });
 }
 void shutDown() {
    r419ShutdownCommitThread = Thread.currentThread();
    instance = null;
    persistHistory();
    r419ShutdownCommitThread = null;
    final Function closer = closingStore::r419CloseOwner;
 }
 void persistHistory() {
    if (!r399AcceptingDrops &&
       Thread.currentThread() != r419ShutdownCommitThread) { return; }
 }
 void r402ApplyPanelDeletion(Runnable mutation) {
    if (!r399AcceptingDrops || instance != this) { return; }
 }
 void clearHistory() {
    if (!r399AcceptingDrops || instance != this) { return; }
 }
}
"""


class R419AuditNegativeTests(unittest.TestCase):
    def bad_store(self, old: str, new: str):
        changed = STORE.replace(old, new)
        self.assertNotEqual(changed, STORE)
        with self.assertRaises(Refused):
            check_source(changed, PLUGIN)

    def bad_plugin(self, old: str, new: str):
        changed = PLUGIN.replace(old, new)
        self.assertNotEqual(changed, PLUGIN)
        with self.assertRaises(Refused):
            check_source(STORE, changed)

    def test_01_good_synthetic_contract(self):
        result = check_source(STORE, PLUGIN)
        self.assertTrue(result["all_four_history_entrypoint_wrappers"])

    def test_02_owner_not_volatile(self):
        self.bad_store("volatile R418CooperativeLease", "R418CooperativeLease")

    def test_03_no_os_lock_acquisition(self):
        self.bad_store("r418TryAcquireCooperativeLease()", "null")

    def test_04_unconditional_successful_activation(self):
        self.bad_store("r419Owner = admitted;", "r419Owner = null;")

    def test_05_close_does_not_revoke(self):
        self.bad_store("r419Owner = null;", "r419Owner = prior;")

    def test_06_close_release_before_revocation(self):
        self.bad_store("r419Owner = null;\n    prior.close();",
                       "prior.close();\n    r419Owner = null;")

    def test_07_withowner_removed(self):
        self.bad_store("owner.withOwner(owner.sessionToken(), operation)", "true")

    def test_08_stage_does_not_require_owner(self):
        self.bad_store("if (!r419OwnsLease())", "if (false)")

    def test_09_stage_no_failclosed_receipt(self):
        self.bad_store("return R411StageState.UNSAFE;", "return R411StageState.CLEAR;")

    def test_10_stage_old_ack_gate_removed(self):
        self.bad_store("r417UnresolvedAckEvidence()", "false")

    def test_11_unleased_cleanup(self):
        self.bad_store("r419WithOwner(this::r419DeleteStaleLeased)",
                       "r419DeleteStaleLeased()")

    def test_12_unleased_load(self):
        self.bad_store("r419WithOwner(() -> receipt.add(r419LoadForMergeLeased()))",
                       "receipt.add(r419LoadForMergeLeased())")

    def test_13_unleased_save(self):
        self.bad_store("r419WithOwner(() -> r419SaveWithReceiptLeased(records, confirmedDeletion))",
                       "r419SaveWithReceiptLeased(records, confirmedDeletion)")

    def test_14_unleased_clear(self):
        self.bad_store("r419WithOwner(() -> receipt[0] = r419ClearWithReceiptLeased())",
                       "r419ClearWithReceiptLeased()")

    def test_15_no_pre_replace_receipt(self):
        self.bad_store("R413WriteDisposition.FAILED_BEFORE_REPLACE",
                       "R413WriteDisposition.REPLACE_ATTEMPTED")

    def test_16_startup_cleanup_before_owner(self):
        self.bad_plugin("historyStore = new LootHistoryStore();",
                        "historyStore = new LootHistoryStore();\n historyStore.deleteStale();")

    def test_17_no_background_worker(self):
        self.bad_plugin("new Thread(", "new Runnable(")

    def test_18_no_worker_lease_acquire(self):
        self.bad_plugin("restoreStore.r419ActivateOwner()", "true")

    def test_19_no_restart_epoch_check(self):
        self.bad_plugin("generation != r395HistoryGeneration", "false")

    def test_20_cleanup_before_lease(self):
        self.bad_plugin("if (!restoreStore.r419ActivateOwner()) { return; }",
                        "restoreStore.deleteStale();\n if (!restoreStore.r419ActivateOwner()) { return; }")

    def test_21_load_before_cleanup(self):
        self.bad_plugin("restoreStore.deleteStale();\n       stored = restoreStore.loadForMerge();",
                        "stored = restoreStore.loadForMerge();\n       restoreStore.deleteStale();")

    def test_22_no_shutdown_owner_revocation(self):
        self.bad_plugin("closingStore::r419CloseOwner", "closingStore::doNothing")

    def test_23_shutdown_thread_gate_missing(self):
        self.bad_plugin("r419ShutdownCommitThread = Thread.currentThread()",
                        "r419ShutdownCommitThread = null")

    def test_24_shutdown_thread_not_reset(self):
        self.bad_plugin("r419ShutdownCommitThread = null;",
                        "r419ShutdownCommitThread = Thread.currentThread();")

    def test_25_late_autosave_not_fenced(self):
        self.bad_plugin("Thread.currentThread() != r419ShutdownCommitThread", "false")

    def test_26_stale_panel_delete_not_fenced(self):
        self.bad_plugin("void r402ApplyPanelDeletion(Runnable mutation) {\n    if (!r399AcceptingDrops || instance != this)",
                        "void r402ApplyPanelDeletion(Runnable mutation) {\n    if (false)")

    def test_27_stale_clear_not_fenced(self):
        self.bad_plugin("void clearHistory() {\n    if (!r399AcceptingDrops || instance != this)",
                        "void clearHistory() {\n    if (false)")


if __name__ == "__main__":
    unittest.main()
