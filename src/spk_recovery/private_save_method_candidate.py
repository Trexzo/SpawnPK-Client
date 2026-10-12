"""R85: private original v309 364-instruction settings-save source assembly.

Requires R82 (42 repeated writers), R83 (five unusual writers), and R84
(file I/O envelope). The exact remaining two JVM instructions are a
standalone BufferedWriter.newLine after the indexed int-array loop.
No claim of Java compiler, exact operand or runtime equivalence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

from .bytecode_profile import profile_jar_class
from .mutable_scalar_initializer_source import _digest, _instructions
from .properties_save_writer_source import (
    SaveWriterSourceError, extract_writer_lines, _writer,
)
from .properties_save_special_source import plan_original_special_save_sources
from .properties_save_io_envelope import plan_original_save_io_envelope


PIN = re.compile(r"[a-fA-F0-9]{64}\Z")


def need(ok, why):
    if not ok:
        raise SaveWriterSourceError(why)


def partition_original_save_method(
    rows: list[dict], regular: list[dict], special: list[dict],
) -> dict:
    """Require exact nonoverlapping instruction-span coverage, not mere 47 count."""
    need(len(rows)==364 and len(regular)==42 and len(special)==5,
         "ORIGINAL_SAVE_EXPECTED_JVM_AND_WRITE_SITE_COUNTS")
    index={row["offset"]: i for i,row in enumerate(rows)}
    need(len(index)==364 and rows[0]["offset"]==0
         and rows[20]["offset"]==44
         and rows[152]["offset"]==380
         and rows[153]["offset"]==381
         and rows[154]["offset"]==384
         and rows[336]["offset"]==871,
         "ORIGINAL_SAVE_CRITICAL_ORDINAL_OFFSETS_DRIFT")
    blocks=[]
    for r in regular:
        first=r.get("original_JVM_start_offset")
        end=r.get("original_JVM_end_next_offset")
        source=r.get("private_java_source_fragment")
        need(type(first) is int and type(end) is int
             and first in index and end in index
             and isinstance(source,str) and source.strip(),
             "ORIGINAL_R82_SITE_UNVERIFIABLE")
        blocks.append((index[first],index[end],"R82",source))
    for r in special:
        first=r.get("original_start_offset")
        end=r.get("original_end_offset")
        source=r.get("private_java_source_fragment")
        need(type(first) is int and type(end) is int
             and first in index and end in index
             and isinstance(source,str) and source.strip(),
             "ORIGINAL_R83_SITE_UNVERIFIABLE")
        blocks.append((index[first],index[end],"R83",source))
    blocks.sort(key=lambda x:x[0])
    need(len(blocks)==47 and sum(x[2]=="R82" for x in blocks)==42
         and sum(x[2]=="R83" for x in blocks)==5,
         "ORIGINAL_SAVE_WRITER_SOURCE_FAMILY_COUNTS_DRIFT")
    cursor=20
    assembled=[]
    orphan_positions=[]
    for first,end,family,java in blocks:
        need(end>first and first>=cursor,
             "ORIGINAL_SAVE_SOURCE_OVERLAP_OR_REORDER")
        if first>cursor:
            gap=tuple(range(cursor,first))
            orphan_positions.extend(gap)
            need(gap==(152,153)
                 and rows[152]["opcode"]=="0x2b"
                 and _writer(rows[153],"newLine"),
                 "UNEXPLAINED_ORIGINAL_SAVE_JVM_GAP")
            assembled.append((cursor,first,"ORIGINAL_ARRAY_SEPARATOR",
                              "originalLocalSlot1.newLine();\n"))
        need(first==cursor or (cursor==152 and first==154),
             "ORIGINAL_SAVE_WRITER_REGION_DISCONTINUITY")
        part=rows[first:end]
        write=[x for x in part if _writer(x,"write")]
        need(len(write)==1,"ORIGINAL_WRITE_SITE_NOT_ONE_TO_ONE")
        assembled.append((first,end,family,java))
        cursor=end
    need(cursor==336 and orphan_positions==[152,153],
         "ORIGINAL_SAVE_FINAL_WRITER_OR_SEPARATOR_NOT_EXACT")
    write_total=sum(_writer(row,"write") for row in rows)
    need(write_total==47,"ORIGINAL_SAVE_METHOD_WRITES_NOT_47")
    accounted=sum(b-a for a,b,_,_ in assembled)
    need(accounted==316
         and 20+accounted+28==364,
         "ORIGINAL_SAVE_364_INSTRUCTION_PARTITION_INCOMPLETE")
    return {
        "private_ordered_writer_and_separator_blocks": assembled,
        "original_total_jvm_instructions":364,
        "original_file_creation_writer_prefix":20,
        "original_42_regular_write_source_regions":42,
        "original_5_special_write_source_regions":5,
        "original_standalone_array_separator_instruction_count":2,
        "original_writer_and_separator_JVM_instructions":316,
        "original_final_file_io_exception_tail":28,
        "original_write_calls_accounted_for":47,
        "original_all_JVM_instruction_ordinals_accounted_for":True,
        "complete_original_method_compiled":False,
        "original_operand_exception_and_branch_parity_passed":False,
        "runtime_and_file_side_effect_parity_certified":False,
    }


def plan_private_complete_save_body(profile,method_name,descriptor):
    methods=[m for m in profile.get("methods",[])
             if m.get("name")==method_name and m.get("descriptor")==descriptor]
    need(len(methods)==1,"ORIGINAL_PRIVATE_SAVE_METHOD_NOT_UNIQUE")
    method=methods[0]
    rows=_instructions(method)
    regular=extract_writer_lines(profile,method)
    special=plan_original_special_save_sources(profile,method_name,descriptor)
    envelope=plan_original_save_io_envelope(profile,method_name,descriptor)
    fragments=partition_original_save_method(
        rows,regular,special["private_special_java_sources"])
    sections=fragments.pop("private_ordered_writer_and_separator_blocks")
    pre=envelope["private_source_open_prefix"]
    suffix=envelope["private_source_close_copy_delete_tail"]
    catch=envelope["private_source_original_exception_catch"]
    # Source candidate is a method-body fragment. The surrounding owner
    # fields, nested enums and helper methods are not fabricated here.
    body=("try {\n"
          + "".join("    "+line+"\n" for line in pre.splitlines())
          + "".join("    "+line+"\n"
                    for _,_,_,fragment in sections for line in fragment.splitlines())
          + "".join("    "+line+"\n" for line in suffix.splitlines())
          + "} "+catch)
    return {
        "private_364_op_save_java_method_body_candidate":body,
        **fragments,
        "original_outer_Exception_table_entry":1,
        "private_source_families_stitched_in_original_opcode_order":True,
        "all_original_instructions_to_source_forms_proven":False,
        "whole_364_op_candidate_compiled_against_original_dependencies":False,
        "complete_original_364_op_jvm_parity_passed":False,
        "original_runtime_equivalence_certified":False,
    }


def replay_private_save_body(jar,entry,method,descriptor,out,*,original_sha256):
    jar,out=Path(jar),Path(out)
    need(not out.exists() and not out.is_symlink(),"OUTPUT_ALREADY_EXISTS")
    need(isinstance(original_sha256,str) and PIN.fullmatch(original_sha256)
         and jar.is_file() and not jar.is_symlink()
         and _digest(jar)==original_sha256.lower(),
         "ORIGINAL_SAVE_WHOLE_JAR_PIN_FAILED")
    need(isinstance(entry,str) and entry.endswith(".class")
         and not entry.startswith("/") and "\\" not in entry
         and all(part not in ("",".","..") and ":" not in part
                 for part in entry.split("/")),
         "ORIGINAL_SAVE_PRIVATE_OWNER_ENTRY_INVALID")
    with ZipFile(jar) as z:
        need(z.namelist().count(entry)==1,
             "ORIGINAL_SAVE_OWNER_CLASS_NOT_UNIQUE")
    profile=profile_jar_class(jar,entry)
    evidence=plan_private_complete_save_body(profile,method,descriptor)
    need(_digest(jar)==original_sha256.lower(),
         "ORIGINAL_SAVE_JAR_CHANGED_DURING_REPLAY")
    source=evidence.pop("private_364_op_save_java_method_body_candidate")
    public={
        "schema_version":1,"kind":"v309_original_private_364_op_save_java_candidate",
        "whole_original_jar_sha256":original_sha256.lower(),
        "private_source_sha256":hashlib.sha256(source.encode()).hexdigest(),
        "research_only":True,**evidence,
    }
    out.mkdir(parents=True,exist_ok=False)
    with (out/"save-method-body.private.java.txt").open(
            "x",encoding="utf-8",newline="\n") as f:
        f.write(source)
    with (out/"save-method-candidate.aggregate.json").open(
            "x",encoding="utf-8",newline="\n") as f:
        json.dump(public,f,indent=2,sort_keys=True);f.write("\n")
    return public


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ("original_jar","original_class_entry","original_method",
                "descriptor","new_private_output"):parser.add_argument(arg)
    parser.add_argument("--original-sha256",required=True)
    a=parser.parse_args(argv)
    try:
        print(json.dumps(replay_private_save_body(
            a.original_jar,a.original_class_entry,a.original_method,
            a.descriptor,a.new_private_output,
            original_sha256=a.original_sha256),sort_keys=True))
    except (SaveWriterSourceError,OSError,ValueError) as exc:
        parser.error(str(exc))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
