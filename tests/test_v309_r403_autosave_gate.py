"""R403 public synthetic integrity and old-session autosave gate tests."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("r403_public_gate",ROOT/"tools/r403/audit_coalesced_autosave.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

# Deliberately fabricated source; not reconstructed or derived Java.
SYNTH_PLUGIN="""
class FabricatedLoot {
  private volatile boolean savePending;
  private volatile long lastPersistAt;
  private java.util.concurrent.ExecutorService r403AutosaveExecutor;
  private boolean r403AutosaveQueued;
  private boolean r403AutosaveDirty;
  private ThreadLocal<Long> r403WorkerEpoch;
  void startUp() {
    ++r399SessionEpoch;
    r399AcceptingDrops = true;
    r403AutosaveQueued = false;
    r403AutosaveDirty = false;
    r403AutosaveExecutor = java.util.concurrent.Executors.newSingleThreadExecutor(task -> {
      Thread worker = new Thread(task,"synthetic");
      worker.setDaemon(true);
      return worker;
    });
  }
  void shutDown() {
    ++r399SessionEpoch;
    r399AcceptingDrops = false;
    r403RetiredWorker.shutdown();
    r396FinishStopMerge();
    persistHistory();
  }
  void requestSave() {
    if (!config.rememberLoot() || historyStore == null) return;
    if (now - lastPersistAt < AUTOSAVE_INTERVAL_MS) {
      savePending = true;
      return;
    }
    r403QueueAutosave();
  }
  void onGameTick(GameTick event) {
    if (savePending && timeSinceLastCommit > AUTOSAVE_INTERVAL_MS) {
      r403QueueAutosave();
    }
    scanForLootKeyInterface();
  }
  void r403QueueAutosave() {
    synchronized (r395HistoryGate) {
      executor = r403AutosaveExecutor;
      if (executor == null || !r399AcceptingDrops || instance != this) return;
      if (!historyLoaded) {savePending=true;return;}
      if (r403AutosaveQueued) {
        r403AutosaveDirty = true;
        return;
      }
      r403AutosaveQueued = true;
      r403AutosaveDirty = false;
      issuedEpoch = r399SessionEpoch;
    }
    try {
      executor.execute(() -> {
        try {
          if (issuedEpoch != r399SessionEpoch) return;
          r396LastCommitSucceeded = false;
          r403WorkerEpoch.set(issuedEpoch);
          persistHistory();
          if (!r396LastCommitSucceeded) savePending = true;
        } finally {
          r403WorkerEpoch.remove();
          if (issuedEpoch == r399SessionEpoch) {
            if (r403AutosaveDirty) savePending=true;
            r403AutosaveQueued = false;
          }
        }
      });
    } catch (java.util.concurrent.RejectedExecutionException error) {
      savePending = true;
    }
  }
  void persistHistory() {
    synchronized (r401FileGate) {
      synchronized (r395HistoryGate) {
        final Long r403ExpectedEpoch = r403WorkerEpoch.get();
        if (r403ExpectedEpoch != null &&
            (r403ExpectedEpoch.longValue() != r399SessionEpoch ||
            !r399AcceptingDrops || instance != this)) return;
      }
      r401Committed = historyStore.saveWithReceipt(merged);
    }
    if (r401Committed) {
      synchronized(r395HistoryGate) {
        final Long r403ExpectedEpoch = r403WorkerEpoch.get();
        if (r403ExpectedEpoch != null &&
            (r403ExpectedEpoch.longValue() != r399SessionEpoch ||
            !r399AcceptingDrops || instance != this)) return;
      }
    }
  }
  void r402ApplyPanelDeletion(Runnable mutation) {
    synchronized (r401FileGate) {
      mutation.run();
      persistHistory();
      if (!r402EditWriteReceipt) return;
    }
  }
  void onGameStateChanged(GameStateChanged event) {
    switch (event.getGameState()) {
      case LOGIN_SCREEN:
      case LOGGING_IN:
      case CONNECTION_LOST:
        persistHistory();
        break;
      case LOGGED_IN:
        loadHistory();
        break;
    }
  }
}
"""

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class R403WorkerGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        r=Path(self.temp.name)
        self.kit=r/"kit.zip"
        self.ref=r/"reference.jar"
        self.prior_src=r/"old_source"
        self.prior_cls=r/"old_class"
        self.new_src=r/"new_source"
        self.new_cls=r/"new_class"
        self.candidate=SYNTH_PLUGIN.encode("utf8")
        self.prior=b"class PriorSyntheticPlugin {}"
        self.panel=b"synthetic prior panel changed"
        self.store=b"synthetic prior store changed"
        self.class_old=b"synthetic old plugin class"
        self.class_new=b"synthetic new plugin class"
        self.write()

    @staticmethod
    def files(folder,mapping):
        folder.mkdir(parents=True,exist_ok=True)
        for old in folder.rglob("*"):
            if old.is_file():old.unlink()
        for path,data in mapping.items():
            f=folder/path
            f.parent.mkdir(parents=True,exist_ok=True)
            f.write_bytes(data)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            for name in (audit.PLUGIN,audit.PANEL,audit.STORE):
                z.writestr("source/"+name,b"golden synthetic source")
        with ZipFile(self.ref,"w") as z:
            for name in (audit.PLUGIN,audit.PANEL,audit.STORE):
                z.writestr(name[:-5]+".class",b"golden synthetic class")
        self.files(self.prior_src,{
            audit.PLUGIN:self.prior,audit.PANEL:self.panel,audit.STORE:self.store})
        self.files(self.new_src,{
            audit.PLUGIN:self.candidate,audit.PANEL:self.panel,audit.STORE:self.store})
        self.files(self.prior_cls,{
            audit.CLASS:self.class_old,audit.PANEL[:-5]+".class":b"synthetic panel class",
            audit.STORE[:-5]+".class":b"synthetic store class"})
        self.files(self.new_cls,{
            audit.CLASS:self.class_new,audit.PANEL[:-5]+".class":b"synthetic panel class",
            audit.STORE[:-5]+".class":b"synthetic store class"})

    def validate(self):
        return audit.audit(
            kit=self.kit,kit_sha=sha(self.kit),
            reference=self.ref,reference_sha=sha(self.ref),
            previous_sources=self.prior_src,previous_classes=self.prior_cls,
            candidate_sources=self.new_src,candidate_classes=self.new_cls,
            expected_sources=3,expected_classes=3)

    def change(self,old,new):
        a=old.encode("utf8")
        self.assertIn(a,self.candidate)
        self.candidate=self.candidate.replace(a,new.encode("utf8"))
        self.write()

    def refusal(self,code=None):
        if code:
            with self.assertRaisesRegex(audit.Refused,code):self.validate()
        else:
            with self.assertRaises(audit.Refused):self.validate()

    def test_valid_synthetic_release_gates_closed(self):
        result=self.validate()
        self.assertEqual(result["status"],"R403_PRIVATE_COALESCED_AUTOSAVE_STATIC_GATE_PASS")
        self.assertEqual(result["changed_class_count_vs_r402"],1)
        for flag in ("actual_client_thread_latency_measured","all_save_callers_background_only",
                     "real_game_runtime_executed","crash_recovery_durability_proven",
                     "normal_host_launch_authorized","merge_approved"):
            self.assertFalse(result[flag])

    def test_receipt_excludes_source(self):
        r=json.dumps(self.validate())
        self.assertNotIn("FabricatedLoot",r)
        self.assertNotIn("ExecutorService",r)

    def test_pending_visibility_required(self):
        self.change("volatile boolean savePending;","boolean savePending;")
        self.refusal("R403_SAVE_PENDING_NOT_VOLATILE")

    def test_last_commit_visibility_required(self):
        self.change("volatile long lastPersistAt;","long lastPersistAt;")
        self.refusal("R403_LAST_SAVE_NOT_VOLATILE")

    def test_worker_field_required(self):
        self.change("boolean r403AutosaveQueued;","boolean wrongQueued;")
        self.refusal("R403_WORKER_FIELD_MISSING")

    def test_startup_daemon_required(self):
        self.change("worker.setDaemon(true);","worker.setDaemon(false);")
        self.refusal("R403_WORKER_NOT_DAEMON")

    def test_startup_worker_required(self):
        self.change("java.util.concurrent.Executors.newSingleThreadExecutor(",
                    "java.util.concurrent.Executors.newFixedThreadPool(")
        self.refusal("R403_AUTOSAVE_LIFECYCLE_ORDER_DRIFT")

    def test_stop_must_retire_worker(self):
        self.change("r403RetiredWorker.shutdown();","noop();")
        self.refusal("R403_AUTOSAVE_LIFECYCLE_ORDER_DRIFT")

    def test_stop_must_not_interrupt_commit(self):
        self.change("r403RetiredWorker.shutdown();","r403RetiredWorker.shutdownNow();")
        self.refusal()

    def test_request_cannot_save_on_caller(self):
        self.change("    r403QueueAutosave();\n  }\n  void onGameTick",
                    "    persistHistory();\n  }\n  void onGameTick")
        self.refusal()

    def test_tick_cannot_save_on_client_thread(self):
        self.change("      r403QueueAutosave();\n    }\n    scanForLootKeyInterface();",
                    "      persistHistory();\n    }\n    scanForLootKeyInterface();")
        self.refusal()

    def test_coalescing_on_busy_worker_required(self):
        self.change("r403AutosaveDirty = true;","r403AutosaveDirty = false;")
        self.refusal()

    def test_session_epoch_captured(self):
        self.change("issuedEpoch = r399SessionEpoch","issuedEpoch = 0")
        self.refusal()

    def test_worker_receipt_retry_required(self):
        self.change("if (!r396LastCommitSucceeded) savePending = true;",
                    "if (!r396LastCommitSucceeded) noop();")
        self.refusal("R403_AUTOSAVE_LIFECYCLE_ORDER_DRIFT")

    def test_threadlocal_must_be_cleared(self):
        self.change("r403WorkerEpoch.remove();","noop();")
        self.refusal("R403_AUTOSAVE_LIFECYCLE_ORDER_DRIFT")

    def test_rejected_executor_must_be_handled(self):
        self.change("java.util.concurrent.RejectedExecutionException",
                    "java.io.IOException")
        self.refusal("REJECTION_NOT_HANDLED")

    def test_write_epoch_guard_required(self):
        self.change("r403ExpectedEpoch.longValue() != r399SessionEpoch",
                    "r403ExpectedEpoch.longValue() == r399SessionEpoch")
        self.refusal("STALE_BACKGROUND_SESSION_CAN_WRITE")

    def test_write_and_ack_both_fenced(self):
        self.change("final Long r403ExpectedEpoch = r403WorkerEpoch.get();",
                    "final Long r403ExpectedEpoch = null;")
        self.refusal("WORKER_EPOCH_MUST_GUARD_WRITE_AND_ACK")

    def test_explicit_deletes_remain_synchronous(self):
        self.change("      persistHistory();\n      if (!r402EditWriteReceipt)",
                    "      r403QueueAutosave();\n      if (!r402EditWriteReceipt)")
        self.refusal("R403_AUTOSAVE_LIFECYCLE_ORDER_DRIFT")

    def test_logout_remains_synchronous(self):
        self.change("      case CONNECTION_LOST:\n        persistHistory();",
                    "      case CONNECTION_LOST:\n        r403QueueAutosave();")
        self.refusal("R403_AUTOSAVE_LIFECYCLE_ORDER_DRIFT")

    def test_changed_source_scope(self):
        self.candidate=self.prior
        self.write()
        self.refusal("ONE_PLUGIN_SOURCE_CLASS_DELTA_REQUIRED")

    def test_changed_class_scope(self):
        self.class_new=self.class_old
        self.write()
        self.refusal("ONE_PLUGIN_SOURCE_CLASS_DELTA_REQUIRED")

    def test_reference_archive_pin(self):
        with self.assertRaisesRegex(audit.Refused,"ARCHIVE_SHA_DRIFT"):
            audit.audit(
                kit=self.kit,kit_sha="0"*64,
                reference=self.ref,reference_sha=sha(self.ref),
                previous_sources=self.prior_src,previous_classes=self.prior_cls,
                candidate_sources=self.new_src,candidate_classes=self.new_cls,
                expected_sources=3,expected_classes=3)

    def args(self,out):
        return [
            "--kit",str(self.kit),"--kit-sha256",sha(self.kit),
            "--reference",str(self.ref),"--reference-sha256",sha(self.ref),
            "--previous-sources",str(self.prior_src),
            "--previous-classes",str(self.prior_cls),
            "--candidate-sources",str(self.new_src),
            "--candidate-classes",str(self.new_cls),
            "--expected-sources","3","--expected-classes","3","--out",str(out)]

    def test_no_overwrite_existing_report(self):
        out=Path(self.temp.name)/"receipt.json"
        out.write_text("KEEP")
        self.assertEqual(audit.main(self.args(out)),2)
        self.assertEqual(out.read_text(),"KEEP")

    def test_positive_cli_one_new_receipt(self):
        out=Path(self.temp.name)/"receipt.json"
        self.assertEqual(audit.main(self.args(out)),0)
        self.assertFalse(json.loads(out.read_text())["merge_approved"])

if __name__=="__main__":
    unittest.main()
