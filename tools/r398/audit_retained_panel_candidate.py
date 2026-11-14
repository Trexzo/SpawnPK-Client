#!/usr/bin/env python3
"""R398 source-only retained-panel fail-closed gate (private candidate custody).

Only audits SHA-pinned owner-private disposable Java source/class trees.
Never invokes game code, accesses account/loot history data, copies private
source to the repo, or authorizes GUI/client execution or release.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

_PARENT=Path(__file__).resolve().parents[1]/"r396"/"audit_shutdown_merge_candidate.py"
if not _PARENT.is_file():
    raise RuntimeError("Missing inherited R396 verifier")
spec=importlib.util.spec_from_file_location("r398_inherit_r396",_PARENT)
r396=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r396)
r395,r394,r393=r396.r395,r396.r394,r396.r393
Refused=r395.Refused
PLUGIN=r396.PLUGIN
CLASS=PLUGIN[:-5]+".class"


def check_private_structure(source: bytes) -> dict:
    try:
        masked=r393.mask_java(source.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise Refused("NON_UTF8_CANDIDATE") from exc
    if not re.search(r"\bvolatile\s+boolean\s+r398UnreconciledPanelAtStart\s*;",masked):
        raise Refused("UNRECONCILED_FLAG_NOT_VOLATILE")
    start=r394.method_body(masked,"startUp")
    load=r394.method_body(masked,"loadHistory")
    shutdown=r394.method_body(masked,"r396FinishStopMerge")
    clear=r394.method_body(masked,"clearHistory")
    # Start must check the actual retained panel AFTER clearing a prior
    # successful save. The original plugin may be disabled/re-enabled.
    if not r395.ordered(start,
        "panel = this.injector.getInstance(",
        "r398ResetPreviouslyCommitted = r396PanelResetAfterVerifiedStop",
        "r396PanelResetAfterVerifiedStop = false",
        "if (r398ResetPreviouslyCommitted)",
        "panel.clearRecords(",
        "r398HasRetainedRecords",
        "panel.getRecordsOffEdt().isEmpty(",
        "r398UnreconciledPanelAtStart = r398HasRetainedRecords"):
        raise Refused("STARTUP_RETAINED_PANEL_PROVENANCE_DRIFT")
    # Neither the panel monitor nor the panel mutation may be acquired
    # while the restore gate is held. This source-only check is narrower
    # than a whole-program lock-order proof.
    start_panel=r393.braced_body(start,start.index("{",start.index("if (r398ResetPreviouslyCommitted)")))
    if "panel.clearRecords(" not in start_panel:
        raise Refused("COMMITTED_PANEL_RESET_MISSING")
    if not r395.ordered(load,
        "if (r398UnreconciledPanelAtStart)",
        "return;",
        "final LootHistoryStore restoreStore"):
        raise Refused("RETENTION_RESTORE_BLOCK_MISSING")
    start_guard=re.search(
        r"\bif\s*\(\s*r398UnreconciledPanelAtStart\s*\)\s*\{",shutdown)
    if start_guard is None:
        raise Refused("DIRTY_SHUTDOWN_RETENTION_GUARD_MISSING")
    guard_body=r393.braced_body(
        shutdown,shutdown.find("{",start_guard.start(),start_guard.end()))
    if "return false;" not in guard_body:
        raise Refused("AMBIGUOUS_PANEL_NOT_REFUSED")
    if shutdown.find("historyStore.loadForMerge(")<start_guard.end():
        raise Refused("AMBIGUOUS_PANEL_CHECK_TOO_LATE")
    # Snapshot outside the history gate; previous R397 locked the
    # history gate and then called synchronized panel getter.
    snapshot="r398PanelEmpty = panel.getRecordsOffEdt().isEmpty()"
    guard="synchronized (r395HistoryGate)"
    if snapshot not in shutdown:
        raise Refused("PANEL_SNAPSHOT_MISSING")
    snap_at=shutdown.index(snapshot)
    lock_at=shutdown.find(guard,snap_at)
    load_at=shutdown.find("historyStore.loadForMerge(",snap_at)
    if lock_at<0 or load_at<0 or not snap_at<lock_at<load_at:
        raise Refused("PANEL_LOCK_ORDER_DRIFT")
    lock_open=shutdown.find("{",lock_at)
    locked=r393.braced_body(shutdown,lock_open)
    if "panel.getRecordsOffEdt(" in locked:
        raise Refused("PANEL_ACCESS_NESTED_INSIDE_RESTORE_GATE")
    if not r395.ordered(locked,
        "r396PreloadRecords.isEmpty()",
        "pendingRecords.isEmpty()",
        "r398PanelEmpty",
        "return true;"):
        raise Refused("CLEAN_STOP_TRIPLE_EMPTY_GUARD_DRIFT")
    if "r398UnreconciledPanelAtStart = false;" not in clear:
        raise Refused("USER_CLEAR_MUST_RESET_RETENTION_GUARD")
    return {
        "restarted_panel_provenance_captured":True,
        "ambiguous_panel_autorestore_blocked":True,
        "ambiguous_panel_shutdown_rewrite_refused":True,
        "user_clear_invalidates_unreconciled_guard":True,
        "panel_snapshot_outside_history_gate":True,
        "clean_stop_three_buffer_guard_retained":True,
        "source_structure_not_runtime_proof":True,
    }


def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,expected_classes:int=1388)->dict:
    inherited=r396.audit(
        kit=kit,kit_sha=kit_sha,
        reference=reference,reference_sha=reference_sha,
        sources=candidate_sources,classes=candidate_classes,
        expected_sources=expected_sources,expected_classes=expected_classes)
    old_src=r395.read_tree_bytes(previous_sources,".java")
    new_src=r395.read_tree_bytes(candidate_sources,".java")
    if len(old_src)!=expected_sources or old_src.keys()!=new_src.keys():
        raise Refused("PRIOR_SOURCE_SET_DRIFT")
    changes=sorted(k for k in old_src if old_src[k]!=new_src[k])
    if changes!=[PLUGIN]:
        raise Refused("SOURCE_CHANGE_SCOPE_DRIFT")
    old_cls=r395.read_tree_bytes(previous_classes,".class")
    new_cls=r395.read_tree_bytes(candidate_classes,".class")
    if len(old_cls)!=expected_classes or old_cls.keys()!=new_cls.keys():
        raise Refused("PRIOR_CLASS_SET_DRIFT")
    class_changes=sorted(k for k in old_cls if old_cls[k]!=new_cls[k])
    if class_changes!=[CLASS]:
        raise Refused("CLASS_CHANGE_SCOPE_DRIFT")
    structure=check_private_structure(new_src[PLUGIN])
    inherited.pop("status",None)
    return {
        "status":"R398_PRIVATE_RETAINED_PANEL_STATIC_GATE_PASS",
        **inherited,**structure,
        "changed_sources_vs_r397":len(changes),
        "changed_classes_vs_r397":len(class_changes),
        "changed_class_vs_r397":CLASS,
        "runtime_races_exercised_in_real_client":False,
        "unresolved_panel_durability_proven":False,
        "full_client_execution_authorized":False,
        "history_journal_integrated":False,
        "zero_data_loss_proven":False,
        "production_data_touched":False,
        "private_source_release_approved":False,
        "merge_approved":False,
    }


def main(argv=None)->int:
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
        report=audit(
            kit=a.kit,kit_sha=a.kit_sha256,
            reference=a.reference,reference_sha=a.reference_sha256,
            previous_sources=a.previous_sources,previous_classes=a.previous_classes,
            candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
            expected_sources=a.expected_sources,expected_classes=a.expected_classes)
        serialized=json.dumps(report,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as out:
                out.write(serialized)
        else:
            print(serialized,end="")
        return 0
    except (Refused,OSError,ValueError) as exc:
        reason=str(exc) if isinstance(exc,Refused) else "INPUT_OR_FILESYSTEM_FAILURE"
        print(json.dumps({"status":"R398_REFUSED","reason":reason}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
