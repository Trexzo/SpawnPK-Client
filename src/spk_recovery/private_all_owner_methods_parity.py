"""R94: all nine ordinary v309 owner methods match one compiled candidate.

R58 verifies <clinit> separately. R94 applies existing R66+R81 to every
other original method (constructor, six helper/boolean/array/callback forms,
697-op loader and 364-op saver) with exact same-owner field identities.
No runtime, nested class or external dependency equivalence implied.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .clinit_store_order_witness import _verified_class
from .large_method_cfg_parity import _static_writes
from .mutable_scalar_initializer_source import _digest
from .whole_method_operand_parity import (
    WholeMethodOperandError, compare_all_method_operands,
)

class AllOwnerMethodsParityError(ValueError):
    pass

def need(ok,code):
    if not ok:raise AllOwnerMethodsParityError(code)

def unique_methods(profile):
    rows=profile.get("methods")
    need(isinstance(rows,list),"OWNER_METHOD_TABLE_MISSING")
    out={}
    for m in rows:
        need(isinstance(m,dict)
             and isinstance(m.get("name"),str)
             and isinstance(m.get("descriptor"),str),
             "ORIGINAL_OR_CANDIDATE_METHOD_DECLARATION_INVALID")
        key=(m["name"],m["descriptor"])
        need(key not in out,"OWNER_METHOD_DECLARATION_DUPLICATE")
        out[key]=m
    return out

def prove_all_original_nonclinit_methods(
    original,candidate,*,expected_owner_method_counts=None,
):
    need(original.get("internal_name")==candidate.get("internal_name"),
         "ORIGINAL_CANDIDATE_OWNER_NAME_DIFFERENT")
    a=unique_methods(original)
    b=unique_methods(candidate)
    need(set(a)==set(b) and len(a)==10
         and sum(k[0]=="<clinit>" for k in a)==1,
         "ORIGINAL_TEN_METHOD_DECLARATIONS_NOT_EXACT")
    ordinary=sorted(k for k in a if k[0]!="<clinit>")
    need(len(ordinary)==9,"NINE_ORIGINAL_ORDINARY_METHODS_NOT_PRESENT")
    lengths=sorted(len(a[k].get("instructions",[])) for k in a)
    if expected_owner_method_counts is not None:
        need(lengths==sorted(expected_owner_method_counts),
             "ORIGINAL_TEN_METHOD_INSTRUCTION_COUNTS_CHANGED")
    proved=[]
    for key in ordinary:
        ma,mb=a[key],b[key]
        original_rows=ma.get("instructions",[])
        writes=_static_writes(original,original_rows)
        own=original["internal_name"]
        aliases=[]
        fields=set()
        for owner,name,desc in writes:
            if owner==own and (name,desc) not in fields:
                fields.add((name,desc))
                aliases.append({
                    "original":{"name":name,"descriptor":desc},
                    "candidate":{"name":name,"descriptor":desc},
                })
        try:
            report=compare_all_method_operands(
                original,key[0],key[1],candidate,key[0],key[1],
                aliases,[],[])
        except (WholeMethodOperandError,ValueError,TypeError,KeyError,IndexError) as exc:
            raise AllOwnerMethodsParityError(
                "R66_R81_ORIGINAL_OWNER_ORDINARY_METHOD_PARITY_REJECTED") from exc
        need(report["original_instructions_with_all_semantic_operands_compared"]
             ==len(original_rows),
             "COMPLETE_METHOD_JVM_OPERAND_COVERAGE_NOT_PROVEN")
        proved.append(report)
    total=sum(x["original_instructions_with_all_semantic_operands_compared"]
              for x in proved)
    return {
        "original_owner_total_method_declarations":10,
        "original_ordinary_methods_parity_checked":9,
        "original_ordinary_jvm_instruction_operands_compared":total,
        "original_ordinary_exception_table_entries_checked":
            sum(x["original_ordered_typed_exception_entries"] for x in proved),
        "original_ordinary_explicit_branches_checked":
            sum(x["original_explicit_branches"] for x in proved),
        "original_ordinary_owner_static_writes_checked":
            sum(x["original_ordered_static_writes"] for x in proved),
        "original_exact_same_owner_member_names_required":True,
        "R66_and_R81_parity_passed_all_nine_ordinary_methods":True,
        "original_clinit_R58_parity_checked_by_this_tool":False,
        "original_owner_126_fields_parity_checked_by_this_tool":False,
        "original_nested_enum_or_external_dependency_behavior_proven":False,
        "whole_client_runtime_equivalence_certified":False,
    }

def replay_all_original_methods(
    original_jar,candidate_jar,original_entry,candidate_entry,out,
    *,original_sha256,candidate_sha256,
):
    original_jar,candidate_jar,out=map(
        Path,(original_jar,candidate_jar,out))
    need(not out.exists() and not out.is_symlink(),"OUTPUT_ALREADY_EXISTS")
    original=_verified_class(original_jar,original_entry,original_sha256)
    candidate=_verified_class(candidate_jar,candidate_entry,candidate_sha256)
    proof=prove_all_original_nonclinit_methods(
        original,candidate,
        expected_owner_method_counts=[2,2,2,3,4,20,41,213,364,697])
    need(_digest(original_jar)==original_sha256.lower()
         and _digest(candidate_jar)==candidate_sha256.lower(),
         "PINNED_ORIGINAL_OR_CANDIDATE_JAR_CHANGED_DURING_PROOF")
    aggregate={"schema_version":1,
               "kind":"private_v309_all_nine_ordinary_owner_methods_R66_R81",
               "original_complete_jar_sha256":original_sha256.lower(),
               "candidate_complete_jar_sha256":candidate_sha256.lower(),
               "research_only":True,**proof}
    out.mkdir(parents=True,exist_ok=False)
    (out/"all-owner-method-parity.aggregate.json").write_text(
        json.dumps(aggregate,sort_keys=True,indent=2)+"\n",
        encoding="utf-8")
    return aggregate

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for a in ("original_jar","candidate_jar","original_owner_class",
              "candidate_owner_class","new_private_output"):
        p.add_argument(a)
    p.add_argument("--original-sha256",required=True)
    p.add_argument("--candidate-sha256",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(replay_all_original_methods(
            a.original_jar,a.candidate_jar,a.original_owner_class,
            a.candidate_owner_class,a.new_private_output,
            original_sha256=a.original_sha256,
            candidate_sha256=a.candidate_sha256),sort_keys=True))
    except AllOwnerMethodsParityError as exc:p.error(str(exc))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
