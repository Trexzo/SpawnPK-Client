#!/usr/bin/env python3
"""R405 public-safe, SHA-pinned, read-only private source/class static gate.

The checker reports only structural booleans and counts. It never executes
private classes, prints private sources, reads player history or modifies files.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

PRIOR=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not PRIOR.exists(): raise RuntimeError("Missing inherited R395 public archive helper")
spec=importlib.util.spec_from_file_location("r405_r395",PRIOR)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused

P="rs/plugins/loottracker/"
ITEM=P+"LootTrackerItem.java"
RECORD=P+"LootTrackerRecord.java"
PANEL=P+"LootTrackerPanel.java"
PLUGIN=P+"LootTrackerPlugin.java"
STORE=P+"LootHistoryStore.java"
CHANGED_SRC={ITEM,RECORD,PANEL,PLUGIN}
CHANGED_CLS={p[:-5]+".class" for p in CHANGED_SRC}
GOLD_SRC=CHANGED_SRC|{STORE}
GOLD_CLS=CHANGED_CLS|{
    P+"LootHistoryStore.class",P+"LootHistoryStore$RecordDto.class",
    P+"LootHistoryStore$ItemDto.class",
}

def require(source:str,needle:str,reason:str):
    if needle not in source:raise Refused(reason)

def ordered(source:str,*terms:str):
    if not r395.ordered(source,*terms):
        raise Refused("R405_CRITICAL_SOURCE_ORDER_DRIFT")

def braced_after(text:str,needle:str):
    idx=text.find(needle)
    if idx<0:raise Refused("R405_EXPECTED_BLOCK_MISSING")
    brace=text.find("{",idx+len(needle))
    if brace<0:raise Refused("R405_EXPECTED_OPEN_BRACE_MISSING")
    return r393.braced_body(text,brace)

def check_structure(*,item:bytes,record:bytes,panel:bytes,plugin:bytes)->dict:
    try:
        i=r393.mask_java(item.decode("utf8"))
        r=r393.mask_java(record.decode("utf8"))
        p=r393.mask_java(panel.decode("utf8"))
        u=r393.mask_java(plugin.decode("utf8"))
    except UnicodeDecodeError as e:
        raise Refused("R405_NON_UTF8_SOURCE") from e

    if not re.search(r"\bsynchronized\s+LootTrackerItem\s+r405FrozenCopy\s*\(\s*\)",i):
        raise Refused("R405_ITEM_FREEZE_MUST_USE_ITEM_MONITOR")
    item_copy=r394.method_body(i,"r405FrozenCopy")
    ordered(item_copy,"new LootTrackerItem(", "id, name, quantity, price, ignored")
    if "return this" in item_copy:
        raise Refused("R405_ITEM_FREEZE_MUST_NOT_ALIAS")
    for label in ("setName","setPrice","setIgnored","r404ApplyDefinition"):
        if not re.search(r"\bsynchronized\s+void\s+"+label+r"\s*\(",i):
            raise Refused("R405_ITEM_MUTATOR_MONITOR_DRIFT")

    record_copy=r394.method_body(r,"r405FrozenCopy")
    ordered(record_copy,
        "LootTrackerItem[] references = items.clone()",
        "new LootTrackerItem[references.length]",
        "for (int i = 0; i < references.length; ++i)",
        "if (references[i] == null)",
        "frozen[i] = references[i].r405FrozenCopy()",
        "new LootTrackerRecord(title, subTitle, type, frozen, kills, timestamp)")
    if record_copy.count("items.clone()")!=1:
        raise Refused("R405_RECORD_ITEMS_ARRAY_READ_COUNT_DRIFT")
    if "getCountedKills()" in record_copy:
        raise Refused("R405_MUST_PRESERVE_RAW_KILL_COUNT")

    if not re.search(r"\bsynchronized\s+Collection<LootTrackerRecord>\s+r405FrozenRecords\s*\(\s*\)",p):
        raise Refused("R405_PANEL_FREEZE_MUST_USE_CANONICAL_PANEL_MONITOR")
    panel_copy=r394.method_body(p,"r405FrozenRecords")
    ordered(panel_copy,
        "new ArrayList<>(records.size())",
        "for (LootTrackerRecord record : records)",
        "if (record == null)",
        "frozen.add(record.r405FrozenCopy())",
        "return frozen;")
    if any(x in panel_copy for x in ("persistHistory(", "invokeAndWait(","r401FileGate","r395HistoryGate")):
        raise Refused("R405_PANEL_SNAPSHOT_MUST_NOT_BLOCK_ON_FILE_OR_CLIENT_GATE")

    price=r394.method_body(u,"reloadRecordedPrices")
    if price.count("synchronized (panel)")!=1:
        raise Refused("R405_PRICE_BATCH_MUST_OWN_PANEL_MONITOR")
    price_lock=braced_after(price,"synchronized (panel)")
    ordered(price_lock,
        "for (LootTrackerRecord record : panel.getAllRecords())",
        "for (LootTrackerItem item : record.getItems())",
        "ItemDefinition def = safeDefinition(item.getId())",
        "item.r404ApplyDefinition(r404Name, price)")
    if "panel.rebuild()" in price_lock:
        raise Refused("R405_PANEL_RENDER_INSIDE_BATCH_LOCK")
    if "item.setName(" in price or "item.setPrice(" in price:
        raise Refused("R405_PRICE_MUTATION_REINTRODUCED_SPLIT_WRITES")
    ordered(price,"SwingUtilities.invokeLater(", "synchronized (panel)", "panel.rebuild()", "requestSave()")

    ignore=r394.method_body(p,"updateIgnoredRecords")
    require(ignore,"synchronized (this)","R405_IGNORED_BATCH_MONITOR_REGRESSION")
    lock=braced_after(ignore,"synchronized (this)")
    ordered(lock,
        "for (LootTrackerRecord record : records)",
        "applyIgnored(record, ignored)")
    if "recountAggregates()" in lock or "rebuild()" in lock:
        raise Refused("R405_IGNORED_RENDER_UNDER_PANEL_MONITOR_REGRESSION")

    save=r394.method_body(u,"persistHistory")
    if "panel.getRecordsOffEdt()" in save:
        raise Refused("R405_WRITER_STILL_READS_LIVE_PANEL_RECORDS")
    ordered(save,
        "r400Before = r400PanelHandoffVersion",
        "panel.r405FrozenRecords()",
        "r400ConsistentPending = new ArrayList<>(pendingRecords)",
        "new ArrayList<>(r400ConsistentPending.size())",
        "for (LootTrackerRecord pending : r400ConsistentPending)",
        "r405FrozenPending.add(pending.r405FrozenCopy())",
        "synchronized (r395HistoryGate)",
        "r400Before != r400PanelHandoffVersion",
        "r400ConsistentMerged = new ArrayList<>(stored)",
        "r400ConsistentMerged.addAll(r405FrozenPending)",
        "synchronized (r401FileGate)",
        "historyStore.saveWithReceipt(merged)")
    if save.count("r400Before != r400PanelHandoffVersion")<2:
        raise Refused("R405_PENDING_CLONE_REQUIRES_SECOND_HANDOFF_RECHECK")
    if save.count("r401ConsistentClearGeneration != r401ClearGeneration")<2:
        raise Refused("R405_PENDING_CLONE_REQUIRES_SECOND_CLEAR_RECHECK")
    if save.count("r405FrozenPending.add(pending.r405FrozenCopy())")!=1:
        raise Refused("R405_PENDING_DEEP_SNAPSHOT_REQUIRED")
    if save.count("panel.r405FrozenRecords()")!=1:
        raise Refused("R405_SINGLE_PANEL_SNAPSHOT_REQUIRED")
    file_gate=braced_after(save,"synchronized (r401FileGate)")
    require(file_gate,"historyStore.saveWithReceipt(merged)","R405_FILE_GATE_ACKNOWLEDGED_COMMIT_REQUIRED")
    if "panel.r405FrozenRecords()" in file_gate or "r405FrozenPending" in file_gate:
        raise Refused("R405_MUST_FREEZE_RECORDS_OUTSIDE_FILE_GATE")
    return {
        "item_and_record_deep_snapshots":True,
        "panel_batch_prices_share_snapshot_monitor":True,
        "ignored_batch_shares_snapshot_monitor":True,
        "freeze_does_not_wait_for_edt_or_file_gate":True,
        "pending_snapshot_rechecks_handoff_and_clear_generation":True,
        "disk_uses_frozen_record_values":True,
        "does_not_prove_cross_process_or_live_edt_schedule":True,
    }

def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,expected_classes:int=1388)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    golden=r395.read_zip_bytes(kit,"source/",".java")
    previous=r395.read_tree_bytes(previous_sources,".java")
    candidate=r395.read_tree_bytes(candidate_sources,".java")
    gold_cls=r395.read_zip_bytes(reference,"",".class")
    prev_cls=r395.read_tree_bytes(previous_classes,".class")
    cand_cls=r395.read_tree_bytes(candidate_classes,".class")
    if any(len(x)!=expected_sources for x in (golden,previous,candidate)):
        raise Refused("R405_SOURCE_FILE_COUNT_DRIFT")
    if any(len(x)!=expected_classes for x in (gold_cls,prev_cls,cand_cls)):
        raise Refused("R405_CLASS_FILE_COUNT_DRIFT")
    if golden.keys()!=previous.keys() or previous.keys()!=candidate.keys():
        raise Refused("R405_SOURCE_SET_DRIFT")
    if gold_cls.keys()!=prev_cls.keys() or prev_cls.keys()!=cand_cls.keys():
        raise Refused("R405_CLASS_SET_DRIFT")
    sources={x for x in candidate if candidate[x]!=previous[x]}
    classes={x for x in cand_cls if cand_cls[x]!=prev_cls[x]}
    from_orig={x for x in candidate if candidate[x]!=golden[x]}
    from_orig_cls={x for x in cand_cls if cand_cls[x]!=gold_cls[x]}
    if sources!=CHANGED_SRC or classes!=CHANGED_CLS:
        raise Refused("R405_FOUR_SOURCE_CLASS_SCOPE_DRIFT")
    if from_orig!=GOLD_SRC or from_orig_cls!=GOLD_CLS:
        raise Refused("R405_GOLDEN_FIVE_SOURCE_SEVEN_CLASS_SCOPE_DRIFT")
    checks=check_structure(
        item=candidate[ITEM],record=candidate[RECORD],
        panel=candidate[PANEL],plugin=candidate[PLUGIN])
    return {
        "status":"R405_PRIVATE_FROZEN_PANEL_STATIC_GATE_PASS",
        "java_source_count":len(candidate),
        "compiled_class_count":len(cand_cls),
        "modified_source_count_vs_r404":4,
        "modified_class_count_vs_r404":4,
        **checks,
        "private_runtime_executed":False,
        "real_edt_file_lock_latency_measured":False,
        "every_possible_record_mutation_serialized":False,
        "all_cross_item_updates_atomic":False,
        "cross_process_writes_locked":False,
        "power_loss_durability_proven":False,
        "private_source_release_authorized":False,
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
            raise Refused("R405_REFUSE_EXISTING_RECEIPT")
        report=audit(
            kit=a.kit,kit_sha=a.kit_sha256,
            reference=a.reference,reference_sha=a.reference_sha256,
            previous_sources=a.previous_sources,previous_classes=a.previous_classes,
            candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
            expected_sources=a.expected_sources,expected_classes=a.expected_classes)
        data=json.dumps(report,indent=2,sort_keys=True)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as f:f.write(data)
        else:print(data,end="")
        return 0
    except (Refused,ValueError,OSError) as e:
        print(json.dumps({
            "status":"R405_REFUSED",
            "reason":str(e) if isinstance(e,Refused) else "INPUT_OR_FS_FAILURE"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
