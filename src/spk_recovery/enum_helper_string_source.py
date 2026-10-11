"""R53: exact JVM enum-helper-backed String final initializer micro-slices.

A pure getstatic owner.enumRef / invokestatic nestedEnum.helper(enumRef):String /
putstatic owner.finalString chain is a recoverable *source expression form*.
Original source, nested class parity and runtime equivalence remain unproven.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from .boolean_join_witness import _edges
from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _clinit, _digest, _fields, _instructions,
)


class EnumHelperStringSourceError(ValueError):
    """Exact Enum helper String initializers cannot be proven."""


_PIN = re.compile(r"[a-fA-F0-9]{64}\Z")
_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")


def _need(check: bool, reason: str) -> None:
    if not check:
        raise EnumHelperStringSourceError(reason)


def _identifier(x: object) -> str:
    _need(type(x) is str and _IDENTIFIER.fullmatch(x) is not None,
          "ORIGINAL_MEMBER_NOT_JAVA_SOURCE_REPRESENTABLE")
    return x


def _classes_unique(path: Path, entries: list[str]) -> None:
    with ZipFile(path) as z:
        names = z.namelist()
        for entry in entries:
            _need(names.count(entry) == 1,
                  "CLASSFILE_ENTRY_MISSING_OR_DUPLICATED")


def plan_enum_helper_strings(owner_class: dict, nested_classes: dict) -> dict:
    owner = owner_class.get("internal_name")
    _need(type(owner) is str and bool(owner), "ORIGINAL_CLASS_OWNER_UNDEFINED")
    all_fields = _fields(owner_class)
    string_targets = {
        key: f for key, f in all_fields.items()
        if (f["access"] & 0x0018) == 0x0018
        and key[1] == "Ljava/lang/String;"
        and f["constant_value"] is None
    }
    _need(bool(string_targets), "NO_DYNAMIC_FINAL_STRING_FIELDS")
    init = _clinit(owner_class, required=True)
    rows = _instructions(init)
    incoming = {dest for _, dest in _edges(rows)}
    handlers = init.get("exception_handlers")
    _need(isinstance(handlers, list), "EXCEPTION_TABLE_MISSING")
    all_writes = {key: [] for key in string_targets}
    for i, row in enumerate(rows):
        key = row.get("name"), row.get("descriptor")
        if (row.get("opcode") == "0xb3"
                and row.get("owner") == owner and key in all_writes):
            all_writes[key].append((i, row))
    _need(all(len(stores) == 1 for stores in all_writes.values()),
          "FINAL_STRING_STORE_MISSING_OR_DUPLICATED")
    fragments = []
    for key, ((i, store),) in all_writes.items():
        if i < 2:
            continue
        get, call = rows[i - 2:i]
        if not (get.get("opcode") == "0xb2"
                and call.get("opcode") == "0xb8"
                and get["offset"] + get["length"] == call["offset"]
                and call["offset"] + call["length"] == store["offset"]
                and get.get("owner") == owner):
            continue
        original_ref = all_fields.get(
            (get.get("name"), get.get("descriptor"))
        )
        nested = get.get("descriptor")
        if (original_ref is None
                or (original_ref["access"] & 0x0018) != 0x0018
                or type(nested) is not str
                or not nested.startswith("L" + owner + "$")
                or not nested.endswith(";")):
            continue
        enum_type = nested[1:-1]
        if (call.get("owner") != enum_type
                or call.get("descriptor")
                != "(" + nested + ")Ljava/lang/String;"):
            continue
        enum = nested_classes.get(enum_type)
        if (not isinstance(enum, dict)
                or enum.get("internal_name") != enum_type
                or enum.get("super_name") != "java/lang/Enum"
                or (enum.get("class_access", 0) & 0x4000) == 0):
            continue
        signatures = [
            m for m in enum.get("methods", [])
            if m.get("name") == call.get("name")
            and m.get("descriptor") == call.get("descriptor")
        ]
        if len(signatures) != 1 or signatures[0].get("access", 0) & 0x0008 == 0:
            continue
        segment = (get, call, store)
        if any(x["offset"] in incoming for x in segment):
            continue
        covered = False
        for h in handlers:
            _need(isinstance(h, dict)
                  and all(type(h.get(k)) is int for k in
                          ("start_pc", "end_pc", "handler_pc")),
                  "INVALID_EXCEPTION_HANDLER")
            offsets = [x["offset"] for x in segment]
            if (h["handler_pc"] in offsets or any(
                    h["start_pc"] <= pc < h["end_pc"]
                    for pc in offsets)):
                covered = True
        if covered:
            continue
        type_name = ".".join(enum_type.split("/"))
        _need(all(_IDENTIFIER.fullmatch(x)
                  for x in type_name.split(".")),
              "PRIVATE_ENUM_TYPE_UNREPRESENTABLE")
        target = _identifier(key[0])
        source = _identifier(get["name"])
        method = _identifier(call["name"])
        fragments.append(
            (store["offset"],
             f"    {target} = {type_name}.{method}({source});\n")
        )
    fragments.sort()
    source = (
        "// PRIVATE: original JVM enum-helper String final store forms.\n"
        "// Nested enum helper method semantics independently unverified.\n"
        "static {\n"
        + "".join(x for _, x in fragments)
        + "}\n"
    )
    return {
        "private_source_fragment": source,
        "original_nonconstant_final_string_fields": len(string_targets),
        "exact_enum_helper_string_initializers": len(fragments),
        "remaining_string_initializer_forms_unrecovered":
            len(string_targets) - len(fragments),
        "original_enum_helper_runtime_behavior_verified": False,
        "nested_enum_source_equivalence_certified": False,
        "original_complete_clinit_equivalence_certified": False,
        "complete_java_source_recovered": False,
        "runtime_equivalence_certified": False,
        "canonical_field_identity_accepted": False,
    }


def private_enum_helper_string_source(
    original_jar: Path, class_entry: str, output_root: Path, *,
    original_sha256: str,
) -> dict:
    jar, out = Path(original_jar), Path(output_root)
    _need(not out.exists() and not out.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    _need(type(original_sha256) is str
          and _PIN.fullmatch(original_sha256) is not None,
          "INVALID_ORIGINAL_JAR_PIN")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar) == original_sha256.lower(),
          "ORIGINAL_COMPLETE_JAR_SHA256_MISMATCH")
    _need(type(class_entry) is str and class_entry.endswith(".class")
          and not class_entry.startswith("/") and "\\" not in class_entry
          and all(p not in ("", ".", "..") and ":" not in p
                  for p in class_entry.split("/")),
          "INVALID_PRIVATE_CLASS_ENTRY")
    try:
        _classes_unique(jar, [class_entry])
        original = profile_jar_class(jar, class_entry)
        owner = original["internal_name"]
        fields = _fields(original)
        inner_refs = {
            descriptor[1:-1]
            for (_, descriptor), field in fields.items()
            if (field["access"] & 0x0018) == 0x0018
            and descriptor.startswith("L" + owner + "$")
            and descriptor.endswith(";")
        }
        _classes_unique(jar, [x + ".class" for x in sorted(inner_refs)])
        enums = {x: profile_jar_class(jar, x + ".class")
                 for x in inner_refs}
        result = plan_enum_helper_strings(original, enums)
    except (BadZipFile, BytecodeProfileError, ScalarInitializerRecoveryError,
            OSError, KeyError, IndexError):
        raise EnumHelperStringSourceError(
            "ORIGINAL_STRING_SOURCE_CLASSFILE_UNEVALUABLE"
        ) from None
    _need(_digest(jar) == original_sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_SOURCE_FORM_REPLAY")
    snippet = result.pop("private_source_fragment")
    report = {
        "schema_version": 1,
        "kind": "original_private_enum_helper_static_final_string_forms",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "private_fragment_sha256": hashlib.sha256(
            snippet.encode("utf-8")
        ).hexdigest(),
        **result,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "enum-helper-strings.private.txt").open(
        "x", encoding="utf-8", newline="\n"
    ) as f:
        f.write(snippet)
    with (out / "enum-helper-strings.aggregate.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as f:
        json.dump(report, f, sort_keys=True, indent=2)
        f.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("class_entry")
    p.add_argument("output_root", type=Path)
    p.add_argument("--original-sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(private_enum_helper_string_source(
            a.original_jar, a.class_entry, a.output_root,
            original_sha256=a.original_sha256,
        ), sort_keys=True))
    except EnumHelperStringSourceError as exc:
        p.error(str(exc))
    except (OSError, ValueError):
        p.error("ENUM_HELPER_STRING_SOURCE_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
