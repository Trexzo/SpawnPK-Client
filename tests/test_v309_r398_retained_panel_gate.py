"""R398 synthetic SHA-pinned retained-panel and panel-lock ordering gate tests."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

audit=load_module("r398_gate",ROOT/"tools/r398/audit_retained_panel_candidate.py")
fixture=load_module("r396_synthetic",ROOT/"tests/test_v309_r396_shutdown_merge_gate.py")

FAKE_OLD=fixture.FAKE_PLUGIN
FAKE_STORE=fixture.FAKE_STORE

def candidate_body():
    s=FAKE_OLD.replace(
        "class SyntheticPlugin {",
        "class SyntheticPlugin {\n  volatile boolean r398UnreconciledPanelAtStart;"
    )
    s=s.replace(
        "    if (r396PanelResetAfterVerifiedStop) panel.clearRecords();",
        """    panel = this.injector.getInstance(LootTrackerPanel.class);
    boolean r398ResetPreviouslyCommitted = r396PanelResetAfterVerifiedStop;
    r396PanelResetAfterVerifiedStop = false;
    if (r398ResetPreviouslyCommitted) {panel.clearRecords();}
    boolean r398HasRetainedRecords = !panel.getRecordsOffEdt().isEmpty();
    synchronized (r395HistoryGate) {
      r398UnreconciledPanelAtStart = r398HasRetainedRecords;
    }""")
    s=s.replace(
        "  void loadHistory() {\n",
        "  void loadHistory() {\n    if (r398UnreconciledPanelAtStart) {return;}\n")
    s=s.replace(
        "  boolean r396FinishStopMerge() {\n",
        """  boolean r396FinishStopMerge() {
    if (r398UnreconciledPanelAtStart) {return false;}
    final boolean r398PanelEmpty = panel.getRecordsOffEdt().isEmpty();
    synchronized (r395HistoryGate) {
      if (r396PreloadRecords.isEmpty() &&
          pendingRecords.isEmpty() && r398PanelEmpty) {
        return true;
      }
    }
""")
    s=s.replace(
        "    r396PreloadRecords.clear();\n    pendingRecords.clear();",
        "    r396PreloadRecords.clear();\n"
        "    r398UnreconciledPanelAtStart = false;\n"
        "    pendingRecords.clear();")
    return s


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R398PanelGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.kit=self.root/"kit.zip"
        self.reference=self.root/"reference.jar"
        self.prior_source_dir=self.root/"prior-source"
        self.prior_class_dir=self.root/"prior-class"
        self.source_dir=self.root/"source"
        self.class_dir=self.root/"classes"
        self.prior_plugin=FAKE_OLD.encode("utf8")
        self.new_plugin=candidate_body().encode("utf8")
        self.prior_store=FAKE_STORE.encode("utf8")
        self.new_store=FAKE_STORE.encode("utf8")
        self.prior_plugin_class=b"r397 original synthetic plugin class"
        self.current_plugin_class=b"r398 new synthetic plugin class"
        self.write()

    @staticmethod
    def files(root,content):
        root.mkdir(parents=True,exist_ok=True)
        for p in root.rglob("*"):
            if p.is_file():p.unlink()
        for name,data in content.items():
            full=root/name
            full.parent.mkdir(parents=True,exist_ok=True)
            full.write_bytes(data)

    def write(self):
        plugin=audit.PLUGIN
        store=audit.r396.STORE
        plugin_class=audit.CLASS
        store_class=store[:-5]+".class"
        with ZipFile(self.kit,"w") as z:
            z.writestr("source/"+plugin,b"synthetic original plugin")
            z.writestr("source/"+store,b"synthetic original store")
        with ZipFile(self.reference,"w") as z:
            z.writestr(plugin_class,b"synthetic base plugin class")
            z.writestr(store_class,b"synthetic base store class")
        self.files(self.prior_source_dir,{plugin:self.prior_plugin,store:self.prior_store})
        self.files(self.source_dir,{plugin:self.new_plugin,store:self.new_store})
        self.files(self.prior_class_dir,
                   {plugin_class:self.prior_plugin_class,store_class:b"synthetic store"})
        self.files(self.class_dir,
                   {plugin_class:self.current_plugin_class,store_class:b"synthetic store"})

    def audit(self):
        return audit.audit(
            kit=self.kit,kit_sha=digest(self.kit),
            reference=self.reference,reference_sha=digest(self.reference),
            previous_sources=self.prior_source_dir,
            previous_classes=self.prior_class_dir,
            candidate_sources=self.source_dir,candidate_classes=self.class_dir,
            expected_sources=2,expected_classes=2)

    def alter(self,old,new):
        self.assertIn(old.encode("utf8"),self.new_plugin)
        self.new_plugin=self.new_plugin.replace(old.encode("utf8"),new.encode("utf8"))
        self.write()

    def test_all_gates_closed_and_exact_delta(self):
        out=self.audit()
        self.assertEqual(out["status"],"R398_PRIVATE_RETAINED_PANEL_STATIC_GATE_PASS")
        self.assertEqual(out["changed_classes_vs_r397"],1)
        self.assertTrue(out["ambiguous_panel_autorestore_blocked"])
        self.assertTrue(out["panel_snapshot_outside_history_gate"])
        for flag in ("unresolved_panel_durability_proven","full_client_execution_authorized",
                     "history_journal_integrated","zero_data_loss_proven",
                     "private_source_release_approved","merge_approved"):
            self.assertFalse(out[flag])

    def test_no_private_code_leaks_into_report(self):
        data=json.dumps(self.audit())
        self.assertNotIn("getRecordsOffEdt().isEmpty()",data)
        self.assertNotIn("source/",data)
        self.assertNotIn("r398-source",data)

    def test_retained_flag_requires_volatile(self):
        self.alter("volatile boolean r398UnreconciledPanelAtStart",
                   "boolean r398UnreconciledPanelAtStart")
        with self.assertRaisesRegex(audit.Refused,"UNRECONCILED_FLAG_NOT_VOLATILE"):
            self.audit()

    def test_missing_retained_panel_snapshot_refused(self):
        self.alter("boolean r398HasRetainedRecords = !panel.getRecordsOffEdt().isEmpty();",
                   "boolean r398HasRetainedRecords = false;")
        with self.assertRaisesRegex(audit.Refused,"STARTUP_RETAINED_PANEL_PROVENANCE_DRIFT"):
            self.audit()

    def test_panel_reset_must_use_verified_commit_flag(self):
        self.alter("r398ResetPreviouslyCommitted = r396PanelResetAfterVerifiedStop",
                   "r398ResetPreviouslyCommitted = true")
        with self.assertRaisesRegex(audit.Refused,"STARTUP_RETAINED_PANEL_PROVENANCE_DRIFT"):
            self.audit()

    def test_startup_must_clear_prior_verified_panel(self):
        self.alter("if (r398ResetPreviouslyCommitted) {panel.clearRecords();}",
                   "if (r398ResetPreviouslyCommitted) {noOp();}")
        with self.assertRaisesRegex(audit.Refused,"STARTUP_RETAINED_PANEL_PROVENANCE_DRIFT"):
            self.audit()

    def test_restore_guard_cannot_be_removed(self):
        self.alter("if (r398UnreconciledPanelAtStart) {return;}",
                   "if (false) {return;}")
        with self.assertRaisesRegex(audit.Refused,"RETENTION_RESTORE_BLOCK_MISSING"):
            self.audit()

    def test_shutdown_refusal_cannot_be_removed(self):
        self.alter("if (r398UnreconciledPanelAtStart) {return false;}",
                   "if (r398UnreconciledPanelAtStart) {return true;}")
        with self.assertRaisesRegex(audit.Refused,"AMBIGUOUS_PANEL_NOT_REFUSED"):
            self.audit()

    def test_shutdown_guard_must_precede_disk_io(self):
        self.alter("    if (r398UnreconciledPanelAtStart) {return false;}",
                   "    boolean ignore = true;")
        with self.assertRaisesRegex(audit.Refused,"DIRTY_SHUTDOWN_RETENTION_GUARD_MISSING"):
            self.audit()

    def test_panel_snapshot_required_outside_gate(self):
        self.alter("r398PanelEmpty = panel.getRecordsOffEdt().isEmpty()",
                   "r398PanelEmpty = true")
        with self.assertRaisesRegex(audit.Refused,"PANEL_SNAPSHOT_MISSING"):
            self.audit()

    def test_panel_nested_inside_gate_refused(self):
        self.alter("pendingRecords.isEmpty() && r398PanelEmpty",
                   "pendingRecords.isEmpty() && panel.getRecordsOffEdt().isEmpty()")
        with self.assertRaisesRegex(audit.Refused,"PANEL_ACCESS_NESTED_INSIDE_RESTORE_GATE"):
            self.audit()

    def test_panel_clear_must_reset_unresolved(self):
        self.alter("r398UnreconciledPanelAtStart = false;",
                   "r398UnreconciledPanelAtStart = true;")
        with self.assertRaisesRegex(audit.Refused,"USER_CLEAR_MUST_RESET_RETENTION_GUARD"):
            self.audit()

    def test_dirty_merging_still_required(self):
        self.alter("combined.addAll(r396PreloadRecords)",
                   "combined.clear()")
        with self.assertRaises(audit.Refused):
            self.audit()

    def test_previous_source_delta_scope(self):
        self.prior_store+=b"\n// changed"
        self.write()
        with self.assertRaisesRegex(audit.Refused,"SOURCE_CHANGE_SCOPE_DRIFT"):
            self.audit()

    def test_class_delta_scope(self):
        self.current_plugin_class=self.prior_plugin_class
        self.write()
        with self.assertRaisesRegex(audit.Refused,"CLASS_CHANGE_SCOPE_DRIFT"):
            self.audit()

    def test_reference_pin_mismatch_refused(self):
        with self.assertRaisesRegex(audit.Refused,"ARCHIVE_SHA_DRIFT"):
            audit.audit(
                kit=self.kit,kit_sha=digest(self.kit),
                reference=self.reference,reference_sha="0"*64,
                previous_sources=self.prior_source_dir,
                previous_classes=self.prior_class_dir,
                candidate_sources=self.source_dir,candidate_classes=self.class_dir,
                expected_sources=2,expected_classes=2)

    def args(self,out):
        return [
            "--kit",str(self.kit),"--kit-sha256",digest(self.kit),
            "--reference",str(self.reference),"--reference-sha256",digest(self.reference),
            "--previous-sources",str(self.prior_source_dir),
            "--previous-classes",str(self.prior_class_dir),
            "--candidate-sources",str(self.source_dir),
            "--candidate-classes",str(self.class_dir),
            "--expected-sources","2","--expected-classes","2","--out",str(out)]

    def test_no_report_overwrite(self):
        file=self.root/"report.json"
        file.write_text("KEEP",encoding="utf8")
        self.assertEqual(audit.main(self.args(file)),2)
        self.assertEqual(file.read_text("utf8"),"KEEP")

    def test_positive_cli_synthetic_only(self):
        file=self.root/"report.json"
        self.assertEqual(audit.main(self.args(file)),0)
        self.assertFalse(json.loads(file.read_text("utf8"))["full_client_execution_authorized"])


if __name__=="__main__":
    unittest.main()
