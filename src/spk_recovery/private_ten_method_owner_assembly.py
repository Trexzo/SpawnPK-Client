"""R93: attach the verified R92 four-op source to R91's nine-method owner.

Requires matching original-JAR source hashes and rederives the exact
LambdaMetafactory method reference from original bytecode; no fabricated
source, runtime, dependency or original-class parity claims.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from .bytecode_profile import profile_jar_class
from .clinit_store_order_witness import _verified_class
from .mutable_scalar_initializer_source import _digest
from .private_lambda_method_source import recover_private_four_op_lambda

class OriginalTenMethodAssemblyError(ValueError):
    pass

def need(condition,code):
    if not condition:raise OriginalTenMethodAssemblyError(code)

def private_file(path):
    path=Path(path)
    need(path.is_file() and not path.is_symlink()
         and path.stat().st_size<=2*1024*1024,
         "PRIVATE_SOURCE_NOT_FOUND")
    raw=path.read_bytes()
    need(b"\x00" not in raw,"PRIVATE_SOURCE_BINARY_NUL")
    return raw.decode("utf-8"),hashlib.sha256(raw).hexdigest()

def report(path,original_sha,hash_key,source_hash):
    text,_=private_file(path)
    try:data=json.loads(text)
    except (TypeError,ValueError) as e:
        raise OriginalTenMethodAssemblyError("PRIVATE_SOURCE_AGGREGATE_INVALID") from e
    need(isinstance(data,dict)
         and data.get("original_complete_jar_sha256")==original_sha.lower()
         and data.get(hash_key)==source_hash,
         "PRIVATE_SOURCE_PIN_OR_CONTENT_HASH_MISMATCH")
    return data

def integrate_exact_tenth_method(original,nine_source,lambda_source,nine_proof):
    need(original.get("class_access")==0x0031
         and len(original.get("fields",[]))==126
         and len(original.get("methods",[]))==10,
         "ORIGINAL_OWNER_126_FIELD_TEN_METHOD_PROFILE_CHANGED")
    need(nine_proof.get("original_owner_methods_still_unrecovered")==1
         and nine_proof.get("original_total_method_declarations")==10,
         "R91_NINE_METHOD_SOURCE_INVENTORY_NOT_PROVEN")
    need(nine_source.count("public final class ")==1
         and nine_source.rstrip().endswith("}")
         and nine_source.count("public static boolean ")==3
         and nine_source.count("private static void ")==1,
         "R91_NINE_METHOD_SOURCE_NOT_RECOGNIZED")
    need(lambda_source.startswith("    public static void ")
         and "::" in lambda_source
         and "return" not in lambda_source,
         "R92_FINAL_LAMBDA_SOURCE_NOT_RECOGNIZED")
    last=nine_source.rfind("}")
    need(last>0 and not nine_source[last+1:].strip(),
         "R91_FINAL_CLOSING_BRACE_MISSING")
    return {
        "private_ten_method_java_source_candidate":
            nine_source[:last]+lambda_source.rstrip()+"\n"+nine_source[last:],
        "original_ten_method_declaration_inventory_accounted_for":True,
        "original_R59_126_fields_and_initializer_preserved":True,
        "original_R60_six_short_methods_preserved":True,
        "original_R80_loader_and_R85_saver_preserved":True,
        "original_R92_four_op_method_reference_added":True,
        "original_unrecovered_owner_method_source_form_count":0,
        "complete_original_owner_java9_compiled_and_accepted":False,
        "original_inner_classes_nested_enum_implementations_equivalent":False,
        "external_callback_and_helper_side_effects_equivalent":False,
        "whole_original_client_runtime_equivalence_certified":False,
    }

def assemble_private_ten_method_owner(
    jar,owner_entry,lambda_method,nine_source,nine_aggregate,
    lambda_source,lambda_aggregate,output,*,original_sha256):
    jar,output=Path(jar),Path(output)
    need(not output.exists() and not output.is_symlink(),"OUTPUT_ALREADY_EXISTS")
    original=_verified_class(jar,owner_entry,original_sha256)
    nine,nine_hash=private_file(nine_source)
    last,last_hash=private_file(lambda_source)
    proof=report(nine_aggregate,original_sha256,
                 "private_nine_method_java_sha256",nine_hash)
    report(lambda_aggregate,original_sha256,
           "private_lambda_source_sha256",last_hash)
    with ZipFile(jar) as z:
        candidate=[m for m in original.get("methods",[])
                   if m.get("name")==lambda_method and
                   len(m.get("instructions",[]))==4]
        need(len(candidate)==1,"ORIGINAL_FINAL_LAMBDA_METHOD_NOT_UNIQUE")
        rows=candidate[0]["instructions"]
        dynamic=rows[1].get("descriptor","")
        need(isinstance(dynamic,str) and dynamic.startswith("()L")
             and dynamic.endswith(";"),
             "ORIGINAL_FINAL_LAMBDA_DESCRIPTOR_INVALID")
        fn=dynamic[3:-1]+".class"
        reg=rows[2].get("owner","")+".class"
        need(z.namelist().count(fn)==1 and z.namelist().count(reg)==1,
             "ORIGINAL_LAMBDA_INTERFACE_OR_REGISTRAR_NOT_UNIQUE")
        interface=profile_jar_class(jar,fn)
        registrar=profile_jar_class(jar,reg)
    verified=recover_private_four_op_lambda(
        original,registrar,interface,lambda_method)
    need(last==verified["private_four_op_lambda_java_source"],
         "R92_LAMBDA_SOURCE_NOT_EXACT_ORIGINAL_BYTECODE")
    combined=integrate_exact_tenth_method(original,nine,last,proof)
    need(_digest(jar)==original_sha256.lower(),
         "ORIGINAL_JAR_CHANGED_DURING_TEN_METHOD_JOIN")
    source=combined.pop("private_ten_method_java_source_candidate")
    aggregate={
        "schema_version":1,
        "kind":"private_v309_R59_R60_R80_R85_R92_ten_method_java_candidate",
        "original_complete_jar_sha256":original_sha256.lower(),
        "private_all_ten_method_java_sha256":hashlib.sha256(source.encode()).hexdigest(),
        "research_only":True,**combined}
    output.mkdir(parents=True,exist_ok=False)
    (output/"ten-original-owner-methods.private.java.txt").write_text(
        source,encoding="utf-8")
    (output/"ten-original-owner-methods.aggregate.json").write_text(
        json.dumps(aggregate,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return aggregate

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for arg in (
        "original_jar","original_owner_class","original_lambda_method",
        "r91_nine_owner_source","r91_aggregate",
        "r92_lambda_source","r92_aggregate","new_private_output",
    ):p.add_argument(arg)
    p.add_argument("--original-sha256",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(assemble_private_ten_method_owner(
            a.original_jar,a.original_owner_class,a.original_lambda_method,
            a.r91_nine_owner_source,a.r91_aggregate,
            a.r92_lambda_source,a.r92_aggregate,a.new_private_output,
            original_sha256=a.original_sha256),sort_keys=True))
    except OriginalTenMethodAssemblyError as e:
        p.error(str(e))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
