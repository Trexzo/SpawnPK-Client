"""R113: pinned original-v309 364-op saver vs source-compiled Java9 witness.

Require R66 CFG/ordered handler parity, R81 every JVM operand incl. original
StringConcatFactory recipes, and exact ORIGINAL 10-entry StackMapTable encoding
after a separate *metadata-only* source-frame restoration.

This verifier does not copy original executable method Code, compile sources,
execute the original JAR, prove original external helper bodies or certify the
complete 697-op loader / ten-method owner.
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
from .private_large_owner_methods_inventory_r112 import (
    TwoLargeOwnerMethodInventoryError, unique_unrecovered,
)
from .private_original_fourth_enum_accessors import digest
from .whole_method_operand_parity import (
    WholeMethodOperandError, compare_all_method_operands,
)


class OriginalSaverMethodAcceptanceError(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise OriginalSaverMethodAcceptanceError(reason)


def original_saver_method_profile_proof(original, compiled):
    need(original.get("internal_name") == compiled.get("internal_name")
         and original.get("classfile_major") ==
             compiled.get("classfile_major") == 53
         and original.get("class_access") ==
             compiled.get("class_access")
         and original.get("super_name") ==
             compiled.get("super_name"),
         "ORIGINAL_V309_OWNER_CLASS_IDENTITY_NOT_EQUAL")
    try:
        large = unique_unrecovered(original)
    except TwoLargeOwnerMethodInventoryError as exc:
        raise OriginalSaverMethodAcceptanceError(
            "ORIGINAL_126FIELD_TENMETHOD_INVENTORY_NOT_PROVEN") from exc
    original_method = large[364]
    key = original_method["name"], original_method["descriptor"]
    need(key[1] == "()V" and original_method.get("access") == 10
         and len(original_method.get("instructions") or []) == 364,
         "ORIGINAL_PRIVATE_STATIC_SAVER_NOT_364_OP")
    candidates = [m for m in compiled.get("methods", [])
                  if (m.get("name"), m.get("descriptor")) == key]
    need(len(candidates) == 1,
         "SOURCE_COMPILED_SAVER_ORIGINAL_JVM_IDENTITY_NOT_UNIQUE")
    candidate_method = candidates[0]
    need(candidate_method.get("access") == 10
         and candidate_method.get("signature") ==
             original_method.get("signature")
         and candidate_method.get("code_length") ==
             original_method.get("code_length") == 929
         and candidate_method.get("max_stack") ==
             original_method.get("max_stack") == 6
         and candidate_method.get("max_locals") ==
             original_method.get("max_locals") == 3,
         "SOURCE_JAVA9_364_SAVER_METHOD_ACCESS_OR_CODE_FRAME_NOT_EXACT")
    need(len(candidate_method.get("instructions") or []) == 364,
         "SOURCE_JAVA9_364_SAVER_METHOD_INSTRUCTION_COUNT_WRONG")

    try:
        comparison = compare_all_method_operands(
            original, key[0], key[1], compiled, key[0], key[1],
            [], [], [])
    except (WholeMethodOperandError, ValueError, IndexError, TypeError,
            KeyError) as exc:
        raise OriginalSaverMethodAcceptanceError(
            "ORIGINAL_R66_R81_364_METHOD_OPERANDS_NOT_ACCEPTED") from exc
    need(comparison.get(
             "original_instructions_with_all_semantic_operands_compared")
         == 364
         and comparison.get("original_ordered_typed_exception_entries") == 1
         and comparison.get("original_explicit_branches") == 9
         and comparison.get("original_ordered_static_writes") == 0
         and comparison.get("all_parsed_JVM_operands_equal_with_private_aliases")
         is True
         and comparison.get(
             "original_invokedynamic_bootstrap_semantics_equal") is True,
         "R66_R81_ORIGINAL_364_SAVER_METHOD_EVIDENCE_NOT_EXACT")
    need(original_method.get("stackmap_table_present") is True
         and candidate_method.get("stackmap_table_present") is True,
         "EXACT_ORIGINAL_SAVER_STACKMAP_TABLE_MISSING")
    expected = original_method.get("stackmap_frames")
    actual = candidate_method.get("stackmap_frames")
    need(type(expected) is list and len(expected) == 10
         and [x.get("frame_type") for x in expected] ==
             [252, 255, 36, 250, 251, 23, 23, 251, 255, 4],
         "EXPECTED_ORIGINAL_364_SAVER_STACKMAP_ENCODINGS_CHANGED")
    need(actual == expected,
         "ORIGINAL_364_SAVER_ALL_TEN_STACKMAP_FRAMES_NOT_EXACT")
    need(original_method.get("exception_handlers") ==
             candidate_method.get("exception_handlers")
         and len(original_method["exception_handlers"]) == 1,
         "ORIGINAL_364_SAVER_EXCEPTION_REGION_NOT_EXACT")

    return {
        "original_saver_method_jvm_instructions": 364,
        "original_saver_all_jvm_instruction_operands_R81_compared": 364,
        "original_saver_explicit_branch_edges": 9,
        "original_saver_ordered_typed_handlers": 1,
        "original_saver_jvm_StackMapTable_frames_equal": 10,
        "original_saver_method_code_length": 929,
        "original_saver_max_stack": 6,
        "original_saver_max_locals": 3,
        "original_saver_R66_R81_all_operands_passed": True,
        "original_saver_StackMapTable_original_encoding_passed": True,
        "original_saver_original_executable_Code_copied": False,
        "original_saver_external_helper_bodies_proven": False,
        "original_loader_697_op_source_recovered": False,
        "original_complete_ten_owner_methods_R94_passed": False,
        "original_complete_owner_R107_passed": False,
        "whole_original_client_runtime_equivalence_certified": False,
    }


def accept_original_source_recompiled_saver(
    original_jar, candidate_jar, owner_entry, output, *,
    original_sha256, candidate_sha256,
):
    original_jar, candidate_jar, output = map(
        Path, (original_jar, candidate_jar, output))
    need(not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "FRESH_PRIVATE_SAVER_REPORT_REQUIRED")
    need(type(owner_entry) is str and owner_entry.endswith(".class")
         and not owner_entry.startswith("/") and "\\" not in owner_entry
         and all(x not in ("", ".", "..") for x in owner_entry.split("/")),
         "ORIGINAL_OWNER_CLASS_ENTRY_UNSAFE")
    need(original_jar.resolve() != candidate_jar.resolve(),
         "ORIGINAL_AND_SOURCE_CANDIDATE_MUST_BE_SEPARATE_JARS")
    for path, pin in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        need(path.is_file() and not path.is_symlink()
             and isinstance(pin, str)
             and re.fullmatch(r"[0-9a-fA-F]{64}", pin)
             and digest(path) == pin.lower(),
             "COMPLETE_ORIGINAL_OR_SOURCE_CANDIDATE_SHA256_MISMATCH")
    with ZipFile(original_jar) as old, ZipFile(candidate_jar) as new:
        need(old.namelist().count(owner_entry) == 1
             and new.namelist().count(owner_entry) == 1
             and len(old.namelist()) == len(set(old.namelist()))
             and len(new.namelist()) == len(set(new.namelist())),
             "ORIGINAL_OR_CANDIDATE_OWNER_ARCHIVE_NOT_UNIQUE")
    old = profile_jar_class(original_jar, owner_entry)
    new = profile_jar_class(candidate_jar, owner_entry)
    need(old.get("internal_name") + ".class" == owner_entry
         and new.get("internal_name") + ".class" == owner_entry,
         "ORIGINAL_SOURCE_OWNER_INTERNAL_NAME_NOT_EXACT")
    proof = original_saver_method_profile_proof(old, new)
    need(digest(original_jar) == original_sha256.lower()
         and digest(candidate_jar) == candidate_sha256.lower(),
         "PINNED_ORIGINAL_OR_SOURCE_JAR_CHANGED_DURING_R113")
    report = {
        "schema_version": 1,
        "kind": "private_original_v309_source_compiled_364_saver_R66_R81_StackMap",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "source_compiled_candidate_jar_sha256": candidate_sha256.lower(),
        **proof,
    }
    with tempfile.TemporaryDirectory(
        prefix="v309-saver-original-r113-", dir=output.parent
    ) as temp:
        accepted = Path(temp) / "accepted"
        accepted.mkdir()
        with (accepted / "original-364-saver.aggregate.json").open(
            "x", encoding="utf-8", newline="\n"
        ) as stream:
            json.dump(report, stream, sort_keys=True, indent=2)
            stream.write("\n")
        need(not output.exists(), "PRIVATE_ORIGINAL_SAVER_OUTPUT_OCCUPIED")
        os.rename(accepted, output)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("original_jar", "candidate_jar", "owner_entry",
                "new_private_output"):
        p.add_argument(arg)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    args = p.parse_args(argv)
    try:
        result = accept_original_source_recompiled_saver(
            args.original_jar, args.candidate_jar, args.owner_entry,
            args.new_private_output,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
        )
        print(json.dumps(result, sort_keys=True))
    except (OriginalSaverMethodAcceptanceError, BytecodeProfileError,
            ValueError, OSError, KeyError, IndexError, TypeError):
        p.error("PRIVATE_ORIGINAL_V309_364_SAVER_R113_NOT_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
