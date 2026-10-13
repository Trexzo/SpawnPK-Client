"""R111: seven original-v309 ordinary owner methods after Java9 recompilation.

Checks source-compiler candidate against a complete pinned original JAR:
constructor, three Boolean methods, state-switch method, callback registration
and 41-instruction int-array setup. Source's 364-op original save helper is
an explicit **one-op PRIVATE STUB**; original 697-op loader is absent.
The two source-only outer Java helper methods used to trigger inner-class
accessor generation are likewise unresolved extras, NOT original owner code.

Requires R110's exact 93-write/213-instruction original <clinit> preflight.
Never declare R94/R107, original helper/runtime or gameplay equivalence.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import tempfile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .clinit_operand_semantic_witness import _bootstrap
from .private_original_fourth_enum_accessors import digest
from .private_original_93write_initializer_source_preflight_r110 import (
    OriginalInitializerSourcePreflightError,
    compare_original_93write_source_preflight,
)


class SevenOwnerMethodsSourceError(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise SevenOwnerMethodsSourceError(code)


def by_signature(profile):
    entries = profile.get("methods")
    need(isinstance(entries, list), "OWNER_METHOD_INVENTORY_REQUIRED")
    result = {}
    for m in entries:
        key = m.get("name"), m.get("descriptor")
        need(all(type(v) is str for v in key)
             and key not in result, "DUPLICATE_OWNER_METHOD_SIGNATURE")
        result[key] = m
    return result


def _ord_branch(rows):
    where = {r["offset"]: index for index, r in enumerate(rows)}
    results = []
    for index, row in enumerate(rows):
        opcode = row.get("opcode")
        if opcode not in ("0x99", "0x9a", "0xa6", "0xa7"):
            continue
        dest = row.get("branch_target_offset")
        need(type(dest) is int and dest in where,
             "SMALL_METHOD_BRANCH_TARGET_NOT_A_JVM_INSTRUCTION")
        results.append((index, opcode, where[dest]))
    return results


def _semantic_small_method(original_profile, candidate_profile, a, b):
    old, new = a.get("instructions"), b.get("instructions")
    need(isinstance(old, list) and isinstance(new, list)
         and len(old) == len(new), "SEVEN_METHOD_CODE_LENGTH_DIFFERENT")
    need([x.get("opcode") for x in old]
         == [x.get("opcode") for x in new],
         "SMALL_ORIGINAL_OWNER_OPCODE_SEQUENCE_DIFFERENT")
    need(a.get("access") == b.get("access")
         and a.get("descriptor") == b.get("descriptor")
         and a.get("signature") == b.get("signature")
         and a.get("max_stack") == b.get("max_stack")
         and a.get("max_locals") == b.get("max_locals")
         and a.get("exception_handlers") == b.get("exception_handlers"),
         "ORIGINAL_SMALL_METHOD_HEADER_STACK_OR_EXCEPTION_DIFFERENT")
    need(_ord_branch(old) == _ord_branch(new),
         "ORIGINAL_SMALL_METHOD_BRANCH_DESTINATION_DIFFERENT")

    owner = original_profile.get("internal_name")
    for left, right in zip(old, new):
        op = left["opcode"]
        if op in ("0xb2", "0xb3", "0xb8", "0xb7"):
            need(all(left.get(x) == right.get(x)
                     for x in ("owner", "name", "descriptor")),
                 "SMALL_OWNER_FIELD_OR_METHOD_REFERENCE_DIFFERENT")
            # Same-owner statics and external field/helper declarations are
            # constrained symbolically, never executed from original JAR.
            if op == "0xb3":
                need(left.get("owner") == owner or
                     (type(left.get("owner")) is str
                      and left.get("owner") != owner),
                     "ORIGINAL_SMALL_METHOD_STORE_OWNER_INVALID")
        if op in ("0x10", "0x11"):
            need(left.get("int_constant") == right.get("int_constant"),
                 "ORIGINAL_SMALL_METHOD_IMMEDIATE_DIFFERENT")
        if op in ("0x12", "0x13"):
            need(left.get("constant_pool_tag") ==
                     right.get("constant_pool_tag")
                 and left.get("constant") == right.get("constant"),
                 "ORIGINAL_SMALL_METHOD_LITERAL_DIFFERENT")
        if op == "0xba":
            need(left.get("name") == right.get("name")
                 and left.get("descriptor") == right.get("descriptor")
                 and _bootstrap(
                     original_profile,
                     left.get("bootstrap_method_attr_index")) ==
                     _bootstrap(
                         candidate_profile,
                         right.get("bootstrap_method_attr_index")),
                 "ORIGINAL_CALLBACK_LAMBDA_BOOTSTRAP_OR_TARGET_NOT_EXACT")
    return len(old)


def prove_original_seven_small_methods(
    original, candidate, *, source_nested_type, original_nested_type,
):
    full = compare_original_93write_source_preflight(
        original, candidate,
        candidate_nested_type=source_nested_type,
        original_nested_type=original_nested_type)
    need(full.get("original_initializer_writes_in_original_order_compared") == 93
         and full.get("original_candidate_jvm_instructions_compared") == 213
         and full.get("strict_R58_original_all_operands_certified") is False,
         "R110_COMPLETE_ORIGINAL_INITIALIZER_SOURCE_PREFLIGHT_REQUIRED")
    old, new = by_signature(original), by_signature(candidate)
    need(len(old) == 10
         and sorted(len(m.get("instructions") or []) for m in old.values()) ==
             [2, 2, 2, 3, 4, 20, 41, 213, 364, 697],
         "ORIGINAL_TEN_METHOD_V309_SIGNATURE_SHAPES_CHANGED")
    small = {key: m for key, m in old.items()
             if key[0] != "<clinit>"
             and len(m.get("instructions", [])) in (2, 3, 4, 20, 41)}
    need(len(small) == 7 and all(key in new for key in small),
         "SEVEN_ORIGINAL_ORDINARY_OWNER_METHODS_NOT_PRESENT")
    counts = sorted(
        _semantic_small_method(original, candidate, m, new[key])
        for key, m in small.items()
    )
    need(counts == [2, 2, 2, 3, 4, 20, 41],
         "SEVEN_SMALL_OWNER_METHOD_OPCODE_COUNTS_NOT_EXACT")
    big364 = [(key, m) for key, m in old.items()
              if len(m.get("instructions") or []) == 364]
    big697 = [(key, m) for key, m in old.items()
              if len(m.get("instructions") or []) == 697]
    need(len(big364) == len(big697) == 1,
         "TWO_UNRECOVERED_ORIGINAL_LARGE_METHODS_NOT_UNIQUE")
    key364, key697 = big364[0][0], big697[0][0]
    need(key364 in new
         and [r.get("opcode") for r in new[key364].get("instructions", [])]
             == ["0xb1"]
         and key697 not in new,
         "ORIGINAL_364_METHOD_PLACEHOLDER_OR_MISSING_697_NOT_EXACT")
    # Two provisional outer helpers trigger javac's fourth-enum getter
    # accessor generation. R107 MUST reject these extras after source recovery.
    source_extras = set(new) - set(old)
    target_descriptor = "(L" + source_nested_type + ";)Ljava/lang/String;"
    need(len(source_extras) == 2
         and all(new[key].get("access") == 9
                 and new[key].get("descriptor") == target_descriptor
                 and len(new[key].get("instructions", [])) == 3
                 for key in source_extras),
         "EXACT_TWO_SOURCE_ONLY_PROVISIONAL_PRIVATE_ACCESS_HELPERS_REQUIRED")
    need(len(new) == 11 and ("<clinit>", "()V") in new,
         "CANDIDATE_NINE_ORIGINAL_AND_TWO_SOURCE_HELPER_METHODS_REQUIRED")
    return {
        "original_small_owner_methods_opcode_verified": 7,
        "original_small_owner_method_instructions_verified": sum(counts),
        "original_small_owner_method_opcounts": counts,
        "original_callback_lambda_bootstrap_semantics_compared": 1,
        "original_owner_93_store_initializer_preflight_passed": True,
        "provisional_original_364_instruction_method_body_is_stub": True,
        "provisional_original_697_instruction_method_is_absent": True,
        "source_only_provisional_outer_helper_methods": 2,
        "original_owner_full_method_declarations_recovered": False,
        "R94_all_nine_owner_methods_accepted": False,
        "R58_full_initialization_and_members_accepted": False,
        "R107_complete_owner_source_accepted": False,
        "external_stub_helper_behavior_original": False,
        "whole_client_runtime_equivalence_certified": False,
    }


def replay_private_v309_seven_owner_method_preflight(
    original_jar, candidate_jar, owner_entry, source_surrogate,
    fresh_output, *, original_sha256, candidate_sha256,
):
    original_jar, candidate_jar, fresh_output = map(
        Path, (original_jar, candidate_jar, fresh_output))
    need(fresh_output.parent.is_dir() and
         not fresh_output.parent.is_symlink() and
         not fresh_output.exists() and
         not fresh_output.is_symlink(), "FRESH_PRIVATE_R111_OUTPUT_REQUIRED")
    for path, pin in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        need(path.is_file() and not path.is_symlink()
             and type(pin) is str
             and re.fullmatch("[0-9a-fA-F]{64}", pin)
             and digest(path) == pin.lower(),
             "EXACT_ORIGINAL_V309_AND_SOURCE_CANDIDATE_SHA_REQUIRED")
    need(type(owner_entry) is str and owner_entry.endswith(".class")
         and not owner_entry.startswith("/") and "\\" not in owner_entry
         and all(x not in ("", ".", "..")
                 for x in owner_entry.split("/"))
         and type(source_surrogate) is str
         and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*",
                          source_surrogate),
         "ORIGINAL_OWNER_OR_SOURCE_SURROGATE_ENTRY_UNSAFE")
    owner = owner_entry[:-6]
    original_nested = owner + "$" + owner.rsplit("/", 1)[-1]
    candidate_nested = owner + "$" + source_surrogate
    need(original_nested != candidate_nested,
         "SOURCE_INVALID_FOURTH_ENUM_NESTED_NAME_COLLISION_NOT_PRESENT")
    original = profile_jar_class(original_jar, owner_entry)
    candidate = profile_jar_class(candidate_jar, owner_entry)
    proof = prove_original_seven_small_methods(
        original, candidate,
        source_nested_type=candidate_nested,
        original_nested_type=original_nested)
    need(digest(original_jar) == original_sha256.lower()
         and digest(candidate_jar) == candidate_sha256.lower(),
         "PINNED_SOURCE_OR_ORIGINAL_CHANGED_DURING_SEVEN_METHOD_PROOF")
    report = {
        "schema_version": 1,
        "kind": "private_v309_seven_ordinary_methods_93write_compiler_preflight",
        "original_complete_jar_sha256": original_sha256.lower(),
        "source_compiled_candidate_sha256": candidate_sha256.lower(),
        **proof,
    }
    with tempfile.TemporaryDirectory(
        prefix="v309-r111-seven-owner-", dir=fresh_output.parent
    ) as temp:
        accepted = Path(temp) / "accepted"
        accepted.mkdir()
        (accepted / "seven-small-owner-methods.aggregate.json").write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        need(not fresh_output.exists(),
             "OUTPUT_OCCUPIED_DURING_SEVEN_METHOD_PREFLIGHT")
        os.rename(accepted, fresh_output)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("original_jar", "candidate_jar", "owner_entry",
                  "source_surrogate", "new_private_output"):
        p.add_argument(field)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(replay_private_v309_seven_owner_method_preflight(
            a.original_jar, a.candidate_jar, a.owner_entry,
            a.source_surrogate, a.new_private_output,
            original_sha256=a.original_sha256,
            candidate_sha256=a.candidate_sha256), sort_keys=True))
    except (SevenOwnerMethodsSourceError,
            OriginalInitializerSourcePreflightError, BytecodeProfileError,
            ValueError, OSError, KeyError, IndexError, TypeError):
        p.error("PRIVATE_V309_R111_SEVEN_METHOD_ORIGINAL_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
