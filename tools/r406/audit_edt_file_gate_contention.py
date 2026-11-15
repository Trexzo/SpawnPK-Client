#!/usr/bin/env python3
"""R406 passive SHA-pinned source audit of EDT history-write contention.

This is a read-only diagnostic, NOT an implementation or release gate.
It never executes recovered classes, reads player history, modifies files,
prints private code, or claims asynchronous deletion works.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path

HELPER=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not HELPER.is_file():
    raise RuntimeError("R406 requires inherited public R395 archive reader")
spec=importlib.util.spec_from_file_location("r406_inherited_r395",HELPER)
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
CHANGED_SOURCE={PLUGIN,PANEL,ITEM,RECORD,STORE}
CHANGED_CLASS={
    P+"LootTrackerPlugin.class",
    P+"LootTrackerPanel.class",
    P+"LootTrackerItem.class",
    P+"LootTrackerRecord.class",
    P+"LootHistoryStore.class",
    P+"LootHistoryStore$ItemDto.class",
    P+"LootHistoryStore$RecordDto.class",
}

def require(body:str,token:str,reason:str):
    if token not in body:raise Refused(reason)

def ordered(body:str,*tokens:str):
    if not r395.ordered(body,*tokens):
        raise Refused("R406_LOCK_OR_ACK_ORDER_DRIFT")

def method_block(source:str,name:str)->str:
    try:return r394.method_body(source,name)
    except Exception as e:raise Refused("R406_REQUIRED_METHOD_NOT_FOUND") from e

def inside_lock(body:str,lock:str)->str:
    needle="synchronized ("+lock+")"
    if needle not in body:raise Refused("R406_REQUIRED_MONITOR_NOT_FOUND")
    start=body.find("{",body.index(needle)+len(needle))
    if start<0:raise Refused("R406_REQUIRED_MONITOR_BODY_NOT_FOUND")
    return r393.braced_body(body,start)

def analyze(plugin:bytes,panel:bytes,store:bytes)->dict:
    try:
        p=r393.mask_java(plugin.decode("utf8"))
        ui=r393.mask_java(panel.decode("utf8"))
        disk=r393.mask_java(store.decode("utf8"))
    except UnicodeDecodeError as e:
        raise Refused("R406_NON_UTF8_SOURCE") from e

    edit=method_block(p,"r402ApplyPanelDeletion")
    ordered(edit,
        "SwingUtilities.isEventDispatchThread()",
        "config.rememberLoot()",
        "synchronized (r401FileGate)",
        "mutation.run()",
        "persistHistory()",
        "if (!r402EditWriteReceipt)")
    lock=inside_lock(edit,"r401FileGate")
    ordered(lock,
        "synchronized (r395HistoryGate)",
        "mutation.run()",
        "persistHistory()",
        "if (!r402EditWriteReceipt)",
        "r402EditTransactionOpen = false")
    if "executor.execute(" in edit or "SwingUtilities.invokeLater(" in edit:
        raise Refused("R406_DELETE_CONTRACT_CHANGED_FROM_SYNC")
    if edit.count("persistHistory()")!=1:
        raise Refused("R406_EDIT_SYNCHRONOUS_RECEIPT_DRIFT")

    writer=method_block(p,"persistHistory")
    require(writer,"panel.r405FrozenRecords()",
            "R406_FROZEN_PANEL_SNAPSHOT_REGRESSION")
    filelock=inside_lock(writer,"r401FileGate")
    ordered(filelock,
        "synchronized (r395HistoryGate)",
        "historyStore.saveWithReceipt(merged)")
    if "SwingUtilities.invokeAndWait(" in writer:
        raise Refused("R406_NEW_CLIENT_EDT_HOP_REFUSED")

    autosave=method_block(p,"r403QueueAutosave")
    ordered(autosave,"executor.execute(", "persistHistory()")
    request=method_block(p,"requestSave")
    require(request,"r403QueueAutosave()",
            "R406_ROUTINE_SAVE_WORKER_MISSING")
    if "persistHistory()" in request:
        raise Refused("R406_REQUEST_SAVE_SYNCHRONOUS_REGRESSION")

    clear=method_block(p,"clearHistory")
    ordered(clear,
        "SwingUtilities.isEventDispatchThread()",
        "r401ClearInProgress = true",
        "synchronized (r401FileGate)",
        "historyStore.clearWithReceipt()",
        "panel.clearRecords()")
    clearlock=inside_lock(clear,"r401FileGate")
    require(clearlock,"historyStore.clearWithReceipt()",
            "R406_CLEAR_DISK_RECEIPT_OUTSIDE_LOCK")
    require(clear,"if (!deleted)",
            "R406_CLEAR_FAILURE_MUST_FAIL_CLOSED")

    for name,selector in (
        ("removeSource","r.matchesGroup(title, type)"),
        ("removeType","r.isType(type)"),
        ("removeRecord","r == record")):
        action=method_block(ui,name)
        ordered(action,"confirm(", "plugin.r402ApplyPanelDeletion(",
                "records.removeIf(", "rebuild()")
        require(action,selector,"R406_PANEL_SELECTOR_CHANGED_"+name)
        if "plugin.persistHistory()" in action:
            raise Refused("R406_DIRECT_UI_SAVE_REGRESSION_"+name)

    save=method_block(disk,"saveWithReceipt")
    ordered(save,
        "RecordDto.from(record)",
        "Files.newOutputStream(temp.toPath())",
        "GSON.a(document, writer)",
        "AtomicFileReplace.move(temp, file)",
        "return true;")
    if "Thread.sleep(" in save or "SwingUtilities.invokeLater(" in save:
        raise Refused("R406_STORAGE_BEHAVIOR_CHANGED")
    shutdown=method_block(p,"shutDown")
    require(shutdown,"persistHistory()","R406_SHUTDOWN_RECEIPT_CHANGED")
    logout=method_block(p,"onGameStateChanged")
    require(logout,"persistHistory()","R406_LOGOUT_RECEIPT_CHANGED")

    return {
        "source_confirmed_edt_delete_acquires_shared_file_monitor":True,
        "source_confirmed_edt_delete_calls_disk_commit_synchronously":True,
        "source_confirmed_edt_clear_acquires_shared_file_monitor":True,
        "background_autosave_competes_for_same_file_monitor":True,
        "source_confirmed_direct_logout_and_shutdown_saves":True,
        "three_confirmation_selectors_retain_receipts":True,
        "unsafe_naive_async_ack_not_integrated":True,
        "proposed_nonblocking_production_delete_implemented":False,
        "measured_real_edt_latency":False,
        "actual_client_executed":False,
        "real_disk_content_read":False,
        "source_structure_cannot_prove_exact_latency_or_absence_of_deadlock":True,
    }

def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          inspected_sources:Path,inspected_classes:Path,
          expected_sources:int=1277,expected_classes:int=1388)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    golden=r395.read_zip_bytes(kit,"source/",".java")
    goldcls=r395.read_zip_bytes(reference,"",".class")
    current=r395.read_tree_bytes(inspected_sources,".java")
    currcls=r395.read_tree_bytes(inspected_classes,".class")
    if len(golden)!=expected_sources or len(current)!=expected_sources:
        raise Refused("R406_SOURCE_FILE_COUNT_DRIFT")
    if len(goldcls)!=expected_classes or len(currcls)!=expected_classes:
        raise Refused("R406_CLASS_FILE_COUNT_DRIFT")
    if golden.keys()!=current.keys() or goldcls.keys()!=currcls.keys():
        raise Refused("R406_ORIGINAL_SOURCE_CLASS_SET_DRIFT")
    diff_src={x for x in current if current[x]!=golden[x]}
    diff_cls={x for x in currcls if currcls[x]!=goldcls[x]}
    if diff_src!=CHANGED_SOURCE or diff_cls!=CHANGED_CLASS:
        raise Refused("R406_R405_REFERENCE_DELTA_SCOPE_DRIFT")
    observations=analyze(current[PLUGIN],current[PANEL],current[STORE])
    return {
        "status":"R406_PASSIVE_EDT_CONTENTION_EVIDENCE_PASS",
        "inspected_source_count":len(current),
        "inspected_class_count":len(currcls),
        "existing_changes_vs_original_source_count":len(diff_src),
        "existing_changes_vs_original_class_count":len(diff_cls),
        **observations,
        "private_source_modified_by_r406":False,
        "private_client_rebuilt_by_r406":False,
        "production_file_modified":False,
        "private_source_release_authorized":False,
        "merge_approved":False,
    }

def main(argv=None)->int:
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ("kit","reference","inspected-sources","inspected-classes"):
        ap.add_argument("--"+name,type=Path,required=True)
    ap.add_argument("--kit-sha256",required=True)
    ap.add_argument("--reference-sha256",required=True)
    ap.add_argument("--expected-sources",type=int,default=1277)
    ap.add_argument("--expected-classes",type=int,default=1388)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args(argv)
    try:
        if a.out and (a.out.is_symlink() or a.out.exists()):
            raise Refused("R406_EXISTING_REPORT_REFUSED")
        result=audit(
            kit=a.kit,kit_sha=a.kit_sha256,
            reference=a.reference,reference_sha=a.reference_sha256,
            inspected_sources=a.inspected_sources,
            inspected_classes=a.inspected_classes,
            expected_sources=a.expected_sources,
            expected_classes=a.expected_classes)
        rendered=json.dumps(result,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as out:
                out.write(rendered)
        else:print(rendered,end="")
        return 0
    except (Refused,OSError,ValueError) as e:
        print(json.dumps({
            "status":"R406_REFUSED",
            "reason":str(e) if isinstance(e,Refused) else "INPUT_OR_FILESYSTEM_ERROR"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
