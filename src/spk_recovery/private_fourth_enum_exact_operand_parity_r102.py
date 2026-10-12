"""R102: strict nine-method original-v309 fourth enum resolved operand proof.

Permitted normalization, no others:
  * one surrogate nested binary type name -> original colliding nested identity
  * positional enum-constant JVM fields and generated values-array field
  * one Java compiler-generated values-array helper method
  * two synthetic accessors paired by their exact private String field target
All real private String field identities, getter names, all six literals,
ordinary invocations, JVM operands and method metadata must stay exact.

This does NOT compare outer owner InnerClasses or certify R95 / runtime parity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

from .bytecode_profile import profile_jar_class
from .private_fourth_enum_nine_shape_witness import (
    FourthEnumSourceShapeError, classify,
)
from .private_original_fourth_enum_accessors import (
    OriginalEnumAccessorError, _accessors, digest,
)


class FourthEnumExactOperandError(ValueError):
    pass


def need(test, reason):
    if not test:
        raise FourthEnumExactOperandError(reason)


def _rename_type(value, src, dst):
    need(isinstance(value, str), "JVM_TYPE_TOKEN_NOT_STRING")
    if src == dst:
        return value
    if value == src:
        return dst
    # Rebind only JVM complete internal names in descriptors, not substring
    # references or arbitrary user String constants.
    needle = "L" + src + ";"
    changed = value.replace(needle, "L" + dst + ";")
    need(src not in changed, "UNSUPPORTED_SURROGATE_TYPE_REFERENCE")
    return changed


def _get_private_accessors(profile):
    try:
        return _accessors(profile)
    except (OriginalEnumAccessorError, KeyError, IndexError, ValueError) as exc:
        raise FourthEnumExactOperandError(
            "FOURTH_ENUM_R99_ACCESSORS_NOT_EXACT") from exc


def _roles(profile):
    owner = profile.get("internal_name")
    need(isinstance(owner, str) and "$" in owner,
         "FOURTH_ENUM_BINARY_IDENTITY_REQUIRED")
    private_access = _get_private_accessors(profile)
    all_methods = profile.get("methods", [])
    need(len(all_methods) == 9, "FOURTH_ENUM_NINE_METHODS_REQUIRED")
    all_fields = set(private_access)
    roles = {}
    by_name = {(m["name"], m["descriptor"]): m for m in all_methods}
    need(len(by_name) == 9, "FOURTH_ENUM_DUPLICATE_METHOD_IDENTITY")
    for key, sign in (
        ("values", ("values", "()[L" + owner + ";")),
        ("valueOf", ("valueOf", "(Ljava/lang/String;)L" + owner + ";")),
        ("constructor", ("<init>",
                         "(Ljava/lang/String;ILjava/lang/String;Ljava/lang/String;)V")),
        ("initializer", ("<clinit>", "()V")),
    ):
        need(sign in by_name, "FOURTH_ENUM_REQUIRED_METHOD_MISSING")
        roles[key] = by_name[sign]
    helpers = [m for m in all_methods
               if m.get("descriptor") == "()[L" + owner + ";"
               and m.get("name") != "values"
               and m.get("access") == 0x100a]
    need(len(helpers) == 1, "FOURTH_ENUM_VALUES_HELPER_NOT_UNIQUE")
    roles["values_helper"] = helpers[0]
    for field in sorted(all_fields):
        getters = [m for m in all_methods
                   if m.get("descriptor") == "()Ljava/lang/String;"
                   and m.get("access") == 1
                   and len(m.get("instructions", [])) == 3
                   and m["instructions"][1].get("owner") == owner
                   and m["instructions"][1].get("name") == field]
        need(len(getters) == 1,
             "FOURTH_ENUM_PRIVATE_STRING_GETTER_NOT_UNIQUE")
        roles["getter:" + field] = getters[0]
        roles["accessor:" + field] = private_access[field]
    need(len(roles) == 9 and
         len({(m["name"], m["descriptor"]) for m in roles.values()}) == 9,
         "FOURTH_ENUM_NINE_METHOD_ROLES_NOT_EXACT")
    return roles


def _field_aliases(original, candidate):
    a, b = original["fields"], candidate["fields"]
    oldowner = original["internal_name"]
    newowner = candidate["internal_name"]
    need(len(a) == len(b) == 5, "FOURTH_ENUM_FIVE_FIELDS_REQUIRED")
    rename = {}
    generated = 0
    for left, right in zip(a, b):
        candidate_signature = right.get("signature")
        if candidate_signature is not None:
            candidate_signature = _rename_type(
                candidate_signature, newowner, oldowner)
        need(left["access"] == right["access"]
             and left.get("signature") == candidate_signature,
             "ORIGINAL_ENUM_FIELD_SIGNATURE_DIFFERENCE")
        need(left["descriptor"] ==
             _rename_type(right["descriptor"], newowner, oldowner)
             and left.get("constant_value") == right.get("constant_value"),
             "ORIGINAL_ENUM_FIELD_DESCRIPTOR_OR_CONSTANT_DIFFERENCE")
        generated_field = (
            left["access"] == 0x4019 and
            left["descriptor"] == "L" + oldowner + ";"
        ) or (
            left["access"] == 0x101a and
            left["descriptor"] == "[L" + oldowner + ";"
        )
        if generated_field:
            generated += 1
        else:
            need(left["name"] == right["name"],
                 "ORIGINAL_NON_GENERATED_FIELD_IDENTITY_CHANGED")
        need(right["name"] not in rename,
             "AMBIGUOUS_COMPILER_GENERATED_FIELD_ALIAS")
        rename[right["name"]] = left["name"]
    need(generated == 3, "EXPECTED_TWO_CONSTANTS_ONE_VALUES_FIELD")
    return rename


def _normalize_instruction(row, candidate_owner, original_owner,
                           field_aliases, method_aliases):
    need(isinstance(row, dict)
         and isinstance(row.get("opcode"), str),
         "JVM_RESOLVED_INSTRUCTION_REQUIRED")
    excluded = {
        "offset", "length", "constant_pool_index", "mnemonic",
        "bootstrap_method_attr_index",
    }
    projected = {k: v for k, v in row.items() if k not in excluded}
    need("branch_target_offset" not in projected
         and "switch_target_offsets" not in projected
         and "switch_default_target_offset" not in projected,
         "UNEXPECTED_JVM_BRANCH_OR_SWITCH_IN_NINE_METHODS")
    op = projected["opcode"]
    # Exact string ldc values must remain exact. Only a CONSTANT_Class ldc
    # is a JVM type and may rebind from candidate name to original.
    for k in ("owner", "descriptor", "class_name", "array_type", "type"):
        if isinstance(projected.get(k), str):
            projected[k] = _rename_type(
                projected[k], candidate_owner, original_owner)
    if projected.get("constant_pool_tag") == 7 and isinstance(
        projected.get("constant"), str
    ):
        projected["constant"] = _rename_type(
            projected["constant"], candidate_owner, original_owner)
    if projected.get("owner") == original_owner and (
        op in ("0xb2", "0xb3", "0xb4", "0xb5")
    ):
        name = projected.get("name")
        need(name in field_aliases, "UNREVIEWED_ENUM_FIELD_REFERENCE")
        projected["name"] = field_aliases[name]
    if projected.get("owner") == original_owner and (
        op in ("0xb6", "0xb7", "0xb8", "0xb9")
    ):
        name = projected.get("name")
        if name in method_aliases:
            projected["name"] = method_aliases[name]
    return projected


def exact_fourth_enum_operands(original, candidate):
    old = original.get("internal_name")
    new = candidate.get("internal_name")
    need(isinstance(old, str) and isinstance(new, str)
         and "$" in old and "$" in new and old != new
         and old.rsplit("$", 1)[0] == new.rsplit("$", 1)[0],
         "SURROGATE_AND_ORIGINAL_MUST_SHARE_OUTER_OWNER")
    outer = old.rsplit("$", 1)[0]
    need(old == outer + "$" + outer.rsplit("/", 1)[-1],
         "ORIGINAL_FOURTH_ENUM_NAME_COLLISION_NOT_EXACT")
    try:
        classify(original)
        classify(candidate)
    except (FourthEnumSourceShapeError, ValueError, KeyError, IndexError) as exc:
        raise FourthEnumExactOperandError(
            "ORIGINAL_OR_CANDIDATE_NINE_OPCODE_SHAPES_NOT_ACCEPTED") from exc
    need(original["class_access"] == candidate["class_access"]
         and original["classfile_major"] == candidate["classfile_major"] == 53
         and original["classfile_minor"] == candidate["classfile_minor"]
         and original.get("super_name") == candidate.get("super_name")
         and original.get("interfaces") == candidate.get("interfaces"),
         "ORIGINAL_ENUM_CLASS_HEADER_MISMATCH")
    field_map = _field_aliases(original, candidate)
    roles_a = _roles(original)
    roles_b = _roles(candidate)
    need(set(roles_a) == set(roles_b),
         "ORIGINAL_TWO_GETTER_OR_ACCESSOR_FIELDS_NOT_EXACT")
    helper_alias = {
        roles_b["values_helper"]["name"]: roles_a["values_helper"]["name"]
    }
    for field in sorted(_get_private_accessors(original)):
        source = roles_b["accessor:" + field]["name"]
        dest = roles_a["accessor:" + field]["name"]
        need(source not in helper_alias or helper_alias[source] == dest,
             "JAVAC_MEMBER_ALIAS_NOT_ONE_TO_ONE")
        helper_alias[source] = dest
    need(len(helper_alias) == 3,
         "EXPECTED_ONE_VALUES_HELPER_TWO_SYNTHETIC_ACCESSOR_ALIASES")
    # A method inventory maps accessors by the fields they read, but the
    # *ordered* original accessor field targets must also be preserved.
    # The first actual-v309 surrogate was opcode-identical yet reversed
    # those two reads; do not accept it as an exact source reconstruction.
    def ordered_accessor_targets(profile):
        owner = profile["internal_name"]
        return [
            m["instructions"][1].get("name")
            for m in profile["methods"]
            if m.get("access") == 0x1008
            and m.get("descriptor") ==
                "(L" + owner + ";)Ljava/lang/String;"
        ]
    need(ordered_accessor_targets(original) ==
         ordered_accessor_targets(candidate),
         "ORIGINAL_SYNTHETIC_ACCESSOR_TARGET_ORDER_CHANGED")
    matched = 0
    operand_rows = 0
    for role in sorted(roles_a):
        left, right = roles_a[role], roles_b[role]
        # Getter names, the standard enum entry points, constructors and
        # initializer are original JVM identities. Only the one compiler
        # values-helper and two synthetic accessor *names* are aliased.
        if role != "values_helper" and not role.startswith("accessor:"):
            need(left["name"] == right["name"],
                 "ORIGINAL_NON_GENERATED_ENUM_METHOD_NAME_CHANGED")
        need(left["access"] == right["access"] and
             left.get("signature") == right.get("signature") and
             left["descriptor"] == _rename_type(
                 right["descriptor"], new, old) and
             left.get("max_stack") == right.get("max_stack") and
             left.get("max_locals") == right.get("max_locals") and
             left.get("exception_handlers") == right.get("exception_handlers") and
             left.get("stackmap_frames") == right.get("stackmap_frames"),
             "ORIGINAL_ENUM_METHOD_FRAME_OR_DECLARATION_MISMATCH")
        arows = left.get("instructions", [])
        brows = right.get("instructions", [])
        need(len(arows) == len(brows) and len(arows) > 0,
             "ORIGINAL_ENUM_METHOD_OPCODE_LENGTH_MISMATCH")
        for a, b in zip(arows, brows):
            left_projected = _normalize_instruction(
                a, old, old,
                {f["name"]: f["name"] for f in original["fields"]},
                {})
            right_projected = _normalize_instruction(
                b, new, old, field_map, helper_alias)
            need(left_projected == right_projected,
                 "ORIGINAL_ENUM_EXACT_RESOLVED_OPERAND_MISMATCH")
            operand_rows += 1
        matched += 1
    need(matched == 9, "ALL_NINE_ENUM_METHODS_NOT_COMPARED")
    return {
        "schema_version": 1,
        "kind": "private_v309_fourth_enum_nine_exact_operands_after_scoped_aliases",
        "original_methods_operand_and_opcode_exact": 9,
        "original_instructions_operand_and_opcode_exact": operand_rows,
        "permitted_compiler_generated_enum_field_aliases": 3,
        "permitted_generated_helper_aliases": 1,
        "permitted_synthetic_accessor_aliases_by_exact_private_field": 2,
        "permitted_surrogate_nested_type_aliases": 1,
        "ordinary_getter_aliases_used": 0,
        "private_string_data_field_aliases_used": 0,
        "original_InnerClasses_binary_metadata_parity_certified": False,
        "four_nested_enums_R95_parity_certified": False,
        "R97_complete_owner_source_acceptance_certified": False,
        "whole_client_runtime_equivalence_certified": False,
    }


def replay_private_fourth_enum_exact_operands(
    original_jar, candidate_jar, owner_entry, surrogate_simple, output, *,
    original_sha256, candidate_sha256,
):
    original_jar, candidate_jar, output = map(
        Path, (original_jar, candidate_jar, output))
    need(output.parent.is_dir() and not output.parent.is_symlink()
         and not output.exists() and not output.is_symlink(),
         "NEW_PRIVATE_OPERAND_PROOF_OUTPUT_REQUIRED")
    need(original_jar.resolve() != candidate_jar.resolve(),
         "ORIGINAL_AND_CANDIDATE_JARS_MUST_DIFFER")
    for path, pin in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        need(path.is_file() and not path.is_symlink()
             and isinstance(pin, str) and re.fullmatch(r"[0-9a-fA-F]{64}", pin)
             and digest(path) == pin.lower(),
             "ORIGINAL_OR_CANDIDATE_COMPLETE_JAR_SHA256_MISMATCH")
    need(isinstance(owner_entry, str) and owner_entry.endswith(".class")
         and not owner_entry.startswith("/") and "\\" not in owner_entry
         and ".." not in owner_entry and
         isinstance(surrogate_simple, str)
         and re.fullmatch("[A-Za-z_$][A-Za-z0-9_$]*", surrogate_simple),
         "UNSAFE_PRIVATE_ENUM_IDENTITY")
    owner = owner_entry[:-6]
    original_enum = owner + "$" + owner.rsplit("/", 1)[-1] + ".class"
    candidate_enum = owner + "$" + surrogate_simple + ".class"
    with ZipFile(original_jar) as a, ZipFile(candidate_jar) as b:
        need(a.namelist().count(owner_entry) == 1
             and a.namelist().count(original_enum) == 1
             and b.namelist().count(owner_entry) == 1
             and b.namelist().count(candidate_enum) == 1
             and len(a.namelist()) == len(set(a.namelist()))
             and len(b.namelist()) == len(set(b.namelist())),
             "ORIGINAL_OR_CANDIDATE_OWNER_OR_ENUM_MISSING")
    proof = exact_fourth_enum_operands(
        profile_jar_class(original_jar, original_enum),
        profile_jar_class(candidate_jar, candidate_enum))
    need(digest(original_jar) == original_sha256.lower()
         and digest(candidate_jar) == candidate_sha256.lower(),
         "PINNED_JARS_CHANGED_DURING_EXACT_OPERAND_REPLAY")
    report = {
        **proof,
        "original_complete_jar_sha256": original_sha256.lower(),
        "candidate_complete_jar_sha256": candidate_sha256.lower(),
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "fourth-enum-exact-operands.aggregate.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("original_jar", "candidate_jar", "owner_entry",
                "surrogate_simple", "new_private_output"):
        p.add_argument(arg)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(replay_private_fourth_enum_exact_operands(
            a.original_jar, a.candidate_jar, a.owner_entry,
            a.surrogate_simple, a.new_private_output,
            original_sha256=a.original_sha256,
            candidate_sha256=a.candidate_sha256), sort_keys=True))
    except FourthEnumExactOperandError:
        p.error("PRIVATE_FOURTH_ENUM_EXACT_OPERANDS_NOT_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
