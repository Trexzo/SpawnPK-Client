"""R412 public-only source guard negatives and metadata-only inspector tests.

Every Java source snippet and class byte is invented. File-system tests use
new per-test temporary directories and synthetic strings, not user data.
"""
from __future__ import annotations
import hashlib
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import os
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
def imported(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
gate=imported("r412_public_gate",ROOT/"tools/r412/audit_delete_preadmission_guard.py")
inspector=imported("r412_public_inspector",ROOT/"tools/r412/inspect_history_stage.py")

FAKE_BASE="""
class InventedPlugin {
  void r402ApplyPanelDeletion(Runnable mutation) {
    if (mutation == null || historyStore == null || panel == null ||
        !SwingUtilities.isEventDispatchThread())return;
    if (!config.rememberLoot()) {
      mutation.run();
      return;
    }
    synchronized (r401FileGate) {
      synchronized (r395HistoryGate) {
        if (!historyLoaded || r401ClearInProgress || r401ClearUnsafe ||
            r400PanelHandoffUnsafe || r398UnreconciledPanelAtStart ||
            r402EditTransactionOpen) {
           return;
        }
        ++r401ClearGeneration;
        r402PanelEditMutating = true;
        r402EditTransactionOpen = true;
        r402EditWriteReceipt = false;
        r396LastCommitSucceeded = false;
      }
      boolean finished=false;
      try {
        mutation.run();
        finished=true;
      }
      finally {
        synchronized (r395HistoryGate) {
          ++r401ClearGeneration;
          r402PanelEditMutating = false;
        }
      }
      try {
        persistHistory();
      }
      finally {
        synchronized (r395HistoryGate) {
          if (!r402EditWriteReceipt) {
            r401ClearUnsafe = true;
          }
          r402EditTransactionOpen = false;
        }
      }
    }
  }
  void r403QueueAutosave() {executor.execute(()->persistHistory());}
}
"""
PREFLIGHT="""
      if (historyStore.r411StageState() != LootHistoryStore.R411StageState.CLEAR) {
        synchronized (r395HistoryGate) {
          r401ClearUnsafe = true;
          r396LastCommitSucceeded = false;
        }
        log.warn("invented stage refusal");
        return;
      }
"""
FAKE_STORE="""
class InventedStore {
 enum R411StageState {CLEAR,ORPHAN,UNSAFE}
 R411StageState r411StageState() {
    final BasicFileAttributes attrs=Files.readAttributes(staging.toPath(),
       BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
    return attrs.isRegularFile()?R411StageState.ORPHAN:R411StageState.UNSAFE;
    catch (NoSuchFileException missing) {
      return R411StageState.CLEAR;
    }
    catch (IOException | SecurityException unreadable) {
      return R411StageState.UNSAFE;
    }
 }
 private boolean r411RefuseUnresolvedStage(String operation) {return true;}
 List<InventedRow> loadForMerge() {
    if (r411RefuseUnresolvedStage("history restoration"))return null;
    return rows;
 }
 boolean saveWithReceipt() {
    if (r411RefuseUnresolvedStage("history save"))return false;
    return true;
 }
 boolean clearWithReceipt() {
    if (r411RefuseUnresolvedStage("clear all"))return false;
    return true;
 }
}
"""

def inject_guard(text):
    anchor="    synchronized (r401FileGate) {\n"
    if text.count(anchor)!=1:raise AssertionError("synthetic anchor")
    return text.replace(anchor,anchor+PREFLIGHT)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

class R412SourceSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name)
        self.kit=base/"fabricated-source.zip"
        self.reference=base/"fabricated-class.jar"
        self.prior_src=base/"prior-source"
        self.next_src=base/"next-source"
        self.prior_classes=base/"prior-classes"
        self.next_classes=base/"next-classes"
        self.old_plugin=FAKE_BASE.encode()
        self.new_plugin=inject_guard(FAKE_BASE).encode()
        self.store=FAKE_STORE.encode()
        self.other={name:b"invented Java "+name.encode() for name in gate.KNOWN_ORIGINAL_DIFF
                    if name not in (gate.PLUGIN,gate.STORE)}
        self.other["rs/plugins/loottracker/TradingPostPrices.java"]=b"invented price cache"
        self.prior={**self.other,gate.PLUGIN:self.old_plugin,gate.STORE:self.store}
        self.current={**self.other,gate.PLUGIN:self.new_plugin,gate.STORE:self.store}
        self.prior_class={name:b"invented prior class "+name.encode()
                          for name in gate.KNOWN_ORIGINAL_CLASS_DIFF}
        self.prior_class[gate.STAGE_ENUM]=b"invented R411 enum bytes"
        self.new_class=self.prior_class.copy()
        self.new_class[next(iter(gate.MODIFIED_CLASS))]=b"invented R412 plugin bytes"
        self.write()

    @staticmethod
    def put_tree(folder,entries):
        folder.mkdir(parents=True,exist_ok=True)
        for f in folder.rglob("*"):
            if f.is_file():f.unlink()
        for name,blob in entries.items():
            f=folder/name
            f.parent.mkdir(parents=True,exist_ok=True)
            f.write_bytes(blob)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            for name in sorted(self.prior):
                data=(self.other[name] if name in self.other and
                     name not in gate.KNOWN_ORIGINAL_DIFF else b"fabricated gold Java")
                z.writestr("source/"+name,data)
        with ZipFile(self.reference,"w") as z:
            for name in sorted(gate.KNOWN_ORIGINAL_CLASS_DIFF):
                z.writestr(name,b"fabricated gold class")
        self.put_tree(self.prior_src,self.prior)
        self.put_tree(self.next_src,self.current)
        self.put_tree(self.prior_classes,self.prior_class)
        self.put_tree(self.next_classes,self.new_class)

    def check(self):
        return gate.audit(
            kit=self.kit,kit_sha=digest(self.kit),
            reference=self.reference,reference_sha=digest(self.reference),
            previous_sources=self.prior_src,previous_classes=self.prior_classes,
            candidate_sources=self.next_src,candidate_classes=self.next_classes,
            expected_sources=7,expected_classes=9)

    def reject(self,why=None):
        if why:
            with self.assertRaisesRegex(gate.Refused,why):self.check()
        else:
            with self.assertRaises(gate.Refused):self.check()

    def patch(self,file,old,new):
        old_bytes=old.encode()
        self.assertIn(old_bytes,self.current[file])
        self.current[file]=self.current[file].replace(old_bytes,new.encode())
        self.write()

    def test_positive_private_scope_static_gate_no_release(self):
        report=self.check()
        self.assertEqual(report["status"],"R412_PRIVATE_DELETE_PREADMISSION_STATIC_GATE_PASS")
        self.assertEqual(report["source_diff_vs_r411"],1)
        self.assertEqual(report["existing_class_diff_vs_r411"],1)
        self.assertTrue(report["nonclear_stage_refuses_before_panel_mutation"])
        for key in ("private_client_executed","private_history_or_stage_read",
                    "complete_delete_rollback_proven","real_edt_latency_improved",
                    "physical_power_loss_safety_proven","private_release_authorized",
                    "merge_approved"):
            self.assertFalse(report[key])

    def test_report_does_not_expose_source_or_history(self):
        report=json.dumps(self.check())
        for phrase in ("InventedPlugin","invented price cache","stage refusal",
                       "fabricated-source.zip","historyStore.r411StageState()"):
            self.assertNotIn(phrase,report)

    def test_missing_preflight_is_refused(self):
        self.current[gate.PLUGIN]=self.old_plugin
        self.write()
        self.reject("R412_EXACT_ONE_PLUGIN_SOURCE_AND_CLASS_REQUIRED")

    def test_guard_must_be_inside_file_gate(self):
        self.patch(gate.PLUGIN,
            "    synchronized (r401FileGate) {\n"+PREFLIGHT,
            PREFLIGHT+"    synchronized (r401FileGate) {\n")
        self.reject()

    def test_guard_must_be_first_inside_file_gate(self):
        self.patch(gate.PLUGIN,
            "    synchronized (r401FileGate) {\n"+PREFLIGHT,
            "    synchronized (r401FileGate) {\n      beforeMutation();\n"+PREFLIGHT)
        self.reject("R412_GUARD_MUST_BE_FIRST_INSIDE_FILEGATE")

    def test_guard_must_require_exact_clear_stage(self):
        self.patch(gate.PLUGIN,
            "!= LootHistoryStore.R411StageState.CLEAR",
            "== LootHistoryStore.R411StageState.CLEAR")
        self.reject()

    def test_guard_must_not_skip_session_error_when_orphan(self):
        self.patch(gate.PLUGIN,
            "r401ClearUnsafe = true;\n          r396LastCommitSucceeded = false;",
            "r401ClearUnsafe = false;\n          r396LastCommitSucceeded = false;")
        self.reject()

    def test_guard_must_reset_write_receipt(self):
        self.patch(gate.PLUGIN,
            "r396LastCommitSucceeded = false;\n        }\n        log.warn",
            "r396LastCommitSucceeded = true;\n        }\n        log.warn")
        self.reject()

    def test_guard_refusal_must_return_before_mutation(self):
        self.patch(gate.PLUGIN,
            'log.warn("invented stage refusal");\n        return;',
            'log.warn("invented stage refusal");\n        noop();')
        self.reject()

    def test_guard_must_not_invoke_mutation(self):
        self.patch(gate.PLUGIN,
            'log.warn("invented stage refusal");',
            'mutation.run(); log.warn("invented stage refusal");')
        self.reject()

    def test_guard_must_not_invoke_persist(self):
        self.patch(gate.PLUGIN,
            'log.warn("invented stage refusal");',
            'persistHistory(); log.warn("invented stage refusal");')
        self.reject()

    def test_guard_must_not_set_transaction_open(self):
        self.patch(gate.PLUGIN,
            'log.warn("invented stage refusal");',
            'r402EditTransactionOpen = true; log.warn("invented stage refusal");')
        self.reject()

    def test_nonpersistent_ui_only_mode_preserved(self):
        self.patch(gate.PLUGIN,
            "if (!config.rememberLoot())",
            "if (false)")
        self.reject()

    def test_edtonly_guard_preserved(self):
        self.patch(gate.PLUGIN,
            "SwingUtilities.isEventDispatchThread()",
            "Thread.currentThread().isAlive()")
        self.reject()

    def test_existing_loaded_guard_preserved(self):
        self.patch(gate.PLUGIN,
            "if (!historyLoaded || r401ClearInProgress",
            "if (r401ClearInProgress")
        self.reject()

    def test_existing_clear_in_progress_guard_preserved(self):
        self.patch(gate.PLUGIN,
            "r401ClearInProgress || r401ClearUnsafe",
            "r401ClearUnsafe")
        self.reject()

    def test_existing_unsafe_history_guard_preserved(self):
        self.patch(gate.PLUGIN,
            "r401ClearInProgress || r401ClearUnsafe",
            "r401ClearInProgress")
        self.reject()

    def test_existing_handoff_guard_preserved(self):
        self.patch(gate.PLUGIN,"r400PanelHandoffUnsafe ||","true ||")
        self.reject()

    def test_edit_generation_increment_retained(self):
        self.patch(gate.PLUGIN,"++r401ClearGeneration","noop()")
        self.reject()

    def test_delete_receipt_retained(self):
        self.patch(gate.PLUGIN,"if (!r402EditWriteReceipt)","if (false)")
        self.reject()

    def test_sync_persist_not_replaced_with_queue(self):
        self.patch(gate.PLUGIN,
            "        persistHistory();",
            "        r403QueueAutosave();")
        self.reject()

    def test_no_new_nested_class(self):
        self.new_class["rs/plugins/loottracker/Invented.class"]=b"extra"
        self.write()
        self.reject("R412_PRIVATE_CLASS_COUNT_DRIFT")

    def test_unrelated_existing_class_mutation_rejected(self):
        self.new_class[gate.P+"LootTrackerPanel.class"]=b"different panel class"
        self.write()
        self.reject("R412_EXACT_ONE_PLUGIN_SOURCE_AND_CLASS_REQUIRED")

    def test_unrelated_source_change_rejected(self):
        self.current[gate.MOVER]=b"modified strict move helper"
        self.write()
        self.reject("R412_EXACT_ONE_PLUGIN_SOURCE_AND_CLASS_REQUIRED")

    def test_stage_store_byte_identity_required(self):
        self.current[gate.STORE]=b"new invented stage store"
        self.write()
        self.reject("R412_EXACT_ONE_PLUGIN_SOURCE_AND_CLASS_REQUIRED")

    def test_pinned_kit_hash_required(self):
        with self.assertRaisesRegex(gate.Refused,"ARCHIVE_SHA_DRIFT"):
            gate.audit(kit=self.kit,kit_sha="0"*64,
                reference=self.reference,reference_sha=digest(self.reference),
                previous_sources=self.prior_src,previous_classes=self.prior_classes,
                candidate_sources=self.next_src,candidate_classes=self.next_classes,
                expected_sources=7,expected_classes=9)

    def test_pinned_reference_hash_required(self):
        with self.assertRaisesRegex(gate.Refused,"ARCHIVE_SHA_DRIFT"):
            gate.audit(kit=self.kit,kit_sha=digest(self.kit),
                reference=self.reference,reference_sha="0"*64,
                previous_sources=self.prior_src,previous_classes=self.prior_classes,
                candidate_sources=self.next_src,candidate_classes=self.next_classes,
                expected_sources=7,expected_classes=9)

    def args(self,output):
        return ["--kit",str(self.kit),"--kit-sha256",digest(self.kit),
                "--reference",str(self.reference),"--reference-sha256",digest(self.reference),
                "--previous-sources",str(self.prior_src),
                "--previous-classes",str(self.prior_classes),
                "--candidate-sources",str(self.next_src),
                "--candidate-classes",str(self.next_classes),
                "--expected-sources","7","--expected-classes","9",
                "--out",str(output)]

    def test_refuse_overwrite_receipt(self):
        path=Path(self.tmp.name)/"receipt.json"
        path.write_text("KEEP")
        self.assertEqual(gate.main(self.args(path)),2)
        self.assertEqual(path.read_text(),"KEEP")

    def test_positive_cli_is_unmerged(self):
        path=Path(self.tmp.name)/"receipt.json"
        self.assertEqual(gate.main(self.args(path)),0)
        self.assertFalse(json.loads(path.read_text())["merge_approved"])

