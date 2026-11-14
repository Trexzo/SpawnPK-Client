"""R397 public-only synthetic tests for private clean-stop static acceptance.

No recovered Java source, JAR, client process, network or production data.
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
def load_module(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

audit=load_module("r397_clean_gate",ROOT/"tools/r397/audit_clean_stop_candidate.py")
prior_tests=load_module("r396_public_fixtures",ROOT/"tests/test_v309_r396_shutdown_merge_gate.py")

GUARD="""    synchronized (r395HistoryGate) {
      if (r396PreloadRecords.isEmpty() &&
          pendingRecords.isEmpty() &&
          panel.getRecordsOffEdt().isEmpty()) {
        return true;
      }
    }
"""
PRIOR=prior_tests.FAKE_PLUGIN
CURRENT=PRIOR.replace(
    "    List<LootTrackerRecord> original = historyStore.loadForMerge();",
    GUARD+"    List<LootTrackerRecord> original = historyStore.loadForMerge();")
STORE=prior_tests.FAKE_STORE


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R397CleanStopTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir=Path(self.temp.name)
        self.kit=self.dir/"kit.zip"
        self.ref=self.dir/"reference.jar"
        self.oldsrc=self.dir/"r396-source"
        self.oldcls=self.dir/"r396-classes"
        self.newsrc=self.dir/"r397-source"
        self.newcls=self.dir/"r397-classes"
        self.prior_plugin=PRIOR.encode("utf8")
        self.current_plugin=CURRENT.encode("utf8")
        self.prior_store=STORE.encode("utf8")
        self.current_store=STORE.encode("utf8")
        self.prior_class=b"r396 private synthetic class"
        self.current_class=b"r397 private synthetic class"
        self.write()

    @staticmethod
    def save_tree(root, values):
        root.mkdir(parents=True,exist_ok=True)
        for path in root.rglob("*"):
            if path.is_file(): path.unlink()
        for name,data in values.items():
            full=root/name
            full.parent.mkdir(parents=True,exist_ok=True)
            full.write_bytes(data)

    def write(self):
        plugin=audit.PLUGIN_SOURCE
        store=audit.r396.STORE
        pc=audit.PLUGIN_CLASS
        sc=store[:-5]+".class"
        with ZipFile(self.kit,"w") as archive:
            archive.writestr("source/"+plugin,b"original synthetic plugin")
            archive.writestr("source/"+store,b"original synthetic store")
        with ZipFile(self.ref,"w") as archive:
            archive.writestr(pc,b"original synthetic class P")
            archive.writestr(sc,b"original synthetic class S")
        self.save_tree(self.oldsrc,{plugin:self.prior_plugin,store:self.prior_store})
        self.save_tree(self.newsrc,{plugin:self.current_plugin,store:self.current_store})
        self.save_tree(self.oldcls,{pc:self.prior_class,sc:b"r396 store class"})
        self.save_tree(self.newcls,{pc:self.current_class,sc:b"r396 store class"})

    def run_audit(self):
        return audit.audit(self.kit,sha(self.kit),self.ref,sha(self.ref),
                           self.oldsrc,self.oldcls,self.newsrc,self.newcls,2,2)

    def test_realistic_synthetic_success_and_fail_closed(self):
        result=self.run_audit()
        self.assertEqual(result["status"],"R397_PRIVATE_CLEAN_STOP_STATIC_GATE_PASS")
        self.assertEqual(result["change_vs_r396_source_count"],1)
        self.assertEqual(result["change_vs_r396_class_count"],1)
        for flag in ("normal_host_launch_authorized","journal_integrated_with_game",
                     "real_crash_recovery_durability_proven",
                     "actual_clean_stop_noop_observed","merge_approved",
                     "private_source_release_approved"):
            self.assertFalse(result[flag])

    def test_no_private_source_bodies_in_report(self):
        payload=json.dumps(self.run_audit())
        self.assertNotIn("r396PreloadRecords.isEmpty()",payload)
        self.assertNotIn("source/",payload)
        self.assertNotIn("r397-source",payload)

    def test_missing_preload_guard_refused(self):
        self.current_plugin=self.current_plugin.replace(
            b"r396PreloadRecords.isEmpty()",b"r396PreloadRecords.size()>=0")
        self.write()
        with self.assertRaisesRegex(audit.Refused,"CLEAN_STOP_TRIPLE_EMPTY_GUARD_MISSING"):
            self.run_audit()

    def test_missing_pending_guard_refused(self):
        self.current_plugin=self.current_plugin.replace(
            b"pendingRecords.isEmpty()",b"pendingRecords.size()>=0")
        self.write()
        with self.assertRaisesRegex(audit.Refused,"CLEAN_STOP_TRIPLE_EMPTY_GUARD_MISSING"):
            self.run_audit()

    def test_missing_panel_guard_refused(self):
        self.current_plugin=self.current_plugin.replace(
            b"panel.getRecordsOffEdt().isEmpty()",b"true")
        self.write()
        with self.assertRaisesRegex(audit.Refused,"CLEAN_STOP_TRIPLE_EMPTY_GUARD_MISSING"):
            self.run_audit()

    def test_noop_must_return_true(self):
        self.current_plugin=self.current_plugin.replace(
            b"        return true;\n      }\n    }\n    List<LootTrackerRecord>",
            b"        return false;\n      }\n    }\n    List<LootTrackerRecord>")
        self.write()
        with self.assertRaisesRegex(audit.Refused,"CLEAN_STOP_TRIPLE_EMPTY_GUARD_MISSING"):
            self.run_audit()

    def test_guard_after_read_refused(self):
        self.current_plugin=PRIOR.replace(
            "    List<LootTrackerRecord> original = historyStore.loadForMerge();",
            "    List<LootTrackerRecord> original = historyStore.loadForMerge();\n"+GUARD).encode("utf8")
        self.write()
        with self.assertRaisesRegex(audit.Refused,"CLEAN_STOP_GUARD_NOT_BEFORE_DISK_IO"):
            self.run_audit()

    def test_guard_only_in_comment_refused(self):
        self.current_plugin=PRIOR.replace(
            "  boolean r396FinishStopMerge() {",
            "  boolean r396FinishStopMerge() { // "+GUARD.replace("\n"," ")).encode("utf8")
        self.write()
        with self.assertRaisesRegex(audit.Refused,"CLEAN_STOP_TRIPLE_EMPTY_GUARD_MISSING"):
            self.run_audit()

    def test_prior_source_replaced_not_only_one_delta(self):
        self.prior_store+=b"\n// changed owner-private store unexpectedly"
        self.write()
        with self.assertRaisesRegex(audit.Refused,"PREVIOUS_SOURCE_DELTA_SCOPE_DRIFT"):
            self.run_audit()

    def test_candidate_store_changed_again_refused(self):
        self.current_store+=b"\n// unexpected change"
        self.write()
        with self.assertRaisesRegex(audit.Refused,"PREVIOUS_SOURCE_DELTA_SCOPE_DRIFT"):
            self.run_audit()

    def test_old_class_set_changed_refused(self):
        self.oldcls.joinpath(audit.PLUGIN_CLASS).unlink()
        with self.assertRaisesRegex(audit.Refused,"PREVIOUS_CLASS_SET_DRIFT"):
            self.run_audit()

    def test_unexpected_new_class_same_as_prior_refused(self):
        self.current_class=self.prior_class
        self.write()
        with self.assertRaisesRegex(audit.Refused,"PREVIOUS_CLASS_DELTA_SCOPE_DRIFT"):
            self.run_audit()

    def test_source_pin_drift_refused(self):
        with self.assertRaisesRegex(audit.Refused,"ARCHIVE_SHA_DRIFT"):
            audit.audit(self.kit,"0"*64,self.ref,sha(self.ref),
                        self.oldsrc,self.oldcls,self.newsrc,self.newcls,2,2)

    def test_refuses_to_overwrite_output(self):
        path=self.dir/"report.json"
        path.write_text("KEEP",encoding="utf8")
        args=[
            "--kit",str(self.kit),"--kit-sha256",sha(self.kit),
            "--reference",str(self.ref),"--reference-sha256",sha(self.ref),
            "--previous-sources",str(self.oldsrc),
            "--previous-classes",str(self.oldcls),
            "--candidate-sources",str(self.newsrc),
            "--candidate-classes",str(self.newcls),
            "--expected-sources","2","--expected-classes","2","--out",str(path)
        ]
        self.assertEqual(audit.main(args),2)
        self.assertEqual(path.read_text("utf8"),"KEEP")

    def test_positive_cli_json(self):
        path=self.dir/"report.json"
        args=[
            "--kit",str(self.kit),"--kit-sha256",sha(self.kit),
            "--reference",str(self.ref),"--reference-sha256",sha(self.ref),
            "--previous-sources",str(self.oldsrc),
            "--previous-classes",str(self.oldcls),
            "--candidate-sources",str(self.newsrc),
            "--candidate-classes",str(self.newcls),
            "--expected-sources","2","--expected-classes","2","--out",str(path)
        ]
        self.assertEqual(audit.main(args),0)
        self.assertEqual(json.loads(path.read_text("utf8"))["status"],
                         "R397_PRIVATE_CLEAN_STOP_STATIC_GATE_PASS")


if __name__=="__main__":
    unittest.main()
