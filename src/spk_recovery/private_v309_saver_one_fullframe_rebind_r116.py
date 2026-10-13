"""R116: restore ONE original-v309 saver StackMap full_frame, preserving Code.

Original private-static 364-op method: frame #2 full_frame(delta=308,
locals=[top, java/io/BufferedWriter, integer], stack=[]) where original-like
javac9 emits append_frame(2)(delta=308, [BufferedWriter,integer]).
Reconstruct the original verification encoding using candidate CP indices.
Do not import original executable Code. Then REQUIRE exact R113 R66/R81,
original full 10-frame StackMapTable, and one unchanged 364-op Code sequence.
Original JAR, private candidate, source and rebuilt output stay PRIVATE.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import tempfile
from zipfile import ZipFile

from .bytecode_profile import (
    BytecodeProfileError, _Reader, _class_name, _utf8, profile_jar_class,
)
from .private_original_fourth_enum_accessors import digest
from .private_large_owner_methods_inventory_r112 import (
    TwoLargeOwnerMethodInventoryError, unique_unrecovered,
)
from .private_v309_enum_stackmap_repair_r106 import (
    _class_method_layout, u2, u4,
)
from .private_recompiled_v309_saver_r113 import (
    OriginalSaverMethodAcceptanceError,
    accept_original_source_recompiled_saver,
)


class SaverFullFrameR116Error(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise SaverFullFrameR116Error(why)


def _saver_stackmap_in_code(code_body, cp):
    r = _Reader(code_body)
    stack, locals_ = r.u2(), r.u2()
    code = r.take(r.u4())
    ecount = r.u2()
    exceptions = r.take(8 * ecount)
    entries = r.u2()
    attributes = []
    for _ in range(entries):
        attr_idx = r.u2()
        body = r.take(r.u4())
        attributes.append((attr_idx, _utf8(cp, attr_idx), body))
    need(r.offset == len(code_body), "SAVER_CODE_ATTRIBUTE_TRAILING_BYTES")
    frame = [x for x in attributes if x[1] == "StackMapTable"]
    need(len(frame) == 1, "EXACT_ONE_SAVER_STACKMAP_TABLE_REQUIRED")
    return stack, locals_, code, ecount, exceptions, attributes, frame[0][2]


def _single_saver_frame_layout(raw, cp, *, original):
    """Recognize all ten frames, allowing only the single append/full rewrite.

    Parsing type payloads ensures the BufferedWriter CP index is already in
    the *candidate*, and no original Code or CP bytes are transferred.
    """
    r = _Reader(raw)
    need(r.u2() == 10, "EXACT_TEN_SAVER_FRAMES_REQUIRED")
    need(r.u1() == 252 and r.u2() == 28
         and r.u1() == 7, "FIRST_SAVER_APPENDED_FILE_FRAME_CHANGED")
    file_cp = r.u2()
    need(_class_name(cp, file_cp) == "java/io/File",
         "FIRST_SAVER_FRAME_ORIGINAL_FILE_TYPE_CHANGED")
    start = r.offset
    if original:
        need(r.u1() == 255 and r.u2() == 308 and
             r.u2() == 3 and r.u1() == 0 and r.u1() == 7,
             "ORIGINAL_SECOND_SAVER_FULL_FRAME_NOT_EXACT")
    else:
        need(r.u1() == 253 and r.u2() == 308 and r.u1() == 7,
             "JAVAC_SECOND_SAVER_APPEND_TWO_NOT_EXACT")
    writer_cp = r.u2()
    need(_class_name(cp, writer_cp) == "java/io/BufferedWriter"
         and r.u1() == 1,
         "SAVER_SECOND_FRAME_BUFFERED_WRITER_AND_INT_NOT_EXACT")
    if original:
        need(r.u2() == 0, "ORIGINAL_SECOND_FRAME_STACK_MUST_BE_EMPTY")
    end = r.offset
    # Bounded tail: eight original frames, including second full-frame later.
    need(r.u1() == 36
         and r.u1() == 250 and r.u2() == 5
         and r.u1() == 251 and r.u2() == 171
         and r.u1() == 23 and r.u1() == 23
         and r.u1() == 251 and r.u2() == 158
         and r.u1() == 255 and r.u2() == 163 and r.u2() == 0
         and r.u2() == 1 and r.u1() == 7,
         "ORIGINAL_SAVER_REMAINING_EIGHT_FRAMES_CHANGED")
    exception_cp = r.u2()
    need(_class_name(cp, exception_cp) == "java/lang/Exception"
         and r.u1() == 4 and r.offset == len(raw),
         "LAST_SAVER_EXCEPTION_FRAME_OR_TRAILING_BYTES_DIFFERENT")
    return start, end, writer_cp


def _method_code_attribute(data, method_name):
    cp, start, end, method_count, methods = _class_method_layout(data)
    matches = []
    for access, name, desc, raw, attrs, _ in methods:
        if access == 10 and name == method_name and desc == "()V":
            code = [x for x in attrs if x[1] == "Code"]
            need(len(code) == 1, "EXACT_ONE_PRIVATE_STATIC_SAVER_CODE_REQUIRED")
            matches.append(_saver_stackmap_in_code(code[0][2], cp))
    need(len(matches) == 1, "PRIVATE_STATIC_SAVER_CLASSFILE_METHOD_MISSING")
    return matches[0], cp


def restore_original_saver_full_frame(
    original_classfile, candidate_classfile, method_name,
):
    original_code, original_cp = _method_code_attribute(
        original_classfile, method_name)
    source_code, candidate_cp = _method_code_attribute(
        candidate_classfile, method_name)
    original_stack, original_locals, original_bytes, _, _, _, old_table = (
        original_code)
    source_stack, source_locals, source_bytes, _, _, _, src_table = (
        source_code)
    _single_saver_frame_layout(old_table, original_cp, original=True)
    start, end, writer_cp = _single_saver_frame_layout(
        src_table, candidate_cp, original=False)
    need(original_stack == source_stack == 6
         and original_locals == source_locals == 3
         and len(original_bytes) == len(source_bytes) == 929,
         "ORIGINAL_SOURCE_SAVER_STACK_LOCAL_CODE_LENGTH_NOT_EXACT")

    # 255 full_frame, delta308, three locals top/BufferedWriter/int,
    # zero stack items. CP index refers only to existing candidate pool.
    reconstructed = (
        bytes([255]) + u2(308) + u2(3) + bytes([0, 7])
        + u2(writer_cp) + bytes([1]) + u2(0)
    )
    need(len(reconstructed) == 12 and end - start == 7,
         "SINGLE_SAVER_FIVE_BYTE_FRAME_EXPANSION_REQUIRED")
    new_stackmap = src_table[:start] + reconstructed + src_table[end:]
    _single_saver_frame_layout(new_stackmap, candidate_cp, original=True)
    need(len(new_stackmap) == len(src_table) + 5,
         "NONMETADATA_OR_MULTIPLE_FRAMES_MODIFIED")

    cp, method_start, methods_end, count, methods = _class_method_layout(
        candidate_classfile)
    rebuilt = bytearray(candidate_classfile[:method_start] + u2(count))
    methods_changed = 0
    for access, name, desc, raw, attrs, _ in methods:
        rebuilt.extend(raw[:8])
        for idx, label, body in attrs:
            if (access == 10 and name == method_name
                    and desc == "()V" and label == "Code"):
                max_stack, max_locals, code, exc_n, exceptions, code_attrs, sm = (
                    _saver_stackmap_in_code(body, cp))
                need(sm == src_table and code == source_bytes,
                     "SAVER_COMPILED_CODE_CHANGED_DURING_METADATA_REBUILD")
                out = (u2(max_stack) + u2(max_locals)
                       + u4(len(code)) + code
                       + u2(exc_n) + exceptions
                       + u2(len(code_attrs)))
                for a_idx, a_label, a_body in code_attrs:
                    if a_label == "StackMapTable":
                        a_body = new_stackmap
                    out += u2(a_idx) + u4(len(a_body)) + a_body
                body = out
                methods_changed += 1
            rebuilt.extend(u2(idx) + u4(len(body)) + body)
    rebuilt.extend(candidate_classfile[methods_end:])
    need(methods_changed == 1,
         "EXACT_ONE_PRIVATE_SAVER_METADATA_REBUILD_REQUIRED")
    normalized = bytes(rebuilt)
    updated_code, updated_cp = _method_code_attribute(
        normalized, method_name)
    need(updated_code[2] == source_bytes
         and updated_code[6] == new_stackmap,
         "PRIVATE_JAVA9_EXECUTABLE_SAVER_CODE_NOT_PRESERVED")
    _single_saver_frame_layout(updated_code[6], updated_cp, original=True)
    return normalized


def normalize_saver_then_require_original_r113(
    original_jar, candidate_jar, owner_entry, output, *,
    original_sha256, candidate_sha256,
):
    original_jar, candidate_jar, output = (
        Path(original_jar), Path(candidate_jar), Path(output))
    need(not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "FRESH_PRIVATE_SAVER_OUTPUT_REQUIRED")
    need(isinstance(owner_entry, str) and owner_entry.endswith(".class")
         and not owner_entry.startswith("/") and "\\" not in owner_entry
         and all(v not in ("", ".", "..") for v in owner_entry.split("/")),
         "ORIGINAL_OWNER_BINARY_CLASS_ENTRY_UNSAFE")
    need(original_jar.resolve() != candidate_jar.resolve(),
         "ORIGINAL_AND_SOURCE_MUST_BE_SEPARATE_JARS")
    for jar, pin in ((original_jar, original_sha256),
                     (candidate_jar, candidate_sha256)):
        need(jar.is_file() and not jar.is_symlink()
             and type(pin) is str
             and re.fullmatch(r"[a-fA-F0-9]{64}", pin)
             and digest(jar) == pin.lower(),
             "ORIGINAL_OR_PRIVATE_CANDIDATE_JAR_SHA256_MISMATCH")
    with ZipFile(original_jar) as src, ZipFile(candidate_jar) as cand:
        old, new = src.namelist(), cand.namelist()
        need(old.count(owner_entry) == new.count(owner_entry) == 1
             and len(old) == len(set(old))
             and len(new) == len(set(new)),
             "ORIGINAL_OR_RECOMPILED_OWNER_JAR_ENTRIES_NOT_UNIQUE")
        original_class = src.read(owner_entry)
        candidate_class = cand.read(owner_entry)
    original_profile = profile_jar_class(original_jar, owner_entry)
    try:
        original_saver = unique_unrecovered(original_profile)[364]
    except (TwoLargeOwnerMethodInventoryError,KeyError) as exc:
        raise SaverFullFrameR116Error(
            "PINNED_ORIGINAL_V309_364_METHOD_NOT_UNIQUE") from exc
    method_name = original_saver["name"]
    need(original_saver.get("access") == 10
         and original_saver.get("descriptor") == "()V",
         "ORIGINAL_364_SAVER_METHOD_ACCESS_NOT_EXACT")
    fixed_class = restore_original_saver_full_frame(
        original_class, candidate_class, method_name)

    with tempfile.TemporaryDirectory(
        prefix="v309-saver-frame-r116-", dir=output.parent,
    ) as temp:
        root = Path(temp)
        provisional = root / "source-frame-normalized.PRIVATE.jar"
        with ZipFile(candidate_jar) as src, ZipFile(provisional, "w") as dest:
            for info in src.infolist():
                dest.writestr(
                    info, fixed_class if info.filename == owner_entry
                    else src.read(info))
        fixed_sha = digest(provisional)
        need(fixed_sha != candidate_sha256.lower()
             and digest(original_jar) == original_sha256.lower()
             and digest(candidate_jar) == candidate_sha256.lower(),
             "PINNED_ORIGINAL_SOURCE_OR_NORMALIZED_CANDIDATE_CHANGED")
        try:
            accepted = accept_original_source_recompiled_saver(
                original_jar, provisional, owner_entry, root / "r113",
                original_sha256=original_sha256,
                candidate_sha256=fixed_sha)
        except (OriginalSaverMethodAcceptanceError,OSError,ValueError) as exc:
            raise SaverFullFrameR116Error(
                "EXACT_ORIGINAL_SAVER_R113_POSTFRAME_PARITY_NOT_ACCEPTED") from exc
        need(accepted.get("original_saver_R66_R81_all_operands_passed")
             is True and
             accepted.get("original_saver_StackMapTable_original_encoding_passed")
             is True and
             accepted.get("original_saver_jvm_StackMapTable_frames_equal") == 10,
             "ORIGINAL_R113_SAVER_CODE_FRAME_PROOF_NOT_COMPLETE")
        report = {
            "schema_version": 1,
            "kind": "private_original_v309_saver_full_frame_metadata_then_R113",
            "original_complete_jar_sha256": original_sha256.lower(),
            "source_javac9_candidate_sha256": candidate_sha256.lower(),
            "saver_frame_normalized_candidate_sha256": fixed_sha,
            "original_saver_jvm_instructions_verified": 364,
            "original_saver_R66_R81_operands_and_handlers_passed": True,
            "original_saver_StackMapTable_frames_exact": 10,
            "saver_original_executable_Code_transferred": False,
            "candidate_saver_Code_bytes_preserved": True,
            "original_loader_697_StackMap_metadata_accepted": False,
            "complete_original_owner_R107_accepted": False,
            "whole_original_client_runtime_equivalence_certified": False,
        }
        dest=root/"accepted"
        dest.mkdir()
        (dest/"original-364-saver-R113-after-StackMap.aggregate.json").write_text(
            json.dumps(report,sort_keys=True,indent=2)+"\n",
            encoding="utf-8")
        import shutil
        shutil.copyfile(provisional,dest/"candidate.saver-frame.PRIVATE.jar")
        need(not output.exists(),"PRIVATE_OUTPUT_OCCUPIED_AFTER_R113")
        os.rename(dest,output)
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for item in ("original_jar","candidate_jar","owner_entry",
                 "new_private_output"):
        p.add_argument(item)
    p.add_argument("--original-sha256",required=True)
    p.add_argument("--candidate-sha256",required=True)
    args=p.parse_args(argv)
    try:
        print(json.dumps(normalize_saver_then_require_original_r113(
            args.original_jar,args.candidate_jar,args.owner_entry,
            args.new_private_output,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256),sort_keys=True))
    except (SaverFullFrameR116Error,BytecodeProfileError,OSError,
            ValueError,IndexError,KeyError,TypeError):
        p.error("PRIVATE_R116_ORIGINAL_JAVA9_SAVER_FRAME_R113_NOT_ACCEPTED")


if __name__=="__main__":
    main()
