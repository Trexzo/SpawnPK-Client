#!/usr/bin/env python3
"""R415 strict read-only SHA-pinned private candidate source/class gate.

Outputs only booleans and counts, not recovered Java, compiled bytecode,
loot history, credentials, user filesystem paths or private packages.
Never executes the private game or opens history/intent staging files.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

BASE=Path(__file__).resolve().parents[1]
HELPER=BASE/"r395"/"audit_private_candidate_delta.py"
if not HELPER.is_file():
    raise RuntimeError("R415 public R395 archive helper required")
spec=importlib.util.spec_from_file_location("r415_r395",HELPER)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused
P="rs/plugins/loottracker/"
STORE=P+"LootHistoryStore.java"
PLUGIN=P+"LootTrackerPlugin.java"
MOVE=P+"AtomicFileReplace.java"
PRICE=P+"TradingPostPrices.java"
SOURCE_DIFF={STORE,PLUGIN}
CLASS_DIFF={P+"LootHistoryStore.class",P+"LootTrackerPlugin.class"}
GOLD_SOURCE_DIFF={
    STORE,PLUGIN,MOVE,P+"LootTrackerPanel.java",
    P+"LootTrackerItem.java",P+"LootTrackerRecord.java",
}
GOLD_CLASS_DIFF={
    P+"LootHistoryStore.class",P+"LootHistoryStore$ItemDto.class",
    P+"LootHistoryStore$RecordDto.class",P+"AtomicFileReplace.class",
    P+"LootTrackerPlugin.class",P+"LootTrackerPanel.class",
    P+"LootTrackerItem.class",P+"LootTrackerRecord.class",
}
NESTED_PREEXISTING={
    P+"LootHistoryStore$R411StageState.class",
    P+"LootHistoryStore$R413WriteDisposition.class",
    P+"LootTrackerPanel$R413DeleteSnapshot.class",
    P+"LootHistoryStore$R414IntentState.class",
}

def require(s:str,token:str,why:str):
    if token not in s:raise Refused(why)

def ordered(s:str,*tokens:str):
    offset=0
    for token in tokens:
        found=s.find(token,offset)
        if found<0:
            raise Refused("R415_PRIVATE_INTENT_PHASE_ORDER_DRIFT_"+token[:45])
        offset=found+len(token)

def code(blob:bytes)->str:
    try:return r393.mask_java(blob.decode("utf8"))
    except UnicodeDecodeError as e:raise Refused("R415_NON_UTF8_SOURCE") from e

def method(text:str,name:str)->str:
    try:return r394.method_body(text,name)
    except Exception as e:raise Refused("R415_METHOD_NOT_FOUND_"+name) from e

def verify_structure(old_store:bytes,new_store:bytes,
                     old_plugin:bytes,new_plugin:bytes,
                     old_move:bytes,new_move:bytes,
                     old_price:bytes,new_price:bytes)->dict:
    if old_move!=new_move or old_price!=new_price:
        raise Refused("R415_ATOMIC_MOVER_OR_PRICING_CHANGED")
    original_store=code(old_store)
    store=code(new_store)
    original_plugin=code(old_plugin)
    plugin=code(new_plugin)
    try:
        store_raw=new_store.decode("utf8")
    except UnicodeError as e:raise Refused("R415_JAVA_TEXT_DECODE_FAILED") from e
    if "r415PrepareConfirmedDeleteIntent" in original_store:
        raise Refused("R415_PRIOR_ALREADY_HAS_PRODUCER")
    # Crucial R414 protocol detail: Java must contain escaped
    # newline sequences; source double-escaped backslash+n would
    # serialize LITERAL \n and R414 would quarantine every marker.
    for marker_literal in (
        '"v=1\\nserial=1\\nnonce="',
        '"\\nbefore="',
        '"\\nafter="',
        '"\\n"',
    ):
        require(store_raw,marker_literal,
                "R415_CANONICAL_JAVA_NEWLINE_LITERAL_REQUIRED")
    if '"v=1\\\\nserial=1' in store_raw:
        raise Refused("R415_MARKER_DOUBLE_ESCAPED_NEWLINE_REFUSED")
    for required in (
        "UUID.randomUUID().toString()",
        "R414_INTENT_NAME",
        'R414_INTENT_NAME + ".tmp"',
        "StandardCharsets.US_ASCII",
    ):
        require(store_raw,required,"R415_MARKER_GRAMMAR_OR_NAME_DRIFT")
    writer=method(store,"r415SaveWithReceipt")
    routine=method(store,"saveWithReceipt")
    confirmed=method(store,"r415SaveConfirmedDeletionWithReceipt")
    require(routine,"return r415SaveWithReceipt(records, false)",
            "R415_ROUTINE_AUTOSAVE_NOT_JOURNAL_FREE")
    require(confirmed,"return r415SaveWithReceipt(records, true)",
            "R415_CONFIRMED_WRITER_NOT_SELECTED")
    if routine.count("r415SaveWithReceipt(records, false)")!=1 or \
       confirmed.count("r415SaveWithReceipt(records, true)")!=1:
        raise Refused("R415_AMBIGUOUS_WRITER_DISPATCH")
    ordered(writer,
        "r413LastWriteDisposition = R413WriteDisposition.FAILED_BEFORE_REPLACE",
        "r411RefuseUnresolvedStage(",
        "if (records == null)",
        "if (confirmedDeletion)",
        "r415OriginalDigest = r414DigestCurrentHistory()",
        "Document document = new Document()",
        "StandardOpenOption.CREATE_NEW",
        "writer.flush()",
        "channel.force(true)",
        "if (confirmedDeletion)",
        "r415DigestStagedHistory(temp.toPath())",
        "r415PrepareConfirmedDeleteIntent(r415OriginalDigest,",
        "r415OriginalDigest.equals(r414DigestCurrentHistory())",
        "r415AfterDigest.equals(r415DigestStagedHistory(temp.toPath()))",
        "r413LastWriteDisposition = R413WriteDisposition.REPLACE_ATTEMPTED",
        "AtomicFileReplace.moveStrict(temp, file)",
        "r413LastWriteDisposition = R413WriteDisposition.COMMITTED",
        "return true")
    if writer.count("if (confirmedDeletion)")!=2 or \
       writer.count("r415PrepareConfirmedDeleteIntent(")!=1:
        raise Refused("R415_EXACTLY_ONE_CONFIRMED_JOURNAL_PRODUCER")
    if "r413LastWriteDisposition = R413WriteDisposition.FAILED_BEFORE_REPLACE" in \
       writer[writer.index("AtomicFileReplace.moveStrict(temp, file)"):]:
        raise Refused("R415_POSTREPLACE_FAILURE_MISCLASSIFIED")
    intent=method(store,"r415PrepareConfirmedDeleteIntent")
    ordered(intent,
        "before == null || after == null || before.equals(after)",
        "UUID.randomUUID().toString()",
        "markerText.getBytes(StandardCharsets.US_ASCII)",
        "markerBytes.length > R414_MAX_INTENT_BYTES",
        "FileChannel.open(intentTemp",
        "StandardOpenOption.CREATE_NEW",
        "channel.force(true)",
        "r414DigestCurrentHistory()",
        "r415DigestStagedHistory(stagedHistory.toPath())",
        "Files.createLink(intentFinal, intentTemp)",
        "Files.delete(intentTemp)",
        "r414IntentState() != R414IntentState.ABORTED_BEFORE_REPLACE",
        "return true")
    if intent.count("Files.createLink(intentFinal, intentTemp)")!=1 or \
       intent.count("channel.force(true)")!=1:
        raise Refused("R415_INTENT_PUBLISH_OR_FORCE_COUNT_DRIFT")
    for prohibited in (
        "Files.move(intentTemp", "Files.copy(intentTemp",
        "Files.delete(intentFinal)", "Files.deleteIfExists(intentFinal)",
        "StandardCopyOption.REPLACE_EXISTING",
        "AtomicFileReplace.moveStrict(intentTemp",
        "Files.write(intentFinal",
    ):
        if prohibited in intent:
            raise Refused("R415_FINAL_MARKER_MUTATION_OR_CLOBBER_FORBIDDEN")
    if "Files.delete(intentTemp)" in intent.split(
        "Files.createLink(intentFinal, intentTemp)",1)[0]:
        raise Refused("R415_TEMP_LINK_REMOVED_BEFORE_FINAL_CREATION")
    generic_digest=method(store,"r415DigestRegularPath")
    staged_digest=method(store,"r415DigestStagedHistory")
    original_digest=method(store,"r414DigestCurrentHistory")
    require(original_digest,"r415DigestRegularPath(file.toPath(), true)",
            "R415_ORIGINAL_HISTORY_ABSENCE_RULE_CHANGED")
    require(staged_digest,"r415DigestRegularPath(staged, false)",
            "R415_STAGING_MISSING_MUST_NOT_EQUAL_ABSENT")
    ordered(generic_digest,
        "Files.readAttributes(target",
        "LinkOption.NOFOLLOW_LINKS",
        "absentMeansOriginalHistory ?",
        "prior.isRegularFile()",
        "prior.size() > MAX_HISTORY_BYTES",
        "options.add(LinkOption.NOFOLLOW_LINKS)",
        "Files.newByteChannel(target, options)",
        "observed > MAX_HISTORY_BYTES",
        "r414SameMetadata(prior, after)",
        "observed != prior.size()",
        "sha.digest()")
    if "Files.newOutputStream(" in generic_digest or "Files.write(" in generic_digest:
        raise Refused("R415_DIGEST_IS_NOT_READ_ONLY")
    for method_name in ("r414IntentState","r411StageState","loadForMerge",
                        "clearWithReceipt","deleteStale","r414SameMetadata",
                        "r411RefuseUnresolvedStage"):
        if method(original_store,method_name)!=method(store,method_name):
            raise Refused("R415_EXISTING_READER_OR_FENCE_CHANGED_"+method_name)
    # All previous confirmed-edit safety gates must remain intact.
    previous_edit=method(original_plugin,"r402ApplyPanelDeletion")
    edit=method(plugin,"r402ApplyPanelDeletion")
    if previous_edit!=edit.replace(
        '''                  else
                  {
                     // R415 produces a persistent unresolved journal.
                     // The disk commit is acknowledged, but later
                     // writes must stay disabled until R416 safely
                     // adopts the exact committed history and
                     // reconciles the intent.
                     r401ClearUnsafe = true;
                     r396LastCommitSucceeded = false;
                     log.warn("LootTracker: confirmed deletion committed with "
                        + "unresolved intent; further writes quarantined");
                  }
''',""):
        # Whitespace and reconstructed comments are not security
        # relevant; insist on all actual admission/receipt primitives.
        for token in (
            "historyStore.r411StageState()", "panel.r413CaptureDeleteSnapshot()",
            "historyStore.r413ResetWriteDisposition()",
            "mutation.run()", "persistHistory()", "r402EditTransactionOpen = false",
            "panel.r413RestoreDeleteSnapshot(r413Before)",
        ):
            require(edit,token,"R415_R413_DELETION_ADMISSION_REGRESSION")
    ordered(edit,
        "historyStore.r411StageState()",
        "panel.r413CaptureDeleteSnapshot()",
        "historyStore.r413ResetWriteDisposition()",
        "mutation.run()",
        "persistHistory()",
        "if (!r402EditWriteReceipt)",
        "r413ProvenUncommitted =",
        "r401ClearUnsafe = true",
        "r396LastCommitSucceeded = false",
        "panel.r413RestoreDeleteSnapshot(r413Before)",
        "r402EditTransactionOpen = false")
    if not re.search(r"else\s*\{\s*r401ClearUnsafe\s*=\s*true\s*;\s*"
                     r"r396LastCommitSucceeded\s*=\s*false\s*;",edit):
        raise Refused("R415_SUCCESS_MUST_QUARANTINE_FUTURE_WRITES")
    persist=method(plugin,"persistHistory")
    ordered(persist,
        "synchronized (r401FileGate)",
        "final boolean r415ConfirmedDelete",
        "r402EditTransactionOpen",
        "r415ConfirmedDelete",
        "historyStore.r415SaveConfirmedDeletionWithReceipt(merged)",
        "historyStore.saveWithReceipt(merged)",
        "if (r401Committed)")
    if persist.count("r415SaveConfirmedDeletionWithReceipt(merged)")!=1 or \
       persist.count("historyStore.saveWithReceipt(merged)")!=1:
        raise Refused("R415_NORMAL_AND_CONFIRMED_WRITER_MUST_REMAIN_DISTINCT")
    for method_name in ("r403QueueAutosave","clearHistory","shutDown"):
        if method(original_plugin,method_name)!=method(plugin,method_name):
            raise Refused("R415_UNRELATED_PLUGIN_FLOW_CHANGED_"+method_name)
    return {
        "canonical_newline_serialization_verified":True,
        "single_confirmed_only_journal_producer":True,
        "routine_save_does_not_create_intent":True,
        "stage_and_marker_created_exclusively":True,
        "both_stage_and_marker_forced":True,
        "final_marker_created_without_clobber":True,
        "postpublication_digest_rechecks":True,
        "strict_history_atomic_move_after_forced_intent":True,
        "ambiguous_move_not_rollback_safe":True,
        "successful_delete_blocks_future_writes":True,
        "r414_marker_classifier_and_r411_fences_retained":True,
        "automatic_intent_cleanup":False,
        "restart_adoption_and_acknowledgment_implemented":False,
        "cross_process_writer_lock_proven":False,
        "power_loss_durability_proven":False,
    }

def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,previous_classes_count:int=1392,
          candidate_classes_count:int=1392,golden_classes_count:int=1388)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    orig=r395.read_zip_bytes(kit,"source/",".java")
    gold=r395.read_zip_bytes(reference,"",".class")
    old=r395.read_tree_bytes(previous_sources,".java")
    new=r395.read_tree_bytes(candidate_sources,".java")
    oc=r395.read_tree_bytes(previous_classes,".class")
    nc=r395.read_tree_bytes(candidate_classes,".class")
    if any(len(x)!=expected_sources for x in (orig,old,new)) or \
       len(gold)!=golden_classes_count or \
       len(oc)!=previous_classes_count or len(nc)!=candidate_classes_count:
        raise Refused("R415_PINNED_SOURCE_CLASS_COUNT_DRIFT")
    if not orig.keys()==old.keys()==new.keys() or not oc.keys()==nc.keys():
        raise Refused("R415_SOURCE_CLASS_INVENTORY_CHANGED")
    if {n for n in old if old[n]!=new[n]}!=SOURCE_DIFF or \
       {n for n in oc if oc[n]!=nc[n]}!=CLASS_DIFF:
        raise Refused("R415_EXACT_TWO_EXISTING_SOURCE_CLASS_DIFF_REQUIRED")
    if {n for n in orig if orig[n]!=new[n]}!=GOLD_SOURCE_DIFF or \
       {n for n in gold if gold[n]!=nc[n]}!=GOLD_CLASS_DIFF or \
       set(oc)-set(gold)!=NESTED_PREEXISTING:
        raise Refused("R415_GOLDEN_SOURCE_CLASS_DELTA_MISMATCH")
    checks=verify_structure(old[STORE],new[STORE],
                            old[PLUGIN],new[PLUGIN],
                            old[MOVE],new[MOVE],
                            old[PRICE],new[PRICE])
    return {
        "status":"R415_PRIVATE_NONCLOBBER_INTENT_STATIC_GATE_PASS",
        "source_count":len(new),
        "compiled_class_count":len(nc),
        "changed_existing_source_vs_r414":len(SOURCE_DIFF),
        "changed_existing_class_vs_r414":len(CLASS_DIFF),
        "new_nested_class_vs_r414":0,
        **checks,
        "private_client_executed":False,
        "production_history_read_or_modified":False,
        "verified_actual_client_restart_or_handoff":False,
        "private_release_authorized":False,
        "merge_approved":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("kit","reference","previous-sources","previous-classes",
                "candidate-sources","candidate-classes"):
        p.add_argument("--"+key,required=True,type=Path)
    p.add_argument("--kit-sha256",required=True)
    p.add_argument("--reference-sha256",required=True)
    p.add_argument("--expected-sources",type=int,default=1277)
    p.add_argument("--previous-classes-count",type=int,default=1392)
    p.add_argument("--candidate-classes-count",type=int,default=1392)
    p.add_argument("--golden-classes-count",type=int,default=1388)
    p.add_argument("--out",type=Path)
    a=p.parse_args(argv)
    try:
        if a.out and (a.out.exists() or a.out.is_symlink()):
            raise Refused("R415_REFUSE_EXISTING_REPORT")
        r=audit(kit=a.kit,kit_sha=a.kit_sha256,
            reference=a.reference,reference_sha=a.reference_sha256,
            previous_sources=a.previous_sources,previous_classes=a.previous_classes,
            candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
            expected_sources=a.expected_sources,
            previous_classes_count=a.previous_classes_count,
            candidate_classes_count=a.candidate_classes_count,
            golden_classes_count=a.golden_classes_count)
        result=json.dumps(r,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as out:out.write(result)
        else:print(result,end="")
        return 0
    except (Refused,OSError,ValueError) as e:
        print(json.dumps({"status":"R415_PRIVATE_STATIC_REFUSED",
                          "reason":str(e) if isinstance(e,Refused) else "INPUT_OR_FILESYSTEM_ERROR"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
