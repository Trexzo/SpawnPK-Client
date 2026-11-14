"""R400 public synthetic source/class-scope and fail-closed source-contract tests."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("r400_audit",ROOT/"tools/r400/audit_optimistic_handoff.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

# Invented Java fixtures; no recovered/private source, no real game client.
FAKE_PLUGIN="""
class SyntheticLoot {
  private long r400PanelHandoffVersion;
  private boolean r400PanelHandoffUnsafe;
  void startUp() { ++r399SessionEpoch; r399AcceptingDrops = true; }
  void shutDown() { r399AcceptingDrops = false; ++r399SessionEpoch; }
  boolean r396FinishStopMerge() {
    if (r398UnreconciledPanelAtStart || r400PanelHandoffUnsafe) return false;
    return true;
  }
  void clearHistory() {
    r400PanelHandoffUnsafe = false;
    r400PanelHandoffVersion += 2L;
  }
  void persistHistory() {
    List<LootTrackerRecord> r400ConsistentMerged = null;
    List<LootTrackerRecord> r400ConsistentPending = null;
    long r400ConsistentMutation = -1L;
    for (int r400Attempt = 0; r400Attempt < 5; ++r400Attempt) {
      final long r400Before;
      synchronized (r395HistoryGate) {
        if (r400PanelHandoffUnsafe) return;
        r400Before = r400PanelHandoffVersion;
      }
      if ((r400Before & 1L) != 0L) continue;
      Collection<LootTrackerRecord> stored = panel.getRecordsOffEdt();
      if (stored == null) return;
      synchronized (r395HistoryGate) {
        if (r400PanelHandoffUnsafe ||
            r400Before != r400PanelHandoffVersion ||
            (r400PanelHandoffVersion & 1L) != 0L) continue;
        r400ConsistentPending = new ArrayList<>(pendingRecords);
        r400ConsistentMutation = r399RecordMutationSequence;
      }
      r400ConsistentMerged = new ArrayList<>(stored);
      r400ConsistentMerged.addAll(r400ConsistentPending);
      break;
    }
    if (r400ConsistentMerged == null) {
      savePending = true;
      return;
    }
    List<LootTrackerRecord> merged = r400ConsistentMerged;
    List<LootTrackerRecord> r399PendingSnapshot = r400ConsistentPending;
    long r399MutationAtSnapshot = r400ConsistentMutation;
    if (historyStore.saveWithReceipt(merged)) {
      for (LootTrackerRecord saved : r399PendingSnapshot) {
        if (it.next() == saved) it.remove();
      }
      boolean unchanged =
          r399RecordMutationSequence == r399MutationAtSnapshot;
    }
  }
  void addLoot() {
    final long r399DropSessionEpoch;
    synchronized (r395HistoryGate) {
      r399DropSessionEpoch = r399SessionEpoch;
      pendingRecords.add(record);
    }
    SwingUtilities.invokeLater(() -> {
      synchronized (r395HistoryGate) {
        if (!r399AcceptingDrops ||
            r399DropSessionEpoch != r399SessionEpoch ||
            instance != this) return;
        ++r400PanelHandoffVersion;
      }
      boolean r400Finished = false;
      try {
        panel.add(name, subtitle, type, entries);
        synchronized (r395HistoryGate) {
          for (Iterator it = pendingRecords.iterator(); it.hasNext();) {
            if (it.next() == record) it.remove();
          }
        }
        r400Finished = true;
      } finally {
        synchronized (r395HistoryGate) {
          if (!r400Finished) {r400PanelHandoffUnsafe = true;}
          ++r400PanelHandoffVersion;
        }
      }
      requestSave();
    });
  }
}
"""

def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()

class R400AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.kit=self.root/"original.zip"
        self.ref=self.root/"reference.jar"
        self.previous_sources=self.root/"prior-sources"
        self.candidate_sources=self.root/"candidate-sources"
        self.previous_classes=self.root/"prior-classes"
        self.candidate_classes=self.root/"candidate-classes"
        self.src=FAKE_PLUGIN.encode("utf8")
        self.previous_src=b"class PriorSyntheticLoot {}"
        self.store=b"class SyntheticStoreChanged {}"
        self.golden_plugin=b"class SyntheticOriginalLoot {}"
        self.golden_store=b"class SyntheticOriginalStore {}"
        self.old_class=b"prior-synthetic-plugin-class"
        self.new_class=b"candidate-synthetic-plugin-class"
        self.write()

    @staticmethod
    def tree(dir,contents):
        dir.mkdir(parents=True,exist_ok=True)
        for p in dir.rglob("*"):
            if p.is_file():p.unlink()
        for name,data in contents.items():
            p=dir/name
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(data)

    def write(self):
        with ZipFile(self.kit,"w") as z:
            z.writestr("source/"+audit.PLUGIN,self.golden_plugin)
            z.writestr("source/"+audit.STORE,self.golden_store)
        with ZipFile(self.ref,"w") as z:
            z.writestr(audit.PLUGIN_CLASS,b"original synthetic class")
            z.writestr(audit.STORE_CLASS,b"original synthetic store class")
        self.tree(self.previous_sources,{audit.PLUGIN:self.previous_src,audit.STORE:self.store})
        self.tree(self.candidate_sources,{audit.PLUGIN:self.src,audit.STORE:self.store})
        self.tree(self.previous_classes,
                  {audit.PLUGIN_CLASS:self.old_class,audit.STORE_CLASS:b"same compiled store"})
        self.tree(self.candidate_classes,
                  {audit.PLUGIN_CLASS:self.new_class,audit.STORE_CLASS:b"same compiled store"})

    def result(self):
        return audit.audit(
            kit=self.kit,kit_sha=sha(self.kit),reference=self.ref,reference_sha=sha(self.ref),
            previous_sources=self.previous_sources,previous_classes=self.previous_classes,
            candidate_sources=self.candidate_sources,candidate_classes=self.candidate_classes,
            expected_sources=2,expected_classes=2)

    def mutate(self,old,new):
        self.assertIn(old.encode("utf8"),self.src)
        self.src=self.src.replace(old.encode("utf8"),new.encode("utf8"))
        self.write()

    def rejects(self,reason):
        with self.assertRaisesRegex(audit.Refused,reason):self.result()

    def test_valid_synthetic_and_closed_release_flags(self):
        r=self.result()
        self.assertEqual(r["status"],"R400_PRIVATE_OPTIMISTIC_HANDOFF_STATIC_GATE_PASS")
        self.assertEqual(r["changed_source_count_vs_r399"],1)
        for name in ("actual_runtime_interleaving_covered","normal_host_launch_authorized",
                     "private_release_authorized","merge_approved",
                     "power_loss_durability_proven"):
            self.assertFalse(r[name])

    def test_receipt_not_source_extraction(self):
        s=json.dumps(self.result())
        self.assertNotIn("SyntheticLoot",s)
        self.assertNotIn("panel.getRecordsOffEdt()",s)
        self.assertNotIn("original.zip",s)

    def test_version_field_declaration_required(self):
        self.mutate("private long r400PanelHandoffVersion;",
                    "private long differentName;")
        self.rejects("HANDOFF_VERSION_FIELD_MISSING")

    def test_unsafe_field_required(self):
        self.mutate("private boolean r400PanelHandoffUnsafe;",
                    "private boolean differentName;")
        self.rejects("HANDOFF_UNSAFE_FIELD_MISSING")

    def test_shutdown_refusal_required(self):
        self.mutate("r398UnreconciledPanelAtStart || r400PanelHandoffUnsafe",
                    "r398UnreconciledPanelAtStart")
        self.rejects("SHUTDOWN_UNSAFE_PERSIST_REFUSAL_MISSING")

    def test_clear_resets_uncertain_state(self):
        self.mutate("r400PanelHandoffUnsafe = false;",
                    "r400PanelHandoffUnsafe = true;")
        self.rejects("EXPLICIT_CLEAR_RESET_MISSING")

    def test_clear_invalidates_version(self):
        self.mutate("r400PanelHandoffVersion += 2L;",
                    "r400PanelHandoffVersion += 0L;")
        self.rejects("EXPLICIT_CLEAR_VERSION_INVALIDATION_MISSING")

    def test_limit_retries_to_five(self):
        self.mutate("r400Attempt < 5","r400Attempt < 9999")
        self.rejects("R400_CRITICAL_SOURCE_ORDER_DRIFT")

    def test_odd_handoff_must_be_rejected(self):
        self.mutate("(r400Before & 1L) != 0L",
                    "(r400Before & 0L) != 0L")
        self.rejects("HANDOFF_ODD_VERSION_NOT_CHECKED")

    def test_handoff_version_rechecked(self):
        self.mutate("r400Before != r400PanelHandoffVersion",
                    "r400Before == r400PanelHandoffVersion")
        self.rejects("HANDOFF_VERSION_NOT_REVALIDATED")

    def test_snapshot_collects_pending(self):
        self.mutate("r400ConsistentPending = new ArrayList<>(pendingRecords)",
                    "r400ConsistentPending = new ArrayList<>()")
        self.rejects("PENDING_SNAPSHOT_NOT_CAPTURED")

    def test_snapshot_merges_pending(self):
        self.mutate("r400ConsistentMerged.addAll(r400ConsistentPending)",
                    "r400ConsistentMerged.clear()")
        self.rejects("CONSISTENT_MERGE_MISSING")

    def test_failed_retries_defer_save(self):
        self.mutate("savePending = true;","savePending = false;")
        self.rejects("RETRY_EXHAUSTION_NOT_DEFERRED")

    def test_save_must_have_receipt(self):
        self.mutate("historyStore.saveWithReceipt(merged)",
                    "historyStore.save(merged)")
        self.rejects("VERIFIED_SAVE_MISSING")

    def test_bad_callback_does_not_masquerade_complete(self):
        self.mutate("r400PanelHandoffUnsafe = true;",
                    "r400PanelHandoffUnsafe = false;")
        self.rejects("FAILED_HANDOFF_NOT_QUARANTINED")

    def test_handoff_requires_two_version_increments(self):
        self.mutate("          ++r400PanelHandoffVersion;\n        }\n      }\n      requestSave();",
                    "          r400PanelHandoffVersion;\n        }\n      }\n      requestSave();")
        self.rejects("R400_CRITICAL_SOURCE_ORDER_DRIFT")

    def test_save_request_must_follow_finalization(self):
        self.mutate("      requestSave();",
                    "      requestSave();\n      requestSave();")
        self.rejects("REQUEST_SAVE_BEFORE_HANDOFF_FINALIZATION")

    def test_changed_source_set_restricted(self):
        self.src=self.previous_src
        self.write()
        self.rejects("R400_ONE_FILE_CLASS_SCOPE_DRIFT")

    def test_changed_class_set_restricted(self):
        self.new_class=self.old_class
        self.write()
        self.rejects("R400_ONE_FILE_CLASS_SCOPE_DRIFT")

    def test_unexpected_store_change_restricted(self):
        path=self.candidate_sources/audit.STORE
        path.write_bytes(b"class InvalidAdditionalStoreRevision {}")
        self.rejects("R400_ONE_FILE_CLASS_SCOPE_DRIFT")

    def test_reference_hash_pinning(self):
        with self.assertRaisesRegex(audit.Refused,"ARCHIVE_SHA_DRIFT"):
            audit.audit(
                kit=self.kit,kit_sha="0"*64,reference=self.ref,reference_sha=sha(self.ref),
                previous_sources=self.previous_sources,previous_classes=self.previous_classes,
                candidate_sources=self.candidate_sources,candidate_classes=self.candidate_classes,
                expected_sources=2,expected_classes=2)

    def cli(self,out):
        return ["--kit",str(self.kit),"--kit-sha256",sha(self.kit),
                "--reference",str(self.ref),"--reference-sha256",sha(self.ref),
                "--previous-sources",str(self.previous_sources),
                "--previous-classes",str(self.previous_classes),
                "--candidate-sources",str(self.candidate_sources),
                "--candidate-classes",str(self.candidate_classes),
                "--expected-sources","2","--expected-classes","2",
                "--out",str(out)]

    def test_cli_refuses_existing_report(self):
        output=self.root/"report.json"
        output.write_text("KEEP",encoding="utf8")
        self.assertEqual(audit.main(self.cli(output)),2)
        self.assertEqual(output.read_text("utf8"),"KEEP")

    def test_cli_writes_one_new_no_release_receipt(self):
        output=self.root/"report.json"
        self.assertEqual(audit.main(self.cli(output)),0)
        data=json.loads(output.read_text("utf8"))
        self.assertFalse(data["normal_host_launch_authorized"])


if __name__=="__main__":
    unittest.main()
