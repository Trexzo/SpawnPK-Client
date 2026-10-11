"""Bounded recovered Java enum parity with explicit JVM-field name aliases.

This compares class method instructions and field declarations *after*
strict positional aliases of enum constants, values array and the compiler
generated values helper. It never accepts obfuscated-to-source identities,
publishes private field names, or claims runtime/source equivalence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .bytecode_profile import BytecodeProfileError, profile_jar_class


class NestedEnumSourceParityError(ValueError):
    """Exact pinned enum source evidence is unsupported or mismatched."""


def _need(test: bool, reason: str) -> None:
    if not test:
        raise NestedEnumSourceParityError(reason)


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _enum_shape(profile: dict) -> dict:
    _need(isinstance(profile, dict), "ENUM_PROFILE_INVALID")
    owner = profile.get("internal_name")
    _need(type(owner) is str and owner and "$" in owner,
          "NESTED_ENUM_OWNER_REQUIRED")
    _need(profile.get("super_name") == "java/lang/Enum"
          and type(profile.get("class_access")) is int
          and profile["class_access"] & 0x4000
          and profile["class_access"] & 0x0010,
          "NOT_FINAL_JVM_ENUM")
    _need(isinstance(profile.get("interfaces"), list)
          and not profile["interfaces"], "ENUM_INTERFACE_EVIDENCE_UNEXPECTED")
    fields = profile.get("fields")
    _need(isinstance(fields, list), "ENUM_FIELDS_MISSING")
    constants = [r for r in fields if isinstance(r, dict)
                 and r.get("descriptor") == "L" + owner + ";"
                 and type(r.get("access")) is int
                 and r["access"] & 0x4019 == 0x4019]
    arrays = [r for r in fields if isinstance(r, dict)
              and r.get("descriptor") == "[L" + owner + ";"
              and type(r.get("access")) is int
              and r["access"] & 0x001A == 0x001A]
    _need(len(constants) > 0 and len(arrays) == 1,
          "ENUM_CONSTANT_OR_VALUES_ARRAY_AMBIGUOUS")
    _need(len({x["name"] for x in fields}) == len(fields),
          "DUPLICATE_ENUM_FIELD_NAMES")
    methods = profile.get("methods")
    _need(isinstance(methods, list), "ENUM_METHODS_MISSING")
    helper = [m for m in methods if isinstance(m, dict)
              and m.get("descriptor") == "()[L" + owner + ";"
              and m.get("name") != "values"
              and type(m.get("access")) is int
              and m["access"] & 0x000A == 0x000A]
    _need(len(helper) == 1, "ENUM_VALUES_HELPER_AMBIGUOUS")
    _need(any(m.get("name") == "values"
              and m.get("descriptor") == "()[L" + owner + ";"
              for m in methods), "ENUM_VALUES_METHOD_MISSING")
    _need(any(m.get("name") == "valueOf"
              and m.get("descriptor") == "(Ljava/lang/String;)L" + owner + ";"
              for m in methods), "ENUM_VALUEOF_METHOD_MISSING")
    _need(any(m.get("name") == "<clinit>" and m.get("descriptor") == "()V"
              for m in methods), "ENUM_CLINIT_MISSING")
    _need(len({(m["name"], m["descriptor"]) for m in methods}) == len(methods),
          "DUPLICATE_ENUM_METHODS")
    return {
        "fields": fields, "constants": constants, "values_field": arrays[0],
        "methods": methods, "helper": helper[0], "owner": owner,
    }


def _alias_structure(original: dict, candidate: dict) -> tuple[dict, dict]:
    a, b = _enum_shape(original), _enum_shape(candidate)
    _need(a["owner"] == b["owner"], "NO_ACCEPTED_ENUM_OWNER_ALIAS")
    _need(original["class_access"] == candidate["class_access"]
          and original["classfile_major"] == candidate["classfile_major"]
          and original["classfile_minor"] == candidate["classfile_minor"]
          and original.get("signature") == candidate.get("signature"),
          "ENUM_CLASS_HEADER_MISMATCH")
    _need(len(a["fields"]) == len(b["fields"])
          and len(a["constants"]) == len(b["constants"])
          and len(a["methods"]) == len(b["methods"]),
          "ENUM_INVENTORY_COUNT_MISMATCH")
    renames = {}
    for old, new in zip(a["fields"], b["fields"]):
        _need(
            old["descriptor"] == new["descriptor"]
            and old["access"] == new["access"]
            and old.get("signature") == new.get("signature")
            and old.get("constant_value") == new.get("constant_value"),
            "ENUM_FIELD_METADATA_MISMATCH",
        )
        # Non-enum data fields must retain their JVM identity. Only
        # synthetic generated enum constant/values fields may be aliased.
        permitted = old in a["constants"] or old is a["values_field"]
        _need(old["name"] == new["name"] or permitted,
              "UNREVIEWED_ENUM_DATA_FIELD_ALIAS")
        renames[(a["owner"], old["name"], old["descriptor"])] = new["name"]
    method_alias = {
        (a["owner"], a["helper"]["name"], a["helper"]["descriptor"]):
            b["helper"]["name"],
    }
    return renames, method_alias


def _normal_instructions(method: dict, renames: dict, method_alias: dict) -> list[dict]:
    instructions = method.get("instructions")
    _need(isinstance(instructions, list) and bool(instructions),
          "ENUM_METHOD_CODE_REQUIRED")
    offsets = [r.get("offset") for r in instructions]
    _need(all(type(x) is int for x in offsets)
          and len(set(offsets)) == len(offsets),
          "ENUM_INSTRUCTION_OFFSETS_INVALID")
    offset_to_index = {off: i for i, off in enumerate(offsets)}
    excluded = {
        "offset", "length", "constant_pool_index",
        "mnemonic", "bootstrap_method_attr_index",
    }
    sequence = []
    for row in instructions:
        _need(isinstance(row, dict) and isinstance(row.get("opcode"), str),
              "INVALID_ENUM_INSTRUCTION")
        ins = {k: v for k, v in row.items() if k not in excluded}
        if "branch_target_offset" in ins:
            dest = ins.pop("branch_target_offset")
            _need(dest in offset_to_index, "ENUM_BRANCH_OUTSIDE_CODE")
            ins["branch_target_index"] = offset_to_index[dest]
        if "switch_default_target_offset" in ins or "switch_target_offsets" in ins:
            raise NestedEnumSourceParityError("ENUM_SWITCH_CONTROL_FLOW_UNSUPPORTED")
        if "owner" in ins and "name" in ins and "descriptor" in ins:
            key = ins["owner"], ins["name"], ins["descriptor"]
            if ins["opcode"] in ("0xb2", "0xb3", "0xb4", "0xb5"):
                if key in renames:
                    ins["name"] = renames[key]
            elif ins["opcode"] in ("0xb6", "0xb7", "0xb8", "0xb9"):
                if key in method_alias:
                    ins["name"] = method_alias[key]
        sequence.append(ins)
    return sequence


def compare_nested_enum_source(
    original: dict, candidate: dict, *,
    original_jar_sha256: str,
) -> dict[str, Any]:
    """Instruction parity modulo *declared* enum name aliases only."""
    _need(type(original_jar_sha256) is str
          and re.fullmatch(r"[a-fA-F0-9]{64}", original_jar_sha256) is not None,
          "INVALID_ORIGINAL_JAR_SHA256")
    field_alias, method_alias = _alias_structure(original, candidate)
    a, b = _enum_shape(original), _enum_shape(candidate)
    target = {(m["name"], m["descriptor"]): m for m in b["methods"]}
    _need(len(target) == len(b["methods"]), "DUPLICATE_ENUM_TARGET_METHOD")
    results = []
    for old in a["methods"]:
        signature = (
            method_alias.get((a["owner"], old["name"], old["descriptor"]),
                             old["name"]), old["descriptor"]
        )
        other = target.get(signature)
        _need(other is not None and old["access"] == other["access"]
              and old.get("signature") == other.get("signature"),
              "ENUM_METHOD_DECLARATION_MISMATCH")
        left = _normal_instructions(old, field_alias, method_alias)
        right = _normal_instructions(other, {}, {})
        results.append(left == right
                       and old.get("max_stack") == other.get("max_stack")
                       and old.get("max_locals") == other.get("max_locals")
                       and old.get("stackmap_frames") == other.get("stackmap_frames")
                       and old.get("exception_handlers") == other.get("exception_handlers"))
    _need(all(results), "ENUM_METHOD_INSTRUCTION_PARITY_MISMATCH")
    return {
        "schema_version": 1,
        "kind": "private_jvm_nested_enum_source_alias_parity",
        "research_only": True,
        "original_jar_sha256": original_jar_sha256.lower(),
        "enum_constant_count": len(a["constants"]),
        "method_declarations_compared": len(results),
        "method_instruction_parity_after_aliases": sum(results),
        "allowed_enum_constant_field_alias_count": len(a["constants"]),
        "allowed_compiler_helper_alias_count": 1,
        "source_level_enum_constant_names_accepted_as_original_jvm_fields": False,
        "canonical_enum_identity_accepted": False,
        "runtime_equivalence_certified": False,
        "whole_client_source_reconstructed": False,
    }


def replay_nested_enum_source(
    original_jar: Path, candidate_jar: Path, *, original_sha256: str,
    candidate_sha256: str, entries: list[str],
) -> dict[str, Any]:
    _need(len(entries) in (1, 2, 3) and len(set(entries)) == len(entries),
          "ENUM_ENTRY_COUNT_INVALID")
    for entry in entries:
        _need(type(entry) is str and entry.endswith(".class")
              and "$" in entry and not entry.startswith("/")
              and "\\" not in entry
              and all(x not in ("", ".", "..") and ":" not in x
                      for x in entry.split("/")),
              "INVALID_NESTED_ENUM_ENTRY")
    for path, sha in ((Path(original_jar), original_sha256),
                      (Path(candidate_jar), candidate_sha256)):
        _need(type(sha) is str and re.fullmatch(r"[a-fA-F0-9]{64}", sha) is not None,
              "INVALID_JAR_SHA_PIN")
        _need(path.is_file() and not path.is_symlink(),
              "ENUM_JAR_MISSING_OR_SYMLINK")
        _need(_hash_file(path) == sha.lower(), "ENUM_JAR_SHA_MISMATCH")
    try:
        results = [
            compare_nested_enum_source(
                profile_jar_class(original_jar, entry),
                profile_jar_class(candidate_jar, entry),
                original_jar_sha256=original_sha256,
            )
            for entry in entries
        ]
    except (BytecodeProfileError, OSError, KeyError, IndexError, ValueError):
        raise NestedEnumSourceParityError("ENUM_SOURCE_INPUT_UNEVALUABLE") from None
    for path, sha in ((Path(original_jar), original_sha256),
                      (Path(candidate_jar), candidate_sha256)):
        _need(_hash_file(path) == sha.lower(), "ENUM_JAR_CHANGED_DURING_REPLAY")
    payload = {
        "schema_version": 1,
        "kind": "private_three_nested_enum_source_parity",
        "original_jar_sha256": original_sha256.lower(),
        "candidate_jar_sha256": candidate_sha256.lower(),
        "enum_classes_checked": len(results),
        "enum_constant_declarations": sum(x["enum_constant_count"] for x in results),
        "method_declarations_compared":
            sum(x["method_declarations_compared"] for x in results),
        "exact_normalized_method_bodies":
            sum(x["method_instruction_parity_after_aliases"] for x in results),
        "all_exact_after_explicit_aliases": True,
        "canonical_identity_accepted": False,
        "whole_client_source_reconstructed": False,
        "runtime_equivalence_certified": False,
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("candidate_jar", type=Path)
    p.add_argument("entries", nargs="+")
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    try:
        result = replay_nested_enum_source(
            args.original_jar, args.candidate_jar,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
            entries=args.entries,
        )
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as output:
                json.dump(result, output, sort_keys=True, indent=2)
                output.write("\n")
        print(json.dumps(result, sort_keys=True))
    except NestedEnumSourceParityError as exc:
        p.error(str(exc))
    except (OSError, ValueError):
        p.error("ENUM_PARITY_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
