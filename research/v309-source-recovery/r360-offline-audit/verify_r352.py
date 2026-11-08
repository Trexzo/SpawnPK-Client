"""Strict allowlist parser for an R352 startup trace; this does NOT attest its provenance."""
from __future__ import annotations
import json
import re
from verify_receipt import evaluate as evaluate_r351, ReceiptRefused

PREFIX="R352_RECEIPT:"
PIN="ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
FIELDS={"status","original_jar_sha256","launcher_class_verified","original_main_invoked",
        "phase","failure_type","windows_showing","window_query_finished","window_queries",
        "stdout_redirected","endpoint_audit","login_verified","same_pid_reconnect"}
PHASES={"NOT_INVOKED","CLASS_LOADING","CLASS_VERIFIED","MAIN_INVOKED","MAIN_RETURNED","LAUNCH_EXCEPTION"}

def no_duplicates(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ReceiptRefused("R352_DUPLICATE_JSON_KEY")
        out[k]=v
    return out

def validate(data):
    if type(data) is not dict or set(data)!=FIELDS:
        raise ReceiptRefused("R352_FIELDS_MISMATCH")
    if data["status"]!="R352_ORIGINAL_STARTUP_DENY_TRACE_ONLY" or data["original_jar_sha256"]!=PIN:
        raise ReceiptRefused("R352_BAD_STATUS_OR_HASH")
    for name in ("launcher_class_verified","original_main_invoked","window_query_finished",
                 "stdout_redirected","login_verified"):
        if type(data[name]) is not bool: raise ReceiptRefused("R352_BAD_BOOLEAN")
    if data["login_verified"] or data["same_pid_reconnect"]!="NOT_TESTED":
        raise ReceiptRefused("R352_FALSE_ACCEPTANCE")
    if type(data["phase"]) is not str or data["phase"] not in PHASES:
        raise ReceiptRefused("R352_INVALID_PHASE")
    if not isinstance(data["failure_type"],str) or not re.fullmatch(r"[A-Za-z0-9_]{1,60}",data["failure_type"]):
        raise ReceiptRefused("R352_INVALID_FAILURE_TYPE")
    for name in ("windows_showing","window_queries"):
        if type(data[name]) is not int or not 0<=data[name]<=10000:
            raise ReceiptRefused("R352_INVALID_COUNTER")
    if data["original_main_invoked"] and not data["launcher_class_verified"]:
        raise ReceiptRefused("R352_MAIN_BEFORE_CLASS_VERIFIED")
    if data["phase"] in {"MAIN_INVOKED","MAIN_RETURNED"} and not data["original_main_invoked"]:
        raise ReceiptRefused("R352_INVALID_LAUNCH_PHASE")
    trace=evaluate_r351(data["endpoint_audit"])
    return {"status":"R352_RECEIPT_CONSISTENT_NOT_ATTESTED",
            "original_jar_sha256":PIN,
            "launcher_class_verified":data["launcher_class_verified"],
            "original_main_invoked":data["original_main_invoked"],
            "phase":data["phase"],
            "dns_checks":trace["dns_checks"],"socket_checks":trace["socket_checks"],
            "unknown_host_groups":trace["unknown_host_groups"],
            "login_verified":False,"same_pid_reconnect":"NOT_TESTED",
            "original_runtime_provenance_attested":False}

def parse_console(raw):
    if len(raw)>65536: raise ReceiptRefused("R352_CONSOLE_OVERSIZE")
    lines=[line[len(PREFIX):] for line in raw.splitlines() if line.startswith(PREFIX)]
    if len(lines)!=1: raise ReceiptRefused("R352_EXPECT_EXACTLY_ONE_RECEIPT")
    try: data=json.loads(lines[0],object_pairs_hook=no_duplicates)
    except ValueError as exc: raise ReceiptRefused("R352_BAD_JSON") from exc
    return validate(data)
