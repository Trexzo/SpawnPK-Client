"""R91: attach R60's six exact short owner methods to the R89 candidate.

This is a bounded original-v309 source join, not a newly inferred
implementation. One 4-instruction invokedynamic helper method remains.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from .clinit_store_order_witness import _verified_class
from .bytecode_profile import profile_jar_class
from .mutable_scalar_initializer_source import _digest
from .small_owner_method_source import (
    plan_small_original_owner_methods, _private_external_field_owners,
)

class ShortOwnerAssemblyError(ValueError):
    pass

def need(ok,why):
    if not ok: raise ShortOwnerAssemblyError(why)

def private_input(path):
    path=Path(path)
    need(path.is_file() and not path.is_symlink()
         and path.stat().st_size<=2*1024*1024,
         "PRIVATE_SOURCE_OR_AGGREGATE_MISSING")
    data=path.read_bytes()
    need(b"\x00" not in data,"PRIVATE_INPUT_NUL")
    return data.decode("utf-8"),hashlib.sha256(data).hexdigest()

def aggregate(path,pin,source_key,sha):
    src,_=private_input(path)
    try: obj=json.loads(src)
    except (ValueError,TypeError) as e:
        raise ShortOwnerAssemblyError("PRIVATE_PROOF_JSON_INVALID") from e
    need(isinstance(obj,dict) and
         obj.get("original_complete_jar_sha256")==pin.lower() and
         obj.get(source_key)==sha,
         "ORIGINAL_SOURCE_SHA_OR_PIN_INVALID")
    return obj

def integrate_short_owner_methods(original,combined,short,proof):
    need(original.get("class_access")==0x0031
         and len(original.get("fields",[]))==126
         and len(original.get("methods",[]))==10,
         "ORIGINAL_126_FIELD_TEN_METHOD_OWNER_NOT_VERIFIED")
    need(proof.get("bounded_short_method_sources")==6
         and proof.get("remaining_methods_unreconstructed")==3
         and proof.get("original_total_jvm_methods")==10
         and proof.get("exact_original_array_element_writes")==10,
         "R60_SIX_SHORT_METHOD_SOURCE_PROOF_UNVERIFIED")
    need(short.startswith(
         "// PRIVATE: strictly proved original JVM short method source forms.")
         and short.count("public static boolean ")==3
         and short.count("public static void ")==2
         and short.count("public ")>=6,
         "R60_PRIVATE_SHORT_METHOD_FRAGMENT_SHAPE_DRIFT")
    need("public final class " in combined
         and "private static void " in combined
         and "public static void " in combined
         and combined.rstrip().endswith("}"),
         "R89_PRIVATE_OWNER_SOURCE_NOT_VERIFIED")
    close=combined.rfind("}")
    need(close>=0 and not combined[close+1:].strip(),
         "R89_SOURCE_OUTER_CLASS_CLOSING_BRACE_INVALID")
    joined=combined[:close]+short.rstrip()+"\n"+combined[close:]
    return {
        "private_nine_of_ten_method_owner_candidate_source":joined,
        "original_total_method_declarations":10,
        "original_complete_initializer_source_from_R59":True,
        "original_six_bounded_short_methods_from_R60":True,
        "original_loader_source_from_R80":True,
        "original_saver_source_from_R85":True,
        "original_owner_methods_still_unrecovered":1,
        "remaining_original_method_is_four_op_indy_invocation":True,
        "original_complete_owner_source_compiled":False,
        "exact_all_owner_method_parity_certified":False,
        "nested_class_and_external_helper_behavior_certified":False,
        "whole_client_runtime_equivalence_certified":False,
    }

def assemble_nine_methods(
    jar,entry,r89_source,r89_aggregate,r60_source,r60_aggregate,out,
    *,original_sha256,
):
    jar,out=Path(jar),Path(out)
    need(not out.exists() and not out.is_symlink(),"OUTPUT_ALREADY_EXISTS")
    original=_verified_class(jar,entry,original_sha256)
    full,full_sha=private_input(r89_source)
    short,short_sha=private_input(r60_source)
    aggregate(r89_aggregate,original_sha256,"private_combined_java_sha256",full_sha)
    r60=aggregate(r60_aggregate,original_sha256,
                  "private_short_method_fragment_sha256",short_sha)
    with ZipFile(jar) as z:
        owners=_private_external_field_owners(original)
        need(all(isinstance(o,str) and z.namelist().count(o+".class")==1
                 for o in owners),
             "R60_EXTERNAL_FIELD_OWNER_BINARY_NOT_UNIQUE")
        external={o:profile_jar_class(jar,o+".class") for o in owners}
    original_r60=plan_small_original_owner_methods(original,external)
    expected=original_r60.pop("private_method_source_fragment")
    need(short==expected and original_r60["bounded_short_method_sources"]==6,
         "R60_PRIVATE_SOURCE_NOT_EQUAL_EXACT_PINNED_ORIGINAL")
    report=integrate_short_owner_methods(original,full,short,r60)
    need(_digest(jar)==original_sha256.lower(),
         "ORIGINAL_JAR_CHANGED_DURING_SHORT_METHOD_JOIN")
    content=report.pop("private_nine_of_ten_method_owner_candidate_source")
    output={"schema_version":1,
            "kind":"v309_private_R59_R60_R80_R85_nine_owner_method_candidate",
            "original_complete_jar_sha256":original_sha256.lower(),
            "private_nine_method_java_sha256":hashlib.sha256(content.encode()).hexdigest(),
            "research_only":True,**report}
    out.mkdir(parents=True,exist_ok=False)
    (out/"nine-original-methods.private.java.txt").write_text(content,encoding="utf-8")
    (out/"nine-owner-methods.aggregate.json").write_text(
        json.dumps(output,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return output

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for a in ("original_jar","original_owner_class",
              "r89_owner_source","r89_aggregate",
              "r60_short_methods","r60_aggregate","new_private_output"):
        p.add_argument(a)
    p.add_argument("--original-sha256",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(assemble_nine_methods(
            a.original_jar,a.original_owner_class,a.r89_owner_source,
            a.r89_aggregate,a.r60_short_methods,a.r60_aggregate,
            a.new_private_output,original_sha256=a.original_sha256),
            sort_keys=True))
    except ShortOwnerAssemblyError as e:
        p.error(str(e))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
