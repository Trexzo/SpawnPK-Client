"""R67: reconstruct PRIVATE exact local Java try/catch primitive source forms.

Only an exact 13-instruction JVM protected range with both assignment paths,
the same String lookup and same original static Boolean target, and a proved
empty Exception catch is emitted. Local slot 1 remains unresolved; no
complete original source or runtime equivalence is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from .boolean_join_witness import BooleanJoinWitnessError, _edges
from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)


class LocalExceptionPrimitiveSourceError(ValueError):
    """Original JVM protected primitive region cannot be exactly reconstructed."""


_SHA = re.compile(r"[0-9a-fA-F]{64}\Z")
_ID = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")
_PATTERN = (
    "0x2b", "0x12", "0xb6", "0xc7", None, "0xb3", "0xa7",
    "0x2b", "0x12", "0xb6", "0xb8", "0xb6", "0xb3",
)


def _need(ok: bool, error: str) -> None:
    if not ok:
        raise LocalExceptionPrimitiveSourceError(error)


def _name(text: object) -> str:
    _need(type(text) is str and _ID.fullmatch(text) is not None,
          "ORIGINAL_JAVA_MEMBER_NAME_UNREPRESENTABLE")
    return text


def _owner_name(owner: str) -> str:
    parts = owner.replace("/", ".").split(".")
    _need(bool(parts) and all(_ID.fullmatch(p) is not None for p in parts),
          "ORIGINAL_HELPER_CLASS_JAVA_NAME_UNREPRESENTABLE")
    return ".".join(parts)


def _literal(row: dict) -> str:
    value = row.get("constant")
    _need(row.get("opcode") == "0x12"
          and row.get("constant_pool_tag") == 8
          and type(value) is str,
          "ORIGINAL_LDC_NOT_EXACT_STRING_LITERAL")
    _need(all(32 <= ord(c) <= 126 for c in value),
          "NONPRINTING_OR_NONASCII_KEY_SOURCE_FORM_UNSUPPORTED")
    return json.dumps(value, ensure_ascii=True)


def _lookup_equal(a: dict, b: dict) -> bool:
    return all(a.get(k) == b.get(k)
               for k in ("opcode", "owner", "name", "descriptor"))


def _single_handler_region(method: dict, handler: dict,
                           instructions: list[dict], fields: dict,
                           owner: str, incoming: set[int]) -> dict | None:
    start = handler.get("start_pc")
    end = handler.get("end_pc")
    target = handler.get("handler_pc")
    offsets = {r["offset"]: i for i, r in enumerate(instructions)}
    if (handler.get("catch_type") != "java/lang/Exception"
            or any(type(x) is not int for x in (start, end, target))
            or start not in offsets or end not in offsets
            or target not in offsets):
        return None
    start_i, end_i, handler_i = (offsets[start], offsets[end],
                                 offsets[target])
    if (handler_i != end_i + 1 or handler_i + 1 >= len(instructions)):
        return None
    group = instructions[start_i:end_i]
    if (len(group) != len(_PATTERN)
            or any(expected is not None and row.get("opcode") != expected
                   for row, expected in zip(group, _PATTERN))
            or group[4].get("opcode") not in ("0x03", "0x04", "0x10")):
        return None
    # Exact original catch bytecode: goto after single astore_3, with
    # empty original catch body. No extra cleanup or handler side effects.
    endgoto, caught, after = instructions[end_i:handler_i+2]
    if (endgoto.get("opcode") != "0xa7"
            or caught.get("opcode") != "0x4e"
            or endgoto.get("branch_target_offset") != after["offset"]):
        return None
    a, key1, read1, branch, fallback, field1, jump, _, key2, read2, convert, get_bool, field2 = group
    if (branch.get("branch_target_offset") != group[7]["offset"]
            or jump.get("branch_target_offset") != endgoto["offset"]):
        return None
    if (key1.get("constant") != key2.get("constant")
            or key1.get("constant_pool_tag") != 8
            or key2.get("constant_pool_tag") != 8
            or type(key1.get("constant")) is not str
            or not _lookup_equal(read1, read2)
            or any(field1.get(k) != field2.get(k)
                   for k in ("owner", "name", "descriptor"))
            or field1.get("owner") != owner
            or field1.get("descriptor") not in ("Z", "I")):
        return None
    target_desc = field1["descriptor"]
    decl = fields.get((field1.get("name"), target_desc))
    if decl is None or not decl["access"] & 0x0008:
        return None
    read_desc = read1.get("descriptor")
    boxed_name = "Boolean" if target_desc == "Z" else "Integer"
    unbox_name = "booleanValue" if target_desc == "Z" else "intValue"
    if (type(read_desc) is not str
            or not read_desc.startswith("(Ljava/lang/String;)L")
            or not read_desc.endswith(";")
            or convert.get("descriptor")
            != "(" + read_desc.split(")", 1)[1] + ")Ljava/lang/" + boxed_name + ";"
            or get_bool.get("owner") != "java/lang/" + boxed_name
            or get_bool.get("descriptor") != "()" + target_desc
            or get_bool.get("name") != unbox_name):
        return None
    if target_desc == "Z":
        if fallback.get("opcode") not in ("0x03", "0x04"):
            return None
        default_expr = "true" if fallback["opcode"] == "0x04" else "false"
    else:
        if fallback.get("opcode") == "0x03":
            default_expr = "0"
        elif (fallback.get("opcode") == "0x10"
              and type(fallback.get("int_constant")) is int
              and -128 <= fallback["int_constant"] <= 127):
            default_expr = str(fallback["int_constant"])
        else:
            return None
    # Internal protected region may be entered at its START; no incoming
    # control-flow edge or exception handler may cut into its interior.
    covered = {r["offset"] for r in group[1:]}
    allowed_incoming = {group[7]["offset"], endgoto["offset"]}
    if (covered & (incoming - allowed_incoming)):
        return None
    if any(h is not handler and h.get("handler_pc") in covered
           for h in method.get("exception_handlers", [])):
        return None
    _need(all(x["offset"] + x["length"] == y["offset"]
              for x, y in zip(group, group[1:])),
          "ORIGINAL_PROTECTED_BOOLEAN_REGION_NOT_CONTIGUOUS")
    field_name = _name(field1["name"])
    lookup = _name(read1["name"])
    conversion = _owner_name(convert["owner"]) + "." + _name(convert["name"])
    first_key = _literal(key1)
    # The original JVM executes the same lookup AGAIN on the non-null path.
    # Do not deduplicate that call; doing so could change side effects.
    expr = "originalLocalSlot1." + lookup + "(" + first_key + ")"
    source = (
        "try {\n"
        "    if (" + expr + " == null) {\n"
        "        " + field_name + " = "
        + default_expr + ";\n"
        "    } else {\n"
        "        " + field_name + " = " + conversion
        + "(" + expr + ")." + unbox_name + "();\n"
        "    }\n"
        "} catch (java.lang.Exception ignored) {\n"
        "}\n"
    )
    return {
        "private_source": source,
        "private_original_field": field_name,
        "private_original_key": key1["constant"],
        "original_start_pc": start,
        "original_end_pc": end,
        "original_handler_pc": target,
        "original_primitive_descriptor": target_desc,
        "original_null_default_expression": default_expr,
        "lookup_evaluated_twice_on_nonnull_branch": True,
        "empty_catch_verified": True,
        "source_local_slot_one_type_proven": False,
    }


def plan_private_local_exception_primitive_sources(
    original: dict, method_name: str, descriptor: str,
) -> dict:
    owner = original.get("internal_name")
    _need(type(owner) is str and owner, "ORIGINAL_OWNER_UNKNOWN")
    methods = original.get("methods")
    _need(isinstance(methods, list), "JVM_METHODS_MISSING")
    exact = [m for m in methods
             if m.get("name") == method_name
             and m.get("descriptor") == descriptor]
    _need(len(exact) == 1, "EXACT_PRIVATE_METHOD_IDENTITY_NOT_UNIQUE")
    method = exact[0]
    rows = _instructions(method)
    _need(rows and rows[0]["offset"] == 0
          and all(a["offset"] + a["length"] == b["offset"]
                  for a, b in zip(rows, rows[1:])),
          "ORIGINAL_METHOD_HAS_GAPS_OR_UNACCOUNTED_INSTRUCTIONS")
    handlers = method.get("exception_handlers")
    _need(isinstance(handlers, list), "ORIGINAL_EXCEPTION_TABLE_MISSING")
    try:
        branch_edges = _edges(rows)
    except BooleanJoinWitnessError:
        raise LocalExceptionPrimitiveSourceError(
            "ORIGINAL_JVM_BRANCH_TARGET_NOT_VERIFIABLE"
        ) from None
    incoming = {target for _, target in branch_edges}
    fields = _fields(original)
    original_local_handlers = [
        h for h in handlers if h.get("catch_type") == "java/lang/Exception"
    ]
    accepted = []
    for h in original_local_handlers:
        proof = _single_handler_region(
            method, h, rows, fields, owner, incoming)
        if proof is not None:
            accepted.append(proof)
    _need(len({x["original_start_pc"] for x in accepted}) == len(accepted),
          "ORIGINAL_PROTECTED_REGION_PROOF_DUPLICATED")
    _need(all(x["empty_catch_verified"] for x in accepted),
          "NONEMPTY_CATCH_REJECTED")
    fragments = [
        "// PRIVATE JVM-derived protected primitive source form.\n"
        "// originalLocalSlot1 is a placeholder; full method absent.\n"
        + x["private_source"] for x in accepted
    ]
    return {
        "private_local_region_sources": accepted,
        "private_source_fragments": "".join(fragments),
        "original_local_exception_handlers": len(original_local_handlers),
        "exact_conditional_primitive_try_catch_regions": len(accepted),
        "other_exception_local_regions_not_reconstructed":
            len(original_local_handlers) - len(accepted),
        "conditional_boolean_regions": sum(
            x["original_primitive_descriptor"] == "Z" for x in accepted),
        "conditional_integer_regions": sum(
            x["original_primitive_descriptor"] == "I" for x in accepted),
        "conditional_true_default_regions": sum(
            x["original_primitive_descriptor"] == "Z"
            and x["original_null_default_expression"] == "true"
            for x in accepted),
        "conditional_false_default_regions": sum(
            x["original_primitive_descriptor"] == "Z"
            and x["original_null_default_expression"] == "false"
            for x in accepted),
        "conditional_integer_zero_default_regions": sum(
            x["original_primitive_descriptor"] == "I"
            and x["original_null_default_expression"] == "0"
            for x in accepted),
        "conditional_integer_nonzero_default_regions": sum(
            x["original_primitive_descriptor"] == "I"
            and x["original_null_default_expression"] != "0"
            for x in accepted),
        "each_reconstructed_catch_has_exact_empty_body": True,
        "original_local_slot_one_java_type_recovered": False,
        "complete_original_method_java_source_recovered": False,
        "protected_region_exception_order_runtime_certified": False,
        "helper_implementation_side_effects_equivalent": False,
        "entire_original_class_runtime_equivalent": False,
    }


def recover_private_local_exception_sources(
    original_jar: Path, class_entry: str, private_method_name: str,
    private_descriptor: str, output_dir: Path, *, original_sha256: str,
) -> dict:
    jar, out = Path(original_jar), Path(output_dir)
    _need(not out.exists() and not out.is_symlink(),
          "OUTPUT_ALREADY_EXISTS")
    _need(type(original_sha256) is str
          and _SHA.fullmatch(original_sha256) is not None,
          "INVALID_WHOLE_JAR_SHA256_PIN")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar) == original_sha256.lower(),
          "ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(class_entry) is str and class_entry.endswith(".class")
          and not class_entry.startswith("/")
          and "\\" not in class_entry
          and all(p not in ("", ".", "..") and ":" not in p
                  for p in class_entry.split("/")),
          "INVALID_PRIVATE_JVM_CLASS_ENTRY")
    try:
        with ZipFile(jar) as archive:
            _need(archive.namelist().count(class_entry) == 1,
                  "ORIGINAL_OWNER_CLASS_ENTRY_NOT_UNIQUE")
            profile = profile_jar_class(jar, class_entry)
        proof = plan_private_local_exception_primitive_sources(
            profile, private_method_name, private_descriptor)
    except (OSError, BadZipFile, BytecodeProfileError,
            ScalarInitializerRecoveryError, KeyError, IndexError, TypeError):
        raise LocalExceptionPrimitiveSourceError(
            "ORIGINAL_PRIVATE_PROTECTED_BOOLEAN_SOURCES_NOT_VERIFIABLE"
        ) from None
    _need(_digest(jar) == original_sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_SOURCE_RECOVERY")
    blocks = proof.pop("private_local_region_sources")
    source = proof.pop("private_source_fragments")
    _need(bool(blocks), "NO_EXACT_LOCAL_EXCEPTION_BOOLEAN_SOURCE_REGIONS")
    raw = json.dumps(blocks, sort_keys=True, indent=2) + "\n"
    report = {
        "schema_version": 1,
        "kind": "private_exact_original_empty_catch_conditional_primitive_source",
        "original_complete_jar_sha256": original_sha256.lower(),
        "research_only": True,
        "private_original_region_graph_sha256":
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "private_local_java_source_sha256":
            hashlib.sha256(source.encode("utf-8")).hexdigest(),
        **proof,
    }
    out.mkdir(parents=True, exist_ok=False)
    for filename, data in (
        ("local-exception-primitive-sites.private.json", raw),
        ("local-exception-primitive-source.private.java.txt", source),
        ("local-exception-primitive.aggregate.json",
         json.dumps(report, sort_keys=True, indent=2) + "\n"),
    ):
        with (out / filename).open("x", encoding="utf-8", newline="\n") as fd:
            fd.write(data)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("original_class_entry")
    parser.add_argument("private_method_name")
    parser.add_argument("private_method_descriptor")
    parser.add_argument("new_private_output", type=Path)
    parser.add_argument("--original-sha256", required=True)
    opts = parser.parse_args(argv)
    try:
        print(json.dumps(recover_private_local_exception_sources(
            opts.original_jar, opts.original_class_entry,
            opts.private_method_name, opts.private_method_descriptor,
            opts.new_private_output, original_sha256=opts.original_sha256,
        ), sort_keys=True))
    except LocalExceptionPrimitiveSourceError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
