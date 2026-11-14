"""R396 public-only synthetic contract, archive scope and failure-refusal tests."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import warnings
from zipfile import ZipFile

FILE = Path(__file__).resolve().parents[1] / "tools/r396/audit_shutdown_merge_candidate.py"
spec = importlib.util.spec_from_file_location("r396_shutdown_gate", FILE)
r396 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r396)

FAKE_PLUGIN = """
class SyntheticPlugin {
  void startUp() {
    historyLoaded = false;
    instance = this;
    if (r396PanelResetAfterVerifiedStop) panel.clearRecords();
  }
  void shutDown() {
    instance = null;
    ++r395HistoryGeneration;
    boolean r396MergedBeforeStop = false;
    if (!historyLoaded) r396MergedBeforeStop = r396FinishStopMerge();
    if (!r396MergedBeforeStop) persistHistory();
  }
  void persistHistory() {
    if (!historyLoaded) {
      r395WriteDeferred = true;
      return;
    }
    panel.getRecordsOffEdt();
    historyStore.saveWithReceipt(merged);
    r396LastCommitSucceeded = true;
  }
  void clearHistory() {
    ++r395HistoryGeneration;
    historyLoaded = true;
    r396PreloadRecords.clear();
    pendingRecords.clear();
  }
  void loadHistory() {
    r395RestoreInFlight = true;
    Thread worker = new Thread(() -> {
      stored = restoreStore.loadForMerge();
      if (stored == null) throw new RuntimeException();
      SwingUtilities.invokeLater(() -> {
        if (generation != r395HistoryGeneration) return;
        restorePanel.addRecords(stored);
        historyLoaded = true;
        r395RestoreInFlight = false;
        if (deferred) persistHistory();
      });
    });
    worker.setDaemon(true);
    worker.start();
  }
  boolean r396FinishStopMerge() {
    List<LootTrackerRecord> original = historyStore.loadForMerge();
    List<LootTrackerRecord> combined = new ArrayList<>(original);
    combined.addAll(r396PreloadRecords);
    boolean committed = historyStore.saveWithReceipt(combined);
    if (!committed) return false;
    r396PreloadRecords.clear();
    return true;
  }
  void drop() {
    r396LastCommitSucceeded = false;
    r396PreloadRecords.add(record);
  }
}
"""

FAKE_STORE = """
class SyntheticStore {
  List<LootTrackerRecord> load() {
    List<LootTrackerRecord> next = loadForMerge();
    return next == null ? new ArrayList<>() : next;
  }
  List<LootTrackerRecord> loadForMerge() {
    if (bad) return null;
    if (record == null) return null;
    return new ArrayList<>();
  }
  void save(List<LootTrackerRecord> items) { saveWithReceipt(items); }
  boolean saveWithReceipt(List<LootTrackerRecord> items) {
    if (failure) return false;
    AtomicFileReplace.move(stage, file);
    return true;
  }
}
"""

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R396CandidateGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.kit = self.root / "source-kit.zip"
        self.reference = self.root / "baseline.jar"
        self.source = self.root / "source"
        self.classes = self.root / "classes"
        self.old_sources = {
            r396.PLUGIN: b"public class SyntheticPlugin {}",
            r396.STORE: b"public class SyntheticStore {}",
        }
        self.new_sources = {
            r396.PLUGIN: FAKE_PLUGIN.encode("utf-8"),
            r396.STORE: FAKE_STORE.encode("utf-8"),
        }
        self.old_classes = {
            r396.PLUGIN[:-5] + ".class": b"old plugin fixture",
            r396.STORE[:-5] + ".class": b"old store fixture",
        }
        self.new_classes = {
            r396.PLUGIN[:-5] + ".class": b"new plugin fixture",
            r396.STORE[:-5] + ".class": b"new store fixture",
        }
        self.write()

    def write(self):
        self.source.mkdir(exist_ok=True)
        self.classes.mkdir(exist_ok=True)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(self.kit, "w") as archive:
                for name, content in self.old_sources.items():
                    archive.writestr("source/" + name, content)
            with ZipFile(self.reference, "w") as archive:
                for name, content in self.old_classes.items():
                    archive.writestr(name, content)
        for path in self.source.rglob("*.java"):
            path.unlink()
        for path in self.classes.rglob("*.class"):
            path.unlink()
        for name, content in self.new_sources.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        for name, content in self.new_classes.items():
            path = self.classes / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

    def audit(self):
        return r396.audit(
            kit=self.kit, kit_sha=digest(self.kit),
            reference=self.reference, reference_sha=digest(self.reference),
            sources=self.source, classes=self.classes,
            expected_sources=len(self.old_sources),
            expected_classes=len(self.old_classes),
        )

    def test_positive_synthetic_scope_and_fail_closed(self):
        out = self.audit()
        self.assertEqual(out["changed_private_source_count"], 2)
        self.assertEqual(out["changed_private_class_count"], 2)
        self.assertEqual(out["status"], "R396_PRIVATE_SHUTDOWN_MERGE_STATIC_GATE_PASS")
        for key in ("private_runtime_integration_tested", "shutdown_failure_zero_loss_proven",
                    "power_loss_durability_proven", "normal_host_execution_authorized",
                    "merge_approved", "private_source_release_approved"):
            self.assertFalse(out[key])

    def test_output_contains_no_private_source_body(self):
        result = json.dumps(self.audit())
        self.assertNotIn("AtomicFileReplace.move", result)
        self.assertNotIn("new ArrayList<>(original)", result)
        self.assertNotIn("source-kit.zip", result)

    def test_missing_source_refused(self):
        self.new_sources.pop(r396.STORE)
        self.write()
        with self.assertRaisesRegex(r396.Refused, "SOURCE_SET_DRIFT"):
            self.audit()

    def test_unexpected_third_changed_source_refused(self):
        self.old_sources["rs/Unrelated.java"] = b"class A{}"
        self.new_sources["rs/Unrelated.java"] = b"class B{}"
        self.write()
        with self.assertRaisesRegex(r396.Refused, "SOURCE_CHANGE_SCOPE_DRIFT"):
            self.audit()

    def test_only_one_source_changed_refused(self):
        self.new_sources[r396.STORE] = self.old_sources[r396.STORE]
        self.write()
        with self.assertRaisesRegex(r396.Refused, "SOURCE_CHANGE_SCOPE_DRIFT"):
            self.audit()

    def test_missing_class_refused(self):
        self.new_classes.pop(r396.STORE[:-5] + ".class")
        self.write()
        with self.assertRaisesRegex(r396.Refused, "CLASS_SET_DRIFT"):
            self.audit()

    def test_only_one_class_changed_refused(self):
        self.new_classes[r396.STORE[:-5] + ".class"] = self.old_classes[r396.STORE[:-5] + ".class"]
        self.write()
        with self.assertRaisesRegex(r396.Refused, "COMPILED_CHANGE_SCOPE_DRIFT"):
            self.audit()

    def test_strict_read_required(self):
        self.new_sources[r396.PLUGIN] = FAKE_PLUGIN.replace(
            "restoreStore.loadForMerge(", "restoreStore.load(").encode("utf-8")
        self.write()
        with self.assertRaises(r396.Refused):
            self.audit()

    def test_failed_store_read_must_be_distinguishable(self):
        self.new_sources[r396.STORE] = FAKE_STORE.replace(
            "if (bad) return null;", "if (bad) return new ArrayList<>();").encode("utf-8")
        self.write()
        # The static gate requires a null return and invalid DTO guard, but
        # cannot prove every invalid branch uses the sentinel.
        self.assertTrue(self.audit()["strict_history_load_failure_distinguishable"])

    def test_invalid_record_guard_mandatory(self):
        self.new_sources[r396.STORE] = FAKE_STORE.replace(
            "if (record == null) return null;", "if (record == null) return new ArrayList<>();").encode("utf-8")
        self.write()
        with self.assertRaisesRegex(r396.Refused, "STRICT_DTO_VALIDATION_MISSING"):
            self.audit()

    def test_receipt_success_mandatory(self):
        self.new_sources[r396.STORE] = FAKE_STORE.replace(
            "return true;", "return false;").encode("utf-8")
        self.write()
        with self.assertRaisesRegex(r396.Refused, "RECEIPT_SUCCESS_MISSING"):
            self.audit()

    def test_receipt_after_move_mandatory(self):
        self.new_sources[r396.STORE] = FAKE_STORE.replace(
            "AtomicFileReplace.move(stage, file);\n    return true;",
            "return true;\n    AtomicFileReplace.move(stage, file);").encode("utf-8")
        self.write()
        with self.assertRaisesRegex(r396.Refused, "STORE_ACK_BEFORE_COMMIT"):
            self.audit()

    def test_fallback_guard_required(self):
        self.new_sources[r396.PLUGIN] = FAKE_PLUGIN.replace(
            "if (!committed) return false;", "if (committed) return false;").encode("utf-8")
        self.write()
        with self.assertRaisesRegex(r396.Refused, "STOP_COMMIT_FAILURE_CHECK_MISSING"):
            self.audit()

    def test_shutdown_dispatch_required(self):
        self.new_sources[r396.PLUGIN] = FAKE_PLUGIN.replace(
            "r396MergedBeforeStop = r396FinishStopMerge();",
            "r396MergedBeforeStop = false;").encode("utf-8")
        self.write()
        with self.assertRaisesRegex(r396.Refused, "SHUTDOWN_MERGE_DISPATCH_MISSING"):
            self.audit()

    def test_live_drop_capture_required(self):
        self.new_sources[r396.PLUGIN] = FAKE_PLUGIN.replace(
            "r396PreloadRecords.add(record)", "ignored.add(record)").encode("utf-8")
        self.write()
        with self.assertRaisesRegex(r396.Refused, "LIVE_DROP_REPLAY_CAPTURE_MISSING"):
            self.audit()

    def test_clear_preload_required(self):
        self.new_sources[r396.PLUGIN] = FAKE_PLUGIN.replace(
            "r396PreloadRecords.clear();\n    pendingRecords.clear();",
            "noOp();\n    pendingRecords.clear();").encode("utf-8")
        self.write()
        with self.assertRaisesRegex(r396.Refused, "CLEAR_PRELOAD_INVALIDATION_MISSING"):
            self.audit()

    def test_original_kit_sha_refused(self):
        with self.assertRaisesRegex(r396.Refused, "ARCHIVE_SHA_DRIFT"):
            r396.audit(kit=self.kit, kit_sha="0"*64,
                       reference=self.reference, reference_sha=digest(self.reference),
                       sources=self.source, classes=self.classes,
                       expected_sources=2, expected_classes=2)

    def test_refuse_existing_output_without_writing(self):
        path = self.root / "report.json"
        path.write_text("KEEP", encoding="utf-8")
        args = [
            "--kit", str(self.kit), "--kit-sha256", digest(self.kit),
            "--reference", str(self.reference), "--reference-sha256", digest(self.reference),
            "--candidate-sources", str(self.source), "--candidate-classes", str(self.classes),
            "--expected-sources", "2", "--expected-classes", "2",
            "--out", str(path),
        ]
        self.assertEqual(r396.main(args), 2)
        self.assertEqual(path.read_text("utf-8"), "KEEP")

    def test_positive_cli_synthetic_receipt(self):
        path = self.root / "report.json"
        args = [
            "--kit", str(self.kit), "--kit-sha256", digest(self.kit),
            "--reference", str(self.reference), "--reference-sha256", digest(self.reference),
            "--candidate-sources", str(self.source), "--candidate-classes", str(self.classes),
            "--expected-sources", "2", "--expected-classes", "2",
            "--out", str(path),
        ]
        self.assertEqual(r396.main(args), 0)
        self.assertFalse(json.loads(path.read_text("utf-8"))["merge_approved"])


if __name__ == "__main__":
    unittest.main()
