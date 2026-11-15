"""Public synthetic negative controls for passive R406 EDT contention auditing.

All toy Java is invented. No recovered SpawnPK Java/class bytes, client
launch, real history file or user-specific data is needed.
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
    "r406_passive",ROOT/"tools/r406/audit_edt_file_gate_contention.py")
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
        r402EditTransactionOpen = true;
      }
      mutation.run();
      persistHistory();
      if (!r402EditWriteReceipt) unsafe = true;
      r402EditTransactionOpen = false;
    }
  }
  void persistHistory() {
    Collection stored = panel.r405FrozenRecords();
    synchronized (r401FileGate) {
      synchronized (r395HistoryGate) {
        if (unsafe) return;
      }
      committed = historyStore.saveWithReceipt(merged);
    }
  }
  void r403QueueAutosave() {
    executor.execute(() -> {
      try {
        persistHistory();
      } finally {
        if (issuedEpoch == r399SessionEpoch) {
          r403AutosaveQueued = false;
        }
      }
    });
  }
  void requestSave() {
    r403QueueAutosave();
  }
  void clearHistory() {
    if (!SwingUtilities.isEventDispatchThread()) {
      SwingUtilities.invokeLater(this::clearHistory);
      return;
    }
    r401ClearInProgress = true;
    ++r399SessionEpoch;
    final boolean deleted;
    synchronized (r401FileGate) {
      deleted = historyStore.clearWithReceipt();
    }
    if (!deleted) {
      unsafe = true;
      return;
    }
    panel.clearRecords();
  }
  void shutDown() {
    persistHistory();
  }
  void onGameStateChanged() {
    persistHistory();
  }
}
"""
FAKE_PANEL="""
class InventedPanel {
  private void removeSource(String title,LootRecordType type) {
    if (!confirm("synthetic source")) return;
    plugin.r402ApplyPanelDeletion(() -> {
      records.removeIf(r -> r.matchesGroup(title, type));
      rebuild();
    });
  }
  private void removeType(LootRecordType type) {
    if (!confirm("synthetic type")) return;
    plugin.r402ApplyPanelDeletion(() -> {
      records.removeIf(r -> r.isType(type));
      rebuild();
    });
  }
  private void removeRecord(LootTrackerRecord record) {
    if (!confirm("synthetic record")) return;
    plugin.r402ApplyPanelDeletion(() -> {
      records.removeIf(r -> r == record);
      rebuild();
    });
  }
}
"""
FAKE_STORE="""
class InventedHistoryStore {
  boolean saveWithReceipt(Collection<LootTrackerRecord> records) {
    for (LootTrackerRecord record : records) {
      document.records.add(RecordDto.from(record));
    }
    Files.newOutputStream(temp.toPath());
    GSON.a(document, writer);
    AtomicFileReplace.move(temp, file);
    return true;
  }
}
"""

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

