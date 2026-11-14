"""R395 public-only candidate scope and read-only gate synthetic regressions.

No original/recovered game content and no network or launcher execution.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import warnings
from zipfile import ZipFile

SCRIPT = Path(__file__).resolve().parents[1] / "tools/r395/audit_private_candidate_delta.py"
spec = importlib.util.spec_from_file_location("r395_private_gate", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

FAKE_JAVA = """
public final class Demo {
  boolean historyLoaded, deferred;
  int r395HistoryGeneration;
  Object r395WriteDeferred, r395RestoreInFlight, generation, instance, panel;
  void startUp(){
    historyLoaded = false;
    instance = this;
  }
  void shutDown(){
    instance = null;
    ++r395HistoryGeneration;
    persistHistory();
  }
  void persistHistory(){
    if (!historyLoaded){
      r395WriteDeferred = true;
      return;
    }
    panel.getRecordsOffEdt();
  }
  void clearHistory(){
    ++r395HistoryGeneration;
    historyLoaded = true;
    pendingRecords.clear();
  }
  void loadHistory(){
    r395RestoreInFlight = true;
    Thread worker = new Thread(() -> {
      Object rows = restoreStore.load();
      SwingUtilities.invokeLater(() -> {
        if (generation != r395HistoryGeneration) return;
        restorePanel.addRecords(rows);
        historyLoaded = true;
        r395RestoreInFlight = false;
        if (deferred) {
          persistHistory();
        }
      });
    });
    worker.setDaemon(true);
    worker.start();
  }
}
"""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CandidateGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.kit = self.root / "kit.zip"
        self.reference = self.root / "baseline.jar"
        self.sources = self.root / "source"
        self.classes = self.root / "classes"
        self.inputs = {
            audit.SOURCE_REL: (FAKE_JAVA + "\n// synthetic candidate marker\n").encode("utf8"),
        }
        self.originals = {
            audit.SOURCE_REL: FAKE_JAVA.encode("utf8"),
        }
        self.class_baseline = {audit.CLASS_REL: b"synthetic-class-old"}
        self.class_candidate = {audit.CLASS_REL: b"synthetic-class-new"}
        self.write_all()

    def write_all(self):
        self.sources.mkdir(parents=True, exist_ok=True)
        self.classes.mkdir(parents=True, exist_ok=True)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(self.kit, "w") as z:
                for path, data in self.originals.items():
                    z.writestr("source/" + path, data)
            with ZipFile(self.reference, "w") as z:
                for path, data in self.class_baseline.items():
                    z.writestr(path, data)
        for target in self.sources.rglob("*.java"):
            target.unlink()
        for target in self.classes.rglob("*.class"):
            target.unlink()
        for path, data in self.inputs.items():
            target = self.sources / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        for path, data in self.class_candidate.items():
            target = self.classes / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    def audit(self):
        return audit.audit(
            kit=self.kit, reference=self.reference,
            sources=self.sources, classes=self.classes,
            kit_sha=digest(self.kit), reference_sha=digest(self.reference),
            expected_sources=len(self.originals), expected_classes=len(self.class_baseline),
        )

    def test_expected_candidate_scope_and_fail_closed(self):
        report = self.audit()
        self.assertEqual(report["java_source_count"], 1)
        self.assertEqual(report["class_file_count"], 1)
        self.assertEqual(report["modified_source_count"], 1)
        self.assertEqual(report["modified_compiled_class_count"], 1)
        self.assertTrue(report["save_deferral_source_structure_verified"])
        for key in ("launch_authorized", "merge_approved",
                    "private_source_release_approved", "real_runtime_race_acceptance_proven",
                    "shutdown_during_restore_durability_proven",
                    "original_v309_behavioral_parity_proven"):
            self.assertFalse(report[key])

    def test_no_recovered_source_or_user_data_output(self):
        text = json.dumps(self.audit())
        self.assertNotIn("synthetic candidate marker", text)
        self.assertNotIn("SwingUtilities.invokeLater", text)
        self.assertNotIn("kit.zip", text)

    def test_kit_sha_drift_refused(self):
        with self.assertRaisesRegex(audit.Refused, "ARCHIVE_SHA_DRIFT"):
            audit.audit(
                kit=self.kit, reference=self.reference,
                sources=self.sources, classes=self.classes,
                kit_sha="0"*64, reference_sha=digest(self.reference),
                expected_sources=1, expected_classes=1,
            )

    def test_reference_sha_drift_refused(self):
        with self.assertRaisesRegex(audit.Refused, "ARCHIVE_SHA_DRIFT"):
            audit.audit(
                kit=self.kit, reference=self.reference,
                sources=self.sources, classes=self.classes,
                kit_sha=digest(self.kit), reference_sha="0"*64,
                expected_sources=1, expected_classes=1,
            )

    def test_invalid_pin_refused(self):
        with self.assertRaisesRegex(audit.Refused, "INVALID_SHA_PIN"):
            audit.require_pin(self.kit, "bad")

    def test_no_changed_source_refused(self):
        self.inputs[audit.SOURCE_REL] = self.originals[audit.SOURCE_REL]
        self.write_all()
        with self.assertRaisesRegex(audit.Refused, "SOURCE_CHANGE_SCOPE_DRIFT"):
            self.audit()

    def test_unexpected_second_source_change_refused(self):
        self.inputs["safe/Other.java"] = b"class Other { int v=1; }"
        self.originals["safe/Other.java"] = b"class Other { int v=0; }"
        self.write_all()
        with self.assertRaisesRegex(audit.Refused, "SOURCE_CHANGE_SCOPE_DRIFT"):
            self.audit()

    def test_missing_compiled_class_refused(self):
        self.class_candidate = {}
        self.write_all()
        with self.assertRaisesRegex(audit.Refused, "CLASS_SET_DRIFT"):
            self.audit()

    def test_identical_compiled_class_refused(self):
        self.class_candidate = dict(self.class_baseline)
        self.write_all()
        with self.assertRaisesRegex(audit.Refused, "COMPILED_CHANGE_SCOPE_DRIFT"):
            self.audit()

    def test_unexpected_second_changed_class_refused(self):
        other = "rs/unused/Other.class"
        self.class_baseline[other] = b"one"
        self.class_candidate[other] = b"two"
        self.write_all()
        with self.assertRaisesRegex(audit.Refused, "COMPILED_CHANGE_SCOPE_DRIFT"):
            self.audit()

    def test_no_pending_clear_inside_restore(self):
        self.inputs[audit.SOURCE_REL] += b"\nvoid extra() { pendingRecords.clear(); }\n"
        # Source-level prohibition is scoped to loadHistory, not the whole class.
        self.write_all()
        self.assertTrue(self.audit()["pending_live_drops_not_cleared_in_restore"])

    def test_pending_clear_in_load_refused(self):
        updated = self.inputs[audit.SOURCE_REL].replace(
            b"restorePanel.addRecords(rows);",
            b"restorePanel.addRecords(rows); pendingRecords.clear();",
        )
        self.inputs[audit.SOURCE_REL] = updated
        self.write_all()
        with self.assertRaisesRegex(audit.Refused, "PENDING_DROP_CLEAR_IN_RESTORE"):
            self.audit()

    def test_save_barrier_removed_refused(self):
        self.inputs[audit.SOURCE_REL] = self.inputs[audit.SOURCE_REL].replace(
            b"r395WriteDeferred = true;", b"r395WriteDeferred = false;")
        self.write_all()
        with self.assertRaisesRegex(audit.Refused, "PERSISTENCE_BARRIER_MISSING"):
            self.audit()

    def test_clear_invalidation_removed_refused(self):
        self.inputs[audit.SOURCE_REL] = self.inputs[audit.SOURCE_REL].replace(
            b"void clearHistory(){\n    ++r395HistoryGeneration;",
            b"void clearHistory(){\n    noOp();")
        self.write_all()
        with self.assertRaisesRegex(audit.Refused, "CLEAR_INVALIDATION_MISSING"):
            self.audit()

    def test_stop_invalidation_removed_refused(self):
        self.inputs[audit.SOURCE_REL] = self.inputs[audit.SOURCE_REL].replace(
            b"instance = null;\n    ++r395HistoryGeneration;",
            b"instance = null;\n    noOp();")
        self.write_all()
        with self.assertRaisesRegex(audit.Refused, "STOP_INVALIDATION_MISSING"):
            self.audit()

    def test_start_generation_reset_removed_refused(self):
        self.inputs[audit.SOURCE_REL] = self.inputs[audit.SOURCE_REL].replace(
            b"historyLoaded = false;", b"historyLoaded = true;")
        self.write_all()
        with self.assertRaisesRegex(audit.Refused, "START_GENERATION_RESET_MISSING"):
            self.audit()

    def test_generation_guard_removed_refused(self):
        self.inputs[audit.SOURCE_REL] = self.inputs[audit.SOURCE_REL].replace(
            b"generation != r395HistoryGeneration",
            b"generation == r395HistoryGeneration")
        self.write_all()
        with self.assertRaisesRegex(audit.Refused, "STALE_GENERATION_GUARD_MISSING"):
            self.audit()

    def test_edt_callback_removed_refused(self):
        self.inputs[audit.SOURCE_REL] = self.inputs[audit.SOURCE_REL].replace(
            b"SwingUtilities.invokeLater(", b"SwingUtilities.invokeAndWait(")
        self.write_all()
        with self.assertRaisesRegex(audit.Refused, "ASYNC_LOAD_STRUCTURE_DRIFT"):
            self.audit()

    def test_archive_traversal_refused(self):
        with ZipFile(self.kit, "w") as z:
            z.writestr("source/../bad.java", b"bad")
        with self.assertRaisesRegex(audit.Refused, "UNSAFE_ZIP_MEMBER"):
            audit.read_zip_bytes(self.kit, "source/", ".java")

    def test_archive_duplicate_refused(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(self.kit, "w") as z:
                z.writestr("source/" + audit.SOURCE_REL, b"a")
                z.writestr("source/" + audit.SOURCE_REL, b"b")
        with self.assertRaisesRegex(audit.Refused, "DUPLICATE_ZIP_ENTRY"):
            audit.read_zip_bytes(self.kit, "source/", ".java")

    def test_refuse_existing_report_no_mutation(self):
        out = self.root / "report.json"
        out.write_text("KEEP", encoding="utf8")
        args = [
            "--kit", str(self.kit), "--kit-sha256", digest(self.kit),
            "--reference", str(self.reference), "--reference-sha256", digest(self.reference),
            "--candidate-sources", str(self.sources), "--candidate-classes", str(self.classes),
            "--expected-sources", "1", "--expected-classes", "1",
            "--out", str(out),
        ]
        self.assertEqual(audit.main(args), 2)
        self.assertEqual(out.read_text("utf8"), "KEEP")

    def test_positive_cli_json(self):
        out = self.root / "new.json"
        args = [
            "--kit", str(self.kit), "--kit-sha256", digest(self.kit),
            "--reference", str(self.reference), "--reference-sha256", digest(self.reference),
            "--candidate-sources", str(self.sources), "--candidate-classes", str(self.classes),
            "--expected-sources", "1", "--expected-classes", "1",
            "--out", str(out),
        ]
        self.assertEqual(audit.main(args), 0)
        self.assertFalse(json.loads(out.read_text("utf8"))["launch_authorized"])


if __name__ == "__main__":
    unittest.main()
