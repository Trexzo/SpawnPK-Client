"""R73: exact v309 indexed Properties int[] source with pinned concat bootstrap.

Only an original 22-op JVM protected for-loop is accepted. Verify BOTH
invokedynamic sites refer to the SAME StringConcatFactory bootstrap,
including the exact private recipe with one integer placeholder.
Original enum/field names and recipe are emitted only to private outputs.
No complete source, helper behavior or runtime parity is certified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .boolean_join_witness import BooleanJoinWitnessError, _edges
from .local_exception_primitive_source import _name
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)


class IndexedArraySourceError(ValueError):
    """Original JVM indexed-array source loop has not been proved."""


_PIN = re.compile(r"[a-fA-F0-9]{64}\Z")
_OPS = (
    "0x03", "0x3e", "0x1d", "0xb2", "0xbe", "0xa2",
    "0x2b", "0x1d", "0xba", "0xb6", "0xc6",
    "0xb2", "0x1d", "0x2b", "0x1d", "0xba", "0xb6",
    "0xb8", "0xb6", "0x4f", "0x84", "0xa7",
)
_CONCAT_OWNER = "java/lang/invoke/StringConcatFactory"
_CONCAT_NAME = "makeConcatWithConstants"
_CONCAT_DESCRIPTOR = (
    "(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;"
    "Ljava/lang/invoke/MethodType;Ljava/lang/String;[Ljava/lang/Object;)"
    "Ljava/lang/invoke/CallSite;"
)


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise IndexedArraySourceError(reason)


def _getprop(row: dict) -> bool:
    return (
        row.get("opcode") == "0xb6"
        and row.get("owner") == "java/util/Properties"
        and row.get("name") == "getProperty"
        and row.get("descriptor")
        == "(Ljava/lang/String;)Ljava/lang/String;"
    )


def _recipe(profile: dict, invokedynamic: dict) -> str:
    _need(invokedynamic.get("opcode") == "0xba"
          and invokedynamic.get("descriptor")
          == "(I)Ljava/lang/String;"
          and invokedynamic.get("name") == _CONCAT_NAME,
          "INDEXED_ARRAY_CONCAT_INDY_SIGNATURE_NOT_EXACT")
    index = invokedynamic.get("bootstrap_method_attr_index")
    _need(type(index) is int, "INDEXED_CONCAT_BOOTSTRAP_INDEX_MISSING")
    choices = [
        b for b in profile.get("bootstrap_methods", [])
        if b.get("index") == index
    ]
    _need(len(choices) == 1, "INDEXED_CONCAT_BOOTSTRAP_NOT_UNIQUE")
    entry = choices[0]
    method = entry.get("bootstrap_method", {})
    _need(method.get("reference_kind") == 6
          and method.get("owner") == _CONCAT_OWNER
          and method.get("name") == _CONCAT_NAME
          and method.get("descriptor") == _CONCAT_DESCRIPTOR,
          "INDEXED_ARRAY_NOT_STRING_CONCAT_FACTORY")
    args = entry.get("arguments")
    _need(isinstance(args, list) and len(args) == 1
          and args[0].get("kind") == "string"
          and type(args[0].get("value")) is str,
          "INDEXED_CONCAT_RECIPE_NOT_ONE_LITERAL")
    recipe = args[0]["value"]
    _need(recipe.count("\x01") == 1 and recipe.endswith("\x01")
          and "\x02" not in recipe,
          "INDEXED_CONCAT_RECIPE_HAS_UNSUPPORTED_DYNAMIC_ARGUMENTS")
    _need(all(32 <= ord(ch) <= 126 for ch in recipe[:-1]),
          "INDEXED_CONCAT_RECIPE_NOT_ASCII_SAFE")
    return recipe[:-1]


def plan_private_indexed_array_source(
    profile: dict, private_method: str, method_descriptor: str,
) -> dict:
    owner = profile.get("internal_name")
    _need(type(owner) is str and owner, "ORIGINAL_OWNER_MISSING")
    methods = [
        method for method in profile.get("methods", [])
        if method.get("name") == private_method
        and method.get("descriptor") == method_descriptor
    ]
    _need(len(methods) == 1, "ORIGINAL_METHOD_NOT_UNIQUE")
    method = methods[0]
    rows = _instructions(method)
    _need(rows and rows[0]["offset"] == 0
          and all(a["offset"] + a["length"] == b["offset"]
                  for a, b in zip(rows, rows[1:])),
          "ORIGINAL_JVM_METHOD_NOT_CONTIGUOUS")
    handlers = method.get("exception_handlers")
    _need(isinstance(handlers, list), "ORIGINAL_HANDLER_TABLE_MISSING")
    fields = _fields(profile)
    positions = {r["offset"]: i for i, r in enumerate(rows)}
    try:
        incoming = {target for _, target in _edges(rows)}
    except BooleanJoinWitnessError:
        raise IndexedArraySourceError("ORIGINAL_BRANCH_GRAPH_UNRESOLVED") from None
    proven = []
    for handler in handlers:
        if handler.get("catch_type") != "java/lang/Exception":
            continue
        start, end, catch = (
            handler.get("start_pc"), handler.get("end_pc"),
            handler.get("handler_pc"),
        )
        if any(type(x) is not int or x not in positions
               for x in (start, end, catch)):
            continue
        a, b, c = positions[start], positions[end], positions[catch]
        if c != b + 1 or c + 1 >= len(rows):
            continue
        block = rows[a:b]
        if (len(block) != len(_OPS)
                or tuple(row.get("opcode") for row in block) != _OPS):
            continue
        jump, ignored, after = rows[b:c+2]
        if (jump.get("opcode") != "0xa7"
                or jump.get("branch_target_offset") != after["offset"]
                or ignored.get("opcode") != "0x4e"):
            continue
        loop_cond = block[2]["offset"]
        increment = block[20]["offset"]
        if (block[5].get("branch_target_offset") != jump["offset"]
                or block[10].get("branch_target_offset") != increment
                or block[21].get("branch_target_offset") != loop_cond
                or block[20].get("local_variable_index") not in (3, None)
                or block[20].get("increment") not in (1, None)):
            continue
        first_array, second_array = block[3], block[11]
        if (first_array.get("opcode") != "0xb2"
                or second_array.get("opcode") != "0xb2"
                or any(first_array.get(x) != second_array.get(x)
                       for x in ("owner", "name", "descriptor"))
                or first_array.get("owner") != owner
                or first_array.get("descriptor") != "[I"
                or (first_array.get("name"), "[I") not in fields
                or not fields[(first_array["name"], "[I")]["access"] & 0x0008):
            continue
        if (not _getprop(block[9]) or not _getprop(block[16])
                or block[17].get("owner") != "java/lang/Integer"
                or block[17].get("name") != "valueOf"
                or block[17].get("descriptor")
                != "(Ljava/lang/String;)Ljava/lang/Integer;"
                or block[18].get("owner") != "java/lang/Integer"
                or block[18].get("name") != "intValue"
                or block[18].get("descriptor") != "()I"):
            continue
        if (block[8].get("bootstrap_method_attr_index")
                != block[15].get("bootstrap_method_attr_index")
                or block[8].get("descriptor")
                != block[15].get("descriptor")):
            continue
        key_prefix = _recipe(profile, block[8])
        # The only legitimate interior branch targets are the for-loop
        # test and increment. No unrelated caller or catch may enter.
        allowed = {
            block[2]["offset"], block[20]["offset"]
        }
        interior = {row["offset"] for row in block[1:]}
        if (interior & (incoming - allowed)
                or any(h is not handler
                       and h.get("handler_pc") in interior
                       for h in handlers)):
            continue
        target = _name(first_array["name"])
        key = json.dumps(key_prefix, ensure_ascii=True)
        expression = (
            "originalLocalSlot1.getProperty("
            + key + " + originalArrayIndex)"
        )
        source = (
            "try {\n"
            "    for (int originalArrayIndex = 0; "
            "originalArrayIndex < " + target + ".length; "
            "originalArrayIndex++) {\n"
            "        if (" + expression + " != null) {\n"
            "            " + target + "[originalArrayIndex] = "
            "java.lang.Integer.valueOf(" + expression
            + ").intValue();\n"
            "        }\n"
            "    }\n"
            "} catch (java.lang.Exception ignored) {\n}\n"
        )
        proven.append({
            "original_protected_start": start,
            "original_protected_end": end,
            "original_exception_handler_pc": catch,
            "private_original_static_array_field": target,
            "private_original_concat_recipe_prefix": key_prefix,
            "private_java_source": source,
            "original_same_invokedynamic_bootstrap_both_keys": True,
            "original_index_increment_one": True,
        })
    _need(len({x["original_protected_start"] for x in proven})
          == len(proven), "DUPLICATE_ORIGINAL_INDEXED_LOOP")
    return {
        "private_original_indexed_loop_regions": proven,
        "exact_indexed_array_empty_catch_source_regions": len(proven),
        "exact_indexed_array_22_opcodes_per_region": True,
        "original_concat_recipe_verified_including_prefix": True,
        "original_getProperty_repeated_when_present": True,
        "original_integer_array_store_type_verified": True,
        "original_full_java_method_reconstructed": False,
        "original_helper_side_effects_equivalent": False,
        "original_runtime_behavior_equivalent": False,
    }


def recover_private_indexed_loop(
    original_jar: Path, class_entry: str,
    method_name: str, descriptor: str, out: Path, *,
    complete_jar_sha256: str,
) -> dict:
    jar, target = Path(original_jar), Path(out)
    _need(not target.exists() and not target.is_symlink(),
          "OUTPUT_ALREADY_EXISTS")
    _need(type(complete_jar_sha256) is str
          and _PIN.fullmatch(complete_jar_sha256) is not None,
          "INVALID_ORIGINAL_JAR_COMPLETE_SHA256")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_NOT_FOUND_OR_SYMLINK")
    _need(_digest(jar) == complete_jar_sha256.lower(),
          "ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(class_entry) is str and class_entry.endswith(".class")
          and not class_entry.startswith("/")
          and "\\" not in class_entry
          and all(x not in ("", ".", "..") and ":" not in x
                  for x in class_entry.split("/")),
          "INVALID_PRIVATE_ORIGINAL_CLASS_ENTRY")
    try:
        with ZipFile(jar) as archive:
            _need(archive.namelist().count(class_entry) == 1,
                  "ORIGINAL_JVM_CLASSFILE_NOT_UNIQUE")
            profile = profile_jar_class(jar, class_entry)
        result = plan_private_indexed_array_source(
            profile, method_name, descriptor,
        )
    except (BadZipFile, OSError, BytecodeProfileError,
            ScalarInitializerRecoveryError, KeyError, TypeError, IndexError):
        raise IndexedArraySourceError(
            "ORIGINAL_PRIVATE_INDEXED_ARRAY_SOURCE_NOT_VERIFIABLE"
        ) from None
    _need(_digest(jar) == complete_jar_sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_INDEXED_SOURCE_RECOVERY")
    proof = result.pop("private_original_indexed_loop_regions")
    _need(bool(proof), "NO_EXACT_INDEXED_PROTECTED_LOOP_FOUND")
    source = "".join(x["private_java_source"] for x in proof)
    private_json = json.dumps(proof, indent=2, sort_keys=True) + "\n"
    public = {
        "schema_version": 1,
        "kind": "private_original_indexed_properties_int_array_source",
        "complete_original_jar_sha256": complete_jar_sha256.lower(),
        "private_source_sha256":
            hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "private_operand_graph_sha256":
            hashlib.sha256(private_json.encode("utf-8")).hexdigest(),
        "research_only": True,
        **result,
    }
    target.mkdir(parents=True, exist_ok=False)
    for name, content in (
        ("indexed-array-loop.private.java.txt", source),
        ("indexed-array-loop.private.json", private_json),
        ("indexed-array-loop.aggregate.json",
         json.dumps(public, indent=2, sort_keys=True) + "\n"),
    ):
        with (target/name).open("x", encoding="utf-8", newline="\n") as fd:
            fd.write(content)
    return public


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("private_class_entry")
    p.add_argument("private_method_name")
    p.add_argument("private_method_descriptor")
    p.add_argument("new_private_output", type=Path)
    p.add_argument("--complete-jar-sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(recover_private_indexed_loop(
            a.original_jar, a.private_class_entry,
            a.private_method_name, a.private_method_descriptor,
            a.new_private_output,
            complete_jar_sha256=a.complete_jar_sha256,
        ), sort_keys=True))
    except IndexedArraySourceError as error:
        p.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
