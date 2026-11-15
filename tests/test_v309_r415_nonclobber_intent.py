"""Public-only R415 nonclobber intent-producer structural negative controls.

The input is the independently invented Java fixture only. These tests
never read private client sources, JARs, actual histories, marker files
or production paths and are not evidence of a private R415 build.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"tests/fixtures/r415/R415NonClobberDeleteIntentSynthetic.java"
spec=importlib.util.spec_from_file_location(
    "r415_public_gate",ROOT/"tools/r415/audit_nonclobber_intent_synthetic.py")
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class R415PublicIntentGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=FIXTURE.read_text(encoding="utf8")
        cls.valid=gate.inspect(cls.original)

    def mutate(self,old,new,expected=None):
        self.assertIn(old,self.original,"synthetic mutation anchor absent")
        text=self.original.replace(old,new)
        with self.assertRaises(gate.Refused) as failure:
            gate.inspect(text)
        if expected:self.assertIn(expected,str(failure.exception))

    def test_positive_public_only_scope(self):
        self.assertEqual(self.valid["status"],
                         "R415_PUBLIC_ONLY_NONCLOBBER_SYNTHETIC_GATE_PASS")
        self.assertTrue(self.valid["intent_publication_uses_exclusive_hardlink"])
        self.assertTrue(self.valid["fresh_jvm_restart_covered"])
        self.assertFalse(self.valid["actual_private_candidate_verified"])
        self.assertFalse(self.valid["private_game_executed"])
        self.assertFalse(self.valid["release_authorized"])
        self.assertFalse(self.valid["merge_approved"])

    def test_report_never_exposes_private_source_or_identity(self):
        data=json.dumps(self.valid)
        for forbidden in ("C:\\\\Users", "loot-history.json", "client.jar",
                          "DESKTOP-", "session", "credentials", "real history bytes"):
            self.assertNotIn(forbidden,data)

    def test_no_marker_auto_cleanup(self):
        self.assertFalse(self.valid["final_marker_auto_cleanup"])

    def test_second_delete_disallowed_until_reconcile(self):
        self.assertFalse(self.valid["second_delete_accepted_before_reconciliation"])

    def test_no_physical_power_loss_durability_claim(self):
        self.assertFalse(self.valid["directory_metadata_durability_proven"])

    def test_no_interprocess_lock_claim(self):
        self.assertFalse(self.valid["interprocess_lock_proven"])

    def test_history_staged_before_marker(self):
        self.mutate("forced(stage,next);","stageSkipped(next);")

    def test_fsync_marker_before_publication(self):
        self.mutate("forced(markerTemp,markerBytes);",
                    "Files.write(markerTemp,markerBytes);")

    def test_marker_cannot_be_overwritten_by_atomic_move(self):
        self.mutate("Files.createLink(marker,markerTemp);",
                    "Files.move(markerTemp,marker,StandardCopyOption.ATOMIC_MOVE);",
                    "R415_MARKER_OVERWRITE_BY_ATOMIC_MOVE_NOT_ALLOWED")

    def test_marker_must_be_published_once(self):
        self.mutate("Files.createLink(marker,markerTemp);",
                    "Files.createLink(marker,markerTemp); Files.createLink(marker,markerTemp);")

    def test_existing_final_marker_must_never_be_deleted(self):
        self.mutate("Files.createLink(marker,markerTemp);",
                    "Files.delete(marker); Files.createLink(marker,markerTemp);",
                    "R415_NEVER_AUTO_CLEAN_FINAL_INTENT")

    def test_marker_renaming_with_replace_refused(self):
        self.mutate("Files.createLink(marker,markerTemp);",
                    "Files.move(markerTemp,marker,StandardCopyOption.REPLACE_EXISTING);")

    def test_marker_temp_only_removed_after_link(self):
        self.mutate("Files.delete(markerTemp); // only the newly owned temporary link",
                    "Files.delete(markerTemp); // only the newly owned temporary link\n                Files.delete(marker);")

    def test_prepared_marker_must_match_old_history(self):
        self.mutate('eq(classify(),State.ABORTED_BEFORE_REPLACE,',
                    'eq(classify(),State.NONE,')

    def test_strict_atomic_history_move_required(self):
        self.mutate("Files.move(stage,history,StandardCopyOption.ATOMIC_MOVE,",
                    "Files.move(stage,history,StandardCopyOption.REPLACE_EXISTING,")

    def test_writer_must_mark_ambiguous_move_phase(self):
        self.mutate("phase=Phase.REPLACE_ATTEMPTED;",
                    "phase=Phase.FAILED_BEFORE_REPLACE;")

    def test_writer_must_mark_success_after_move(self):
        self.mutate("phase=Phase.COMMITTED;",
                    "phase=Phase.REPLACE_ATTEMPTED;")

    def test_original_digest_required(self):
        self.mutate("String before=digest(history,true);",
                    "String before=null;")

    def test_new_staged_digest_required(self):
        self.mutate("String after=digest(stage,false);",
                    "String after=null;")

    def test_new_image_reverified_before_move(self):
        self.mutate("!after.equals(digest(stage,false)))return false;",
                    "false)return false;")

    def test_old_image_reverified_before_move(self):
        self.mutate("if(!before.equals(digest(history,true))||",
                    "if(false||")

    def test_before_and_after_image_must_differ(self):
        self.mutate("if(after==null||before.equals(after))return false;",
                    "if(after==null)return false;")

    def test_refuse_unresolved_intent_before_mutation(self):
        self.mutate("if(unsafe||!admitted())",
                    "if(unsafe)")

    def test_recovery_inspector_must_fence_intent_temp(self):
        self.mutate("if(present(markerTemp))return State.QUARANTINED;",
                    "if(false)return State.QUARANTINED;")

    def test_recovery_inspector_must_fence_unresolved_intent(self):
        self.mutate("if(!present(marker))return State.NONE;",
                    "if(true)return State.NONE;")

    def test_recovery_inspector_must_fence_orphan_history_stage(self):
        self.mutate("classify()==State.NONE&&!present(stage)",
                    "classify()==State.NONE")

    def test_post_move_failure_must_not_roll_back_original_rows(self):
        self.mutate("if(phase==Phase.FAILED_BEFORE_REPLACE)",
                    "if(phase!=Phase.COMMITTED)",
                    "R415_AMBIGUOUS_WRITE_ROLLBACK_NOT_ALLOWED")

    def test_commit_disposition_must_not_be_optimistic(self):
        self.mutate("phase=Phase.REPLACE_ATTEMPTED;\n            historyMoveAttempts++;",
                    "phase=Phase.COMMITTED;\n            historyMoveAttempts++;")

    def test_crash_after_intent_force_test_mandatory(self):
        self.mutate("crashAfterIntentTempForceIsQuarantined();","")

    def test_crash_after_hardlink_test_mandatory(self):
        self.mutate("crashAfterHardlinkQuarantinesBothNames();","")

    def test_crash_after_published_intent_test_mandatory(self):
        self.mutate("crashAfterIntentPublishedClassifiesAborted();","")

    def test_crash_after_history_move_test_mandatory(self):
        self.mutate("crashAfterHistoryMoveRecognizedOnRestart();","")

    def test_cross_process_marker_collision_test_mandatory(self):
        self.mutate("foreignMarkerAfterPreflightNotOverwritten();","")

    def test_cross_process_history_conflict_test_mandatory(self):
        self.mutate("mainChangedAfterMarkerRefusesMove();","")

    def test_cross_process_staged_image_conflict_test_mandatory(self):
        self.mutate("stagedChangedAfterMarkerRefusesMove();","")

    def test_separate_jvm_restart_test_mandatory(self):
        self.mutate("separateJvmRestartCommittedBeforeAck();","")

    def test_cli_refuses_an_unexpected_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"wrong-synthetic-fixture.java"
            p.write_text(self.original,encoding="utf8")
            self.assertEqual(gate.main(["--fixture",str(p)]),2)

    def test_cli_positive_result_disallows_deployment(self):
        self.assertEqual(gate.main(["--fixture",str(FIXTURE)]),0)

if __name__=="__main__":
    unittest.main()
