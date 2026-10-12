"""R109: recover all eight original-v309 nonconstant-final clinit write recipes.

No guessed source expressions: derive each RHS opcode/operand/control-flow
slice from a pinned original Java9 classfile. Emit detailed original symbolic
operands ONLY inside a fresh, private, SHA-pinned output. Only aggregate
counts/digests leave the private environment.

This is source-dependency recovery, NOT Java source equivalence, R58 or R107.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from zipfile import ZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .private_original_fourth_enum_accessors import digest


class OriginalEightFinalInitializerError(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise OriginalEightFinalInitializerError(code)


def ops(rows):
    return tuple(row.get("opcode") for row in rows)


def _same_owner_store(row, owner):
    return row.get("opcode") == "0xb3" and row.get("owner") == owner


def _private_bootstrap(profile, row):
    idx = row.get("bootstrap_method_attr_index")
    need(type(idx) is int,
         "INVOKEDYNAMIC_BOOTSTRAP_ID_MISSING")
    matches = [x for x in profile.get("bootstrap_methods", [])
               if x.get("index") == idx]
    need(len(matches) == 1 and
         isinstance(matches[0].get("bootstrap_method"), dict),
         "EXACT_ORIGINAL_INDY_BOOTSTRAP_NOT_UNIQUE")
    return matches[0]


def classify_final_write(profile, rows, index, target):
    descriptor = target["descriptor"]
    name = target["name"]
    owner = profile["internal_name"]
    store = rows[index]
    need(_same_owner_store(store, owner) and
         store.get("name") == name and
         store.get("descriptor") == descriptor,
         "FINAL_FIELD_PUTSTATIC_OPERAND_MISMATCH")

    def source(count, pattern):
        need(index + 1 >= count,
             "FINAL_FIELD_ASSIGNMENT_LACKS_PROVEN_RHS")
        window = rows[index - count + 1:index + 1]
        need(ops(window) == pattern and
             all(window[i]["offset"] + window[i]["length"] ==
                 window[i + 1]["offset"]
                 for i in range(len(window) - 1)),
             "FINAL_FIELD_RHS_JVM_TEMPLATE_NOT_EXACT")
        return window

    code = store.get("opcode")
    if descriptor.startswith("L") and descriptor != "Ljava/lang/String;" and \
            descriptor != "Ljava/lang/Integer;":
        window = source(2, ("0xb2", "0xb3"))
        rhs = window[0]
        need(rhs.get("descriptor") == descriptor and
             rhs.get("owner") == descriptor[1:-1] and
             isinstance(rhs.get("name"), str),
             "ENUM_FINAL_VALUE_NOT_PROVEN_FROM_EXACT_GETSTATIC")
        kind = "direct_enum_constant"

    elif descriptor == "Ljava/lang/String;":
        if index >= 7 and ops(rows[index - 7:index + 1]) == (
                "0xb2", "0xb2", "0xa6", "0x12",
                "0xa7", "0x12", "0xba", "0xb3"):
            window = source(8, (
                "0xb2", "0xb2", "0xa6", "0x12",
                "0xa7", "0x12", "0xba", "0xb3"))
            e0, e1, branch, first, go, second, concat, _ = window
            need(e0.get("descriptor") == e1.get("descriptor")
                 and e0.get("owner") == e1.get("owner")
                 and e0.get("descriptor", "").startswith("L")
                 and e0.get("descriptor", "").endswith(";")
                 and branch.get("branch_target_offset") == second["offset"]
                 and go.get("branch_target_offset") == concat["offset"]
                 and all(x.get("constant_pool_tag") == 8 and
                         type(x.get("constant")) is str
                         for x in (first, second))
                 and concat.get("descriptor") ==
                     "(Ljava/lang/String;)Ljava/lang/String;",
                 "CONDITIONAL_STRING_CONCAT_BRANCH_OR_LITERALS_NOT_EXACT")
            _private_bootstrap(profile, concat)
            kind = "conditional_enum_comparison_concat"
        elif index >= 2 and ops(rows[index - 2:index + 1]) == (
                "0xb2", "0xb8", "0xb3"):
            window = source(3, ("0xb2", "0xb8", "0xb3"))
            value, call, _ = window
            need(value.get("descriptor", "").startswith("L")
                 and call.get("descriptor") ==
                     "(" + value["descriptor"] + ")Ljava/lang/String;"
                 and all(type(call.get(x)) is str
                         for x in ("owner", "name")),
                 "ENUM_TO_STRING_HELPER_RHS_NOT_EXACT")
            kind = "enum_to_string_static_helper"
        else:
            window = source(3, ("0xb8", "0xba", "0xb3"))
            helper, concat, _ = window
            need(helper.get("descriptor") == "()Ljava/lang/String;"
                 and concat.get("descriptor") ==
                     "(Ljava/lang/String;)Ljava/lang/String;",
                 "STRING_HELPER_CONCAT_RHS_NOT_EXACT")
            _private_bootstrap(profile, concat)
            kind = "static_string_helper_concat"

    elif descriptor == "[I":
        window = source(3, ("0x10", "0xbc", "0xb3"))
        count, newarray, _ = window
        need(type(count.get("int_constant")) is int
             and 0 <= count["int_constant"] <= 127
             and newarray.get("array_primitive_atype") == 10,
             "ORIGINAL_INTEGER_ARRAY_ALLOCATION_NOT_EXACT")
        kind = "fixed_integer_array_allocation"

    elif descriptor == "Ljava/lang/Integer;":
        window = source(3, ("0x12", "0xb8", "0xb3"))
        number, call, _ = window
        need(number.get("constant_pool_tag") == 3
             and type(number.get("constant")) is int
             and call.get("owner") == "java/lang/Integer"
             and call.get("name") == "valueOf"
             and call.get("descriptor") == "(I)Ljava/lang/Integer;",
             "ORIGINAL_BOXED_INTEGER_VALUEOF_RHS_NOT_EXACT")
        kind = "integer_valueof_constant"

    else:
        raise OriginalEightFinalInitializerError(
            "ORIGINAL_FINAL_FIELD_RHS_TYPE_UNSUPPORTED")

    # Preserve full decoded operands only in private file. Record origin
    # ordinal/offset for later source synthesis and branch/indy reconstruction.
    return {
        "original_field": {
            "name": name, "descriptor": descriptor,
            "access": target["access"],
        },
        "source_recipe_kind": kind,
        "original_store_instruction_ordinal": index,
        "original_store_bytecode_offset": store["offset"],
        "original_rhs_instructions": window,
        "original_indy_bootstraps": [
            _private_bootstrap(profile, x)
            for x in window if x.get("opcode") == "0xba"
        ],
        "source_java_expression_compiled_and_proven": False,
    }


def original_eight_final_write_proof(profile):
    owner = profile.get("internal_name")
    need(isinstance(owner, str) and profile.get("classfile_major") == 53,
         "PINNED_ORIGINAL_OWNER_JAVA9_IDENTITY_UNAVAILABLE")
    fields = profile.get("fields")
    need(isinstance(fields, list) and len(fields) == 126
         and len({(f.get("name"), f.get("descriptor")) for f in fields}) == 126,
         "ORIGINAL_OWNER_126_FIELD_INVENTORY_NOT_EXACT")
    finals = [f for f in fields if f.get("access") == 25
              and f.get("constant_value") is None]
    need(len(finals) == 8, "ORIGINAL_NONCONSTANT_FINAL_FIELDS_NOT_EIGHT")
    need(sum(f.get("access") == 25 and
             f.get("constant_value") is not None for f in fields) == 33,
         "ORIGINAL_COMPILETIME_CONSTANT_FIELD_COUNT_NOT_33")
    methods = [m for m in profile.get("methods", [])
               if m.get("name") == "<clinit>"
               and m.get("descriptor") == "()V"]
    need(len(methods) == 1 and methods[0].get("access") == 8,
         "ORIGINAL_STATIC_INITIALIZER_NOT_UNIQUE")
    rows = methods[0].get("instructions")
    need(isinstance(rows, list) and len(rows) == 213
         and len({r.get("offset") for r in rows}) == 213,
         "ORIGINAL_STATIC_INITIALIZER_213_INSTRUCTIONS_REQUIRED")
    need(sum(_same_owner_store(row, owner) for row in rows) == 93,
         "ORIGINAL_OWNER_93_STATIC_WRITES_REQUIRED")
    indexed_writes = {}
    for i, row in enumerate(rows):
        if not _same_owner_store(row, owner):
            continue
        key = (row.get("name"), row.get("descriptor"))
        need(key not in indexed_writes,
             "ORIGINAL_OWNER_STATIC_FIELD_ASSIGNED_MORE_THAN_ONCE")
        indexed_writes[key] = i
    field_names = {(f["name"], f["descriptor"]) for f in fields}
    need(set(indexed_writes).issubset(field_names),
         "UNKNOWN_ORIGINAL_STATIC_FIELD_WRITE_TARGET")
    final_names = [(f["name"], f["descriptor"]) for f in finals]
    need(all(key in indexed_writes for key in final_names),
         "ORIGINAL_NONCONSTANT_FINAL_FIELD_NOT_INITIALIZED")
    snapshots = [classify_final_write(
        profile, rows, indexed_writes[key], field)
        for key, field in zip(final_names, finals)]
    classifications = {
        "direct_enum_constant": 1,
        "conditional_enum_comparison_concat": 2,
        "enum_to_string_static_helper": 2,
        "fixed_integer_array_allocation": 1,
        "static_string_helper_concat": 1,
        "integer_valueof_constant": 1,
    }
    found = {k: sum(x["source_recipe_kind"] == k for x in snapshots)
             for k in classifications}
    need(found == classifications,
         "ORIGINAL_EIGHT_FINAL_RHS_RECIPE_DISTRIBUTION_CHANGED")
    return snapshots, {
        "original_owner_field_declarations": 126,
        "original_owner_clinit_instruction_count": 213,
        "original_owner_static_field_writes": 93,
        "original_nonconstant_static_final_assignments_recovered": 8,
        "exact_original_initializer_opcode_and_operand_recipes": found,
        "original_simple_rhs_sites_without_indy": 5,
        "original_concat_rhs_sites_with_private_bootstrap": 3,
        "original_exact_java_source_of_eight_assignments_compiled": False,
        "R58_complete_clinit_parity_proven": False,
        "R107_complete_owner_java9_source_compiled": False,
        "whole_client_runtime_equivalence_certified": False,
    }


def emit_private_final_write_provenance(
    original_jar, original_entry, output, *, original_sha256,
):
    original_jar, output = Path(original_jar), Path(output)
    need(output.parent.is_dir() and not output.parent.is_symlink()
         and not output.exists() and not output.is_symlink(),
         "FRESH_PRIVATE_FINAL_WRITE_OUTPUT_REQUIRED")
    need(type(original_sha256) is str
         and re.fullmatch(r"[0-9a-fA-F]{64}", original_sha256)
         and original_jar.is_file() and not original_jar.is_symlink()
         and digest(original_jar) == original_sha256.lower(),
         "EXACT_ORIGINAL_COMPLETE_JAR_SHA256_MISMATCH")
    need(type(original_entry) is str
         and original_entry.endswith(".class")
         and not original_entry.startswith("/")
         and "\\" not in original_entry
         and all(x not in ("", ".", "..")
                 for x in original_entry.split("/")),
         "ORIGINAL_OWNER_ENTRY_UNSAFE")
    with ZipFile(original_jar) as archive:
        entries = archive.namelist()
        need(len(entries) == len(set(entries))
             and entries.count(original_entry) == 1,
             "EXACT_ORIGINAL_OWNER_CLASSFILE_NOT_UNIQUE")
    original = profile_jar_class(original_jar, original_entry)
    need(original.get("internal_name") + ".class" == original_entry,
         "OWNER_BINARY_NAME_UNEXPECTED")
    records, aggregate = original_eight_final_write_proof(original)
    private = {
        "schema_version": 1,
        "kind": "PRIVATE_original_v309_eight_final_assignments",
        "original_complete_jar_sha256": original_sha256.lower(),
        "original_owner_class_entry": original_entry,
        "original_eight_rhs_write_recipes": records,
    }
    raw = json.dumps(private, sort_keys=True, indent=2) + "\n"
    need(digest(original_jar) == original_sha256.lower(),
         "PINNED_ORIGINAL_JAR_CHANGED_DURING_PROVENANCE")
    report = {
        "schema_version": 1,
        "kind": "original_v309_eight_final_init_rhs_recovered_not_source_proven",
        "original_complete_jar_sha256": original_sha256.lower(),
        "private_exact_operand_map_sha256": hashlib.sha256(
            raw.encode("utf-8")).hexdigest(),
        **aggregate,
    }
    with tempfile.TemporaryDirectory(
        prefix="v309-r109-private-final-", dir=output.parent,
    ) as tmp:
        accepted = Path(tmp) / "accepted"
        accepted.mkdir()
        (accepted / "original-eight-final-writes.PRIVATE.json").write_text(
            raw, encoding="utf-8")
        (accepted / "original-eight-final-writes.aggregate.json").write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        need(not output.exists(), "OUTPUT_OCCUPIED_AFTER_FINAL_RHS_PROOF")
        os.rename(accepted, output)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("original_jar", "original_owner_class", "new_private_output"):
        p.add_argument(arg)
    p.add_argument("--original-sha256", required=True)
    args = p.parse_args(argv)
    try:
        print(json.dumps(emit_private_final_write_provenance(
            args.original_jar, args.original_owner_class,
            args.new_private_output, original_sha256=args.original_sha256),
            sort_keys=True))
    except (OriginalEightFinalInitializerError, BytecodeProfileError,
            ValueError, OSError, KeyError, IndexError, TypeError):
        p.error("PRIVATE_V309_EIGHT_FINAL_SOURCE_RECOVERY_NOT_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
