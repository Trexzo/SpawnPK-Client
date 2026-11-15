#!/usr/bin/env python3
"""R413 public SHA-pinned read-only private delete known-precommit rollback audit.

Checks prior/candidate source and compiled class membership and exact
semantic guard order. Never launches recovered classes or opens history,
staging files, user data, credentials or the live game directory.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re
HELPER=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not HELPER.is_file():
    raise RuntimeError("R413 public inherited read-only archive helpers required")
spec=importlib.util.spec_from_file_location("r413_r395",HELPER)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused
P="rs/plugins/loottracker/"
PLUGIN=P+"LootTrackerPlugin.java"
STORE=P+"LootHistoryStore.java"
PANEL=P+"LootTrackerPanel.java"
MOVE=P+"AtomicFileReplace.java"
PRICE=P+"TradingPostPrices.java"
SOURCES={PLUGIN,STORE,PANEL}
CLASSES={P+n+".class" for n in ("LootTrackerPlugin","LootTrackerPanel","LootHistoryStore")}
ADDED={P+"LootHistoryStore$R413WriteDisposition.class",
       P+"LootTrackerPanel$R413DeleteSnapshot.class"}
R411_ADDED=P+"LootHistoryStore$R411StageState.class"
ORIGINAL_DIFFERENCES={
    PLUGIN,STORE,PANEL,MOVE,P+"LootTrackerItem.java",
    P+"LootTrackerRecord.java"}
ORIGINAL_CLASS_DIFFERENCES={
    P+"LootTrackerPlugin.class",P+"LootTrackerPanel.class",
    P+"LootHistoryStore.class",P+"AtomicFileReplace.class",
    P+"LootTrackerItem.class",P+"LootTrackerRecord.class",
    P+"LootHistoryStore$ItemDto.class",P+"LootHistoryStore$RecordDto.class",
}

def require(body:str,token:str,reason:str):
    if token not in body:raise Refused(reason)

def ordered(body:str,*tokens:str):
    if not r395.ordered(body,*tokens):
        raise Refused("R413_MUTATION_RECEIPT_ORDER_DRIFT")

def code(raw:bytes)->str:
    try:return r393.mask_java(raw.decode("utf8"))
    except UnicodeDecodeError as e:raise Refused("R413_PRIVATE_SOURCE_DECODE_REFUSED") from e

def method(body:str,name:str)->str:
    try:return r394.method_body(body,name)
    except Exception as e:raise Refused("R413_METHOD_MISSING_"+name) from e

def check_structure(prior:dict[str,bytes],new:dict[str,bytes])->dict:
    if prior[MOVE]!=new[MOVE] or prior[PRICE]!=new[PRICE]:
        raise Refused("R413_SHARED_MOVE_AND_CACHE_MUST_BE_UNCHANGED")
    b_plugin=code(prior[PLUGIN])
    plugin=code(new[PLUGIN])
    b_panel=code(prior[PANEL])
    panel=code(new[PANEL])
    b_store=code(prior[STORE])
    store=code(new[STORE])
    if "R413WriteDisposition" in b_store or "R413DeleteSnapshot" in b_panel or \
       "r413RestoreDeleteSnapshot" in b_plugin:
        raise Refused("R413_PARENT_ALREADY_HAS_ROLLBACK")

    # Only known non-replacement dispositions permit rollback. A
    # speculative or post-rename I/O error must never be conflated
    # with definitive failure to commit.
    for token in ("NOT_ATTEMPTED","FAILED_BEFORE_REPLACE","REPLACE_ATTEMPTED","COMMITTED"):
        require(store,token,"R413_MISSING_WRITER_DISPOSITION_"+token)
    if store.count("enum R413WriteDisposition")!=1:
        raise Refused("R413_WRITER_ENUM_MUST_BE_UNIQUE")
    reset=method(store,"r413ResetWriteDisposition")
    require(reset,"r413LastWriteDisposition = R413WriteDisposition.NOT_ATTEMPTED",
            "R413_WRITER_RESET_DRIFT")
    getter=method(store,"r413WriteDisposition")
    require(getter,"return r413LastWriteDisposition",
            "R413_DISPOSITION_GETTER_DRIFT")
    store_save=method(store,"saveWithReceipt")
    ordered(store_save,
        "r413LastWriteDisposition = R413WriteDisposition.FAILED_BEFORE_REPLACE",
        "r411RefuseUnresolvedStage(",
        "StandardOpenOption.CREATE_NEW",
        "writer.flush()",
        "channel.force(true)",
        "r413LastWriteDisposition = R413WriteDisposition.REPLACE_ATTEMPTED",
        "AtomicFileReplace.moveStrict(temp, file)",
        "r413LastWriteDisposition = R413WriteDisposition.COMMITTED",
        "return true")
    if store_save.count("r413LastWriteDisposition = R413WriteDisposition.FAILED_BEFORE_REPLACE")!=1 \
       or store_save.count("r413LastWriteDisposition = R413WriteDisposition.REPLACE_ATTEMPTED")!=1 \
       or store_save.count("r413LastWriteDisposition = R413WriteDisposition.COMMITTED")!=1:
        raise Refused("R413_WRITE_PHASE_ASSIGNMENT_COUNT_DRIFT")
    if "AtomicFileReplace.move(temp, file)" in store_save:
        raise Refused("R413_NONATOMIC_HISTORY_FALLBACK_REGRESSION")
    if "r413LastWriteDisposition = R413WriteDisposition.FAILED_BEFORE_REPLACE" in \
       store_save[store_save.index("AtomicFileReplace.moveStrict(temp, file)"):]:
        raise Refused("R413_POSTREPLACE_FAILURE_FALSELY_CALLED_SAFE")
    for method_name in ("loadForMerge","clearWithReceipt","r411StageState","deleteStale"):
        if method(b_store,method_name)!=method(store,method_name):
            raise Refused("R413_STORE_UNRELATED_METHOD_CHANGED_"+method_name)

    if panel.count("class R413DeleteSnapshot")!=1:
        raise Refused("R413_PANEL_SNAPSHOT_CLASS_MISSING")
    capture=method(panel,"r413CaptureDeleteSnapshot")
    ordered(capture,
        "SwingUtilities.isEventDispatchThread()",
        "throw new IllegalStateException(",
        "new R413DeleteSnapshot(new ArrayList<>(records), filterTitle,",
        "filterType, page, overallView, groupedView)")
    if not re.search(r"synchronized\s+R413DeleteSnapshot\s+r413CaptureDeleteSnapshot\s*\(",panel):
        raise Refused("R413_SNAPSHOT_NOT_SYNCHRONIZED")
    if "r405FrozenCopy()" in capture:
        raise Refused("R413_ROLLBACK_MUST_RETAIN_ORIGINAL_IDENTITIES")
    restore=method(panel,"r413RestoreDeleteSnapshot")
    ordered(restore,
        "before == null",
        "SwingUtilities.isEventDispatchThread()",
        "records.clear()",
        "records.addAll(before.records)",
        "filterTitle = before.filterTitle",
        "filterType = before.filterType",
        "page = before.page",
        "overallView = before.overallView",
        "groupedView = before.groupedView",
        "recountAggregates()",
        "addLeft(filterTitle != null)",
        "rebuild()")
    if not re.search(r"synchronized\s+void\s+r413RestoreDeleteSnapshot\s*\(",panel):
        raise Refused("R413_RESTORE_NOT_SYNCHRONIZED")
    if any(m in restore for m in ("Files.move(", "Files.delete(", "Files.write(",
                                  "persistHistory(", "invokeAndWait(")):
        raise Refused("R413_ROLLBACK_MUST_NOT_PERFORM_DISK_OR_BLOCKING_HOP")
    for method_name in ("getRecords","getRecordsOffEdt","r405FrozenRecords",
                        "clearRecords","addRecords","recountAggregates","rebuild"):
        if method(b_panel,method_name)!=method(panel,method_name):
            raise Refused("R413_PANEL_UNRELATED_METHOD_CHANGED_"+method_name)

    old_edit=method(b_plugin,"r402ApplyPanelDeletion")
    edit=method(plugin,"r402ApplyPanelDeletion")
    ordered(edit,
        "SwingUtilities.isEventDispatchThread()",
        "if (!config.rememberLoot())",
        "mutation.run()",
        "synchronized (r401FileGate)",
        "historyStore.r411StageState()",
        "R411StageState.CLEAR",
        "panel.r413CaptureDeleteSnapshot()",
        "if (!historyLoaded",
        "r402EditTransactionOpen = true",
        "historyStore.r413ResetWriteDisposition()",
        "mutation.run()",
        "persistHistory()",
        "if (!r402EditWriteReceipt)",
        "r401ClearUnsafe = true",
        "historyStore.r413WriteDisposition()",
        "R413WriteDisposition.FAILED_BEFORE_REPLACE",
        "if (r413ProvenUncommitted)",
        "panel.r413RestoreDeleteSnapshot(r413Before)",
        "r402EditTransactionOpen = false")
    if edit.count("mutation.run()")!=2 or edit.count("persistHistory()")!=1:
        raise Refused("R413_PANEL_DELETE_OR_COMMIT_COUNT_CHANGED")
    if edit.count("panel.r413CaptureDeleteSnapshot()")!=1 or \
       edit.count("panel.r413RestoreDeleteSnapshot(r413Before)")!=1:
        raise Refused("R413_SNAPSHOT_ROLLBACK_ADMISSION_COUNT_DRIFT")
    if "r413WriteDisposition() == LootHistoryStore.R413WriteDisposition.REPLACE_ATTEMPTED" in edit \
       or "r413WriteDisposition() != LootHistoryStore.R413WriteDisposition.COMMITTED" in edit:
        raise Refused("R413_AMBIGUOUS_COMMIT_MUST_NOT_ROLLBACK")
    if "r402EditTransactionOpen = false" not in edit[
          edit.index("panel.r413RestoreDeleteSnapshot(r413Before)"):]:
        raise Refused("R413_TRANSACTION_CLOSED_BEFORE_ROLLBACK")
    if "r401ClearUnsafe = false" in edit or "r396LastCommitSucceeded = true" in edit:
        raise Refused("R413_FAILED_DELETE_MUST_REMAIN_QUARANTINED")
    for name in ("persistHistory","r403QueueAutosave","clearHistory","shutDown"):
        if method(b_plugin,name)!=method(plugin,name):
            raise Refused("R413_PLUGIN_UNRELATED_METHOD_CHANGED_"+name)
    return {
        "write_attempt_disposition_four_states_present":True,
        "pre_replace_status_assigned_before_staging_check":True,
        "post_replace_ambiguity_never_marked_pre_replace":True,
        "strict_atomic_move_and_staged_file_force_retained":True,
        "original_panel_record_identity_snapshot":True,
        "panel_navigation_page_filter_rollback":True,
        "rollback_requires_explicit_failed_before_replace":True,
        "confirmed_edit_stays_transaction_open_through_rollback":True,
        "prior_r412_stage_guard_preserved":True,
        "price_cache_unchanged":True,
        "postreplace_ambiguous_commit_auto_rollback":False,
        "rollback_on_no_write_attempt":False,
        "full_cross_process_correctness_proven":False,
        "asynchronous_confirmed_deletions_enabled":False,
    }

def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,previous_classes_count:int=1389,
          candidate_classes_count:int=1391,expected_golden_classes:int=1388)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    original=r395.read_zip_bytes(kit,"source/",".java")
    golden=r395.read_zip_bytes(reference,"",".class")
    prior=r395.read_tree_bytes(previous_sources,".java")
    new=r395.read_tree_bytes(candidate_sources,".java")
    prior_cls=r395.read_tree_bytes(previous_classes,".class")
    classes=r395.read_tree_bytes(candidate_classes,".class")
    if any(len(x)!=expected_sources for x in (original,prior,new)):
        raise Refused("R413_PRIVATE_SOURCE_COUNT_DRIFT")
    if len(golden)!=expected_golden_classes or len(prior_cls)!=previous_classes_count or \
       len(classes)!=candidate_classes_count:
        raise Refused("R413_PRIVATE_CLASS_COUNT_DRIFT")
    if not(original.keys()==prior.keys()==new.keys()):
        raise Refused("R413_PRIVATE_SOURCE_SET_DRIFT")
    if set(classes)-set(prior_cls)!=ADDED or set(prior_cls)-set(classes):
        raise Refused("R413_NEW_NESTED_CLASS_SCOPE_DRIFT")
    changed={n for n in prior if prior[n]!=new[n]}
    changed_cls={n for n in prior_cls if prior_cls[n]!=classes[n]}
    if changed!=SOURCES or changed_cls!=CLASSES:
        raise Refused("R413_EXACT_THREE_SOURCE_THREE_CLASS_REQUIRED")
    if {n for n in new if original[n]!=new[n]}!=ORIGINAL_DIFFERENCES or \
       {n for n in golden if golden[n]!=classes[n]}!=ORIGINAL_CLASS_DIFFERENCES or \
       set(prior_cls)-set(golden)!={R411_ADDED}:
        raise Refused("R413_PINNED_R381_CORPUS_DRIFT")
    checks=check_structure(prior,new)
    return {
        "status":"R413_PRIVATE_KNOWN_PRE_REPLACE_ROLLBACK_GATE_PASS",
        "source_count":len(new),"compiled_class_count":len(classes),
        "changed_source_count_vs_r412":len(changed),
        "changed_existing_classes_vs_r412":len(changed_cls),
        "new_nested_classes_vs_r412":len(ADDED),
        **checks,
        "private_client_executed":False,
        "production_history_read_or_modified":False,
        "true_swing_latency_measured":False,
        "power_loss_durability_proven":False,
        "private_release_authorized":False,
        "merge_approved":False,
    }

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("kit","reference","previous-sources","previous-classes",
                "candidate-sources","candidate-classes"):
        p.add_argument("--"+key,type=Path,required=True)
    p.add_argument("--kit-sha256",required=True)
    p.add_argument("--reference-sha256",required=True)
    p.add_argument("--expected-sources",type=int,default=1277)
    p.add_argument("--previous-classes-count",type=int,default=1389)
    p.add_argument("--candidate-classes-count",type=int,default=1391)
    p.add_argument("--expected-golden-classes",type=int,default=1388)
    p.add_argument("--out",type=Path)
    a=p.parse_args(argv)
    try:
        if a.out and (a.out.exists() or a.out.is_symlink()):
            raise Refused("R413_REFUSE_EXISTING_REPORT")
        r=audit(kit=a.kit,kit_sha=a.kit_sha256,reference=a.reference,
                reference_sha=a.reference_sha256,
                previous_sources=a.previous_sources,previous_classes=a.previous_classes,
                candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
                expected_sources=a.expected_sources,
                previous_classes_count=a.previous_classes_count,
                candidate_classes_count=a.candidate_classes_count,
                expected_golden_classes=a.expected_golden_classes)
        encoded=json.dumps(r,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as out:out.write(encoded)
        else:print(encoded,end="")
        return 0
    except (Refused,OSError,ValueError) as e:
        print(json.dumps({"status":"R413_REFUSED",
                          "reason":str(e) if isinstance(e,Refused) else "INPUT_OR_FILESYSTEM_ERROR"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
