"""R73: exact original indexed Properties loop and concat-bootstrap proof.

Conservatively proves the original 22-instruction protected body, including
two identical invokedynamic StringConcatFactory recipes and repeated
Properties.getProperty calls. Keeps original property prefix/private fields
off the public report. This does NOT reconstruct its enclosing Java method.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from .bytecode_profile import profile_jar_class
from .mutable_scalar_initializer_source import _digest, _instructions, _fields

class IndexedLoopProofError(ValueError): pass

def need(ok, msg):
    if not ok: raise IndexedLoopProofError(msg)

def recover_loop(profile):
    owner=profile.get("internal_name")
    need(isinstance(owner,str),"OWNER_MISSING")
    hits=[]
    for method in profile.get("methods",[]):
        rows=_instructions(method)
        handlers=method.get("exception_handlers",[])
        for h in handlers:
            if h.get("catch_type")!="java/lang/Exception":continue
            offsets={r["offset"]:i for i,r in enumerate(rows)}
            a,b=(offsets.get(h.get("start_pc")),offsets.get(h.get("end_pc")))
            if a is None or b is None or b-a!=22:continue
            w=rows[a:b]
            concat=[x for x in w if x.get("opcode")=="0xba"]
            if len(concat)!=2:continue
            need(concat[0].get("bootstrap_method_attr_index")==
                 concat[1].get("bootstrap_method_attr_index"),
                 "DYNAMIC_KEY_BOOTSTRAP_DIFFERENT")
            need(all(x.get("descriptor")=="(I)Ljava/lang/String;"
                     and x.get("invokedynamic_reserved")==0 for x in concat),
                 "DYNAMIC_KEY_DESCRIPTOR_MISMATCH")
            ix=concat[0]["bootstrap_method_attr_index"]
            boot=[x for x in profile.get("bootstrap_methods",[])
                  if x.get("index")==ix]
            need(len(boot)==1,"BOOTSTRAP_NOT_UNIQUE")
            method_handle=boot[0].get("bootstrap_method",{})
            need(method_handle.get("owner")==
                 "java/lang/invoke/StringConcatFactory"
                 and method_handle.get("name")=="makeConcatWithConstants"
                 and method_handle.get("reference_kind")==6,
                 "NOT_STRINGCONCATFACTORY")
            args=boot[0].get("arguments")
            need(isinstance(args,list) and len(args)==1
                 and args[0].get("kind")=="string",
                 "RECIPE_NOT_ONE_STRING")
            recipe=args[0].get("value")
            need(isinstance(recipe,str) and recipe.count("\u0001")==1
                 and recipe.endswith("\u0001")
                 and "\u0002" not in recipe,
                 "RECIPE_NOT_CONSTANT_PREFIX_PLUS_INDEX")
            getters=[x for x in w if x.get("opcode")=="0xb6"
                     and x.get("owner")=="java/util/Properties"
                     and x.get("name")=="getProperty"]
            need(len(getters)==2 and all(x.get("descriptor")==
                "(Ljava/lang/String;)Ljava/lang/String;" for x in getters),
                "ORIGINAL_PROPERTY_LOOKUPS_NOT_EXACT")
            stores=[x for x in w if x.get("opcode")=="0x4f"]
            need(len(stores)==1,"EXPECTED_ONE_INT_ARRAY_ELEMENT_STORE")
            hits.append({"method":method.get("name"),
                         "descriptor":method.get("descriptor"),
                         "start_pc":h["start_pc"],"end_pc":h["end_pc"],
                         "private_recipe":recipe,"bootstrap_index":ix,
                         "original_opcodes":[x["opcode"] for x in w]})
    need(len(hits)==1,"EXACT_ONE_INDEXED_LOOP_REGION_REQUIRED")
    return hits[0]

def replay(jar:Path,entry:str,out:Path,sha:str):
    need(not out.exists(),"OUTPUT_EXISTS")
    need(jar.is_file() and _digest(jar)==sha.lower(),"WHOLE_JAR_SHA_MISMATCH")
    with ZipFile(jar) as z:
        need(z.namelist().count(entry)==1,"ORIGINAL_ENTRY_NOT_UNIQUE")
        profile=profile_jar_class(jar,entry)
    p=recover_loop(profile)
    need(_digest(jar)==sha.lower(),"ORIGINAL_JAR_CHANGED")
    raw=json.dumps(p,sort_keys=True,indent=2)+"\n"
    report={"schema_version":1,
            "original_whole_jar_sha256":sha.lower(),
            "protected_jvm_instructions":22,
            "dynamic_concat_site_count":2,
            "same_bootstrap_recipe":True,
            "original_properties_getter_calls":2,
            "private_proof_sha256":hashlib.sha256(raw.encode()).hexdigest(),
            "full_original_method_compiled":False,
            "runtime_parity":False}
    out.mkdir(parents=True)
    (out/"indexed-loop.private.json").write_text(raw,encoding="utf-8")
    (out/"indexed-loop.aggregate.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("original_jar",type=Path)
    p.add_argument("private_class_entry")
    p.add_argument("new_private_output",type=Path)
    p.add_argument("--sha256",required=True)
    a=p.parse_args()
    print(json.dumps(replay(a.original_jar,a.private_class_entry,
                            a.new_private_output,a.sha256),sort_keys=True))
if __name__=="__main__":main()
