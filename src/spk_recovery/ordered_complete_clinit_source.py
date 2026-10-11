"""R57: reconstruct one PRIVATE ordered Java <clinit> source fragment.

All original instructions must be partitioned into accepted local patterns.
This is stricter than staging separate fragments but is still not proof that
a rebuilt Java source has identical constant-pool operands or runtime behavior.
Original Java, names, original strings and host literals never enter GitHub.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from .boolean_join_witness import _edges
from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _clinit, _digest, _fields,
    _instructions, _literal,
)
from .conditional_concat_string_source import (
    _readable_field, _concat_recipe, _member,
)

class OrderedClinitSourceError(ValueError):
    """Original JVM initializer contains an unsupported or ambiguous form."""

def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise OrderedClinitSourceError(reason)

def _literal_expr(row: dict, descriptor: str) -> str:
    try:
        return _literal(row, descriptor)[0]
    except (ScalarInitializerRecoveryError, KeyError, ValueError):
        raise OrderedClinitSourceError(
            "ORIGINAL_VALUE_NOT_AN_EXACT_SUPPORTED_LITERAL"
        ) from None

def _source_field(row: dict, owner: str, declarations: dict,
                  external: dict) -> str:
    _require(row.get("opcode") == "0xb2", "EXPECTED_GETSTATIC")
    source_owner = row.get("owner")
    fields = declarations if source_owner == owner else _fields(
        external.get(source_owner, {})
    )
    key = row.get("name"), row.get("descriptor")
    found = fields.get(key)
    _require(found is not None and found["access"] & 0x0008,
             "GETSTATIC_SOURCE_NOT_PROVEN_STATIC_FIELD")
    return _readable_field(row, owner)

def _method_source(row: dict, external: dict) -> str:
    _require(row.get("opcode") == "0xb8", "EXPECTED_INVOKESTATIC")
    source_owner = row.get("owner")
    p = external.get(source_owner)
    _require(p is not None, "INVOKESTATIC_CLASS_NOT_IN_PINNED_ORIGINAL_JAR")
    found = [
        m for m in p.get("methods", [])
        if m.get("name") == row.get("name")
        and m.get("descriptor") == row.get("descriptor")
        and m.get("access", 0) & 0x0008
    ]
    _require(len(found) == 1, "INVOKESTATIC_METHOD_NOT_EXACTLY_PROVEN")
    path = source_owner.replace("/", ".")
    _require(all(_member(x) == x for x in path.split(".")),
             "UNREPRESENTABLE_METHOD_OWNER")
    return path + "." + _member(row["name"])

def _line(group: list[dict], owner: str, declarations: dict,
          external: dict, original: dict) -> tuple[str, str, set]:
    ops = [r["opcode"] for r in group]
    dest = group[-1]
    _require(dest.get("opcode") == "0xb3"
             and dest.get("owner") == owner,
             "EXPECTED_EXACT_OWNER_PUTSTATIC")
    field = (dest.get("name"), dest.get("descriptor"))
    desc = field[1]
    _require(field in declarations and declarations[field]["access"] & 0x0008,
             "ORIGINAL_TARGET_NOT_DECLARED_STATIC")
    target = _member(field[0])
    used_edges: set[tuple[int, int]] = set()

    if len(group) == 2:
        value = group[0]
        if value.get("opcode") == "0xb2":
            _require(value.get("descriptor") == desc,
                     "GETSTATIC_VALUE_TARGET_DESCRIPTOR_MISMATCH")
            expr = _source_field(value, owner, declarations, external)
        elif value.get("opcode") == "0x01":
            _require(desc.startswith(("L", "[")), "NULL_ASSIGNED_TO_PRIMITIVE")
            expr = "null"
        else:
            expr = _literal_expr(value, desc)
        return "direct", f"    {target} = {expr};\n", used_edges

    if len(group) == 3:
        a, b, _ = group
        if a.get("opcode") in ("0x10", "0x11", "0x02", "0x03", "0x04",
                               "0x05", "0x06", "0x07", "0x08",
                               "0x12", "0x13") and b.get("opcode") == "0xbc":
            _require(desc == "[I" and b.get("array_primitive_atype") == 10,
                     "UNSUPPORTED_ARRAY_INITIALIZER_TYPE")
            expr = "new int[" + _literal_expr(a, "I") + "]"
            kind = "array"
        elif b.get("opcode") == "0xb8" and a.get("opcode") in (
                "0x10", "0x11", "0x12", "0x13",
                "0x02", "0x03", "0x04", "0x05", "0x06", "0x07", "0x08"):
            _require(desc == "Ljava/lang/Integer;"
                     and b.get("owner") == "java/lang/Integer"
                     and b.get("name") == "valueOf"
                     and b.get("descriptor") == "(I)Ljava/lang/Integer;",
                     "UNSUPPORTED_BOXING_INITIALIZER")
            expr = "Integer.valueOf(" + _literal_expr(a, "I") + ")"
            kind = "boxed_integer"
        elif a.get("opcode") == "0xb2" and b.get("opcode") == "0xb8":
            _require(desc == "Ljava/lang/String;"
                     and b.get("descriptor")
                     == "(" + a.get("descriptor", "") + ")Ljava/lang/String;"
                     and b.get("owner") == a.get("descriptor", "")[1:-1],
                     "UNSUPPORTED_ENUM_HELPER_STRING_CALL")
            source = _source_field(a, owner, declarations, external)
            helper = _method_source(b, external)
            expr = f"{helper}({source})"
            kind = "enum_helper_string"
        elif a.get("opcode") == "0xb8" and b.get("opcode") == "0xba":
            _require(desc == "Ljava/lang/String;"
                     and a.get("descriptor") == "()Ljava/lang/String;",
                     "UNSUPPORTED_EXTERNAL_HELPER_SIGNATURE")
            helper = _method_source(a, external)
            recipe = _concat_recipe(original, b)
            _require(recipe is not None, "UNPROVEN_STRING_CONCAT_BOOTSTRAP")
            prefix, suffix = recipe
            expr = (json.dumps(prefix, ensure_ascii=True) + " + "
                    + helper + "() + " + json.dumps(suffix, ensure_ascii=True))
            kind = "external_concat_string"
        else:
            raise OrderedClinitSourceError("UNSUPPORTED_THREE_INSTRUCTION_ASSIGNMENT")
        return kind, f"    {target} = {expr};\n", used_edges

    if len(group) in (6, 7):
        n = len(group)
        if n == 6:
            a, cond, yes, jump, no, _ = group
            _require(a.get("opcode") == "0xb2"
                     and a.get("descriptor") == "Z"
                     and cond.get("opcode") == "0x9a",
                     "UNSUPPORTED_BOOLEAN_NEGATION_PATTERN")
            expr = "(!" + _source_field(a, owner, declarations, external) + ")"
            kind = "boolean_negation"
        else:
            a, b, cond, yes, jump, no, _ = group
            _require(a.get("opcode") == b.get("opcode") == "0xb2"
                     and cond.get("opcode") == "0xa6"
                     and a.get("descriptor") == b.get("descriptor")
                     and a.get("descriptor", "").startswith(("L", "[")),
                     "UNSUPPORTED_BOOLEAN_REFERENCE_COMPARISON")
            expr = ("(" + _source_field(a, owner, declarations, external)
                    + " == " + _source_field(b, owner, declarations, external)
                    + ")")
            kind = "boolean_reference_equality"
        _require(desc == "Z" and yes.get("opcode") == "0x04"
                 and no.get("opcode") == "0x03"
                 and jump.get("opcode") == "0xa7"
                 and cond.get("branch_target_offset") == no["offset"]
                 and jump.get("branch_target_offset") == dest["offset"],
                 "UNSUPPORTED_BOOLEAN_BRANCH_JOIN")
        used_edges.add((cond["offset"], no["offset"]))
        used_edges.add((jump["offset"], dest["offset"]))
        return kind, f"    {target} = {expr};\n", used_edges

    if len(group) == 8:
        a, b, cond, yes, jump, no, concat, _ = group
        _require(a.get("opcode") == b.get("opcode") == "0xb2"
                 and cond.get("opcode") == "0xa6"
                 and a.get("descriptor") == b.get("descriptor")
                 and a.get("descriptor", "").startswith("L")
                 and yes.get("opcode") in ("0x12", "0x13")
                 and no.get("opcode") in ("0x12", "0x13")
                 and jump.get("opcode") == "0xa7"
                 and cond.get("branch_target_offset") == no["offset"]
                 and jump.get("branch_target_offset") == concat["offset"]
                 and desc == "Ljava/lang/String;",
                 "UNSUPPORTED_CONDITIONAL_CONCAT_BRANCH")
        recipe = _concat_recipe(original, concat)
        _require(recipe is not None, "UNPROVEN_CONDITIONAL_CONCAT_BOOTSTRAP")
        prefix, suffix = recipe
        lhs = _source_field(a, owner, declarations, external)
        rhs = _source_field(b, owner, declarations, external)
        truth = _literal_expr(yes, "Ljava/lang/String;")
        false = _literal_expr(no, "Ljava/lang/String;")
        expr = (json.dumps(prefix, ensure_ascii=True)
                + f" + ({lhs} == {rhs} ? {truth} : {false}) + "
                + json.dumps(suffix, ensure_ascii=True))
        used_edges.add((cond["offset"], no["offset"]))
        used_edges.add((jump["offset"], concat["offset"]))
        return "conditional_concat_string", f"    {target} = {expr};\n", used_edges

    raise OrderedClinitSourceError("UNSUPPORTED_OR_UNACCOUNTED_ORIGINAL_ASSIGNMENT")

def plan_ordered_initializer(original: dict, external: dict) -> dict:
    owner = original.get("internal_name")
    _require(type(owner) is str and owner, "ORIGINAL_OWNER_UNAVAILABLE")
    declarations = _fields(original)
    init = _clinit(original, required=True)
    rows = _instructions(init)
    _require(rows and rows[0]["offset"] == 0
             and rows[-1]["opcode"] == "0xb1",
             "ORIGINAL_INITIALIZER_DOES_NOT_TERMINATE_WITH_RETURN")
    _require(isinstance(init.get("exception_handlers"), list)
             and not init["exception_handlers"],
             "EXCEPTION_HANDLERS_REQUIRE_MANUAL_RECONSTRUCTION")
    _require(
        all(x["offset"] + x["length"] == y["offset"]
            for x, y in zip(rows, rows[1:])),
        "ORIGINAL_OPCODE_LAYOUT_HAS_GAPS",
    )
    declared_write_order = []
    assignments = []
    groups: dict[str, int] = {}
    used_edges: set[tuple[int, int]] = set()
    pending = []
    for row in rows[:-1]:
        pending.append(row)
        if row.get("opcode") != "0xb3":
            continue
        kind, source, accepted_edges = _line(
            pending, owner, declarations, external, original
        )
        for edge in accepted_edges:
            _require(edge not in used_edges, "DUPLICATE_CONDITIONAL_EDGE")
        used_edges.update(accepted_edges)
        assignments.append(source)
        declared_write_order.append((row.get("name"), row.get("descriptor")))
        groups[kind] = groups.get(kind, 0) + 1
        pending = []
    _require(not pending, "UNACCOUNTED_TRAILING_CLINIT_INSTRUCTIONS")
    _require(len(assignments) == len(declared_write_order),
             "LOST_OWNER_STATIC_FIELD_WRITE")
    original_edges = set(_edges(rows))
    _require(original_edges == used_edges,
             "UNACCOUNTED_OR_UNSUPPORTED_CLINIT_CONTROL_FLOW")
    known = (
        original.get("classfile_major") == 53
        and len(declarations) == 126
        and len(rows) == 213
        and len(assignments) == 93
    )
    fragment = (
        "// PRIVATE candidate JVM-derived expression sequence.\n"
        "// Original authorial Java, dependency source and runtime parity unproven.\n"
        "static {\n" + "".join(assignments) + "}\n"
    )
    return {
        "private_source_fragment": fragment,
        "jvm_instructions_consumed": len(rows),
        "owner_static_field_writes_accounted_for": len(assignments),
        "distinct_owner_static_targets": len(set(declared_write_order)),
        "exact_original_static_write_order_in_fragment": True,
        "original_branch_edges_accounted_for": len(used_edges),
        "source_form_counts": dict(sorted(groups.items())),
        "matches_known_v309_126field_213instruction_93write_shape": known,
        "java_source_compilation_parity_certified": False,
        "original_helper_or_enum_binary_parity_certified": False,
        "original_constant_pool_equivalence_certified": False,
        "runtime_equivalence_certified": False,
        "canonical_field_identities_accepted": False,
    }

def recover_private_ordered_initializer(original_jar: Path, class_entry: str,
                                        output: Path, *, sha256: str) -> dict:
    jar, out = Path(original_jar), Path(output)
    _require(not out.exists() and not out.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    _require(type(sha256) is str and len(sha256) == 64
             and all(c in "0123456789abcdefABCDEF" for c in sha256),
             "INVALID_WHOLE_ORIGINAL_JAR_PIN")
    _require(jar.is_file() and not jar.is_symlink(),
             "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _require(_digest(jar) == sha256.lower(),
             "WHOLE_ORIGINAL_JAR_SHA256_MISMATCH")
    _require(type(class_entry) is str and class_entry.endswith(".class")
             and not class_entry.startswith("/") and "\\" not in class_entry
             and all(p not in ("", ".", "..") and ":" not in p
                     for p in class_entry.split("/")),
             "INVALID_PRIVATE_CLASS_ENTRY")
    try:
        with ZipFile(jar) as zipfile:
            names = zipfile.namelist()
            _require(names.count(class_entry) == 1,
                     "ORIGINAL_OWNER_CLASSFILE_NOT_UNIQUE")
            original = profile_jar_class(jar, class_entry)
            owner = original["internal_name"]
            init = _clinit(original, required=True)
            owners = {
                row.get("owner")
                for row in _instructions(init)
                if row.get("opcode") in ("0xb2", "0xb8")
                and row.get("owner") not in (owner, "java/lang/Integer")
            }
            _require(all(type(x) is str and names.count(x + ".class") == 1
                         for x in owners),
                     "ORIGINAL_DEPENDENCY_CLASSFILE_NOT_UNIQUE")
            externals = {
                name: profile_jar_class(jar, name + ".class")
                for name in owners
            }
        result = plan_ordered_initializer(original, externals)
    except (BadZipFile, BytecodeProfileError, ScalarInitializerRecoveryError,
            OSError, KeyError, TypeError, IndexError):
        raise OrderedClinitSourceError(
            "ORIGINAL_CLINIT_SOURCE_PLAN_UNVERIFIABLE"
        ) from None
    _require(_digest(jar) == sha256.lower(),
             "ORIGINAL_JAR_CHANGED_DURING_RECOVERY")
    private = result.pop("private_source_fragment")
    aggregate = {
        "schema_version": 1,
        "kind": "original_jvm_ordered_complete_initializer_source_fragment",
        "research_only": True,
        "original_complete_jar_sha256": sha256.lower(),
        "private_source_fragment_sha256":
            hashlib.sha256(private.encode("utf-8")).hexdigest(),
        **result,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "complete-clinit.private.java.txt").open(
            "x", encoding="utf-8", newline="\n") as fd:
        fd.write(private)
    with (out / "complete-clinit.aggregate.json").open(
            "x", encoding="utf-8", newline="\n") as fd:
        json.dump(aggregate, fd, sort_keys=True, indent=2)
        fd.write("\n")
    return aggregate

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("owner_class_entry")
    parser.add_argument("new_private_output_directory", type=Path)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(recover_private_ordered_initializer(
            args.original_jar, args.owner_class_entry,
            args.new_private_output_directory, sha256=args.sha256,
        ), sort_keys=True))
    except OrderedClinitSourceError as exc:
        parser.error(str(exc))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
