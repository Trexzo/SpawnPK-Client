"""R349: prevent external reconstructed-source flags from certifying original v309.

This is an evidence-admission policy, NOT a test of the actual original JAR.
The 2026-10-13 external-source audit says the override flags were an edited
source change. R346 original GUI runtime allowed one window but blocked
three network attempts on each of two isolated runs.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

PIN="ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"

class AdmissionRefused(ValueError):
    pass

def read_json_no_duplicate_keys(path):
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:
                raise AdmissionRefused("DUPLICATE_KEY_"+k)
            result[k]=v
        return result
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      object_pairs_hook=unique)

def evaluate(original_gui_trials):
    if not isinstance(original_gui_trials,dict):
        raise AdmissionRefused("TRIAL_EVIDENCE_NOT_OBJECT")
    if original_gui_trials.get("milestone")!="R346":
        raise AdmissionRefused("NOT_R346_EVIDENCE")
    if original_gui_trials.get("original_game_jar_sha256")!=PIN:
        raise AdmissionRefused("UNPINNED_CLIENT_IDENTITY")
    for name in ("first_trial","second_trial"):
        trial=original_gui_trials.get(name)
        if not isinstance(trial,dict):
            raise AdmissionRefused("MISSING_OWNER_TRIAL_"+name)
        if (trial.get("original_launcher_main_invoked") is not True or
            trial.get("original_launcher_stage")!="MAIN_RETURNED" or
            trial.get("original_stdout_redirected") is not True or
            trial.get("awt_windows_showing")!=1 or
            type(trial.get("blocked_other_connections")) is not int or
            trial["blocked_other_connections"]<1 or
            trial.get("parent_exit_code")!=0):
            raise AdmissionRefused("INCONSISTENT_OWNER_GUI_TRIAL_"+name)
    if (original_gui_trials.get("login")!="NOT_TESTED" or
        original_gui_trials.get("same_original_jvm_reconnect")!="NOT_TESTED"):
        raise AdmissionRefused("UNVERIFIED_LOGIN_OR_RECONNECT_PROMOTED")
    return {
        "status":"R349_ORIGINAL_ENDPOINT_ADMISSION_BLOCKED",
        "external_decompiled_source":
            "LATER_EDIT_ADDED_SPK_SERVERHOST_SERVERPORT_OVERRIDES",
        "original_v309_override_property_support":"NOT_VERIFIED",
        "original_v309_remote_host":"NOT_RESOLVED",
        "original_v309_cache_subfolder":"NOT_RESOLVED",
        "original_java_gui_window":"OBSERVED_TWICE",
        "original_launcher_stdout_redirected":"OBSERVED_TWICE",
        "original_gui_guard_blocked_non_test_connections":[
            original_gui_trials[n]["blocked_other_connections"]
            for n in ("first_trial","second_trial")],
        "configured_property_is_not_original_endpoint_proof":True,
        "localhost_protocol_test_authorized":False,
        "original_client_connected_to_localhost":"NOT_TESTED",
        "authenticated_login":"NOT_TESTED",
        "same_jvm_reconnect":"NOT_TESTED",
        "required_next_evidence":[
            "ORIGINAL_JAR_CONFIRMED_ENDPOINT_CONFIGURATION",
            "ORIGINAL_CLIENT_PROCESS_LOCALHOST_CONNECTION_VERIFIED",
            "ISOLATED_APPROVED_CACHE_AND_SERVER_PROTOCOL_FIXTURE"
        ],
        "independent_os_attestation":False
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--owner-gui-evidence",required=True,type=Path)
    a=p.parse_args(argv)
    try:
        result=evaluate(read_json_no_duplicate_keys(a.owner_gui_evidence))
    except (AdmissionRefused,OSError,ValueError) as ex:
        print(json.dumps({"status":"R349_ADMISSION_REFUSED","reason":str(ex),
                          "same_jvm_reconnect":"NOT_TESTED"}))
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
