"""R413 public-only fabricated source/class integrity tests.

All source text and Java class bytes are invented independently for
negative controls; no recovered client source or player data is embedded.
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
    "r413_gate",ROOT/"tools/r413/audit_known_precommit_rollback.py")
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

STORE_OLD="""
class InventedStore {
 enum R411StageState {CLEAR,ORPHAN,UNSAFE}
 R411StageState r411StageState() {
    if (Files.readAttributes(staging.toPath(),BasicFileAttributes.class,
        LinkOption.NOFOLLOW_LINKS).isRegularFile())return R411StageState.ORPHAN;
    return R411StageState.CLEAR;
 }
 Object loadForMerge() {return originalRecords;}
 boolean clearWithReceipt() {return true;}
 void deleteStale() {noop();}
 boolean saveWithReceipt(Object rows) {
    if (r411RefuseUnresolvedStage("history save"))return false;
    try(FileChannel channel=FileChannel.open(temp.toPath(),
         StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){
       writer.flush();
       channel.force(true);
    }
    AtomicFileReplace.moveStrict(temp, file);
    return true;
 }
}
"""
STORE_NEW="""
class InventedStore {
 enum R411StageState {CLEAR,ORPHAN,UNSAFE}
 enum R413WriteDisposition {
    NOT_ATTEMPTED,FAILED_BEFORE_REPLACE,REPLACE_ATTEMPTED,COMMITTED
 }
 private R413WriteDisposition r413LastWriteDisposition =
    R413WriteDisposition.NOT_ATTEMPTED;
 void r413ResetWriteDisposition() {
    r413LastWriteDisposition = R413WriteDisposition.NOT_ATTEMPTED;
 }
 R413WriteDisposition r413WriteDisposition() {
    return r413LastWriteDisposition;
 }
 R411StageState r411StageState() {
    if (Files.readAttributes(staging.toPath(),BasicFileAttributes.class,
        LinkOption.NOFOLLOW_LINKS).isRegularFile())return R411StageState.ORPHAN;
    return R411StageState.CLEAR;
 }
 Object loadForMerge() {return originalRecords;}
 boolean clearWithReceipt() {return true;}
 void deleteStale() {noop();}
 boolean saveWithReceipt(Object rows) {
    r413LastWriteDisposition = R413WriteDisposition.FAILED_BEFORE_REPLACE;
    if (r411RefuseUnresolvedStage("history save"))return false;
    try(FileChannel channel=FileChannel.open(temp.toPath(),
         StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){
       writer.flush();
       channel.force(true);
    }
    r413LastWriteDisposition = R413WriteDisposition.REPLACE_ATTEMPTED;
    AtomicFileReplace.moveStrict(temp, file);
    r413LastWriteDisposition = R413WriteDisposition.COMMITTED;
    return true;
 }
}
"""
PANEL_OLD="""
class InventedPanel {
 synchronized Collection<LootTrackerRecord> getRecords() {
    return new ArrayList<>(records);
 }
 Collection<LootTrackerRecord> getRecordsOffEdt() {return getRecords();}
 synchronized Collection<LootTrackerRecord> r405FrozenRecords() {
    return new ArrayList<>(records);
 }
 synchronized void clearRecords() {records.clear();}
 void addRecords(Collection<LootTrackerRecord> copy) {records.addAll(copy);}
 private synchronized void recountAggregates() {fakeAggregates();}
 void rebuild() {fakeLayout();}
}
"""
PANEL_NEW="""
class InventedPanel {
 synchronized Collection<LootTrackerRecord> getRecords() {
    return new ArrayList<>(records);
 }
 static final class R413DeleteSnapshot {
    final List<LootTrackerRecord> records;
    final String filterTitle;
    final LootRecordType filterType;
    final int page;
    final boolean overallView,groupedView;
    R413DeleteSnapshot(List<LootTrackerRecord> records, String filterTitle,
         LootRecordType filterType, int page, boolean overallView,boolean groupedView) {
        this.records=records;this.filterTitle=filterTitle;
        this.filterType=filterType;this.page=page;
        this.overallView=overallView;this.groupedView=groupedView;
    }
 }
 synchronized R413DeleteSnapshot r413CaptureDeleteSnapshot() {
    if (!javax.swing.SwingUtilities.isEventDispatchThread())
       throw new IllegalStateException("synthetic off-EDT");
    return new R413DeleteSnapshot(new ArrayList<>(records), filterTitle,
        filterType, page, overallView, groupedView);
 }
 synchronized void r413RestoreDeleteSnapshot(R413DeleteSnapshot before) {
    if (before == null || !javax.swing.SwingUtilities.isEventDispatchThread())
       throw new IllegalStateException("synthetic wrong state");
    records.clear();
    records.addAll(before.records);
    filterTitle = before.filterTitle;
    filterType = before.filterType;
    page = before.page;
    overallView = before.overallView;
    groupedView = before.groupedView;
    recountAggregates();
    addLeft(filterTitle != null);
    rebuild();
 }
 Collection<LootTrackerRecord> getRecordsOffEdt() {return getRecords();}
 synchronized Collection<LootTrackerRecord> r405FrozenRecords() {
    return new ArrayList<>(records);
 }
 synchronized void clearRecords() {records.clear();}
 void addRecords(Collection<LootTrackerRecord> copy) {records.addAll(copy);}
 private synchronized void recountAggregates() {fakeAggregates();}
 void rebuild() {fakeLayout();}
}
"""
PLUGIN_OLD="""
class InventedPlugin {
 void r402ApplyPanelDeletion(Runnable mutation) {
    if (!SwingUtilities.isEventDispatchThread()) return;
    if (!config.rememberLoot()) {
       mutation.run();
       return;
    }
    synchronized (r401FileGate) {
      if (historyStore.r411StageState() != LootHistoryStore.R411StageState.CLEAR) {
        synchronized (r395HistoryGate) {
          r401ClearUnsafe = true;
          r396LastCommitSucceeded = false;
        }
        return;
      }
      synchronized (r395HistoryGate) {
        if (!historyLoaded) return;
        ++r401ClearGeneration;
        r402PanelEditMutating = true;
        r402EditTransactionOpen = true;
        r402EditWriteReceipt = false;
        r396LastCommitSucceeded = false;
      }
      boolean finished = false;
      try {
        mutation.run();
        finished = true;
      }finally {
        synchronized (r395HistoryGate) {
           ++r401ClearGeneration;
           r402PanelEditMutating = false;
        }
      }
      try {
        persistHistory();
      }finally{
        synchronized (r395HistoryGate) {
          if (!r402EditWriteReceipt) {
             r401ClearUnsafe = true;
          }
          r402EditTransactionOpen = false;
        }
      }
    }
 }
 void persistHistory() {saveOnFileGate();}
 void r403QueueAutosave() {executeBackground();}
 void clearHistory() {clearWithReceipt();}
 void shutDown() {persistHistory();}
}
"""
PLUGIN_NEW="""
class InventedPlugin {
 void r402ApplyPanelDeletion(Runnable mutation) {
    if (!SwingUtilities.isEventDispatchThread()) return;
    if (!config.rememberLoot()) {
       mutation.run();
       return;
    }
    synchronized (r401FileGate) {
      if (historyStore.r411StageState() != LootHistoryStore.R411StageState.CLEAR) {
        synchronized (r395HistoryGate) {
          r401ClearUnsafe = true;
          r396LastCommitSucceeded = false;
        }
        return;
      }
      final LootTrackerPanel.R413DeleteSnapshot r413Before =
          panel.r413CaptureDeleteSnapshot();
      synchronized (r395HistoryGate) {
        if (!historyLoaded) return;
        ++r401ClearGeneration;
        r402PanelEditMutating = true;
        r402EditTransactionOpen = true;
        r402EditWriteReceipt = false;
        r396LastCommitSucceeded = false;
        historyStore.r413ResetWriteDisposition();
      }
      boolean finished = false;
      try {
        mutation.run();
        finished = true;
      }finally {
        synchronized (r395HistoryGate) {
           ++r401ClearGeneration;
           r402PanelEditMutating = false;
        }
      }
      try {
        persistHistory();
      }finally {
        boolean r413ProvenUncommitted = false;
        try {
          synchronized (r395HistoryGate) {
            if (!r402EditWriteReceipt) {
              r401ClearUnsafe = true;
              r413ProvenUncommitted = historyStore.r413WriteDisposition() ==
                  LootHistoryStore.R413WriteDisposition.FAILED_BEFORE_REPLACE;
            }
          }
          if (r413ProvenUncommitted) {
            panel.r413RestoreDeleteSnapshot(r413Before);
          }
        } finally {
          synchronized (r395HistoryGate) {
            r402EditTransactionOpen = false;
          }
        }
      }
    }
 }
 void persistHistory() {saveOnFileGate();}
 void r403QueueAutosave() {executeBackground();}
 void clearHistory() {clearWithReceipt();}
 void shutDown() {persistHistory();}
}
"""

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class R413PrivateGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        r=Path(self.temp.name)
        self.kit=r/"invented-original.zip";self.ref=r/"invented-original.jar"
        self.before_dir=r/"source-before";self.after_dir=r/"source-after"
        self.old_classes=r/"classes-before";self.new_classes=r/"classes-after"
        others={name:b"invented Java "+name.encode()
                for name in gate.ORIGINAL_DIFFERENCES if name not in gate.SOURCES}
        others[gate.PRICE]=b"invented price cache"
        self.prior={**others,gate.PLUGIN:PLUGIN_OLD.encode(),
                    gate.STORE:STORE_OLD.encode(),gate.PANEL:PANEL_OLD.encode()}
        self.candidate={**others,gate.PLUGIN:PLUGIN_NEW.encode(),
                        gate.STORE:STORE_NEW.encode(),gate.PANEL:PANEL_NEW.encode()}
        self.prior_classes={name:b"old invented "+name.encode()
                            for name in gate.ORIGINAL_CLASS_DIFFERENCES}
        self.prior_classes[gate.R411_ADDED]=b"old R411 nested enum"
        self.new_classes=self.prior_classes.copy()
        for name in gate.CLASSES:
            self.new_classes[name]=b"new invented "+name.encode()
        for name in gate.ADDED:
            self.new_classes[name]=b"new invented nested "+name.encode()
        self.write()

    @staticmethod
    def put(root,content):
        root.mkdir(parents=True,exist_ok=True)
        for f in root.rglob("*"):
            if f.is_file():f.unlink()
        for name,blob in content.items():
            path=root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(blob)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            for name in sorted(self.candidate):
                payload=(self.candidate[name] if name==gate.PRICE else
                         b"independent invented original Java")
                z.writestr("source/"+name,payload)
        with ZipFile(self.ref,"w") as z:
            for name in sorted(gate.ORIGINAL_CLASS_DIFFERENCES):
                z.writestr(name,b"independent invented original class")
        self.put(self.before_dir,self.prior)
        self.put(self.after_dir,self.candidate)
        self.put(self.old_classes,self.prior_classes)
        self.put(self.new_classes,self.new_classes)

    def gate(self):
        return gate.audit(kit=self.kit,kit_sha=sha(self.kit),
            reference=self.ref,reference_sha=sha(self.ref),
            previous_sources=self.before_dir,previous_classes=self.old_classes,
            candidate_sources=self.after_dir,candidate_classes=self.new_classes,
            expected_sources=7,previous_classes_count=9,
            candidate_classes_count=11)

    def patch(self,name,a,b):
        prior=self.candidate[name]
        self.assertIn(a.encode(),prior)
        self.candidate[name]=prior.replace(a.encode(),b.encode())
        self.write()

    def refuse(self,msg=None):
        if msg:
            with self.assertRaisesRegex(gate.Refused,msg):self.gate()
        else:
            with self.assertRaises(gate.Refused):self.gate()

    def test_positive_scope_and_release_gates(self):
        r=self.gate()
        self.assertEqual(r["status"],"R413_PRIVATE_KNOWN_PRE_REPLACE_ROLLBACK_GATE_PASS")
        self.assertEqual(r["source_count"],7)
        self.assertEqual(r["compiled_class_count"],11)
        self.assertEqual(r["changed_source_count_vs_r412"],3)
        self.assertEqual(r["changed_existing_classes_vs_r412"],3)
        self.assertEqual(r["new_nested_classes_vs_r412"],2)
        for name in ("postreplace_ambiguous_commit_auto_rollback",
                     "rollback_on_no_write_attempt","full_cross_process_correctness_proven",
                     "asynchronous_confirmed_deletions_enabled",
                     "private_client_executed","production_history_read_or_modified",
                     "private_release_authorized","merge_approved"):
            self.assertFalse(r[name])

    def test_receipt_does_not_expose_source_or_paths(self):
        data=json.dumps(self.gate())
        for x in ("InventedStore","files.move(","invented-original.zip","filterType, page,"):
            self.assertNotIn(x,data)

    def test_known_failure_state_required(self):
        self.patch(gate.STORE,"FAILED_BEFORE_REPLACE","UNKNOWN")
        self.refuse()

    def test_pre_replace_status_must_precede_stage_check(self):
        self.patch(gate.STORE,
            "r413LastWriteDisposition = R413WriteDisposition.FAILED_BEFORE_REPLACE;\n    if (r411",
            "if (r411")
        self.refuse()

    def test_post_replace_transition_required(self):
        self.patch(gate.STORE,
            "r413LastWriteDisposition = R413WriteDisposition.REPLACE_ATTEMPTED;",
            "r413LastWriteDisposition = R413WriteDisposition.FAILED_BEFORE_REPLACE;")
        self.refuse()

    def test_successful_write_committed_state_required(self):
        self.patch(gate.STORE,
            "r413LastWriteDisposition = R413WriteDisposition.COMMITTED;",
            "r413LastWriteDisposition = R413WriteDisposition.REPLACE_ATTEMPTED;")
        self.refuse()

    def test_atomic_must_not_downgrade(self):
        self.patch(gate.STORE,
            "AtomicFileReplace.moveStrict(temp, file)",
            "AtomicFileReplace.move(temp, file)")
        self.refuse()

    def test_flush_before_force_required(self):
        self.patch(gate.STORE,
            "       writer.flush();\n       channel.force(true);",
            "       channel.force(true);\n       writer.flush();")
        self.refuse()

    def test_staging_create_new_required(self):
        self.patch(gate.STORE,"StandardOpenOption.CREATE_NEW",
                   "StandardOpenOption.CREATE")
        self.refuse()

    def test_restore_only_if_proven_before_replace(self):
        self.patch(gate.PLUGIN,
            "LootHistoryStore.R413WriteDisposition.FAILED_BEFORE_REPLACE",
            "LootHistoryStore.R413WriteDisposition.REPLACE_ATTEMPTED")
        self.refuse()

    def test_no_rollback_for_every_non_success(self):
        self.patch(gate.PLUGIN,
            "historyStore.r413WriteDisposition() ==",
            "historyStore.r413WriteDisposition() !=")
        self.refuse()

    def test_rollback_keeps_unsafe_flag(self):
        self.patch(gate.PLUGIN,
            "if (!r402EditWriteReceipt) {\n              r401ClearUnsafe = true;",
            "if (!r402EditWriteReceipt) {\n              r401ClearUnsafe = false;")
        self.refuse()

    def test_rollback_happens_after_saving_attempt(self):
        self.patch(gate.PLUGIN,
            "        persistHistory();",
            "        panel.r413RestoreDeleteSnapshot(r413Before); persistHistory();")
        self.refuse()

    def test_transaction_stays_open_until_rollback_finishes(self):
        self.patch(gate.PLUGIN,
            "            r402EditTransactionOpen = false;",
            "            r402EditTransactionOpen = false;")
        # Use a genuine position violation rather than equal replacement.
        self.patch(gate.PLUGIN,
            "            panel.r413RestoreDeleteSnapshot(r413Before);",
            "            r402EditTransactionOpen = false;\n            panel.r413RestoreDeleteSnapshot(r413Before);")
        self.refuse()

    def test_original_synchronous_save_retained(self):
        self.patch(gate.PLUGIN,
            "        persistHistory();",
            "        r403QueueAutosave();")
        self.refuse()

    def test_preexisting_stage_preadmission_required(self):
        self.patch(gate.PLUGIN,
            "historyStore.r411StageState()",
            "historyStore.stagingFile()")
        self.refuse()

    def test_nonpersistent_ui_only_mode_retained(self):
        self.patch(gate.PLUGIN,"!config.rememberLoot()","false")
        self.refuse()

    def test_ui_mutation_occurs_once_inside_transaction(self):
        self.patch(gate.PLUGIN,
            "        mutation.run();\n        finished = true;",
            "        mutation.run(); mutation.run();\n        finished = true;")
        self.refuse()

    def test_snapshot_captures_record_object_references(self):
        self.patch(gate.PANEL,
            "new R413DeleteSnapshot(new ArrayList<>(records), filterTitle,",
            "new R413DeleteSnapshot(deepCloned(records), filterTitle,")
        self.refuse()

    def test_snapshot_capture_requires_edt(self):
        self.patch(gate.PANEL,
            "if (!javax.swing.SwingUtilities.isEventDispatchThread())",
            "if (false)")
        self.refuse()

    def test_restore_uses_original_identity_list(self):
        self.patch(gate.PANEL,
            "records.addAll(before.records)",
            "records.addAll(deepCloned(before.records))")
        self.refuse()

    def test_restore_must_not_drop_record_order(self):
        self.patch(gate.PANEL,
            "records.addAll(before.records)",
            "records.addAll(reverse(before.records))")
        self.refuse()

    def test_restore_must_rebuild_aggregates(self):
        self.patch(gate.PANEL,
            "recountAggregates();\n    addLeft(filterTitle != null);",
            "noop();\n    addLeft(filterTitle != null);")
        self.refuse()

    def test_restore_must_restore_page(self):
        self.patch(gate.PANEL,"page = before.page;","page = 0;")
        self.refuse()

    def test_restore_must_restore_filter(self):
        self.patch(gate.PANEL,"filterTitle = before.filterTitle",
            "filterTitle = null")
        self.refuse()

    def test_restore_must_restore_grouped_mode(self):
        self.patch(gate.PANEL,"groupedView = before.groupedView;",
            "groupedView = true;")
        self.refuse()

    def test_restore_must_restore_overall_mode(self):
        self.patch(gate.PANEL,"overallView = before.overallView;",
            "overallView = false;")
        self.refuse()

    def test_restore_must_rebuild_visible_entries(self):
        self.patch(gate.PANEL,
            "    addLeft(filterTitle != null);\n    rebuild();",
            "    addLeft(filterTitle != null);\n    noop();")
        self.refuse()

    def test_restore_must_not_write_disk(self):
        self.patch(gate.PANEL,
            "    recountAggregates();",
            "    Files.delete(file.toPath()); recountAggregates();")
        self.refuse("R413_ROLLBACK_MUST_NOT_PERFORM_DISK_OR_BLOCKING_HOP")

    def test_unrelated_file_source_change_refused(self):
        self.candidate[gate.MOVE]=b"different helper"
        self.write()
        self.refuse("R413_EXACT_THREE_SOURCE_THREE_CLASS_REQUIRED")

    def test_changed_price_cache_refused(self):
        self.candidate[gate.PRICE]=b"price cache mutated"
        self.write()
        self.refuse("R413_EXACT_THREE_SOURCE_THREE_CLASS_REQUIRED")

    def test_class_drift_refused(self):
        self.new_classes[gate.P+"LootTrackerItem.class"]=b"unrelated class changed"
        self.write()
        self.refuse("R413_EXACT_THREE_SOURCE_THREE_CLASS_REQUIRED")

    def test_new_nested_snapshot_class_must_exist(self):
        self.new_classes.pop(gate.P+"LootTrackerPanel$R413DeleteSnapshot.class")
        self.write()
        self.refuse("R413_PRIVATE_CLASS_COUNT_DRIFT")

    def test_new_nested_disposition_class_must_exist(self):
        self.new_classes.pop(gate.P+"LootHistoryStore$R413WriteDisposition.class")
        self.write()
        self.refuse("R413_PRIVATE_CLASS_COUNT_DRIFT")

    def test_reference_archive_pin_refused(self):
        with self.assertRaisesRegex(gate.Refused,"ARCHIVE_SHA_DRIFT"):
            gate.audit(kit=self.kit,kit_sha="0"*64,
                reference=self.ref,reference_sha=sha(self.ref),
                previous_sources=self.before_dir,previous_classes=self.old_classes,
                candidate_sources=self.after_dir,candidate_classes=self.new_classes,
                expected_sources=7,previous_classes_count=9,candidate_classes_count=11)

    def cli_args(self,out):
        return ["--kit",str(self.kit),"--kit-sha256",sha(self.kit),
                "--reference",str(self.ref),"--reference-sha256",sha(self.ref),
                "--previous-sources",str(self.before_dir),
                "--previous-classes",str(self.old_classes),
                "--candidate-sources",str(self.after_dir),
                "--candidate-classes",str(self.new_classes),
                "--expected-sources","7",
                "--previous-classes-count","9","--candidate-classes-count","11",
                "--out",str(out)]

    def test_existing_receipt_refused(self):
        out=Path(self.temp.name)/"receipt.json"
        out.write_text("KEEP")
        self.assertEqual(gate.main(self.cli_args(out)),2)
        self.assertEqual(out.read_text(),"KEEP")

    def test_cli_receipt_release_closed(self):
        out=Path(self.temp.name)/"receipt.json"
        self.assertEqual(gate.main(self.cli_args(out)),0)
        self.assertFalse(json.loads(out.read_text())["merge_approved"])

if __name__=="__main__":
    unittest.main()
