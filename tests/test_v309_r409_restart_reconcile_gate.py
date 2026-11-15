"""R409 public-only negative tests for exact source/class and durability gaps.

Every Java text string here is invented; the inputs are fake source and
fake class bytes. Does not include actual private client files or user data.
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
    "r409_public",ROOT/"tools/r409/audit_restart_reconcile_prerequisites.py")
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

SYNTH_STORE="""
class InventedStore {
 static final String FILE_NAME = "loot-history.json";
 private static final int FORMAT_VERSION = 1;
 private static final long MAX_HISTORY_BYTES = 64L * 1024L * 1024L;
 List<LootTrackerRecord> loadForMerge() {
    if (!file.exists()) {
       return new ArrayList<>();
    }
    Files.newInputStream(file.toPath());
    Document document = GSON.a(reader, Document.class);
    if (document.version != FORMAT_VERSION) return null;
    return records;
 }
 boolean saveWithReceipt(Collection<LootTrackerRecord> rows) {
    Document document = new Document();
    document.version = FORMAT_VERSION;
    for (LootTrackerRecord record : rows) {
       document.records.add(RecordDto.from(record));
    }
    File temp = new File(parent, FILE_NAME + ".tmp");
    Files.newOutputStream(temp.toPath());
    GSON.a(document, writer);
    AtomicFileReplace.move(temp, file);
    return true;
 }
}
"""
SYNTH_MOVE="""
class InventedAtomicFileReplace {
 static void move(File temp, File target) throws IOException {
   try {
     Files.move(temp.toPath(), target.toPath(),
        StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
   } catch (AtomicMoveNotSupportedException e) {
     Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING);
   }
   return;
 }
}
"""
SYNTH_PLUGIN="""
class InventedPlugin {
 void r402ApplyPanelDeletion(Runnable mutation) {
   if (!SwingUtilities.isEventDispatchThread()) return;
   synchronized (r401FileGate) {
      mutation.run();
      persistHistory();
      if (!r402EditWriteReceipt) {
         unsafe = true;
      }
   }
 }
 void loadHistory() {
    List<LootTrackerRecord> stored = restoreStore.loadForMerge();
    SwingUtilities.invokeLater(()->{
        restorePanel.addRecords(stored);
    });
 }
 void clearHistory() {
    ++r399SessionEpoch;
    r403AutosaveQueued = false;
    r403AutosaveDirty = false;
    historyStore.clearWithReceipt();
    panel.clearRecords();
 }
 void shutDown() {
    persistHistory();
 }
}
"""
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class R409PrivatePrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        r=Path(self.tmp.name)
        self.kit=r/"synthetic-kit.zip"
        self.ref=r/"synthetic-ref.jar"
        self.src=r/"invented-source"
        self.cls=r/"invented-classes"
        self.content={
            gate.STORE:SYNTH_STORE.encode("utf8"),
            gate.MOVE:SYNTH_MOVE.encode("utf8"),
            gate.PLUGIN:SYNTH_PLUGIN.encode("utf8"),
            gate.PANEL:b"class InventedPanel {}",
            gate.RECORD:b"class InventedRecord {}",
            gate.ITEM:b"class InventedItem {}",
        }
        self.classes={n:b"new-synthetic-class-"+n.encode("utf8")
                      for n in gate.CHANGED_CLASSES}
        self.write()

    @staticmethod
    def tree(root,mapping):
        root.mkdir(parents=True,exist_ok=True)
        for f in root.rglob("*"):
            if f.is_file():f.unlink()
        for n,body in mapping.items():
            f=root/n
            f.parent.mkdir(parents=True,exist_ok=True)
            f.write_bytes(body)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            for name in sorted(self.content):
                if name==gate.MOVE:
                    z.writestr("source/"+name,self.content[name])
                else:
                    z.writestr("source/"+name,b"earlier synthetic java")
        with ZipFile(self.ref,"w") as z:
            for name in sorted(gate.CHANGED_CLASSES):
                z.writestr(name,b"earlier synthetic class")
        self.tree(self.src,self.content)
        self.tree(self.cls,self.classes)

    def audit(self):
        return gate.audit(
            kit=self.kit,kit_sha=sha(self.kit),
            reference=self.ref,reference_sha=sha(self.ref),
            inspected_sources=self.src,inspected_classes=self.cls,
            expected_sources=6,expected_classes=7)

    def inspect(self):
        return gate.inspect(
            self.content[gate.PLUGIN],
            self.content[gate.STORE],
            self.content[gate.MOVE])

    def mutate(self,name,old,new):
        old=old.encode("utf8")
        self.assertIn(old,self.content[name])
        self.content[name]=self.content[name].replace(old,new.encode("utf8"))
        self.write()

    def reject(self,reason=None,structure_only=False):
        action=self.inspect if structure_only else self.audit
        if reason:
            with self.assertRaisesRegex(gate.Refused,reason):action()
        else:
            with self.assertRaises(gate.Refused):action()

    def test_positive_gap_report_is_not_release_approval(self):
        r=self.audit()
        self.assertEqual(r["status"],"R409_PRIVATE_RESTART_DURABILITY_GAPS_CONFIRMED")
        self.assertEqual(r["inspected_source_count"],6)
        self.assertEqual(r["inspected_class_count"],7)
        self.assertTrue(r["non_atomic_replace_fallback_present"])
        self.assertTrue(r["history_store_does_not_force_file_bytes_to_storage"])
        self.assertTrue(r["history_store_does_not_force_directory_metadata"])
        for key in (
            "private_source_changed_for_r409",
            "private_binary_built_for_r409",
            "actual_client_executed",
            "power_loss_durability_verified",
            "private_release_authorized",
            "merge_approved",
            "file_backed_synthetic_protocol_integrated"):
            self.assertFalse(r[key])

    def test_receipt_never_exposes_private_or_synthetic_source(self):
        r=json.dumps(self.audit())
        for marker in ("InventedStore","InventedPlugin",
                       "Files.move(","loot-history.json","synthetic-kit.zip"):
            self.assertNotIn(marker,r)

    def test_history_filename_must_be_current_one(self):
        self.mutate(gate.STORE,
            'FILE_NAME = "loot-history.json"',
            'FILE_NAME = "other.json"')
        self.reject("R409_HISTORY_FILENAME_CHANGED")

    def test_format_version_must_be_one(self):
        self.mutate(gate.STORE,"FORMAT_VERSION = 1","FORMAT_VERSION = 2")
        self.reject("R409_JSON_HISTORY_VERSION_CHANGED")

    def test_max_history_cap_required(self):
        self.mutate(gate.STORE,
            "MAX_HISTORY_BYTES = 64L * 1024L * 1024L",
            "MAX_HISTORY_BYTES = Long.MAX_VALUE")
        self.reject("R409_EXISTING_READ_CAP_CHANGED")

    def test_missing_file_still_loads_as_empty(self):
        self.mutate(gate.STORE,"if (!file.exists())","if (false)")
        self.reject("R409_SOURCE_RECEIPT_OR_FALLBACK_ORDER_DRIFT")

    def test_loading_requires_input_stream(self):
        self.mutate(gate.STORE,"Files.newInputStream(file.toPath())",
                    "noop()")
        self.reject()

    def test_load_requires_json_read(self):
        self.mutate(gate.STORE,"GSON.a(reader, Document.class)",
                    "new Document()")
        self.reject()

    def test_load_requires_version_check(self):
        self.mutate(gate.STORE,"document.version != FORMAT_VERSION",
                    "false")
        self.reject()

    def test_save_has_versioned_document(self):
        self.mutate(gate.STORE,"document.version = FORMAT_VERSION",
                    "document.version = 0")
        self.reject()

    def test_save_requires_record_dto(self):
        self.mutate(gate.STORE,"RecordDto.from(record)","record.toString()")
        self.reject()

    def test_save_requires_expected_temp_suffix(self):
        self.mutate(gate.STORE,'FILE_NAME + ".tmp"','FILE_NAME + ".bak"')
        self.reject("R409_HISTORY_TEMP_NAMING_DRIFT")

    def test_save_requires_disk_output(self):
        self.mutate(gate.STORE,
            "Files.newOutputStream(temp.toPath())",
            "openInMemoryWriter()")
        self.reject()

    def test_save_requires_gson_serialization(self):
        self.mutate(gate.STORE,"GSON.a(document, writer)","noop()")
        self.reject()

    def test_save_requires_move_helper(self):
        self.mutate(gate.STORE,
            "AtomicFileReplace.move(temp, file)",
            "Files.copy(temp, file)")
        self.reject()

    def test_save_requires_success_receipt_after_move(self):
        self.mutate(gate.STORE,"    return true;","    return false;")
        self.reject()

    def test_atomic_move_is_attempted_first(self):
        self.mutate(gate.MOVE,
            "StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE",
            "StandardCopyOption.REPLACE_EXISTING")
        self.reject(structure_only=True)

    def test_non_atomic_fallback_detected(self):
        self.mutate(gate.MOVE,
            "catch (AtomicMoveNotSupportedException e)",
            "catch (IOException e)")
        self.reject(structure_only=True)

    def test_non_atomic_fallback_line_detected(self):
        self.mutate(gate.MOVE,
            "Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING)",
            "noop()")
        self.reject(structure_only=True)

    def test_directory_force_cannot_be_mistaken_as_original(self):
        self.mutate(gate.MOVE,
            "   return;",
            "   directory.force(true); return;")
        self.reject(structure_only=True)

    def test_atomic_helper_must_match_original_byte_for_byte(self):
        self.mutate(gate.MOVE,"   return;","   return; // changed helper")
        self.reject("R409_R407_ORIGINAL_SOURCE_SCOPE_DRIFT")

    def test_delete_from_edt_required_currently(self):
        self.mutate(gate.PLUGIN,
            "SwingUtilities.isEventDispatchThread()",
            "thread.alive()")
        self.reject()

    def test_delete_still_owns_file_gate(self):
        self.mutate(gate.PLUGIN,
            "synchronized (r401FileGate) {",
            "synchronized (otherGate) {")
        self.reject()

    def test_delete_mutation_must_precede_sync_save(self):
        self.mutate(gate.PLUGIN,
            "      mutation.run();\n      persistHistory();",
            "      persistHistory();\n      mutation.run();")
        self.reject()

    def test_delete_receipt_must_remain_checked(self):
        self.mutate(gate.PLUGIN,"if (!r402EditWriteReceipt)","if (false)")
        self.reject()

    def test_startup_reads_restored_history(self):
        self.mutate(gate.PLUGIN,
            "restoreStore.loadForMerge()",
            "restoreStore.load()")
        self.reject()

    def test_startup_restores_only_on_edt(self):
        self.mutate(gate.PLUGIN,"SwingUtilities.invokeLater(",
            "executor.execute(")
        self.reject()

    def test_startup_applies_loaded_records(self):
        self.mutate(gate.PLUGIN,"restorePanel.addRecords(stored)",
                    "restorePanel.removeAll()")
        self.reject()

    def test_clear_keeps_epoch_fence(self):
        self.mutate(gate.PLUGIN,"++r399SessionEpoch","--r399SessionEpoch")
        self.reject()

    def test_clear_keeps_queue_reset(self):
        self.mutate(gate.PLUGIN,"r403AutosaveQueued = false",
                    "r403AutosaveQueued = true")
        self.reject()

    def test_clear_requires_disk_receipt(self):
        self.mutate(gate.PLUGIN,"historyStore.clearWithReceipt()",
                    "historyStore.clear()")
        self.reject()

    def test_shutdown_keeps_final_flush(self):
        self.mutate(gate.PLUGIN,
            " void shutDown() {\n    persistHistory();",
            " void shutDown() {\n    noop();")
        self.reject()

    def test_no_extra_unexpected_private_java(self):
        self.content[gate.ITEM]=b"earlier synthetic java"
        self.write()
        self.reject("R409_R407_ORIGINAL_SOURCE_SCOPE_DRIFT")

    def test_class_delta_scope_refuses_missing_plugin(self):
        self.classes[gate.P+"LootTrackerPlugin.class"]=b"earlier synthetic class"
        self.write()
        self.reject("R409_R407_ORIGINAL_CLASS_SCOPE_DRIFT")

    def test_sha_pin_refuses_untrusted_original(self):
        with self.assertRaisesRegex(gate.Refused,"ARCHIVE_SHA_DRIFT"):
            gate.audit(
                kit=self.kit,kit_sha="0"*64,
                reference=self.ref,reference_sha=sha(self.ref),
                inspected_sources=self.src,inspected_classes=self.cls,
                expected_sources=6,expected_classes=7)

    def args(self,path):
        return [
            "--kit",str(self.kit),"--kit-sha256",sha(self.kit),
            "--reference",str(self.ref),"--reference-sha256",sha(self.ref),
            "--inspected-sources",str(self.src),
            "--inspected-classes",str(self.cls),
            "--expected-sources","6","--expected-classes","7",
            "--out",str(path)
        ]

    def test_existing_receipt_is_not_overwritten(self):
        out=Path(self.tmp.name)/"receipt.json"
        out.write_text("KEEP")
        self.assertEqual(gate.main(self.args(out)),2)
        self.assertEqual(out.read_text(),"KEEP")

    def test_cli_receipt_remains_unmerged(self):
        out=Path(self.tmp.name)/"receipt.json"
        self.assertEqual(gate.main(self.args(out)),0)
        self.assertFalse(json.loads(out.read_text())["merge_approved"])

if __name__=="__main__":
    unittest.main()
