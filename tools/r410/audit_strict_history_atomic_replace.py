#!/usr/bin/env python3
"""R410 public, read-only, SHA-pinned strict history atomic move acceptance gate.

Never executes private classes, reads history data, modifies the client,
prints private source or exports recovered Java/class bytes.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

BASE=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not BASE.is_file():
    raise RuntimeError("R410 requires public inherited archive readers")
spec=importlib.util.spec_from_file_location("r410_public_r395",BASE)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused

P="rs/plugins/loottracker/"
MOVER=P+"AtomicFileReplace.java"
STORE=P+"LootHistoryStore.java"
CACHE=P+"TradingPostPrices.java"
PLUGIN=P+"LootTrackerPlugin.java"
PANEL=P+"LootTrackerPanel.java"
ITEM=P+"LootTrackerItem.java"
RECORD=P+"LootTrackerRecord.java"
NEW_SRC={MOVER,STORE}
NEW_CLS={P+"AtomicFileReplace.class",P+"LootHistoryStore.class"}
GOLD_SRC=NEW_SRC|{PLUGIN,PANEL,ITEM,RECORD}
GOLD_CLS=NEW_CLS|{
    P+"LootHistoryStore$ItemDto.class",
    P+"LootHistoryStore$RecordDto.class",
    P+"LootTrackerItem.class",P+"LootTrackerPanel.class",
    P+"LootTrackerPlugin.class",P+"LootTrackerRecord.class",
}

def require(body:str,part:str,reason:str)->None:
    if part not in body:
        raise Refused(reason)

def ordered(body:str,*terms:str)->None:
    if not r395.ordered(body,*terms):
        raise Refused("R410_CRITICAL_WRITE_OR_MOVE_ORDER_DRIFT")

def method(text:str,name:str)->str:
    try:return r394.method_body(text,name)
    except Exception as e:
        raise Refused("R410_METHOD_NOT_FOUND_"+name) from e

def normalize(raw:bytes)->str:
    try:return r393.mask_java(raw.decode("utf8"))
    except UnicodeDecodeError as e:
        raise Refused("R410_NON_UTF8_SOURCE") from e

def check_structure(before_move:bytes,move:bytes,before_store:bytes,
                    store:bytes,price:bytes,before_price:bytes)->dict:
    m=normalize(move)
    earlier_m=normalize(before_move)
    h=normalize(store)
    earlier_h=normalize(before_store)
    c=normalize(price)
    earlier_c=normalize(before_price)
    if price!=before_price:
        raise Refused("R410_PRICE_CACHE_SOURCE_MUST_BE_BYTE_IDENTICAL")
    if method(m,"move")!=method(earlier_m,"move"):
        raise Refused("R410_LEGACY_PRICE_CACHE_MOVE_CHANGED")
    if method(h,"loadForMerge")!=method(earlier_h,"loadForMerge"):
        raise Refused("R410_HISTORY_READER_CHANGED")
    if method(h,"clearWithReceipt")!=method(earlier_h,"clearWithReceipt"):
        raise Refused("R410_CLEAR_ALL_DISK_RECEIPT_CHANGED")
    if method(h,"save")!=method(earlier_h,"save"):
        raise Refused("R410_HISTORY_SAVE_DISPATCH_CHANGED")
    if "r410" in method(h,"clearWithReceipt").lower():
        raise Refused("R410_CLEAR_ALL_REWRITE_NOT_AUTHORIZED")

    old=method(m,"move")
    ordered(old,
        "Files.move(temp.toPath(), target.toPath()",
        "StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE",
        "catch (AtomicMoveNotSupportedException e)",
        "StandardCopyOption.REPLACE_EXISTING")
    if old.count("Files.move(temp.toPath(), target.toPath()")!=2:
        raise Refused("R410_LEGACY_FALLBACK_MOVES_CHANGED")
    strict=method(m,"moveStrict")
    ordered(strict,
        "temp.getCanonicalFile().getParentFile().equals(",
        "target.getCanonicalFile().getParentFile()",
        "throw new IOException(",
        "Files.move(temp.toPath(), target.toPath()",
        "StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE",
        "catch (AtomicMoveNotSupportedException unsupported)",
        "throw unsupported;",
        "catch (FileSystemException locked)",
        "if (attempt >= MAX_ATTEMPTS)",
        "throw locked;",
        "Thread.sleep(RETRY_DELAY_MS)",
        "Thread.currentThread().interrupt()",
        "throw new IOException(")
    if strict.count("Files.move(temp.toPath(), target.toPath()")!=1:
        raise Refused("R410_STRICT_MOVE_COUNT_DRIFT")
    if "Files.copy(" in strict:
        raise Refused("R410_STRICT_REPLACEMENT_MUST_NOT_COPY")
    if re.search(r"Files\.move\([^;]*StandardCopyOption\.REPLACE_EXISTING\s*\);",strict,re.DOTALL):
        raise Refused("R410_NON_ATOMIC_STRICT_FALLBACK")
    if strict.count("catch (AtomicMoveNotSupportedException unsupported)")!=1:
        raise Refused("R410_ATOMIC_UNSUPPORTED_MUST_FAIL_CLOSED")
    if "return false;" in strict:
        raise Refused("R410_STRICT_MOVE_MUST_NOT_FAKE_RECEIPT")

    save=method(h,"saveWithReceipt")
    ordered(save,
        "if (records == null)",
        "new Document()",
        "document.version = FORMAT_VERSION",
        "RecordDto.from(record)",
        "FileChannel.open(temp.toPath()",
        "StandardOpenOption.CREATE_NEW",
        "StandardOpenOption.WRITE",
        "Channels.newOutputStream(channel)",
        "GSON.a(document, writer)",
        "writer.flush()",
        "channel.force(true)",
        "catch (IOException e)",
        "return false;",
        "AtomicFileReplace.moveStrict(temp, file)",
        "return true;")
    if save.count("AtomicFileReplace.moveStrict(temp, file)")!=1:
        raise Refused("R410_HISTORY_STRICT_MOVE_COUNT_DRIFT")
    if "AtomicFileReplace.move(temp, file)" in save:
        raise Refused("R410_HISTORY_STILL_USES_NONATOMIC_FALLBACK")
    if "Files.newOutputStream(temp.toPath())" in save:
        raise Refused("R410_STAGE_MAY_TRUNCATE_EXISTING_TEMP")
    if save.count("channel.force(true)")!=1 or \
       save.count("StandardOpenOption.CREATE_NEW")!=1:
        raise Refused("R410_HISTORY_FORCE_OR_TEMP_OWNERSHIP_DRIFT")
    if "Files.deleteIfExists(temp.toPath())" in save or "temp.delete()" in save:
        raise Refused("R410_UNEXPLAINED_TEMP_AUTOCLEANUP")
    if "Thread.sleep(" in save:
        raise Refused("R410_HISTORY_STORE_INTRODUCED_ADDITIONAL_SLEEP")
    if "FileChannel.open(" in method(h,"loadForMerge"):
        raise Refused("R410_HISTORY_LOAD_SEMANTICS_CHANGED")

    # This is only staged-file fsync and strict rename. No journal,
    # directory force, durable receipt or async EDT edit is implemented.
    return {
        "strict_history_atomic_move_required":True,
        "strict_path_has_no_nonatomic_copy_or_move_fallback":True,
        "strict_move_rejects_different_canonical_parent":True,
        "strict_move_retries_transient_filesystem_lock":True,
        "history_stage_is_create_new":True,
        "history_stage_is_flushed_and_forced_before_move":True,
        "legacy_price_cache_move_is_unchanged":True,
        "read_and_clear_history_methods_are_unchanged":True,
        "directory_metadata_forced":False,
        "durable_journal_integrated":False,
        "cross_process_writer_lock_proven":False,
        "confirmed_edt_deletion_made_nonblocking":False,
        "power_loss_survivability_proven":False,
    }

def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,expected_classes:int=1388)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    original=r395.read_zip_bytes(kit,"source/",".java")
    gold_cls=r395.read_zip_bytes(reference,"",".class")
    old=r395.read_tree_bytes(previous_sources,".java")
    new=r395.read_tree_bytes(candidate_sources,".java")
    old_cls=r395.read_tree_bytes(previous_classes,".class")
    new_cls=r395.read_tree_bytes(candidate_classes,".class")
    if any(len(x)!=expected_sources for x in (original,old,new)):
        raise Refused("R410_SOURCE_COUNT_DRIFT")
    if any(len(x)!=expected_classes for x in (gold_cls,old_cls,new_cls)):
        raise Refused("R410_CLASS_COUNT_DRIFT")
    if not(original.keys()==old.keys()==new.keys()) or \
       not(gold_cls.keys()==old_cls.keys()==new_cls.keys()):
        raise Refused("R410_SOURCE_CLASS_SET_DRIFT")
    changed={x for x in new if new[x]!=old[x]}
    changed_class={x for x in new_cls if new_cls[x]!=old_cls[x]}
    changed_orig={x for x in new if new[x]!=original[x]}
    class_orig={x for x in new_cls if new_cls[x]!=gold_cls[x]}
    if changed!=NEW_SRC or changed_class!=NEW_CLS:
        raise Refused("R410_EXACT_TWO_SOURCE_TWO_CLASS_REQUIRED")
    if changed_orig!=GOLD_SRC or class_orig!=GOLD_CLS:
        raise Refused("R410_PINNED_GOLDEN_SIX_SOURCE_EIGHT_CLASS_DRIFT")
    flags=check_structure(
        old[MOVER],new[MOVER],old[STORE],new[STORE],
        new[CACHE],old[CACHE])
    return {
        "status":"R410_PRIVATE_STRICT_HISTORY_ATOMIC_GATE_PASS",
        "java_source_count":len(new),
        "compiled_class_count":len(new_cls),
        "modified_sources_vs_r407":len(changed),
        "modified_classes_vs_r407":len(changed_class),
        **flags,
        "private_client_executed":False,
        "production_history_modified":False,
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
    p.add_argument("--expected-classes",type=int,default=1388)
    p.add_argument("--out",type=Path)
    a=p.parse_args(argv)
    try:
        if a.out and (a.out.exists() or a.out.is_symlink()):
            raise Refused("R410_REFUSE_EXISTING_REPORT")
        r=audit(kit=a.kit,kit_sha=a.kit_sha256,reference=a.reference,
                reference_sha=a.reference_sha256,
                previous_sources=a.previous_sources,previous_classes=a.previous_classes,
                candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
                expected_sources=a.expected_sources,expected_classes=a.expected_classes)
        data=json.dumps(r,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as f:f.write(data)
        else:print(data,end="")
        return 0
    except (Refused,ValueError,OSError) as e:
        print(json.dumps({"status":"R410_REFUSED",
                          "reason":str(e) if isinstance(e,Refused) else "INPUT_OR_FS_ERROR"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
