"""R407 synthetic source/class and stale-session autosave negative controls.

Everything here is fabricated Java text and synthetic bytes. No private
client classes, source, loot history, credentials or production inputs.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "r407_public_gate",ROOT/"tools/r407/audit_clear_autosave_epoch.py")
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

SYNTH_PLUGIN="""
class FabricatedLoot {
  void clearHistory() {
    if (!SwingUtilities.isEventDispatchThread()) {
      SwingUtilities.invokeLater(this::clearHistory);
      return;
    }
    synchronized (r395HistoryGate) {
      if (r401ClearInProgress) return;
      r401ClearInProgress = true;
      ++r399SessionEpoch;
      r403AutosaveQueued = false;
      r403AutosaveDirty = false;
    }
    final boolean deleted;
    synchronized (r401FileGate) {
      deleted = historyStore.clearWithReceipt();
    }
    if (!deleted) {
      r401ClearUnsafe = true;
      return;
    }
    synchronized (r395HistoryGate) {
      r396PreloadRecords.clear();
      pendingRecords.clear();
      savePending = false;
    }
    panel.clearRecords();
    synchronized (r395HistoryGate) {
      r401ClearUnsafe = false;
      r401ClearInProgress = false;
    }
  }
  private void r403QueueAutosave() {
    synchronized (r395HistoryGate) {
      if (r403AutosaveQueued) {
        r403AutosaveDirty = true;
        return;
      }
      r403AutosaveQueued = true;
      issuedEpoch = r399SessionEpoch;
    }
    try {
      executor.execute(() -> {
        try {
          synchronized (r395HistoryGate) {
            if (!r399AcceptingDrops || instance != this ||
                issuedEpoch != r399SessionEpoch) {
              return;
            }
            r396LastCommitSucceeded = false;
          }
          r403WorkerEpoch.set(issuedEpoch);
          persistHistory();
          if (issuedEpoch == r399SessionEpoch &&
              !r396LastCommitSucceeded) {
            savePending = true;
          }
        }
        catch (RuntimeException error) {
          log.warn("fabricated", error);
          synchronized (r395HistoryGate) {
            if (issuedEpoch == r399SessionEpoch &&
                r399AcceptingDrops && instance == this &&
                !r401ClearInProgress && !r401ClearUnsafe) {
              savePending = true;
            }
          }
        }
        finally {
          r403WorkerEpoch.remove();
          synchronized (r395HistoryGate) {
            if (issuedEpoch == r399SessionEpoch) {
              if (r403AutosaveDirty) {
                savePending = true;
              }
              r403AutosaveQueued = false;
              r403AutosaveDirty = false;
            }
          }
        }
      });
    }
    catch (java.util.concurrent.RejectedExecutionException error) {
      synchronized (r395HistoryGate) {
        if (issuedEpoch == r399SessionEpoch) {
          r403AutosaveQueued = false;
          savePending = true;
        }
      }
    }
  }
  void persistHistory() {
    synchronized (r401FileGate) {
      Long epoch = r403WorkerEpoch.get();
      boolean written = historyStore.saveWithReceipt(merged);
    }
    if (r401Committed) {
      Long verified = r403WorkerEpoch.get();
    }
  }
  void shutDown() {
    r403RetiredWorker.shutdown();
    persistHistory();
  }
  void requestSave() {
    r403QueueAutosave();
  }
  void onGameTick() {
    r403QueueAutosave();
  }
  void r402ApplyPanelDeletion(Runnable mutation) {
    synchronized (r401FileGate) {
      mutation.run();
      persistHistory();
      if (!r402EditWriteReceipt) {
        unsafe = true;
      }
    }
  }
}
"""

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

class R407EpochGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        r=Path(self.temp.name)
        self.kit=r/"original.zip"
        self.reference=r/"original.jar"
        self.previous=r/"R405-source"
        self.candidate=r/"R407-source"
        self.prevcls=r/"R405-classes"
        self.newcls=r/"R407-classes"
        self.plugin=SYNTH_PLUGIN.encode("utf8")
        self.oldplugin=b"class PriorFabricatedLoot {}"
        self.additional={name:b"synthetic earlier modified "+name.encode("utf8")
                         for name in gate.GOLD_SRC if name!=gate.PLUGIN}
        self.classes_before={
            name:b"synthetic previous class "+name.encode("utf8")
            for name in gate.GOLD_CLS}
        self.classes_after=self.classes_before.copy()
        self.classes_after[gate.PLUGIN_CLS]=b"new fabricated plugin class"
        self.write()

    @staticmethod
    def files(folder,entries):
        folder.mkdir(parents=True,exist_ok=True)
        for f in folder.rglob("*"):
            if f.is_file():f.unlink()
        for name,data in entries.items():
            path=folder/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            for name in sorted(gate.GOLD_SRC):
                z.writestr("source/"+name,b"golden fabricated source")
        with ZipFile(self.reference,"w") as z:
            for name in sorted(gate.GOLD_CLS):
                z.writestr(name,b"golden fabricated class")
        self.files(self.previous,{**self.additional,gate.PLUGIN:self.oldplugin})
        self.files(self.candidate,{**self.additional,gate.PLUGIN:self.plugin})
        self.files(self.prevcls,self.classes_before)
        self.files(self.newcls,self.classes_after)

    def audit(self):
        return gate.audit(
            kit=self.kit,kit_sha=sha(self.kit),
            reference=self.reference,reference_sha=sha(self.reference),
            previous_sources=self.previous,previous_classes=self.prevcls,
            candidate_sources=self.candidate,candidate_classes=self.newcls,
            expected_sources=5,expected_classes=7)

    def mutate(self,old,new):
        original=old.encode("utf8")
        self.assertIn(original,self.plugin)
        self.plugin=self.plugin.replace(original,new.encode("utf8"))
        self.write()

    def refuse(self,reason=None):
        if reason:
            with self.assertRaisesRegex(gate.Refused,reason):self.audit()
        else:
            with self.assertRaises(gate.Refused):self.audit()

    def test_positive_exact_scope_and_release_closed(self):
        r=self.audit()
        self.assertEqual(r["status"],"R407_PRIVATE_CLEAR_AUTOSAVE_EPOCH_GATE_PASS")
        self.assertEqual(r["changed_source_count_vs_r405"],1)
        self.assertEqual(r["changed_class_count_vs_r405"],1)
        for key in ("private_client_runtime_executed","real_swing_schedule_verified",
                    "cross_process_file_lock_proven","power_loss_durability_proven",
                    "private_source_release_authorized","merge_approved"):
            self.assertFalse(r[key])
        self.assertTrue(r["clear_epoch_bump_resets_queue_and_dirty_under_history_gate"])
        self.assertTrue(r["obsolete_worker_exception_cannot_rearm_pending_save"])

    def test_receipt_contains_no_source(self):
        result=json.dumps(self.audit())
        self.assertNotIn("FabricatedLoot",result)
        self.assertNotIn("persistHistory()",result)
        self.assertNotIn("R405-source",result)

    def test_clear_epoch_must_advance(self):
        self.mutate("++r399SessionEpoch;","r399SessionEpoch;")
        self.refuse()

    def test_clear_queue_reset_required(self):
        self.mutate("      r403AutosaveQueued = false;\n      r403AutosaveDirty = false;",
                    "      r403AutosaveDirty = false;")
        self.refuse()

    def test_clear_dirty_reset_required(self):
        self.mutate("      r403AutosaveQueued = false;\n      r403AutosaveDirty = false;",
                    "      r403AutosaveQueued = false;")
        self.refuse()

    def test_clear_reset_must_follow_epoch_increment(self):
        self.mutate(
            "      ++r399SessionEpoch;\n      r403AutosaveQueued = false;",
            "      r403AutosaveQueued = false;\n      ++r399SessionEpoch;")
        self.refuse("R407_CRITICAL_EPOCH_OR_RECEIPT_ORDER_DRIFT")

    def test_clear_reset_must_be_inside_history_gate(self):
        self.mutate(
            "      r403AutosaveDirty = false;\n    }\n    final boolean deleted;",
            "    }\n    r403AutosaveDirty = false;\n    final boolean deleted;")
        self.refuse()

    def test_clear_reset_must_not_duplicate(self):
        self.mutate("      r403AutosaveDirty = false;\n    }\n    final boolean deleted;",
                    "      r403AutosaveDirty = false;\n      r403AutosaveDirty = false;\n    }\n    final boolean deleted;")
        self.refuse("R407_CLEAR_RESET_MUST_BE_EXACTLY_ONCE")

    def test_worker_receipt_reset_requires_shared_admission_monitor(self):
        self.mutate(
            "            r396LastCommitSucceeded = false;",
            "          }\n          synchronized (r395HistoryGate) {\n            r396LastCommitSucceeded = false;")
        self.refuse()

    def test_worker_early_epoch_check_required(self):
        self.mutate("issuedEpoch != r399SessionEpoch) {",
                    "issuedEpoch == r399SessionEpoch) {")
        self.refuse()

    def test_worker_admission_requires_accepted_session(self):
        self.mutate("if (!r399AcceptingDrops || instance != this ||",
                    "if (instance != this ||")
        self.refuse()

    def test_worker_admission_requires_instance_fence(self):
        self.mutate("if (!r399AcceptingDrops || instance != this ||",
                    "if (!r399AcceptingDrops ||")
        self.refuse()

    def test_worker_receipt_reset_not_allowed_before_guard(self):
        self.mutate("            r396LastCommitSucceeded = false;",
                    "            r396LastCommitSucceeded = false;")
        # Same exact source must remain valid; test the guard's order
        # through a separate deliberate reorder.
        self.mutate(
            "            if (!r399AcceptingDrops || instance != this ||",
            "            r396LastCommitSucceeded = false;\n            if (!r399AcceptingDrops || instance != this ||")
        self.refuse()

    def test_stale_exception_must_use_history_gate(self):
        self.mutate(
            '          synchronized (r395HistoryGate) {\n            if (issuedEpoch == r399SessionEpoch &&',
            '          if (issuedEpoch == r399SessionEpoch &&')
        self.refuse()

    def test_stale_exception_epoch_check_required(self):
        self.mutate(
            "if (issuedEpoch == r399SessionEpoch &&\n                r399AcceptingDrops",
            "if (true &&\n                r399AcceptingDrops")
        self.refuse()

    def test_stale_exception_acceptance_required(self):
        self.mutate(
            "r399AcceptingDrops && instance == this &&",
            "true && instance == this &&")
        self.refuse()

    def test_stale_exception_instance_check_required(self):
        self.mutate("instance == this &&\n                !r401ClearInProgress",
                    "true &&\n                !r401ClearInProgress")
        self.refuse()

    def test_stale_exception_clear_in_progress_guard(self):
        self.mutate("!r401ClearInProgress && !r401ClearUnsafe",
                    "true && !r401ClearUnsafe")
        self.refuse()

    def test_stale_exception_unsafe_history_guard(self):
        self.mutate("!r401ClearInProgress && !r401ClearUnsafe",
                    "!r401ClearInProgress && true")
        self.refuse()

    def test_stale_exception_cannot_reset_queued_flag(self):
        self.mutate(
            "              savePending = true;\n            }\n          }\n        }\n        finally",
            "              savePending = true;\n              r403AutosaveQueued = false;\n            }\n          }\n        }\n        finally")
        self.refuse("R407_EXCEPTION_CANNOT_RESET_QUEUE_FROM_OLD_SESSION")

    def test_old_worker_final_epoch_guard_required(self):
        self.mutate(
            "            if (issuedEpoch == r399SessionEpoch) {\n              if (r403AutosaveDirty)",
            "            if (true) {\n              if (r403AutosaveDirty)")
        self.refuse()

    def test_old_worker_rejected_executor_epoch_guard_required(self):
        self.mutate(
            "        if (issuedEpoch == r399SessionEpoch) {\n          r403AutosaveQueued",
            "        if (true) {\n          r403AutosaveQueued")
        self.refuse()

    def test_threadlocal_token_must_be_removed(self):
        self.mutate("r403WorkerEpoch.remove();","noOp();")
        self.refuse("R407_WORKER_EPOCH_TOKEN_LEAK")

    def test_both_persistence_fences_required(self):
        self.mutate(
            "Long verified = r403WorkerEpoch.get();",
            "Long verified = null;")
        self.refuse("R407_WORKER_EPOCH_WRITE_AND_ACK_FENCES_MISSING")

    def test_file_gate_must_remain(self):
        self.mutate(
            "synchronized (r401FileGate) {\n      Long epoch",
            "synchronized (otherGate) {\n      Long epoch")
        self.refuse()

    def test_clear_disk_receipt_must_be_preserved(self):
        self.mutate(
            "deleted = historyStore.clearWithReceipt();",
            "deleted = true;")
        self.refuse()

    def test_failed_clear_must_quarantine(self):
        self.mutate(
            "    if (!deleted) {\n      r401ClearUnsafe = true;",
            "    if (!deleted) {\n      noOp();")
        self.refuse()

    def test_explicit_panel_delete_remains_synchronous(self):
        self.mutate(
            "      mutation.run();\n      persistHistory();",
            "      mutation.run();\n      r403QueueAutosave();")
        self.refuse()

    def test_normal_request_must_stay_async(self):
        self.mutate(
            "  void requestSave() {\n    r403QueueAutosave();",
            "  void requestSave() {\n    persistHistory();")
        self.refuse()

    def test_stop_must_not_interrupt_executor(self):
        self.mutate("r403RetiredWorker.shutdown();",
                    "r403RetiredWorker.shutdownNow();")
        self.refuse()

    def test_source_delta_must_be_one_file(self):
        self.plugin=self.oldplugin
        self.write()
        self.refuse("R407_EXACT_ONE_SOURCE_AND_CLASS_REQUIRED")

    def test_class_delta_must_be_one_file(self):
        self.classes_after[gate.PLUGIN_CLS]=self.classes_before[gate.PLUGIN_CLS]
        self.write()
        self.refuse("R407_EXACT_ONE_SOURCE_AND_CLASS_REQUIRED")

    def test_unrelated_class_change_refused(self):
        self.classes_after[gate.P+"LootTrackerPanel.class"]=b"unexpected panel class"
        self.write()
        self.refuse("R407_EXACT_ONE_SOURCE_AND_CLASS_REQUIRED")

    def test_unrelated_source_change_refused(self):
        key=gate.PANEL
        (self.candidate/key).write_bytes(b"unexpected")
        self.refuse("R407_EXACT_ONE_SOURCE_AND_CLASS_REQUIRED")

    def test_sha_pinned_golden_original(self):
        with self.assertRaisesRegex(gate.Refused,"ARCHIVE_SHA_DRIFT"):
            gate.audit(
                kit=self.kit,kit_sha="0"*64,
                reference=self.reference,reference_sha=sha(self.reference),
                previous_sources=self.previous,previous_classes=self.prevcls,
                candidate_sources=self.candidate,candidate_classes=self.newcls,
                expected_sources=5,expected_classes=7)

    def args(self,out):
        return [
            "--kit",str(self.kit),"--kit-sha256",sha(self.kit),
            "--reference",str(self.reference),"--reference-sha256",sha(self.reference),
            "--previous-sources",str(self.previous),
            "--previous-classes",str(self.prevcls),
            "--candidate-sources",str(self.candidate),
            "--candidate-classes",str(self.newcls),
            "--expected-sources","5","--expected-classes","7",
            "--out",str(out)]

    def test_existing_receipt_never_overwritten(self):
        out=Path(self.temp.name)/"receipt.json"
        out.write_text("KEEP")
        self.assertEqual(gate.main(self.args(out)),2)
        self.assertEqual(out.read_text(),"KEEP")

    def test_cli_positive_is_unmerged(self):
        out=Path(self.temp.name)/"receipt.json"
        self.assertEqual(gate.main(self.args(out)),0)
        self.assertFalse(json.loads(out.read_text())["merge_approved"])

if __name__=="__main__":
    unittest.main()
