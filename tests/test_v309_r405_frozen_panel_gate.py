"""R405 public-only four-source/class SHA-pinned frozen panel gate tests.

Every Java fragment below is invented synthetic text. No private source,
actual client class, original game binary, user history or credentials.
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
    "r405_audit",ROOT/"tools/r405/audit_frozen_panel_snapshot.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

FAKE_ITEM="""
class InventedItem {
  synchronized void setName(String name) {this.name=name;}
  synchronized void setPrice(long price) {this.price=price;}
  synchronized void setIgnored(boolean ignored) {this.ignored=ignored;}
  synchronized void r404ApplyDefinition(String n,long p) {this.name=n;this.price=p;}
  synchronized LootTrackerItem r405FrozenCopy() {
    return new LootTrackerItem(id, name, quantity, price, ignored);
  }
}
"""
FAKE_RECORD="""
class InventedRecord {
  LootTrackerRecord r405FrozenCopy() {
    LootTrackerItem[] references = items.clone();
    LootTrackerItem[] frozen = new LootTrackerItem[references.length];
    for (int i = 0; i < references.length; ++i) {
      if (references[i] == null) {
        throw new IllegalStateException("invented item");
      }
      frozen[i] = references[i].r405FrozenCopy();
    }
    return new LootTrackerRecord(title, subTitle, type, frozen, kills, timestamp);
  }
}
"""
FAKE_PANEL="""
class InventedPanel {
  synchronized Collection<LootTrackerRecord> r405FrozenRecords() {
    List<LootTrackerRecord> frozen = new ArrayList<>(records.size());
    for (LootTrackerRecord record : records) {
      if (record == null) throw new IllegalStateException("invented record");
      frozen.add(record.r405FrozenCopy());
    }
    return frozen;
  }
  void updateIgnoredRecords() {
    synchronized (this) {
      for (LootTrackerRecord record : records) {
        applyIgnored(record, ignored);
      }
    }
    recountAggregates();
    rebuild();
  }
}
"""
FAKE_PLUGIN="""
class InventedPlugin {
  void reloadRecordedPrices() {
    SwingUtilities.invokeLater(() -> {
      synchronized (panel) {
        for (LootTrackerRecord record : panel.getAllRecords()) {
          for (LootTrackerItem item : record.getItems()) {
            ItemDefinition def = safeDefinition(item.getId());
            if (def == null) continue;
            String r404Name = "invented";
            long price = 3L;
            item.r404ApplyDefinition(r404Name, price);
          }
        }
      }
      panel.rebuild();
      requestSave();
    });
  }
  void persistHistory() {
    long r400Before;
    List<LootTrackerRecord> r400ConsistentMerged=null;
    List<LootTrackerRecord> r400ConsistentPending=null;
    long r401ConsistentClearGeneration;
    for(int r400Attempt=0;r400Attempt<5;++r400Attempt) {
      synchronized (r395HistoryGate) {
        r400Before = r400PanelHandoffVersion;
        r401ConsistentClearGeneration = r401ClearGeneration;
      }
      Collection<LootTrackerRecord> stored = panel.r405FrozenRecords();
      synchronized (r395HistoryGate) {
        if (r401ConsistentClearGeneration != r401ClearGeneration ||
            r400Before != r400PanelHandoffVersion) continue;
        r400ConsistentPending = new ArrayList<>(pendingRecords);
      }
      List<LootTrackerRecord> r405FrozenPending =
        new ArrayList<>(r400ConsistentPending.size());
      for (LootTrackerRecord pending : r400ConsistentPending) {
        r405FrozenPending.add(pending.r405FrozenCopy());
      }
      synchronized (r395HistoryGate) {
        if (r401ConsistentClearGeneration != r401ClearGeneration ||
            r400Before != r400PanelHandoffVersion) continue;
      }
      r400ConsistentMerged = new ArrayList<>(stored);
      r400ConsistentMerged.addAll(r405FrozenPending);
      break;
    }
    synchronized (r401FileGate) {
      historyStore.saveWithReceipt(merged);
    }
  }
}
"""

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

class R405SnapshotGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        r=Path(self.tmp.name)
        self.kit=r/"synthetic-kit.zip"
        self.reference=r/"synthetic-ref.jar"
        self.prior_src=r/"prior-source"
        self.current_src=r/"current-source"
        self.prior_cls=r/"prior-classes"
        self.current_cls=r/"current-classes"
        self.fake={
            audit.ITEM:FAKE_ITEM.encode("utf8"),
            audit.RECORD:FAKE_RECORD.encode("utf8"),
            audit.PANEL:FAKE_PANEL.encode("utf8"),
            audit.PLUGIN:FAKE_PLUGIN.encode("utf8"),
            audit.STORE:b"R404 synthetic unchanged store",
        }
        self.baseline={name:b"old synthetic "+name.encode("utf8")
                       for name in audit.GOLD_SRC}
        self.baseline[audit.STORE]=self.fake[audit.STORE]
        self.class_old={name:b"R404 synthetic previous "+name.encode("utf8")
                        for name in audit.GOLD_CLS}
        self.class_new=self.class_old.copy()
        for name in audit.CHANGED_CLS:
            self.class_new[name]=b"R405 synthetic new "+name.encode("utf8")
        self.write()

    @staticmethod
    def place(root,entries):
        root.mkdir(parents=True,exist_ok=True)
        for old in root.rglob("*"):
            if old.is_file():old.unlink()
        for name,data in entries.items():
            dst=root/name
            dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_bytes(data)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            for name in sorted(audit.GOLD_SRC):
                z.writestr("source/"+name,b"golden synthetic source")
        with ZipFile(self.reference,"w") as z:
            for name in sorted(audit.GOLD_CLS):
                z.writestr(name,b"golden synthetic class")
        self.place(self.prior_src,self.baseline)
        self.place(self.current_src,self.fake)
        self.place(self.prior_cls,self.class_old)
        self.place(self.current_cls,self.class_new)

    def run_gate(self):
        return audit.audit(
            kit=self.kit,kit_sha=sha(self.kit),
            reference=self.reference,reference_sha=sha(self.reference),
            previous_sources=self.prior_src,previous_classes=self.prior_cls,
            candidate_sources=self.current_src,candidate_classes=self.current_cls,
            expected_sources=5,expected_classes=7)

    def mutate(self,name,old,new):
        before=old.encode("utf8")
        self.assertIn(before,self.fake[name])
        self.fake[name]=self.fake[name].replace(before,new.encode("utf8"))
        self.write()

    def reject(self,error=None):
        if error:
            with self.assertRaisesRegex(audit.Refused,error):self.run_gate()
        else:
            with self.assertRaises(audit.Refused):self.run_gate()

    def test_valid_release_closed_synthetic(self):
        receipt=self.run_gate()
        self.assertEqual(receipt["status"],"R405_PRIVATE_FROZEN_PANEL_STATIC_GATE_PASS")
        self.assertEqual(receipt["modified_source_count_vs_r404"],4)
        self.assertEqual(receipt["modified_class_count_vs_r404"],4)
        for name in ("private_runtime_executed","real_edt_file_lock_latency_measured",
                     "every_possible_record_mutation_serialized","cross_process_writes_locked",
                     "power_loss_durability_proven","private_source_release_authorized",
                     "merge_approved"):
            self.assertFalse(receipt[name])

    def test_receipt_does_not_expose_private_text(self):
        rendered=json.dumps(self.run_gate())
        self.assertNotIn("InventedPlugin",rendered)
        self.assertNotIn("r405FrozenCopy()",rendered)
        self.assertNotIn("synthetic-kit.zip",rendered)

    def test_item_clone_requires_synchronized(self):
        self.mutate(audit.ITEM,"synchronized LootTrackerItem r405FrozenCopy()",
                    "LootTrackerItem r405FrozenCopy()")
        self.reject("R405_ITEM_FREEZE_MUST_USE_ITEM_MONITOR")

    def test_item_clone_must_be_new_object(self):
        self.mutate(audit.ITEM,"return new LootTrackerItem(id, name, quantity, price, ignored)",
                    "return this")
        self.reject()

    def test_mutable_item_price_setter_remains_synchronized(self):
        self.mutate(audit.ITEM,"synchronized void setPrice","void setPrice")
        self.reject("R405_ITEM_MUTATOR_MONITOR_DRIFT")

    def test_mutable_item_ignore_setter_remains_synchronized(self):
        self.mutate(audit.ITEM,"synchronized void setIgnored","void setIgnored")
        self.reject("R405_ITEM_MUTATOR_MONITOR_DRIFT")

    def test_definition_pair_stays_synchronized(self):
        self.mutate(audit.ITEM,"synchronized void r404ApplyDefinition",
                    "void r404ApplyDefinition")
        self.reject("R405_ITEM_MUTATOR_MONITOR_DRIFT")

    def test_record_clones_references_once(self):
        self.mutate(audit.RECORD,"items.clone()","items")
        self.reject("R405_CRITICAL_SOURCE_ORDER_DRIFT")

    def test_record_copies_each_item(self):
        self.mutate(audit.RECORD,"frozen[i] = references[i].r405FrozenCopy()",
                    "frozen[i] = references[i]")
        self.reject("R405_CRITICAL_SOURCE_ORDER_DRIFT")

    def test_record_rejects_null_item(self):
        self.mutate(audit.RECORD,"if (references[i] == null)","if (false)")
        self.reject("R405_CRITICAL_SOURCE_ORDER_DRIFT")

    def test_record_preserves_timestamp(self):
        self.mutate(audit.RECORD,"frozen, kills, timestamp","frozen, kills, 0")
        self.reject("R405_CRITICAL_SOURCE_ORDER_DRIFT")

    def test_record_preserves_raw_kills(self):
        self.mutate(audit.RECORD,"frozen, kills, timestamp",
                    "frozen, getCountedKills(), timestamp")
        self.reject("R405_MUST_PRESERVE_RAW_KILL_COUNT")

    def test_panel_freeze_requires_canonical_lock(self):
        self.mutate(audit.PANEL,"synchronized Collection<LootTrackerRecord> r405FrozenRecords",
                    "Collection<LootTrackerRecord> r405FrozenRecords")
        self.reject("R405_PANEL_FREEZE_MUST_USE_CANONICAL_PANEL_MONITOR")

    def test_panel_freeze_requires_deep_records(self):
        self.mutate(audit.PANEL,"frozen.add(record.r405FrozenCopy())","frozen.add(record)")
        self.reject("R405_CRITICAL_SOURCE_ORDER_DRIFT")

    def test_panel_freeze_rejects_null_record(self):
        self.mutate(audit.PANEL,"if (record == null)","if (false)")
        self.reject("R405_CRITICAL_SOURCE_ORDER_DRIFT")

    def test_panel_freeze_cannot_wait_on_edt(self):
        self.mutate(audit.PANEL,"return frozen;",
                    "SwingUtilities.invokeAndWait(action); return frozen;")
        self.reject("R405_PANEL_SNAPSHOT_MUST_NOT_BLOCK_ON_FILE_OR_CLIENT_GATE")

    def test_panel_freeze_cannot_lock_history_gate(self):
        self.mutate(audit.PANEL,"return frozen;",
                    "synchronized (r395HistoryGate) {} return frozen;")
        self.reject("R405_PANEL_SNAPSHOT_MUST_NOT_BLOCK_ON_FILE_OR_CLIENT_GATE")

    def test_price_refresh_requires_panel_monitor(self):
        self.mutate(audit.PLUGIN,"synchronized (panel)","synchronized (wrongPanel)")
        self.reject("R405_PRICE_BATCH_MUST_OWN_PANEL_MONITOR")

    def test_price_refresh_cannot_render_while_locked(self):
        self.mutate(audit.PLUGIN,"item.r404ApplyDefinition(r404Name, price);",
                    "item.r404ApplyDefinition(r404Name, price); panel.rebuild();")
        self.reject("R405_PANEL_RENDER_INSIDE_BATCH_LOCK")

    def test_price_refresh_must_update_inside_panel_monitor(self):
        self.mutate(audit.PLUGIN,"item.r404ApplyDefinition(r404Name, price);",
                    "noOp();")
        self.reject("R405_CRITICAL_SOURCE_ORDER_DRIFT")

    def test_ignored_batch_requires_panel_monitor(self):
        self.mutate(audit.PANEL,"synchronized (this)","synchronized (other)")
        self.reject("R405_IGNORED_BATCH_MONITOR_REGRESSION")

    def test_ignored_batch_must_update_inside_monitor(self):
        self.mutate(audit.PANEL,"applyIgnored(record, ignored);","noop();")
        self.reject("R405_CRITICAL_SOURCE_ORDER_DRIFT")

    def test_save_must_use_frozen_panel(self):
        self.mutate(audit.PLUGIN,"panel.r405FrozenRecords()","panel.getRecordsOffEdt()")
        self.reject("R405_WRITER_STILL_READS_LIVE_PANEL_RECORDS")

    def test_pending_must_be_frozen(self):
        self.mutate(audit.PLUGIN,"r405FrozenPending.add(pending.r405FrozenCopy())",
                    "r405FrozenPending.add(pending)")
        self.reject("R405_CRITICAL_SOURCE_ORDER_DRIFT")

    def test_post_clone_handoff_version_required(self):
        marker="""      synchronized (r395HistoryGate) {
        if (r401ConsistentClearGeneration != r401ClearGeneration ||
            r400Before != r400PanelHandoffVersion) continue;
      }
      r400ConsistentMerged"""
        self.mutate(audit.PLUGIN,marker,"      r400ConsistentMerged")
        self.reject("R405_PENDING_CLONE_REQUIRES_SECOND_HANDOFF_RECHECK")

    def test_post_clone_clear_generation_required(self):
        self.mutate(audit.PLUGIN,
                    "r400Before != r400PanelHandoffVersion) continue;\n      }\n      r400ConsistentMerged",
                    "false) continue;\n      }\n      r400ConsistentMerged")
        self.reject("R405_PENDING_CLONE_REQUIRES_SECOND_HANDOFF_RECHECK")

    def test_frozen_panel_must_be_outside_file_gate(self):
        self.mutate(audit.PLUGIN,
                    "historyStore.saveWithReceipt(merged)",
                    "panel.r405FrozenRecords(); historyStore.saveWithReceipt(merged)")
        self.reject("R405_MUST_FREEZE_RECORDS_OUTSIDE_FILE_GATE")

    def test_save_receipt_kept_inside_file_gate(self):
        self.mutate(audit.PLUGIN,"historyStore.saveWithReceipt(merged)",
                    "historyStore.save(merged)")
        self.reject("R405_CRITICAL_SOURCE_ORDER_DRIFT")

    def test_exact_source_set_rejects_panel_revert(self):
        self.fake[audit.PANEL]=self.baseline[audit.PANEL]
        self.write()
        self.reject("R405_FOUR_SOURCE_CLASS_SCOPE_DRIFT")

    def test_exact_class_set_rejects_extra_store_change(self):
        key=audit.P+"LootHistoryStore.class"
        self.class_new[key]=b"wrong additional synthetic store class"
        self.write()
        self.reject("R405_FOUR_SOURCE_CLASS_SCOPE_DRIFT")

    def test_exact_class_set_rejects_missing_record_change(self):
        key=audit.RECORD[:-5]+".class"
        self.class_new[key]=self.class_old[key]
        self.write()
        self.reject("R405_FOUR_SOURCE_CLASS_SCOPE_DRIFT")

    def test_sha_pin_rejects_modified_golden_archive(self):
        with self.assertRaisesRegex(audit.Refused,"ARCHIVE_SHA_DRIFT"):
            audit.audit(
                kit=self.kit,kit_sha="0"*64,
                reference=self.reference,reference_sha=sha(self.reference),
                previous_sources=self.prior_src,previous_classes=self.prior_cls,
                candidate_sources=self.current_src,candidate_classes=self.current_cls,
                expected_sources=5,expected_classes=7)

    def args(self,out):
        return [
            "--kit",str(self.kit),"--kit-sha256",sha(self.kit),
            "--reference",str(self.reference),"--reference-sha256",sha(self.reference),
            "--previous-sources",str(self.prior_src),
            "--previous-classes",str(self.prior_cls),
            "--candidate-sources",str(self.current_src),
            "--candidate-classes",str(self.current_cls),
            "--expected-sources","5","--expected-classes","7",
            "--out",str(out),
        ]

    def test_existing_receipt_not_overwritten(self):
        out=Path(self.tmp.name)/"result.json"
        out.write_text("KEEP",encoding="utf8")
        self.assertEqual(audit.main(self.args(out)),2)
        self.assertEqual(out.read_text("utf8"),"KEEP")

    def test_cli_produces_release_closed_receipt(self):
        out=Path(self.tmp.name)/"result.json"
        self.assertEqual(audit.main(self.args(out)),0)
        self.assertFalse(json.loads(out.read_text("utf8"))["merge_approved"])

if __name__=="__main__":
    unittest.main()
