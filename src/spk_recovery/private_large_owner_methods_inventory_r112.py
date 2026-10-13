"""R112: private, SHA-pinned v309 outstanding 364/697-method inventory.

Original executable member symbols and literals remain in PRIVATE output only.
Aggregate reports instruction/branch/invocation/field/indy counts to support
source reconstruction; never claims inferred Java expressions or R94 success.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from zipfile import ZipFile

from .bytecode_profile import profile_jar_class
from .private_original_fourth_enum_accessors import digest


class TwoLargeOwnerMethodInventoryError(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise TwoLargeOwnerMethodInventoryError(code)


BRANCHES = frozenset({
    "0x99","0x9a","0x9b","0x9c","0x9d","0x9e","0x9f","0xa0",
    "0xa1","0xa2","0xa3","0xa4","0xa5","0xa6","0xa7","0xa8",
    "0xc6","0xc7","0xc8","0xc9",
})
CALLS = frozenset({"0xb6","0xb7","0xb8","0xb9","0xba"})
FIELDS = frozenset({"0xb2","0xb3","0xb4","0xb5"})
RETURNS = frozenset({"0xac","0xad","0xae","0xaf","0xb0","0xb1"})
SWITCHES = frozenset({"0xaa","0xab"})


def unique_unrecovered(profile):
    fields = profile.get("fields")
    methods = profile.get("methods")
    need(profile.get("classfile_major") == 53
         and isinstance(fields, list) and len(fields) == 126
         and isinstance(methods, list) and len(methods) == 10,
         "ORIGINAL_V309_126FIELD_TENMETHOD_OWNER_REQUIRED")
    counts = [len(x.get("instructions", [])) for x in methods]
    need(sorted(counts)==[2,2,2,3,4,20,41,213,364,697],
         "ORIGINAL_V309_TEN_METHOD_INSTRUCTION_DISTRIBUTION_CHANGED")
    found = {}
    for wanted in (364,697):
        matches = [m for m in methods if len(m.get("instructions",[]))==wanted]
        need(len(matches)==1 and matches[0].get("descriptor")=="()V",
             "EXACT_ONE_ORIGINAL_VOID_LARGE_OWNER_METHOD_REQUIRED")
        m=matches[0]
        need(isinstance(m.get("name"),str)
             and m.get("name") not in ("<init>","<clinit>")
             and isinstance(m.get("instructions"),list)
             and all(isinstance(x,dict)
                     and isinstance(x.get("opcode"),str)
                     and type(x.get("offset")) is int
                     for x in m["instructions"]),
             "ORIGINAL_LARGE_METHOD_CODE_OR_SIGNATURE_INVALID")
        found[wanted]=m
    return found


def method_inventory(method):
    rows = method["instructions"]
    opcodes=[r["opcode"] for r in rows]
    counts=Counter(opcodes)
    offsets={r["offset"]:i for i,r in enumerate(rows)}
    need(len(offsets)==len(rows)
         and list(offsets)==sorted(offsets),
         "ORIGINAL_LARGE_METHOD_OFFSETS_NOT_UNIQUE_ORDERED")
    branches=[]
    for i,r in enumerate(rows):
        if r["opcode"] in BRANCHES:
            target=r.get("branch_target_offset")
            need(type(target) is int and target in offsets,
                 "LARGE_METHOD_BRANCH_TARGET_UNRESOLVED")
            branches.append((i,offsets[target]))
    indy=[r for r in rows if r["opcode"]=="0xba"]
    need(all(type(x.get("bootstrap_method_attr_index")) is int
             and isinstance(x.get("name"),str)
             and isinstance(x.get("descriptor"),str)
             for x in indy),
         "LARGE_METHOD_INVOKEDYNAMIC_UNRESOLVED")
    calls=[r for r in rows if r["opcode"] in CALLS]
    fields=[r for r in rows if r["opcode"] in FIELDS]
    need(all(all(isinstance(x.get(f),str) for f in
                 ("owner","name","descriptor"))
             for x in calls if x["opcode"]!="0xba")
         and all(all(isinstance(x.get(f),str) for f in
                     ("owner","name","descriptor")) for x in fields),
         "LARGE_METHOD_SYMBOLIC_MEMBER_OPERANDS_UNRESOLVED")
    kinds={
        "method_jvm_instructions":len(rows),
        "explicit_branch_sites":len(branches),
        "method_invocation_sites":len(calls),
        "invokedynamic_sites":len(indy),
        "field_reference_sites":len(fields),
        "field_read_sites":sum(counts[k] for k in ("0xb2","0xb4")),
        "field_write_sites":sum(counts[k] for k in ("0xb3","0xb5")),
        "return_sites":sum(counts[k] for k in RETURNS),
        "switch_sites":sum(counts[k] for k in SWITCHES),
        "ordered_typed_exception_handlers":len(method.get("exception_handlers") or []),
        "max_stack":method.get("max_stack"),
        "max_locals":method.get("max_locals"),
        "private_operand_map_sha256":hashlib.sha256(
            json.dumps(rows,sort_keys=True,separators=(",",":"))
            .encode("utf-8")).hexdigest(),
    }
    need(type(kinds["max_stack"]) is int
         and type(kinds["max_locals"]) is int
         and kinds["return_sites"]>=1,
         "LARGE_METHOD_STACK_LOCAL_OR_RETURN_MISSING")
    return kinds, {"method_name":method["name"],
                   "descriptor":method["descriptor"],
                   "access":method["access"],
                   "instructions":rows,
                   "exception_handlers":method.get("exception_handlers"),
                   "symbolic_bootstrap_ids":sorted({
                       r["bootstrap_method_attr_index"] for r in indy}),
                   "branch_ordinal_edges":branches}


def inventory_two_original_methods(original_jar,owner_entry,output,*,
                                   original_sha256):
    original_jar,output=Path(original_jar),Path(output)
    need(not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "FRESH_PRIVATE_LARGE_METHOD_REPORT_REQUIRED")
    need(isinstance(original_sha256,str)
         and re.fullmatch(r"[A-Fa-f0-9]{64}",original_sha256)
         and original_jar.is_file() and not original_jar.is_symlink()
         and digest(original_jar)==original_sha256.lower(),
         "ORIGINAL_COMPLETE_JAR_SHA256_MISMATCH")
    need(isinstance(owner_entry,str) and owner_entry.endswith(".class")
         and not owner_entry.startswith("/") and "\\" not in owner_entry
         and all(p not in ("",".","..") for p in owner_entry.split("/")),
         "ORIGINAL_OWNER_ARCHIVE_ENTRY_UNSAFE")
    with ZipFile(original_jar) as z:
        need(z.namelist().count(owner_entry)==1,
             "ORIGINAL_OWNER_ARCHIVE_ENTRY_NOT_UNIQUE")
    profile=profile_jar_class(original_jar,owner_entry)
    need(profile.get("internal_name")+".class"==owner_entry,
         "ORIGINAL_OWNER_INTERNAL_IDENTITY_MISMATCH")
    methods=unique_unrecovered(profile)
    summary={}
    private={}
    for length,method in sorted(methods.items()):
        counts,detail=method_inventory(method)
        summary[str(length)]=counts
        private[str(length)]=detail
    need(digest(original_jar)==original_sha256.lower(),
         "ORIGINAL_JAR_CHANGED_DURING_PRIVATE_INVENTORY")
    report={"schema_version":1,
            "kind":"original_v309_364_697_method_source_frontier",
            "original_complete_jar_sha256":original_sha256.lower(),
            "original_owner_fields":126,
            "original_owner_methods":10,
            "source_reconstructed_ordinary_methods":7,
            "unrecovered_original_large_methods":2,
            "unrecovered_method_inventory":summary,
            "original_large_java_source_reconstructed":False,
            "R94_R107_owner_parity_certified":False,
            "original_helper_runtime_equivalence_certified":False}
    with tempfile.TemporaryDirectory(prefix="v309-r112-",dir=output.parent) as tmp:
        dest=Path(tmp)/"accepted"
        dest.mkdir()
        (dest/"large-original-methods.PRIVATE.json").write_text(
            json.dumps(private,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        (dest/"large-methods.aggregate.json").write_text(
            json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        need(not output.exists(),"OUTPUT_OCCUPIED_AFTER_PRIVATE_VERIFICATION")
        os.rename(dest,output)
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("original_jar","original_owner_entry","new_private_output"):
        p.add_argument(name)
    p.add_argument("--original-sha256",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(inventory_two_original_methods(
            a.original_jar,a.original_owner_entry,a.new_private_output,
            original_sha256=a.original_sha256),sort_keys=True))
    except (TwoLargeOwnerMethodInventoryError,ValueError,OSError,
            KeyError,TypeError,IndexError):
        p.error("ORIGINAL_V309_364_697_PRIVATE_SOURCE_FRONTIER_REJECTED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
