#!/usr/bin/env python3
"""R404 read-only SHA-pinned checker for owner-private atomic item DTO snapshots.

Public-safe: prints only generic scope metadata, never private Java,
loot histories, dependencies, player records or source text.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

PRIOR=Path(__file__).resolve().parents[1]/"r395"/"audit_private_candidate_delta.py"
if not PRIOR.is_file():
    raise RuntimeError("Missing inherited R395 read-only archive support")
spec=importlib.util.spec_from_file_location("r404_r395",PRIOR)
r395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
r393,r394=r395.r393,r395.r394
Refused=r395.Refused
PREFIX="rs/plugins/loottracker/"
PLUGIN=PREFIX+"LootTrackerPlugin.java"
ITEM=PREFIX+"LootTrackerItem.java"
STORE=PREFIX+"LootHistoryStore.java"
PANEL=PREFIX+"LootTrackerPanel.java"
SOURCE_CHANGED={PLUGIN,ITEM,STORE}
GOLD_SOURCE_CHANGED=SOURCE_CHANGED|{PANEL}
CLASS_CHANGED={
    PREFIX+"LootHistoryStore$ItemDto.class",
    PREFIX+"LootHistoryStore$RecordDto.class",
    PREFIX+"LootTrackerItem.class",
    PREFIX+"LootTrackerPlugin.class",
}
GOLD_CLASS_CHANGED=CLASS_CHANGED|{
    PREFIX+"LootHistoryStore.class",
    PREFIX+"LootTrackerPanel.class",
}


def require(block:str,token:str,reason:str):
    if token not in block:raise Refused(reason)


def in_order(block:str,*tokens:str):
    if not r395.ordered(block,*tokens):
        raise Refused("R404_MUTATION_OR_SNAPSHOT_ORDER_DRIFT")


def method_after(source:str,marker:str)->str:
    if source.count(marker)!=1:
        raise Refused("R404_METHOD_SCOPE_DRIFT")
    i=source.index(marker)
    at=source.find("{",i+len(marker))
    if at<0:raise Refused("R404_METHOD_BODY_MISSING")
    return r393.braced_body(source,at)


def check_structure(item_bytes:bytes,store_bytes:bytes,plugin_bytes:bytes)->dict:
    try:
        item=r393.mask_java(item_bytes.decode("utf8"))
        store=r393.mask_java(store_bytes.decode("utf8"))
        plugin=r393.mask_java(plugin_bytes.decode("utf8"))
    except UnicodeDecodeError as e:
        raise Refused("R404_NON_UTF8_SOURCE") from e

    for name,type_name in (("setName","String"),("setPrice","long"),
                           ("setIgnored","boolean")):
        pattern=r"\bsynchronized\s+void\s+"+name+r"\s*\(\s*"+type_name+r"\s+\w+\s*\)"
        if not re.search(pattern,item):
            raise Refused("R404_ITEM_MUTATOR_MUST_BE_SYNCHRONIZED")
    if not re.search(r"\bsynchronized\s+void\s+r404ApplyDefinition\s*\(\s*String\s+\w+\s*,\s*long\s+\w+\s*\)",item):
        raise Refused("R404_ATOMIC_DEFINITION_METHOD_REQUIRED")
    apply=method_after(item,"void r404ApplyDefinition(String newName, long newPrice)")
    for needle,reason in (
        ("if (newName != null)","R404_NULL_DEFINITION_NAME_MUST_BE_NOOP"),
        ("name = newName;","R404_DEFINITION_NAME_NOT_UPDATED"),
        ("if (newPrice > 0 || price <= 0)","R404_NOMINAL_PRICE_POLICY_CHANGED"),
        ("price = newPrice;","R404_DEFINITION_PRICE_NOT_UPDATED")):
        require(apply,needle,reason)
    in_order(apply,"if (newName != null)","name = newName;",
             "if (newPrice > 0 || price <= 0)","price = newPrice;")
    if "synchronized (r401FileGate)" in apply or "synchronized (r395HistoryGate)" in apply:
        raise Refused("R404_ITEM_REFRESH_NESTS_PLUGIN_FILE_OR_HISTORY_GATE")

    convert=method_after(store,"static RecordDto from(LootTrackerRecord record)")
    in_order(convert,
        "LootTrackerItem[] capturedItems = record.getItems().clone()",
        "new ArrayList<>(capturedItems.length)",
        "for (LootTrackerItem item : capturedItems)",
        "ItemDto.from(item)")
    if convert.count("record.getItems()")!=1:
        raise Refused("R404_RECORD_ITEMS_READ_MULTIPLE_TIMES")

    dto=method_after(store,"static ItemDto from(LootTrackerItem item)")
    in_order(dto,"if (item == null)","synchronized (item)",
             "dto.id = item.getId()",
             "dto.name = item.getName()",
             "dto.quantity = item.getQuantity()",
             "dto.price = item.getPrice()",
             "dto.hidden = item.isIgnored()",
             "return dto;")
    sync_start=dto.find("synchronized (item)")
    if sync_start<0:raise Refused("R404_DTO_ITEM_MONITOR_MISSING")
    locked=r393.braced_body(dto,dto.find("{",sync_start))
    for token in (
        "dto.id = item.getId()",
        "dto.name = item.getName()",
        "dto.quantity = item.getQuantity()",
        "dto.price = item.getPrice()",
        "dto.hidden = item.isIgnored()",
        "return dto;"):
        require(locked,token,"R404_DTO_FIELD_READ_ESCAPES_ITEM_MONITOR")
    if dto.count("synchronized (item)")!=1:
        raise Refused("R404_DTO_ITEM_MONITOR_SCOPE_DRIFT")
    if "synchronized (r401FileGate)" in locked or "synchronized (r395HistoryGate)" in locked:
        raise Refused("R404_DTO_CANNOT_NEST_PLUGIN_GATES")

    reload=r394.method_body(plugin,"reloadRecordedPrices")
    in_order(reload,
        "SwingUtilities.invokeLater(",
        "panel.getAllRecords()",
        "ItemDefinition def = safeDefinition(item.getId())",
        "String r404Name",
        "long price = priceOf(item.getId(), def)",
        "item.r404ApplyDefinition(r404Name, price)",
        "requestSave()")
    if "item.setName(" in reload or "item.setPrice(" in reload:
        raise Refused("R404_SPLIT_NAME_PRICE_REFRESH_REINTRODUCED")
    if reload.count("item.r404ApplyDefinition(")!=1:
        raise Refused("R404_NAME_PRICE_REFRESH_COUNT_DRIFT")
    if not re.search(
        r"String\s+r404Name\s*=\s*def\.name\s*!=\s*null\s*&&\s*!def\.name\.isEmpty\(\)",
        reload):
        raise Refused("R404_EMPTY_DEFINITION_NAME_POLICY_CHANGED")
    save=r394.method_body(plugin,"persistHistory")
    queue=r394.method_body(plugin,"r403QueueAutosave")
    require(save,"historyStore.saveWithReceipt(merged)","R404_STORE_RECEIPT_REGRESSION")
    require(queue,"executor.execute(","R404_WORKER_REGRESSION")
    return {
        "per_item_name_price_hidden_dto_snapshot_atomic":True,
        "definition_name_and_price_single_mutation":True,
        "item_array_reference_list_captured_once":True,
        "original_price_fallback_rule_preserved":True,
        "edt_definition_refresh_and_worker_retained":True,
        "no_nested_plugin_gates_introduced":True,
        "cross_record_atomic_snapshot_not_proven":True,
        "real_edt_runtime_not_executed":True,
    }


def audit(*,kit:Path,kit_sha:str,reference:Path,reference_sha:str,
          previous_sources:Path,previous_classes:Path,
          candidate_sources:Path,candidate_classes:Path,
          expected_sources:int=1277,expected_classes:int=1388)->dict:
    r395.require_pin(kit,kit_sha)
    r395.require_pin(reference,reference_sha)
    golden=r395.read_zip_bytes(kit,"source/",".java")
    old=r395.read_tree_bytes(previous_sources,".java")
    new=r395.read_tree_bytes(candidate_sources,".java")
    gold_classes=r395.read_zip_bytes(reference,"",".class")
    prior_classes=r395.read_tree_bytes(previous_classes,".class")
    new_classes=r395.read_tree_bytes(candidate_classes,".class")
    if any(len(tree)!=expected_sources for tree in (golden,old,new)):
        raise Refused("R404_SOURCE_FILE_COUNT_DRIFT")
    if any(len(tree)!=expected_classes for tree in (gold_classes,prior_classes,new_classes)):
        raise Refused("R404_CLASS_FILE_COUNT_DRIFT")
    if not (golden.keys()==old.keys()==new.keys()):
        raise Refused("R404_SOURCE_FILE_SET_DRIFT")
    if not (gold_classes.keys()==prior_classes.keys()==new_classes.keys()):
        raise Refused("R404_CLASS_FILE_SET_DRIFT")
    source_changed={x for x in new if new[x]!=old[x]}
    class_changed={x for x in new_classes if new_classes[x]!=prior_classes[x]}
    gold_src_changed={x for x in new if new[x]!=golden[x]}
    gold_cls_changed={x for x in new_classes if new_classes[x]!=gold_classes[x]}
    if source_changed!=SOURCE_CHANGED or class_changed!=CLASS_CHANGED:
        raise Refused("R404_THREE_SOURCE_FOUR_CLASS_SCOPE_DRIFT")
    if gold_src_changed!=GOLD_SOURCE_CHANGED or gold_cls_changed!=GOLD_CLASS_CHANGED:
        raise Refused("R404_GOLDEN_FOUR_SOURCE_SIX_CLASS_SCOPE_DRIFT")
    evidence=check_structure(new[ITEM],new[STORE],new[PLUGIN])
    return {
        "status":"R404_PRIVATE_ITEM_SNAPSHOT_STATIC_GATE_PASS",
        "java_source_count":len(new),
        "compiled_class_count":len(new_classes),
        "changed_source_count_vs_r403":len(source_changed),
        "changed_class_count_vs_r403":len(class_changed),
        **evidence,
        "actual_private_client_executed":False,
        "real_thread_schedule_verified":False,
        "complete_panel_record_snapshot_atomic":False,
        "cross_process_writes_locked":False,
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
    p.add_argument("--expected-classes",type=int,default=1388)
    p.add_argument("--out",type=Path)
    a=p.parse_args(argv)
    try:
        if a.out and (a.out.exists() or a.out.is_symlink()):
            raise Refused("R404_REFUSE_EXISTING_RECEIPT")
        result=audit(
            kit=a.kit,kit_sha=a.kit_sha256,
            reference=a.reference,reference_sha=a.reference_sha256,
            previous_sources=a.previous_sources,previous_classes=a.previous_classes,
            candidate_sources=a.candidate_sources,candidate_classes=a.candidate_classes,
            expected_sources=a.expected_sources,expected_classes=a.expected_classes)
        text=json.dumps(result,sort_keys=True,indent=2)+"\n"
        if a.out:
            with a.out.open("x",encoding="utf8") as f:f.write(text)
        else:print(text,end="")
        return 0
    except (Refused,OSError,ValueError) as e:
        why=str(e) if isinstance(e,Refused) else "INPUT_OR_FILESYSTEM_ERROR"
        print(json.dumps({"status":"R404_REFUSED","reason":why}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
