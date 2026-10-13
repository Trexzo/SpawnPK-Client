"""R117: reconstruct 161 original loader verification STATES at source JVM PCs.

Java9 source widened original ldc to ldc_w, making original raw frame_type
bytes/PC deltas unrepresentative. Preserve 161 original verification *kinds*,
chop/appended counts, object types and locals/stack arrays at the matching
JVM *instruction ordinals*. Encode legal post-javac StackMap at candidate
byte offsets and candidate CP indices, NEVER original executable Code bytes.

Requires BOTH: R113's exact 364-method original 10-frame saver parity on
the input and R66/R81 original 697-method operand/handler/write parity.
The output remains a research preimage, NOT R94/R58/R95/R107 or gameplay.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZipFile

from .bytecode_profile import (
    BytecodeProfileError, _Reader, _class_name, _utf8, profile_jar_class,
)
from .private_v309_enum_stackmap_repair_r106 import (
    _class_method_layout, u2, u4,
)
from .private_original_fourth_enum_accessors import digest
from .private_large_owner_methods_inventory_r112 import (
    TwoLargeOwnerMethodInventoryError, unique_unrecovered,
)
from .private_recompiled_v309_saver_r113 import (
    OriginalSaverMethodAcceptanceError, original_saver_method_profile_proof,
)
from .whole_method_operand_parity import (
    WholeMethodOperandError, compare_all_method_operands,
)


class LoaderSymbolicFramesR117Error(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise LoaderSymbolicFramesR117Error(code)


def category(frame):
    ft = frame.get("frame_type")
    need(type(ft) is int, "JVM_LOADER_FRAME_ENCODING_REQUIRED")
    if ft <= 63 or ft == 251:
        return ("same", 0)
    if 64 <= ft <= 127 or ft == 247:
        return ("stack1", 1)
    if 248 <= ft <= 250:
        return ("chop", 251 - ft)
    if 252 <= ft <= 254:
        return ("append", ft - 251)
    if ft == 255:
        return ("full", 0)
    raise LoaderSymbolicFramesR117Error("JVM_LOADER_FRAME_RESERVED_TYPE")


def frames_at_ordinals(method):
    ins = method.get("instructions")
    frames = method.get("stackmap_frames")
    need(method.get("stackmap_table_present") is True
         and type(ins) is list and len(ins) == 697
         and type(frames) is list and len(frames) == 161,
         "EXACT_697_LOADER_AND_161_FRAMES_REQUIRED")
    map_offsets = {x.get("offset"): i for i,x in enumerate(ins)}
    need(len(map_offsets) == 697
         and all(type(x) is int for x in map_offsets)
         and list(map_offsets) == sorted(map_offsets),
         "JVM_LOADER_INSTRUCTION_OFFSETS_NOT_UNIQUE_OR_ORDERED")
    ordinals = []
    for frame in frames:
        pc=frame.get("bytecode_offset")
        need(type(pc) is int and pc in map_offsets,
             "JVM_FRAME_OFFSET_NOT_AT_INSTRUCTION_BOUNDARY")
        ordinals.append(map_offsets[pc])
    need(ordinals == sorted(set(ordinals)),
         "JVM_STACKMAP_FRAME_ORDINALS_NOT_STRICTLY_ORDERED")
    return ordinals, map_offsets


def semantic_frame(frame, original_index, new_instr):
    kind = category(frame)
    def vt(x):
        need(type(x) is dict and type(x.get("kind")) is str,
             "JVM_FRAME_VERIFICATION_TYPE_INVALID")
        if x["kind"] == "uninitialized":
            old_pc = x.get("new_offset")
            need(type(old_pc) is int and old_pc in original_index,
                 "ORIGINAL_UNINITIALIZED_NEW_INSTRUCTION_MISSING")
            at = original_index[old_pc]
            need(new_instr[at].get("opcode") == "0xbb",
                 "CANDIDATE_UNINITIALIZED_NEW_OPCODE_CHANGED")
            return {"kind": "uninitialized", "new_offset":
                    new_instr[at]["offset"]}
        return x
    return (
        kind,
        [vt(x) for x in frame.get("locals", [])],
        [vt(x) for x in frame.get("appended_locals", [])],
        [vt(x) for x in frame.get("stack", [])],
        frame.get("chopped_locals", 0),
    )


def _verification_bytes(verification_type, cp_to_class, old_offsets, new_instr):
    kind = verification_type.get("kind")
    values = {
        "top": 0, "integer": 1, "float": 2, "double": 3,
        "long": 4, "null": 5, "uninitialized_this": 6,
    }
    if kind in values:
        return bytes([values[kind]])
    if kind == "object":
        class_name = verification_type.get("class")
        need(type(class_name) is str and class_name in cp_to_class,
             "ORIGINAL_FRAME_CLASS_NOT_IN_CANDIDATE_POOL")
        return b"\x07" + u2(cp_to_class[class_name])
    if kind == "uninitialized":
        old_pc = verification_type.get("new_offset")
        need(type(old_pc) is int and old_pc in old_offsets,
             "ORIGINAL_UNINITIALIZED_NEW_PC_INVALID")
        index = old_offsets[old_pc]
        need(new_instr[index].get("opcode") == "0xbb",
             "CANDIDATE_UNINITIALIZED_NEW_OPCODE_MISMATCH")
        return b"\x08" + u2(new_instr[index]["offset"])
    raise LoaderSymbolicFramesR117Error(
        "ORIGINAL_VERIFICATION_TYPE_NOT_SUPPORTED")


def encode_original_states_at_candidate_pcs(
    original_method, candidate_method, candidate_cp,
):
    original_frames = original_method["stackmap_frames"]
    new_instr = candidate_method["instructions"]
    old_ordinals, old_pc_index = frames_at_ordinals(original_method)
    new_ordinals, new_pc_index = frames_at_ordinals(candidate_method)
    need(old_ordinals == new_ordinals,
         "ORIGINAL_161_FRAME_INSTRUCTION_ORDINALS_NOT_ALIGNED")

    categories = sum(category(a) != category(b)
                     for a,b in zip(original_frames,
                                    candidate_method["stackmap_frames"]))
    explicit_locals = sum(
        a.get("locals") != b.get("locals")
        or a.get("appended_locals") != b.get("appended_locals")
        for a,b in zip(original_frames, candidate_method["stackmap_frames"]))
    explicit_stack = sum(
        a.get("stack") != b.get("stack")
        for a,b in zip(original_frames, candidate_method["stackmap_frames"]))
    need(categories == 4 and explicit_locals == 2 and explicit_stack == 0,
         "EXPECTED_ORIGINAL_SOURCE_LOADER_FRAME_FRONTIER_CHANGED")

    cp_to_class = {
        _class_name(candidate_cp, i): i
        for i, item in enumerate(candidate_cp)
        if i > 0 and item is not None and item[0] == 7
    }
    encoded=[]
    last_pc=-1
    for original_frame, ordinal in zip(original_frames,old_ordinals):
        candidate_pc = new_instr[ordinal]["offset"]
        delta = candidate_pc - last_pc - 1
        need(0 <= delta < 65536,
             "RECOMPILED_JAVA9_STACKMAP_DELTA_OUT_OF_RANGE")
        last_pc = candidate_pc
        kind, count = category(original_frame)
        v = lambda row: _verification_bytes(
            row, cp_to_class, old_pc_index, new_instr)
        if kind == "same":
            raw = (bytes([delta]) if delta < 64
                   else b"\xfb" + u2(delta))
        elif kind == "stack1":
            stack = original_frame.get("stack")
            need(type(stack) is list and len(stack) == 1,
                 "ONE_STACK_VERIFICATION_ITEM_REQUIRED")
            raw = ((bytes([64 + delta]) if delta < 64
                    else b"\xf7" + u2(delta)) + v(stack[0]))
        elif kind == "chop":
            need(original_frame.get("chopped_locals") == count,
                 "EXACT_ORIGINAL_CHOP_COUNT_REQUIRED")
            raw = bytes([251 - count]) + u2(delta)
        elif kind == "append":
            local = original_frame.get("appended_locals")
            need(type(local) is list and len(local) == count,
                 "ORIGINAL_APPEND_VERIFICATION_LOCALS_REQUIRED")
            raw = (bytes([251 + count]) + u2(delta)
                   + b"".join(v(x) for x in local))
        elif kind == "full":
            local=original_frame.get("locals")
            stack=original_frame.get("stack")
            need(type(local) is list and type(stack) is list,
                 "ORIGINAL_FULL_FRAME_LOCALS_AND_STACK_REQUIRED")
            raw = (b"\xff" + u2(delta) + u2(len(local))
                   + b"".join(v(x) for x in local)
                   + u2(len(stack)) + b"".join(v(x) for x in stack))
        else:
            raise LoaderSymbolicFramesR117Error(
                "UNKNOWN_ORIGINAL_FRAME_ENCODING_CATEGORY")
        encoded.append(raw)
    return u2(161) + b"".join(encoded), {
        "original_loader_161_frame_ordinals_aligned": True,
        "original_loader_preimage_frame_category_differences": 4,
        "original_loader_preimage_explicit_locals_differences": 2,
        "original_loader_preimage_explicit_stack_differences": 0,
    }


def _get_loader_code(data, method_name):
    cp, _, _, _, methods = _class_method_layout(data)
    matches = []
    for access, name, desc, raw, attrs, _ in methods:
        if access == 9 and name == method_name and desc == "()V":
            code=[x for x in attrs if x[1] == "Code"]
            need(len(code) == 1,"ORIGINAL_697_LOADER_CODE_NOT_UNIQUE")
            matches.append(code[0][2])
    need(len(matches) == 1,"SOURCE_697_LOADER_METHOD_BINARY_NOT_FOUND")
    return matches[0],cp


def _modify_one_loader_stackmap(classfile, method_name, source_sm):
    cp, method_start, method_end, n, methods = _class_method_layout(classfile)
    out=bytearray(classfile[:method_start]+u2(n))
    touched=0
    code_old=None
    for access,name,desc,raw,attrs,_ in methods:
        out.extend(raw[:8])
        for idx,label,body in attrs:
            if access == 9 and name == method_name and desc == "()V" and label=="Code":
                r=_Reader(body)
                header=r.take(4)
                code=r.take(r.u4())
                code_old=code
                exc_num=r.u2()
                exc=r.take(8*exc_num)
                attrs_n=r.u2()
                parts=[]
                sm_changed=0
                for __ in range(attrs_n):
                    ai=r.u2()
                    data=r.take(r.u4())
                    if _utf8(cp,ai)=="StackMapTable":
                        data=source_sm
                        sm_changed+=1
                    parts.append((ai,data))
                need(r.offset == len(body) and sm_changed == 1,
                     "EXACT_ONE_JAVA9_LOADER_STACKMAP_ATTRIBUTE_REQUIRED")
                # Preserve all candidate executable Code bytes, exception table,
                # maximum stack/local values and all other nested attributes.
                body=(header+u4(len(code))+code+u2(exc_num)+exc+u2(attrs_n)
                      +b"".join(u2(ai)+u4(len(data))+data for ai,data in parts))
                touched+=1
            out.extend(u2(idx)+u4(len(body))+body)
    out.extend(classfile[method_end:])
    need(touched == 1,"EXACT_ONE_697_LOADER_STACKMAP_REBIND_REQUIRED")
    result=bytes(out)
    after,cp2=_get_loader_code(result,method_name)
    r=_Reader(after)
    r.take(4)
    need(r.take(r.u4()) == code_old,
         "PRIVATE_JAVA9_EXECUTABLE_LOADER_CODE_CHANGED")
    return result


def normalize_original_161_frames_then_require_large_R81(
    original_jar, compiled_source_jar, owner_entry, output, *,
    original_sha256, candidate_sha256,
):
    original_jar,compiled_source_jar,output=(
        Path(original_jar),Path(compiled_source_jar),Path(output))
    need(not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "NEW_PRIVATE_R117_OUTPUT_REQUIRED")
    need(type(owner_entry) is str and owner_entry.endswith(".class")
         and not owner_entry.startswith("/") and "\\" not in owner_entry
         and all(x not in ("", ".", "..") for x in owner_entry.split("/")),
         "ORIGINAL_OWNER_ARCHIVE_ENTRY_UNSAFE")
    need(original_jar.resolve()!=compiled_source_jar.resolve(),
         "ORIGINAL_CLIENT_CANNOT_BE_SOURCE_CANDIDATE")
    for jar,pin in ((original_jar,original_sha256),
                    (compiled_source_jar,candidate_sha256)):
        need(jar.is_file() and not jar.is_symlink()
             and type(pin) is str and re.fullmatch(r"[A-Fa-f0-9]{64}",pin)
             and digest(jar)==pin.lower(),
             "EXACT_COMPLETE_ORIGINAL_OR_SOURCE_JAR_PIN_REQUIRED")
    with ZipFile(original_jar) as orig, ZipFile(compiled_source_jar) as src:
        need(orig.namelist().count(owner_entry)==1
             and src.namelist().count(owner_entry)==1
             and len(orig.namelist())==len(set(orig.namelist()))
             and len(src.namelist())==len(set(src.namelist())),
             "ORIGINAL_OR_SOURCE_OWNER_CLASS_ENTRY_NOT_UNIQUE")
        src_class=src.read(owner_entry)
    original=profile_jar_class(original_jar,owner_entry)
    candidate=profile_jar_class(compiled_source_jar,owner_entry)
    need(original.get("internal_name")==candidate.get("internal_name")
         and original.get("classfile_major")==candidate.get("classfile_major")==53,
         "PINNED_ORIGINAL_JAVA9_OWNER_NAME_VERSION_MISMATCH")
    try:
        large=unique_unrecovered(original)
    except (TwoLargeOwnerMethodInventoryError,KeyError) as exc:
        raise LoaderSymbolicFramesR117Error(
            "ORIGINAL_126_FIELDS_TEN_METHODS_NOT_PROVEN") from exc
    old=large[697]
    method_name=old["name"]
    matches=[m for m in candidate.get("methods",[])
             if (m.get("name"),m.get("descriptor"))==(method_name,"()V")]
    need(len(matches)==1 and old.get("access")==matches[0].get("access")==9
         and old.get("max_stack")==matches[0].get("max_stack")==4
         and old.get("max_locals")==matches[0].get("max_locals")==6,
         "ORIGINAL_SOURCE_697_METHOD_HEADER_NOT_IDENTICAL")

    # Accept neither source-only stub nor a candidate with a broken saver.
    try:
        saver=original_saver_method_profile_proof(original,candidate)
        loader=compare_all_method_operands(
            original,method_name,"()V",candidate,method_name,"()V",
            [],[],[])
    except (OriginalSaverMethodAcceptanceError,WholeMethodOperandError,
            KeyError,ValueError,IndexError,TypeError) as exc:
        raise LoaderSymbolicFramesR117Error(
            "ORIGINAL_SAVER_R113_OR_LOADER_R81_PREIMAGE_REJECTED") from exc
    need(saver.get("original_saver_R66_R81_all_operands_passed") is True
         and saver.get("original_saver_jvm_StackMapTable_frames_equal")==10
         and loader.get("original_instructions_with_all_semantic_operands_compared")==697
         and loader.get("original_explicit_branches")==120
         and loader.get("original_ordered_typed_exception_entries")==44
         and loader.get("original_ordered_static_writes")==78
         and loader.get("all_parsed_JVM_operands_equal_with_private_aliases") is True,
         "R113_SAVER_OR_R81_LOADER_JVM_EVIDENCE_INCOMPLETE")

    _,cp=_get_loader_code(src_class,method_name)
    stackmap,frontier=encode_original_states_at_candidate_pcs(
        old,matches[0],cp)
    fixed_class=_modify_one_loader_stackmap(src_class,method_name,stackmap)

    with tempfile.TemporaryDirectory(
        prefix="v309-loader-frames-r117-",dir=output.parent) as td:
        root=Path(td)
        patched=root/"candidate.161-frames.PRIVATE.jar"
        with ZipFile(compiled_source_jar) as src, ZipFile(patched,"w") as out:
            for info in src.infolist():
                out.writestr(
                    info,fixed_class if info.filename==owner_entry
                    else src.read(info))
        final_pin=digest(patched)
        need(final_pin != candidate_sha256.lower()
             and digest(original_jar)==original_sha256.lower()
             and digest(compiled_source_jar)==candidate_sha256.lower(),
             "PRIVATE_ORIGINAL_SOURCE_POSTIMAGE_JAR_SHA256_MISMATCH")

        repaired=profile_jar_class(patched,owner_entry)
        final_saver=original_saver_method_profile_proof(original,repaired)
        final_loader=compare_all_method_operands(
            original,method_name,"()V",repaired,method_name,"()V",[],[],[])
        fixed=[m for m in repaired["methods"]
               if (m["name"],m["descriptor"])==(method_name,"()V")]
        need(len(fixed)==1 and final_saver.get(
             "original_saver_R66_R81_all_operands_passed") is True
             and final_loader.get(
                "original_instructions_with_all_semantic_operands_compared")==697,
             "ORIGINAL_BOTH_LARGE_METHOD_R81_AFTER_STACKMAP_FAILED")
        original_ord,original_offsets=frames_at_ordinals(old)
        final_ord,_=frames_at_ordinals(fixed[0])
        need(original_ord==final_ord,
             "REBUILT_ORIGINAL_161_FRAME_ORDINALS_DIFFERENT")
        for a,b in zip(old["stackmap_frames"],fixed[0]["stackmap_frames"]):
            need(semantic_frame(a,original_offsets,fixed[0]["instructions"])
                 == semantic_frame(b,original_offsets,fixed[0]["instructions"]),
                 "ORIGINAL_LOADER_FRAME_VERIFICATION_SEMANTICS_NOT_RESTORED")

        report={
            "schema_version":1,
            "kind":"private_v309_source_postjavac_saver_and_loader_frame_semantic_parity",
            "original_complete_jar_sha256":original_sha256.lower(),
            "input_source_candidate_sha256":candidate_sha256.lower(),
            "final_both_large_method_candidate_sha256":final_pin,
            "original_saver_364_R113_all_operands_10_frames_exact":True,
            "original_loader_697_R81_operands_120_branches_44_handlers_78_writes":True,
            "original_loader_161_frame_ordinals_and_verification_states_equal":True,
            "candidate_697_executable_Code_bytes_preserved":True,
            "original_loader_StackMap_literal_frame_encoding_equal":False,
            "original_executable_Code_bytes_transferred":False,
            "original_four_enum_R95_certified":False,
            "original_all_ten_owner_R94_R58_R88_R107_certified":False,
            "whole_client_runtime_equivalence_certified":False,
            **frontier,
        }
        stage=root/"accepted"
        stage.mkdir()
        shutil.copyfile(patched,stage/"candidate.large-method-frames.PRIVATE.jar")
        (stage/"original-364-697-frames.aggregate.json").write_text(
            json.dumps(report,sort_keys=True,indent=2)+"\n",
            encoding="utf-8")
        need(not output.exists(),"PRIVATE_R117_OUTPUT_OCCUPIED_AFTER_VERIFY")
        os.rename(stage,output)
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for a in ("original_jar","candidate_jar","owner_entry",
              "new_private_output"):
        p.add_argument(a)
    p.add_argument("--original-sha256",required=True)
    p.add_argument("--candidate-sha256",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(normalize_original_161_frames_then_require_large_R81(
            a.original_jar,a.candidate_jar,a.owner_entry,a.new_private_output,
            original_sha256=a.original_sha256,candidate_sha256=a.candidate_sha256),
            sort_keys=True))
    except (LoaderSymbolicFramesR117Error,BytecodeProfileError,OSError,
            ValueError,IndexError,KeyError,TypeError):
        p.error("PRIVATE_V309_LOADER_161_STACKMAP_RECONSTRUCTION_R117_NOT_ACCEPTED")


if __name__=="__main__":
    main()
