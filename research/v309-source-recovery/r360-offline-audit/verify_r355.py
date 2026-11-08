#!/usr/bin/env python3
"""R355 report shape verifier: does NOT attest that a real JAR was scanned."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from scan_v309_network import PIN, AuditRefused, MAX_REPORT_ROWS, MAX_CLASSES, interesting

HEADER={
    "schema", "original_jar_sha256", "original_jar_bytes", "scope", "original_jar_executed",
    "os_egress_attested", "runtime_network_destinations_verified", "login_verified",
    "same_pid_reconnect_verified", "classes_scanned", "network_invocations_count",
    "network_calling_classes_count", "indirect_invocation_or_reflection_count",
    "indirect_calling_classes_count", "known_client_b_getByName_seen",
    "nominal_launcher_main_roots", "nominal_startup_reachable_network_calls_count",
    "nominal_startup_paths_truncated", "nominal_startup_network_paths",
    "nominal_startup_path_hop_limit",
    "known_client_b_socket_init_seen", "startup_class_network_callsite_count", "network_calls",
}
ROW={"class","method","method_descriptor","bytecode_offset","opcode",
     "target_class","target_method","target_descriptor"}


def _pairs_unique(pairs):
    result={}
    for k,v in pairs:
        if k in result:raise AuditRefused("DUPLICATE_JSON_KEY")
        result[k]=v
    return result

def verify_text(raw:str)->dict:
    try: report=json.loads(raw,object_pairs_hook=_pairs_unique)
    except (ValueError,TypeError) as e:raise AuditRefused("INVALID_JSON") from e
    if not isinstance(report,dict) or set(report)!=HEADER:
        raise AuditRefused("INVALID_REPORT_SCHEMA")
    if (report["schema"]!="R355_ORIGINAL_V309_NETWORK_BYTECODE_INVOKES_V1"
        or report["original_jar_sha256"]!=PIN
        or type(report["original_jar_bytes"]) is not int or report["original_jar_bytes"]!=17_532_075
        or report["scope"]!="rs/ classes only; method-level direct invocation instructions"):
        raise AuditRefused("INVALID_ORIGINAL_IDENTITY")
    for name in ("original_jar_executed","os_egress_attested",
                 "runtime_network_destinations_verified", "login_verified",
                 "same_pid_reconnect_verified"):
        if report[name] is not False:raise AuditRefused("FORGED_RUNTIME_CLAIM")
    for key in ("classes_scanned","network_invocations_count","network_calling_classes_count",
                "indirect_invocation_or_reflection_count","indirect_calling_classes_count",
                "startup_class_network_callsite_count", "nominal_launcher_main_roots",
                "nominal_startup_reachable_network_calls_count", "nominal_startup_path_hop_limit"):
        value=report[key]
        if type(value) is not int or not (0<=value<=MAX_REPORT_ROWS+MAX_REPORT_ROWS*100):
            raise AuditRefused("BAD_COUNTER")
    if report["nominal_startup_path_hop_limit"] != 12 or report["nominal_launcher_main_roots"] > 100:
        raise AuditRefused("BAD_NOMINAL_REACHABILITY_LIMIT")
    if report["classes_scanned"] == 0 or report["classes_scanned"]>MAX_CLASSES:
        raise AuditRefused("INVALID_CLASSES_SCANNED")
    if (report["known_client_b_getByName_seen"] is not True or
        report["known_client_b_socket_init_seen"] is not True):
        raise AuditRefused("MISSING_PREVIOUSLY_CONFIRMED_CLIENT_B_BASELINE")
    rows=report["network_calls"]
    if type(rows) is not list or len(rows)>MAX_REPORT_ROWS or len(rows)!=report["network_invocations_count"]:
        raise AuditRefused("BAD_ROW_COUNT")
    classes=set();startup=0
    for row in rows:
        if not isinstance(row,dict) or set(row)!=ROW:raise AuditRefused("BAD_ROW_KEYS")
        for key,pattern in (
            ("class",r"[A-Za-z_$][A-Za-z0-9_$.]*"),
            ("target_class",r"[A-Za-z_$][A-Za-z0-9_$.]*"),
            ("method",r"(?:[A-Za-z_$][A-Za-z0-9_$]*|<init>|<clinit>)"),
            ("target_method",r"(?:[A-Za-z_$][A-Za-z0-9_$]*|<init>|<clinit>)"),
            ("method_descriptor",r"[\[\]()A-Za-z0-9_$;/.]+"),
            ("target_descriptor",r"[\[\]()A-Za-z0-9_$;/.]+"),
            ("opcode",r"0x[0-9a-f]{2}")):
            if type(row[key]) is not str or len(row[key])>500 or not re.fullmatch(pattern,row[key]):
                raise AuditRefused("BAD_ROW_VALUE_OR_POTENTIAL_RAW_SECRET")
        if type(row["bytecode_offset"]) is not int or not 0<=row["bytecode_offset"]<=65535:
            raise AuditRefused("INVALID_BYTECODE_OFFSET")
        if row["opcode"] not in {"0xb6","0xb7","0xb8","0xb9"}:
            raise AuditRefused("NONINVOKE_OPCODE")
        if not interesting(row["target_class"].replace(".","/")):
            raise AuditRefused("NOT_A_NETWORK_API")
        if not row["class"].startswith("rs."):
            raise AuditRefused("NOT_FIRST_PARTY_CLASS")
        classes.add(row["class"])
        if row["class"] in {"rs.gui.Launcher","rs.p.a","rs.gui.M","rs.s.g","rs.ui.f","rs.A.q"}:
            startup+=1
    if len(classes)!=report["network_calling_classes_count"]:
        raise AuditRefused("CALLING_CLASS_COUNT_MISMATCH")
    if startup!=report["startup_class_network_callsite_count"]:
        raise AuditRefused("STARTUP_COUNT_MISMATCH")
    paths=report["nominal_startup_network_paths"]
    reachable=report["nominal_startup_reachable_network_calls_count"]
    truncated=report["nominal_startup_paths_truncated"]
    if (type(paths) is not list or len(paths) > 100 or type(truncated) is not bool
        or truncated != (reachable>100) or len(paths)!=min(reachable,100)
        or reachable>len(rows)):
        raise AuditRefused("BAD_NOMINAL_REACHABILITY_TOTALS")
    row_targets={(r["class"],r["method"],r["target_class"],r["target_method"]) for r in rows}
    for path in paths:
        if not isinstance(path,dict) or set(path)!={"class","method","target_class","target_method",
                "nominal_hops_from_launcher_main","path"}:
            raise AuditRefused("BAD_NOMINAL_PATH")
        if any(type(path[k]) is not str for k in ("class","method","target_class","target_method")):
            raise AuditRefused("BAD_NOMINAL_PATH_TYPES")
        if (path["class"],path["method"],path["target_class"],path["target_method"]) not in row_targets:
            raise AuditRefused("NOMINAL_PATH_NOT_A_NETWORK_CALLSITE")
        hops=path["nominal_hops_from_launcher_main"]
        chain=path["path"]
        if (type(hops) is not int or hops<0 or hops>12 or type(chain) is not list
            or len(chain)!=hops+1 or not chain[0].startswith("rs.gui.Launcher#main(")
            or not chain[-1].startswith(path["class"]+"#"+path["method"]+"(")
            or any(type(v) is not str or len(v)>500 or not re.fullmatch(r"[A-Za-z0-9_$.#;\[\]()/<>]+",v) for v in chain)):
            raise AuditRefused("INVALID_NOMINAL_PATH_CHAIN")
    return {"status":"R355_REPORT_SHAPE_CONSISTENT_UNATTESTED",
            "original_jar_verified_by_report_validator":False,
            "runtime_admitted":False,"network_callsite_count":len(rows),
            "original_binary_execution":"NOT_TESTED"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("report",type=Path)
    args=p.parse_args()
    try:
        print(json.dumps(verify_text(args.report.read_text(encoding="utf-8")),sort_keys=True))
    except (AuditRefused,OSError) as e:
        print(json.dumps({"status":"R355_REPORT_REJECTED","reason":str(e)}))
        raise SystemExit(2)
if __name__=="__main__":main()
