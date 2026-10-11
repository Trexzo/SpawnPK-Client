"""R59: private complete 126-field Java source shell + R57 ordered <clinit>.

Recovers exact original field declaration access, descriptors, ConstantValue
attributes and empty/dynamic final fields from a SHA-256-pinned original class.
Appends one R57 verified instruction-partitioned ordered initializer. This
builds a *source shell*, not original methods/nested enum source or runtime.
No original source literals/class/field names are returned in aggregate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _clinit, _digest, _fields, _instructions,
)
from .ordered_complete_clinit_source import (
    OrderedClinitSourceError, plan_ordered_initializer,
)

class OwnerSourceShellError(ValueError):
    """Original field declarations or initializer lack source-form proof."""


_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")
_SHA = re.compile(r"[0-9A-Fa-f]{64}\Z")


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise OwnerSourceShellError(reason)


def _name(value: str) -> str:
    _need(type(value) is str and _IDENTIFIER.fullmatch(value) is not None,
          "UNREPRESENTABLE_ORIGINAL_JAVA_IDENTIFIER")
    return value


def _java_type(desc: str, owner: str) -> str:
    table = {
        "Z": "boolean", "I": "int", "[I": "int[]",
        "Ljava/lang/String;": "java.lang.String",
        "Ljava/lang/Integer;": "java.lang.Integer",
    }
    if desc in table:
        return table[desc]
    _need(desc.startswith("L" + owner + "$") and desc.endswith(";"),
          "FIELD_DESCRIPTOR_REQUIRES_MANUAL_JAVA_TYPE_SOURCE")
    typename = desc[1:-1].replace("/", ".")
    _need(all(_IDENTIFIER.fullmatch(x) for x in typename.split(".")),
          "UNREPRESENTABLE_ORIGINAL_JVM_NESTED_TYPE")
    return typename


def _literal(value: object, desc: str) -> str:
    _need(value is not None, "LITERAL_CONSTANT_VALUE_MISSING")
    if desc == "Z":
        _need(type(value) is int and value in (0, 1),
              "INVALID_JVM_BOOLEAN_CONSTANTVALUE")
        return "true" if value else "false"
    if desc == "I":
        _need(type(value) is int and -(2**31) <= value < 2**31,
              "INVALID_JVM_INTEGER_CONSTANTVALUE")
        return str(value)
    if desc == "Ljava/lang/String;":
        _need(type(value) is str
              and all(32 <= ord(c) <= 126 for c in value),
              "NONASCII_OR_NONPRINTING_JVM_STRING_NEEDS_MANUAL_SOURCE")
        return json.dumps(value, ensure_ascii=True)
    raise OwnerSourceShellError("UNSUPPORTED_ORIGINAL_CONSTANTVALUE_TYPE")


def plan_private_owner_source_shell(original: dict, external: dict) -> dict:
    owner = original.get("internal_name")
    _need(type(owner) is str and owner
          and original.get("class_access") == 0x0031,
          "ORIGINAL_OWNER_FLAGS_NOT_EXACT_PUBLIC_FINAL_SUPER")
    namespace, _, leaf = owner.rpartition("/")
    classname = _name(leaf)
    package = ".".join(_name(x) for x in namespace.split("/")) if namespace else ""
    fields = original.get("fields")
    _need(isinstance(fields, list) and bool(fields),
          "ORIGINAL_JVM_FIELD_DECLARATIONS_MISSING")
    original_inventory = _fields(original)
    init = _clinit(original, required=True)
    write_counts = {}
    for row in _instructions(init):
        if row.get("opcode") == "0xb3":
            _need(row.get("owner") == owner, "FOREIGN_OWNER_STATIC_WRITE")
            key = (row.get("name"), row.get("descriptor"))
            _need(key in original_inventory, "UNDECLARED_OWNER_STATIC_WRITE")
            write_counts[key] = write_counts.get(key, 0) + 1
    declarations = []
    stat = {
        "original_field_declarations": len(fields),
        "original_static_final_fields": 0,
        "original_jvm_constantvalue_fields": 0,
        "original_blank_dynamic_final_fields": 0,
        "original_mutable_static_fields": 0,
    }
    for field in fields:
        key = (field.get("name"), field.get("descriptor"))
        _need(key in original_inventory, "ORIGINAL_DECLARATION_INVENTORY_MISMATCH")
        flags = field.get("access")
        _need(flags in (0x0009, 0x0019),
              "FIELD_ACCESS_METADATA_NOT_JAVA_SOURCE_REPRESENTABLE")
        _need(field.get("signature") is None,
              "ORIGINAL_GENERIC_FIELD_SIGNATURE_NEEDS_MANUAL_RECOVERY")
        name = _name(key[0])
        typ = _java_type(key[1], owner)
        is_final = flags == 0x0019
        cv = field.get("constant_value")
        initializer = ""
        if is_final:
            stat["original_static_final_fields"] += 1
        else:
            stat["original_mutable_static_fields"] += 1
        if cv is not None:
            _need(is_final and write_counts.get(key, 0) == 0,
                  "CONSTANTVALUE_FIELD_IS_MUTABLE_OR_REASSIGNED")
            initializer = " = " + _literal(cv, key[1])
            stat["original_jvm_constantvalue_fields"] += 1
        elif is_final:
            _need(write_counts.get(key, 0) == 1,
                  "BLANK_FINAL_MUST_HAVE_EXACTLY_ONE_CLINIT_STORE")
            stat["original_blank_dynamic_final_fields"] += 1
        declarations.append("    public static "
                            + ("final " if is_final else "")
                            + typ + " " + name + initializer + ";\n")
    complete_init = plan_ordered_initializer(original, external)
    private_init = complete_init.pop("private_source_fragment")
    _need(complete_init["owner_static_field_writes_accounted_for"]
          == sum(write_counts.values()),
          "SOURCE_INITIALIZER_NOT_ALL_DECLARED_WRITES")
    private_source = (
        "// PRIVATE original JVM declaration and initializer source shell.\n"
        "// Original methods / nested enums / exact runtime unverified.\n"
        + ("package " + package + ";\n" if package else "")
        + "public final class " + classname + " {\n"
        + "".join(declarations)
        + private_init
        + "}\n"
    )
    return {
        "private_complete_owner_source_shell": private_source,
        **stat,
        "original_declarations_plus_init_in_one_java_shell": True,
        "ordered_initializer_writes": complete_init["owner_static_field_writes_accounted_for"],
        "ordered_initializer_instructions": complete_init["jvm_instructions_consumed"],
        "ordered_initializer_source_form_counts": complete_init["source_form_counts"],
        "private_shell_dependency_source_uses_original_binary_names": True,
        "original_helper_method_bodies_recovered": False,
        "nested_enum_java_source_and_innerclasses_equivalent": False,
        "java_recompilation_field_metadata_equivalence_certified": False,
        "whole_original_classfile_equivalent": False,
        "runtime_behavior_equivalent": False,
        "canonical_original_aliases_accepted": False,
    }


def private_complete_owner_shell(
    original_jar: Path, class_entry: str, out: Path, *, sha256: str,
) -> dict:
    jar, output = Path(original_jar), Path(out)
    _need(not output.exists() and not output.is_symlink(),
          "OUTPUT_ALREADY_EXISTS")
    _need(type(sha256) is str and _SHA.fullmatch(sha256) is not None,
          "INVALID_ORIGINAL_WHOLE_JAR_SHA256")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar) == sha256.lower(), "ORIGINAL_WHOLE_JAR_SHA256_MISMATCH")
    _need(type(class_entry) is str and class_entry.endswith(".class")
          and not class_entry.startswith("/") and "\\" not in class_entry
          and all(x not in ("", ".", "..") and ":" not in x
                  for x in class_entry.split("/")),
          "ORIGINAL_PRIVATE_CLASS_ENTRY_INVALID")
    try:
        with ZipFile(jar) as z:
            filenames = z.namelist()
            _need(filenames.count(class_entry) == 1,
                  "ORIGINAL_OWNER_CLASSFILE_NOT_UNIQUE")
            original = profile_jar_class(jar, class_entry)
            owner = original["internal_name"]
            rows = _instructions(_clinit(original, required=True))
            refs = {
                row.get("owner") for row in rows
                if row.get("opcode") in ("0xb2", "0xb8")
                and row.get("owner") not in (owner, "java/lang/Integer")
            }
            _need(all(type(x) is str
                      and filenames.count(x + ".class") == 1 for x in refs),
                  "ORIGINAL_NESTED_OR_HELPER_CLASSFILE_NOT_UNIQUE")
            external = {
                name: profile_jar_class(jar, name + ".class")
                for name in refs
            }
        proof = plan_private_owner_source_shell(original, external)
    except (BadZipFile, BytecodeProfileError, ScalarInitializerRecoveryError,
            OrderedClinitSourceError, OSError, KeyError, TypeError, IndexError):
        raise OwnerSourceShellError("ORIGINAL_SOURCE_SHELL_UNVERIFIABLE") from None
    _need(_digest(jar) == sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_SHELL_RECOVERY")
    fragment = proof.pop("private_complete_owner_source_shell")
    report = {
        "schema_version": 1,
        "kind": "original_jvm_fields_and_entire_clinit_private_source_shell",
        "research_only": True,
        "original_complete_jar_sha256": sha256.lower(),
        "private_source_shell_sha256":
            hashlib.sha256(fragment.encode("utf-8")).hexdigest(),
        **proof,
    }
    output.mkdir(parents=True, exist_ok=False)
    with (output / "original-owner-shell.private.java.txt").open(
            "x", encoding="utf-8", newline="\n") as fd:
        fd.write(fragment)
    with (output / "original-owner-shell.aggregate.json").open(
            "x", encoding="utf-8", newline="\n") as fd:
        json.dump(report, fd, indent=2, sort_keys=True)
        fd.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("private_class_entry")
    p.add_argument("new_private_output", type=Path)
    p.add_argument("--sha256", required=True)
    args = p.parse_args(argv)
    try:
        print(json.dumps(private_complete_owner_shell(
            args.original_jar, args.private_class_entry,
            args.new_private_output, sha256=args.sha256,
        ), sort_keys=True))
    except OwnerSourceShellError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
