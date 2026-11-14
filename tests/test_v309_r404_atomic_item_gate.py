"""R404 public synthetic exact-scope and atomic-item serialization negative tests.

All Java source strings in this test are fabricated fixtures; there is no
recovered private client source, private class file, or real loot history.
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
    "r404_gate",ROOT/"tools/r404/audit_atomic_item_snapshot.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

ITEM_SOURCE="""
class FabricatedItem {
  synchronized void setName(String name) {this.name = name;}
  synchronized void setPrice(long price) {this.price = price;}
  synchronized void setIgnored(boolean ignored) {this.ignored = ignored;}
  synchronized void r404ApplyDefinition(String newName, long newPrice) {
    if (newName != null) {
      name = newName;
    }
    if (newPrice > 0 || price <= 0) {
      price = newPrice;
    }
  }
}
"""
STORE_SOURCE="""
class FabricatedHistoryStore {
  static RecordDto from(LootTrackerRecord record) {
    LootTrackerItem[] capturedItems = record.getItems().clone();
    dto.items = new ArrayList<>(capturedItems.length);
    for (LootTrackerItem item : capturedItems) {
      dto.items.add(ItemDto.from(item));
    }
    return dto;
  }
  static ItemDto from(LootTrackerItem item) {
    if (item == null) {
      throw new IllegalArgumentException("synthetic");
    }
    synchronized (item) {
      ItemDto dto = new ItemDto();
      dto.id = item.getId();
      dto.name = item.getName();
      dto.quantity = item.getQuantity();
      dto.price = item.getPrice();
      dto.hidden = item.isIgnored();
      return dto;
    }
  }
}
"""
PLUGIN_SOURCE="""
class FabricatedPlugin {
  private void reloadRecordedPrices() {
    SwingUtilities.invokeLater(() -> {
      for (LootTrackerRecord record : panel.getAllRecords()) {
        for (LootTrackerItem item : record.getItems()) {
          ItemDefinition def = safeDefinition(item.getId());
          if (def == null) continue;
          String r404Name = def.name != null && !def.name.isEmpty()
            ? Text.stripFormatting(def.name) : null;
          long price = priceOf(item.getId(), def);
          item.r404ApplyDefinition(r404Name, price);
        }
      }
      requestSave();
    });
  }
  void persistHistory() {
    boolean ok = historyStore.saveWithReceipt(merged);
  }
  void r403QueueAutosave() {
    executor.execute(() -> persistHistory());
  }
}
"""

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

class R404GateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        r=Path(self.temp.name)
        self.kit=r/"original-kit.zip"
        self.ref=r/"original-class-reference.jar"
        self.old_source=r/"previous_source"
        self.new_source=r/"candidate_source"
        self.old_class=r/"previous_classes"
        self.new_class=r/"candidate_classes"
        self.item=ITEM_SOURCE.encode("utf8")
        self.store=STORE_SOURCE.encode("utf8")
        self.plugin=PLUGIN_SOURCE.encode("utf8")
        self.panel=b"unchanged fabricated panel"
        self.prev_item=b"previous fabricated item"
        self.prev_store=b"previous fabricated store"
        self.prev_plugin=b"previous fabricated plugin"
        self.prev_class={key:b"previous-class-"+key.encode("utf8")
                         for key in audit.GOLD_CLASS_CHANGED}
        self.curr_class=self.prev_class.copy()
        for key in audit.CLASS_CHANGED:
            self.curr_class[key]=b"candidate-class-"+key.encode("utf8")
        self.write()

    @staticmethod
    def tree(folder,items):
        folder.mkdir(parents=True,exist_ok=True)
        for f in folder.rglob("*"):
            if f.is_file():f.unlink()
        for key,value in items.items():
            p=folder/key
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(value)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            for name in audit.GOLD_SOURCE_CHANGED:
                z.writestr("source/"+name,b"original-synthetic-"+name.encode("utf8"))
        with ZipFile(self.ref,"w") as z:
            for key in audit.GOLD_CLASS_CHANGED:
                z.writestr(key,b"reference-synthetic-class-"+key.encode("utf8"))
        self.tree(self.old_source,{
            audit.ITEM:self.prev_item,
            audit.STORE:self.prev_store,
            audit.PLUGIN:self.prev_plugin,
            audit.PANEL:self.panel,
        })
        self.tree(self.new_source,{
            audit.ITEM:self.item,
            audit.STORE:self.store,
            audit.PLUGIN:self.plugin,
            audit.PANEL:self.panel,
        })
        self.tree(self.old_class,self.prev_class)
        self.tree(self.new_class,self.curr_class)

    def check(self):
        return audit.audit(
            kit=self.kit,kit_sha=digest(self.kit),
            reference=self.ref,reference_sha=digest(self.ref),
            previous_sources=self.old_source,previous_classes=self.old_class,
            candidate_sources=self.new_source,candidate_classes=self.new_class,
            expected_sources=4,expected_classes=6)

    def mutate(self,where,old,new):
        original=old.encode("utf8")
        current=getattr(self,where)
        self.assertIn(original,current)
        setattr(self,where,current.replace(original,new.encode("utf8")))
        self.write()

    def reject(self,reason=None):
        if reason:
            with self.assertRaisesRegex(audit.Refused,reason):self.check()
        else:
            with self.assertRaises(audit.Refused):self.check()

    def test_positive_scope_and_closed_release_flags(self):
        r=self.check()
        self.assertEqual(r["status"],"R404_PRIVATE_ITEM_SNAPSHOT_STATIC_GATE_PASS")
        self.assertEqual(r["changed_source_count_vs_r403"],3)
        self.assertEqual(r["changed_class_count_vs_r403"],4)
        for key in ("actual_private_client_executed","real_thread_schedule_verified",
                    "complete_panel_record_snapshot_atomic","cross_process_writes_locked",
                    "private_release_authorized","merge_approved"):
            self.assertFalse(r[key])

    def test_receipt_never_contains_source(self):
        data=json.dumps(self.check())
        for forbidden in ("FabricatedPlugin","FabricatedItem","record.getItems()",".jar"):
            self.assertNotIn(forbidden,data)

    def test_name_setter_synchronized(self):
        self.mutate("item","synchronized void setName(String name)",
                    "void setName(String name)")
        self.reject("R404_ITEM_MUTATOR_MUST_BE_SYNCHRONIZED")

    def test_price_setter_synchronized(self):
        self.mutate("item","synchronized void setPrice(long price)",
                    "void setPrice(long price)")
        self.reject("R404_ITEM_MUTATOR_MUST_BE_SYNCHRONIZED")

    def test_ignored_setter_synchronized(self):
        self.mutate("item","synchronized void setIgnored(boolean ignored)",
                    "void setIgnored(boolean ignored)")
        self.reject("R404_ITEM_MUTATOR_MUST_BE_SYNCHRONIZED")

    def test_definition_update_must_be_atomic(self):
        self.mutate("item","synchronized void r404ApplyDefinition",
                    "void r404ApplyDefinition")
        self.reject("R404_ATOMIC_DEFINITION_METHOD_REQUIRED")

    def test_definition_null_name_guard_required(self):
        self.mutate("item","if (newName != null)","if (true)")
        self.reject("R404_NULL_DEFINITION_NAME_MUST_BE_NOOP")

    def test_definition_name_assignment_required(self):
        self.mutate("item","name = newName;","name = null;")
        self.reject("R404_DEFINITION_NAME_NOT_UPDATED")

    def test_old_positive_price_fallback_preserved(self):
        self.mutate("item","if (newPrice > 0 || price <= 0)",
                    "if (newPrice > 0)")
        self.reject("R404_NOMINAL_PRICE_POLICY_CHANGED")

    def test_definition_price_assignment_required(self):
        self.mutate("item","price = newPrice;","price = 0L;")
        self.reject("R404_DEFINITION_PRICE_NOT_UPDATED")

    def test_item_update_cannot_take_disk_lock(self):
        self.mutate("item","name = newName;",
                    "synchronized (r401FileGate) {name = newName;}")
        self.reject("R404_ITEM_REFRESH_NESTS_PLUGIN_FILE_OR_HISTORY_GATE")

    def test_record_array_capture_required(self):
        self.mutate("store","record.getItems().clone()",
                    "record.getItems()")
        self.reject("R404_MUTATION_OR_SNAPSHOT_ORDER_DRIFT")

    def test_record_array_read_only_once(self):
        self.mutate("store","new ArrayList<>(capturedItems.length)",
                    "new ArrayList<>(capturedItems.length + record.getItems().length)")
        self.reject("R404_RECORD_ITEMS_READ_MULTIPLE_TIMES")

    def test_record_loop_must_use_captured_array(self):
        self.mutate("store","for (LootTrackerItem item : capturedItems)",
                    "for (LootTrackerItem item : record.getItems())")
        self.reject("R404_MUTATION_OR_SNAPSHOT_ORDER_DRIFT")

    def test_item_dto_requires_item_monitor(self):
        self.mutate("store","synchronized (item) {","if (true) {")
        self.reject("R404_MUTATION_OR_SNAPSHOT_ORDER_DRIFT")

    def test_item_dto_name_captured_under_monitor(self):
        self.mutate("store","dto.name = item.getName();","dto.name = \"old\";")
        self.reject("R404_MUTATION_OR_SNAPSHOT_ORDER_DRIFT")

    def test_item_dto_price_captured_under_monitor(self):
        self.mutate("store","dto.price = item.getPrice();","dto.price = 0L;")
        self.reject("R404_MUTATION_OR_SNAPSHOT_ORDER_DRIFT")

    def test_item_dto_hidden_captured_under_monitor(self):
        self.mutate("store","dto.hidden = item.isIgnored();","dto.hidden = false;")
        self.reject("R404_MUTATION_OR_SNAPSHOT_ORDER_DRIFT")

    def test_item_dto_quantity_captured_under_monitor(self):
        self.mutate("store","dto.quantity = item.getQuantity();","dto.quantity = 0;")
        self.reject("R404_MUTATION_OR_SNAPSHOT_ORDER_DRIFT")

    def test_item_dto_null_rejected(self):
        self.mutate("store","if (item == null)","if (false)")
        self.reject("R404_MUTATION_OR_SNAPSHOT_ORDER_DRIFT")

    def test_split_refresh_not_reintroduced(self):
        self.mutate("plugin","item.r404ApplyDefinition(r404Name, price);",
                    "item.setName(r404Name); item.setPrice(price);")
        self.reject()

    def test_definition_missing_name_policy_preserved(self):
        self.mutate("plugin","def.name != null && !def.name.isEmpty()",
                    "def.name != null")
        self.reject("R404_EMPTY_DEFINITION_NAME_POLICY_CHANGED")

    def test_definition_refresh_must_call_atomic_method_once(self):
        self.mutate("plugin","item.r404ApplyDefinition(r404Name, price);",
                    "noOp();")
        self.reject("R404_MUTATION_OR_SNAPSHOT_ORDER_DRIFT")

    def test_refreshed_values_must_request_save(self):
        self.mutate("plugin","requestSave();","noOp();")
        self.reject("R404_MUTATION_OR_SNAPSHOT_ORDER_DRIFT")

    def test_existing_worker_preserved(self):
        self.mutate("plugin","executor.execute(","executor.executeLater(")
        self.reject("R404_WORKER_REGRESSION")

    def test_existing_receipt_preserved(self):
        self.mutate("plugin","historyStore.saveWithReceipt(merged)",
                    "historyStore.save(merged)")
        self.reject("R404_STORE_RECEIPT_REGRESSION")

    def test_source_scope_refuses_extra_panel_revision(self):
        self.panel=b"additional fabricated panel change"
        self.write()
        self.reject("R404_THREE_SOURCE_FOUR_CLASS_SCOPE_DRIFT")

    def test_class_scope_refuses_extra_outer_store_revision(self):
        key=audit.PREFIX+"LootHistoryStore.class"
        self.curr_class[key]=b"unintended-outer-store-class-change"
        self.write()
        self.reject("R404_THREE_SOURCE_FOUR_CLASS_SCOPE_DRIFT")

    def test_class_scope_requires_inner_item_dto_revision(self):
        key=audit.PREFIX+"LootHistoryStore$ItemDto.class"
        self.curr_class[key]=self.prev_class[key]
        self.write()
        self.reject("R404_THREE_SOURCE_FOUR_CLASS_SCOPE_DRIFT")

    def test_source_scope_requires_all_three_changes(self):
        self.item=self.prev_item
        self.write()
        self.reject("R404_THREE_SOURCE_FOUR_CLASS_SCOPE_DRIFT")

    def test_original_source_hash_is_pinned(self):
        with self.assertRaisesRegex(audit.Refused,"ARCHIVE_SHA_DRIFT"):
            audit.audit(
                kit=self.kit,kit_sha="0"*64,
                reference=self.ref,reference_sha=digest(self.ref),
                previous_sources=self.old_source,previous_classes=self.old_class,
                candidate_sources=self.new_source,candidate_classes=self.new_class,
                expected_sources=4,expected_classes=6)

    def args(self,out):
        return [
            "--kit",str(self.kit),"--kit-sha256",digest(self.kit),
            "--reference",str(self.ref),"--reference-sha256",digest(self.ref),
            "--previous-sources",str(self.old_source),
            "--previous-classes",str(self.old_class),
            "--candidate-sources",str(self.new_source),
            "--candidate-classes",str(self.new_class),
            "--expected-sources","4","--expected-classes","6",
            "--out",str(out)]

    def test_refuses_overwriting_report(self):
        out=Path(self.temp.name)/"receipt.json"
        out.write_text("KEEP")
        self.assertEqual(audit.main(self.args(out)),2)
        self.assertEqual(out.read_text(),"KEEP")

    def test_cli_success_creates_closed_release_receipt(self):
        out=Path(self.temp.name)/"receipt.json"
        self.assertEqual(audit.main(self.args(out)),0)
        self.assertFalse(json.loads(out.read_text())["merge_approved"])

if __name__=="__main__":
    unittest.main()
