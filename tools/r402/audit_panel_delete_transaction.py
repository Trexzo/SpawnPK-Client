#!/usr/bin/env python3
"""R402: read-only SHA-pinned private source/class gate for panel deletion commits.

Public-safe diagnostics only; never export recovered Java, inspect actual
player histories, launch a private client or authorize merge/deployment.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

PRIOR=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not PRIOR.is_file(): raise RuntimeError("Missing R395 immutable source-kit helpers")
spec=importlib.util.spec_from_file_location("r402_inherit_r395",PRIOR)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused

PLUGIN="rs/plugins/loottracker/LootTrackerPlugin.java"
PANEL="rs/plugins/loottracker/LootTrackerPanel.java"
STORE="rs/plugins/loottracker/LootHistoryStore.java"
EXPECTED={PLUGIN,PANEL}
EXPECTED_GOLDEN={PLUGIN,PANEL,STORE}
CLASS=lambda p:p[:-5]+".class"

def require(text:str,token:str,reason:str):
    if token not in text:raise Refused(reason)

def sequence(text:str,*tokens:str):
    if not r395.ordered(text,*tokens):
        raise Refused("R402_DELETION_TRANSACTION_ORDER_DRIFT")

def check_structure(plugin:bytes,panel:bytes)->dict:
    try:
        s=r393.mask_java(plugin.decode("utf8"))
        p=r393.mask_java(panel.decode("utf8"))
    except UnicodeDecodeError as exc:
        raise Refused("NON_UTF8_CANDIDATE") from exc

    for name in ("r402PanelEditMutating","r402EditTransactionOpen",
                 "r402EditWriteReceipt"):
        if not re.search(r"\bboolean\s+"+name+r"\s*;",s):
            raise Refused("R402_TRANSACTION_FIELD_MISSING")
    edit=r394.method_body(s,"r402ApplyPanelDeletion")
    save=r394.method_body(s,"persistHistory")
    merge=r394.method_body(s,"r396FinishStopMerge")
    clear=r394.method_body(s,"clearHistory")
    for name,match in (
        ("removeSource","matchesGroup(title, type)"),
        ("removeType","r.isType(type)"),
        ("removeRecord","r == record"),
    ):
        meth=r394.method_body(p,name)
        sequence(meth,
                 "confirm(", "plugin.r402ApplyPanelDeletion(",
                 "synchronized (this)", "records.removeIf(",
                 "rebuild(")
        if "plugin.persistHistory()" in meth:
            raise Refused("R402_UNTRANSACTIONAL_PANEL_DELETE_"+name)
        if meth.count("plugin.r402ApplyPanelDeletion(")!=1:
            raise Refused("R402_PANEL_DELETE_WRAP_COUNT_"+name)
        require(meth,match,"R402_PANEL_DELETION_SELECTOR_DRIFT_"+name)
        if name=="removeRecord":
            require(meth,"r == record","R402_SINGLE_DROP_MUST_USE_IDENTITY")
    sequence(edit,
        "SwingUtilities.isEventDispatchThread()",
        "config.rememberLoot()",
        "mutation.run()",
        "synchronized (r401FileGate)",
        "r402EditTransactionOpen",
        "++r401ClearGeneration",
        "r402PanelEditMutating = true",
        "r402EditTransactionOpen = true",
        "r402EditWriteReceipt = false",
        "mutation.run()",
        "finally",
        "++r401ClearGeneration",
        "r402PanelEditMutating = false",
        "persistHistory()",
        "if (!r402EditWriteReceipt)",
        "r401ClearUnsafe = true",
        "r402EditTransactionOpen = false")
    if edit.count("++r401ClearGeneration")!=2:
        raise Refused("R402_BOTH_EDIT_EPOCH_TRANSITIONS_REQUIRED")
    if edit.count("mutation.run()")!=2:
        raise Refused("R402_PERSISTENCE_DISABLED_MODE_CONTRACT_DRIFT")
    if edit.count("persistHistory()")!=1:
        raise Refused("R402_DELETE_COMMIT_COUNT_DRIFT")
    # No history -> file lock inversion while transaction is opened.
    if edit.index("synchronized (r401FileGate)") < edit.index("synchronized (r395HistoryGate)"):
        pass
    else:
        raise Refused("R402_FILE_HISTORY_LOCK_ORDER_DRIFT")
    for match in re.finditer(r"synchronized\s*\(\s*r395HistoryGate\s*\)\s*\{",edit):
        block=r393.braced_body(edit,edit.find("{",match.start()))
        if "synchronized (r401FileGate)" in block:
            raise Refused("R402_NESTED_FILE_GATE_IN_HISTORY_GATE")
        if "mutation.run()" in block:
            raise Refused("R402_PANEL_MUTATION_UNDER_HISTORY_GATE")
    # R401's file commit remains serialized; both checkpoints must
    # reject in-progress partial panel mutations.
    require(save,"r402PanelEditMutating","R402_SAVE_EDIT_GUARD_MISSING")
    if save.count("r402PanelEditMutating")<4:
        raise Refused("R402_SAVE_EDIT_GUARD_COUNT_DRIFT")
    sequence(save,
        "r402PanelEditMutating",
        "panel.getRecordsOffEdt()",
        "r402PanelEditMutating",
        "synchronized (r401FileGate)",
        "historyStore.saveWithReceipt(merged)",
        "if (r401Committed)",
        "if (r402EditTransactionOpen)",
        "r402EditWriteReceipt = true")
    require(merge,"r402PanelEditMutating","R402_SHUTDOWN_MERGE_EDIT_GUARD_MISSING")
    require(clear,"r401ClearInProgress = true","R401_CLEAR_ALL_REGRESSION")
    # Verify rendering/edit mutation sits inside wrapper closure and no
    # direct panel write can be triggered before transaction admission.
    return {
        "three_panel_deletion_selectors_wrapped":True,
        "edit_and_save_share_same_instance_file_gate":True,
        "edit_generation_bumped_before_and_after_mutation":True,
        "save_refuses_partial_panel_mutation":True,
        "commit_receipt_checked_before_marking_delete_durable":True,
        "failed_commit_quarantines_auto_writes":True,
        "persistence_disabled_preserves_ui_only_edit":True,
        "no_history_to_file_lock_inversion_detected":True,
        "source_only_not_actual_race_proof":True,
    }

def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,expected_classes:int=1388)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    g_src=r395.read_zip_bytes(kit,"source/",".java")
    g_cls=r395.read_zip_bytes(reference,"",".class")
    old=r395.read_tree_bytes(previous_sources,".java")
    new=r395.read_tree_bytes(candidate_sources,".java")
    oldcls=r395.read_tree_bytes(previous_classes,".class")
    newcls=r395.read_tree_bytes(candidate_classes,".class")
    if (any(len(x)!=expected_sources for x in (g_src,old,new)) or
        any(x.keys()!=new.keys() for x in (g_src,old))):
        raise Refused("R402_GOLDEN_OR_PREVIOUS_SOURCE_DRIFT")
    if (any(len(x)!=expected_classes for x in (g_cls,oldcls,newcls)) or
        any(x.keys()!=newcls.keys() for x in (g_cls,oldcls))):
        raise Refused("R402_GOLDEN_OR_PREVIOUS_CLASS_DRIFT")
    changes={p for p in new if new[p]!=old[p]}
    classchanges={p for p in newcls if newcls[p]!=oldcls[p]}
    vs_golden={p for p in new if new[p]!=g_src[p]}
    classgolden={p for p in newcls if newcls[p]!=g_cls[p]}
    if changes!=EXPECTED or classchanges!={CLASS(p) for p in EXPECTED}:
        raise Refused("R402_TWO_SOURCE_CLASS_SCOPE_DRIFT")
    if vs_golden!=EXPECTED_GOLDEN or classgolden!={CLASS(p) for p in EXPECTED_GOLDEN}:
        raise Refused("R402_GOLDEN_THREE_SOURCE_CLASS_SCOPE_DRIFT")
    checks=check_structure(new[PLUGIN],new[PANEL])
    return {
        "status":"R402_PRIVATE_PANEL_DELETE_STATIC_GATE_PASS",
        "source_count":len(new),
        "compiled_class_count":len(newcls),
        "modified_source_count_vs_r401":2,
        "modified_class_count_vs_r401":2,
        **checks,
        "private_client_runtime_executed":False,
        "production_history_written":False,
        "actual_edt_ordering_verified":False,
        "cross_process_writer_lock_proven":False,
        "power_loss_durability_proven":False,
        "private_release_authorized":False,
        "merge_approved":False,
    }

def main(argv=None)->int:
    ap=argparse.ArgumentParser(description=__doc__)
    for arg in ("kit","reference","previous-sources","previous-classes",
                "candidate-sources","candidate-classes"):
        ap.add_argument("--"+arg,type=Path,required=True)
    ap.add_argument("--kit-sha256",required=True)
    ap.add_argument("--reference-sha256",required=True)
    ap.add_argument("--expected-sources",type=int,default=1277)
    ap.add_argument("--expected-classes",type=int,default=1388)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args(argv)
    try:
        if a.out and (a.out.exists() or a.out.is_symlink()):
            raise Refused("REFUSE_EXISTING_REPORT")
        receipt=audit(
            kit=a.kit,kit_sha=a.kit_sha256,
            reference=a.reference,reference_sha=a.reference_sha256,
            previous_sources=a.previous_sources,previous_classes=a.previous_classes,
            candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
            expected_sources=a.expected_sources,expected_classes=a.expected_classes)
        text=json.dumps(receipt,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as f:f.write(text)
        else:print(text,end="")
        return 0
    except (Refused,OSError,ValueError) as ex:
        reason=str(ex) if isinstance(ex,Refused) else "INPUT_OR_FILESYSTEM_FAILURE"
        print(json.dumps({"status":"R402_REFUSED","reason":reason}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
