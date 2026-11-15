#!/usr/bin/env python3
"""R412 SHA-pinned private source/class read-only pre-mutation safety gate.

No private source is output, no private class is executed and no actual loot
history, tmp file, account data or production directory is opened.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

HELPER=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not HELPER.is_file():raise RuntimeError("Missing public R395 archive helper")
spec=importlib.util.spec_from_file_location("r412_public_r395",HELPER)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused

P="rs/plugins/loottracker/"
PLUGIN=P+"LootTrackerPlugin.java"
STORE=P+"LootHistoryStore.java"
MOVER=P+"AtomicFileReplace.java"
PRICE=P+"TradingPostPrices.java"
MODIFIED_SOURCE={PLUGIN}
MODIFIED_CLASS={P+"LootTrackerPlugin.class"}
KNOWN_ORIGINAL_DIFF={
    PLUGIN,STORE,MOVER,P+"LootTrackerPanel.java",
    P+"LootTrackerItem.java",P+"LootTrackerRecord.java"}
KNOWN_ORIGINAL_CLASS_DIFF={
    P+"LootTrackerPlugin.class",P+"LootHistoryStore.class",
    P+"LootHistoryStore$RecordDto.class",P+"LootHistoryStore$ItemDto.class",
    P+"AtomicFileReplace.class",P+"LootTrackerPanel.class",
    P+"LootTrackerItem.class",P+"LootTrackerRecord.class"}
STAGE_ENUM=P+"LootHistoryStore$R411StageState.class"

def require(body:str,needle:str,why:str):
    if needle not in body:raise Refused(why)

def ordered(body:str,*tokens:str):
    if not r395.ordered(body,*tokens):
        raise Refused("R412_DELETE_STAGE_GATE_ORDER_DRIFT")

def code(raw:bytes)->str:
    try:return r393.mask_java(raw.decode("utf8"))
    except UnicodeDecodeError as e:raise Refused("R412_NON_UTF8_SOURCE") from e

def method(raw:str,name:str)->str:
    try:return r394.method_body(raw,name)
    except Exception as e:
        raise Refused("R412_METHOD_NOT_FOUND_"+name) from e

def monitor_body(body:str,lock:str)->str:
    hit=re.search(r"synchronized\s*\(\s*"+re.escape(lock)+r"\s*\)\s*\{",body)
    if not hit:raise Refused("R412_MISSING_MONITOR_"+lock)
    try:return r393.braced_body(body,hit.end()-1)
    except Exception as e:raise Refused("R412_UNBALANCED_MONITOR_"+lock) from e

def validate(old_plugin:bytes,new_plugin:bytes,old_store:bytes,new_store:bytes)->dict:
    if old_store!=new_store:raise Refused("R412_PRIOR_STORE_MUST_BE_BYTE_IDENTICAL")
    before=code(old_plugin)
    after=code(new_plugin)
    old=method(before,"r402ApplyPanelDeletion")
    new=method(after,"r402ApplyPanelDeletion")
    if before.count("r411StageState()")!=0:
        raise Refused("R412_PREVIOUS_PREADMISSION_ALREADY_PRESENT")
    if new.count("r411StageState()")!=1 or new.count("R411StageState.CLEAR")!=1:
        raise Refused("R412_EXACT_ONE_STAGE_ADMISSION_REQUIRED")
    if "r411StageState()" in old:
        raise Refused("R412_ORIGINAL_ALREADY_HAS_STAGE_GUARD")
    ordered(new,
        "SwingUtilities.isEventDispatchThread()",
        "if (!config.rememberLoot())",
        "mutation.run()",
        "synchronized (r401FileGate)",
        "historyStore.r411StageState()",
        "LootHistoryStore.R411StageState.CLEAR",
        "synchronized (r395HistoryGate)",
        "r401ClearUnsafe = true",
        "r396LastCommitSucceeded = false",
        "return;",
        "synchronized (r395HistoryGate)",
        "if (!historyLoaded",
        "++r401ClearGeneration",
        "r402PanelEditMutating = true",
        "r402EditTransactionOpen = true",
        "mutation.run()",
        "persistHistory()",
        "if (!r402EditWriteReceipt)",
        "r401ClearUnsafe = true",
        "r402EditTransactionOpen = false")
    # Keep every original admission condition, not merely the edit
    # generation and eventual failure receipt. Otherwise a source
    # change could skip an existing unsafe/clear/handoff barrier.
    original_admission = (
        r"if\s*\(\s*!historyLoaded\s*\|\|\s*r401ClearInProgress"
        r"\s*\|\|\s*r401ClearUnsafe\s*\|\|\s*r400PanelHandoffUnsafe"
        r"\s*\|\|\s*r398UnreconciledPanelAtStart\s*\|\|"
        r"\s*r402EditTransactionOpen\s*\)"
    )
    if not re.search(original_admission,new):
        raise Refused("R412_ORIGINAL_ADMISSION_CONDITIONS_CHANGED")
    if not re.search(original_admission,old):
        raise Refused("R412_PREVIOUS_ADMISSION_CONDITIONS_DRIFT")
    if new.count("mutation.run()")!=2:
        raise Refused("R412_DELETE_MUTATION_COUNT_DRIFT")
    if new.count("persistHistory()")!=1:
        raise Refused("R412_DELETE_ACKNOWLEDGED_SAVE_COUNT_DRIFT")
    file_section=monitor_body(new,"r401FileGate")
    if not file_section.lstrip().startswith("if (historyStore.r411StageState()"):
        raise Refused("R412_GUARD_MUST_BE_FIRST_INSIDE_FILEGATE")
    # Stage check must be evaluated before the BEGIN_EDIT history
    # lock; otherwise mutation state changes before the refusal.
    first_guard=re.match(
        r"^\s*if\s*\(\s*historyStore\.r411StageState\(\)\s*!=\s*"+
        r"LootHistoryStore\.R411StageState\.CLEAR\s*\)\s*\{",
        file_section)
    if first_guard is None:raise Refused("R412_EXACT_CLEAR_ONLY_GATE_REQUIRED")
    stage_block=r393.braced_body(file_section,first_guard.end()-1)
    ordered(stage_block,
        "synchronized (r395HistoryGate)",
        "r401ClearUnsafe = true",
        "r396LastCommitSucceeded = false",
        "return;")
    if not stage_block.rstrip().endswith("return;"):
        raise Refused("R412_STAGE_REFUSAL_MUST_EXIT_EDIT")
    if "mutation.run()" in stage_block or "persistHistory()" in stage_block or \
       "r402EditTransactionOpen = true" in stage_block:
        raise Refused("R412_REFUSAL_MUST_NOT_MUTATE_OR_SAVE")
    if "r401ClearUnsafe = false" in stage_block:
        raise Refused("R412_REFUSAL_CANNOT_CLEAR_UNSAFE_FLAG")
    if file_section.count("synchronized (r395HistoryGate)")<3:
        raise Refused("R412_HISTORY_MONITOR_INVARIANT_DRIFT")
    gate_after=method(code(new_store),"r411StageState")
    ordered(gate_after,
        "Files.readAttributes(staging.toPath()",
        "LinkOption.NOFOLLOW_LINKS",
        "attrs.isRegularFile()",
        "catch (NoSuchFileException missing)",
        "return R411StageState.CLEAR",
        "catch (IOException | SecurityException unreadable)",
        "return R411StageState.UNSAFE")
    for required in ("loadForMerge","saveWithReceipt","clearWithReceipt"):
        if "r411RefuseUnresolvedStage(" not in method(code(new_store),required):
            raise Refused("R412_R411_STAGE_STORE_GUARD_REGRESSION_"+required)
    if "r403QueueAutosave()" not in after:
        raise Refused("R412_AUTOSAVE_EXECUTOR_MISSING")
    return {
        "preexisting_stage_checked_inside_file_gate_before_edit":True,
        "nonclear_stage_refuses_before_panel_mutation":True,
        "unsafe_history_and_receipt_reset_on_refusal":True,
        "original_synchronous_delete_receipt_retained":True,
        "ui_only_mode_unchanged":True,
        "r411_store_stage_guard_retained":True,
        "r403_background_autosave_retained":True,
        "cross_process_stage_appearance_after_check_excluded":False,
        "failed_save_rolls_back_prior_ui_mutation":False,
        "automatic_stage_cleanup_integrated":False,
        "durable_transaction_journal_integrated":False,
    }

def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,expected_classes:int=1389)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    orig=r395.read_zip_bytes(kit,"source/",".java")
    gold_classes=r395.read_zip_bytes(reference,"",".class")
    prior=r395.read_tree_bytes(previous_sources,".java")
    now=r395.read_tree_bytes(candidate_sources,".java")
    prev_classes=r395.read_tree_bytes(previous_classes,".class")
    new_classes=r395.read_tree_bytes(candidate_classes,".class")
    if any(len(x)!=expected_sources for x in (orig,prior,now)):
        raise Refused("R412_PRIVATE_SOURCE_COUNT_DRIFT")
    if len(prev_classes)!=expected_classes or len(new_classes)!=expected_classes or \
       len(gold_classes)!=expected_classes-1:
        raise Refused("R412_PRIVATE_CLASS_COUNT_DRIFT")
    if not(orig.keys()==prior.keys()==now.keys()) or prev_classes.keys()!=new_classes.keys():
        raise Refused("R412_EXACT_SOURCE_CLASS_SET_DRIFT")
    if set(prev_classes)-set(gold_classes)!={STAGE_ENUM}:
        raise Refused("R412_R411_ENUM_BASELINE_DRIFT")
    changed={n for n in now if prior[n]!=now[n]}
    changed_class={n for n in prev_classes if prev_classes[n]!=new_classes[n]}
    if changed!=MODIFIED_SOURCE or changed_class!=MODIFIED_CLASS:
        raise Refused("R412_EXACT_ONE_PLUGIN_SOURCE_AND_CLASS_REQUIRED")
    if {n for n in now if now[n]!=orig[n]}!=KNOWN_ORIGINAL_DIFF:
        raise Refused("R412_PINNED_R381_SOURCE_SCOPE_DRIFT")
    if {n for n in gold_classes if new_classes[n]!=gold_classes[n]}!=KNOWN_ORIGINAL_CLASS_DIFF:
        raise Refused("R412_PINNED_R381_CLASS_SCOPE_DRIFT")
    results=validate(prior[PLUGIN],now[PLUGIN],prior[STORE],now[STORE])
    return {
        "status":"R412_PRIVATE_DELETE_PREADMISSION_STATIC_GATE_PASS",
        "source_count":len(now),
        "compiled_class_count":len(new_classes),
        "source_diff_vs_r411":len(changed),
        "existing_class_diff_vs_r411":len(changed_class),
        **results,
        "private_client_executed":False,
        "private_history_or_stage_read":False,
        "no_merged_or_deployed_artifact":True,
        "complete_delete_rollback_proven":False,
        "real_edt_latency_improved":False,
        "physical_power_loss_safety_proven":False,
        "private_release_authorized":False,
        "merge_approved":False,
    }

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("kit","reference","previous-sources","previous-classes",
              "candidate-sources","candidate-classes"):
        p.add_argument("--"+n,required=True,type=Path)
    p.add_argument("--kit-sha256",required=True)
    p.add_argument("--reference-sha256",required=True)
    p.add_argument("--expected-sources",type=int,default=1277)
    p.add_argument("--expected-classes",type=int,default=1389)
    p.add_argument("--out",type=Path)
    a=p.parse_args(argv)
    try:
        if a.out and (a.out.exists() or a.out.is_symlink()):
            raise Refused("R412_REFUSE_EXISTING_RECEIPT")
        result=audit(kit=a.kit,kit_sha=a.kit_sha256,reference=a.reference,
            reference_sha=a.reference_sha256,
            previous_sources=a.previous_sources,previous_classes=a.previous_classes,
            candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
            expected_sources=a.expected_sources,expected_classes=a.expected_classes)
        text=json.dumps(result,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as out:out.write(text)
        else:print(text,end="")
        return 0
    except (Refused,OSError,ValueError) as e:
        print(json.dumps({"status":"R412_REFUSED",
                          "reason":str(e) if isinstance(e,Refused) else "INPUT_OR_FILESYSTEM_ERROR"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
