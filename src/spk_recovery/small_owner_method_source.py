"""R60: recover PRIVATE exact short original-v309 owner method source forms.

Proves only explicit JVM micro-patterns: default constructor, constant-false
boolean methods, no-argument boolean delegate, boolean two-branch static
flag setter, and contiguous int-array element stores. Refuses to invent
complex method bodies. Whole original methods/runtime remain unverified.
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
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)


class SimpleOwnerMethodSourceError(ValueError):
    """Original method source cannot be staged under conservative JVM forms."""


_ID = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")
_PIN = re.compile(r"[0-9a-fA-F]{64}\Z")


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise SimpleOwnerMethodSourceError(reason)


def _java_name(value: object) -> str:
    _require(type(value) is str and _ID.fullmatch(value) is not None,
             "ORIGINAL_METHOD_OR_FIELD_NAME_NOT_JAVA_REPRESENTABLE")
    return value


def _typed_field(row: dict, owner: str, fields: dict,
                 external: dict, descriptor: str) -> str:
    _require(row.get("opcode") in ("0xb2", "0xb3"),
             "METHOD_FIELD_OPCODE_NOT_STATIC")
    name, declared = row.get("name"), row.get("descriptor")
    source_owner = row.get("owner")
    _require(declared == descriptor, "METHOD_FIELD_DESCRIPTOR_MISMATCH")
    if source_owner == owner:
        resolved = fields
        source = _java_name(name)
    else:
        _require(type(source_owner) is str
                 and source_owner in external,
                 "ORIGINAL_METHOD_FIELD_OWNER_NOT_PINNED")
        resolved = _fields(external[source_owner])
        parts = source_owner.replace("/", ".").split(".")
        _require(all(_ID.fullmatch(x) for x in parts),
                 "EXTERNAL_METHOD_FIELD_OWNER_UNREPRESENTABLE")
        source = ".".join(parts) + "." + _java_name(name)
    field = resolved.get((name, descriptor))
    _require(field is not None and field["access"] & 0x0008,
             "METHOD_FIELD_NOT_DECLARED_STATIC")
    return source


def _no_exception_handlers(method: dict) -> None:
    _require(isinstance(method.get("exception_handlers"), list)
             and not method["exception_handlers"],
             "METHOD_EXCEPTION_HANDLERS_NOT_RECOVERED")


def _literal_integer(row: dict) -> int:
    op = row.get("opcode")
    _require(op in {f"0x{i:02x}" for i in range(0x02, 0x09)}
             | {"0x10", "0x11"}, "UNSUPPORTED_EXACT_INTEGER_LITERAL_OPCODE")
    v = row.get("int_constant")
    _require(type(v) is int and -(2**31) <= v < 2**31,
             "JVM_INTEGER_LITERAL_NOT_PROVEN")
    return v


def _constructor(method: dict, owner: str) -> str | None:
    if (method.get("name") != "<init>"
            or method.get("descriptor") != "()V"
            or method.get("access") != 0x0001):
        return None
    _no_exception_handlers(method)
    rows = _instructions(method)
    if [x.get("opcode") for x in rows] != ["0x2a", "0xb7", "0xb1"]:
        return None
    call = rows[1]
    if (call.get("owner") != "java/lang/Object"
            or call.get("name") != "<init>"
            or call.get("descriptor") != "()V"):
        return None
    return "    public " + _java_name(owner.rsplit("/", 1)[-1]) + "() {}\n"


def _boolean_constant(method: dict) -> str | None:
    if (method.get("access") != 0x0009
            or method.get("descriptor") != "()Z"):
        return None
    _no_exception_handlers(method)
    rows = _instructions(method)
    if [x.get("opcode") for x in rows] != ["0x03", "0xac"]:
        return None
    return ("    public static boolean " + _java_name(method["name"])
            + "() { return false; }\n")


def _boolean_delegate(method: dict, owner: str, declared: list[dict]) -> str | None:
    if (method.get("access") != 0x0009
            or method.get("descriptor") != "()Z"):
        return None
    _no_exception_handlers(method)
    rows = _instructions(method)
    if [x.get("opcode") for x in rows] != ["0xb8", "0xac"]:
        return None
    call = rows[0]
    if (call.get("owner") != owner
            or call.get("descriptor") != "()Z"):
        return None
    method_name = _java_name(call.get("name"))
    _require(any(m.get("name") == method_name
                 and m.get("descriptor") == "()Z"
                 and m.get("access", 0) & 0x0008
                 for m in declared),
             "DELEGATE_METHOD_NOT_ORIGINAL_DECLARED_STATIC_BOOLEAN")
    return ("    public static boolean " + _java_name(method["name"])
            + "() { return " + method_name + "(); }\n")


def _boolean_toggle(method: dict, owner: str, fields: dict,
                    external: dict) -> str | None:
    if (method.get("access") != 0x0009
            or method.get("descriptor") != "(Z)V"):
        return None
    _no_exception_handlers(method)
    rows = _instructions(method)
    if len(rows) < 12 or rows[0].get("opcode") != "0x1a":
        return None
    cond = rows[1]
    if cond.get("opcode") != "0x99":
        return None
    ends = [i for i, row in enumerate(rows)
            if row.get("opcode") == "0xa7"]
    if len(ends) != 1:
        return None
    jump_i = ends[0]
    jump = rows[jump_i]
    index_by_offset = {r["offset"]: i for i, r in enumerate(rows)}
    otherwise = index_by_offset.get(cond.get("branch_target_offset"))
    destination = index_by_offset.get(jump.get("branch_target_offset"))
    if (otherwise != jump_i + 1
            or destination != len(rows) - 1
            or rows[-1].get("opcode") != "0xb1"):
        return None
    if set(_edges(rows)) != {
        (cond["offset"], rows[otherwise]["offset"]),
        (jump["offset"], rows[-1]["offset"]),
    }:
        return None

    def statements(data: list[dict]) -> list[str] | None:
        if not data or len(data) % 2:
            return None
        built = []
        for i in range(0, len(data), 2):
            literal, target = data[i:i+2]
            if (literal.get("opcode") not in ("0x03", "0x04")
                    or target.get("opcode") != "0xb3"):
                return None
            field = _typed_field(target, owner, fields, external, "Z")
            value = "true" if literal["opcode"] == "0x04" else "false"
            built.append(f"        {field} = {value};\n")
        return built

    yes = statements(rows[2:jump_i])
    no = statements(rows[otherwise:-1])
    if yes is None or no is None or len(yes) != len(no):
        return None
    return (
        "    public static void " + _java_name(method["name"])
        + "(boolean value) {\n"
        + "        if (value) {\n" + "".join(yes)
        + "        } else {\n" + "".join(no)
        + "        }\n"
        + "    }\n"
    )


def _array_writer(method: dict, owner: str, fields: dict,
                  external: dict) -> tuple[str, int] | None:
    if (method.get("access") != 0x0009
            or method.get("descriptor") != "()V"):
        return None
    _no_exception_handlers(method)
    rows = _instructions(method)
    if (len(rows) < 5 or (len(rows) - 1) % 4
            or rows[-1].get("opcode") != "0xb1"
            or _edges(rows)):
        return None
    lines = []
    prior_index = -1
    one_array = None
    for j in range(0, len(rows) - 1, 4):
        load, key, value, write = rows[j:j+4]
        if load.get("opcode") != "0xb2" or write.get("opcode") != "0x4f":
            return None
        source = _typed_field(load, owner, fields, external, "[I")
        index, literal = _literal_integer(key), _literal_integer(value)
        if index != prior_index + 1 or (one_array is not None and source != one_array):
            return None
        prior_index, one_array = index, source
        lines.append(f"        {source}[{index}] = {literal};\n")
    source = ("    public static void " + _java_name(method["name"])
              + "() {\n" + "".join(lines) + "    }\n")
    return source, len(lines)


def plan_small_original_owner_methods(
    original: dict, external: dict,
) -> dict:
    owner = original.get("internal_name")
    _require(type(owner) is str and bool(owner), "ORIGINAL_OWNER_UNRESOLVED")
    fields = _fields(original)
    methods = original.get("methods")
    _require(isinstance(methods, list) and bool(methods),
             "ORIGINAL_METHOD_INVENTORY_MISSING")
    emitted = []
    kinds: dict[str, int] = {}
    unhandled = 0
    array_stores = 0
    for method in methods:
        if method.get("name") == "<clinit>":
            continue
        fragment = _constructor(method, owner)
        kind = "default_constructor" if fragment else None
        if fragment is None:
            fragment = _boolean_constant(method)
            if fragment is not None:
                kind = "constant_false_boolean"
        if fragment is None:
            fragment = _boolean_delegate(method, owner, methods)
            if fragment is not None:
                kind = "static_boolean_delegate"
        if fragment is None:
            fragment = _boolean_toggle(method, owner, fields, external)
            if fragment is not None:
                kind = "two_branch_boolean_toggle"
        if fragment is None:
            array = _array_writer(method, owner, fields, external)
            if array is not None:
                fragment, count = array
                kind = "array_element_writer"
                array_stores += count
        if fragment is None:
            unhandled += 1
        else:
            emitted.append(fragment)
            kinds[kind] = kinds.get(kind, 0) + 1
    _require(emitted, "NO_ORIGINAL_SMALL_METHOD_SOURCE_FORMS")
    private = (
        "// PRIVATE: strictly proved original JVM short method source forms.\n"
        "// Remaining methods must NOT be fabricated or defaulted.\n"
        + "".join(emitted)
    )
    return {
        "private_method_source_fragment": private,
        "original_total_jvm_methods": len(methods),
        "original_nonclinit_methods": len(methods) - 1,
        "bounded_short_method_sources": len(emitted),
        "remaining_methods_unreconstructed": unhandled,
        "source_method_form_counts": dict(sorted(kinds.items())),
        "exact_original_array_element_writes": array_stores,
        "full_original_class_method_body_parity_certified": False,
        "unsupported_original_method_bodies_defaulted": False,
        "original_java_source_equivalence_certified": False,
        "runtime_behavior_equivalence_certified": False,
        "canonical_private_original_class_aliases_accepted": False,
    }


def private_short_method_source(
    jar_path: Path, owner_entry: str, out_dir: Path, *,
    original_sha256: str,
) -> dict:
    jar, out = Path(jar_path), Path(out_dir)
    _require(not out.exists() and not out.is_symlink(),
             "OUTPUT_ALREADY_EXISTS")
    _require(type(original_sha256) is str
             and _PIN.fullmatch(original_sha256) is not None,
             "INVALID_EXACT_WHOLE_ORIGINAL_JAR_SHA256")
    _require(jar.is_file() and not jar.is_symlink(),
             "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _require(_digest(jar) == original_sha256.lower(),
             "ORIGINAL_WHOLE_JAR_SHA256_MISMATCH")
    _require(type(owner_entry) is str and owner_entry.endswith(".class")
             and not owner_entry.startswith("/") and "\\" not in owner_entry
             and all(x not in ("", ".", "..") and ":" not in x
                     for x in owner_entry.split("/")),
             "INVALID_PRIVATE_CLASS_ENTRY")
    try:
        with ZipFile(jar) as z:
            names = z.namelist()
            _require(names.count(owner_entry) == 1,
                     "ORIGINAL_OWNER_CLASS_ENTRY_NOT_UNIQUE")
            original = profile_jar_class(jar, owner_entry)
            owner = original["internal_name"]
            refs = {
                r.get("owner")
                for m in original.get("methods", [])
                if m.get("name") != "<clinit>"
                for r in m.get("instructions", [])
                if r.get("opcode") in ("0xb2", "0xb3")
                and r.get("owner") != owner
            }
            _require(all(type(x) is str
                         and names.count(x + ".class") == 1 for x in refs),
                     "ORIGINAL_EXTERNAL_FIELD_CLASS_ENTRY_NOT_UNIQUE")
            external = {
                x: profile_jar_class(jar, x + ".class")
                for x in refs
            }
        report = plan_small_original_owner_methods(original, external)
    except (BadZipFile, BytecodeProfileError,
            ScalarInitializerRecoveryError, OSError, KeyError, IndexError):
        raise SimpleOwnerMethodSourceError("PRIVATE_METHOD_EVIDENCE_UNVERIFIABLE") from None
    _require(_digest(jar) == original_sha256.lower(),
             "ORIGINAL_JAR_CHANGED_DURING_METHOD_RECOVERY")
    fragment = report.pop("private_method_source_fragment")
    aggregate = {
        "schema_version": 1,
        "kind": "original_short_jvm_method_source_form_recovery",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "private_short_method_fragment_sha256":
            hashlib.sha256(fragment.encode("utf-8")).hexdigest(),
        **report,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "short-owner-methods.private.java.txt").open(
            "x", encoding="utf-8", newline="\n") as fd:
        fd.write(fragment)
    with (out / "short-owner-methods.aggregate.json").open(
            "x", encoding="utf-8", newline="\n") as fd:
        json.dump(aggregate, fd, indent=2, sort_keys=True)
        fd.write("\n")
    return aggregate


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("private_owner_class_entry")
    p.add_argument("new_private_output", type=Path)
    p.add_argument("--original-sha256", required=True)
    args = p.parse_args(argv)
    try:
        print(json.dumps(private_short_method_source(
            args.original_jar, args.private_owner_class_entry,
            args.new_private_output, original_sha256=args.original_sha256,
        ), sort_keys=True))
    except SimpleOwnerMethodSourceError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
