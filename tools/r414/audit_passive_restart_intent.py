#!/usr/bin/env python3
"""R414 public SHA-pinned read-only audit of passive restart-intent classification.

No recovered Java or class bytes are emitted. The tool does not execute
private classes or touch history, the stage, marker, credentials or live client.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re
HELPER=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not HELPER.is_file():raise RuntimeError("R414 inherited public archive helpers missing")
spec=importlib.util.spec_from_file_location("r414_public_r395",HELPER)
r395=importlib.util.module_from_spec(spec);spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused
P="rs/plugins/loottracker/"
STORE=P+"LootHistoryStore.java"
MOVE=P+"AtomicFileReplace.java"
PRICE=P+"TradingPostPrices.java"
PLUGIN=P+"LootTrackerPlugin.java"
PANEL=P+"LootTrackerPanel.java"
SOURCE_DIFF={STORE}
CLASS_DIFF={P+"LootHistoryStore.class"}
NEW_CLASS={P+"LootHistoryStore$R414IntentState.class"}
R411_NEW=P+"LootHistoryStore$R411StageState.class"
R413_NEW={P+"LootHistoryStore$R413WriteDisposition.class",
          P+"LootTrackerPanel$R413DeleteSnapshot.class"}
GOLD_SOURCES={STORE,MOVE,PLUGIN,PANEL,P+"LootTrackerItem.java",P+"LootTrackerRecord.java"}
GOLD_CLASSES={
 P+"LootHistoryStore.class",P+"LootHistoryStore$ItemDto.class",
 P+"LootHistoryStore$RecordDto.class",P+"LootTrackerPlugin.class",
 P+"LootTrackerPanel.class",P+"AtomicFileReplace.class",
 P+"LootTrackerItem.class",P+"LootTrackerRecord.class"}

def require(text:str,token:str,why:str):
    if token not in text:raise Refused(why)

def ordered(text:str,*tokens:str):
    if not r395.ordered(text,*tokens):
        raise Refused("R414_RECOVERY_CLASSIFICATION_ORDER_DRIFT")

def code(blob:bytes)->str:
    try:return r393.mask_java(blob.decode("utf8"))
    except UnicodeDecodeError as e:raise Refused("R414_NON_UTF8_SOURCE") from e

def method(text:str,name:str)->str:
    try:return r394.method_body(text,name)
    except Exception as e:raise Refused("R414_REQUIRED_METHOD_MISSING_"+name) from e

def check_structure(old_store:bytes,new_store:bytes,
                    old_move:bytes,new_move:bytes,
                    old_price:bytes,new_price:bytes)->dict:
    if old_move!=new_move:raise Refused("R414_STRICT_ATOMIC_MOVE_CHANGED")
    if old_price!=new_price:raise Refused("R414_PRICE_CACHE_CHANGED")
    before=code(old_store)
    s=code(new_store)
    for token in ("NONE","ABORTED_BEFORE_REPLACE",
                  "COMMITTED_BEFORE_ACK","QUARANTINED"):
        require(s,token,"R414_INTENT_STATUS_MISSING_"+token)
    if s.count("enum R414IntentState")!=1:
        raise Refused("R414_SINGLE_CLASSIFIER_ENUM_REQUIRED")
    require(s,"R414_MAX_INTENT_BYTES = 512",
            "R414_MARKER_MAX_BYTES_CHANGED")
    require(s,'R414_INTENT_NAME = "loot-history.delete.intent"',
            "R414_INTENT_FILENAME_DRIFT")
    classify=method(s,"r414IntentState")
    ordered(classify,
        "unresolvedIntentTemp",
        "Files.readAttributes(unresolvedIntentTemp",
        "LinkOption.NOFOLLOW_LINKS",
        "return R414IntentState.QUARANTINED",
        "Files.readAttributes(intent",
        "return R414IntentState.NONE",
        "intentBefore.isRegularFile()",
        "intentBefore.size() > R414_MAX_INTENT_BYTES",
        "noFollowRead.add(LinkOption.NOFOLLOW_LINKS)",
        "Files.newByteChannel(intent, noFollowRead)",
        "r414SameMetadata(intentBefore",
        "text.split(",
        '"v=1".equals(fields[0])',
        "serial=[1-9][0-9]{0,15}",
        "nonce=[0-9a-f]{8}",
        "before=(ABSENT|[0-9a-f]{64})",
        "after=[0-9a-f]{64}",
        "Arrays.equals(marker, text.getBytes(StandardCharsets.US_ASCII))",
        "before.equals(after)",
        "r414DigestCurrentHistory()",
        "current.equals(before)",
        "return R414IntentState.ABORTED_BEFORE_REPLACE",
        "current.equals(after)",
        "return R414IntentState.COMMITTED_BEFORE_ACK",
        "return R414IntentState.QUARANTINED")
    if not re.search(r"catch\s*\(\s*IOException\s*\|\s*RuntimeException\s+\w+\s*\)",classify):
        raise Refused("R414_INTENT_IO_AND_SECURITY_ERRORS_NOT_QUARANTINED")
    if classify.count("Files.newByteChannel(intent, noFollowRead)")!=1:
        raise Refused("R414_UNBOUNDED_OR_EXTRA_MARKER_READ")
    if classify.count("Files.readAttributes(unresolvedIntentTemp")!=1:
        raise Refused("R414_PARTIAL_PREPARED_INTENT_NOT_FENCED")
    if classify.count("return R414IntentState.NONE")!=1:
        raise Refused("R414_FALSE_CLEAN_MARKER")
    digest=method(s,"r414DigestCurrentHistory")
    ordered(digest,
        "Files.readAttributes(target",
        "LinkOption.NOFOLLOW_LINKS",
        'return "ABSENT"',
        "prior.isRegularFile()",
        "prior.size() > MAX_HISTORY_BYTES",
        'MessageDigest.getInstance("SHA-256")',
        "options.add(LinkOption.NOFOLLOW_LINKS)",
        "Files.newByteChannel(target, options)",
        "observed > MAX_HISTORY_BYTES",
        "r414SameMetadata(prior, after)",
        "observed != prior.size()",
        "sha.digest()",
        "return digest.toString()")
    if digest.count("Files.newByteChannel(target, options)")!=1:
        raise Refused("R414_HISTORY_HASH_READ_BOUNDARY_CHANGED")
    if not re.search(r"observed\s*>\s*MAX_HISTORY_BYTES",digest):
        raise Refused("R414_HISTORY_HASH_NOT_BOUNDED")
    metadata=method(s,"r414SameMetadata")
    for key in ("isRegularFile()","size()","lastModifiedTime()","fileKey()"):
        require(metadata,key,"R414_METADATA_IDENTITY_CHECK_MISSING")
    for body in (classify,digest,metadata):
        for prohibited in (
            "Files.delete(", "Files.deleteIfExists(", "Files.move(", "Files.copy(",
            "Files.write(", "Files.newOutputStream(", "FileChannel.open(",
            "AtomicFileReplace.moveStrict(", "Thread.sleep(", "SwingUtilities.invokeAndWait("):
            if prohibited in body:
                raise Refused("R414_PASSIVE_CLASSIFIER_ATTEMPTS_MUTATION_OR_BLOCKING_HOP")
    stage=method(s,"r411StageState")
    ordered(stage,
        "r414IntentState() != R414IntentState.NONE",
        "return R411StageState.UNSAFE",
        "new File(file.getParentFile(), FILE_NAME +",
        "Files.readAttributes(staging.toPath()",
        "LinkOption.NOFOLLOW_LINKS",
        "return R411StageState.CLEAR")
    if not stage.lstrip().startswith("if (r414IntentState() != R414IntentState.NONE)"):
        raise Refused("R414_INTENT_GUARD_NOT_FIRST_STAGE_CHECK")
    for method_name in ("loadForMerge","saveWithReceipt",
                        "clearWithReceipt","deleteStale"):
        if method(before,method_name)!=method(s,method_name):
            raise Refused("R414_UNRELATED_WRITER_OR_READER_CHANGED_"+method_name)
        if "r411RefuseUnresolvedStage(" not in method(s,method_name):
            raise Refused("R414_R411_ADMISSION_GUARD_REMOVED_"+method_name)
    if "AtomicFileReplace.moveStrict(temp, file)" not in method(s,"saveWithReceipt"):
        raise Refused("R414_STRICT_SAVE_WRITER_BROKEN")
    return {
        "version_one_marker_grammar_and_digest_classification_present":True,
        "absent_marker_and_orphan_marker_tmp_distinguished":True,
        "no_follow_bounded_marker_and_history_reads":True,
        "pre_and_post_digest_metadata_consistency_checks":True,
        "unresolved_marker_fences_existing_r411_stage_guard":True,
        "legacy_cleanup_startup_save_clear_all_confirmed_edit_fenced":True,
        "strict_history_writer_and_cache_unchanged":True,
        "automatic_marker_production_integrated":False,
        "automatic_marker_cleanup_integrated":False,
        "startup_adoption_or_replay_implemented":False,
        "valid_marker_authorizes_new_writes":False,
        "cross_process_stability_or_authenticated_marker_proven":False,
        "physical_power_loss_durability_proven":False,
    }

def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,previous_class_count:int=1391,
          candidate_class_count:int=1392,
          golden_class_count:int=1388)->dict:
    r395.require_pin(kit,kit_sha);r395.require_pin(reference,reference_sha)
    orig=r395.read_zip_bytes(kit,"source/",".java")
    gold=r395.read_zip_bytes(reference,"",".class")
    before=r395.read_tree_bytes(previous_sources,".java")
    after=r395.read_tree_bytes(candidate_sources,".java")
    old_classes=r395.read_tree_bytes(previous_classes,".class")
    new_classes=r395.read_tree_bytes(candidate_classes,".class")
    if any(len(x)!=expected_sources for x in (orig,before,after)):
        raise Refused("R414_SOURCE_COUNT_DRIFT")
    if len(gold)!=golden_class_count or len(old_classes)!=previous_class_count or \
       len(new_classes)!=candidate_class_count:
        raise Refused("R414_COMPILED_CLASS_COUNT_DRIFT")
    if not(orig.keys()==before.keys()==after.keys()):
        raise Refused("R414_SOURCE_FILE_SET_DRIFT")
    if set(new_classes)-set(old_classes)!=NEW_CLASS or set(old_classes)-set(new_classes):
        raise Refused("R414_ADDED_ENUM_CLASS_SCOPE_DRIFT")
    if {x for x in before if before[x]!=after[x]}!=SOURCE_DIFF or \
       {x for x in old_classes if old_classes[x]!=new_classes[x]}!=CLASS_DIFF:
        raise Refused("R414_EXACT_ONE_SOURCE_ONE_EXISTING_CLASS_REQUIRED")
    if {x for x in orig if orig[x]!=after[x]}!=GOLD_SOURCES or \
       {x for x in gold if gold[x]!=new_classes[x]}!=GOLD_CLASSES or \
       set(old_classes)-set(gold)!={R411_NEW}|R413_NEW:
        raise Refused("R414_PINNED_R381_SOURCE_CLASS_SCOPE_DRIFT")
    result=check_structure(before[STORE],after[STORE],
                           before[MOVE],after[MOVE],before[PRICE],after[PRICE])
    return {
        "status":"R414_PRIVATE_PASSIVE_RESTART_INTENT_GATE_PASS",
        "source_count":len(after),"compiled_class_count":len(new_classes),
        "modified_sources_vs_r413":1,
        "modified_existing_classes_vs_r413":1,
        "new_nested_enum_classes_vs_r413":1,
        **result,
        "owner_private_client_executed":False,
        "actual_history_or_marker_read":False,
        "private_release_authorized":False,
        "merge_approved":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("kit","reference","previous-sources","previous-classes",
                 "candidate-sources","candidate-classes"):
        p.add_argument("--"+name,required=True,type=Path)
    p.add_argument("--kit-sha256",required=True)
    p.add_argument("--reference-sha256",required=True)
    p.add_argument("--expected-sources",type=int,default=1277)
    p.add_argument("--previous-class-count",type=int,default=1391)
    p.add_argument("--candidate-class-count",type=int,default=1392)
    p.add_argument("--golden-class-count",type=int,default=1388)
    p.add_argument("--out",type=Path)
    a=p.parse_args(argv)
    try:
        if a.out and (a.out.exists() or a.out.is_symlink()):
            raise Refused("R414_REFUSE_EXISTING_REPORT")
        result=audit(kit=a.kit,kit_sha=a.kit_sha256,
            reference=a.reference,reference_sha=a.reference_sha256,
            previous_sources=a.previous_sources,previous_classes=a.previous_classes,
            candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
            expected_sources=a.expected_sources,previous_class_count=a.previous_class_count,
            candidate_class_count=a.candidate_class_count,
            golden_class_count=a.golden_class_count)
        encoded=json.dumps(result,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as out:out.write(encoded)
        else:print(encoded,end="")
        return 0
    except (Refused,OSError,ValueError) as e:
        print(json.dumps({"status":"R414_REFUSED",
                          "reason":str(e) if isinstance(e,Refused) else "INPUT_OR_FILESYSTEM_ERROR"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
