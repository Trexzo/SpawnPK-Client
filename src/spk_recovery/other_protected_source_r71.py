"""R71: private Java source for five other exact v309 protected regions.

Three Properties.getProperty guards followed by List.add(enum reference);
one guarded Integer.valueOf(...).intValue() assignment; one String
default-or-second-lookup assignment. Each is proven within an original
typed empty Exception catch. No full-method or runtime parity claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, BadZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .boolean_join_witness import BooleanJoinWitnessError, _edges
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)
from .local_exception_primitive_source import _name, _owner_name, _literal


class OtherProtectedSourceError(ValueError):
    """Original protected source shape cannot be proved."""


_SHA = re.compile(r"[a-fA-F0-9]{64}\Z")


def _need(ok: bool, why: str) -> None:
    if not ok:
        raise OtherProtectedSourceError(why)


def _is_getproperty(row: dict) -> bool:
    return (
        row.get("opcode") == "0xb6"
        and row.get("owner") == "java/util/Properties"
        and row.get("name") == "getProperty"
        and row.get("descriptor")
        == "(Ljava/lang/String;)Ljava/lang/String;"
    )


def _static_expression(row: dict, owner: str, declared: dict) -> str:
    _need(row.get("opcode") == "0xb2"
          and type(row.get("owner")) is str
          and type(row.get("name")) is str
          and type(row.get("descriptor")) is str,
          "ORIGINAL_STATIC_REFERENCE_NOT_RESOLVED")
    if row["owner"] == owner:
        field = declared.get((row["name"], row["descriptor"]))
        _need(field is not None and field["access"] & 0x0008,
              "ORIGINAL_OWNER_STATIC_REFERENCE_NOT_DECLARED")
        return _name(row["name"])
    return _owner_name(row["owner"]) + "." + _name(row["name"])


def _local_form(window: list[dict], owner: str, fields: dict,
                offsets: set[int]) -> tuple[str, str] | None:
    ops = [x.get("opcode") for x in window]
    if (ops == ["0x2b", "0x12", "0xb6", "0xc6", "0xb2", "0xb2",
                "0xb9", "0x57"]):
        receiver, key, get, conditional, listfield, elemfield, call, _ = window
        if (not _is_getproperty(get) or key.get("constant_pool_tag") != 8
                or conditional.get("branch_target_offset") not in offsets
                or listfield.get("descriptor") != "Ljava/util/List;"
                or call.get("owner") != "java/util/List"
                or call.get("name") != "add"
                or call.get("descriptor") != "(Ljava/lang/Object;)Z"):
            return None
        lhs = _static_expression(listfield, owner, fields)
        rhs = _static_expression(elemfield, owner, fields)
        expr = "originalLocalSlot1.getProperty(" + _literal(key) + ")"
        return "guarded_list_add", (
            "    if (" + expr + " != null) {\n"
            "        " + lhs + ".add(" + rhs + ");\n"
            "    }\n"
        )
    if (ops == ["0x2b", "0x12", "0xb6", "0xc6", "0x2b", "0x12",
                "0xb6", "0xb8", "0xb6", "0xb3"]):
        _, key, read, conditional, _, key2, read2, convert, val, store = window
        if (not _is_getproperty(read) or not _is_getproperty(read2)
                or key.get("constant_pool_tag") != 8
                or key2.get("constant_pool_tag") != 8
                or key.get("constant") != key2.get("constant")
                or conditional.get("branch_target_offset") not in offsets
                or convert.get("descriptor")
                != "(Ljava/lang/String;)Ljava/lang/Integer;"
                or val.get("owner") != "java/lang/Integer"
                or val.get("name") != "intValue"
                or val.get("descriptor") != "()I"
                or store.get("owner") != owner
                or store.get("descriptor") != "I"):
            return None
        declaration = fields.get((store.get("name"), "I"))
        if declaration is None or not declaration["access"] & 0x0008:
            return None
        exp = "originalLocalSlot1.getProperty(" + _literal(key) + ")"
        converted = _owner_name(convert["owner"]) + "." + _name(convert["name"])
        return "guarded_integer_conversion", (
            "    if (" + exp + " != null) {\n"
            "        " + _name(store["name"]) + " = "
            + converted + "(" + exp + ").intValue();\n"
            "    }\n"
        )
    if (ops == ["0x2b", "0x12", "0xb6", "0xc7", "0x12", "0xb3",
                "0xa7", "0x2b", "0x12", "0xb6", "0xb3"]):
        _, key, lookup, branch, fallback, left, jump, _, key2, lookup2, right = window
        if (not _is_getproperty(lookup) or not _is_getproperty(lookup2)
                or key.get("constant_pool_tag") != 8
                or key2.get("constant_pool_tag") != 8
                or fallback.get("constant_pool_tag") != 8
                or key.get("constant") != key2.get("constant")
                or branch.get("branch_target_offset") != window[7]["offset"]
                or jump.get("branch_target_offset") not in offsets
                or any(left.get(x) != right.get(x)
                       for x in ("owner", "name", "descriptor"))
                or left.get("owner") != owner
                or left.get("descriptor") != "Ljava/lang/String;"):
            return None
        declaration = fields.get((left.get("name"), left.get("descriptor")))
        if declaration is None or not declaration["access"] & 0x0008:
            return None
        lhs = _name(left["name"])
        expr = "originalLocalSlot1.getProperty(" + _literal(key) + ")"
        return "nullable_string_default", (
            "    if (" + expr + " == null) {\n"
            "        " + lhs + " = " + _literal(fallback) + ";\n"
            "    } else {\n"
            "        " + lhs + " = " + expr + ";\n"
            "    }\n"
        )
    return None


def plan_original_other_protected_sources(
    original: dict, method_name: str, descriptor: str,
) -> dict:
    owner = original.get("internal_name")
    _need(type(owner) is str and owner, "ORIGINAL_OWNER_UNKNOWN")
    methods = [m for m in original.get("methods", [])
               if m.get("name") == method_name
               and m.get("descriptor") == descriptor]
    _need(len(methods) == 1, "PRIVATE_ORIGINAL_METHOD_NOT_UNIQUE")
    method = methods[0]
    rows = _instructions(method)
    _need(rows and rows[0]["offset"] == 0
          and all(a["offset"] + a["length"] == b["offset"]
                  for a, b in zip(rows, rows[1:])),
          "ORIGINAL_INSTRUCTIONS_NOT_CONTIGUOUS")
    fields = _fields(original)
    handlers = method.get("exception_handlers")
    _need(isinstance(handlers, list), "ORIGINAL_EXCEPTION_TABLE_MISSING")
    try:
        incoming = {dest for _, dest in _edges(rows)}
    except BooleanJoinWitnessError:
        raise OtherProtectedSourceError("ORIGINAL_BRANCH_TARGET_INVALID") from None
    positions = {row["offset"]: i for i, row in enumerate(rows)}
    local = [h for h in handlers if h.get("catch_type")
             == "java/lang/Exception"]
    accepted = []
    counts: dict[str, int] = {}
    for h in local:
        start, end, target = (h.get("start_pc"), h.get("end_pc"),
                              h.get("handler_pc"))
        if any(type(v) is not int or v not in positions
               for v in (start, end, target)):
            continue
        a, b, c = positions[start], positions[end], positions[target]
        if c != b + 1 or c + 1 >= len(rows):
            continue
        protected = rows[a:b]
        endjump, caught, nextrow = rows[b:c+2]
        if (endjump.get("opcode") != "0xa7"
                or endjump.get("branch_target_offset") != nextrow["offset"]
                or caught.get("opcode") != "0x4e"):
            continue
        # The only inside-branch target may be the local Boolean/String
        # alternative path. Other handler/branch entry points veto recovery.
        inside = {r["offset"] for r in protected[1:]}
        expected = {
            protected[7]["offset"]
            if len(protected) == 11 and protected[3]["opcode"] == "0xc7"
            else None
        }
        if (inside & (incoming - expected)
                or any(other is not h and other.get("handler_pc") in inside
                       for other in handlers)):
            continue
        match = _local_form(protected, owner, fields,
                            {endjump["offset"], nextrow["offset"]})
        if match is None:
            continue
        kind, fragment = match
        counts[kind] = counts.get(kind, 0) + 1
        accepted.append({
            "kind": kind,
            "original_protected_start": start,
            "original_protected_end": end,
            "original_exception_handler_pc": target,
            "private_original_jvm_window": protected,
            "private_java_source": (
                "try {\n" + fragment
                + "} catch (java.lang.Exception ignored) {\n}\n"
            ),
        })
    _need(len({r["original_protected_start"] for r in accepted})
          == len(accepted), "PROTECTED_REGIONS_NOT_UNIQUE")
    return {
        "private_verified_source_regions": accepted,
        "original_local_exception_protected_regions": len(local),
        "exact_other_source_regions": len(accepted),
        "bounded_original_source_kinds": dict(sorted(counts.items())),
        "original_empty_exception_handlers_verified_per_site": True,
        "original_properties_type_from_R69": True,
        "original_complete_java_method_source_equivalent": False,
        "original_helper_side_effects_equivalent": False,
        "original_runtime_behavior_equivalent": False,
    }


def recover_private_other_protected_sources(
    original_jar: Path, owner_entry: str, method_name: str,
    descriptor: str, destination: Path, *, sha256: str,
) -> dict:
    jar, out = Path(original_jar), Path(destination)
    _need(not out.exists() and not out.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    _need(type(sha256) is str and _SHA.fullmatch(sha256) is not None,
          "INVALID_WHOLE_ORIGINAL_JAR_PIN")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar) == sha256.lower(), "ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(owner_entry) is str and owner_entry.endswith(".class")
          and not owner_entry.startswith("/")
          and "\\" not in owner_entry
          and all(x not in ("", ".", "..") and ":" not in x
                  for x in owner_entry.split("/")),
          "INVALID_PRIVATE_ORIGINAL_OWNER_ENTRY")
    try:
        with ZipFile(jar) as archive:
            _need(archive.namelist().count(owner_entry) == 1,
                  "ORIGINAL_CLASSFILE_ENTRY_NOT_UNIQUE")
            profile = profile_jar_class(jar, owner_entry)
        proof = plan_original_other_protected_sources(
            profile, method_name, descriptor)
    except (BadZipFile, BytecodeProfileError,
            ScalarInitializerRecoveryError, OSError, KeyError, IndexError):
        raise OtherProtectedSourceError(
            "ORIGINAL_PROTECTED_SOURCE_INPUT_UNVERIFIABLE"
        ) from None
    _need(_digest(jar) == sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_SOURCE_RECOVERY")
    regions = proof.pop("private_verified_source_regions")
    _need(bool(regions), "NO_EXACT_OTHER_LOCAL_SOURCES_RECOVERED")
    fragment = "".join(r["private_java_source"] for r in regions)
    serialized = json.dumps(regions, indent=2, sort_keys=True) + "\n"
    public = {
        "schema_version": 1,
        "kind": "private_original_exception_protected_list_int_string_source",
        "original_complete_jar_sha256": sha256.lower(),
        "research_only": True,
        "private_region_graph_sha256":
            hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        "private_source_fragment_sha256":
            hashlib.sha256(fragment.encode("utf-8")).hexdigest(),
        **proof,
    }
    out.mkdir(parents=True, exist_ok=False)
    for name, payload in (
        ("other-protected-regions.private.json", serialized),
        ("other-protected-source.private.java.txt", fragment),
        ("other-protected-source.aggregate.json",
         json.dumps(public, indent=2, sort_keys=True) + "\n"),
    ):
        with (out/name).open("x", encoding="utf-8", newline="\n") as fd:
            fd.write(payload)
    return public


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("private_owner_class_entry")
    p.add_argument("private_method_name")
    p.add_argument("private_method_descriptor")
    p.add_argument("new_private_output", type=Path)
    p.add_argument("--sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(recover_private_other_protected_sources(
            a.original_jar, a.private_owner_class_entry,
            a.private_method_name, a.private_method_descriptor,
            a.new_private_output, sha256=a.sha256,
        ), sort_keys=True))
    except OtherProtectedSourceError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
