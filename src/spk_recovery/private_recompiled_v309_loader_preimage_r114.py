"""R114: actual original-v309 697-op loader R66/R81 + honest StackMap frontier.

Bounded Java9 source-recompiled 697-instruction candidate must match all
original JVM instruction operands, 120 branch edges, 44 typed exception
handlers and 78 ordered static field stores. Original and candidate both have
161 frames at identical JVM *instruction ordinals*, but the source compiler
still differs in verification-frame encoding and local payloads.
This is a PREIMAGE source frontier, NEVER full StackMap or R107 acceptance.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import tempfile
from zipfile import ZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .private_original_fourth_enum_accessors import digest
from .private_large_owner_methods_inventory_r112 import (
    TwoLargeOwnerMethodInventoryError, unique_unrecovered,
)
from .whole_method_operand_parity import (
    WholeMethodOperandError, compare_all_method_operands,
)


class OriginalLoaderR114Error(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise OriginalLoaderR114Error(reason)


def frame_kind(frame):
    typ = frame.get("frame_type")
    need(type(typ) is int, "LOADER_STACKMAP_FRAME_TYPE_UNAVAILABLE")
    if typ <= 63 or typ == 251:
        return "same"
    if 64 <= typ <= 127 or typ == 247:
        return "stack_one"
    if 248 <= typ <= 250:
        return "chop_" + str(251 - typ)
    if 252 <= typ <= 254:
        return "append_" + str(typ - 251)
    if typ == 255:
        return "full"
    raise OriginalLoaderR114Error("LOADER_FRAME_ENCODING_RESERVED")


def frame_ordinals(method):
    rows = method.get("instructions")
    frames = method.get("stackmap_frames")
    need(type(rows) is list and type(frames) is list
         and len(rows) == 697 and len(frames) == 161
         and method.get("stackmap_table_present") is True,
         "ORIGINAL_CANDIDATE_LOADER_697_OP_161_FRAME_REQUIRED")
    offset_index = {ins.get("offset"): index for index, ins in enumerate(rows)}
    need(len(offset_index) == 697 and
         list(offset_index) == sorted(offset_index) and
         all(type(x) is int for x in offset_index),
         "LOADER_INSTRUCTION_BYTECODE_OFFSETS_UNORDERED")
    recorded = []
    for frame in frames:
        offset = frame.get("bytecode_offset")
        need(type(offset) is int and offset in offset_index,
             "STACKMAP_FRAME_NOT_AT_VALID_INSTRUCTION_BOUNDARY")
        recorded.append(offset_index[offset])
    need(recorded == sorted(set(recorded)),
         "STACKMAP_FRAME_ORDINALS_NOT_UNIQUE_AND_ORDERED")
    return recorded


def original_697_loader_source_frontier(original, source_compiled):
    need(original.get("internal_name") ==
             source_compiled.get("internal_name")
         and original.get("classfile_major") ==
             source_compiled.get("classfile_major") == 53
         and original.get("class_access") ==
             source_compiled.get("class_access")
         and original.get("super_name") ==
             source_compiled.get("super_name"),
         "ORIGINAL_CANDIDATE_JAVA9_OWNER_IDENTITY_MISMATCH")
    try:
        originals = unique_unrecovered(original)
    except TwoLargeOwnerMethodInventoryError as exc:
        raise OriginalLoaderR114Error(
            "PINNED_ORIGINAL_126_FIELD_TEN_METHOD_INVENTORY_CHANGED") from exc
    old = originals[697]
    key = old["name"], old["descriptor"]
    need(key[1] == "()V" and old.get("access") == 9,
         "ORIGINAL_697_LOADER_MUST_BE_PUBLIC_STATIC_VOID")
    rows = [m for m in source_compiled.get("methods", [])
            if (m.get("name"), m.get("descriptor")) == key]
    need(len(rows) == 1, "RECOMPILED_697_METHOD_JVM_IDENTITY_MISSING_OR_DUPLICATE")
    new = rows[0]
    need(new.get("access") == old.get("access") and
         len(new.get("instructions") or []) == 697 and
         old.get("max_stack") == new.get("max_stack") == 4 and
         old.get("max_locals") == new.get("max_locals") == 6,
         "ORIGINAL_CANDIDATE_LOADER_697_HEADER_STACK_LOCALS_WRONG")
    try:
        parity = compare_all_method_operands(
            original, key[0], key[1],
            source_compiled, key[0], key[1], [], [], [])
    except (WholeMethodOperandError, ValueError, IndexError,
            KeyError, TypeError) as exc:
        raise OriginalLoaderR114Error(
            "R66_R81_FULL_697_JVM_OPERAND_AND_CFG_MISMATCH") from exc
    need(parity.get("original_instructions_with_all_semantic_operands_compared")
         == 697 and
         parity.get("original_explicit_branches") == 120 and
         parity.get("original_ordered_typed_exception_entries") == 44 and
         parity.get("original_ordered_static_writes") == 78 and
         parity.get("all_parsed_JVM_operands_equal_with_private_aliases")
         is True and
         parity.get("original_invokedynamic_bootstrap_semantics_equal")
         is True,
         "ORIGINAL_697_R81_EXACT_METHOD_COUNTS_NOT_VERIFIED")

    a, b = frame_ordinals(old), frame_ordinals(new)
    need(a == b, "ORIGINAL_CANDIDATE_161_FRAMES_NOT_ORDINAL_ALIGNED")
    orig_frames, new_frames = old["stackmap_frames"], new["stackmap_frames"]
    categories = sum(frame_kind(x) != frame_kind(y)
                     for x, y in zip(orig_frames, new_frames))
    explicit_locals = sum(
        x.get("locals") != y.get("locals")
        or x.get("appended_locals") != y.get("appended_locals")
        for x, y in zip(orig_frames, new_frames)
    )
    stack_payloads = sum(x.get("stack") != y.get("stack")
                         for x, y in zip(orig_frames, new_frames))
    # These exact 2026-10-13 original-vs-Java9-source *preimage*
    # differences are evidence of remaining recovery work, not a gate
    # to pretend the candidate already equals the original verifier data.
    need(categories == 4 and explicit_locals == 2
         and stack_payloads == 0,
         "SOURCE_PREIMAGE_VERIFICATION_FRAMES_NOT_THE_PINNED_FRONTIER")
    need(old.get("exception_handlers") is not None and
         new.get("exception_handlers") is not None,
         "LOADER_ORIGINAL_TYPED_HANDLER_TABLE_NOT_AVAILABLE")
    return {
        "original_697_loader_jvm_instructions_R81_compared": 697,
        "original_loader_branch_ordinals_equal": 120,
        "original_loader_ordered_typed_handlers_equal": 44,
        "original_loader_ordered_static_writes_equal": 78,
        "original_loader_stackmap_frames_each": 161,
        "original_loader_stackmap_ordinal_destinations_equal": 161,
        "original_loader_stackmap_frame_encoding_category_differences": categories,
        "original_loader_stackmap_explicit_local_payload_differences": explicit_locals,
        "original_loader_stackmap_stack_payload_differences": stack_payloads,
        "R66_R81_original_loader_opcodes_cfg_operands_accepted": True,
        "R114_exact_original_StackMap_encoding_accepted": False,
        "original_loader_java_source_authorial_identity_proven": False,
        "R94_all_original_nine_owner_methods_accepted": False,
        "R107_complete_owner_accepted": False,
        "original_helpers_runtime_behavior_proven": False,
        "whole_original_client_runtime_equivalence_certified": False,
    }


def accept_original_recompiled_loader_preimage(
    original_jar, source_candidate_jar, owner_entry, output, *,
    original_sha256, candidate_sha256,
):
    original_jar, source_candidate_jar, output = (
        Path(original_jar), Path(source_candidate_jar), Path(output))
    need(not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "NEW_PRIVATE_ORIGINAL_LOADER_REPORT_REQUIRED")
    need(type(owner_entry) is str and owner_entry.endswith(".class")
         and not owner_entry.startswith("/") and "\\" not in owner_entry
         and all(x not in ("", ".", "..") for x in owner_entry.split("/")),
         "ORIGINAL_LOADER_OWNER_ARCHIVE_ENTRY_UNSAFE")
    need(original_jar.resolve() != source_candidate_jar.resolve(),
         "ORIGINAL_V309_JAR_MUST_NOT_BE_SOURCE_CANDIDATE")
    for p, pin in ((original_jar, original_sha256),
                   (source_candidate_jar, candidate_sha256)):
        need(p.is_file() and not p.is_symlink()
             and type(pin) is str
             and re.fullmatch(r"[0-9a-fA-F]{64}", pin)
             and digest(p) == pin.lower(),
             "PINNED_ORIGINAL_OR_SOURCE_CANDIDATE_SHA256_MISMATCH")
        with ZipFile(p) as z:
            rows=z.namelist()
            need(rows.count(owner_entry)==1 and len(rows)==len(set(rows)),
                 "ORIGINAL_OR_SOURCE_OWNER_JVM_ENTRY_NOT_UNIQUE")
    original = profile_jar_class(original_jar, owner_entry)
    candidate = profile_jar_class(source_candidate_jar, owner_entry)
    need(original.get("internal_name") + ".class" == owner_entry
         and candidate.get("internal_name") + ".class" == owner_entry,
         "ORIGINAL_JAVA9_OWNER_INTERNAL_IDENTITY_DIFFERENT")
    result = original_697_loader_source_frontier(original, candidate)
    need(digest(original_jar) == original_sha256.lower()
         and digest(source_candidate_jar) == candidate_sha256.lower(),
         "PINNED_OWNER_JARS_CHANGED_DURING_R114")
    report = {
        "schema_version": 1,
        "kind": "private_actual_original_v309_697_loader_source_preimage_r114",
        "original_complete_jar_sha256": original_sha256.lower(),
        "candidate_source_compiled_jar_sha256": candidate_sha256.lower(),
        "research_only": True,
        **result,
    }
    with tempfile.TemporaryDirectory(
        prefix="v309-R114-preimage-", dir=output.parent) as td:
        stage=Path(td)/"accepted"
        stage.mkdir()
        with (stage/"697-loader-source-preimage.aggregate.json").open(
             "x", encoding="utf-8", newline="\n") as out:
            json.dump(report, out, indent=2, sort_keys=True)
            out.write("\n")
        need(not output.exists(), "PRIVATE_OUTPUT_ALREADY_EXISTS_AFTER_GATE")
        os.rename(stage, output)
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("original_jar","source_candidate_jar","owner_entry",
                 "new_private_output"):
        p.add_argument(name)
    p.add_argument("--original-sha256",required=True)
    p.add_argument("--candidate-sha256",required=True)
    a=p.parse_args(argv)
    try:
        proof=accept_original_recompiled_loader_preimage(
            a.original_jar, a.source_candidate_jar,
            a.owner_entry, a.new_private_output,
            original_sha256=a.original_sha256,
            candidate_sha256=a.candidate_sha256)
        print(json.dumps(proof,sort_keys=True))
    except (OriginalLoaderR114Error,BytecodeProfileError,OSError,
            ValueError,TypeError,KeyError,IndexError):
        p.error("PRIVATE_R114_ORIGINAL_697_LOADER_PREIMAGE_NOT_ACCEPTED")


if __name__=="__main__":
    main()
