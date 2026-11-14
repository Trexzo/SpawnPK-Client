#!/usr/bin/env python3
"""R399 public-only source/class scope gate for private session-scoped Swing drop callbacks.

Reads SHA-pinned owner-private *disposable* source/class trees in memory.
Never emits recovered Java, executes the game, inspects user history, or
authorizes launch/merge/release.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

_PARENT=Path(__file__).resolve().parents[1]/"r396"/"audit_shutdown_merge_candidate.py"
if not _PARENT.is_file():
    raise RuntimeError("Missing R396 inherited read-only scope gate")
spec=importlib.util.spec_from_file_location("r399_import_r396",_PARENT)
r396=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r396)
r395,r394,r393=r396.r395,r396.r394,r396.r393
Refused=r395.Refused
PLUGIN=r396.PLUGIN
CLASS=PLUGIN[:-5]+".class"


def check_private_structure(source:bytes)->dict:
    try:
        text=r393.mask_java(source.decode("utf8"))
    except UnicodeDecodeError as exc:
        raise Refused("NON_UTF8_PRIVATE_SOURCE") from exc

    fields=(("long","r399SessionEpoch"),
            ("boolean","r399AcceptingDrops"),
            ("long","r399RecordMutationSequence"))
    if any(not re.search(r"\b"+type_name+r"\s+"+name+r"\s*;",text)
           for type_name,name in fields):
        raise Refused("SESSION_OR_MUTATION_FIELD_MISSING")
    start=r394.method_body(text,"startUp")
    stop=r394.method_body(text,"shutDown")
    drop=r394.method_body(text,"addLoot")
    persist=r394.method_body(text,"persistHistory")
    merge=r394.method_body(text,"r396FinishStopMerge")

    if not r395.ordered(start,"++r399SessionEpoch",
                        "r399AcceptingDrops = true","instance = this"):
        raise Refused("START_EPOCH_ADMISSION_ORDER_DRIFT")
    if not r395.ordered(stop,"++r399SessionEpoch",
                        "r399AcceptingDrops = false","r396FinishStopMerge("):
        raise Refused("STOP_EPOCH_CLOSE_BEFORE_MERGE_MISSING")

    if not r395.ordered(drop,
        "final long r399DropSessionEpoch",
        "if (!r399AcceptingDrops || instance != this)",
        "r399DropSessionEpoch = r399SessionEpoch",
        "++r399RecordMutationSequence",
        "pendingRecords.add(record)",
        "SwingUtilities.invokeLater(",
        "r399DropSessionEpoch != r399SessionEpoch",
        "panel.add(",
        "if (it.next() == record)",
        "requestSave("):
        raise Refused("DROP_SESSION_CALLBACK_GUARD_MISSING_OR_REORDERED")

    # Guard must return before panel render, pending removal and late saves.
    match=re.search(r"if\s*\(\s*!r399AcceptingDrops\s*\|\|\s*"
                    r"r399DropSessionEpoch\s*!=\s*r399SessionEpoch\s*\|\|"
                    r"[\s\S]*?instance\s*!=\s*this\s*\)\s*\{",drop)
    if match is None:
        raise Refused("DROP_EPOCH_AND_INSTANCE_GUARD_MISSING")
    callback_guard=r393.braced_body(drop,drop.find("{",match.start(),match.end()))
    if "return;" not in callback_guard:
        raise Refused("STALE_CALLBACK_NOT_RETURNED")
    if drop.find("panel.add(",match.end())<0:
        raise Refused("STALE_GUARD_NOT_BEFORE_RENDER")
    # Verify that the callback's removal uses identity, and is placed
    # within the monitor that also protects pending additions.
    after_render=drop.split("panel.add(",1)[-1]
    if not re.search(r"synchronized\s*\(\s*r395HistoryGate\s*\)\s*\{",
                     after_render):
        raise Refused("PENDING_ACK_NOT_SYNCHRONIZED")
    if "it.next() == record" not in after_render:
        raise Refused("PENDING_ACK_MUST_USE_IDENTITY")
    # A queued callback is forbidden to request any save before its
    # identity-only handoff. A second request is also suspicious.
    if (drop.count("requestSave(")!=1 or
            drop.find("requestSave(")<drop.find("if (it.next() == record)")):
        raise Refused("LATE_OR_DUPLICATE_CALLBACK_SAVE_REQUEST")

    if not r395.ordered(merge,
        "r399MergedPreload = new ArrayList<>(r396PreloadRecords)",
        "combined.addAll(r399MergedPreload)",
        "historyStore.saveWithReceipt(combined)",
        "if (!committed)",
        "for (LootTrackerRecord saved : r399MergedPreload)",
        "if (it.next() == saved)",
        "r396PanelResetAfterVerifiedStop = true"):
        raise Refused("SHUTDOWN_COMMIT_IDENTITY_DRAIN_MISSING")
    if not r395.ordered(persist,
        "panel.getRecordsOffEdt()",
        "r399PendingSnapshot = new ArrayList<>(pendingRecords)",
        "r399MutationAtSnapshot = r399RecordMutationSequence",
        "merged.addAll(r399PendingSnapshot)",
        "historyStore.saveWithReceipt(merged)",
        "for (LootTrackerRecord saved : r399PendingSnapshot)",
        "if (it.next() == saved)",
        "r399RecordMutationSequence == r399MutationAtSnapshot",
        "r396LastCommitSucceeded = r399NoNewDropSinceSnapshot"):
        raise Refused("NORMAL_SAVE_ACK_IDENTITY_OR_MUTATION_GUARD_DRIFT")
    if not r395.ordered(start,
        "r398HasRetainedRecords",
        "r398UnreconciledPanelAtStart =",
        "!pendingRecords.isEmpty()",
        "!r396PreloadRecords.isEmpty()"):
        raise Refused("PREVIOUS_UNCOMMITTED_PENDING_NOT_PROTECTED")

    # Requiring the source to contain correct guards is not a proof of
    # atomic panel/pending snapshots or whole-program lock ordering.
    return {
        "drop_callback_scoped_to_session_epoch":True,
        "drop_admission_closes_before_stop_merge":True,
        "stale_callback_guard_precedes_render_and_save":True,
        "pending_callback_removal_is_identity_only":True,
        "shutdown_merge_drain_follows_success_receipt":True,
        "normal_save_drains_only_acked_pending":True,
        "save_success_is_mutation_version_checked":True,
        "retained_pending_and_preload_guard_present":True,
        "source_only_not_actual_race_execution":True,
    }


def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,expected_classes:int=1388)->dict:
    # R399 intentionally replaces the old R396 preload merge token and the
    # unconditional save-success flag. Check the inherited R396 structure on
    # an IN-MEMORY normalized view only; never modify the private source.
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    golden_src=r395.read_zip_bytes(kit,"source/",".java")
    golden_cls=r395.read_zip_bytes(reference,"",".class")
    old_src=r395.read_tree_bytes(previous_sources,".java")
    new_src=r395.read_tree_bytes(candidate_sources,".java")
    if (len(golden_src)!=expected_sources or golden_src.keys()!=new_src.keys()):
        raise Refused("GOLDEN_SOURCE_SET_DRIFT")
    golden_changes={k for k in golden_src if golden_src[k]!=new_src[k]}
    if golden_changes!=r396.EXPECTED_SOURCES:
        raise Refused("GOLDEN_SOURCE_SCOPE_DRIFT")
    normalized=new_src[PLUGIN]
    for old_token,new_token in (
        (b"combined.addAll(r399MergedPreload)",b"combined.addAll(r396PreloadRecords)"),
        (b"r396LastCommitSucceeded = r399NoNewDropSinceSnapshot",
         b"r396LastCommitSucceeded = true"),
    ):
        if normalized.count(old_token)!=1:
            raise Refused("INHERITED_STRUCTURE_NORMALIZATION_DRIFT")
        normalized=normalized.replace(old_token,new_token)
    inherited=r396.check_structure(normalized,new_src[r396.STORE])
    inherited.update({
        "java_source_count":len(new_src),
        "compiled_class_count":expected_classes,
        "changed_private_source_count":len(golden_changes),
        "changed_private_class_count":len(r396.EXPECTED_CLASSES),
    })
    if len(old_src)!=expected_sources or old_src.keys()!=new_src.keys():
        raise Refused("PREVIOUS_SOURCE_SET_DRIFT")
    changes=sorted(k for k in old_src if old_src[k]!=new_src[k])
    if changes!=[PLUGIN]:
        raise Refused("SOURCE_CHANGE_SCOPE_DRIFT")
    old_cls=r395.read_tree_bytes(previous_classes,".class")
    new_cls=r395.read_tree_bytes(candidate_classes,".class")
    if (len(golden_cls)!=expected_classes or golden_cls.keys()!=new_cls.keys()):
        raise Refused("GOLDEN_CLASS_SET_DRIFT")
    golden_class_changes={k for k in golden_cls if golden_cls[k]!=new_cls[k]}
    if golden_class_changes!=r396.EXPECTED_CLASSES:
        raise Refused("GOLDEN_CLASS_SCOPE_DRIFT")
    if len(old_cls)!=expected_classes or old_cls.keys()!=new_cls.keys():
        raise Refused("PREVIOUS_CLASS_SET_DRIFT")
    changed_classes=sorted(k for k in old_cls if old_cls[k]!=new_cls[k])
    if changed_classes!=[CLASS]:
        raise Refused("CLASS_CHANGE_SCOPE_DRIFT")
    structure=check_private_structure(new_src[PLUGIN])
    inherited.pop("status",None)
    return {
        "status":"R399_PRIVATE_SESSION_CALLBACK_STATIC_GATE_PASS",
        **inherited,**structure,
        "modified_source_count_vs_r398":len(changes),
        "modified_class_count_vs_r398":len(changed_classes),
        "modified_class_vs_r398":CLASS,
        "real_client_queued_callbacks_tested":False,
        "all_panel_pending_snapshot_races_resolved":False,
        "journal_integrated":False,
        "power_loss_durability_proven":False,
        "real_runtime_freeze_root_cause_proven":False,
        "private_source_release_approved":False,
        "normal_host_launch_authorized":False,
        "merge_approved":False,
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
        report=audit(
            kit=a.kit,kit_sha=a.kit_sha256,
            reference=a.reference,reference_sha=a.reference_sha256,
            previous_sources=a.previous_sources,previous_classes=a.previous_classes,
            candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
            expected_sources=a.expected_sources,expected_classes=a.expected_classes)
        out=json.dumps(report,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as f:
                f.write(out)
        else:
            print(out,end="")
        return 0
    except (Refused,OSError,ValueError) as exc:
        reason=str(exc) if isinstance(exc,Refused) else "INPUT_OR_FILESYSTEM_FAILURE"
        print(json.dumps({"status":"R399_REFUSED","reason":reason}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
