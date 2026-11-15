#!/usr/bin/env python3
"""R411 public-safe read-only source/class gate for orphan-stage quarantine.

Reads only approved source/class corpus and SHA-pinned archives. It does
not launch recovered classes, read loot records, inspect any staging
payload, delete files, or approve private execution and distribution.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

HELPER=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not HELPER.is_file():
    raise RuntimeError("R411 requires inherited public R395 archive reader")
spec=importlib.util.spec_from_file_location("r411_public_r395",HELPER)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused

P="rs/plugins/loottracker/"
STORE=P+"LootHistoryStore.java"
MOVE=P+"AtomicFileReplace.java"
PRICE=P+"TradingPostPrices.java"
CHANGED_SRC={STORE}
CHANGED_CLASS={P+"LootHistoryStore.class"}
ADDED_CLASS={P+"LootHistoryStore$R411StageState.class"}
MODIFIED_VS_R381={
    STORE,MOVE,P+"LootTrackerPlugin.java",P+"LootTrackerPanel.java",
    P+"LootTrackerItem.java",P+"LootTrackerRecord.java",
}
CLASS_DIFF_VS_R381={
    P+"LootHistoryStore.class",
    P+"LootHistoryStore$RecordDto.class",
    P+"LootHistoryStore$ItemDto.class",
    P+"AtomicFileReplace.class",
    P+"LootTrackerPlugin.class",P+"LootTrackerPanel.class",
    P+"LootTrackerItem.class",P+"LootTrackerRecord.class",
}

def require(body:str,part:str,reason:str):
    if part not in body:raise Refused(reason)

def ordered(body:str,*parts:str):
    if not r395.ordered(body,*parts):
        raise Refused("R411_QUARANTINE_ORDER_DRIFT")

def method(text:str,name:str)->str:
    try:return r394.method_body(text,name)
    except Exception as e:raise Refused("R411_REQUIRED_METHOD_MISSING_"+name) from e

def code(raw:bytes)->str:
    try:return r393.mask_java(raw.decode("utf8"))
    except UnicodeDecodeError as e:raise Refused("R411_NON_UTF8_SOURCE") from e

def check_structure(before:bytes,current:bytes,prior_move:bytes,
                    current_move:bytes,prior_price:bytes,current_price:bytes)->dict:
    if prior_move!=current_move:
        raise Refused("R411_ATOMIC_MOVE_HELPER_MUST_NOT_CHANGE")
    if prior_price!=current_price:
        raise Refused("R411_PRICE_CACHE_MUST_NOT_CHANGE")
    old=code(before)
    new=code(current)
    enums=re.findall(r"\benum\s+R411StageState\b",new)
    if len(enums)!=1:
        raise Refused("R411_STAGE_CLASS_COUNT_DRIFT")
    for state in ("CLEAR","ORPHAN","UNSAFE"):
        require(new,state,"R411_STAGE_STATE_MISSING_"+state)
    if not re.search(r"\bR411StageState\s+r411StageState\s*\(",new):
        raise Refused("R411_STAGE_PROBE_MISSING")
    probe=method(new,"r411StageState")
    ordered(probe,
        "new File(file.getParentFile(), FILE_NAME +",
        "Files.readAttributes(staging.toPath()",
        "BasicFileAttributes.class",
        "LinkOption.NOFOLLOW_LINKS",
        "attrs.isRegularFile()",
        "R411StageState.ORPHAN",
        "R411StageState.UNSAFE",
        "catch (NoSuchFileException missing)",
        "return R411StageState.CLEAR",
        "catch (IOException | SecurityException unreadable)",
        "return R411StageState.UNSAFE")
    if probe.count("Files.readAttributes(")!=1:
        raise Refused("R411_PROBE_READATTRS_COUNT_DRIFT")
    if any(bad in probe for bad in (
        "Files.readAllBytes(", "Files.newInputStream(", "Files.newBufferedReader(",
        "Files.delete(", "Files.deleteIfExists(", "Files.move(", "Files.copy(",
        "Files.write(", "Files.newOutputStream(", "Files.newBufferedWriter(",
        "staging.delete(", "staging.renameTo(")):
        raise Refused("R411_PROBE_MUST_BE_METADATA_ONLY")
    if "LinkOption.NOFOLLOW_LINKS" not in probe:
        raise Refused("R411_STAGE_SYMLINK_MUST_NOT_BE_FOLLOWED")
    refuse=method(new,"r411RefuseUnresolvedStage")
    ordered(refuse,
        "r411StageState()",
        "if (stage == R411StageState.CLEAR)",
        "return false",
        "return true")
    if "stage == R411StageState.ORPHAN" in refuse:
        raise Refused("R411_UNSAFE_STAGE_MUST_ALSO_BE_REFUSED")
    if "Files.delete(" in refuse or "Files.move(" in refuse:
        raise Refused("R411_REFUSAL_MUST_PRESERVE_FILES")

    expected={
        "deleteStale":("return;","R411_LEGACY_CLEANUP_NOT_QUARANTINED"),
        "loadForMerge":("return null;","R411_STARTUP_MERGE_NOT_QUARANTINED"),
        "saveWithReceipt":("return false;","R411_SAVE_NOT_QUARANTINED"),
        "clearWithReceipt":("return false;","R411_CLEAR_NOT_QUARANTINED"),
    }
    for name,(result,reason) in expected.items():
        m=method(new,name)
        earlier=method(old,name)
        needle="r411RefuseUnresolvedStage("
        if m.count(needle)!=1:
            raise Refused(reason)
        # The first executable operation inside the method must be the
        # staging admission gate. Do not let a partial disk operation
        # proceed and check for an orphan only after that operation.
        first=m.lstrip()
        if not first.startswith("if (r411RefuseUnresolvedStage("):
            raise Refused("R411_"+name+"_GATE_NOT_FIRST")
        # The actual FIRST conditional must have the declared fail-closed
        # return; a later unrelated return false must not disguise
        # an unsafe "return true" in the staging refusal branch.
        first_guard = re.match(
            r"^if\s*\(\s*r411RefuseUnresolvedStage\([^)]*\)\s*\)\s*\{\s*"+
            re.escape(result)+r"\s*\}",first)
        if first_guard is None:
            raise Refused("R411_"+name+"_FIRST_REFUSAL_RETURN_DRIFT")
        ordered(m,needle,result)
        if "Files.delete(" in m[:m.index(needle)] or "AtomicFileReplace.move" in m[:m.index(needle)]:
            raise Refused("R411_LATE_DANGEROUS_STAGE_CHECK")
        if "r411RefuseUnresolvedStage(" in earlier:
            raise Refused("R411_PRIOR_SOURCE_ALREADY_HAS_STAGE_GUARD")
    save=method(new,"saveWithReceipt")
    require(save,"StandardOpenOption.CREATE_NEW",
            "R411_R410_CREATE_NEW_STAGING_GUARD_REGRESSION")
    ordered(save,"writer.flush()","channel.force(true)",
            "AtomicFileReplace.moveStrict(temp, file)","return true")
    if "AtomicFileReplace.move(temp, file)" in save:
        raise Refused("R411_STRICT_HISTORY_MOVE_REGRESSION")
    # The previous R410 history writer's other private methods are not
    # intentionally affected by the R411 staging guard.
    for name in ("getFile","save","load","deleteTree"):
        if method(old,name)!=method(new,name):
            raise Refused("R411_UNRELATED_HISTORY_METHOD_CHANGE_"+name)
    return {
        "staging_status_covers_missing_regular_and_unsafe_nodes":True,
        "probe_uses_nofollow_metadata_only":True,
        "startup_load_and_shutdown_merge_refuse_unresolved_stage":True,
        "routine_and_confirmed_save_refuse_unresolved_stage":True,
        "clear_all_refuses_to_erase_history_while_stage_unresolved":True,
        "legacy_cleanup_skips_on_unresolved_stage":True,
        "r410_create_new_and_strict_move_retained":True,
        "price_cache_and_legacy_move_unmodified":True,
        "staging_payload_read":False,
        "staging_file_automatically_deleted":False,
        "restart_transaction_journal_integrated":False,
        "automatic_orphan_recovery_or_cleanup_implemented":False,
        "cross_process_race_proven_safe":False,
    }

def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,previous_class_count:int=1388,
          candidate_class_count:int=1389)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    original=r395.read_zip_bytes(kit,"source/",".java")
    golden_cls=r395.read_zip_bytes(reference,"",".class")
    old=r395.read_tree_bytes(previous_sources,".java")
    now=r395.read_tree_bytes(candidate_sources,".java")
    old_cls=r395.read_tree_bytes(previous_classes,".class")
    now_cls=r395.read_tree_bytes(candidate_classes,".class")
    if any(len(x)!=expected_sources for x in (original,old,now)):
        raise Refused("R411_SOURCE_COUNT_DRIFT")
    if len(golden_cls)!=previous_class_count or len(old_cls)!=previous_class_count or \
       len(now_cls)!=candidate_class_count:
        raise Refused("R411_COMPILED_CLASS_COUNT_DRIFT")
    if not(original.keys()==old.keys()==now.keys()):
        raise Refused("R411_SOURCE_SET_DRIFT")
    if golden_cls.keys()!=old_cls.keys():
        raise Refused("R411_PREVIOUS_VS_GOLDEN_CLASS_SET_DRIFT")
    if set(now_cls)-set(old_cls)!=ADDED_CLASS or set(old_cls)-set(now_cls):
        raise Refused("R411_NEW_NESTED_CLASS_SCOPE_DRIFT")
    changes={n for n in now if now[n]!=old[n]}
    changed_classes={n for n in old_cls if old_cls[n]!=now_cls[n]}
    prev_against_original={n for n in old if old[n]!=original[n]}
    current_against_original={n for n in now if now[n]!=original[n]}
    class_against_original={n for n in golden_cls if now_cls[n]!=golden_cls[n]}
    if changes!=CHANGED_SRC or changed_classes!=CHANGED_CLASS:
        raise Refused("R411_EXACT_ONE_SOURCE_ONE_EXISTING_CLASS_REQUIRED")
    if prev_against_original!=MODIFIED_VS_R381 or \
       current_against_original!=MODIFIED_VS_R381 or \
       class_against_original!=CLASS_DIFF_VS_R381:
        raise Refused("R411_PINNED_ORIGINAL_SCOPE_DRIFT")
    checks=check_structure(old[STORE],now[STORE],old[MOVE],
                           now[MOVE],old[PRICE],now[PRICE])
    return {
        "status":"R411_PRIVATE_ORPHAN_STAGE_STATIC_GATE_PASS",
        "source_count":len(now),
        "previous_compiled_class_count":len(old_cls),
        "candidate_compiled_class_count":len(now_cls),
        "changed_source_count_vs_r410":len(changes),
        "changed_existing_class_count_vs_r410":len(changed_classes),
        "new_nested_enum_class_count":len(ADDED_CLASS),
        **checks,
        "private_client_executed":False,
        "production_history_modified":False,
        "actual_orphan_runtime_observed":False,
        "physical_power_loss_recovery_proven":False,
        "private_release_authorized":False,
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
    p.add_argument("--previous-class-count",type=int,default=1388)
    p.add_argument("--candidate-class-count",type=int,default=1389)
    p.add_argument("--out",type=Path)
    a=p.parse_args(argv)
    try:
        if a.out and (a.out.exists() or a.out.is_symlink()):
            raise Refused("R411_REFUSE_EXISTING_RECEIPT")
        r=audit(kit=a.kit,kit_sha=a.kit_sha256,
                reference=a.reference,reference_sha=a.reference_sha256,
                previous_sources=a.previous_sources,previous_classes=a.previous_classes,
                candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
                expected_sources=a.expected_sources,
                previous_class_count=a.previous_class_count,
                candidate_class_count=a.candidate_class_count)
        encoded=json.dumps(r,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as f:f.write(encoded)
        else:print(encoded,end="")
        return 0
    except (Refused,ValueError,OSError) as e:
        print(json.dumps({"status":"R411_REFUSED",
                          "reason":str(e) if isinstance(e,Refused)
                          else "INPUT_OR_FILESYSTEM_ERROR"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