class R406EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.r=Path(self.t.name)
        self.kit=self.r/"synthetic-original.zip"
        self.reference=self.r/"synthetic-original.jar"
        self.sources=self.r/"synthetic-sources"
        self.classes=self.r/"synthetic-classes"
        self.src={
            audit.PLUGIN:FAKE_PLUGIN.encode("utf8"),
            audit.PANEL:FAKE_PANEL.encode("utf8"),
            audit.STORE:FAKE_STORE.encode("utf8"),
            audit.ITEM:b"class InventedItem {}",
            audit.RECORD:b"class InventedRecord {}",
        }
        self.cls={name:b"invented-class-"+name.encode("utf8")
                  for name in audit.CHANGED_CLASS}
        self.write()

    @staticmethod
    def tree(dest,parts):
        dest.mkdir(parents=True,exist_ok=True)
        for f in dest.rglob("*"):
            if f.is_file():f.unlink()
        for name,data in parts.items():
            path=dest/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            for name in sorted(audit.CHANGED_SOURCE):
                z.writestr("source/"+name,b"original-synthetic-source")
        with ZipFile(self.reference,"w") as z:
            for name in sorted(audit.CHANGED_CLASS):
                z.writestr(name,b"original-synthetic-class")
        self.tree(self.sources,self.src)
        self.tree(self.classes,self.cls)

    def validate(self):
        return audit.audit(
            kit=self.kit,kit_sha=sha(self.kit),
            reference=self.reference,reference_sha=sha(self.reference),
            inspected_sources=self.sources,inspected_classes=self.classes,
            expected_sources=5,expected_classes=7)

    def mutate(self,where,old,new):
        data=self.src[where]
        anchor=old.encode("utf8")
        self.assertIn(anchor,data)
        self.src[where]=data.replace(anchor,new.encode("utf8"))
        self.write()

    def refuses(self,message=None):
        if message:
            with self.assertRaisesRegex(audit.Refused,message):
                self.validate()
        else:
            with self.assertRaises(audit.Refused):
                self.validate()

    def test_actual_risk_report_stays_release_closed(self):
        report=self.validate()
        self.assertEqual(report["status"],"R406_PASSIVE_EDT_CONTENTION_EVIDENCE_PASS")
        self.assertTrue(report["source_confirmed_edt_delete_calls_disk_commit_synchronously"])
        self.assertTrue(report["source_confirmed_edt_clear_acquires_shared_file_monitor"])
        self.assertTrue(report["background_autosave_competes_for_same_file_monitor"])
        self.assertTrue(report["source_confirmed_clear_can_orphan_r403_queued_autosave"])
        self.assertFalse(report["clear_during_queued_autosave_regression_fixed"])
        for name in ("proposed_nonblocking_production_delete_implemented",
                     "measured_real_edt_latency","actual_client_executed",
                     "private_source_modified_by_r406","private_client_rebuilt_by_r406",
                     "private_source_release_authorized","merge_approved"):
            self.assertFalse(report[name])

    def test_receipt_is_free_of_source(self):
        text=json.dumps(self.validate())
        self.assertNotIn("InventedPlugin",text)
        self.assertNotIn("records.removeIf",text)
        self.assertNotIn("synthetic-original.zip",text)

    def test_edt_guard_required(self):
        self.mutate(audit.PLUGIN,"SwingUtilities.isEventDispatchThread()",
                    "someOtherThread()")
        self.refuses()

    def test_shared_delete_monitor_required(self):
        self.mutate(audit.PLUGIN,
                    "synchronized (r401FileGate) {\n      synchronized (r395HistoryGate)",
                    "synchronized (unrelatedGate) {\n      synchronized (r395HistoryGate)")
        self.refuses()

    def test_deletion_receipt_cannot_be_removed(self):
        self.mutate(audit.PLUGIN,"if (!r402EditWriteReceipt) unsafe = true;",
                    "if (false) unsafe = true;")
        self.refuses()

    def test_deletion_cannot_be_silently_async(self):
        self.mutate(audit.PLUGIN,
                    "      mutation.run();\n      persistHistory();",
                    "      mutation.run();\n      executor.execute(() -> persistHistory());")
        self.refuses()

    def test_deletion_mutation_must_precede_save(self):
        self.mutate(audit.PLUGIN,
                    "      mutation.run();\n      persistHistory();",
                    "      persistHistory();\n      mutation.run();")
        self.refuses()

    def test_delete_closes_transaction(self):
        self.mutate(audit.PLUGIN,"r402EditTransactionOpen = false;",
                    "r402EditTransactionOpen = true;")
        self.refuses()

    def test_save_stays_under_same_file_monitor(self):
        self.mutate(audit.PLUGIN,
                    "    synchronized (r401FileGate) {\n      synchronized (r395HistoryGate)",
                    "    synchronized (otherGate) {\n      synchronized (r395HistoryGate)")
        self.refuses()

    def test_save_file_receipt_required(self):
        self.mutate(audit.PLUGIN,
                    "historyStore.saveWithReceipt(merged)",
                    "historyStore.save(merged)")
        self.refuses()

    def test_save_cannot_hop_to_edt(self):
        self.mutate(audit.PLUGIN,
                    "Collection stored = panel.r405FrozenRecords();",
                    "SwingUtilities.invokeAndWait(job); Collection stored = panel.r405FrozenRecords();")
        self.refuses("R406_NEW_CLIENT_EDT_HOP_REFUSED")

    def test_autosave_remains_worker_submitted(self):
        self.mutate(audit.PLUGIN,
                    "executor.execute(() -> {",
                    "executor.executeLater(() -> {")
        self.refuses()

    def test_request_save_does_not_block_client(self):
        self.mutate(audit.PLUGIN,
                    "    r403QueueAutosave();",
                    "    persistHistory();")
        self.refuses()

    def test_clear_must_check_edt(self):
        self.mutate(audit.PLUGIN,
                    "SwingUtilities.isEventDispatchThread()",
                    "someOtherThread()")
        self.refuses()

    def test_clear_must_advance_session_epoch(self):
        self.mutate(audit.PLUGIN,"++r399SessionEpoch;","r399SessionEpoch;")
        self.refuses("R406_CLEAR_MUST_INVALIDATE_PRE_CLEAR_WORKERS")

    def test_obsolete_worker_completion_must_be_epoch_guarded(self):
        self.mutate(audit.PLUGIN,
                    "if (issuedEpoch == r399SessionEpoch)",
                    "if (true)")
        self.refuses("R406_OLD_WORKER_COMPLETION_EPOCH_GUARD_MISSING")

    def test_clear_queue_flag_reset_changes_prior_r405_risk(self):
        self.mutate(audit.PLUGIN,
                    "++r399SessionEpoch;\n    final boolean deleted;",
                    "++r399SessionEpoch;\n    r403AutosaveQueued = false;\n    final boolean deleted;")
        self.refuses("R406_CLEAR_QUEUE_RESET_ALREADY_CHANGED")

    def test_clear_disk_receipt_must_share_gate(self):
        self.mutate(audit.PLUGIN,
                    "      deleted = historyStore.clearWithReceipt();",
                    "      deleted = true;")
        self.refuses()

    def test_clear_failure_must_not_empty_panel(self):
        self.mutate(audit.PLUGIN,"    if (!deleted) {",
                    "    if (false) {")
        self.refuses()

    def test_source_delete_needs_confirmation(self):
        self.mutate(audit.PANEL,"confirm(\"synthetic source\")",
                    "false")
        self.refuses()

    def test_type_deletion_needs_confirmed_selector(self):
        self.mutate(audit.PANEL,"r.isType(type)",
                    "r.matchesGroup(title, type)")
        self.refuses()

    def test_record_delete_must_use_identity(self):
        self.mutate(audit.PANEL,"r == record",
                    "r.equals(record)")
        self.refuses()

    def test_panel_delete_must_use_plugin_transaction(self):
        self.mutate(audit.PANEL,"plugin.r402ApplyPanelDeletion(() ->",
                    "plugin.requestSave(); plugin.r402ApplyPanelDeletion(() ->")
        self.refuses("R406_DIRECT_UI_SAVE_REGRESSION")

    def test_write_must_serialize_record_dtos(self):
        self.mutate(audit.STORE,
                    "RecordDto.from(record)",
                    "record.toString()")
        self.refuses()

    def test_write_must_have_atomic_replace(self):
        self.mutate(audit.STORE,"AtomicFileReplace.move(temp, file)",
                    "Files.copy(temp, file)")
        self.refuses()

    def test_write_must_touch_disk_inside_receipt(self):
        self.mutate(audit.STORE,"Files.newOutputStream(temp.toPath())",
                    "new InMemoryWriter()")
        self.refuses()

    def test_logout_synchronous_fallback_required(self):
        self.mutate(audit.PLUGIN,"  void onGameStateChanged() {\n    persistHistory();",
                    "  void onGameStateChanged() {\n    r403QueueAutosave();")
        self.refuses()

    def test_stop_synchronous_fallback_required(self):
        self.mutate(audit.PLUGIN,"  void shutDown() {\n    persistHistory();",
                    "  void shutDown() {\n    r403QueueAutosave();")
        self.refuses()

    def test_sha_pin_is_enforced(self):
        with self.assertRaisesRegex(audit.Refused,"ARCHIVE_SHA_DRIFT"):
            audit.audit(
                kit=self.kit,kit_sha="0"*64,
                reference=self.reference,reference_sha=sha(self.reference),
                inspected_sources=self.sources,inspected_classes=self.classes,
                expected_sources=5,expected_classes=7)

    def test_exact_source_scope_is_enforced(self):
        self.src[audit.ITEM]=b"original-synthetic-source"
        self.write()
        self.refuses("R406_R405_REFERENCE_DELTA_SCOPE_DRIFT")

    def test_exact_class_scope_is_enforced(self):
        key=audit.P+"LootHistoryStore$RecordDto.class"
        self.cls[key]=b"original-synthetic-class"
        self.write()
        self.refuses("R406_R405_REFERENCE_DELTA_SCOPE_DRIFT")

    def args(self,out):
        return [
            "--kit",str(self.kit),"--kit-sha256",sha(self.kit),
            "--reference",str(self.reference),"--reference-sha256",sha(self.reference),
            "--inspected-sources",str(self.sources),
            "--inspected-classes",str(self.classes),
            "--expected-sources","5","--expected-classes","7",
            "--out",str(out)]

    def test_existing_report_cannot_be_overwritten(self):
        output=self.r/"receipt.json"
        output.write_text("KEEP")
        self.assertEqual(audit.main(self.args(output)),2)
        self.assertEqual(output.read_text(),"KEEP")

    def test_one_cli_report_remains_release_closed(self):
        output=self.r/"receipt.json"
        self.assertEqual(audit.main(self.args(output)),0)
        self.assertFalse(json.loads(output.read_text())["merge_approved"])


if __name__=="__main__":
    unittest.main()