class R412ReadOnlyInspectorTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.dir=Path(t.name)
        self.main=self.dir/"loot-history.json"
        self.stage=self.dir/"loot-history.json.tmp"

    def probe(self,**kwargs):
        return inspector.inspect(self.dir,**kwargs)

    def test_empty_directory_never_claims_authority(self):
        r=self.probe()
        self.assertEqual(r["stage_state"],"CLEAR")
        self.assertEqual(r["conclusion"],"NO_STAGE_OBSERVED_NO_RECOVERY_PROOF")
        self.assertFalse(r["main_file_authoritative_proven"])
        self.assertFalse(r["automatic_recovery_permitted"])
        self.assertEqual(r["mode"],"METADATA_ONLY")

    def test_regular_main_without_stage_no_recovery_proof(self):
        self.main.write_bytes(b"fabricated")
        r=self.probe()
        self.assertEqual(r["entries"][0]["size_bytes"],10)
        self.assertEqual(r["entries"][0]["status"],"REGULAR")
        self.assertEqual(r["stage_state"],"CLEAR")
        self.assertFalse(r["main_file_authoritative_proven"])

    def test_orphan_stage_requires_explicit_reconciliation(self):
        self.main.write_bytes(b"before")
        self.stage.write_bytes(b"unknown-stage")
        r=self.probe()
        self.assertEqual(r["stage_state"],"ORPHAN")
        self.assertEqual(r["conclusion"],"QUARANTINED_REQUIRES_EXPLICIT_RECONCILIATION")
        self.assertEqual(r["entries"][1]["size_bytes"],13)
        self.assertFalse(r["automatic_recovery_permitted"])

    def test_stage_without_main_is_still_orphan(self):
        self.stage.write_bytes(b"unstable")
        r=self.probe()
        self.assertEqual(r["entries"][0]["status"],"ABSENT")
        self.assertEqual(r["stage_state"],"ORPHAN")

    def test_directory_named_stage_is_unsafe(self):
        self.stage.mkdir()
        r=self.probe()
        self.assertEqual(r["entries"][1]["status"],"DIRECTORY")
        self.assertEqual(r["stage_state"],"UNSAFE")

    def test_empty_regular_stage_is_orphan(self):
        self.stage.write_bytes(b"")
        self.assertEqual(self.probe()["stage_state"],"ORPHAN")

    def test_symlink_stage_not_followed_where_supported(self):
        self.main.write_bytes(b"real")
        try:self.stage.symlink_to(self.main.name)
        except (OSError,NotImplementedError):self.skipTest("test symlink unsupported")
        r=self.probe()
        self.assertEqual(r["entries"][1]["status"],"SYMLINK")
        self.assertEqual(r["stage_state"],"UNSAFE")

    def test_root_symlink_not_accepted_where_supported(self):
        alias=self.dir.parent/(self.dir.name+"-synthetic-alias")
        try:alias.symlink_to(self.dir,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest("directory symlink unsupported")
        self.addCleanup(lambda:alias.unlink(missing_ok=True))
        with self.assertRaisesRegex(ValueError,"R412_DIRECTORY_NOT_REAL_DIRECTORY"):
            inspector.inspect(alias)

    def test_cap_below_one_refused(self):
        with self.assertRaisesRegex(ValueError,"R412_INVALID_SIZE_CAP"):
            self.probe(max_bytes=0)

    def test_cap_over_64mib_refused(self):
        with self.assertRaisesRegex(ValueError,"R412_INVALID_SIZE_CAP"):
            self.probe(max_bytes=inspector.MAX_BYTES+1)

    def test_oversized_main_file_is_not_hashable(self):
        self.main.write_bytes(b"abcdefgh")
        r=self.probe(hash_requested=True,max_bytes=4)
        self.assertEqual(r["entries"][0]["status"],"OVERSIZED")
        self.assertNotIn("sha256",r["entries"][0])
        self.assertEqual(r["conclusion"],"UNSAFE_MAIN_FILE")

    def test_oversized_stage_is_still_unresolved(self):
        self.stage.write_bytes(b"12345")
        r=self.probe(hash_requested=True,max_bytes=4)
        self.assertEqual(r["entries"][1]["status"],"OVERSIZED")
        self.assertEqual(r["stage_state"],"ORPHAN")
        self.assertNotIn("sha256",r["entries"][1])

    def test_hash_opt_in_only(self):
        self.main.write_bytes(b"abc")
        r=self.probe()
        self.assertNotIn("sha256",r["entries"][0])
        self.assertNotIn("hash_status",r["entries"][0])

    def test_hash_opt_in_correct_or_unavailable(self):
        self.main.write_bytes(b"abc")
        r=self.probe(hash_requested=True)
        entry=r["entries"][0]
        if hasattr(os,"O_NOFOLLOW"):
            self.assertEqual(entry["hash_status"],"SHA256_OK")
            self.assertEqual(entry["sha256"],hashlib.sha256(b"abc").hexdigest())
        else:
            self.assertEqual(entry["hash_status"],"UNAVAILABLE_NO_NOFOLLOW")
            self.assertNotIn("sha256",entry)

    def test_hash_does_not_change_bytes_or_mtime(self):
        self.main.write_bytes(b"sample")
        self.stage.write_bytes(b"failed")
        before=[(x.read_bytes(),x.stat().st_mtime_ns) for x in (self.main,self.stage)]
        self.probe(hash_requested=True)
        after=[(x.read_bytes(),x.stat().st_mtime_ns) for x in (self.main,self.stage)]
        self.assertEqual(before,after)

    def test_hash_does_not_open_symlink(self):
        self.main.write_bytes(b"private-looking-contents")
        try:self.stage.symlink_to(self.main.name)
        except (OSError,NotImplementedError):self.skipTest("symlink unsupported")
        r=self.probe(hash_requested=True)
        self.assertNotIn("sha256",r["entries"][1])
        self.assertEqual(r["entries"][1]["status"],"SYMLINK")

    def test_output_never_contains_directory_or_payload(self):
        self.main.write_bytes(b"SECRET_RECORDS_SYNTHETIC")
        self.stage.write_bytes(b"PRIVATE_STAGE_SYNTHETIC")
        report=json.dumps(self.probe(hash_requested=True))
        self.assertNotIn(str(self.dir),report)
        self.assertNotIn("SECRET_RECORDS_SYNTHETIC",report)
        self.assertNotIn("PRIVATE_STAGE_SYNTHETIC",report)
        self.assertFalse(json.loads(report)["file_contents_displayed"])

    def test_unknown_root_refused(self):
        with self.assertRaisesRegex(ValueError,"R412_DIRECTORY_NOT_ACCESSIBLE"):
            inspector.inspect(self.dir/"nonexistent")

    def test_regular_file_not_accepted_as_directory(self):
        self.main.write_bytes(b"not-root")
        with self.assertRaisesRegex(ValueError,"R412_DIRECTORY_NOT_REAL_DIRECTORY"):
            inspector.inspect(self.main)

    def test_cli_default_metadata_only(self):
        self.stage.write_bytes(b"orphan")
        buf=io.StringIO()
        with redirect_stdout(buf):
            result=inspector.main(["--directory",str(self.dir)])
        self.assertEqual(result,0)
        r=json.loads(buf.getvalue())
        self.assertEqual(r["stage_state"],"ORPHAN")
        self.assertEqual(r["mode"],"METADATA_ONLY")
        self.assertFalse(r["files_modified"])

    def test_cli_unknown_directory_fails_closed(self):
        buf=io.StringIO()
        with redirect_stdout(buf):
            rc=inspector.main(["--directory",str(self.dir/"missing")])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(buf.getvalue())["status"],"R412_INSPECTION_REFUSED")

    def test_unreadable_stage_metadata_quarantined(self):
        orig=inspector.os.lstat
        def fail_stage(path):
            if Path(path)==self.stage:raise PermissionError("synthetic")
            return orig(path)
        inspector.os.lstat=fail_stage
        try:
            r=self.probe()
            self.assertEqual(r["stage_state"],"UNSAFE")
            self.assertEqual(r["entries"][1]["status"],"UNREADABLE")
        finally:
            inspector.os.lstat=orig

    def test_untrusted_unsafe_stage_does_not_claim_safe(self):
        self.stage.mkdir()
        r=self.probe()
        for key in ("main_file_authoritative_proven","stage_file_authoritative_proven",
                    "cross_process_stability_proven","automatic_recovery_permitted"):
            self.assertFalse(r[key])

if __name__=="__main__":
    unittest.main()
