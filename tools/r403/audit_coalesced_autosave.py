#!/usr/bin/env python3
"""R403 SHA-pinned, read-only verifier for owner-private routine autosave worker.

Never executes any game client, modifies source/history files, or releases
private Java. Proves exact class/source scope and selected source contracts;
not runtime scheduling, crash durability or EDT-free guarantees for all paths.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re

PRIOR=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not PRIOR.is_file():
    raise RuntimeError("Missing inherited public read-only archive validator")
spec=importlib.util.spec_from_file_location("r403_r395",PRIOR)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused
PLUGIN="rs/plugins/loottracker/LootTrackerPlugin.java"
PANEL="rs/plugins/loottracker/LootTrackerPanel.java"
STORE="rs/plugins/loottracker/LootHistoryStore.java"
CLASS=PLUGIN[:-5]+".class"


def require(text:str,needle:str,reason:str):
    if needle not in text: raise Refused(reason)

def ordered(text:str,*tokens:str):
    if not r395.ordered(text,*tokens):
        raise Refused("R403_AUTOSAVE_LIFECYCLE_ORDER_DRIFT")

def check_structure(raw:bytes)->dict:
    try:
        source=r393.mask_java(raw.decode("utf8"))
    except UnicodeDecodeError as exc:
        raise Refused("NON_UTF8_PRIVATE_SOURCE") from exc
    fields=(
        (r"\b(?:volatile\s+)?java\.util\.concurrent\.ExecutorService\s+r403AutosaveExecutor\s*;", "executor"),
        (r"\bboolean\s+r403AutosaveQueued\s*;", "queued"),
        (r"\bboolean\s+r403AutosaveDirty\s*;", "dirty"),
        (r"\b(?:final\s+)?ThreadLocal<Long>\s+r403WorkerEpoch\s*;", "epoch"))
    for pattern,label in fields:
        if not re.search(pattern,source):
            raise Refused("R403_WORKER_FIELD_MISSING")
    if not re.search(r"\bvolatile\s+boolean\s+savePending\s*;",source):
        raise Refused("R403_SAVE_PENDING_NOT_VOLATILE")
    if not re.search(r"\bvolatile\s+long\s+lastPersistAt\s*;",source):
        raise Refused("R403_LAST_SAVE_NOT_VOLATILE")

    start=r394.method_body(source,"startUp")
    stop=r394.method_body(source,"shutDown")
    schedule=r394.method_body(source,"r403QueueAutosave")
    request=r394.method_body(source,"requestSave")
    tick=r394.method_body(source,"onGameTick")
    save=r394.method_body(source,"persistHistory")
    edit=r394.method_body(source,"r402ApplyPanelDeletion")
    logout=r394.method_body(source,"onGameStateChanged")

    ordered(start,
        "++r399SessionEpoch","r399AcceptingDrops = true",
        "r403AutosaveQueued = false",
        "r403AutosaveDirty = false",
        "r403AutosaveExecutor = java.util.concurrent.Executors.newSingleThreadExecutor(")
    require(start,"worker.setDaemon(true)","R403_WORKER_NOT_DAEMON")
    ordered(stop,
        "++r399SessionEpoch","r399AcceptingDrops = false",
        "r403RetiredWorker.shutdown()","r396FinishStopMerge(",
        "persistHistory()")
    if "shutdownNow(" in stop or "awaitTermination(" in stop:
        raise Refused("R403_SHUTDOWN_BLOCKS_OR_INTERRUPTS_WRITER")

    ordered(request,
        "config.rememberLoot()",
        "lastPersistAt < AUTOSAVE_INTERVAL_MS",
        "savePending = true",
        "r403QueueAutosave()")
    if "persistHistory()" in request:
        raise Refused("R403_ROUTINE_REQUEST_STILL_SYNCHRONOUS")

    ordered(tick,
        "if (savePending &&",
        "r403QueueAutosave()",
        "scanForLootKeyInterface(")
    if "persistHistory()" in tick:
        raise Refused("R403_ROUTINE_TICK_STILL_SYNCHRONOUS")

    ordered(schedule,
        "synchronized (r395HistoryGate)",
        "r403AutosaveExecutor",
        "r403AutosaveQueued",
        "r403AutosaveDirty = true",
        "r403AutosaveQueued = true",
        "issuedEpoch = r399SessionEpoch",
        "executor.execute(",
        "issuedEpoch != r399SessionEpoch",
        "r396LastCommitSucceeded = false",
        "r403WorkerEpoch.set(issuedEpoch)",
        "persistHistory()",
        "!r396LastCommitSucceeded",
        "savePending = true",
        "finally",
        "r403WorkerEpoch.remove()",
        "if (issuedEpoch == r399SessionEpoch)",
        "r403AutosaveQueued = false")
    for token,why in (
        ("r403AutosaveDirty = true;","NO_COALESCING_ON_BUSY_WORKER"),
        ("r403WorkerEpoch.remove();","THREAD_LOCAL_EPOCH_LEAK"),
        ("r403AutosaveQueued = false;","QUEUE_NOT_RELEASED"),
        ("java.util.concurrent.RejectedExecutionException","REJECTION_NOT_HANDLED"),
        ("savePending = true;","FAILED_SAVE_NOT_RETRYABLE"),
        ("r403AutosaveExecutor","MISSING_EXECUTOR"),
        ("instance != this","NO_INSTANCE_FENCE"),
        ("!r399AcceptingDrops","NO_CLOSED_SESSION_FENCE"),
        ("!historyLoaded","UNRESTORED_AUTOSAVE_POSSIBLE")):
        require(schedule,token,why)
    if schedule.count("executor.execute(")!=1:
        raise Refused("MULTIPLE_UNBOUNDED_WORKER_ADMISSIONS")
    if "shutdownNow(" in schedule:
        raise Refused("WORKER_CANCEL_INTERRUPT_RISK")

    # Both disk commit and ack must reject the former session's token,
    # *inside the same per-instance FileGate used by edits and clear*.
    if save.count("r403WorkerEpoch.get()")!=2:
        raise Refused("WORKER_EPOCH_MUST_GUARD_WRITE_AND_ACK")
    if save.count("r403ExpectedEpoch.longValue() != r399SessionEpoch")!=2:
        raise Refused("STALE_BACKGROUND_SESSION_CAN_WRITE")
    if save.count("historyStore.saveWithReceipt(merged)")!=1:
        raise Refused("SAVE_RECEIPT_GUARD_DRIFT")
    lock=save.find("synchronized (r401FileGate)")
    if lock<0:raise Refused("MISSING_FILE_GATE")
    inside=r393.braced_body(save,save.find("{",lock))
    ordered(inside,
        "r403WorkerEpoch.get()",
        "r399SessionEpoch",
        "historyStore.saveWithReceipt(merged)")
    if "r403WorkerEpoch.get()" not in save[save.find("if (r401Committed)"):]:
        raise Refused("POST_WRITE_ACK_STALE_SESSION_NOT_CHECKED")

    # The R402 transactional delete must remain synchronous and receipt
    # acknowledged, while logout/shutdown are not silently made async.
    ordered(edit,
        "synchronized (r401FileGate)",
        "mutation.run()",
        "persistHistory()",
        "r402EditWriteReceipt")
    ordered(logout,
        "case LOGIN_SCREEN:",
        "persistHistory()",
        "case LOGGED_IN:")
    return {
        "routine_request_and_tick_offloaded":True,
        "coalesced_one_worker_per_session":True,
        "daemon_worker_no_interrupting_shutdown":True,
        "two_stage_epoch_fence_under_file_gate":True,
        "failed_or_incomplete_receipt_rescheduled":True,
        "thread_local_token_removed":True,
        "prior_delete_and_logout_sync_receipt_contract_retained":True,
        "source_structure_not_runtime_schedule_proof":True,
    }


def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,expected_classes:int=1388)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    golden=r395.read_zip_bytes(kit,"source/",".java")
    goldcls=r395.read_zip_bytes(reference,"",".class")
    prior=r395.read_tree_bytes(previous_sources,".java")
    candidate=r395.read_tree_bytes(candidate_sources,".java")
    prior_cls=r395.read_tree_bytes(previous_classes,".class")
    new_cls=r395.read_tree_bytes(candidate_classes,".class")
    if any(len(s)!=expected_sources for s in (golden,prior,candidate)):
        raise Refused("SOURCE_COUNT_DRIFT")
    if any(len(s)!=expected_classes for s in (goldcls,prior_cls,new_cls)):
        raise Refused("CLASS_COUNT_DRIFT")
    if not(golden.keys()==prior.keys()==candidate.keys()):
        raise Refused("SOURCE_SET_DRIFT")
    if not(goldcls.keys()==prior_cls.keys()==new_cls.keys()):
        raise Refused("CLASS_SET_DRIFT")
    changes={x for x in candidate if candidate[x]!=prior[x]}
    classchanges={x for x in new_cls if new_cls[x]!=prior_cls[x]}
    goldchanges={x for x in candidate if candidate[x]!=golden[x]}
    goldclasschanges={x for x in new_cls if new_cls[x]!=goldcls[x]}
    if changes!={PLUGIN} or classchanges!={CLASS}:
        raise Refused("ONE_PLUGIN_SOURCE_CLASS_DELTA_REQUIRED")
    expected_gold={PLUGIN,PANEL,STORE}
    if goldchanges!=expected_gold or goldclasschanges!={x[:-5]+".class" for x in expected_gold}:
        raise Refused("THREE_GOLDEN_LOOT_FILES_ONLY")
    structure=check_structure(candidate[PLUGIN])
    return {
        "status":"R403_PRIVATE_COALESCED_AUTOSAVE_STATIC_GATE_PASS",
        "java_source_count":len(candidate),"compiled_class_count":len(new_cls),
        "changed_source_count_vs_r402":1,
        "changed_class_count_vs_r402":1,
        **structure,
        "actual_client_thread_latency_measured":False,
        "all_save_callers_background_only":False,
        "real_game_runtime_executed":False,
        "crash_recovery_durability_proven":False,
        "all_mutable_record_updates_versioned":False,
        "cross_process_writes_serialized":False,
        "normal_host_launch_authorized":False,
        "private_source_release_authorized":False,
        "merge_approved":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for opt in ("kit","reference","previous-sources","previous-classes",
                "candidate-sources","candidate-classes"):
        p.add_argument("--"+opt,type=Path,required=True)
    p.add_argument("--kit-sha256",required=True)
    p.add_argument("--reference-sha256",required=True)
    p.add_argument("--expected-sources",type=int,default=1277)
    p.add_argument("--expected-classes",type=int,default=1388)
    p.add_argument("--out",type=Path)
    a=p.parse_args(argv)
    try:
        if a.out and (a.out.exists() or a.out.is_symlink()):
            raise Refused("REFUSE_EXISTING_REPORT")
        report=audit(
            kit=a.kit,kit_sha=a.kit_sha256,
            reference=a.reference,reference_sha=a.reference_sha256,
            previous_sources=a.previous_sources,previous_classes=a.previous_classes,
            candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
            expected_sources=a.expected_sources,expected_classes=a.expected_classes)
        rendered=json.dumps(report,indent=2,sort_keys=True)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as out:
                out.write(rendered)
        else:
            print(rendered,end="")
        return 0
    except (Refused,OSError,ValueError) as exc:
        print(json.dumps({"status":"R403_REFUSED",
                          "reason":str(exc) if isinstance(exc,Refused) else "INPUT_OR_FILESYSTEM_ERROR"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
