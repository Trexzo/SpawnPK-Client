"""R100: all nine original-v309 fourth-enum JVM opcode source shapes.

Classifies independently compiled Java9 enum methods by JVM signatures and
original private String fields, not obfuscated synthetic accessor names.
This is *opcode-shape evidence only*: operands, literals, InnerClasses,
exact field identities, R95 parity and runtime are NOT certified here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from zipfile import ZipFile

from .bytecode_profile import profile_jar_class
from .private_original_fourth_enum_accessors import (
    OriginalEnumAccessorError, _accessors, digest,
)


class FourthEnumSourceShapeError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise FourthEnumSourceShapeError(reason)


EXPECTED = {
    "values": ("0xb2", "0xb6", "0xc0", "0xb0"),
    "valueOf": ("0x12", "0x2a", "0xb8", "0xc0", "0xb0"),
    "constructor": ("0x2a", "0x2b", "0x1c", "0xb7",
                    "0x2a", "0x2d", "0xb5", "0x2a",
                    "0x19", "0xb5", "0xb1"),
    "getter": ("0x2a", "0xb4", "0xb0"),
    "values_helper": ("0x05", "0xbd", "0x59", "0x03", "0xb2",
                      "0x53", "0x59", "0x04", "0xb2", "0x53", "0xb0"),
    "accessor": ("0x2a", "0xb4", "0xb0"),
    "initializer": ("0xbb", "0x59", "0x12", "0x03", "0x12",
                    "0x12", "0xb7", "0xb3", "0xbb", "0x59",
                    "0x12", "0x04", "0x12", "0x12", "0xb7",
                    "0xb3", "0xb8", "0xb3", "0xb1"),
}
# The constructor and initializer above are authoritative actual opcode
# patterns, NOT the shorter mnemonic count from regexes that omit operands.


def _ops(method):
    rows = method.get("instructions")
    need(isinstance(rows, list) and rows and
         all(isinstance(r, dict) and isinstance(r.get("opcode"), str)
             for r in rows), "NINE_METHOD_OPCODE_ROWS_NOT_EXACT")
    return tuple(r["opcode"] for r in rows)


def classify(profile):
    try:
        accessors = _accessors(profile)
    except OriginalEnumAccessorError as exc:
        raise FourthEnumSourceShapeError(
            "ORIGINAL_OR_CANDIDATE_R99_ACCESSOR_SHAPE_NOT_ACCEPTED"
        ) from exc
    owner = profile["internal_name"]
    fields = set(accessors)
    methods = profile["methods"]
    found = {}
    used = set()

    def one(role, predicate):
        matching = [m for m in methods if predicate(m)]
        need(len(matching) == 1, "FOURTH_ENUM_" + role.upper() + "_NOT_UNIQUE")
        m = matching[0]
        used.add((m["name"], m["descriptor"]))
        found[role] = _ops(m)
        return m

    one("values", lambda m:
        m.get("name") == "values" and
        m.get("descriptor") == "()[L" + owner + ";")
    one("valueOf", lambda m:
        m.get("name") == "valueOf" and
        m.get("descriptor") == "(Ljava/lang/String;)L" + owner + ";")
    one("constructor", lambda m:
        m.get("name") == "<init>" and
        m.get("descriptor") == "(Ljava/lang/String;ILjava/lang/String;Ljava/lang/String;)V")
    one("initializer", lambda m:
        m.get("name") == "<clinit>" and m.get("descriptor") == "()V")
    one("values_helper", lambda m:
        m.get("name") != "values" and
        m.get("descriptor") == "()[L" + owner + ";" and
        isinstance(m.get("access"), int) and
        m["access"] & 0x000a == 0x000a)
    # Ordinary getter source is uniquely determined by its private field,
    # not an invented symbol alias.
    getters = {}
    for m in methods:
        if (m.get("descriptor") != "()Ljava/lang/String;"
                or m.get("access") != 0x0001):
            continue
        rows = m.get("instructions", [])
        need(_ops(m) == EXPECTED["getter"],
             "ORIGINAL_JAVA9_STRING_GETTER_NOT_THREE_OPS")
        field = rows[1]
        need(field.get("owner") == owner and field.get("name") in fields
             and field.get("descriptor") == "Ljava/lang/String;"
             and field["name"] not in getters,
             "ORIGINAL_PRIVATE_STRING_GETTER_FIELD_NOT_UNIQUE")
        getters[field["name"]] = m
    need(len(getters) == 2 and set(getters) == fields,
         "BOTH_PRIVATE_STRING_GETTERS_NOT_PROVEN")
    for field in sorted(fields):
        getter = getters[field]
        accessor = accessors[field]
        found["getter_" + str(sorted(fields).index(field))] = _ops(getter)
        found["accessor_" + str(sorted(fields).index(field))] = _ops(accessor)
        used.add((getter["name"], getter["descriptor"]))
        used.add((accessor["name"], accessor["descriptor"]))
    need(len(used) == 9 and len(methods) == 9,
         "ALL_NINE_FOURTH_ENUM_METHODS_NOT_CLASSIFIED")
    expected = {
        "values": EXPECTED["values"], "valueOf": EXPECTED["valueOf"],
        "constructor": EXPECTED["constructor"],
        "initializer": EXPECTED["initializer"],
        "values_helper": EXPECTED["values_helper"],
        "getter_0": EXPECTED["getter"], "getter_1": EXPECTED["getter"],
        "accessor_0": EXPECTED["accessor"], "accessor_1": EXPECTED["accessor"],
    }
    need(found == expected, "ORIGINAL_OR_CANDIDATE_NINE_OPCODE_SHAPES_CHANGED")
    return found


def prove_fourth_enum_source_shapes(original, candidate):
    a = original.get("internal_name")
    b = candidate.get("internal_name")
    need(type(a) is str and type(b) is str and a != b
         and "$" in a and "$" in b and
         a.rsplit("$", 1)[0] == b.rsplit("$", 1)[0],
         "ORIGINAL_SURROGATE_SAME_OUTER_NOT_PROVEN")
    left, right = classify(original), classify(candidate)
    need(left == right, "ALL_NINE_JAVA9_OPCODE_SHAPES_DIFFER")
    return {
        "schema_version": 1,
        "kind": "v309_fourth_enum_java9_nine_method_source_shape_witness",
        "research_only": True,
        "original_enum_fields": 5,
        "original_enum_methods": 9,
        "original_private_string_getters_checked": 2,
        "original_synthetic_accessors_checked": 2,
        "original_method_opcode_sequences_compared": 9,
        "all_nine_original_jvm_opcode_shapes_matched": True,
        "original_constant_literals_and_field_method_operands_proven": False,
        "original_method_name_aliases_accepted": False,
        "original_four_enums_R95_parity_proven": False,
        "original_InnerClasses_metadata_proven": False,
        "whole_original_client_runtime_equivalence_certified": False,
    }


def replay_private_fourth_enum_shapes(
    original_jar, candidate_jar, original_entry, surrogate_entry, output,
    *, original_sha256, candidate_sha256,
):
    original_jar, candidate_jar, output = map(
        Path, (original_jar, candidate_jar, output))
    need(not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "NEW_PRIVATE_OUTPUT_REQUIRED")
    for jar, pin in ((original_jar, original_sha256),
                     (candidate_jar, candidate_sha256)):
        need(jar.is_file() and not jar.is_symlink()
             and isinstance(pin, str) and re.fullmatch("[0-9a-fA-F]{64}", pin)
             and digest(jar) == pin.lower(),
             "ORIGINAL_OR_CANDIDATE_JAR_PIN_MISMATCH")
    need(original_jar.resolve() != candidate_jar.resolve(),
         "ORIGINAL_AND_CANDIDATE_JARS_MUST_DIFFER")
    for entry in (original_entry, surrogate_entry):
        need(isinstance(entry, str) and entry.endswith(".class")
             and "\" not in entry and not entry.startswith("/")
             and all(x not in ("", ".", "..") for x in entry.split("/")),
             "UNSAFE_ENUM_CLASS_ENTRY")
    with ZipFile(original_jar) as a, ZipFile(candidate_jar) as b:
        need(a.namelist().count(original_entry) == 1
             and b.namelist().count(surrogate_entry) == 1,
             "EXACT_ENUM_ARCHIVE_ENTRIES_NOT_UNIQUE")
    result = prove_fourth_enum_source_shapes(
        profile_jar_class(original_jar, original_entry),
        profile_jar_class(candidate_jar, surrogate_entry))
    need(digest(original_jar) == original_sha256.lower()
         and digest(candidate_jar) == candidate_sha256.lower(),
         "PINNED_SOURCE_JARS_CHANGED_DURING_PROOF")
    report = {**result,
              "original_complete_jar_sha256": original_sha256.lower(),
              "candidate_complete_jar_sha256": candidate_sha256.lower()}
    output.mkdir(parents=True, exist_ok=False)
    (output / "nine-method-opcode-shapes.aggregate.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("original_jar", "candidate_jar", "original_enum_entry",
                  "surrogate_enum_entry", "new_private_output"):
        p.add_argument(field)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(replay_private_fourth_enum_shapes(
            a.original_jar, a.candidate_jar, a.original_enum_entry,
            a.surrogate_enum_entry, a.new_private_output,
            original_sha256=a.original_sha256,
            candidate_sha256=a.candidate_sha256), sort_keys=True))
    except FourthEnumSourceShapeError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
