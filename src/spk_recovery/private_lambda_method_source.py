"""R92: reconstruct the last original-v309 four-op LambdaMetafactory method.

Exact original JVM shape: ldc String, invokedynamic static method reference,
invokestatic callback registration, return. Original names and literal
remain in PRIVATE Java output. Not a runtime/helper equivalence claim.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile
from .bytecode_profile import profile_jar_class
from .local_exception_primitive_source import _name, _owner_name
from .mutable_scalar_initializer_source import _digest, _instructions

class OriginalLambdaSourceError(ValueError):
    pass

def need(ok,reason):
    if not ok: raise OriginalLambdaSourceError(reason)

def _descriptor_internal(desc):
    need(isinstance(desc,str) and re.fullmatch(r"L[^;]+;",desc)
         and ".." not in desc and "\\" not in desc,
         "LAMBDA_FUNCTIONAL_INTERFACE_DESCRIPTOR_INVALID")
    return desc[1:-1]

def recover_private_four_op_lambda(
    original, registrar, function_type, name, *, expected_target_ops=364,
):
    methods=[m for m in original.get("methods",[])
             if m.get("name")==name and m.get("descriptor")=="()V"
             and m.get("access")==0x0009]
    need(len(methods)==1,"ORIGINAL_PUBLIC_STATIC_LAMBDA_METHOD_NOT_UNIQUE")
    method=methods[0]
    rows=_instructions(method)
    need(not method.get("exception_handlers") and len(rows)==4
         and [r.get("opcode") for r in rows]==["0x12","0xba","0xb8","0xb1"],
         "EXPECTED_EXACT_ORIGINAL_FOUR_OPCODE_LAMBDA_METHOD")
    literal, indy, register, _ = rows
    need(literal.get("constant_pool_tag")==8
         and isinstance(literal.get("constant"),str)
         and literal["constant"] and all(32<=ord(ch)<=126 for ch in literal["constant"]),
         "ORIGINAL_LAMBDA_REGISTRATION_STRING_NOT_EXACT_PRINTABLE")
    need(indy.get("invokedynamic_reserved")==0
         and isinstance(indy.get("name"),str)
         and isinstance(indy.get("descriptor"),str)
         and re.fullmatch(r"\(\)L[^;]+;",indy["descriptor"]),
         "ORIGINAL_LAMBDA_INDY_CALLSITE_INVALID")
    interface=_descriptor_internal(indy["descriptor"][2:])
    need(interface==function_type.get("internal_name")
         and function_type.get("class_access",0)&0x0200
         and len([m for m in function_type.get("methods",[])
                  if m.get("access",0)&0x0400])==1,
         "ORIGINAL_FUNCTIONAL_INTERFACE_NOT_UNIQUE")
    abstract=[m for m in function_type["methods"]
              if m.get("access",0)&0x0400][0]
    owner=original.get("internal_name")
    need(register.get("owner")==registrar.get("internal_name")
         and register.get("descriptor")==
             "(Ljava/lang/String;L"+interface+";)V"
         and register.get("opcode")=="0xb8"
         and isinstance(register.get("name"),str),
         "ORIGINAL_CALLBACK_REGISTRAR_SIGNATURE_MISMATCH")
    registrar_methods=[m for m in registrar.get("methods",[])
                       if m.get("name")==register["name"]
                       and m.get("descriptor")==register["descriptor"]
                       and m.get("access",0)&0x0008]
    need(len(registrar_methods)==1,
         "CALLBACK_REGISTRAR_DECLARATION_NOT_STATIC_UNIQUE")
    entries=original.get("bootstrap_methods",[])
    matches=[x for x in entries
             if x.get("index")==indy.get("bootstrap_method_attr_index")]
    need(len(matches)==1,"ORIGINAL_LAMBDA_BOOTSTRAP_INDEX_NOT_UNIQUE")
    bootstrap=matches[0]
    handle=bootstrap.get("bootstrap_method",{})
    args=bootstrap.get("arguments",[])
    need(handle.get("reference_kind")==6
         and handle.get("owner")=="java/lang/invoke/LambdaMetafactory"
         and handle.get("name")=="metafactory"
         and isinstance(args,list) and len(args)==3
         and args[0].get("kind")=="method_type"
         and args[2].get("kind")=="method_type",
         "ORIGINAL_LAMBDA_METAFACTORY_NOT_PROVEN")
    body=args[1].get("method_handle") if isinstance(args[1],dict) else None
    need(args[1].get("kind")=="method_handle"
         and isinstance(body,dict)
         and body.get("reference_kind")==6
         and body.get("owner")==owner
         and isinstance(body.get("name"),str)
         and body.get("descriptor")=="()V"
         and args[0].get("descriptor")==abstract.get("descriptor")=="()V"
         and args[2].get("descriptor")=="()V"
         and indy.get("name")==abstract.get("name"),
         "ORIGINAL_LAMBDA_STATIC_TARGET_AND_SAM_MISMATCH")
    target=[m for m in original.get("methods",[])
            if m.get("name")==body["name"] and m.get("descriptor")=="()V"
            and m.get("access")==0x000a]
    need(len(target)==1
         and len(_instructions(target[0]))==expected_target_ops,
         "ORIGINAL_LAMBDA_TARGET_NOT_PRIVATE_SAVE_METHOD")
    source=("    public static void "+_name(name)+"() {\n"
            "        "+_owner_name(register["owner"])+"."+_name(register["name"])
            +"("+json.dumps(literal["constant"],ensure_ascii=True)+", "
            +_owner_name(owner)+"::"+_name(body["name"])+");\n"
            "    }\n")
    return {
        "private_four_op_lambda_java_source":source,
        "original_exact_instructions":4,
        "original_static_method_reference_to_verified_save_method":True,
        "original_Java9_LambdaMetafactory_bootstrap_exact":True,
        "original_functional_interface_signature_checked":True,
        "original_external_registrar_static_signature_checked":True,
        "original_method_reference_java9_recompiled_on_complete_owner":False,
        "original_whole_owner_method_parity_certified":False,
        "original_callback_registration_runtime_semantics_certified":False,
        "whole_original_client_runtime_equivalence_certified":False,
    }

def replay_private_lambda(
    original_jar, owner_class, method_name, output, *,
    original_sha256, expected_target_ops=364,
):
    original_jar,output=Path(original_jar),Path(output)
    need(not output.exists() and not output.is_symlink(),"OUTPUT_ALREADY_EXISTS")
    need(original_jar.is_file() and not original_jar.is_symlink()
         and _digest(original_jar)==original_sha256.lower(),
         "ORIGINAL_COMPLETE_JAR_PIN_MISMATCH")
    with ZipFile(original_jar) as zipfile:
        need(zipfile.namelist().count(owner_class)==1,
             "ORIGINAL_LAMBDA_OWNER_NOT_UNIQUE")
        original=profile_jar_class(original_jar,owner_class)
        matches=[m for m in original.get("methods",[])
                 if m.get("name")==method_name and len(m.get("instructions",[]))==4]
        need(len(matches)==1,"ORIGINAL_LAMBDA_FOUR_OP_METHOD_NOT_UNIQUE")
        rows=matches[0]["instructions"]
        call=rows[2]
        desc=rows[1].get("descriptor","")
        need(isinstance(desc,str) and re.fullmatch(r"\(\)L[^;]+;",desc),
             "ORIGINAL_INDY_INTERFACE_DESCRIPTOR_MISSING")
        fn=desc[3:-1]+".class"
        reg=call.get("owner","")+".class"
        need(zipfile.namelist().count(fn)==1
             and zipfile.namelist().count(reg)==1,
             "ORIGINAL_LAMBDA_DEPENDENCY_NOT_UNIQUE")
        function=profile_jar_class(original_jar,fn)
        registrar=profile_jar_class(original_jar,reg)
    proof=recover_private_four_op_lambda(
        original,registrar,function,method_name,
        expected_target_ops=expected_target_ops)
    need(_digest(original_jar)==original_sha256.lower(),
         "ORIGINAL_JAR_CHANGED_DURING_LAMBDA_PROOF")
    content=proof.pop("private_four_op_lambda_java_source")
    report={
        "schema_version":1,
        "kind":"original_v309_private_four_op_lambda_registration_source",
        "original_complete_jar_sha256":original_sha256.lower(),
        "private_lambda_source_sha256":hashlib.sha256(content.encode()).hexdigest(),
        "research_only":True,**proof}
    output.mkdir(parents=True,exist_ok=False)
    (output/"lambda-method.private.java.txt").write_text(content,encoding="utf-8")
    (output/"lambda-method.aggregate.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for a in ("original_jar","original_owner_class",
              "original_lambda_method","new_private_output"):
        p.add_argument(a)
    p.add_argument("--original-sha256",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(replay_private_lambda(
            a.original_jar,a.original_owner_class,a.original_lambda_method,
            a.new_private_output,original_sha256=a.original_sha256),
            sort_keys=True))
    except OriginalLambdaSourceError as e:
        p.error(str(e))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
