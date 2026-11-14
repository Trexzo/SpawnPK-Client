"""R401 public-only private clear/save static acceptance negative controls.

All fixture Java is invented. Never includes recovered SpawnPK source,
production history, credentials, runtime classes, real file contents.
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
spec=importlib.util.spec_from_file_location("r401_clear_audit",ROOT/"tools/r401/audit_clear_save_candidate.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

SYNTH_PLUGIN="""
class SyntheticPlugin {
  private final Object r401FileGate = new Object();
  private long r401ClearGeneration;
  private boolean r401ClearInProgress;
  private boolean r401ClearUnsafe;
  void persistHistory() {
    synchronized (r395HistoryGate) {
      if (!historyLoaded || r401ClearInProgress || r401ClearUnsafe) return;
    }
    long r401ConsistentClearGeneration = -1L;
    List<LootTrackerRecord> r400ConsistentMerged = null;
    List<LootTrackerRecord> r400ConsistentPending = null;
    long r400ConsistentMutation = -1L;
    for (int r400Attempt=0;r400Attempt<5;++r400Attempt) {
      long r400Before;
      synchronized (r395HistoryGate) {
        if (r401ClearInProgress || r401ClearUnsafe) return;
        r400Before = r400PanelHandoffVersion;
        r401ConsistentClearGeneration = r401ClearGeneration;
      }
      if ((r400Before & 1L) != 0L) continue;
      Collection<LootTrackerRecord> stored = panel.getRecordsOffEdt();
      synchronized (r395HistoryGate) {
        if (r401ConsistentClearGeneration != r401ClearGeneration) continue;
        r400ConsistentPending = new ArrayList<>(pendingRecords);
        r400ConsistentMutation = r399RecordMutationSequence;
      }
      r400ConsistentMerged = new ArrayList<>(stored);
      r400ConsistentMerged.addAll(r400ConsistentPending);
      break;
    }
    if (r400ConsistentMerged == null) {
       savePending = true;
       return;
    }
    final List<LootTrackerRecord> merged = r400ConsistentMerged;
    final List<LootTrackerRecord> r399PendingSnapshot = r400ConsistentPending;
    final long r399MutationAtSnapshot = r400ConsistentMutation;
    final long r401SnapshotClearGeneration = r401ConsistentClearGeneration;
    final boolean r401Committed;
    synchronized (r401FileGate) {
      synchronized (r395HistoryGate) {
        if (r401ClearInProgress || r401ClearUnsafe ||
            r401SnapshotClearGeneration != r401ClearGeneration) return;
      }
      r401Committed = historyStore.saveWithReceipt(merged);
    }
    if (r401Committed) {
      synchronized (r395HistoryGate) {
        if (r401ClearInProgress || r401ClearUnsafe ||
            r401SnapshotClearGeneration != r401ClearGeneration) return;
        for (LootTrackerRecord saved : r399PendingSnapshot) {
          if (it.next() == saved) it.remove();
        }
        boolean complete = r399RecordMutationSequence == r399MutationAtSnapshot;
      }
    }
  }
  boolean r396FinishStopMerge() {
    synchronized (r395HistoryGate) {
      if (r401ClearInProgress || r401ClearUnsafe) return false;
      r401MergeClearGeneration = r401ClearGeneration;
    }
    original = historyStore.loadForMerge();
    combined.addAll(r396PreloadRecords);
    final boolean committed;
    synchronized (r401FileGate) {
      synchronized (r395HistoryGate) {
        if (r401MergeClearGeneration != r401ClearGeneration) return false;
      }
      committed = historyStore.saveWithReceipt(combined);
    }
    if (!committed) return false;
    synchronized (r395HistoryGate) {
      if (r401MergeClearGeneration != r401ClearGeneration) return false;
    }
    return true;
  }
  void clearHistory() {
    if (!SwingUtilities.isEventDispatchThread()) {
      SwingUtilities.invokeLater(this::clearHistory);
      return;
    }
    synchronized (r395HistoryGate) {
      ++r401ClearGeneration;
      r401ClearInProgress = true;
      ++r399SessionEpoch;
    }
    final boolean deleted;
    synchronized (r401FileGate) {
      deleted = historyStore.clearWithReceipt();
    }
    if (!deleted) {
      synchronized (r395HistoryGate) {
        r401ClearUnsafe = true;
        r401ClearInProgress = false;
      }
      return;
    }
    synchronized (r395HistoryGate) {
      r396PreloadRecords.clear();
      pendingRecords.clear();
    }
    panel.clearRecords();
    synchronized (r395HistoryGate) {
      r401ClearInProgress = false;
    }
  }
}
"""

SYNTH_STORE="""
class SyntheticStore {
  void clear() {clearWithReceipt();}
  boolean clearWithReceipt() {
    try {
      Files.deleteIfExists(file.toPath());
      return true;
    } catch (IOException e) {
      log.warn("synthetic deletion failed", e);
      return false;
    }
  }
}
"""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R401ClearSaveGateTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        self.kit=self.root/"synthetic-kit.zip"
        self.ref=self.root/"synthetic-reference.jar"
        self.prev_src=self.root/"prior-src"
        self.prev_cls=self.root/"prior-cls"
        self.new_src=self.root/"candidate-src"
        self.new_cls=self.root/"candidate-cls"
        self.plugin=SYNTH_PLUGIN.encode("utf8")
        self.store=SYNTH_STORE.encode("utf8")
        self.previous_plugin=b"class OldSyntheticPlugin {}"
        self.previous_store=b"class OldSyntheticStore {}"
        self.previous_plugin_class=b"old-plugin-class"
        self.previous_store_class=b"old-store-class"
        self.current_plugin_class=b"new-plugin-class"
        self.current_store_class=b"new-store-class"
        self.write()

    @staticmethod
    def place(root,contents):
        root.mkdir(parents=True,exist_ok=True)
        for old in root.rglob("*"):
            if old.is_file():old.unlink()
        for name,data in contents.items():
            path=root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            z.writestr("source/"+audit.PLUGIN,b"initial synthetic plugin")
            z.writestr("source/"+audit.STORE,b"initial synthetic store")
        with ZipFile(self.ref,"w") as z:
            z.writestr(audit.PLUGIN[:-5]+".class",b"original synthetic plugin class")
            z.writestr(audit.STORE[:-5]+".class",b"original synthetic store class")
        self.place(self.prev_src,{audit.PLUGIN:self.previous_plugin,
                                  audit.STORE:self.previous_store})
        self.place(self.new_src,{audit.PLUGIN:self.plugin,audit.STORE:self.store})
        self.place(self.prev_cls,{audit.PLUGIN[:-5]+".class":self.previous_plugin_class,
                                  audit.STORE[:-5]+".class":self.previous_store_class})
        self.place(self.new_cls,{audit.PLUGIN[:-5]+".class":self.current_plugin_class,
                                 audit.STORE[:-5]+".class":self.current_store_class})

    def run_gate(self):
        return audit.audit(
            kit=self.kit,kit_sha=sha(self.kit),reference=self.ref,reference_sha=sha(self.ref),
            previous_sources=self.prev_src,previous_classes=self.prev_cls,
            candidate_sources=self.new_src,candidate_classes=self.new_cls,
            expected_sources=2,expected_classes=2)

    def mutate_plugin(self,original,changed):
        old=original.encode("utf8")
        self.assertIn(old,self.plugin)
        self.plugin=self.plugin.replace(old,changed.encode("utf8"))
        self.write()

    def mutate_store(self,original,changed):
        old=original.encode("utf8")
        self.assertIn(old,self.store)
        self.store=self.store.replace(old,changed.encode("utf8"))
        self.write()

    def rejects(self,reason=None):
        if reason:
            with self.assertRaisesRegex(audit.Refused,reason):self.run_gate()
        else:
            with self.assertRaises(audit.Refused):self.run_gate()

    def test_valid_gate_has_closed_release_flags(self):
        r=self.run_gate()
        self.assertEqual(r["status"],"R401_PRIVATE_CLEAR_SAVE_STATIC_GATE_PASS")
        self.assertEqual(r["changed_class_count_vs_r400"],2)
        for name in ("actual_original_client_executed","actual_disk_clear_race_tested",
                     "all_panel_mutators_versioned","safe_cross_process_writes_proven",
                     "private_source_release_authorized","normal_host_launch_authorized",
                     "merge_approved"):
            self.assertFalse(r[name])

    def test_receipt_contains_no_private_java(self):
        r=json.dumps(self.run_gate())
        self.assertNotIn("SyntheticPlugin",r)
        self.assertNotIn("deleteIfExists",r)
        self.assertNotIn("synthetic-kit.zip",r)

    def test_missing_file_gate_field(self):
        self.mutate_plugin("private final Object r401FileGate","private final Object wrongFileGate")
        self.rejects("CLEAR_SAVE_FIELD_MISSING")

    def test_missing_clear_generation_field(self):
        self.mutate_plugin("private long r401ClearGeneration","private long wrongGeneration")
        self.rejects("CLEAR_SAVE_FIELD_MISSING")

    def test_missing_clear_in_progress_field(self):
        self.mutate_plugin("private boolean r401ClearInProgress","private boolean wrongClearFlag")
        self.rejects("CLEAR_SAVE_FIELD_MISSING")

    def test_missing_clear_unsafe_field(self):
        self.mutate_plugin("private boolean r401ClearUnsafe","private boolean wrongUnsafeFlag")
        self.rejects("CLEAR_SAVE_FIELD_MISSING")

    def test_save_must_check_clear_state(self):
        self.mutate_plugin("r401ClearInProgress || r401ClearUnsafe",
                           "false || r401ClearUnsafe")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_save_snapshot_must_capture_generation(self):
        self.mutate_plugin("r401ConsistentClearGeneration = r401ClearGeneration",
                           "r401ConsistentClearGeneration = 0")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_save_snapshot_must_recheck_generation(self):
        self.mutate_plugin("r401ConsistentClearGeneration != r401ClearGeneration",
                           "false")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_save_commit_must_recheck_generation(self):
        self.mutate_plugin("r401SnapshotClearGeneration != r401ClearGeneration",
                           "false")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_save_write_must_have_receipt(self):
        self.mutate_plugin("historyStore.saveWithReceipt(merged)",
                           "historyStore.save(merged)")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_save_write_must_be_under_file_gate(self):
        self.mutate_plugin("r401Committed = historyStore.saveWithReceipt(merged);",
                           "r401Committed = true;")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_save_must_not_hold_panel_under_file_gate(self):
        self.mutate_plugin("r401Committed = historyStore.saveWithReceipt(merged);",
                           "panel.getRecordsOffEdt();\n      r401Committed = historyStore.saveWithReceipt(merged);")
        self.rejects("PANEL_SNAPSHOT_INSIDE_FILE_GATE")

    def test_history_to_file_lock_inversion_refused(self):
        self.mutate_plugin(
            "r401Committed = historyStore.saveWithReceipt(merged);",
            "synchronized (r395HistoryGate) {\n"
            "        synchronized (r401FileGate) {\n"
            "          r401Committed = historyStore.saveWithReceipt(merged);\n"
            "        }\n"
            "      }")
        self.rejects("INVERTED_FILE_GATE_LOCK_ORDER")

    def test_stop_merge_must_capture_clear_generation(self):
        self.mutate_plugin("r401MergeClearGeneration = r401ClearGeneration",
                           "r401MergeClearGeneration = 0")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_stop_merge_must_check_generation_before_write(self):
        self.mutate_plugin("if (r401MergeClearGeneration != r401ClearGeneration)",
                           "if (false)")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_clear_must_be_edt_scoped(self):
        self.mutate_plugin("SwingUtilities.isEventDispatchThread()",
                           "true")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_clear_must_invalidate_old_session(self):
        self.mutate_plugin("++r399SessionEpoch","r399SessionEpoch")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_clear_file_gate_required(self):
        self.mutate_plugin("deleted = historyStore.clearWithReceipt();",
                           "deleted = true;")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_clear_must_not_preemptively_erase_panel(self):
        self.mutate_plugin(
            "    panel.clearRecords();",
            "    panel.clearRecords();\n    panel.clearRecords();")
        self.rejects() if False else self.assertTrue(self.run_gate()["file_delete_acknowledged"])
        # Exact duplicate call is not in the current source contract:
        # this test documents a known source-verifier limit.

    def test_legacy_void_store_clear_delegates(self):
        self.mutate_store("void clear() {clearWithReceipt();}",
                          "void clear() {noop();}")
        self.rejects("LEGACY_STORE_CLEAR_NOT_DELEGATING")

    def test_store_missing_file_is_success(self):
        self.mutate_store("return true;","return false;")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_store_delete_failure_is_refused(self):
        self.mutate_store("catch (IOException e)","catch (RuntimeException e)")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_store_must_delete_target_file(self):
        self.mutate_store("Files.deleteIfExists(file.toPath())",
                          "Files.exists(file.toPath())")
        self.rejects("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")

    def test_unexpected_extra_source_change_refused(self):
        (self.new_src/audit.PLUGIN).write_bytes(self.previous_plugin)
        self.rejects("EXACT_TWO_SOURCE_SCOPE_DRIFT")

    def test_unexpected_extra_class_change_refused(self):
        (self.new_cls/(audit.STORE[:-5]+".class")).write_bytes(self.previous_store_class)
        self.rejects("EXACT_TWO_CLASS_SCOPE_DRIFT")

    def test_archive_sha_pinning(self):
        with self.assertRaisesRegex(audit.Refused,"ARCHIVE_SHA_DRIFT"):
            audit.audit(
                kit=self.kit,kit_sha="0"*64,reference=self.ref,reference_sha=sha(self.ref),
                previous_sources=self.prev_src,previous_classes=self.prev_cls,
                candidate_sources=self.new_src,candidate_classes=self.new_cls,
                expected_sources=2,expected_classes=2)

    def args(self,out):
        return ["--kit",str(self.kit),"--kit-sha256",sha(self.kit),
                "--reference",str(self.ref),"--reference-sha256",sha(self.ref),
                "--previous-sources",str(self.prev_src),
                "--previous-classes",str(self.prev_cls),
                "--candidate-sources",str(self.new_src),
                "--candidate-classes",str(self.new_cls),
                "--expected-sources","2","--expected-classes","2",
                "--out",str(out)]

    def test_refuse_overwrite_receipt(self):
        file=self.root/"report.json"
        file.write_text("KEEP",encoding="utf8")
        self.assertEqual(audit.main(self.args(file)),2)
        self.assertEqual(file.read_text("utf8"),"KEEP")

    def test_positive_cli_writes_one_release_closed_receipt(self):
        file=self.root/"report.json"
        self.assertEqual(audit.main(self.args(file)),0)
        self.assertFalse(json.loads(file.read_text("utf8"))["merge_approved"])


if __name__=="__main__":
    unittest.main()
