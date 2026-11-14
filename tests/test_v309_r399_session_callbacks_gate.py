"""R399 public-only SHA-pinned session callback/identity static regressions.

Synthetic fixtures only. No original/recovered game code or production I/O.
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


def import_file(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit=import_file("r399_static_gate",ROOT/"tools/r399/audit_session_callbacks.py")
prior=import_file("r396_public_synthetic",ROOT/"tests/test_v309_r396_shutdown_merge_gate.py")

# The real private Java methods are not included. This deliberately invented
# class has only the structural tokens the verifier is supposed to inspect.
FAKE_PLUGIN="""
class SyntheticLootTracker {
  long r399SessionEpoch;
  boolean r399AcceptingDrops;
  long r399RecordMutationSequence;
  void startUp() {
    historyLoaded = false;
    ++r399SessionEpoch;
    r399AcceptingDrops = true;
    instance = this;
    panel = this.injector.getInstance(LootTrackerPanel.class);
    if (r396PanelResetAfterVerifiedStop) { panel.clearRecords(); }
    boolean r398HasRetainedRecords = !panel.getRecordsOffEdt().isEmpty();
    r398UnreconciledPanelAtStart = r398HasRetainedRecords ||
         !pendingRecords.isEmpty() || !r396PreloadRecords.isEmpty();
  }
  void shutDown() {
    instance = null;
    ++r395HistoryGeneration;
    ++r399SessionEpoch;
    r399AcceptingDrops = false;
    boolean r396MergedBeforeStop = false;
    if (!historyLoaded) r396MergedBeforeStop = r396FinishStopMerge();
    if (!r396MergedBeforeStop) persistHistory();
  }
  void persistHistory() {
    if (!historyLoaded) {
       r395WriteDeferred = true;
       return;
    }
    panel.getRecordsOffEdt();
    r399PendingSnapshot = new ArrayList<>(pendingRecords);
    r399MutationAtSnapshot = r399RecordMutationSequence;
    merged.addAll(r399PendingSnapshot);
    if (historyStore.saveWithReceipt(merged)) {
       for (LootTrackerRecord saved : r399PendingSnapshot) {
          if (it.next() == saved) it.remove();
       }
       boolean r399NoNewDropSinceSnapshot =
          r399RecordMutationSequence == r399MutationAtSnapshot;
       if (r399NoNewDropSinceSnapshot) r396PreloadRecords.clear();
       r396LastCommitSucceeded = r399NoNewDropSinceSnapshot;
    }
  }
  void clearHistory() {
    ++r395HistoryGeneration;
    historyLoaded = true;
    r396PreloadRecords.clear();
    pendingRecords.clear();
  }
  void loadHistory() {
    r395RestoreInFlight = true;
    Thread worker = new Thread(() -> {
       stored = restoreStore.loadForMerge();
       if (stored == null) throw new RuntimeException();
       SwingUtilities.invokeLater(() -> {
          if (generation != r395HistoryGeneration) return;
          restorePanel.addRecords(stored);
          historyLoaded = true;
          r395RestoreInFlight = false;
          if (deferred) persistHistory();
       });
    });
    worker.setDaemon(true);
    worker.start();
  }
  boolean r396FinishStopMerge() {
    List<LootTrackerRecord> original = historyStore.loadForMerge();
    List<LootTrackerRecord> combined = new ArrayList<>(original);
    r399MergedPreload = new ArrayList<>(r396PreloadRecords);
    combined.addAll(r399MergedPreload);
    boolean committed = historyStore.saveWithReceipt(combined);
    if (!committed) return false;
    r396PreloadRecords.clear();
    for (LootTrackerRecord saved : r399MergedPreload) {
        if (it.next() == saved) it.remove();
    }
    r396PanelResetAfterVerifiedStop = true;
    return true;
  }
  void addLoot() {
    final long r399DropSessionEpoch;
    synchronized (r395HistoryGate) {
       if (!r399AcceptingDrops || instance != this) {return;}
       r399DropSessionEpoch = r399SessionEpoch;
       ++r399RecordMutationSequence;
       pendingRecords.add(record);
    }
    SwingUtilities.invokeLater(() -> {
       synchronized (r395HistoryGate) {
          if (!r399AcceptingDrops ||
              r399DropSessionEpoch != r399SessionEpoch ||
              instance != this) {return;}
       }
       panel.add(record);
       synchronized (r395HistoryGate) {
          for (Iterator it = pendingRecords.iterator(); it.hasNext();) {
             if (it.next() == record) {it.remove();}
          }
       }
       requestSave();
    });
  }
}
"""
FAKE_STORE=prior.FAKE_STORE


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SessionGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.kit=self.root/"kit.zip"
        self.ref=self.root/"reference.jar"
        self.old_src=self.root/"r398-source"
        self.old_cls=self.root/"r398-classes"
        self.new_src=self.root/"r399-source"
        self.new_cls=self.root/"r399-classes"
        self.orig_sources={
            audit.PLUGIN:b"class OldPrivateSynthetic {}",
            audit.r396.STORE:b"class OriginalSyntheticStore {}"}
        self.baseline_classes={
            audit.CLASS:b"old synthetic class",
            audit.r396.STORE[:-5]+".class":b"old synthetic store class"}
        self.previous_plugin=prior.FAKE_PLUGIN.encode("utf8")
        self.current_plugin=FAKE_PLUGIN.encode("utf8")
        self.previous_store=FAKE_STORE.encode("utf8")
        self.current_store=FAKE_STORE.encode("utf8")
        self.previous_plugin_class=b"R398 synthetic class"
        self.current_plugin_class=b"R399 synthetic class"
        self.write()

    @staticmethod
    def populate(root,files):
        root.mkdir(parents=True,exist_ok=True)
        for path in root.rglob("*"):
            if path.is_file():path.unlink()
        for name,data in files.items():
            full=root/name
            full.parent.mkdir(parents=True,exist_ok=True)
            full.write_bytes(data)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            for name,body in self.orig_sources.items():
                z.writestr("source/"+name,body)
        with ZipFile(self.ref,"w") as z:
            for name,body in self.baseline_classes.items():
                z.writestr(name,body)
        self.populate(self.old_src,{audit.PLUGIN:self.previous_plugin,
                                    audit.r396.STORE:self.previous_store})
        self.populate(self.new_src,{audit.PLUGIN:self.current_plugin,
                                    audit.r396.STORE:self.current_store})
        self.populate(self.old_cls,{audit.CLASS:self.previous_plugin_class,
                                    audit.r396.STORE[:-5]+".class":b"same synthetic store"})
        self.populate(self.new_cls,{audit.CLASS:self.current_plugin_class,
                                    audit.r396.STORE[:-5]+".class":b"same synthetic store"})

    def run_gate(self):
        return audit.audit(
            kit=self.kit,kit_sha=sha(self.kit),
            reference=self.ref,reference_sha=sha(self.ref),
            previous_sources=self.old_src,previous_classes=self.old_cls,
            candidate_sources=self.new_src,candidate_classes=self.new_cls,
            expected_sources=2,expected_classes=2)

    def change(self,old,new):
        old=old.encode("utf8")
        self.assertIn(old,self.current_plugin)
        self.current_plugin=self.current_plugin.replace(old,new.encode("utf8"))
        self.write()

    def expect_refusal(self,reason=None):
        if reason:
            with self.assertRaisesRegex(audit.Refused,reason):self.run_gate()
        else:
            with self.assertRaises(audit.Refused):self.run_gate()

    def test_positive_gate_and_release_flags(self):
        result=self.run_gate()
        self.assertEqual(result["status"],"R399_PRIVATE_SESSION_CALLBACK_STATIC_GATE_PASS")
        self.assertEqual(result["modified_source_count_vs_r398"],1)
        self.assertEqual(result["modified_class_count_vs_r398"],1)
        for field in ("normal_host_launch_authorized","real_client_queued_callbacks_tested",
                      "all_panel_pending_snapshot_races_resolved",
                      "private_source_release_approved","merge_approved"):
            self.assertFalse(result[field])

    def test_no_source_leak(self):
        serialized=json.dumps(self.run_gate())
        self.assertNotIn("SwingUtilities.invokeLater",serialized)
        self.assertNotIn("R399 synthetic class",serialized)
        self.assertNotIn("kit.zip",serialized)

    def test_session_field_required(self):
        self.change("long r399SessionEpoch;","long missingEpoch;")
        self.expect_refusal("SESSION_OR_MUTATION_FIELD_MISSING")

    def test_mutation_counter_field_required(self):
        self.change("long r399RecordMutationSequence;","long unrelated;")
        self.expect_refusal("SESSION_OR_MUTATION_FIELD_MISSING")

    def test_start_must_open_admission(self):
        self.change("r399AcceptingDrops = true;","r399AcceptingDrops = false;")
        self.expect_refusal("START_EPOCH_ADMISSION_ORDER_DRIFT")

    def test_stop_must_close_admission(self):
        self.change("r399AcceptingDrops = false;","r399AcceptingDrops = true;")
        self.expect_refusal("STOP_EPOCH_CLOSE_BEFORE_MERGE_MISSING")

    def test_stop_must_bump_epoch(self):
        self.change("++r399SessionEpoch;\n    r399AcceptingDrops = false;",
                    "r399SessionEpoch;\n    r399AcceptingDrops = false;")
        self.expect_refusal("STOP_EPOCH_CLOSE_BEFORE_MERGE_MISSING")

    def test_drop_admission_guard_required(self):
        self.change("if (!r399AcceptingDrops || instance != this) {return;}",
                    "if (false) {return;}")
        self.expect_refusal("DROP_SESSION_CALLBACK_GUARD_MISSING_OR_REORDERED")

    def test_stale_callback_epoch_check_required(self):
        self.change("r399DropSessionEpoch != r399SessionEpoch",
                    "r399DropSessionEpoch == r399SessionEpoch")
        self.expect_refusal("DROP_SESSION_CALLBACK_GUARD_MISSING_OR_REORDERED")

    def test_stale_callback_must_return(self):
        self.change("instance != this) {return;}\n       }\n       panel.add(record);",
                    "instance != this) {noop();}\n       }\n       panel.add(record);")
        self.expect_refusal("STALE_CALLBACK_NOT_RETURNED")

    def test_no_late_save_before_guard(self):
        self.change("panel.add(record);\n       synchronized (r395HistoryGate)",
                    "requestSave();\n       panel.add(record);\n       synchronized (r395HistoryGate)")
        # Generic verifier must not silently approve late saves before ack.
        # Source verifier explicitly checks ordering of first requestSave.
        self.expect_refusal()

    def test_pending_removal_uses_identity(self):
        self.change("if (it.next() == record)","if (it.next().equals(record))")
        self.expect_refusal("DROP_SESSION_CALLBACK_GUARD_MISSING_OR_REORDERED")

    def test_pending_callback_requires_gate(self):
        self.change("panel.add(record);\n       synchronized (r395HistoryGate)",
                    "panel.add(record);\n       noop();\n       // synchronized (r395HistoryGate)")
        self.expect_refusal()

    def test_stop_merge_must_snapshot_preload(self):
        self.change("r399MergedPreload = new ArrayList<>(r396PreloadRecords);",
                    "r399MergedPreload = new ArrayList<>();")
        self.expect_refusal("SHUTDOWN_COMMIT_IDENTITY_DRAIN_MISSING")

    def test_stop_ack_removal_uses_identity(self):
        self.change("if (it.next() == saved)","if (it.next().equals(saved))")
        self.expect_refusal("SHUTDOWN_COMMIT_IDENTITY_DRAIN_MISSING")

    def test_normal_save_uses_mutation_ack(self):
        self.change("r396LastCommitSucceeded = r399NoNewDropSinceSnapshot;",
                    "r396LastCommitSucceeded = true;")
        self.expect_refusal("INHERITED_STRUCTURE_NORMALIZATION_DRIFT")

    def test_normal_save_snapshot_required(self):
        self.change("r399PendingSnapshot = new ArrayList<>(pendingRecords);",
                    "r399PendingSnapshot = new ArrayList<>();")
        self.expect_refusal("NORMAL_SAVE_ACK_IDENTITY_OR_MUTATION_GUARD_DRIFT")

    def test_inflight_pending_provenance_required(self):
        self.change("!pendingRecords.isEmpty() || !r396PreloadRecords.isEmpty()",
                    "false || !r396PreloadRecords.isEmpty()")
        self.expect_refusal("PREVIOUS_UNCOMMITTED_PENDING_NOT_PROTECTED")

    def test_unexpected_modified_source_refused(self):
        self.current_store+=b"\n//unexpected modification"
        self.write()
        self.expect_refusal("SOURCE_CHANGE_SCOPE_DRIFT")

    def test_unexpected_modified_class_refused(self):
        self.current_plugin_class=self.previous_plugin_class
        self.write()
        self.expect_refusal("CLASS_CHANGE_SCOPE_DRIFT")

    def test_hash_drift_refused(self):
        with self.assertRaisesRegex(audit.Refused,"ARCHIVE_SHA_DRIFT"):
            audit.audit(
                kit=self.kit,kit_sha="0"*64,
                reference=self.ref,reference_sha=sha(self.ref),
                previous_sources=self.old_src,previous_classes=self.old_cls,
                candidate_sources=self.new_src,candidate_classes=self.new_cls,
                expected_sources=2,expected_classes=2)

    def cli_args(self,out):
        return ["--kit",str(self.kit),"--kit-sha256",sha(self.kit),
                "--reference",str(self.ref),"--reference-sha256",sha(self.ref),
                "--previous-sources",str(self.old_src),
                "--previous-classes",str(self.old_cls),
                "--candidate-sources",str(self.new_src),
                "--candidate-classes",str(self.new_cls),
                "--expected-sources","2","--expected-classes","2",
                "--out",str(out)]

    def test_refuse_existing_output(self):
        out=self.root/"report.json"
        out.write_text("KEEP",encoding="utf8")
        self.assertEqual(audit.main(self.cli_args(out)),2)
        self.assertEqual(out.read_text("utf8"),"KEEP")

    def test_positive_cli(self):
        out=self.root/"report.json"
        self.assertEqual(audit.main(self.cli_args(out)),0)
        self.assertFalse(json.loads(out.read_text("utf8"))["merge_approved"])


if __name__=="__main__":
    unittest.main()
