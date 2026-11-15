#!/usr/bin/env python3
"""R408 public-safe, read-only original/private async deletion prerequisite audit.

This explicitly does NOT implement background deletes. It compares an exact
SHA-pinned original corpus with the owner-private R407 baseline and confirms
the known synchronous UI/file-gate coupling, source-level barriers and
necessary changes before any future R409+ implementation.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

HELPER=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not HELPER.is_file():
    raise RuntimeError("Missing public R395 read-only archive helper")
spec=importlib.util.spec_from_file_location("r408_r395",HELPER)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused

P="rs/plugins/loottracker/"
PLUGIN=P+"LootTrackerPlugin.java"
PANEL=P+"LootTrackerPanel.java"
RECORD=P+"LootTrackerRecord.java"
ITEM=P+"LootTrackerItem.java"
STORE=P+"LootHistoryStore.java"
CHANGED_SOURCES={PLUGIN,PANEL,RECORD,ITEM,STORE}
CHANGED_CLASSES={
    P+"LootTrackerPlugin.class",P+"LootTrackerPanel.class",
    P+"LootTrackerRecord.class",P+"LootTrackerItem.class",
    P+"LootHistoryStore.class",P+"LootHistoryStore$ItemDto.class",
    P+"LootHistoryStore$RecordDto.class",
}

def require(block:str,needle:str,reason:str)->None:
    if needle not in block:raise Refused(reason)

def ordered(block:str,*tokens:str)->None:
    if not r395.ordered(block,*tokens):
        raise Refused("R408_PREREQUISITE_ORDER_DRIFT")

def monitor_body(source:str,monitor:str)->str:
    m=re.search(r"synchronized\s*\(\s*"+re.escape(monitor)+r"\s*\)\s*\{",source)
    if not m:raise Refused("R408_MISSING_MONITOR_"+monitor)
    return r393.braced_body(source,m.end()-1)

def inspect(plugin:bytes,panel:bytes,record:bytes,store:bytes)->dict:
    try:
        p=r393.mask_java(plugin.decode("utf8"))
        ui=r393.mask_java(panel.decode("utf8"))
        r=r393.mask_java(record.decode("utf8"))
        disk=r393.mask_java(store.decode("utf8"))
    except UnicodeDecodeError as e:
        raise Refused("R408_NON_UTF8_PRIVATE_SOURCE") from e

    edit=r394.method_body(p,"r402ApplyPanelDeletion")
    ordered(edit,
        "SwingUtilities.isEventDispatchThread()",
        "if (!config.rememberLoot())",
        "mutation.run()",
        "synchronized (r401FileGate)",
        "r402PanelEditMutating = true",
        "mutation.run()",
        "persistHistory()",
        "if (!r402EditWriteReceipt)",
        "r401ClearUnsafe = true",
        "r402EditTransactionOpen = false")
    gate=monitor_body(edit,"r401FileGate")
    ordered(gate,
        "r402PanelEditMutating = true",
        "mutation.run()",
        "r402PanelEditMutating = false",
        "persistHistory()",
        "if (!r402EditWriteReceipt)")
    if edit.count("persistHistory()")!=1:
        raise Refused("R408_EXISTING_DELETE_RECEIPT_NOT_SYNCHRONOUS")
    if "executor.execute(" in edit or "r408" in edit:
        raise Refused("R408_ASYNC_DELETE_ALREADY_IN_PRIVATE_BASELINE")

    for method,selector in (
        ("removeSource","r.matchesGroup(title, type)"),
        ("removeType","r.isType(type)"),
        ("removeRecord","r == record")):
        operation=r394.method_body(ui,method)
        ordered(operation,"confirm(", "plugin.r402ApplyPanelDeletion(",
                "records.removeIf(","rebuild()")
        require(operation,selector,"R408_SELECTOR_IDENTITY_DRIFT_"+method)
        if operation.count("plugin.r402ApplyPanelDeletion(")!=1:
            raise Refused("R408_PANEL_TRANSACTION_COUNT_DRIFT_"+method)
    frozen=r394.method_body(ui,"r405FrozenRecords")
    ordered(frozen,
        "new ArrayList<>(records.size())",
        "for (LootTrackerRecord record : records)",
        "frozen.add(record.r405FrozenCopy())")
    if not re.search(r"\bsynchronized\s+Collection<LootTrackerRecord>\s+r405FrozenRecords\s*\(",ui):
        raise Refused("R408_PANEL_FREEZE_MONITOR_CHANGED")
    get=r394.method_body(ui,"getRecords")
    require(get,"new ArrayList<>(records)",
            "R408_ORIGINAL_IDENTITY_REFERENCE_LOOKUP_MISSING")
    if "r408" in frozen or "r408" in get:
        raise Refused("R408_BACKGROUND_EDIT_SNAPSHOT_ALREADY_IMPLEMENTED")

    copy=r394.method_body(r,"r405FrozenCopy")
    ordered(copy,
        "LootTrackerItem[] references = items.clone()",
        "frozen[i] = references[i].r405FrozenCopy()",
        "new LootTrackerRecord(title, subTitle, type, frozen, kills, timestamp)")
    # The record-level deep copy is independent but does NOT retain a
    # mapping of original object identities for confirmed deletions.
    if "IdentityHashMap" in copy:
        raise Refused("R408_IDENTITY_SNAPSHOT_ALREADY_IMPLEMENTED")

    save=r394.method_body(p,"persistHistory")
    ordered(save,
        "panel.r405FrozenRecords()",
        "r405FrozenPending.add(pending.r405FrozenCopy())",
        "synchronized (r401FileGate)",
        "historyStore.saveWithReceipt(merged)")
    require(save,"r403WorkerEpoch.get()",
            "R408_STALE_AUTOSAVE_EPOCH_FENCE_MISSING")
    require(save,"r401SnapshotClearGeneration != r401ClearGeneration",
            "R408_DELETE_GENERATION_FENCE_MISSING")

    executor=r394.method_body(p,"r403QueueAutosave")
    ordered(executor,
        "r403AutosaveQueued = true",
        "issuedEpoch = r399SessionEpoch",
        "executor.execute(",
        "r403WorkerEpoch.set(issuedEpoch)",
        "persistHistory()",
        "r403WorkerEpoch.remove()")
    require(executor,"r403AutosaveDirty = true;",
            "R408_COALESCING_CONTRACT_CHANGED")
    if "r408" in executor:
        raise Refused("R408_EDIT_QUEUE_ALREADY_INTEGRATED")
    clear=r394.method_body(p,"clearHistory")
    ordered(clear,
        "SwingUtilities.isEventDispatchThread()",
        "++r399SessionEpoch",
        "r403AutosaveQueued = false",
        "r403AutosaveDirty = false",
        "synchronized (r401FileGate)",
        "historyStore.clearWithReceipt()",
        "panel.clearRecords()")
    stop=r394.method_body(p,"shutDown")
    ordered(stop,
        "++r399SessionEpoch",
        "r403RetiredWorker.shutdown()",
        "persistHistory()")
    require(stop,"instance = null;","R408_LIFECYCLE_INSTANCE_FENCE_MISSING")
    saveio=r394.method_body(disk,"saveWithReceipt")
    ordered(saveio,
        "RecordDto.from(record)",
        "Files.newOutputStream(temp.toPath())",
        "GSON.a(document, writer)",
        "AtomicFileReplace.move(temp, file)",
        "return true;")
    if "r408" in saveio:
        raise Refused("R408_NEW_COMMIT_PROTOCOL_ALREADY_PRESENT")

    return {
        "confirmed_deletion_still_runs_on_edt":True,
        "confirmed_deletion_still_holds_file_gate_during_ui_mutation":True,
        "confirmed_deletion_has_synchronous_disk_receipt":True,
        "three_existing_delete_selectors_are_confirmed":True,
        "identity_preserving_deleted_target_capture_is_not_integrated":True,
        "panel_frozen_copy_does_not_map_original_to_clone_identities":True,
        "background_autosave_already_has_epoch_fencing":True,
        "clear_and_shutdown_can_invalidate_inflight_edits":True,
        "disk_store_returns_receipt_after_atomic_replacement":True,
        "background_delete_commit_and_edt_ack_integrated":False,
        "durable_post_commit_pre_ack_restart_reconciliation_integrated":False,
        "actual_edt_latency_reduced_by_r408":False,
    }

def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          inspected_sources:Path,inspected_classes:Path,
          expected_sources:int=1277,expected_classes:int=1388)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    original=r395.read_zip_bytes(kit,"source/",".java")
    origcls=r395.read_zip_bytes(reference,"",".class")
    current=r395.read_tree_bytes(inspected_sources,".java")
    classes=r395.read_tree_bytes(inspected_classes,".class")
    if len(original)!=expected_sources or len(current)!=expected_sources:
        raise Refused("R408_PRIVATE_SOURCE_COUNT_DRIFT")
    if len(origcls)!=expected_classes or len(classes)!=expected_classes:
        raise Refused("R408_PRIVATE_CLASS_COUNT_DRIFT")
    if original.keys()!=current.keys() or origcls.keys()!=classes.keys():
        raise Refused("R408_BASELINE_SOURCE_OR_CLASS_SET_DRIFT")
    altered={name for name in current if current[name]!=original[name]}
    changedcls={name for name in classes if classes[name]!=origcls[name]}
    if altered!=CHANGED_SOURCES or changedcls!=CHANGED_CLASSES:
        raise Refused("R408_R407_REFERENCE_DELTA_SCOPE_DRIFT")
    evidence=inspect(current[PLUGIN],current[PANEL],current[RECORD],current[STORE])
    return {
        "status":"R408_PRIVATE_ASYNC_EDIT_PREREQUISITES_PASS",
        "source_count":len(current),
        "class_count":len(classes),
        "prior_private_changed_sources":len(altered),
        "prior_private_changed_classes":len(changedcls),
        **evidence,
        "private_source_modified_for_r408":False,
        "private_client_rebuilt_for_r408":False,
        "private_client_executed":False,
        "runtime_safety_proven":False,
        "cross_process_locking_proven":False,
        "power_loss_recovery_proven":False,
        "source_release_authorized":False,
        "merge_approved":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("kit","reference","inspected-sources","inspected-classes"):
        p.add_argument("--"+arg,required=True,type=Path)
    p.add_argument("--kit-sha256",required=True)
    p.add_argument("--reference-sha256",required=True)
    p.add_argument("--expected-sources",type=int,default=1277)
    p.add_argument("--expected-classes",type=int,default=1388)
    p.add_argument("--out",type=Path)
    x=p.parse_args(argv)
    try:
        if x.out and (x.out.is_symlink() or x.out.exists()):
            raise Refused("R408_REFUSE_EXISTING_RECEIPT")
        result=audit(
            kit=x.kit,kit_sha=x.kit_sha256,
            reference=x.reference,reference_sha=x.reference_sha256,
            inspected_sources=x.inspected_sources,inspected_classes=x.inspected_classes,
            expected_sources=x.expected_sources,expected_classes=x.expected_classes)
        encoded=json.dumps(result,sort_keys=True,indent=2)+"\n"
        if x.out:
            with x.out.open("x",encoding="utf8") as out:out.write(encoded)
        else:print(encoded,end="")
        return 0
    except (Refused,OSError,ValueError) as e:
        print(json.dumps({
            "status":"R408_REFUSED",
            "reason":str(e) if isinstance(e,Refused) else "INPUT_OR_FILESYSTEM_ERROR"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
