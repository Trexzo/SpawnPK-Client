#!/usr/bin/env python3
"""R400: SHA-pinned public-safe verifier for the private optimistic handoff snapshot.

Reads disposable owner-local private source and .class trees. Emits only
counts, booleans and generic class names. No game execution, user history,
network access, recovered source release or production mutation.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

R395=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not R395.is_file():raise RuntimeError("Missing inherited archive helper")
spec=importlib.util.spec_from_file_location("r400_import_r395",R395)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused
PLUGIN="rs/plugins/loottracker/LootTrackerPlugin.java"
STORE="rs/plugins/loottracker/LootHistoryStore.java"
PLUGIN_CLASS=PLUGIN[:-5]+".class"
STORE_CLASS=STORE[:-5]+".class"

def need(block:str,token:str,reason:str):
    if token not in block:raise Refused(reason)

def in_order(block:str, *tokens:str):
    if not r395.ordered(block,*tokens):
        raise Refused("R400_CRITICAL_SOURCE_ORDER_DRIFT")

def check_structure(raw:bytes)->dict:
    try:source=r393.mask_java(raw.decode("utf8"))
    except UnicodeDecodeError as exc:raise Refused("NON_UTF8_CANDIDATE_SOURCE") from exc
    if not re.search(r"\blong\s+r400PanelHandoffVersion\s*;",source):
        raise Refused("HANDOFF_VERSION_FIELD_MISSING")
    if not re.search(r"\bboolean\s+r400PanelHandoffUnsafe\s*;",source):
        raise Refused("HANDOFF_UNSAFE_FIELD_MISSING")
    persist=r394.method_body(source,"persistHistory")
    drop=r394.method_body(source,"addLoot")
    stop_merge=r394.method_body(source,"r396FinishStopMerge")
    clear=r394.method_body(source,"clearHistory")
    start=r394.method_body(source,"startUp")
    stop=r394.method_body(source,"shutDown")

    for block,token,reason in [
        (start,"++r399SessionEpoch","SESSION_START_EPOCH_MISSING"),
        (stop,"r399AcceptingDrops = false","STOP_ADMISSION_NOT_CLOSED"),
        (drop,"r399DropSessionEpoch != r399SessionEpoch","STALE_DROP_GUARD_MISSING"),
        (drop,"if (it.next() == record)","PENDING_HANDOFF_NOT_IDENTITY_ONLY"),
        (drop,"r400PanelHandoffUnsafe = true","FAILED_HANDOFF_NOT_QUARANTINED"),
        (persist,"if (r400PanelHandoffUnsafe)","UNSAFE_HISTORY_WRITE_NOT_REFUSED"),
        (persist,"r400Before & 1L","HANDOFF_ODD_VERSION_NOT_CHECKED"),
        (persist,"r400Before != r400PanelHandoffVersion","HANDOFF_VERSION_NOT_REVALIDATED"),
        (persist,"r400PanelHandoffVersion & 1L","HANDOFF_IN_FLIGHT_NOT_RECHECKED"),
        (persist,"r400ConsistentPending = new ArrayList<>(pendingRecords)","PENDING_SNAPSHOT_NOT_CAPTURED"),
        (persist,"r400ConsistentMutation = r399RecordMutationSequence","MUTATION_WATERMARK_NOT_CAPTURED"),
        (persist,"r400ConsistentMerged.addAll(r400ConsistentPending)","CONSISTENT_MERGE_MISSING"),
        (persist,"savePending = true;","RETRY_EXHAUSTION_NOT_DEFERRED"),
        (persist,"historyStore.saveWithReceipt(merged)","VERIFIED_SAVE_MISSING"),
        (persist,"if (it.next() == saved)","COMMITTED_PENDING_NOT_DRAINED_BY_IDENTITY"),
        (persist,"r399RecordMutationSequence == r399MutationAtSnapshot","POST_SAVE_ADMISSION_GUARD_MISSING"),
        (stop_merge,"r400PanelHandoffUnsafe","SHUTDOWN_UNSAFE_PERSIST_REFUSAL_MISSING"),
        (clear,"r400PanelHandoffUnsafe = false;","EXPLICIT_CLEAR_RESET_MISSING"),
        (clear,"r400PanelHandoffVersion += 2L;","EXPLICIT_CLEAR_VERSION_INVALIDATION_MISSING"),
    ]:
        need(block,token,reason)
    in_order(drop,
        "r399DropSessionEpoch != r399SessionEpoch",
        "++r400PanelHandoffVersion",
        "panel.add(",
        "if (it.next() == record)",
        "r400Finished = true",
        "finally",
        "if (!r400Finished)",
        "r400PanelHandoffUnsafe = true",
        "++r400PanelHandoffVersion",
        "requestSave(")
    if drop.count("++r400PanelHandoffVersion")!=2:
        raise Refused("HANDOFF_MUST_INCREMENT_EXACTLY_TWICE")
    if drop.count("requestSave(")!=1 or drop.find("requestSave(")<drop.find("finally"):
        raise Refused("REQUEST_SAVE_BEFORE_HANDOFF_FINALIZATION")
    in_order(persist,
        "for (int r400Attempt = 0; r400Attempt < 5;",
        "r400Before = r400PanelHandoffVersion",
        "(r400Before & 1L) != 0L",
        "panel.getRecordsOffEdt()",
        "r400Before != r400PanelHandoffVersion",
        "r400ConsistentPending = new ArrayList<>(pendingRecords)",
        "r400ConsistentMutation = r399RecordMutationSequence",
        "r400ConsistentMerged.addAll(r400ConsistentPending)",
        "if (r400ConsistentMerged == null)",
        "savePending = true;",
        "historyStore.saveWithReceipt(merged)")
    if persist.count("panel.getRecordsOffEdt(")!=1:
        raise Refused("UNBOUNDED_OR_UNACCOUNTED_PANEL_SNAPSHOT")
    if persist.count("historyStore.saveWithReceipt(")!=1:
        raise Refused("UNBOUNDED_OR_UNACCOUNTED_STORE_WRITE")
    if not re.search(r"for\s*\(\s*int\s+r400Attempt\s*=\s*0;\s*"
                     r"r400Attempt\s*<\s*5;\s*\+\+r400Attempt\s*\)",persist):
        raise Refused("SNAPSHOT_RETRY_NOT_BOUNDED")
    # Check that no historyGate monitor is held while reading panel.
    at=persist.index("panel.getRecordsOffEdt(")
    before=persist[:at]
    opening=[m.start() for m in re.finditer(r"synchronized\s*\(\s*r395HistoryGate\s*\)\s*\{",before)]
    for k in opening:
        open_brace=before.find("{",k)
        close=r393.braced_body(persist,open_brace)
        if "panel.getRecordsOffEdt(" in close:
            raise Refused("PANEL_GETTER_NESTED_UNDER_HISTORY_GATE")
    # Same lock-order guarantee for EDT rendering: gate only guards the
    # version transitions; expensive Swing panel drawing stays outside.
    pos=drop.find("panel.add(")
    for m in re.finditer(r"synchronized\s*\(\s*r395HistoryGate\s*\)\s*\{",drop[:pos]):
        if "panel.add(" in r393.braced_body(drop,drop.find("{",m.start())):
            raise Refused("EDT_PANEL_RENDER_NESTED_UNDER_HISTORY_GATE")
    return {
        "optimistic_even_version_snapshots":True,
        "bounded_five_attempt_fail_closed":True,
        "no_panel_getter_inside_history_gate":True,
        "no_edt_panel_render_inside_history_gate":True,
        "two_sided_handoff_version_bookends":True,
        "failed_handoff_quarantined":True,
        "old_session_guard_preserved":True,
        "no_unverified_write_on_retry_exhaustion":True,
        "source_structure_not_runtime_race_proof":True,
    }

def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,expected_classes:int=1388)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    golden_src=r395.read_zip_bytes(kit,"source/",".java")
    golden_cls=r395.read_zip_bytes(reference,"",".class")
    old_src=r395.read_tree_bytes(previous_sources,".java")
    new_src=r395.read_tree_bytes(candidate_sources,".java")
    old_cls=r395.read_tree_bytes(previous_classes,".class")
    new_cls=r395.read_tree_bytes(candidate_classes,".class")
    if (len(golden_src)!=expected_sources or
        len(old_src)!=expected_sources or len(new_src)!=expected_sources or
        golden_src.keys()!=old_src.keys() or old_src.keys()!=new_src.keys()):
        raise Refused("SOURCE_FILE_SET_DRIFT")
    if (len(golden_cls)!=expected_classes or
        len(old_cls)!=expected_classes or len(new_cls)!=expected_classes or
        golden_cls.keys()!=old_cls.keys() or old_cls.keys()!=new_cls.keys()):
        raise Refused("CLASS_FILE_SET_DRIFT")
    changed_from_prev=[k for k in sorted(new_src) if old_src[k]!=new_src[k]]
    changed_cls_prev=[k for k in sorted(new_cls) if old_cls[k]!=new_cls[k]]
    changed_from_golden={k for k in golden_src if golden_src[k]!=new_src[k]}
    changed_cls_golden={k for k in golden_cls if golden_cls[k]!=new_cls[k]}
    if changed_from_prev!=[PLUGIN] or changed_cls_prev!=[PLUGIN_CLASS]:
        raise Refused("R400_ONE_FILE_CLASS_SCOPE_DRIFT")
    if changed_from_golden!={PLUGIN,STORE} or changed_cls_golden!={PLUGIN_CLASS,STORE_CLASS}:
        raise Refused("R400_GOLDEN_TWO_FILE_CLASS_SCOPE_DRIFT")
    checks=check_structure(new_src[PLUGIN])
    return {
        "status":"R400_PRIVATE_OPTIMISTIC_HANDOFF_STATIC_GATE_PASS",
        "source_count":len(new_src),"compiled_class_count":len(new_cls),
        "changed_source_count_vs_r399":1,"changed_class_count_vs_r399":1,
        "changed_class_vs_r399":PLUGIN_CLASS,
        **checks,
        "real_private_client_execution":False,
        "actual_runtime_interleaving_covered":False,
        "all_panel_write_producers_instrumented":False,
        "concurrent_writer_file_lock_proven":False,
        "power_loss_durability_proven":False,
        "normal_host_launch_authorized":False,
        "private_release_authorized":False,"merge_approved":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("kit","reference","previous-sources","previous-classes",
                 "candidate-sources","candidate-classes"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--kit-sha256",required=True)
    p.add_argument("--reference-sha256",required=True)
    p.add_argument("--expected-sources",type=int,default=1277)
    p.add_argument("--expected-classes",type=int,default=1388)
    p.add_argument("--out",type=Path)
    a=p.parse_args(argv)
    try:
        if a.out and (a.out.exists() or a.out.is_symlink()):
            raise Refused("REFUSE_EXISTING_REPORT")
        result=audit(
            kit=a.kit,kit_sha=a.kit_sha256,
            reference=a.reference,reference_sha=a.reference_sha256,
            previous_sources=a.previous_sources,previous_classes=a.previous_classes,
            candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
            expected_sources=a.expected_sources,expected_classes=a.expected_classes)
        rendered=json.dumps(result,indent=2,sort_keys=True)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as stream:stream.write(rendered)
        else:print(rendered,end="")
        return 0
    except (Refused,OSError,ValueError) as exc:
        reason=str(exc) if isinstance(exc,Refused) else "INPUT_OR_FILE_ERROR"
        print(json.dumps({"status":"R400_REFUSED","reason":reason}))
        return 2
if __name__=="__main__":
    raise SystemExit(main())
