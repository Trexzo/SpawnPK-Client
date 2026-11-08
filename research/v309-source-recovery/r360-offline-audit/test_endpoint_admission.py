"""R349 original endpoint evidence boundary / no false localhost promotion."""
from __future__ import annotations
from pathlib import Path
import copy
import json
import tempfile
import unittest

from endpoint_admission import (
    AdmissionRefused,evaluate,read_json_no_duplicate_keys,
)

HERE=Path(__file__).resolve().parent
EVIDENCE=HERE.parent/"v309-r346"/"evidence"/"owner_original_gui_two_trials.json"

class R349AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.original=read_json_no_duplicate_keys(EVIDENCE)

    def test_two_actual_owner_gui_receipts_do_not_authorize_localhost(self):
        x=evaluate(self.original)
        self.assertEqual(x["status"],"R349_ORIGINAL_ENDPOINT_ADMISSION_BLOCKED")
        self.assertEqual(x["original_java_gui_window"],"OBSERVED_TWICE")
        self.assertEqual(x["original_gui_guard_blocked_non_test_connections"],[3,3])
        self.assertEqual(x["original_v309_override_property_support"],"NOT_VERIFIED")
        self.assertFalse(x["localhost_protocol_test_authorized"])
        self.assertEqual(x["original_client_connected_to_localhost"],"NOT_TESTED")
        self.assertEqual(x["authenticated_login"],"NOT_TESTED")
        self.assertEqual(x["same_jvm_reconnect"],"NOT_TESTED")

    def test_wrong_binary_does_not_pass(self):
        x=copy.deepcopy(self.original)
        x["original_game_jar_sha256"]="0"*64
        with self.assertRaisesRegex(AdmissionRefused,"UNPINNED"):
            evaluate(x)

    def test_missing_trial_does_not_pass(self):
        for name in ("first_trial","second_trial"):
            x=copy.deepcopy(self.original)
            x.pop(name)
            with self.subTest(name=name),self.assertRaisesRegex(
                AdmissionRefused,"MISSING_OWNER"):
                evaluate(x)

    def test_mutated_owner_gui_assertions_fail(self):
        changes={
            "original_launcher_main_invoked":False,
            "original_launcher_stage":"LOADING_LAUNCHER_CLASS",
            "original_stdout_redirected":False,
            "awt_windows_showing":0,
            "blocked_other_connections":0,
            "parent_exit_code":1,
        }
        for trial in ("first_trial","second_trial"):
            for name,wrong in changes.items():
                x=copy.deepcopy(self.original)
                x[trial][name]=wrong
                with self.subTest(trial=trial,field=name),self.assertRaises(
                    AdmissionRefused):
                    evaluate(x)

    def test_fake_authenticated_login_or_reconnect_refused(self):
        for name,value in (("login","PASS"),
                           ("same_original_jvm_reconnect","PASS")):
            x=copy.deepcopy(self.original)
            x[name]=value
            with self.subTest(field=name),self.assertRaisesRegex(
                AdmissionRefused,"UNVERIFIED"):
                evaluate(x)

    def test_wrong_milestone_refused(self):
        x=copy.deepcopy(self.original)
        x["milestone"]="R348"
        with self.assertRaisesRegex(AdmissionRefused,"R346"):
            evaluate(x)

    def test_json_duplicate_keys_refused(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"ambiguous.json"
            f.write_text('{"login":"PASS","login":"NOT_TESTED"}',encoding="utf-8")
            with self.assertRaisesRegex(AdmissionRefused,"DUPLICATE"):
                read_json_no_duplicate_keys(f)

    def test_source_based_flag_claims_cannot_promote_original(self):
        x=evaluate(self.original)
        self.assertIn("LATER_EDIT_ADDED",x["external_decompiled_source"])
        self.assertTrue(x["configured_property_is_not_original_endpoint_proof"])
        self.assertEqual(x["original_v309_remote_host"],"NOT_RESOLVED")
        self.assertEqual(x["original_v309_cache_subfolder"],"NOT_RESOLVED")

    def test_no_desktop_or_original_binary_exec_in_script(self):
        code=(HERE/"endpoint_admission.py").read_text("utf-8")
        self.assertNotIn("subprocess.",code)
        self.assertNotIn("socket.connect(",code)
        self.assertNotIn("System.setProperty",code)

if __name__=="__main__":
    unittest.main(verbosity=2)
