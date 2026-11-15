"""R408 fabricated source/class refusal tests for passive async-delete prerequisites.

These are entirely invented Java text fragments. They do not contain,
compile, run or export any recovered game source or private client data.
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
    "r408_public",ROOT/"tools/r408/audit_async_delete_prerequisites.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

FAKE_PLUGIN="""
class InventedPlugin {
  void r402ApplyPanelDeletion(Runnable mutation) {
    if (!SwingUtilities.isEventDispatchThread()) return;
    if (!config.rememberLoot()) {
      mutation.run();
      return;
    }
    synchronized (r401FileGate) {
      synchronized (r395HistoryGate) {
        r402PanelEditMutating = true;
      }
      mutation.run();
      synchronized (r395HistoryGate) {
        r402PanelEditMutating = false;
      }
      persistHistory();
      if (!r402EditWriteReceipt) {
        r401ClearUnsafe = true;
      }
      r402EditTransactionOpen = false;
    }
  }
  void persistHistory() {
    Collection<?> copy = panel.r405FrozenRecords();
    r405FrozenPending.add(pending.r405FrozenCopy());
    synchronized (r401FileGate) {
      Long epoch = r403WorkerEpoch.get();
      if (r401SnapshotClearGeneration != r401ClearGeneration) return;
      historyStore.saveWithReceipt(merged);
    }
  }
  void r403QueueAutosave() {
    if (r403AutosaveQueued) {
      r403AutosaveDirty = true;
      return;
    }
    r403AutosaveQueued = true;
    issuedEpoch = r399SessionEpoch;
    executor.execute(() -> {
      r403WorkerEpoch.set(issuedEpoch);
      persistHistory();
      r403WorkerEpoch.remove();
    });
  }
  void clearHistory() {
    if (!SwingUtilities.isEventDispatchThread()) return;
    ++r399SessionEpoch;
    r403AutosaveQueued = false;
    r403AutosaveDirty = false;
    synchronized (r401FileGate) {
      historyStore.clearWithReceipt();
    }
    panel.clearRecords();
  }
  void shutDown() {
    instance = null;
    ++r399SessionEpoch;
    r403RetiredWorker.shutdown();
    persistHistory();
  }
}
"""
FAKE_PANEL="""
class InventedPanel {
  void removeSource(String title,LootRecordType type) {
    if (!confirm("invented source")) return;
    plugin.r402ApplyPanelDeletion(() -> {
      records.removeIf(r -> r.matchesGroup(title, type));
      rebuild();
    });
  }
  void removeType(LootRecordType type) {
    if (!confirm("invented type")) return;
    plugin.r402ApplyPanelDeletion(() -> {
      records.removeIf(r -> r.isType(type));
      rebuild();
    });
  }
  void removeRecord(LootTrackerRecord record) {
    if (!confirm("invented record")) return;
    plugin.r402ApplyPanelDeletion(() -> {
      records.removeIf(r -> r == record);
      rebuild();
    });
  }
  synchronized Collection<LootTrackerRecord> r405FrozenRecords() {
    List<LootTrackerRecord> frozen = new ArrayList<>(records.size());
    for (LootTrackerRecord record : records) {
      frozen.add(record.r405FrozenCopy());
    }
    return frozen;
  }
  synchronized Collection<LootTrackerRecord> getRecords() {
    return new ArrayList<>(records);
  }
}
"""
FAKE_RECORD="""
class InventedRecord {
  LootTrackerRecord r405FrozenCopy() {
    LootTrackerItem[] references = items.clone();
    for (int i=0;i<references.length;++i) {
      frozen[i] = references[i].r405FrozenCopy();
    }
    return new LootTrackerRecord(title, subTitle, type, frozen, kills, timestamp);
  }
}
"""
FAKE_STORE="""
class InventedStore {
  boolean saveWithReceipt(Collection<LootTrackerRecord> rows) {
    for (LootTrackerRecord record : rows) {
      document.add(RecordDto.from(record));
    }
    Files.newOutputStream(temp.toPath());
    GSON.a(document, writer);
    AtomicFileReplace.move(temp, file);
    return true;
  }
}
"""
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class R408PrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        r=Path(self.tmp.name)
        self.kit=r/"synthetic-kit.zip"
        self.ref=r/"synthetic-ref.jar"
        self.source_root=r/"source"
        self.class_root=r/"class"
        self.sources={
            audit.PLUGIN:FAKE_PLUGIN.encode(),
            audit.PANEL:FAKE_PANEL.encode(),
            audit.RECORD:FAKE_RECORD.encode(),
            audit.STORE:FAKE_STORE.encode(),
            audit.ITEM:b"class InventedItem {}",
        }
        self.classes={name:b"synthetic class "+name.encode()
                      for name in audit.CHANGED_CLASSES}
        self.write()

    @staticmethod
    def tree(root,content):
        root.mkdir(parents=True,exist_ok=True)
        for p in root.rglob("*"):
            if p.is_file():p.unlink()
        for name,blob in content.items():
            p=root/name
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(blob)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            for name in sorted(audit.CHANGED_SOURCES):
                z.writestr("source/"+name,b"reference invented source")
        with ZipFile(self.ref,"w") as z:
            for name in sorted(audit.CHANGED_CLASSES):
                z.writestr(name,b"reference invented class")
        self.tree(self.source_root,self.sources)
        self.tree(self.class_root,self.classes)

    def verify(self):
        return audit.audit(
            kit=self.kit,kit_sha=digest(self.kit),
            reference=self.ref,reference_sha=digest(self.ref),
            inspected_sources=self.source_root,inspected_classes=self.class_root,
            expected_sources=5,expected_classes=7)

    def mutate(self,name,old,new):
        before=old.encode()
        content=self.sources[name]
        self.assertIn(before,content)
        self.sources[name]=content.replace(before,new.encode())
        self.write()

    def refusal(self,reason=None):
        if reason:
            with self.assertRaisesRegex(audit.Refused,reason):self.verify()
        else:
            with self.assertRaises(audit.Refused):self.verify()

    def test_positive_prerequisites_explicitly_not_integrated(self):
        r=self.verify()
        self.assertEqual(r["status"],"R408_PRIVATE_ASYNC_EDIT_PREREQUISITES_PASS")
        self.assertEqual(r["source_count"],5)
        self.assertEqual(r["class_count"],7)
        for name in ("private_source_modified_for_r408",
                     "private_client_rebuilt_for_r408","private_client_executed",
                     "runtime_safety_proven","cross_process_locking_proven",
                     "power_loss_recovery_proven","source_release_authorized",
                     "merge_approved",
                     "background_delete_commit_and_edt_ack_integrated",
                     "durable_post_commit_pre_ack_restart_reconciliation_integrated"):
            self.assertFalse(r[name])

    def test_no_private_text_in_receipt(self):
        t=json.dumps(self.verify())
        for marker in ("InventedPlugin","records.removeIf","R408Fake","synthetic-kit.zip"):
            self.assertNotIn(marker,t)

    def test_current_delete_requires_edt(self):
        self.mutate(audit.PLUGIN,"SwingUtilities.isEventDispatchThread()",
                    "Thread.currentThread().isAlive()")
        self.refusal()

    def test_current_deletion_requires_file_gate(self):
        self.mutate(audit.PLUGIN,
                    "    synchronized (r401FileGate) {\n      synchronized (r395HistoryGate)",
                    "    synchronized (otherGate) {\n      synchronized (r395HistoryGate)")
        self.refusal()

    def test_current_deletion_mutates_before_receipt(self):
        self.mutate(audit.PLUGIN,
                    "      mutation.run();\n      synchronized (r395HistoryGate)",
                    "      synchronized (r395HistoryGate)")
        self.refusal()

    def test_current_deletion_persist_is_synchronous(self):
        self.mutate(audit.PLUGIN,
                    "      persistHistory();\n      if (!r402EditWriteReceipt)",
                    "      executor.execute(() -> persistHistory());\n      if (!r402EditWriteReceipt)")
        self.refusal()

    def test_current_deletion_checks_receipt(self):
        self.mutate(audit.PLUGIN,
                    "if (!r402EditWriteReceipt)","if (false)")
        self.refusal()

    def test_current_deletion_failed_commit_quarantines(self):
        self.mutate(audit.PLUGIN,
                    "r401ClearUnsafe = true;","r401ClearUnsafe = false;")
        self.refusal()

    def test_ui_only_mode_preserved(self):
        self.mutate(audit.PLUGIN,
                    "if (!config.rememberLoot())","if (true)")
        self.refusal()

    def test_select_source_requires_confirmation(self):
        self.mutate(audit.PANEL,"confirm(\"invented source\")","true")
        self.refusal()

    def test_select_source_requires_exact_group(self):
        self.mutate(audit.PANEL,
                    "r.matchesGroup(title, type)","r.isType(type)")
        self.refusal()

    def test_select_type_requires_type_selector(self):
        self.mutate(audit.PANEL,"r.isType(type)","r.matchesGroup(title, type)")
        self.refusal()

    def test_single_row_deletion_identity_required(self):
        self.mutate(audit.PANEL,"r == record","r.equals(record)")
        self.refusal()

    def test_panel_transaction_admission_required(self):
        self.mutate(audit.PANEL,
                    "plugin.r402ApplyPanelDeletion(",
                    "plugin.r408QueueDeletion(")
        self.refusal()

    def test_panel_deletion_rebuild_required(self):
        self.mutate(audit.PANEL,
                    "      rebuild();\n    });",
                    "      noop();\n    });")
        self.refusal()

    def test_frozen_records_from_panel_required(self):
        self.mutate(audit.PANEL,
                    "synchronized Collection<LootTrackerRecord> r405FrozenRecords()",
                    "Collection<LootTrackerRecord> r405FrozenRecords()")
        self.refusal()

    def test_deep_copy_of_panel_records_required(self):
        self.mutate(audit.PANEL,
                    "frozen.add(record.r405FrozenCopy())",
                    "frozen.add(record)")
        self.refusal()

    def test_identity_reference_lookup_required(self):
        self.mutate(audit.PANEL,
                    "return new ArrayList<>(records);",
                    "return records;")
        self.refusal()

    def test_record_deep_copy_must_be_separate(self):
        self.mutate(audit.RECORD,
                    "frozen[i] = references[i].r405FrozenCopy()",
                    "frozen[i] = references[i]")
        self.refusal()

    def test_record_copy_preserves_timestamp(self):
        self.mutate(audit.RECORD,
                    "frozen, kills, timestamp",
                    "frozen, kills, 0")
        self.refusal()

    def test_pending_records_must_be_copied(self):
        self.mutate(audit.PLUGIN,
                    "r405FrozenPending.add(pending.r405FrozenCopy())",
                    "r405FrozenPending.add(pending)")
        self.refusal()

    def test_stale_autosave_clear_generation_guard_required(self):
        self.mutate(audit.PLUGIN,
                    "r401SnapshotClearGeneration != r401ClearGeneration",
                    "false")
        self.refusal()

    def test_autosave_epoch_token_required(self):
        self.mutate(audit.PLUGIN,
                    "r403WorkerEpoch.get()","null")
        self.refusal()

    def test_autosave_coalescing_required(self):
        self.mutate(audit.PLUGIN,
                    "r403AutosaveDirty = true;","r403AutosaveDirty = false;")
        self.refusal()

    def test_clear_epoch_fence_required(self):
        self.mutate(audit.PLUGIN,
                    "++r399SessionEpoch;","noop();")
        self.refusal()

    def test_clear_autosave_queued_reset_required(self):
        self.mutate(audit.PLUGIN,
                    "r403AutosaveQueued = false;","r403AutosaveQueued = true;")
        self.refusal()

    def test_shutdown_must_retire_worker(self):
        self.mutate(audit.PLUGIN,
                    "r403RetiredWorker.shutdown();","r403RetiredWorker.shutdownNow();")
        self.refusal()

    def test_store_receipt_requires_serialized_record_dtos(self):
        self.mutate(audit.STORE,
                    "RecordDto.from(record)","record.toString()")
        self.refusal()

    def test_store_receipt_requires_atomic_move(self):
        self.mutate(audit.STORE,
                    "AtomicFileReplace.move(temp, file)",
                    "Files.copy(temp, file)")
        self.refusal()

    def test_store_receipt_true_after_move(self):
        self.mutate(audit.STORE,
                    "    return true;",
                    "    return false;")
        self.refusal()

    def test_no_private_source_change_scope(self):
        self.sources[audit.ITEM]=b"reference invented source"
        self.write()
        self.refusal("R408_R407_REFERENCE_DELTA_SCOPE_DRIFT")

    def test_no_private_class_change_scope(self):
        self.classes[audit.P+"LootTrackerPlugin.class"]=b"reference invented class"
        self.write()
        self.refusal("R408_R407_REFERENCE_DELTA_SCOPE_DRIFT")

    def test_pinned_source_archive_digest(self):
        with self.assertRaisesRegex(audit.Refused,"ARCHIVE_SHA_DRIFT"):
            audit.audit(
                kit=self.kit,kit_sha="0"*64,
                reference=self.ref,reference_sha=digest(self.ref),
                inspected_sources=self.source_root,inspected_classes=self.class_root,
                expected_sources=5,expected_classes=7)

    def args(self,path):
        return ["--kit",str(self.kit),"--kit-sha256",digest(self.kit),
                "--reference",str(self.ref),
                "--reference-sha256",digest(self.ref),
                "--inspected-sources",str(self.source_root),
                "--inspected-classes",str(self.class_root),
                "--expected-sources","5","--expected-classes","7",
                "--out",str(path)]

    def test_refuse_existing_report(self):
        out=Path(self.tmp.name)/"receipt.json"
        out.write_text("KEEP")
        self.assertEqual(audit.main(self.args(out)),2)
        self.assertEqual(out.read_text(),"KEEP")

    def test_positive_cli_receipt(self):
        out=Path(self.tmp.name)/"receipt.json"
        self.assertEqual(audit.main(self.args(out)),0)
        self.assertFalse(json.loads(out.read_text())["merge_approved"])

if __name__=="__main__":
    unittest.main()
