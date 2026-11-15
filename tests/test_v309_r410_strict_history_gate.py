"""R410 public-only source/class gate negative tests with invented Java bytes.

No recovered source, compiled game class, real history file, account or
user data is embedded in these synthetic tests.
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
    "r410_public_gate",ROOT/"tools/r410/audit_strict_history_atomic_replace.py")
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

FAKE_MOVE_BEFORE="""
class FabricatedMove {
 static void move(File temp, File target) throws IOException {
   try {
     Files.move(temp.toPath(), target.toPath(),
       StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
   } catch (AtomicMoveNotSupportedException e) {
     Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING);
   }
 }
}
"""
FAKE_MOVE_AFTER="""
class FabricatedMove {
 static void move(File temp, File target) throws IOException {
   try {
     Files.move(temp.toPath(), target.toPath(),
       StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
   } catch (AtomicMoveNotSupportedException e) {
     Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING);
   }
 }
 static void moveStrict(File temp, File target) throws IOException {
   if (!temp.getCanonicalFile().getParentFile().equals(
       target.getCanonicalFile().getParentFile())) {
     throw new IOException("synthetic other directory");
   }
   for (int attempt=1;;attempt++) {
     try {
       Files.move(temp.toPath(), target.toPath(),
         StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
       return;
     }
     catch (AtomicMoveNotSupportedException unsupported) {
       throw unsupported;
     }
     catch (FileSystemException locked) {
       if (attempt >= MAX_ATTEMPTS) {
          throw locked;
       }
       try {
          Thread.sleep(RETRY_DELAY_MS);
       } catch (InterruptedException interrupted) {
          Thread.currentThread().interrupt();
          throw new IOException("synthetic interruption",interrupted);
       }
     }
   }
 }
}
"""
FAKE_STORE_BEFORE="""
class FabricatedHistoryStore {
  List<LootTrackerRecord> loadForMerge() {
    return new ArrayList<>();
  }
  boolean clearWithReceipt() {
    return true;
  }
  void save(Collection<LootTrackerRecord> records) {
    saveWithReceipt(records);
  }
  boolean saveWithReceipt(Collection<LootTrackerRecord> records) {
    if (records == null) return false;
    Document document = new Document();
    document.version = FORMAT_VERSION;
    for (LootTrackerRecord record : records) {
      document.records.add(RecordDto.from(record));
    }
    File temp = new File(parent, FILE_NAME + ".tmp");
    try (BufferedWriter writer = new BufferedWriter(
       new OutputStreamWriter(Files.newOutputStream(temp.toPath()), StandardCharsets.UTF_8))) {
       GSON.a(document, writer);
    } catch (IOException e) {
       return false;
    }
    try {
       AtomicFileReplace.move(temp, file);
       return true;
    } catch (IOException e) {
       return false;
    }
  }
}
"""
FAKE_STORE_AFTER="""
class FabricatedHistoryStore {
  List<LootTrackerRecord> loadForMerge() {
    return new ArrayList<>();
  }
  boolean clearWithReceipt() {
    return true;
  }
  void save(Collection<LootTrackerRecord> records) {
    saveWithReceipt(records);
  }
  boolean saveWithReceipt(Collection<LootTrackerRecord> records) {
    if (records == null) return false;
    Document document = new Document();
    document.version = FORMAT_VERSION;
    for (LootTrackerRecord record : records) {
      document.records.add(RecordDto.from(record));
    }
    File temp = new File(parent, FILE_NAME + ".tmp");
    try (FileChannel channel = FileChannel.open(temp.toPath(),
           StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
         BufferedWriter writer = new BufferedWriter(
           new OutputStreamWriter(Channels.newOutputStream(channel), StandardCharsets.UTF_8))) {
       GSON.a(document, writer);
       writer.flush();
       channel.force(true);
    } catch (IOException e) {
       return false;
    }
    try {
       AtomicFileReplace.moveStrict(temp, file);
       return true;
    } catch (IOException e) {
       return false;
    }
  }
}
"""
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

class R410StrictHistoryGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.kit=root/"invented-original.zip"
        self.reference=root/"invented-original.jar"
        self.prior_src=root/"prior-source"
        self.new_src=root/"candidate-source"
        self.prior_cls=root/"prior-classes"
        self.new_cls=root/"candidate-classes"
        self.old_move=FAKE_MOVE_BEFORE.encode()
        self.new_move=FAKE_MOVE_AFTER.encode()
        self.old_store=FAKE_STORE_BEFORE.encode()
        self.new_store=FAKE_STORE_AFTER.encode()
        self.cache=b"class FabricatedPriceCache {}"
        self.other={
            gate.PLUGIN:b"class InventedPlugin {}",
            gate.PANEL:b"class InventedPanel {}",
            gate.ITEM:b"class InventedItem {}",
            gate.RECORD:b"class InventedRecord {}",
        }
        self.prior={gate.MOVER:self.old_move,gate.STORE:self.old_store,
                    gate.CACHE:self.cache,**self.other}
        self.current={gate.MOVER:self.new_move,gate.STORE:self.new_store,
                      gate.CACHE:self.cache,**self.other}
        self.class_prior={
            name:b"previous fabricated class "+name.encode()
            for name in gate.GOLD_CLS}
        self.class_new=self.class_prior.copy()
        for name in gate.NEW_CLS:
            self.class_new[name]=b"new fabricated class "+name.encode()
        self.write()

    @staticmethod
    def write_tree(root,items):
        root.mkdir(parents=True,exist_ok=True)
        for existing in root.rglob("*"):
            if existing.is_file():existing.unlink()
        for name,content in items.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(content)

    def write(self):
        with ZipFile(self.kit,"w") as archive:
            for name in sorted(self.current):
                content=(self.old_move if name==gate.MOVER else
                    self.cache if name==gate.CACHE else b"synthetic original Java")
                archive.writestr("source/"+name,content)
        with ZipFile(self.reference,"w") as archive:
            for name in sorted(gate.GOLD_CLS):
                archive.writestr(name,b"synthetic original class")
        self.write_tree(self.prior_src,self.prior)
        self.write_tree(self.new_src,self.current)
        self.write_tree(self.prior_cls,self.class_prior)
        self.write_tree(self.new_cls,self.class_new)

    def gate(self):
        return gate.audit(
            kit=self.kit,kit_sha=sha(self.kit),
            reference=self.reference,reference_sha=sha(self.reference),
            previous_sources=self.prior_src,previous_classes=self.prior_cls,
            candidate_sources=self.new_src,candidate_classes=self.new_cls,
            expected_sources=7,expected_classes=8)

    def mutate(self,name,old,new):
        source=self.current[name];anchor=old.encode()
        self.assertIn(anchor,source)
        self.current[name]=source.replace(anchor,new.encode())
        self.write()

    def refuse(self,message=None):
        if message:
            with self.assertRaisesRegex(gate.Refused,message):self.gate()
        else:
            with self.assertRaises(gate.Refused):self.gate()

    def test_positive_exact_two_class_gate_release_closed(self):
        receipt=self.gate()
        self.assertEqual(receipt["status"],"R410_PRIVATE_STRICT_HISTORY_ATOMIC_GATE_PASS")
        self.assertEqual(receipt["modified_sources_vs_r407"],2)
        self.assertEqual(receipt["modified_classes_vs_r407"],2)
        for key in ("directory_metadata_forced","durable_journal_integrated",
                    "power_loss_survivability_proven","private_release_authorized",
                    "confirmed_edt_deletion_made_nonblocking","merge_approved"):
            self.assertFalse(receipt[key])

    def test_report_contains_no_invented_or_private_source(self):
        report=json.dumps(self.gate())
        for marker in ("FabricatedHistoryStore","Files.move(", "invented-original.zip",
                       "synthetic original Java"):
            self.assertNotIn(marker,report)

    def test_price_cache_source_byte_identical(self):
        self.current[gate.CACHE]=b"changed price cache"
        self.write()
        self.refuse("R410_PRICE_CACHE_SOURCE_MUST_BE_BYTE_IDENTICAL")

    def test_old_legacy_move_method_unchanged(self):
        self.mutate(gate.MOVER,"catch (AtomicMoveNotSupportedException e)",
                    "catch (IOException e)")
        self.refuse("R410_LEGACY_PRICE_CACHE_MOVE_CHANGED")

    def test_history_reader_must_remain_byte_semantically_equal(self):
        self.mutate(gate.STORE,"return new ArrayList<>()","return null")
        self.refuse("R410_HISTORY_READER_CHANGED")

    def test_clear_all_receipt_must_remain_unchanged(self):
        self.mutate(gate.STORE,
                    "boolean clearWithReceipt() {\n    return true;",
                    "boolean clearWithReceipt() {\n    return false;")
        self.refuse("R410_CLEAR_ALL_DISK_RECEIPT_CHANGED")

    def test_existing_public_save_dispatch_not_removed(self):
        self.mutate(gate.STORE,"    saveWithReceipt(records);",
                    "    noop();")
        self.refuse("R410_HISTORY_SAVE_DISPATCH_CHANGED")

    def test_same_parent_check_required(self):
        self.mutate(gate.MOVER,
                    "temp.getCanonicalFile().getParentFile().equals(",
                    "otherFile.getCanonicalFile().getParentFile().equals(")
        self.refuse()

    def test_strict_parent_target_required(self):
        self.mutate(gate.MOVER,
                    "target.getCanonicalFile().getParentFile()",
                    "null")
        self.refuse()

    def test_strict_replacement_must_use_atomic_move(self):
        self.mutate(gate.MOVER,
                    "StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE",
                    "StandardCopyOption.REPLACE_EXISTING")
        self.refuse()

    def test_strict_must_not_fallback_to_plain_replace(self):
        self.mutate(gate.MOVER,
                    "throw unsupported;",
                    "Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING);")
        self.refuse("R410_CRITICAL_WRITE_OR_MOVE_ORDER_DRIFT")

    def test_strict_unsupported_exception_not_swallowed(self):
        self.mutate(gate.MOVER,"catch (AtomicMoveNotSupportedException unsupported)",
                    "catch (IOException unsupported)")
        self.refuse()

    def test_strict_retries_transient_lock_errors(self):
        self.mutate(gate.MOVER,"catch (FileSystemException locked)",
                    "catch (IOException locked)")
        self.refuse()

    def test_strict_retry_must_have_limit(self):
        self.mutate(gate.MOVER,"if (attempt >= MAX_ATTEMPTS)",
                    "if (false)")
        self.refuse()

    def test_strict_raises_last_lock_error(self):
        self.mutate(gate.MOVER,"throw locked;","noop();")
        self.refuse()

    def test_strict_interrupted_thread_flag_restored(self):
        self.mutate(gate.MOVER,"Thread.currentThread().interrupt()",
                    "noop()")
        self.refuse()

    def test_strict_does_not_copy_instead_of_move(self):
        self.mutate(gate.MOVER,"throw unsupported;",
                    "Files.copy(temp.toPath(), target.toPath()); throw unsupported;")
        self.refuse("R410_STRICT_REPLACEMENT_MUST_NOT_COPY")

    def test_strict_excludes_second_move_path(self):
        self.mutate(gate.MOVER,
                    "       return;\n     }\n     catch (AtomicMoveNotSupportedException unsupported)",
                    "       Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING);\n       return;\n     }\n     catch (AtomicMoveNotSupportedException unsupported)")
        self.refuse()

    def test_history_must_use_strict_move(self):
        self.mutate(gate.STORE,"AtomicFileReplace.moveStrict(temp, file)",
                    "AtomicFileReplace.move(temp, file)")
        self.refuse()

    def test_staged_file_must_be_create_new(self):
        self.mutate(gate.STORE,"StandardOpenOption.CREATE_NEW",
                    "StandardOpenOption.CREATE")
        self.refuse()

    def test_staged_file_must_be_write_opened(self):
        self.mutate(gate.STORE,"StandardOpenOption.WRITE",
                    "StandardOpenOption.READ")
        self.refuse()

    def test_staged_file_must_use_owned_filechannel(self):
        self.mutate(gate.STORE,"FileChannel.open(temp.toPath()",
                    "Files.newOutputStream(temp.toPath()")
        self.refuse()

    def test_staged_file_must_use_same_output_channel(self):
        self.mutate(gate.STORE,"Channels.newOutputStream(channel)",
                    "new ByteArrayOutputStream()")
        self.refuse()

    def test_stage_force_required(self):
        self.mutate(gate.STORE,"channel.force(true)","noop()")
        self.refuse()

    def test_stage_force_must_include_metadata(self):
        self.mutate(gate.STORE,"channel.force(true)","channel.force(false)")
        self.refuse()

    def test_stage_flush_precedes_force(self):
        self.mutate(gate.STORE,
                    "       writer.flush();\n       channel.force(true);",
                    "       channel.force(true);\n       writer.flush();")
        self.refuse()

    def test_stage_force_must_precede_atomic_move(self):
        self.mutate(gate.STORE,
                    "       channel.force(true);\n    } catch (IOException e)",
                    "    } catch (IOException e)")
        self.refuse()

    def test_writer_must_serialize_document(self):
        self.mutate(gate.STORE,"GSON.a(document, writer)",
                    "noop()")
        self.refuse()

    def test_history_save_preserves_false_io_receipt(self):
        self.mutate(gate.STORE,
                    "    } catch (IOException e) {\n       return false;",
                    "    } catch (IOException e) {\n       return true;")
        self.refuse()

    def test_history_ambiguous_orphan_not_deleted_by_default(self):
        self.mutate(gate.STORE,
                    "AtomicFileReplace.moveStrict(temp, file)",
                    "Files.deleteIfExists(temp.toPath()); AtomicFileReplace.moveStrict(temp, file)")
        self.refuse("R410_UNEXPLAINED_TEMP_AUTOCLEANUP")

    def test_extra_store_source_refused(self):
        self.current[gate.PANEL]=b"different invented panel"
        self.write()
        self.refuse("R410_EXACT_TWO_SOURCE_TWO_CLASS_REQUIRED")

    def test_extra_class_refused(self):
        self.class_new[gate.P+"LootTrackerPanel.class"]=b"unexpected synthetic panel"
        self.write()
        self.refuse("R410_EXACT_TWO_SOURCE_TWO_CLASS_REQUIRED")

    def test_missing_strict_mover_class_refused(self):
        self.class_new[gate.P+"AtomicFileReplace.class"]=self.class_prior[gate.P+"AtomicFileReplace.class"]
        self.write()
        self.refuse("R410_EXACT_TWO_SOURCE_TWO_CLASS_REQUIRED")

    def test_pinned_archive_digest_required(self):
        with self.assertRaisesRegex(gate.Refused,"ARCHIVE_SHA_DRIFT"):
            gate.audit(
                kit=self.kit,kit_sha="0"*64,
                reference=self.reference,reference_sha=sha(self.reference),
                previous_sources=self.prior_src,previous_classes=self.prior_cls,
                candidate_sources=self.new_src,candidate_classes=self.new_cls,
                expected_sources=7,expected_classes=8)

    def args(self,out):
        return [
            "--kit",str(self.kit),"--kit-sha256",sha(self.kit),
            "--reference",str(self.reference),
            "--reference-sha256",sha(self.reference),
            "--previous-sources",str(self.prior_src),
            "--previous-classes",str(self.prior_cls),
            "--candidate-sources",str(self.new_src),
            "--candidate-classes",str(self.new_cls),
            "--expected-sources","7","--expected-classes","8",
            "--out",str(out)
        ]

    def test_existing_report_must_not_be_replaced(self):
        out=Path(self.temp.name)/"receipt.json"
        out.write_text("KEEP")
        self.assertEqual(gate.main(self.args(out)),2)
        self.assertEqual(out.read_text(),"KEEP")

    def test_cli_report_keeps_release_closed(self):
        out=Path(self.temp.name)/"receipt.json"
        self.assertEqual(gate.main(self.args(out)),0)
        self.assertFalse(json.loads(out.read_text())["merge_approved"])

if __name__=="__main__":
    unittest.main()
