"""R89: join PRIVATE R59 owner shell and R80/R85 original method bodies.

This emits one complete-owner Java SOURCE CANDIDATE, not a passed compile,
method, initializer, nested enum or runtime equivalence certificate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from .clinit_store_order_witness import _verified_class
from .mutable_scalar_initializer_source import _digest

class OriginalOwnerAssemblyError(ValueError):
    pass

def need(ok,why):
    if not ok:
        raise OriginalOwnerAssemblyError(why)

def source_file(path):
    path=Path(path)
    need(path.is_file() and not path.is_symlink()
         and path.stat().st_size<=2*1024*1024,
         "PRIVATE_ORIGINAL_SOURCE_FRAGMENT_MISSING_OR_UNSAFE")
    raw=path.read_bytes()
    need(b"\x00" not in raw, "PRIVATE_SOURCE_CONTAINS_NUL")
    return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()

def proof_file(path,source_hash,original_sha,pin_key,source_key):
    path=Path(path)
    need(path.is_file() and not path.is_symlink()
         and path.stat().st_size<=262144,"ORIGINAL_SOURCE_AGGREGATE_MISSING")
    try:
        obj=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError) as e:
        raise OriginalOwnerAssemblyError("SOURCE_AGGREGATE_INVALID") from e
    need(isinstance(obj,dict)
         and obj.get(pin_key)==original_sha.lower()
         and obj.get(source_key)==source_hash,
         "SOURCE_AGGREGATE_PIN_OR_SHA_MISMATCH")

def stitch_original_owner_source(profile,shell,loader,saver,loader_name,saver_name):
    need(profile.get("class_access")==0x0031
         and len(profile.get("fields",[]))==126,
         "EXPECTED_ORIGINAL_PUBLIC_FINAL_126_FIELD_OWNER")
    methods=[m for m in profile.get("methods",[]) if m.get("descriptor")=="()V"]
    names={}
    for m in methods:
        if m.get("name") in (loader_name,saver_name):
            need(m["name"] not in names,"DUPLICATE_ORIGINAL_METHOD")
            names[m["name"]]=m
    need(loader_name!=saver_name and len(names)==2,
         "ORIGINAL_LOADER_SAVER_NOT_UNIQUE")
    need(names[loader_name].get("access")==0x0009
         and names[saver_name].get("access")==0x000a,
         "ORIGINAL_METHOD_PUBLIC_PRIVATE_STATIC_ACCESS_CHANGED")
    need(len(names[loader_name].get("instructions",[]))==697
         and len(names[saver_name].get("instructions",[]))==364,
         "EXPECTED_ORIGINAL_697_AND_364_METHODS")
    need(shell.startswith("// PRIVATE original JVM declaration and initializer source shell.")
         and "// Original methods / nested enums / exact runtime unverified." in shell
         and re.search(r"}\s*\Z",shell) is not None
         and shell.count("public final class ")==1,
         "PRIVATE_R59_OWNER_SHELL_STRUCTURE_INVALID")
    for body in (loader,saver):
        need(isinstance(body,str) and body.strip()
             and "try {" in body and "\x00" not in body
             and len(body)<1024*1024,
             "R80_OR_R85_BODY_SOURCE_INVALID")
    # The R59 original shell's last closing brace ends the outer class;
    # preserve all original field declarations and initializer source bytes.
    close=shell.rfind("}")
    need(close>0 and not shell[close+1:].strip(),
         "R59_FINAL_OWNER_CLOSING_BRACE_NOT_FOUND")
    def indent_body(value):
        return "".join("        "+line+"\n" for line in value.rstrip().splitlines())
    def member(modifier,name,body):
        need(re.fullmatch(r"[A-Za-z_$][A-Za-z_$0-9]*",name) is not None,
             "PRIVATE_JAVA_METHOD_NAME_NOT_VALID")
        return ("    "+modifier+" static void "+name+"() {\n"
                +indent_body(body)+"    }\n")
    assembled=(shell[:close]
               +member("public",loader_name,loader)
               +member("private",saver_name,saver)
               +shell[close:])
    return {
        "private_complete_owner_java_candidate":assembled,
        "original_126_field_declaration_shell_preserved":True,
        "original_static_initializer_shell_preserved":True,
        "original_697_instruction_loader_body_included":True,
        "original_364_instruction_saver_body_included":True,
        "candidate_compilation_against_original_binary_performed":False,
        "all_original_10_method_implementations_recovered":False,
        "nested_enum_class_metadata_equivalent":False,
        "original_initializer_jvm_operand_parity_passed":False,
        "both_methods_R87_replay_passed":False,
        "runtime_equivalence_certified":False,
    }

def assemble_private_owner(
    original_jar,original_entry,loader_name,saver_name,
    r59_shell,r59_aggregate,r80_body,r80_aggregate,
    r85_body,r85_aggregate,output,*,original_sha256):
    original_jar,output=Path(original_jar),Path(output)
    need(not output.exists() and not output.is_symlink(),
         "OUTPUT_ALREADY_EXISTS")
    profile=_verified_class(original_jar,original_entry,original_sha256)
    texts=[]
    for fragment,report,source_key,pin_key in (
        (r59_shell,r59_aggregate,"private_source_shell_sha256","original_complete_jar_sha256"),
        (r80_body,r80_aggregate,"private_candidate_source_sha256","whole_original_jar_sha256"),
        (r85_body,r85_aggregate,"private_source_sha256","whole_original_jar_sha256"),
    ):
        content,sha=source_file(fragment)
        proof_file(report,sha,original_sha256,pin_key,source_key)
        texts.append(content)
    p=stitch_original_owner_source(profile,*texts,loader_name,saver_name)
    need(_digest(original_jar)==original_sha256.lower(),
         "ORIGINAL_JAR_CHANGED_DURING_SOURCE_JOIN")
    source=p.pop("private_complete_owner_java_candidate")
    report={"schema_version":1,"kind":"private_v309_R59_R80_R85_owner_source_combination",
            "original_complete_jar_sha256":original_sha256.lower(),
            "private_combined_java_sha256":hashlib.sha256(source.encode()).hexdigest(),
            "research_only":True,**p}
    output.mkdir(parents=True,exist_ok=False)
    (output/"original-owner-combined.private.java.txt").write_text(source,encoding="utf-8")
    (output/"owner-source-assembly.aggregate.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return report

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("original_jar","original_class_entry","loader_method",
                 "saver_method","r59_shell","r59_aggregate",
                 "r80_body","r80_aggregate","r85_body","r85_aggregate",
                 "new_private_output"):
        parser.add_argument(name)
    parser.add_argument("--original-sha256",required=True)
    a=parser.parse_args(argv)
    try:
        print(json.dumps(assemble_private_owner(
            a.original_jar,a.original_class_entry,a.loader_method,a.saver_method,
            a.r59_shell,a.r59_aggregate,a.r80_body,a.r80_aggregate,
            a.r85_body,a.r85_aggregate,a.new_private_output,
            original_sha256=a.original_sha256),sort_keys=True))
    except OriginalOwnerAssemblyError as e:
        parser.error(str(e))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
