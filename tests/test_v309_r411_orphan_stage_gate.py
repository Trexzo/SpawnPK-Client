"""R411 public synthetic gate tests for fail-closed orphan-stage admission.

All Java strings and class bytes are invented. No recovered client source,
private class, player history or real staging file is included or read.
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
    "r411_public",ROOT/"tools/r411/audit_orphan_stage_quarantine.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

COMMON_HEAD="""
class InventedHistory {
  File file;
  static final String FILE_NAME="invented-history.txt";
  File getFile() {return file;}
  void save(Collection<InventedRow> data) {saveWithReceipt(data);}
  List<InventedRow> load() {
    List<InventedRow> value=loadForMerge();
    return value==null?new ArrayList<>():value;
  }
  static boolean deleteTree(File f) {
    Files.deleteIfExists(f.toPath());
    return true;
  }
"""
COMMON_END="""}
"""
OLD_BODY="""
  void deleteStale() {
    Files.deleteIfExists(retired.toPath());
  }
  List<InventedRow> loadForMerge() {
    if (!file.exists())return new ArrayList<>();
    return restored;
  }
  boolean saveWithReceipt(Collection<InventedRow> records) {
    if (records == null)return false;
    try (FileChannel channel = FileChannel.open(temp.toPath(),
        StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
         BufferedWriter writer = new BufferedWriter(
         new OutputStreamWriter(Channels.newOutputStream(channel), StandardCharsets.UTF_8))) {
      GSON.a(document, writer);
      writer.flush();
      channel.force(true);
    }catch (IOException error) {
      return false;
    }
    AtomicFileReplace.moveStrict(temp, file);
    return true;
  }
  boolean clearWithReceipt() {
    Files.deleteIfExists(file.toPath());
    return true;
  }
"""
STAGE_CODE="""
  enum R411StageState {CLEAR, ORPHAN, UNSAFE}
  R411StageState r411StageState() {
    final File staging=new File(file.getParentFile(), FILE_NAME + ".tmp");
    try {
      final BasicFileAttributes attrs = Files.readAttributes(staging.toPath(),
          BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
      return attrs.isRegularFile() ? R411StageState.ORPHAN : R411StageState.UNSAFE;
    }
    catch (NoSuchFileException missing) {
      return R411StageState.CLEAR;
    }
    catch (IOException | SecurityException unreadable) {
      return R411StageState.UNSAFE;
    }
  }
  private boolean r411RefuseUnresolvedStage(String operation) {
    final R411StageState stage = r411StageState();
    if (stage == R411StageState.CLEAR) {
      return false;
    }
    return true;
  }
"""
NEW_BODY="""
  void deleteStale() {
    if (r411RefuseUnresolvedStage("legacy cleanup")) {
      return;
    }
    Files.deleteIfExists(retired.toPath());
  }
  List<InventedRow> loadForMerge() {
    if (r411RefuseUnresolvedStage("history restoration")) {
      return null;
    }
    if (!file.exists())return new ArrayList<>();
    return restored;
  }
  boolean saveWithReceipt(Collection<InventedRow> records) {
    if (r411RefuseUnresolvedStage("history save")) {
      return false;
    }
    if (records == null)return false;
    try (FileChannel channel = FileChannel.open(temp.toPath(),
        StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
         BufferedWriter writer = new BufferedWriter(
         new OutputStreamWriter(Channels.newOutputStream(channel), StandardCharsets.UTF_8))) {
      GSON.a(document, writer);
      writer.flush();
      channel.force(true);
    }catch (IOException error) {
      return false;
    }
    AtomicFileReplace.moveStrict(temp, file);
    return true;
  }
  boolean clearWithReceipt() {
    if (r411RefuseUnresolvedStage("clear all")) {
      return false;
    }
    Files.deleteIfExists(file.toPath());
    return true;
  }
"""
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class R411SyntheticGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.kit=root/"synthetic-kit.zip"
        self.reference=root/"synthetic-reference.jar"
        self.oldsrc=root/"prior-source"
        self.newsrc=root/"new-source"
        self.oldcls=root/"prior-class"
        self.newcls=root/"new-class"
        self.old_store=(COMMON_HEAD+OLD_BODY+COMMON_END).encode()
        self.new_store=(COMMON_HEAD+STAGE_CODE+NEW_BODY+COMMON_END).encode()
        self.non_store={
            audit.MOVE:b"class InventedAtomicFileReplace {}",
            audit.PRICE:b"class InventedTradingPostPrices {}",
            "rs/plugins/loottracker/LootTrackerPlugin.java":b"class InventedPlugin {}",
            "rs/plugins/loottracker/LootTrackerPanel.java":b"class InventedPanel {}",
            "rs/plugins/loottracker/LootTrackerItem.java":b"class InventedItem {}",
            "rs/plugins/loottracker/LootTrackerRecord.java":b"class InventedRecord {}",
        }
        self.previous={**self.non_store,audit.STORE:self.old_store}
        self.current={**self.non_store,audit.STORE:self.new_store}
        self.oldclasses={
            n:b"invented previous class "+n.encode()
            for n in audit.CLASS_DIFF_VS_R381}
        self.currentclasses=self.oldclasses.copy()
        self.currentclasses[next(iter(audit.CHANGED_CLASS))]=b"new stage-aware store class"
        self.currentclasses[next(iter(audit.ADDED_CLASS))]=b"new invented enum class"
        self.write()

    @staticmethod
    def files(folder,entries):
        folder.mkdir(parents=True,exist_ok=True)
        for old in folder.rglob("*"):
            if old.is_file():old.unlink()
        for name,content in entries.items():
            path=folder/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(content)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            for name in sorted(self.previous):
                if name==audit.PRICE:
                    before=self.non_store[audit.PRICE]
                else:
                    before=b"fabricated reference source"
                z.writestr("source/"+name,before)
        with ZipFile(self.reference,"w") as z:
            for name in sorted(audit.CLASS_DIFF_VS_R381):
                z.writestr(name,b"fabricated reference class")
        self.files(self.oldsrc,self.previous)
        self.files(self.newsrc,self.current)
        self.files(self.oldcls,self.oldclasses)
        self.files(self.newcls,self.currentclasses)

    def run_audit(self):
        return audit.audit(
            kit=self.kit,kit_sha=sha(self.kit),
            reference=self.reference,reference_sha=sha(self.reference),
            previous_sources=self.oldsrc,previous_classes=self.oldcls,
            candidate_sources=self.newsrc,candidate_classes=self.newcls,
            expected_sources=7,previous_class_count=8,candidate_class_count=9)

    def mutate(self,source,old,new):
        raw=self.current[source]
        self.assertIn(old.encode(),raw)
        self.current[source]=raw.replace(old.encode(),new.encode())
        self.write()

    def refuse(self,why=None):
        if why:
            with self.assertRaisesRegex(audit.Refused,why):self.run_audit()
        else:
            with self.assertRaises(audit.Refused):self.run_audit()

    def test_positive_exact_one_source_added_enum_and_release_closed(self):
        report=self.run_audit()
        self.assertEqual(report["status"],"R411_PRIVATE_ORPHAN_STAGE_STATIC_GATE_PASS")
        self.assertEqual(report["changed_source_count_vs_r410"],1)
        self.assertEqual(report["changed_existing_class_count_vs_r410"],1)
        self.assertEqual(report["new_nested_enum_class_count"],1)
        for key in (
            "private_client_executed","production_history_modified",
            "staging_payload_read","staging_file_automatically_deleted",
            "automatic_orphan_recovery_or_cleanup_implemented",
            "restart_transaction_journal_integrated",
            "physical_power_loss_recovery_proven",
            "private_release_authorized","merge_approved"):
            self.assertFalse(report[key])

    def test_report_does_not_expose_private_or_synthetic_code(self):
        rendered=json.dumps(self.run_audit())
        for phrase in ("InventedHistory","staging.toPath()","synthetic-kit.zip","invented-history.txt"):
            self.assertNotIn(phrase,rendered)

    def test_probe_requires_nofollow_symlink_metadata(self):
        self.mutate(audit.STORE,"LinkOption.NOFOLLOW_LINKS","LinkOption.valueOf(\"FOLLOW\")")
        self.refuse()

    def test_probe_requires_read_attributes(self):
        self.mutate(audit.STORE,"Files.readAttributes(staging.toPath()",
                    "Files.newInputStream(staging.toPath()")
        self.refuse()

    def test_probe_requires_basic_file_attributes(self):
        self.mutate(audit.STORE,"BasicFileAttributes.class","File.class")
        self.refuse()

    def test_probe_must_have_regular_file_type(self):
        self.mutate(audit.STORE,"attrs.isRegularFile()","attrs.isDirectory()")
        self.refuse()

    def test_regular_stage_is_orphan_not_clear(self):
        self.mutate(audit.STORE,
                    "attrs.isRegularFile() ? R411StageState.ORPHAN : R411StageState.UNSAFE",
                    "attrs.isRegularFile() ? R411StageState.CLEAR : R411StageState.UNSAFE")
        self.refuse()

    def test_nonregular_stage_is_unsafe(self):
        self.mutate(audit.STORE,
                    "attrs.isRegularFile() ? R411StageState.ORPHAN : R411StageState.UNSAFE",
                    "attrs.isRegularFile() ? R411StageState.ORPHAN : R411StageState.CLEAR")
        self.refuse()

    def test_missing_stage_is_only_clear_case(self):
        self.mutate(audit.STORE,
                    "catch (NoSuchFileException missing) {\n      return R411StageState.CLEAR;",
                    "catch (NoSuchFileException missing) {\n      return R411StageState.ORPHAN;")
        self.refuse()

    def test_io_metadata_failure_is_unsafe(self):
        self.mutate(audit.STORE,
                    "catch (IOException | SecurityException unreadable) {\n      return R411StageState.UNSAFE;",
                    "catch (IOException | SecurityException unreadable) {\n      return R411StageState.CLEAR;")
        self.refuse()

    def test_security_exception_is_not_ignored(self):
        self.mutate(audit.STORE,"catch (IOException | SecurityException unreadable)",
                    "catch (IOException unreadable)")
        self.refuse()

    def test_probe_cannot_open_stage_payload(self):
        self.mutate(audit.STORE,
                    "final BasicFileAttributes attrs = Files.readAttributes(",
                    "Files.readAllBytes(staging.toPath()); final BasicFileAttributes attrs = Files.readAttributes(")
        self.refuse("R411_PROBE_MUST_BE_METADATA_ONLY")

    def test_probe_cannot_delete_stage(self):
        self.mutate(audit.STORE,
                    "final BasicFileAttributes attrs = Files.readAttributes(",
                    "Files.delete(staging.toPath()); final BasicFileAttributes attrs = Files.readAttributes(")
        self.refuse("R411_PROBE_MUST_BE_METADATA_ONLY")

    def test_probe_cannot_replace_stage(self):
        self.mutate(audit.STORE,
                    "final BasicFileAttributes attrs = Files.readAttributes(",
                    "Files.move(staging.toPath(),file.toPath()); final BasicFileAttributes attrs = Files.readAttributes(")
        self.refuse("R411_PROBE_MUST_BE_METADATA_ONLY")

    def test_refusal_helper_must_treat_clear_as_clean(self):
        self.mutate(audit.STORE,"stage == R411StageState.CLEAR",
                    "stage == R411StageState.ORPHAN")
        self.refuse()

    def test_refusal_helper_cannot_delete_staging(self):
        self.mutate(audit.STORE,"    return true;\n  }\n\n  void deleteStale()",
                    "    Files.delete(staging.toPath()); return true;\n  }\n\n  void deleteStale()")
        self.refuse()

    def test_legacy_cleanup_must_have_quarantine_guard(self):
        self.mutate(audit.STORE,
                    "    if (r411RefuseUnresolvedStage(\"legacy cleanup\"))",
                    "    if (false)")
        self.refuse()

    def test_startup_load_must_have_quarantine_guard(self):
        self.mutate(audit.STORE,
                    "    if (r411RefuseUnresolvedStage(\"history restoration\"))",
                    "    if (false)")
        self.refuse()

    def test_history_save_must_have_quarantine_guard(self):
        self.mutate(audit.STORE,
                    "    if (r411RefuseUnresolvedStage(\"history save\"))",
                    "    if (false)")
        self.refuse()

    def test_clear_all_must_have_quarantine_guard(self):
        self.mutate(audit.STORE,
                    "    if (r411RefuseUnresolvedStage(\"clear all\"))",
                    "    if (false)")
        self.refuse()

    def test_save_guard_must_be_first(self):
        self.mutate(audit.STORE,
                    "  boolean saveWithReceipt(Collection<InventedRow> records) {\n    if (r411",
                    "  boolean saveWithReceipt(Collection<InventedRow> records) {\n    forceDisk(); if (r411")
        self.refuse("R411_saveWithReceipt_GATE_NOT_FIRST")

    def test_restore_guard_must_be_first(self):
        self.mutate(audit.STORE,
                    "  List<InventedRow> loadForMerge() {\n    if (r411",
                    "  List<InventedRow> loadForMerge() {\n    readOldDisk(); if (r411")
        self.refuse("R411_loadForMerge_GATE_NOT_FIRST")

    def test_clear_guard_must_be_first(self):
        self.mutate(audit.STORE,
                    "  boolean clearWithReceipt() {\n    if (r411",
                    "  boolean clearWithReceipt() {\n    Files.deleteIfExists(file.toPath()); if (r411")
        self.refuse("R411_clearWithReceipt_GATE_NOT_FIRST")

    def test_cleanup_guard_must_be_first(self):
        self.mutate(audit.STORE,
                    "  void deleteStale() {\n    if (r411",
                    "  void deleteStale() {\n    Files.deleteIfExists(retired.toPath()); if (r411")
        self.refuse("R411_deleteStale_GATE_NOT_FIRST")

    def test_cleanup_refusal_must_return(self):
        self.mutate(audit.STORE,
                    "if (r411RefuseUnresolvedStage(\"legacy cleanup\")) {\n      return;",
                    "if (r411RefuseUnresolvedStage(\"legacy cleanup\")) {\n      noop();")
        self.refuse()

    def test_load_refusal_must_return_null(self):
        self.mutate(audit.STORE,
                    "if (r411RefuseUnresolvedStage(\"history restoration\")) {\n      return null;",
                    "if (r411RefuseUnresolvedStage(\"history restoration\")) {\n      return new ArrayList<>();")
        self.refuse()

    def test_save_refusal_must_return_false(self):
        self.mutate(audit.STORE,
                    "if (r411RefuseUnresolvedStage(\"history save\")) {\n      return false;",
                    "if (r411RefuseUnresolvedStage(\"history save\")) {\n      return true;")
        self.refuse()

    def test_clear_refusal_must_return_false(self):
        self.mutate(audit.STORE,
                    "if (r411RefuseUnresolvedStage(\"clear all\")) {\n      return false;",
                    "if (r411RefuseUnresolvedStage(\"clear all\")) {\n      return true;")
        self.refuse()

    def test_strict_atomic_history_writer_stays(self):
        self.mutate(audit.STORE,
                    "AtomicFileReplace.moveStrict(temp, file)",
                    "AtomicFileReplace.move(temp, file)")
        self.refuse()

    def test_create_new_staging_stays(self):
        self.mutate(audit.STORE,"StandardOpenOption.CREATE_NEW",
                    "StandardOpenOption.CREATE")
        self.refuse()

    def test_flush_before_force_stays(self):
        self.mutate(audit.STORE,
                    "      writer.flush();\n      channel.force(true);",
                    "      channel.force(true);\n      writer.flush();")
        self.refuse()

    def test_unchanged_history_read_public_entrypoint(self):
        self.mutate(audit.STORE,"File getFile() {return file;}",
                    "File getFile() {return null;}")
        self.refuse("R411_UNRELATED_HISTORY_METHOD_CHANGE_getFile")

    def test_unchanged_save_wrapper(self):
        self.mutate(audit.STORE,
                    "void save(Collection<InventedRow> data) {saveWithReceipt(data);}",
                    "void save(Collection<InventedRow> data) {noop();}")
        self.refuse("R411_UNRELATED_HISTORY_METHOD_CHANGE_save")

    def test_extra_java_source_changed_refused(self):
        self.current[audit.MOVE]=b"changed move helper"
        self.write()
        self.refuse("R411_EXACT_ONE_SOURCE_ONE_EXISTING_CLASS_REQUIRED")

    def test_unexpected_extra_class_refused(self):
        self.currentclasses[audit.P+"LootTrackerPlugin.class"]=b"unexpected plugin class"
        self.write()
        self.refuse("R411_EXACT_ONE_SOURCE_ONE_EXISTING_CLASS_REQUIRED")

    def test_no_nested_enum_class_refused(self):
        self.currentclasses.pop(next(iter(audit.ADDED_CLASS)))
        self.write()
        self.refuse("R411_COMPILED_CLASS_COUNT_DRIFT")

    def test_wrong_nested_class_name_refused(self):
        val=self.currentclasses.pop(next(iter(audit.ADDED_CLASS)))
        self.currentclasses[audit.P+"LootHistoryStore$Unexpected.class"]=val
        self.write()
        self.refuse("R411_NEW_NESTED_CLASS_SCOPE_DRIFT")

    def test_sha_pin_prevents_altered_reference(self):
        with self.assertRaisesRegex(audit.Refused,"ARCHIVE_SHA_DRIFT"):
            audit.audit(
                kit=self.kit,kit_sha="0"*64,reference=self.reference,
                reference_sha=sha(self.reference),
                previous_sources=self.oldsrc,previous_classes=self.oldcls,
                candidate_sources=self.newsrc,candidate_classes=self.newcls,
                expected_sources=7,previous_class_count=8,candidate_class_count=9)

    def args(self,out):
        return ["--kit",str(self.kit),"--kit-sha256",sha(self.kit),
                "--reference",str(self.reference),
                "--reference-sha256",sha(self.reference),
                "--previous-sources",str(self.oldsrc),
                "--previous-classes",str(self.oldcls),
                "--candidate-sources",str(self.newsrc),
                "--candidate-classes",str(self.newcls),
                "--expected-sources","7",
                "--previous-class-count","8","--candidate-class-count","9",
                "--out",str(out)]

    def test_cli_refuses_existing_receipt(self):
        target=Path(self.tmp.name)/"existing.json"
        target.write_text("KEEP",encoding="utf8")
        self.assertEqual(audit.main(self.args(target)),2)
        self.assertEqual(target.read_text("utf8"),"KEEP")

    def test_cli_report_remains_release_closed(self):
        out=Path(self.tmp.name)/"result.json"
        self.assertEqual(audit.main(self.args(out)),0)
        self.assertFalse(json.loads(out.read_text("utf8"))["merge_approved"])

if __name__=="__main__":
    unittest.main()
