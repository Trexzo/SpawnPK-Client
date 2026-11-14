#!/usr/bin/env python3
"""R401 public-safe SHA-pinned owner-local source/class clear-vs-save gate.

Read-only; verifies disposable private candidate and pinned historical corpus.
Never writes Java sources, executes client code, reads actual loot histories,
or authorizes any release, deployment or production cleanup.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

PRIOR=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not PRIOR.is_file():
    raise RuntimeError("Missing inherited R395 read-only archive validator")
spec=importlib.util.spec_from_file_location("r401_inherit_r395",PRIOR)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused

PLUGIN="rs/plugins/loottracker/LootTrackerPlugin.java"
STORE="rs/plugins/loottracker/LootHistoryStore.java"
CLASSES={p[:-5]+".class" for p in (PLUGIN,STORE)}


def require(body:str,term:str,reason:str):
    if term not in body:
        raise Refused(reason)


def ordered(body:str,*terms:str):
    if not r395.ordered(body,*terms):
        raise Refused("CLEAR_SAVE_CRITICAL_ORDER_DRIFT")


def check_structure(plugin:bytes,store:bytes)->dict:
    try:
        p=r393.mask_java(plugin.decode("utf8"))
        s=r393.mask_java(store.decode("utf8"))
    except UnicodeDecodeError as e:
        raise Refused("NON_UTF8_PRIVATE_SOURCE") from e

    for field in ("r401FileGate","r401ClearGeneration","r401ClearInProgress","r401ClearUnsafe"):
        if not re.search(r"\b(?:Object|long|boolean)\s+"+field+r"\b",p):
            raise Refused("CLEAR_SAVE_FIELD_MISSING")
    save=r394.method_body(p,"persistHistory")
    merge=r394.method_body(p,"r396FinishStopMerge")
    clear=r394.method_body(p,"clearHistory")
    store_clear=r394.method_body(s,"clearWithReceipt")
    old_clear=r394.method_body(s,"clear")

    ordered(save,
        "r401ClearInProgress || r401ClearUnsafe",
        "r401ConsistentClearGeneration = r401ClearGeneration",
        "r401ConsistentClearGeneration != r401ClearGeneration",
        "merged = r400ConsistentMerged",
        "r401SnapshotClearGeneration = r401ConsistentClearGeneration",
        "synchronized (r401FileGate)",
        "r401SnapshotClearGeneration != r401ClearGeneration",
        "historyStore.saveWithReceipt(merged)",
        "r401Committed",
        "r401SnapshotClearGeneration != r401ClearGeneration",
        "r399RecordMutationSequence == r399MutationAtSnapshot")
    if save.count("historyStore.saveWithReceipt(merged)")!=1:
        raise Refused("SAVE_WRITE_COUNT_DRIFT")
    # Confirm generation recheck sits inside file monitor before save.
    sf=save.find("synchronized (r401FileGate)")
    if sf<0:raise Refused("SAVE_FILE_LOCK_MISSING")
    filebody=r393.braced_body(save,save.find("{",sf))
    ordered(filebody,"synchronized (r395HistoryGate)",
            "r401SnapshotClearGeneration != r401ClearGeneration",
            "historyStore.saveWithReceipt(merged)")
    if filebody.count("historyStore.saveWithReceipt(merged)")!=1:
        raise Refused("SAVE_NOT_CONTAINED_IN_FILE_GATE")
    if "panel.getRecordsOffEdt(" in filebody:
        raise Refused("PANEL_SNAPSHOT_INSIDE_FILE_GATE")
    # Detect history -> file nested acquisition, which could invert the
    # intended FileGate -> HistoryGate order and create an EDT deadlock.
    for mm in re.finditer(r"synchronized\s*\(\s*r395HistoryGate\s*\)\s*\{",save):
        nested=r393.braced_body(save,save.find("{",mm.start()))
        if "synchronized (r401FileGate)" in nested:
            raise Refused("INVERTED_FILE_GATE_LOCK_ORDER")

    ordered(merge,
        "r401MergeClearGeneration = r401ClearGeneration",
        "historyStore.loadForMerge()",
        "synchronized (r401FileGate)",
        "r401MergeClearGeneration != r401ClearGeneration",
        "historyStore.saveWithReceipt(combined)",
        "if (!committed)",
        "r401MergeClearGeneration != r401ClearGeneration")
    mf=merge.find("synchronized (r401FileGate)")
    if mf<0:raise Refused("MERGE_FILE_GATE_MISSING")
    mergegate=r393.braced_body(merge,merge.find("{",mf))
    if ("historyStore.saveWithReceipt(combined)" not in mergegate or
            "r401MergeClearGeneration != r401ClearGeneration" not in mergegate):
        raise Refused("MERGE_SAVE_NOT_GUARDED_BY_CLEAR_EPOCH")

    ordered(clear,
        "SwingUtilities.isEventDispatchThread()",
        "SwingUtilities.invokeLater(this::clearHistory)",
        "++r401ClearGeneration",
        "r401ClearInProgress = true",
        "++r399SessionEpoch",
        "synchronized (r401FileGate)",
        "historyStore.clearWithReceipt()",
        "if (!deleted)",
        "r401ClearUnsafe = true",
        "r396PreloadRecords.clear()",
        "pendingRecords.clear()",
        "panel.clearRecords()",
        "r401ClearInProgress = false")
    # Original deferred panel clear is unsafe: it might erase fresh
    # post-clear records when a newer EDT callback has already run.
    if "SwingUtilities.invokeLater(panel::clearRecords)" in clear:
        raise Refused("ASYNC_PANEL_CLEAR_NOT_SCOPED")
    if clear.count("panel.clearRecords()")!=1:
        raise Refused("PANEL_CLEAR_COUNT_NOT_EXACTLY_ONE")
    cf=clear.find("synchronized (r401FileGate)")
    if cf<0:raise Refused("CLEAR_FILE_GATE_MISSING")
    cgate=r393.braced_body(clear,clear.find("{",cf))
    if "historyStore.clearWithReceipt()" not in cgate:
        raise Refused("CLEAR_DELETE_OUTSIDE_FILE_GATE")
    if "synchronized (r395HistoryGate)" in cgate:
        raise Refused("CLEAR_FILE_GATE_NESTED_HISTORY_LOCK")
    if clear.find("panel.clearRecords()")<clear.find("if (!deleted)"):
        raise Refused("UI_CLEARED_BEFORE_DISK_RECEIPT")
    if "clearWithReceipt();" not in old_clear:
        raise Refused("LEGACY_STORE_CLEAR_NOT_DELEGATING")
    ordered(store_clear,
        "Files.deleteIfExists(file.toPath())",
        "return true;",
        "catch (IOException | SecurityException e)",
        "return false;")
    if "return true;" not in store_clear:
        raise Refused("MISSING_FILE_MUST_COUNT_AS_DELETED")
    return {
        "save_and_clear_share_file_gate":True,
        "save_snapshot_uses_clear_epoch":True,
        "early_stop_merge_rechecks_clear_epoch":True,
        "clear_is_scoped_to_swing_edt":True,
        "file_delete_acknowledged":True,
        "failed_clear_does_not_discard_panel":True,
        "clear_updates_panel_synchronously_on_edt":True,
        "no_history_to_file_gate_inversion_detected":True,
        "syntactic_guard_not_complete_thread_proof":True,
    }


def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,expected_classes:int=1388)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    orig=r395.read_zip_bytes(kit,"source/",".java")
    refcls=r395.read_zip_bytes(reference,"",".class")
    prevsrc=r395.read_tree_bytes(previous_sources,".java")
    newsrc=r395.read_tree_bytes(candidate_sources,".java")
    prevcls=r395.read_tree_bytes(previous_classes,".class")
    newcls=r395.read_tree_bytes(candidate_classes,".class")
    if any(len(tree)!=expected_sources for tree in (orig,prevsrc,newsrc)):
        raise Refused("SOURCE_COUNT_DRIFT")
    if any(len(tree)!=expected_classes for tree in (refcls,prevcls,newcls)):
        raise Refused("CLASS_COUNT_DRIFT")
    if orig.keys()!=prevsrc.keys() or orig.keys()!=newsrc.keys():
        raise Refused("SOURCE_SET_DRIFT")
    if refcls.keys()!=prevcls.keys() or refcls.keys()!=newcls.keys():
        raise Refused("CLASS_SET_DRIFT")
    expected={PLUGIN,STORE}
    changed={path for path in newsrc if newsrc[path]!=prevsrc[path]}
    changed_cls={path for path in newcls if newcls[path]!=prevcls[path]}
    original_changed={path for path in newsrc if newsrc[path]!=orig[path]}
    original_changed_cls={path for path in newcls if newcls[path]!=refcls[path]}
    if changed!=expected or original_changed!=expected:
        raise Refused("EXACT_TWO_SOURCE_SCOPE_DRIFT")
    if changed_cls!=CLASSES or original_changed_cls!=CLASSES:
        raise Refused("EXACT_TWO_CLASS_SCOPE_DRIFT")
    checks=check_structure(newsrc[PLUGIN],newsrc[STORE])
    return {
        "status":"R401_PRIVATE_CLEAR_SAVE_STATIC_GATE_PASS",
        "java_source_count":len(newsrc),
        "compiled_class_count":len(newcls),
        "changed_source_count_vs_r400":2,
        "changed_class_count_vs_r400":2,
        **checks,
        "actual_original_client_executed":False,
        "actual_disk_clear_race_tested":False,
        "all_panel_mutators_versioned":False,
        "safe_cross_process_writes_proven":False,
        "crash_consistency_proven":False,
        "private_source_release_authorized":False,
        "normal_host_launch_authorized":False,
        "merge_approved":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("kit","reference","previous-sources","previous-classes",
              "candidate-sources","candidate-classes"):
        p.add_argument("--"+n,type=Path,required=True)
    p.add_argument("--kit-sha256",required=True)
    p.add_argument("--reference-sha256",required=True)
    p.add_argument("--expected-sources",type=int,default=1277)
    p.add_argument("--expected-classes",type=int,default=1388)
    p.add_argument("--out",type=Path)
    a=p.parse_args(argv)
    try:
        if a.out and (a.out.exists() or a.out.is_symlink()):
            raise Refused("REFUSE_EXISTING_OUTPUT")
        result=audit(
            kit=a.kit,kit_sha=a.kit_sha256,
            reference=a.reference,reference_sha=a.reference_sha256,
            previous_sources=a.previous_sources,previous_classes=a.previous_classes,
            candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
            expected_sources=a.expected_sources,expected_classes=a.expected_classes)
        out=json.dumps(result,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as f:f.write(out)
        else:print(out,end="")
        return 0
    except (Refused,OSError,ValueError) as ex:
        reason=str(ex) if isinstance(ex,Refused) else "INPUT_OR_FS_FAILURE"
        print(json.dumps({"status":"R401_REFUSED","reason":reason}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
