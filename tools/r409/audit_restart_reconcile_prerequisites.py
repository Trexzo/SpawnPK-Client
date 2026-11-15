#!/usr/bin/env python3
"""R409 public-safe, SHA-pinned read-only audit of private restart prerequisites.

Inspects only named source paths and full archive/class scope, outputs no
recovered code, player records, private binary, account data, or JAR.
Explicitly reports that non-atomic fallback and absent durable journal
BLOCK the use of the R409 synthetic recovery protocol in the client.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

HELPER=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not HELPER.is_file():
    raise RuntimeError("Missing R395 public read-only archive helpers")
spec=importlib.util.spec_from_file_location("r409_r395",HELPER)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused
P="rs/plugins/loottracker/"
PLUGIN=P+"LootTrackerPlugin.java"
PANEL=P+"LootTrackerPanel.java"
ITEM=P+"LootTrackerItem.java"
RECORD=P+"LootTrackerRecord.java"
STORE=P+"LootHistoryStore.java"
MOVE=P+"AtomicFileReplace.java"
CHANGED_SOURCES={PLUGIN,PANEL,ITEM,RECORD,STORE}
CHANGED_CLASSES={
    P+"LootTrackerPlugin.class",P+"LootTrackerPanel.class",
    P+"LootTrackerRecord.class",P+"LootTrackerItem.class",
    P+"LootHistoryStore.class",P+"LootHistoryStore$RecordDto.class",
    P+"LootHistoryStore$ItemDto.class",
}

def require(text:str,token:str,reason:str)->None:
    if token not in text:raise Refused(reason)

def ordered(text:str,*tokens:str)->None:
    if not r395.ordered(text,*tokens):
        raise Refused("R409_SOURCE_RECEIPT_OR_FALLBACK_ORDER_DRIFT")

def block_from(text:str,signature:str)->str:
    start=text.find(signature)
    if start<0:raise Refused("R409_REQUIRED_METHOD_ABSENT")
    brace=text.find("{",start+len(signature))
    if brace<0:raise Refused("R409_BRACE_MISSING")
    return r393.braced_body(text,brace)

def inspect(plugin:bytes,store:bytes,mover:bytes)->dict:
    try:
        p=r393.mask_java(plugin.decode("utf8"))
        h_raw=store.decode("utf8")
        h=r393.mask_java(h_raw)
        m=r393.mask_java(mover.decode("utf8"))
    except UnicodeDecodeError as e:
        raise Refused("R409_UNREADABLE_SOURCE") from e

    require(h_raw,'FILE_NAME = "loot-history.json"',
            "R409_HISTORY_FILENAME_CHANGED")
    require(h,"FORMAT_VERSION = 1",
            "R409_JSON_HISTORY_VERSION_CHANGED")
    require(h,"MAX_HISTORY_BYTES = 64L * 1024L * 1024L",
            "R409_EXISTING_READ_CAP_CHANGED")
    read=r394.method_body(h,"loadForMerge")
    ordered(read,"if (!file.exists())",
            "new ArrayList<>()",
            "Files.newInputStream(file.toPath())",
            "GSON.a(reader, Document.class)",
            "if (document.version != FORMAT_VERSION)",
            "return records")
    if "reconcile" in read.lower() or "intent" in read.lower():
        raise Refused("R409_PRIVATE_RECONCILIATION_ALREADY_INTEGRATED")

    save=r394.method_body(h,"saveWithReceipt")
    require(h_raw,'FILE_NAME + ".tmp"',
            "R409_HISTORY_TEMP_NAMING_DRIFT")
    ordered(save,"new Document()",
            "document.version = FORMAT_VERSION",
            "RecordDto.from(record)",
            "Files.newOutputStream(temp.toPath())",
            "GSON.a(document, writer)",
            "AtomicFileReplace.move(temp, file)",
            "return true")
    if any(x in save for x in ("FileChannel", ".force(", "r409","delete.intent",
                              "COMMITTED_BEFORE_ACK","finishReceipt")):
        raise Refused("R409_STORE_DURABILITY_PROTOCOL_ALREADY_CHANGED")
    if save.count("AtomicFileReplace.move(temp, file)")!=1:
        raise Refused("R409_HISTORY_REPLACE_COUNT_DRIFT")

    move=block_from(m,"static void move(File temp, File target)")
    ordered(move,
        "StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE",
        "catch (AtomicMoveNotSupportedException e)",
        "Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING)",
        "return;")
    if "FileChannel" in move or ".force(" in move:
        raise Refused("R409_MOVE_HELPER_DURABILITY_CHANGED")
    if "AtomicMoveNotSupportedException" not in m:
        raise Refused("R409_ATOMIC_FALLBACK_NO_LONGER_PRESENT")
    if m.count("Files.move(temp.toPath(), target.toPath()")!=2:
        raise Refused("R409_MOVE_ATTEMPTS_STRUCTURE_DRIFT")

    deletion=r394.method_body(p,"r402ApplyPanelDeletion")
    ordered(deletion,"SwingUtilities.isEventDispatchThread()",
            "synchronized (r401FileGate)",
            "mutation.run()",
            "persistHistory()",
            "if (!r402EditWriteReceipt)")
    if "executor.execute(" in deletion or "r409" in deletion:
        raise Refused("R409_ASYNC_DELETE_ALREADY_INTEGRATED")
    shutdown=r394.method_body(p,"shutDown")
    require(shutdown,"persistHistory()","R409_SHUTDOWN_SAVE_CHANGED")
    restore=r394.method_body(p,"loadHistory")
    ordered(restore,"restoreStore.loadForMerge()","SwingUtilities.invokeLater(",
            "restorePanel.addRecords(stored)")
    if "r409" in restore or "intent" in restore.lower():
        raise Refused("R409_RESTART_JOURNAL_ALREADY_ADDED")
    clear=r394.method_body(p,"clearHistory")
    ordered(clear,"++r399SessionEpoch","r403AutosaveQueued = false",
            "r403AutosaveDirty = false",
            "historyStore.clearWithReceipt()",
            "panel.clearRecords()")

    return {
        "history_is_single_json_version_one_file":True,
        "history_bytes_written_to_temporary_file":True,
        "store_reports_success_after_move_helper":True,
        "atomic_move_is_attempted_first":True,
        "non_atomic_replace_fallback_present":True,
        "history_store_does_not_force_file_bytes_to_storage":True,
        "history_store_does_not_force_directory_metadata":True,
        "startup_load_does_not_reconcile_delete_intent":True,
        "confirmed_deletion_remains_synchronous_on_edt":True,
        "clear_all_and_shutdown_lifecycle_barriers_remain":True,
        "file_backed_synthetic_protocol_integrated":False,
        "durable_recovery_for_private_client_proven":False,
    }

def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          inspected_sources:Path,inspected_classes:Path,
          expected_sources:int=1277,expected_classes:int=1388)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    original=r395.read_zip_bytes(kit,"source/",".java")
    origcls=r395.read_zip_bytes(reference,"",".class")
    current=r395.read_tree_bytes(inspected_sources,".java")
    classes=r395.read_tree_bytes(inspected_classes,".class")
    if any(len(x)!=expected_sources for x in (original,current)):
        raise Refused("R409_SOURCE_COUNT_DRIFT")
    if any(len(x)!=expected_classes for x in (origcls,classes)):
        raise Refused("R409_CLASS_COUNT_DRIFT")
    if original.keys()!=current.keys() or origcls.keys()!=classes.keys():
        raise Refused("R409_SOURCE_CLASS_SET_DRIFT")
    if {n for n in current if current[n]!=original[n]}!=CHANGED_SOURCES:
        raise Refused("R409_R407_ORIGINAL_SOURCE_SCOPE_DRIFT")
    if {n for n in classes if classes[n]!=origcls[n]}!=CHANGED_CLASSES:
        raise Refused("R409_R407_ORIGINAL_CLASS_SCOPE_DRIFT")
    if current[MOVE]!=original[MOVE]:
        raise Refused("R409_UNEXPECTED_ATOMIC_MOVE_HELPER_MUTATION")
    results=inspect(current[PLUGIN],current[STORE],current[MOVE])
    return {
        "status":"R409_PRIVATE_RESTART_DURABILITY_GAPS_CONFIRMED",
        "inspected_source_count":len(current),
        "inspected_class_count":len(classes),
        "changed_source_count_vs_r381":len(CHANGED_SOURCES),
        "changed_class_count_vs_r381":len(CHANGED_CLASSES),
        **results,
        "private_source_changed_for_r409":False,
        "private_binary_built_for_r409":False,
        "actual_client_executed":False,
        "cross_process_writer_lock_verified":False,
        "directory_fsync_supported_on_all_platforms":False,
        "power_loss_durability_verified":False,
        "private_release_authorized":False,
        "merge_approved":False,
    }

def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("kit","reference","inspected-sources","inspected-classes"):
        parser.add_argument("--"+name,required=True,type=Path)
    parser.add_argument("--kit-sha256",required=True)
    parser.add_argument("--reference-sha256",required=True)
    parser.add_argument("--expected-sources",type=int,default=1277)
    parser.add_argument("--expected-classes",type=int,default=1388)
    parser.add_argument("--out",type=Path)
    a=parser.parse_args(argv)
    try:
        if a.out and (a.out.is_symlink() or a.out.exists()):
            raise Refused("R409_REFUSE_EXISTING_REPORT")
        result=audit(
            kit=a.kit,kit_sha=a.kit_sha256,reference=a.reference,
            reference_sha=a.reference_sha256,
            inspected_sources=a.inspected_sources,
            inspected_classes=a.inspected_classes,
            expected_sources=a.expected_sources,expected_classes=a.expected_classes)
        encoded=json.dumps(result,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as f:f.write(encoded)
        else:print(encoded,end="")
        return 0
    except (Refused,OSError,ValueError) as e:
        print(json.dumps({
            "status":"R409_REFUSED",
            "reason":str(e) if isinstance(e,Refused) else "INPUT_OR_FS_ERROR"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
