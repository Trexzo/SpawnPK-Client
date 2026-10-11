"""R55: original JVM external-helper StringConcatFactory final source forms.

Only contiguous invokestatic External.helper():String -> invokedynamic
StringConcatFactory.makeConcatWithConstants(String):String -> owner putstatic
is eligible. Source *form* only; external behavior and full runtime unverified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, BadZipFile

from .boolean_join_witness import _edges
from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _clinit, _digest, _fields, _instructions,
)


class ExternalHelperConcatError(ValueError):
    """Original external-helper final String source form is not established."""


_ID = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")
_PIN = re.compile(r"[0-9a-fA-F]{64}\Z")
_FACTORY = "java/lang/invoke/StringConcatFactory"
_DESC = (
    "(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;"
    "Ljava/lang/invoke/MethodType;Ljava/lang/String;"
    "[Ljava/lang/Object;)Ljava/lang/invoke/CallSite;"
)


def _need(condition: bool, reason: str) -> None:
    if not condition:
        raise ExternalHelperConcatError(reason)


def _recipe(original: dict, row: dict) -> tuple[str, str] | None:
    if (row.get("opcode") != "0xba"
            or row.get("name") != "makeConcatWithConstants"
            or row.get("descriptor") != "(Ljava/lang/String;)Ljava/lang/String;"
            or row.get("invokedynamic_reserved") != 0):
        return None
    idx = row.get("bootstrap_method_attr_index")
    if type(idx) is not int:
        return None
    found = [b for b in original.get("bootstrap_methods", [])
             if b.get("index") == idx]
    if len(found) != 1:
        return None
    handle = found[0].get("bootstrap_method", {})
    args = found[0].get("arguments")
    if (handle.get("owner") != _FACTORY
            or handle.get("name") != "makeConcatWithConstants"
            or handle.get("descriptor") != _DESC
            or handle.get("reference_kind") != 6
            or handle.get("target_kind") != "method"
            or not isinstance(args, list) or len(args) != 1
            or args[0].get("kind") != "string"
            or type(args[0].get("value")) is not str):
        return None
    text = args[0]["value"]
    if text.count("\x01") != 1 or "\x02" in text:
        return None
    before, after = text.split("\x01")
    if not all(32 <= ord(x) <= 126 for x in before + after):
        return None
    return before, after


def plan_external_helper_concat(original: dict, class_profiles: dict) -> dict:
    owner = original.get("internal_name")
    _need(type(owner) is str and owner, "ORIGINAL_OWNER_UNKNOWN")
    fields = _fields(original)
    targets = {
        key: field for key, field in fields.items()
        if (field["access"] & 0x0018) == 0x0018
        and field["constant_value"] is None
        and key[1] == "Ljava/lang/String;"
    }
    _need(bool(targets), "NO_ORIGINAL_DYNAMIC_FINAL_STRING_FIELDS")
    init = _clinit(original, required=True)
    rows = _instructions(init)
    incoming = {to for _, to in _edges(rows)}
    handlers = init.get("exception_handlers")
    _need(isinstance(handlers, list), "EXCEPTION_TABLE_MISSING")
    writes = {x: [] for x in targets}
    for index, row in enumerate(rows):
        key = row.get("name"), row.get("descriptor")
        if (row.get("opcode") == "0xb3" and row.get("owner") == owner
                and key in writes):
            writes[key].append((index, row))
    _need(all(len(v) == 1 for v in writes.values()),
          "ORIGINAL_FINAL_STRING_STORE_MISSING_OR_DUPLICATE")
    result = []
    for key, ((i, target),) in writes.items():
        if i < 2:
            continue
        helper, concat = rows[i-2:i]
        chain = (helper, concat, target)
        if (helper.get("opcode") != "0xb8"
                or helper.get("descriptor") != "()Ljava/lang/String;"
                or concat.get("opcode") != "0xba"
                or any(a["offset"] + a["length"] != b["offset"]
                       for a, b in zip(chain, chain[1:]))):
            continue
        recipe = _recipe(original, concat)
        external_owner = helper.get("owner")
        if (recipe is None or type(external_owner) is not str
                or external_owner == owner):
            continue
        external_class = class_profiles.get(external_owner)
        if (not isinstance(external_class, dict)
                or external_class.get("internal_name") != external_owner):
            continue
        methods = [
            m for m in external_class.get("methods", [])
            if m.get("name") == helper.get("name")
            and m.get("descriptor") == helper.get("descriptor")
        ]
        if len(methods) != 1 or methods[0].get("access", 0) & 0x0008 == 0:
            continue
        if any(x["offset"] in incoming for x in chain):
            continue
        overlaps = False
        for h in handlers:
            _need(isinstance(h, dict)
                  and all(type(h.get(k)) is int for k in
                          ("start_pc", "end_pc", "handler_pc")),
                  "INVALID_EXCEPTION_HANDLER")
            if (h["handler_pc"] in {x["offset"] for x in chain}
                    or any(h["start_pc"] <= x["offset"] < h["end_pc"]
                           for x in chain)):
                overlaps = True
        if overlaps:
            continue
        type_name = external_owner.replace("/", ".")
        method = helper.get("name")
        target_name = key[0]
        _need(all(_ID.fullmatch(x) for x in type_name.split("."))
              and type(method) is str and _ID.fullmatch(method) is not None
              and type(target_name) is str and _ID.fullmatch(target_name) is not None,
              "EXTERNAL_METHOD_JAVA_NAME_UNREPRESENTABLE")
        prefix, suffix = recipe
        source = (
            f"    {target_name} = "
            + json.dumps(prefix, ensure_ascii=True)
            + f" + {type_name}.{method}() + "
            + json.dumps(suffix, ensure_ascii=True)
            + ";\n"
        )
        result.append((target["offset"], source))
    result.sort()
    snippet = (
        "// PRIVATE exact external helper + StringConcatFactory source forms.\n"
        "// External method body, side effects and source parity unverified.\n"
        "static {\n" + "".join(x for _, x in result) + "}\n"
    )
    return {
        "private_source_fragment": snippet,
        "original_nonconstant_final_string_fields": len(targets),
        "exact_external_helper_concat_expression_forms": len(result),
        "other_string_fields_not_handled_by_this_source_form":
            len(targets) - len(result),
        "external_helper_runtime_semantics_verified": False,
        "complete_original_clinit_order_recovered": False,
        "private_java_recompilation_and_parity_certified": False,
        "runtime_equivalence_certified": False,
        "canonical_class_member_identities_accepted": False,
    }


def private_external_helper_concat_source(
    original_jar: Path, class_entry: str, out_root: Path, *,
    original_sha256: str,
) -> dict:
    jar, out = Path(original_jar), Path(out_root)
    _need(not out.exists() and not out.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    _need(type(original_sha256) is str and _PIN.fullmatch(original_sha256)
          is not None, "INVALID_COMPLETE_JAR_SHA256")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar) == original_sha256.lower(),
          "ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(class_entry) is str and class_entry.endswith(".class")
          and not class_entry.startswith("/") and "\\" not in class_entry
          and all(x not in ("", ".", "..") and ":" not in x
                  for x in class_entry.split("/")),
          "INVALID_PRIVATE_CLASS_ENTRY")
    try:
        with ZipFile(jar) as archive:
            entries = archive.namelist()
            _need(entries.count(class_entry) == 1,
                  "ORIGINAL_OWNER_CLASSFILE_MISSING_OR_DUPLICATE")
            original = profile_jar_class(jar, class_entry)
            owners = {
                x.get("owner") for m in original.get("methods", [])
                if m.get("name") == "<clinit>"
                for x in m.get("instructions", [])
                if x.get("opcode") == "0xb8"
                and x.get("descriptor") == "()Ljava/lang/String;"
            }
            owners.discard(None)
            owners.discard(original.get("internal_name"))
            for owner in owners:
                _need(type(owner) is str and entries.count(owner + ".class") == 1,
                      "EXTERNAL_OWNER_CLASS_MISSING_OR_DUPLICATE")
            class_profiles = {
                owner: profile_jar_class(jar, owner + ".class")
                for owner in owners
            }
        plan = plan_external_helper_concat(original, class_profiles)
    except (BadZipFile, BytecodeProfileError, ScalarInitializerRecoveryError,
            KeyError, IndexError, OSError):
        raise ExternalHelperConcatError("ORIGINAL_EXTERNAL_HELPER_UNEVALUABLE") from None
    _need(_digest(jar) == original_sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_REPLAY")
    snippet = plan.pop("private_source_fragment")
    report = {
        "schema_version": 1,
        "kind": "original_private_external_helper_string_final_expression",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "private_fragment_sha256": hashlib.sha256(
            snippet.encode("utf-8")
        ).hexdigest(),
        **plan,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "external-helper-concat.private.txt").open(
        "x", encoding="utf-8", newline="\n"
    ) as f:
        f.write(snippet)
    with (out / "external-helper-concat.aggregate.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("class_entry")
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--original-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(private_external_helper_concat_source(
            args.original_jar, args.class_entry, args.output_root,
            original_sha256=args.original_sha256,
        ), sort_keys=True))
    except ExternalHelperConcatError as exc:
        parser.error(str(exc))
    except (OSError, ValueError):
        parser.error("EXTERNAL_HELPER_CONCAT_SOURCE_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
