"""R110: exact-original v309 93-store Java9 source compilation preflight.

A source-recompiled 126-field v309 owner may represent the complete 213-op
initializer with two compiler-chosen ldc vs ldc_w widths and an unavoidable
nested enum class-name collision. Check exact 126 original field declarations,
33 ConstantValue initializers, 85 mutable and eight final writes, 93 ordered
putstatic targets, all 213 opcode roles, branch destination ordinals and
all three original StringConcatFactory bootstrap recipes.

Synthetic fourth-enum accessor names and nested constant members are not yet
original identity: this is NOT R105/R58/R94/R95/R107 acceptance. Final
original operand parity must be proved independently after R105 post-javac.
No private member IDs, literal values or source fragments are printed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .clinit_operand_semantic_witness import _bootstrap
from .private_original_fourth_enum_accessors import digest


class OriginalInitializerSourcePreflightError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise OriginalInitializerSourcePreflightError(reason)


def _nested_type(value, candidate_type, original_type):
    if value is None:
        return None
    need(type(value) is str, "INVALID_SOURCE_NESTED_TYPE_SYMBOL")
    return value.replace(candidate_type, original_type)


def _fields(profile, candidate_type, original_type):
    fields = profile.get("fields")
    need(isinstance(fields, list) and len(fields) == 126,
         "ORIGINAL_126_DECLARED_SOURCE_FIELDS_REQUIRED")
    entries = []
    for f in fields:
        need(type(f.get("name")) is str
             and type(f.get("access")) is int
             and type(f.get("descriptor")) is str,
             "UNRESOLVED_SOURCE_FIELD_DECLARATION")
        entries.append((
            f["name"],
            _nested_type(f["descriptor"], candidate_type, original_type),
            f["access"],
            _nested_type(f.get("signature"), candidate_type, original_type),
            f.get("constant_value"),
        ))
    need(len(set((x[0], x[1]) for x in entries)) == 126,
         "DUPLICATE_FIELD_IDENTITY")
    need(sum(f[2] == 9 for f in entries) == 85
         and sum(f[2] == 25 for f in entries) == 41
         and sum(f[2] == 25 and f[4] is not None for f in entries) == 33
         and sum(f[2] == 25 and f[4] is None for f in entries) == 8,
         "ORIGINAL_FIELD_ACCESS_AND_CONSTANT_SHAPE_DIFFERENT")
    return entries


def _clinit(profile):
    methods = profile.get("methods")
    need(isinstance(methods, list), "METHOD_INVENTORY_REQUIRED")
    hit = [m for m in methods
           if m.get("name") == "<clinit>" and
           m.get("descriptor") == "()V" and m.get("access") == 8]
    need(len(hit) == 1, "ONE_STATIC_INITIALIZER_REQUIRED")
    m = hit[0]
    rows = m.get("instructions")
    need(isinstance(rows, list) and len(rows) == 213
         and all(isinstance(row, dict) and
                 type(row.get("offset")) is int and
                 type(row.get("length")) is int and row["length"] > 0 and
                 type(row.get("opcode")) is str
                 for row in rows)
         and len({row["offset"] for row in rows}) == 213
         and [row["offset"] for row in rows] ==
             sorted(row["offset"] for row in rows),
         "ORIGINAL_213_ORDERED_CLINIT_INSTRUCTIONS_REQUIRED")
    need(m.get("max_stack") == 2 and m.get("max_locals") == 0
         and m.get("exception_handlers") == [],
         "ORIGINAL_CLINIT_STACK_LOCAL_OR_HANDLERS_CHANGED")
    need(rows[-1]["opcode"] == "0xb1", "CLINIT_VOID_RETURN_MISSING")
    return rows


def _branch_ordinal_map(rows):
    offsets = {r["offset"]: i for i, r in enumerate(rows)}
    result = []
    for i, row in enumerate(rows):
        if row["opcode"] not in ("0xa6", "0x9a", "0xa7"):
            continue
        dest = row.get("branch_target_offset")
        need(type(dest) is int and dest in offsets,
             "ORIGINAL_CLINIT_BRANCH_DESTINATION_NOT_AN_INSTRUCTION")
        result.append((i, row["opcode"], offsets[dest]))
    return result


def _own_writes(profile, rows, candidate_type, original_type, fields):
    owner = profile.get("internal_name")
    need(type(owner) is str and owner, "INVALID_OWNER_BINARY_NAME")
    fields_by_name = {(name, desc): (flags, cv)
                      for name, desc, flags, _, cv in fields}
    writes = []
    seen = set()
    for row in rows:
        if row["opcode"] != "0xb3":
            continue
        name, desc, target = (
            row.get("name"), row.get("descriptor"), row.get("owner"))
        need(target == owner and type(name) is str
             and type(desc) is str,
             "EXTERNAL_OR_UNRESOLVED_ORIGINAL_CLINIT_PUTSTATIC")
        key = name, _nested_type(desc, candidate_type, original_type)
        need(key in fields_by_name, "STORE_TARGET_NOT_AN_ORIGINAL_DECLARATION")
        need(key not in seen, "SAME_ORIGINAL_FIELD_WRITTEN_MORE_THAN_ONCE")
        seen.add(key)
        access, value = fields_by_name[key]
        need(access in (9, 25) and (access != 25 or value is None),
             "ORIGINAL_CONSTANTVALUE_MUST_NOT_BE_WRITTEN")
        writes.append(key)
    need(len(writes) == 93
         and sum(fields_by_name[key][0] == 9 for key in writes) == 85
         and sum(fields_by_name[key][0] == 25 for key in writes) == 8,
         "EXACT_85_MUTABLE_AND_8_FINAL_INITIALIZER_STORES_REQUIRED")
    return writes


def compare_original_93write_source_preflight(
    original, candidate, *, candidate_nested_type, original_nested_type,
):
    need(original.get("internal_name") == candidate.get("internal_name")
         and original.get("classfile_major") ==
             candidate.get("classfile_major") == 53
         and original.get("super_name") == candidate.get("super_name")
         and original.get("class_access") == candidate.get("class_access"),
         "PINNED_ORIGINAL_JAVA9_OWNER_HEADER_DIFFERENT")
    need(type(candidate_nested_type) is str
         and type(original_nested_type) is str
         and candidate_nested_type != original_nested_type,
         "EXACT_ONE_SOURCE_INVALID_ENUM_ALIAS_REQUIRED")
    o_fields = _fields(original, original_nested_type, original_nested_type)
    c_fields = _fields(candidate, candidate_nested_type, original_nested_type)
    need(o_fields == c_fields, "ORIGINAL_126_FIELD_DECLARATIONS_DIFFER")
    a_rows, b_rows = _clinit(original), _clinit(candidate)
    width = 0
    for a, b in zip(a_rows, b_rows):
        if a["opcode"] == b["opcode"]:
            continue
        need(a["opcode"] == "0x12" and b["opcode"] == "0x13",
             "CLINIT_OPCODE_NOT_A_NARROW_TO_WIDE_LDC")
        width += 1
        need(a.get("constant_pool_tag") == b.get("constant_pool_tag")
             and a.get("constant") == b.get("constant"),
             "CLINIT_LDC_WIDTH_CHANGE_LITERAL_NOT_EXACT")
    need(width == 2, "EXACT_TWO_COMPILER_LDC_WIDTH_DIFFERENCES_REQUIRED")
    need(_branch_ordinal_map(a_rows) == _branch_ordinal_map(b_rows)
         and len(_branch_ordinal_map(a_rows)) == 8,
         "CLINIT_BRANCH_TARGET_ORDINALS_NOT_EXACT")
    a_writes = _own_writes(original, a_rows, original_nested_type,
                          original_nested_type, o_fields)
    b_writes = _own_writes(candidate, b_rows, candidate_nested_type,
                          original_nested_type, c_fields)
    need(a_writes == b_writes,
         "93_ORDERED_ORIGINAL_FIELD_TARGETS_NOT_EXACT")

    indy_a = [r for r in a_rows if r["opcode"] == "0xba"]
    indy_b = [r for r in b_rows if r["opcode"] == "0xba"]
    need(len(indy_a) == len(indy_b) == 3,
         "EXACT_THREE_STRING_CONCAT_BOOTSTRAP_SITES_REQUIRED")
    for x, y in zip(indy_a, indy_b):
        need(x.get("name") == y.get("name")
             and x.get("descriptor") == y.get("descriptor")
             and _bootstrap(original, x.get("bootstrap_method_attr_index"))
                 == _bootstrap(candidate, y.get("bootstrap_method_attr_index")),
             "ORIGINAL_CLINIT_THREE_BOOTSTRAP_RECIPES_NOT_EQUAL")

    source_getstatic = sum(r["opcode"] == "0xb2" for r in b_rows)
    source_invokestatic = sum(r["opcode"] == "0xb8" for r in b_rows)
    need(source_getstatic == 14 and source_invokestatic == 4,
         "CLINIT_UNBOUND_METHOD_FIELD_REFERENCE_SHAPES_DIFFERENT")
    return {
        "original_owner_fields_compared": 126,
        "original_compile_time_field_values_compared": 33,
        "original_nonconstant_final_write_targets_compared": 8,
        "original_mutable_field_write_targets_compared": 85,
        "original_initializer_writes_in_original_order_compared": 93,
        "original_candidate_jvm_instructions_compared": 213,
        "original_source_ldc_to_ldc_w_width_differences": 2,
        "original_initializer_explicit_branch_ordinals_compared": 8,
        "original_StringConcatFactory_recipes_compared": 3,
        "strict_R58_original_all_operands_certified": False,
        "R105_synthetic_accessor_method_ids_rebound": False,
        "R94_original_ten_owner_methods_certified": False,
        "R107_complete_original_owner_accepted": False,
        "original_client_runtime_equivalence_certified": False,
    }


def replay_original_93write_source_preflight(
    original_jar, candidate_jar, owner_entry, candidate_surrogate,
    output, *, original_sha256, candidate_sha256,
):
    original_jar, candidate_jar, output = map(
        Path, (original_jar, candidate_jar, output))
    need(output.parent.is_dir() and not output.parent.is_symlink()
         and not output.exists() and not output.is_symlink(),
         "FRESH_PRIVATE_PREFLIGHT_OUTPUT_REQUIRED")
    need(type(owner_entry) is str and owner_entry.endswith(".class")
         and not owner_entry.startswith("/")
         and "\\" not in owner_entry
         and all(part not in ("", ".", "..")
                 for part in owner_entry.split("/"))
         and type(candidate_surrogate) is str
         and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", candidate_surrogate),
         "PRIVATE_OWNER_ENTRY_OR_SURROGATE_NOT_SAFE")
    need(original_jar.resolve() != candidate_jar.resolve(),
         "CANDIDATE_MUST_BE_INDEPENDENT_JAR")
    for path, sha in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        need(path.is_file() and not path.is_symlink()
             and isinstance(sha, str)
             and re.fullmatch("[0-9a-fA-F]{64}", sha)
             and digest(path) == sha.lower(),
             "EXACT_ORIGINAL_AND_CANDIDATE_SHA256_REQUIRED")
    owner = owner_entry[:-6]
    original_nested = owner + "$" + owner.rsplit("/", 1)[-1]
    candidate_nested = owner + "$" + candidate_surrogate
    need(original_nested != candidate_nested,
         "SOURCE_SURROGATE_MUST_DIFFER_FROM_COLLIDING_ORIGINAL")
    original_profile = profile_jar_class(original_jar, owner_entry)
    candidate_profile = profile_jar_class(candidate_jar, owner_entry)
    need(original_profile.get("internal_name") == owner,
         "ORIGINAL_CLASS_ENTRY_AND_JVM_IDENTITY_DIFFER")
    proof = compare_original_93write_source_preflight(
        original_profile, candidate_profile,
        candidate_nested_type=candidate_nested,
        original_nested_type=original_nested)
    need(digest(original_jar) == original_sha256.lower()
         and digest(candidate_jar) == candidate_sha256.lower(),
         "PINNED_JAR_CHANGED_DURING_PRIVATE_PREFLIGHT")
    report = {
        "schema_version": 1,
        "kind": "private_original_v309_complete_93write_initializer_pre_R105",
        "original_complete_jar_sha256": original_sha256.lower(),
        "source_compiled_candidate_sha256": candidate_sha256.lower(),
        **proof,
    }
    with tempfile.TemporaryDirectory(
        prefix="v309-source-clinit-r110-", dir=output.parent,
    ) as temp:
        accepted = Path(temp) / "accepted"
        accepted.mkdir()
        (accepted / "original-93write-source-preflight.aggregate.json").write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        need(not output.exists() and not output.is_symlink(),
             "PRIVATE_PREFLIGHT_OUTPUT_OCCUPIED")
        os.rename(accepted, output)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("original_jar", "candidate_jar", "owner_entry",
                 "candidate_surrogate", "fresh_private_output"):
        p.add_argument(name)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(replay_original_93write_source_preflight(
            a.original_jar, a.candidate_jar, a.owner_entry,
            a.candidate_surrogate, a.fresh_private_output,
            original_sha256=a.original_sha256,
            candidate_sha256=a.candidate_sha256), sort_keys=True))
    except (OriginalInitializerSourcePreflightError, BytecodeProfileError,
            ValueError, OSError, KeyError, IndexError, TypeError):
        p.error("PRIVATE_R110_ORIGINAL_93WRITE_JAVA9_PREFLIGHT_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
