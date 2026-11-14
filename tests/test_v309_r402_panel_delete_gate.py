"""R402 public synthetic source/class gate and negative controls.

No original/recovered Java is in this file; all classes below are invented
toy fixtures that exist solely to exercise the read-only source checker.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "r402_audit",ROOT/"tools/r402/audit_panel_delete_transaction.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

SYNTH_PLUGIN="""
class SyntheticPanelPlugin {
  private boolean r402PanelEditMutating;
  private boolean r402EditTransactionOpen;
  private boolean r402EditWriteReceipt;
  void r402ApplyPanelDeletion(Runnable mutation) {
    if (!SwingUtilities.isEventDispatchThread()) return;
    if (!config.rememberLoot()) {
      mutation.run();
      return;
    }
    synchronized (r401FileGate) {
      synchronized (r395HistoryGate) {
        if (r402EditTransactionOpen) return;
        ++r401ClearGeneration;
        r402PanelEditMutating = true;
        r402EditTransactionOpen = true;
        r402EditWriteReceipt = false;
      }
      boolean finished=false;
      try {
        mutation.run();
        finished=true;
      } finally {
        synchronized (r395HistoryGate) {
          ++r401ClearGeneration;
          r402PanelEditMutating = false;
          if (!finished) r401ClearUnsafe = true;
        }
      }
      try {
        persistHistory();
      } finally {
        synchronized (r395HistoryGate) {
          if (!r402EditWriteReceipt) {
            r401ClearUnsafe = true;
          }
          r402EditTransactionOpen = false;
        }
      }
    }
  }
  void persistHistory() {
    synchronized (r395HistoryGate) {
      if (!historyLoaded || r402PanelEditMutating) return;
    }
    for(int attempt=0;attempt<5;++attempt) {
      synchronized (r395HistoryGate) {
        if (r402PanelEditMutating) continue;
        start = r401ClearGeneration;
      }
      Collection rows = panel.getRecordsOffEdt();
      synchronized (r395HistoryGate) {
        if (r402PanelEditMutating || start != r401ClearGeneration) continue;
        pendingSnapshot = new ArrayList<>(pendingRecords);
      }
      break;
    }
    synchronized (r401FileGate) {
      synchronized (r395HistoryGate) {
        if (r402PanelEditMutating) return;
      }
      r401Committed = historyStore.saveWithReceipt(merged);
    }
    if (r401Committed) {
      synchronized (r395HistoryGate) {
        if (r402EditTransactionOpen) {
          r402EditWriteReceipt = true;
        }
        if (r402PanelEditMutating) return;
      }
    }
  }
  boolean r396FinishStopMerge() {
    synchronized(r395HistoryGate) {
      if (r402PanelEditMutating) return false;
    }
    return true;
  }
  void clearHistory() {
    r401ClearInProgress = true;
  }
}
"""

SYNTH_PANEL="""
class SyntheticPanel {
  void removeSource(String title, LootRecordType type) {
    if (!confirm("delete source")) return;
    plugin.r402ApplyPanelDeletion(() -> {
      synchronized (this) {
        records.removeIf(r -> r.matchesGroup(title, type));
      }
      rebuild();
    });
  }
  void removeType(LootRecordType type) {
    if (!confirm("delete type")) return;
    plugin.r402ApplyPanelDeletion(() -> {
      synchronized (this) {
        records.removeIf(r -> r.isType(type));
      }
      rebuild();
    });
  }
  void removeRecord(LootTrackerRecord record) {
    if (!confirm("delete record")) return;
    plugin.r402ApplyPanelDeletion(() -> {
      synchronized (this) {
        records.removeIf(r -> r == record);
      }
      rebuild();
    });
  }
}
"""

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

class R402DeleteGateTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        self.kit=self.root/"golden.zip"
        self.ref=self.root/"reference.jar"
        self.oldsrc=self.root/"oldsrc"
        self.newsrc=self.root/"newsrc"
        self.oldcls=self.root/"oldcls"
        self.newcls=self.root/"newcls"
        self.plugin=SYNTH_PLUGIN.encode("utf8")
        self.panel=SYNTH_PANEL.encode("utf8")
        self.store=b"new-synthetic-store"
        self.old_plugin=b"older-synthetic-plugin"
        self.old_panel=b"older-synthetic-panel"
        self.old_classes={
            audit.CLASS(audit.PLUGIN):b"old-plugin-class",
            audit.CLASS(audit.PANEL):b"old-panel-class",
            audit.CLASS(audit.STORE):b"same-store-class"}
        self.new_classes={
            audit.CLASS(audit.PLUGIN):b"new-plugin-class",
            audit.CLASS(audit.PANEL):b"new-panel-class",
            audit.CLASS(audit.STORE):b"same-store-class"}
        self.write()

    @staticmethod
    def tree(root,parts):
        root.mkdir(parents=True,exist_ok=True)
        for f in root.rglob("*"):
            if f.is_file():f.unlink()
        for name,data in parts.items():
            f=root/name
            f.parent.mkdir(parents=True,exist_ok=True)
            f.write_bytes(data)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            for name in (audit.PLUGIN,audit.PANEL,audit.STORE):
                z.writestr("source/"+name,b"golden-synthetic-"+name.encode("utf8"))
        with ZipFile(self.ref,"w") as z:
            for name in (audit.PLUGIN,audit.PANEL,audit.STORE):
                z.writestr(audit.CLASS(name),b"golden-synthetic-class")
        self.tree(self.oldsrc,{audit.PLUGIN:self.old_plugin,audit.PANEL:self.old_panel,audit.STORE:self.store})
        self.tree(self.newsrc,{audit.PLUGIN:self.plugin,audit.PANEL:self.panel,audit.STORE:self.store})
        self.tree(self.oldcls,self.old_classes)
        self.tree(self.newcls,self.new_classes)

    def audit(self):
        return audit.audit(
            kit=self.kit,kit_sha=sha(self.kit),
            reference=self.ref,reference_sha=sha(self.ref),
            previous_sources=self.oldsrc,previous_classes=self.oldcls,
            candidate_sources=self.newsrc,candidate_classes=self.newcls,
            expected_sources=3,expected_classes=3)

    def mutate(self,target,old,new):
        old=old.encode("utf8")
        data=getattr(self,target)
        self.assertIn(old,data)
        setattr(self,target,data.replace(old,new.encode("utf8")))
        self.write()

    def refuse(self,reason=None):
        if reason:
            with self.assertRaisesRegex(audit.Refused,reason):self.audit()
        else:
            with self.assertRaises(audit.Refused):self.audit()

    def test_positive_exact_scope(self):
        data=self.audit()
        self.assertEqual(data["status"],"R402_PRIVATE_PANEL_DELETE_STATIC_GATE_PASS")
        self.assertEqual(data["modified_source_count_vs_r401"],2)
        self.assertEqual(data["modified_class_count_vs_r401"],2)
        for key in ("private_client_runtime_executed","production_history_written",
                    "actual_edt_ordering_verified","cross_process_writer_lock_proven",
                    "private_release_authorized","merge_approved"):
            self.assertFalse(data[key])

    def test_report_does_not_expose_source(self):
        s=json.dumps(self.audit())
        self.assertNotIn("SyntheticPanelPlugin",s)
        self.assertNotIn("records.removeIf",s)
        self.assertNotIn("golden.zip",s)

    def test_transaction_field_required(self):
        self.mutate("plugin","private boolean r402PanelEditMutating;",
                    "private boolean renamed;")
        self.refuse("R402_TRANSACTION_FIELD_MISSING")

    def test_edit_requires_edt(self):
        self.mutate("plugin","SwingUtilities.isEventDispatchThread()","true")
        self.refuse("R402_DELETION_TRANSACTION_ORDER_DRIFT")

    def test_config_disabled_preserves_ui_edit(self):
        self.mutate("plugin","config.rememberLoot()","false")
        self.refuse("R402_DELETION_TRANSACTION_ORDER_DRIFT")

    def test_before_edit_generation_required(self):
        self.mutate("plugin","++r401ClearGeneration;","r401ClearGeneration;")
        self.refuse("R402_DELETION_TRANSACTION_ORDER_DRIFT")

    def test_panel_edit_guard_required(self):
        self.mutate("plugin","r402PanelEditMutating = true;",
                    "r402PanelEditMutating = false;")
        self.refuse("R402_DELETION_TRANSACTION_ORDER_DRIFT")

    def test_file_gate_required(self):
        self.mutate("plugin","synchronized (r401FileGate) {","synchronized (wrongGate) {")
        self.refuse("R402_DELETION_TRANSACTION_ORDER_DRIFT")

    def test_mutation_must_not_run_under_history_gate(self):
        self.mutate("plugin","mutation.run();\n        finished=true;",
                    "synchronized(r395HistoryGate){mutation.run();}\n        finished=true;")
        self.refuse("R402_PANEL_MUTATION_UNDER_HISTORY_GATE")

    def test_commit_receipt_required(self):
        self.mutate("plugin","if (!r402EditWriteReceipt) {","if (false) {")
        self.refuse("R402_DELETION_TRANSACTION_ORDER_DRIFT")

    def test_write_receipt_stored(self):
        self.mutate("plugin","r402EditWriteReceipt = true;","r402EditWriteReceipt = false;")
        self.refuse("R402_DELETION_TRANSACTION_ORDER_DRIFT")

    def test_save_rejects_mid_edit(self):
        self.mutate("plugin","if (!historyLoaded || r402PanelEditMutating) return;",
                    "if (!historyLoaded) return;")
        self.refuse("R402_SAVE_EDIT_GUARD_COUNT_DRIFT")

    def test_save_receipt_must_follow_file_save(self):
        self.mutate("plugin","r401Committed = historyStore.saveWithReceipt(merged);",
                    "r401Committed = true;")
        self.refuse("R402_DELETION_TRANSACTION_ORDER_DRIFT")

    def test_shutdown_merge_checks_mutating(self):
        self.mutate("plugin","if (r402PanelEditMutating) return false;",
                    "if (false) return false;")
        self.refuse("R402_SHUTDOWN_MERGE_EDIT_GUARD_MISSING")

    def test_source_selector_exact(self):
        self.mutate("panel","r.matchesGroup(title, type)","r.isType(type)")
        self.refuse("R402_PANEL_DELETION_SELECTOR_DRIFT_removeSource")

    def test_type_selector_exact(self):
        self.mutate("panel","r.isType(type)","r.matchesGroup(title, type)")
        self.refuse("R402_PANEL_DELETION_SELECTOR_DRIFT_removeType")

    def test_record_identity_not_equality(self):
        self.mutate("panel","r == record","r.equals(record)")
        self.refuse("R402_PANEL_DELETION_SELECTOR_DRIFT_removeRecord")

    def test_source_delete_must_be_wrapped(self):
        self.mutate("panel","plugin.r402ApplyPanelDeletion(() ->",
                    "plugin.persistHistory();\n    plugin.r402ApplyPanelDeletion(() ->")
        self.refuse("R402_UNTRANSACTIONAL_PANEL_DELETE_removeSource")

    def test_panel_edit_must_rebuild(self):
        self.mutate("panel","      rebuild();","      noop();")
        self.refuse("R402_DELETION_TRANSACTION_ORDER_DRIFT")

    def test_previous_class_scope_enforced(self):
        self.new_classes[audit.CLASS(audit.PLUGIN)]=self.old_classes[audit.CLASS(audit.PLUGIN)]
        self.write()
        self.refuse("R402_TWO_SOURCE_CLASS_SCOPE_DRIFT")

    def test_previous_source_scope_enforced(self):
        self.plugin=self.old_plugin
        self.write()
        self.refuse("R402_TWO_SOURCE_CLASS_SCOPE_DRIFT")

    def test_golden_reference_pin(self):
        with self.assertRaisesRegex(audit.Refused,"ARCHIVE_SHA_DRIFT"):
            audit.audit(
                kit=self.kit,kit_sha="0"*64,
                reference=self.ref,reference_sha=sha(self.ref),
                previous_sources=self.oldsrc,previous_classes=self.oldcls,
                candidate_sources=self.newsrc,candidate_classes=self.newcls,
                expected_sources=3,expected_classes=3)

    def args(self,out):
        return [
          "--kit",str(self.kit),"--kit-sha256",sha(self.kit),
          "--reference",str(self.ref),"--reference-sha256",sha(self.ref),
          "--previous-sources",str(self.oldsrc),
          "--previous-classes",str(self.oldcls),
          "--candidate-sources",str(self.newsrc),
          "--candidate-classes",str(self.newcls),
          "--expected-sources","3","--expected-classes","3",
          "--out",str(out)]

    def test_output_cannot_overwrite(self):
        out=self.root/"report.json"
        out.write_text("KEEP")
        self.assertEqual(audit.main(self.args(out)),2)
        self.assertEqual(out.read_text(),"KEEP")

    def test_cli_positive_release_closed(self):
        out=self.root/"report.json"
        self.assertEqual(audit.main(self.args(out)),0)
        self.assertFalse(json.loads(out.read_text())["merge_approved"])

if __name__=="__main__":
    unittest.main()
