#!/usr/bin/env python3
"""R407 passive SHA-pinned owner-private clear/worker epoch source-class gate.

Public-safe auditor: never prints recovered code, launches the client,
reads loot history, modifies data, or approves a private build for release.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

HELPER=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not HELPER.is_file():
    raise RuntimeError("Missing public R395 read-only baseline helpers")
spec=importlib.util.spec_from_file_location("r407_inherit_r395",HELPER)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused

P="rs/plugins/loottracker/"
PLUGIN=P+"LootTrackerPlugin.java"
PANEL=P+"LootTrackerPanel.java"
ITEM=P+"LootTrackerItem.java"
RECORD=P+"LootTrackerRecord.java"
STORE=P+"LootHistoryStore.java"
GOLD_SRC={PLUGIN,PANEL,ITEM,RECORD,STORE}
GOLD_CLS={
    P+"LootTrackerPlugin.class",P+"LootTrackerPanel.class",
    P+"LootTrackerItem.class",P+"LootTrackerRecord.class",
    P+"LootHistoryStore.class",P+"LootHistoryStore$RecordDto.class",
    P+"LootHistoryStore$ItemDto.class",
}
PLUGIN_CLS=P+"LootTrackerPlugin.class"


def require(body:str,needle:str,reason:str):
    if needle not in body:raise Refused(reason)


def ordered(body:str,*tokens:str):
    if not r395.ordered(body,*tokens):
        raise Refused("R407_CRITICAL_EPOCH_OR_RECEIPT_ORDER_DRIFT")


def lock_body(body:str,tag:str,nth:int=0)->str:
    pattern=r"synchronized\s*\(\s*"+re.escape(tag)+r"\s*\)\s*\{"
    matches=list(re.finditer(pattern,body))
    if len(matches)<=nth:
        raise Refused("R407_MISSING_REQUIRED_MONITOR_"+tag)
    return r393.braced_body(body,matches[nth].end()-1)


def source_structure(raw:bytes)->dict:
    try:
        code=r393.mask_java(raw.decode("utf8"))
    except UnicodeDecodeError as e:
        raise Refused("R407_NON_UTF8_PLUGIN_SOURCE") from e
    worker=r394.method_body(code,"r403QueueAutosave")
    clear=r394.method_body(code,"clearHistory")
    save=r394.method_body(code,"persistHistory")
    stop=r394.method_body(code,"shutDown")
    explicit_delete=r394.method_body(code,"r402ApplyPanelDeletion")
    request=r394.method_body(code,"requestSave")
    tick=r394.method_body(code,"onGameTick")

    # R407: the same history monitor which advances the session must
    # reset both admission flags. The old worker is not permitted to
    # clear flags in the next epoch.
    admission=lock_body(clear,"r395HistoryGate",0)
    ordered(admission,
        "r401ClearInProgress = true",
        "++r399SessionEpoch",
        "r403AutosaveQueued = false",
        "r403AutosaveDirty = false")
    if admission.count("++r399SessionEpoch")!=1:
        raise Refused("R407_CLEAR_EPOCH_BUMP_COUNT_CHANGED")
    if admission.count("r403AutosaveQueued = false")!=1 or \
       admission.count("r403AutosaveDirty = false")!=1:
        raise Refused("R407_CLEAR_RESET_MUST_BE_EXACTLY_ONCE")
    ordered(clear,
        "SwingUtilities.isEventDispatchThread()",
        "synchronized (r395HistoryGate)",
        "++r399SessionEpoch",
        "r403AutosaveQueued = false",
        "r403AutosaveDirty = false",
        "synchronized (r401FileGate)",
        "historyStore.clearWithReceipt()",
        "if (!deleted)",
        "r401ClearUnsafe = true",
        "return;",
        "r396PreloadRecords.clear()",
        "pendingRecords.clear()",
        "savePending = false",
        "panel.clearRecords()",
        "r401ClearUnsafe = false",
        "r401ClearInProgress = false")
    if "r403AutosaveExecutor.shutdownNow(" in clear:
        raise Refused("R407_CLEAR_MUST_NOT_INTERRUPT_RUNNING_WRITE")
    # A failed clear is quarantined: it must not automatically replay
    # potentially unsynchronized records after disk deletion failed.
    require(clear,"r401ClearUnsafe = true","R407_FAILED_CLEAR_NOT_QUARANTINED")
    if "r403QueueAutosave()" in clear:
        raise Refused("R407_CLEAR_MUST_NOT_FORCE_UNVERIFIED_REWRITE")

    # A worker that checked an old epoch must not then reset the shared
    # success bit AFTER a clear. The admission test and bit reset share
    # one history-monitor interval, not two separate synchronized blocks.
    submit=worker.find("executor.execute(")
    if submit<0:raise Refused("R407_ASYNC_WORKER_NOT_ADMITTED")
    task=worker[submit:]
    locks=[
        r393.braced_body(task,m.end()-1)
        for m in re.finditer(
            r"synchronized\s*\(\s*r395HistoryGate\s*\)\s*\{",task)
    ]
    good=[
        block for block in locks
        if "issuedEpoch != r399SessionEpoch" in block and
           "r396LastCommitSucceeded = false" in block
    ]
    if len(good)!=1:
        raise Refused("R407_WORKER_ADMISSION_AND_RESET_NOT_ATOMIC")
    ordered(good[0],
        "!r399AcceptingDrops",
        "instance != this",
        "issuedEpoch != r399SessionEpoch",
        "return;",
        "r396LastCommitSucceeded = false")
    if worker.count("r396LastCommitSucceeded = false;")!=1:
        raise Refused("R407_UNEXPECTED_WORKER_RECEIPT_RESET")

    # An exception from an obsolete worker must not dirty a successful
    # Clear all or a newer plugin session.
    catch_match=re.search(
        r"catch\s*\(\s*RuntimeException\s+\w+\s*\)\s*\{",worker)
    if not catch_match:raise Refused("R407_WORKER_EXCEPTION_CATCH_MISSING")
    caught=r393.braced_body(worker,catch_match.end()-1)
    error_guard=lock_body(caught,"r395HistoryGate",0)
    ordered(error_guard,
        "issuedEpoch == r399SessionEpoch",
        "r399AcceptingDrops",
        "instance == this",
        "!r401ClearInProgress",
        "!r401ClearUnsafe",
        "savePending = true")
    if caught.count("savePending = true;")!=1:
        raise Refused("R407_WORKER_EXCEPTION_RETRY_COUNT_DRIFT")
    if caught.find("savePending = true")<caught.find("synchronized (r395HistoryGate)"):
        raise Refused("R407_UNGUARDED_STALE_WORKER_RETRY")
    if "r403AutosaveQueued = false" in caught:
        raise Refused("R407_EXCEPTION_CANNOT_RESET_QUEUE_FROM_OLD_SESSION")

    # Retain R403's protection for delayed success/failure and final
    # queue cleanup; these are needed after the Clear resets flags.
    ordered(worker,
        "r403AutosaveQueued = true",
        "issuedEpoch = r399SessionEpoch",
        "executor.execute(",
        "r403WorkerEpoch.set(issuedEpoch)",
        "persistHistory()",
        "r403WorkerEpoch.remove()",
        "if (issuedEpoch == r399SessionEpoch)",
        "r403AutosaveQueued = false",
        "catch (java.util.concurrent.RejectedExecutionException")
    require(worker,"r403AutosaveDirty = true;","R407_COALESCING_REMOVED")
    if worker.count("r403WorkerEpoch.remove()")!=1:
        raise Refused("R407_WORKER_EPOCH_TOKEN_LEAK")
    if worker.count("if (issuedEpoch == r399SessionEpoch)")<3:
        raise Refused("R407_SUCCESS_CLEANUP_OR_REJECTION_FENCE_REMOVED")
    if "shutdownNow(" in worker or "shutdownNow(" in stop:
        raise Refused("R407_INTERRUPT_WHILE_WRITING_NOT_AUTHORIZED")
    require(stop,"r403RetiredWorker.shutdown()","R407_STOP_RETIREMENT_CHANGED")
    require(stop,"persistHistory()","R407_FINAL_SHUTDOWN_RECEIPT_CHANGED")
    require(request,"r403QueueAutosave()","R407_AUTOSAVE_NO_LONGER_ASYNC")
    if "persistHistory()" in request or "persistHistory()" in tick:
        raise Refused("R407_ROUTINE_SAVE_CLIENT_THREAD_REGRESSION")
    require(tick,"r403QueueAutosave()","R407_TICK_SAVE_QUEUE_MISSING")
    if save.count("r403WorkerEpoch.get()")!=2:
        raise Refused("R407_WORKER_EPOCH_WRITE_AND_ACK_FENCES_MISSING")
    require(save,"synchronized (r401FileGate)","R407_FILE_GATE_REMOVED")
    require(save,"historyStore.saveWithReceipt(merged)","R407_DURABLE_RECEIPT_REMOVED")
    ordered(explicit_delete,
        "synchronized (r401FileGate)",
        "mutation.run()",
        "persistHistory()",
        "if (!r402EditWriteReceipt)")
    return {
        "clear_epoch_bump_resets_queue_and_dirty_under_history_gate":True,
        "old_worker_receipt_reset_requires_same_epoch_guard":True,
        "obsolete_worker_exception_cannot_rearm_pending_save":True,
        "old_worker_final_cleanup_still_epoch_guarded":True,
        "failed_clear_keeps_history_unsafe":True,
        "new_session_can_admit_autosave_after_successful_clear":True,
        "no_interrupt_or_async_delete_contract_change":True,
        "static_structure_not_runtime_schedule_proof":True,
    }


def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,expected_classes:int=1388)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    gold=r395.read_zip_bytes(kit,"source/",".java")
    gold_cls=r395.read_zip_bytes(reference,"",".class")
    old=r395.read_tree_bytes(previous_sources,".java")
    new=r395.read_tree_bytes(candidate_sources,".java")
    oldcls=r395.read_tree_bytes(previous_classes,".class")
    newcls=r395.read_tree_bytes(candidate_classes,".class")
    if any(len(t)!=expected_sources for t in (gold,old,new)):
        raise Refused("R407_SOURCE_COUNT_DRIFT")
    if any(len(t)!=expected_classes for t in (gold_cls,oldcls,newcls)):
        raise Refused("R407_CLASS_COUNT_DRIFT")
    if not(gold.keys()==old.keys()==new.keys()):
        raise Refused("R407_SOURCE_SET_DRIFT")
    if not(gold_cls.keys()==oldcls.keys()==newcls.keys()):
        raise Refused("R407_CLASS_SET_DRIFT")
    changed_src={k for k in new if new[k]!=old[k]}
    changed_cls={k for k in newcls if newcls[k]!=oldcls[k]}
    goldsrc={k for k in new if new[k]!=gold[k]}
    goldclass={k for k in newcls if newcls[k]!=gold_cls[k]}
    if changed_src!={PLUGIN} or changed_cls!={PLUGIN_CLS}:
        raise Refused("R407_EXACT_ONE_SOURCE_AND_CLASS_REQUIRED")
    if goldsrc!=GOLD_SRC or goldclass!=GOLD_CLS:
        raise Refused("R407_PINNED_GOLDEN_SCOPE_DRIFT")
    result=source_structure(new[PLUGIN])
    return {
        "status":"R407_PRIVATE_CLEAR_AUTOSAVE_EPOCH_GATE_PASS",
        "source_count":len(new),"compiled_class_count":len(newcls),
        "changed_source_count_vs_r405":1,
        "changed_class_count_vs_r405":1,
        **result,
        "private_client_runtime_executed":False,
        "real_swing_schedule_verified":False,
        "cross_process_file_lock_proven":False,
        "failed_clear_recovery_without_destructive_retry_proven":False,
        "power_loss_durability_proven":False,
        "private_source_release_authorized":False,
        "merge_approved":False,
    }


def main(argv=None)->int:
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ("kit","reference","previous-sources","previous-classes",
                 "candidate-sources","candidate-classes"):
        ap.add_argument("--"+name,type=Path,required=True)
    ap.add_argument("--kit-sha256",required=True)
    ap.add_argument("--reference-sha256",required=True)
    ap.add_argument("--expected-sources",type=int,default=1277)
    ap.add_argument("--expected-classes",type=int,default=1388)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args(argv)
    try:
        if a.out and (a.out.exists() or a.out.is_symlink()):
            raise Refused("R407_REFUSE_EXISTING_RECEIPT")
        result=audit(
            kit=a.kit,kit_sha=a.kit_sha256,
            reference=a.reference,reference_sha=a.reference_sha256,
            previous_sources=a.previous_sources,previous_classes=a.previous_classes,
            candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
            expected_sources=a.expected_sources,expected_classes=a.expected_classes)
        encoded=json.dumps(result,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as f:f.write(encoded)
        else:print(encoded,end="")
        return 0
    except (Refused,ValueError,OSError) as e:
        print(json.dumps({
            "status":"R407_REFUSED",
            "reason":str(e) if isinstance(e,Refused) else "INPUT_OR_FILESYSTEM_ERROR"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
