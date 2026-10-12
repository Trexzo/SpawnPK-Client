"""R83: exact five unusual original v309 BufferedWriter site forms.

Research-only original-JAR-pinned source fragments. Exact JVM offsets are
version-specific and intentionally fail closed. Source files stay private.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

from .bytecode_profile import profile_jar_class
from .local_exception_primitive_source import _name, _owner_name, _literal
from .mutable_scalar_initializer_source import _digest, _fields, _instructions
from .properties_save_writer_source import (
    SaveWriterSourceError, _writer, extract_writer_lines,
)

PATTERNS = {
    "array": ("0x03","0x3d","0x1c","0xb2","0xbe","0xa2",
              "0x2b","0x1c","0xb2","0x1c","0x2e","0xba","0xb6",
              "0x1c","0xb2","0xbe","0x04","0x60","0x9f",
              "0x2b","0xb6","0x84","0xa7"),
    "filter": ("0xb2","0xb2","0xb9","0x99","0x2b","0x12",
               "0xb6","0x2b","0xb6"),
    "enum": ("0xb2","0xc6","0x2b","0xb2","0xb6","0xb2",
             "0xb6","0xba","0xb6","0x2b","0xb6"),
}
WINDOWS = ((335,380,"array"),(528,552,"filter"),(552,576,"filter"),
           (576,600,"filter"),(728,759,"enum"))
SHA = re.compile(r"[0-9a-fA-F]{64}\Z")


def need(ok, why):
    if not ok:
        raise SaveWriterSourceError(why)


def source_field(profile, insn, desc):
    need(insn.get("opcode")=="0xb2"
         and insn.get("descriptor")==desc
         and isinstance(insn.get("owner"),str)
         and isinstance(insn.get("name"),str),
         "ORIGINAL_FIELD_REFERENCE_MISMATCH")
    owner = insn["owner"]
    if owner == profile.get("internal_name"):
        fields = _fields(profile)
        need(fields.get((insn["name"],desc),{}).get("access",0)&8,
             "UNDECLARED_ORIGINAL_STATIC_FIELD")
        return _name(insn["name"])
    return _owner_name(owner)+"."+_name(insn["name"])


def original_region(rows, begin, end, kind):
    indices=[i for i,x in enumerate(rows) if x["offset"]==begin]
    need(len(indices)==1,"ORIGINAL_SPECIAL_REGION_OFFSET_NOT_FOUND")
    i=indices[0]
    seq=rows[i:i+len(PATTERNS[kind])]
    need(len(seq)==len(PATTERNS[kind])
         and tuple(x["opcode"] for x in seq)==PATTERNS[kind]
         and i+len(seq)<len(rows)
         and rows[i+len(seq)]["offset"]==end,
         "ORIGINAL_SPECIAL_JVM_PATTERN_OR_END_DRIFT")
    return seq


def recipe(profile, insn, descriptor, slots):
    need(insn.get("opcode")=="0xba"
         and insn.get("name")=="makeConcatWithConstants"
         and insn.get("descriptor")=="("+descriptor+")Ljava/lang/String;"
         and insn.get("invokedynamic_reserved")==0,
         "ORIGINAL_SPECIAL_CONCAT_DESCRIPTOR_DRIFT")
    table=profile.get("bootstrap_methods")
    index=insn.get("bootstrap_method_attr_index")
    need(isinstance(table,list) and type(index) is int and 0<=index<len(table),
         "ORIGINAL_SPECIAL_BOOTSTRAP_MISSING")
    data=table[index]
    handle=data.get("bootstrap_method",{})
    arguments=data.get("arguments")
    need(handle.get("owner")=="java/lang/invoke/StringConcatFactory"
         and handle.get("name")=="makeConcatWithConstants"
         and handle.get("reference_kind")==6
         and isinstance(arguments,list) and len(arguments)==1
         and arguments[0].get("kind")=="string",
         "ORIGINAL_SPECIAL_BOOTSTRAP_NOT_STRING_CONCAT")
    raw=arguments[0].get("value")
    need(isinstance(raw,str) and raw.count("\x01")==slots
         and "\x02" not in raw
         and all(c=="\x01" or 32<=ord(c)<=126 for c in raw),
         "ORIGINAL_SPECIAL_CONCAT_RECIPE_UNSUPPORTED")
    return raw.split("\x01")


def array_source(profile,b):
    values=source_field(profile,b[3],"[I")
    for i in (8,14):
        need(all(b[i].get(k)==b[3].get(k)
                 for k in ("opcode","owner","name","descriptor")),
             "ORIGINAL_LOOP_ARRAY_RELOAD_NOT_IDENTICAL")
    need(b[5].get("branch_target_offset")==380
         and b[18].get("branch_target_offset")==374
         and b[22].get("branch_target_offset")==337
         and b[21].get("local_index")==2
         and b[21].get("increment")==1
         and _writer(b[12],"write") and _writer(b[20],"newLine"),
         "ORIGINAL_ARRAY_LOOP_BRANCH_OR_WRITER_MISMATCH")
    parts=recipe(profile,b[11],"II",2)
    need(parts[2]=="","ORIGINAL_INDEXED_ARRAY_CONCAT_TRAILING_LITERAL")
    return ("for (int originalIndex = 0; originalIndex < "+values+".length; originalIndex++) {\n"
            "    originalLocalSlot1.write("
            +json.dumps(parts[0],ensure_ascii=True)+" + originalIndex + "
            +json.dumps(parts[1],ensure_ascii=True)+" + "+values+"[originalIndex]);\n"
            "    if (originalIndex != "+values+".length + 1) {\n"
            "        originalLocalSlot1.newLine();\n"
            "    }\n"
            "}\n")


def filter_source(profile,b,end):
    desc=b[1].get("descriptor")
    need(isinstance(desc,str) and desc.startswith("L") and desc.endswith(";")
         and b[2].get("owner")=="java/util/List"
         and b[2].get("name")=="contains"
         and b[2].get("descriptor")=="(Ljava/lang/Object;)Z"
         and b[2].get("invokeinterface_count")==2
         and b[2].get("invokeinterface_reserved")==0
         and b[3].get("branch_target_offset")==end
         and _writer(b[6],"write") and _writer(b[8],"newLine"),
         "ORIGINAL_LIST_FILTER_BRANCH_OR_WRITER_MISMATCH")
    left=source_field(profile,b[0],"Ljava/util/List;")
    right=source_field(profile,b[1],desc)
    literal=_literal(b[5])
    return ("if ("+left+".contains("+right+")) {\n"
            "    originalLocalSlot1.write("+literal+");\n"
            "    originalLocalSlot1.newLine();\n"
            "}\n")


def enum_source(profile,b):
    desc=b[0].get("descriptor")
    right_desc=b[5].get("descriptor")
    need(isinstance(desc,str) and desc.startswith("L") and desc.endswith(";")
         and isinstance(right_desc,str) and right_desc.startswith("L") and right_desc.endswith(";")
         and all(b[0].get(k)==b[3].get(k)
                 for k in ("opcode","owner","name","descriptor"))
         and b[1].get("branch_target_offset")==759
         and _writer(b[8],"write") and _writer(b[10],"newLine"),
         "ORIGINAL_GUARDED_ENUM_FIELD_OR_BRANCH_DRIFT")
    for row,d in ((b[4],desc),(b[6],right_desc)):
        need(row.get("opcode")=="0xb6"
             and row.get("owner")==d[1:-1]
             and row.get("name")=="name"
             and row.get("descriptor")=="()Ljava/lang/String;",
             "ORIGINAL_ENUM_NAME_INVOKE_MISMATCH")
    first=source_field(profile,b[0],desc)
    second=source_field(profile,b[5],right_desc)
    parts=recipe(profile,b[7],"Ljava/lang/String;Ljava/lang/String;",2)
    need(parts[2]=="","ORIGINAL_ENUM_CONCAT_TRAILING_LITERAL")
    return ("if ("+first+" != null) {\n"
            "    originalLocalSlot1.write("
            +json.dumps(parts[0],ensure_ascii=True)+" + "+first+".name() + "
            +json.dumps(parts[1],ensure_ascii=True)+" + "+second+".name());\n"
            "    originalLocalSlot1.newLine();\n"
            "}\n")


def plan_original_special_save_sources(profile,method_name,descriptor):
    methods=[m for m in profile.get("methods",[])
             if m.get("name")==method_name and m.get("descriptor")==descriptor]
    need(len(methods)==1 and descriptor=="()V","ORIGINAL_SAVE_METHOD_ID_NOT_UNIQUE")
    m=methods[0];rows=_instructions(m)
    need(m.get("access")==0x000a and len(rows)==364,
         "ORIGINAL_364_INSTRUCTION_PRIVATE_STATIC_METHOD_REQUIRED")
    sites=extract_writer_lines(profile,m)
    need(len(sites)==42,"R82_ORIGINAL_42_SIMPLE_WRITES_NOT_PRESENT")
    collected=[]
    list_fields=[]
    for start,end,kind in WINDOWS:
        block=original_region(rows,start,end,kind)
        fragment=(array_source(profile,block) if kind=="array" else
                  filter_source(profile,block,end) if kind=="filter" else
                  enum_source(profile,block))
        if kind=="filter":
            list_fields.append(tuple(block[0].get(k) for k in
                                     ("owner","name","descriptor")))
        collected.append({"original_start_offset":start,
                          "original_end_offset":end,"kind":kind,
                          "private_java_source_fragment":fragment})
    need(len(set(list_fields))==1,"ORIGINAL_LIST_FILTER_OWNER_NOT_SHARED")
    starts={x["original_JVM_start_offset"] for x in sites}
    need(not any(x["original_start_offset"] in starts for x in collected),
         "SPECIAL_SOURCE_SITE_DUPLICATES_R82")
    need(sum(_writer(r,"write") for r in rows)==47
         and len(collected)+len(sites)==47,
         "ORIGINAL_COMPLETE_WRITE_SITE_COUNT_NOT_47")
    return {"private_special_java_sources":collected,
            "original_indexed_array_write_regions":1,
            "original_guarded_List_filter_write_regions":3,
            "original_conditional_enum_pair_write_regions":1,
            "original_BW_write_sites_classified":47,
            "original_complete_364_op_method_source_compiled":False,
            "original_filesystem_side_effects_proven":False,
            "original_runtime_equivalence_certified":False}


def replay_private_special_save(jar,class_entry,method,descriptor,out,*,original_sha256):
    jar,out=Path(jar),Path(out)
    need(not out.exists() and not out.is_symlink(),"OUTPUT_ALREADY_EXISTS")
    need(isinstance(original_sha256,str) and SHA.fullmatch(original_sha256)
         and jar.is_file() and not jar.is_symlink()
         and _digest(jar)==original_sha256.lower(),"ORIGINAL_JAR_SHA_MISMATCH")
    need(isinstance(class_entry,str) and class_entry.endswith(".class")
         and not class_entry.startswith("/") and "\\" not in class_entry
         and all(s not in ("",".","..") and ":" not in s
                 for s in class_entry.split("/")),"UNSAFE_ORIGINAL_CLASS_PATH")
    with ZipFile(jar) as zipfile:
        need(zipfile.namelist().count(class_entry)==1,
             "ORIGINAL_CLASS_ENTRY_NOT_UNIQUE")
    profile=profile_jar_class(jar,class_entry)
    proof=plan_original_special_save_sources(profile,method,descriptor)
    need(_digest(jar)==original_sha256.lower(),
         "ORIGINAL_JAR_CHANGED_DURING_PROOF")
    sites=proof.pop("private_special_java_sources")
    source="".join(s["private_java_source_fragment"] for s in sites)
    raw=json.dumps(sites,sort_keys=True,indent=2)+"\n"
    public={"schema_version":1,"kind":"original_v309_five_special_save_write_sources",
            "original_complete_jar_sha256":original_sha256.lower(),
            "private_source_sha256":hashlib.sha256(source.encode()).hexdigest(),
            "private_site_proof_sha256":hashlib.sha256(raw.encode()).hexdigest(),
            "research_only":True,**proof}
    out.mkdir(parents=True,exist_ok=False)
    for file,data in (
        ("five-special-writers.private.java.txt",source),
        ("five-special-sites.private.json",raw),
        ("five-special.aggregate.json",json.dumps(public,indent=2,sort_keys=True)+"\n"),
    ):
        with (out/file).open("x",encoding="utf-8",newline="\n") as f:
            f.write(data)
    return public


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("original_jar","original_owner_class","original_method",
                 "descriptor","new_private_output"):
        p.add_argument(name)
    p.add_argument("--original-sha256",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(replay_private_special_save(
            a.original_jar,a.original_owner_class,a.original_method,
            a.descriptor,a.new_private_output,
            original_sha256=a.original_sha256),sort_keys=True))
    except (SaveWriterSourceError,OSError,ValueError) as exc:
        p.error(str(exc))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
