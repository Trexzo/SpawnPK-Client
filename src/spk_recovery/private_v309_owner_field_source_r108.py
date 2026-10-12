"""R108: emit private original-derived v309 owner Java field declarations.

Exact original complete-JAR SHA, original 126 Java9 field metadata and all
33 ConstantValue literals. Compile those 33 fields independently with javac9,
then verify exact JVM field access, descriptor and literal values. Remaining
eight static-final references must be assigned separately in original clinit.
This does NOT compile or certify the ten-method complete owner.
Original names, types and configuration literals are PRIVATE outputs only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .private_original_fourth_enum_accessors import digest


class OriginalOwnerFieldSourceError(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise OriginalOwnerFieldSourceError(why)


JAVA_RESERVED = frozenset(
    "abstract assert boolean break byte case catch char class const continue "
    "default do double else enum extends final finally float for goto if "
    "implements import instanceof int interface long native new package "
    "private protected public return short static strictfp super switch "
    "synchronized this throw throws transient try void volatile while "
    "true false null _ var yield record sealed permits".split()
)
PRIMITIVES = {
    "B": "byte", "C": "char", "D": "double", "F": "float",
    "I": "int", "J": "long", "S": "short", "Z": "boolean",
}


def java_identifier(name):
    return (type(name) is str and
            re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", name)
            and name not in JAVA_RESERVED)


def java_type(descriptor):
    need(type(descriptor) is str and descriptor,
         "UNSUPPORTED_JVM_FIELD_DESCRIPTOR")
    if descriptor.startswith("["):
        return java_type(descriptor[1:]) + "[]"
    if descriptor in PRIMITIVES:
        return PRIMITIVES[descriptor]
    if (descriptor.startswith("L") and descriptor.endswith(";") and
            re.fullmatch(r"[A-Za-z0-9_$/]+", descriptor[1:-1])):
        return descriptor[1:-1].replace("/", ".")
    raise OriginalOwnerFieldSourceError(
        "UNSUPPORTED_JVM_FIELD_DESCRIPTOR")


def constant_literal(descriptor, value):
    if descriptor == "Z":
        need(type(value) is int and value in (0, 1),
             "INVALID_ORIGINAL_BOOLEAN_CONSTANT_VALUE")
        return "true" if value else "false"
    if descriptor == "I":
        need(type(value) is int and -2**31 <= value < 2**31,
             "INVALID_ORIGINAL_INT_CONSTANT_VALUE")
        return str(value)
    if descriptor == "Ljava/lang/String;":
        need(type(value) is str and
             all(32 <= ord(c) <= 126 and c not in '"\\'
                 for c in value),
             "UNSUPPORTED_ORIGINAL_JAVA9_STRING_CONSTANT")
        return json.dumps(value, ensure_ascii=True)
    raise OriginalOwnerFieldSourceError(
        "UNSUPPORTED_ORIGINAL_CONSTANTVALUE_FIELD_TYPE")


def source_from_original_owner(profile):
    need(profile.get("classfile_major") == 53
         and profile.get("classfile_minor") == 0,
         "ORIGINAL_OWNER_NOT_JAVA9")
    name = profile.get("internal_name")
    need(type(name) is str and "/" in name and
         all(java_identifier(p) for p in name.split("/")),
         "ORIGINAL_OWNER_JAVA_PACKAGE_OR_CLASS_UNSAFE")
    rows = profile.get("fields")
    need(type(rows) is list and len(rows) == 126,
         "ORIGINAL_126_FIELDS_REQUIRED")
    need(len({x.get("name") for x in rows}) == 126,
         "ORIGINAL_OVERLOADED_JVM_FIELD_NAMES_NOT_VALID_JAVA_SOURCE")

    declarations, constant_declarations, identities = [], [], []
    final_without_constant = 0
    descriptors = {"Z": 0, "I": 0, "L": 0, "[": 0}
    counts = {9: 0, 25: 0}
    constant_types = {"Z": 0, "I": 0, "Ljava/lang/String;": 0}
    for field in rows:
        member = field.get("name")
        descriptor = field.get("descriptor")
        access = field.get("access")
        need(java_identifier(member) and access in counts
             and field.get("signature") is None,
             "ORIGINAL_SOURCE_FIELD_NAME_ACCESS_OR_SIGNATURE_UNSUPPORTED")
        type_name = java_type(descriptor)
        need(descriptor[0] in descriptors,
             "UNSUPPORTED_ORIGINAL_FIELD_JVM_CATEGORY")
        descriptors[descriptor[0]] += 1
        counts[access] += 1
        initializer = ""
        value = field.get("constant_value")
        if value is not None:
            need(access == 25 and descriptor in constant_types,
                 "INVALID_NONFINAL_OR_UNSUPPORTED_CONSTANTVALUE")
            initializer = " = " + constant_literal(descriptor, value)
            constant_types[descriptor] += 1
            constant_declarations.append(
                "  public static final " + type_name + " " + member
                + initializer + ";")
            identities.append((member, descriptor, access, value))
        elif access == 25:
            final_without_constant += 1
        declarations.append(
            "  public static" + (" final" if access == 25 else "")
            + " " + type_name + " " + member + initializer + ";")

    need(counts == {9: 85, 25: 41} and
         descriptors == {"Z": 100, "I": 10, "L": 15, "[": 1}
         and constant_types == {
             "Z": 28, "I": 4, "Ljava/lang/String;": 1}
         and len(identities) == 33 and final_without_constant == 8,
         "ORIGINAL_V309_OWNER_FIELD_DISTRIBUTION_NOT_EXACT")
    package = ".".join(name.split("/")[:-1])
    original_simple = name.rsplit("/", 1)[-1]
    fragment = (
        "// PRIVATE original-v309 owner field-source fragment only.\n"
        "// 126 original JVM field identities and declaration order.\n"
        "// 33 original ConstantValue initializers; 8 other finals need "
        "the exact original clinit assignments.\n"
        "// This is NOT a compilable complete owner class or gameplay client.\n"
        + "\n".join(declarations) + "\n"
    )
    witness_class = "FieldConstantsProofR108"
    need(witness_class != original_simple,
         "PRIVATE_CONSTANT_WITNESS_OWNER_NAME_COLLISION")
    witness = (
        "package " + package + ";\n"
        "public final class " + witness_class + " {\n"
        + "\n".join(constant_declarations) + "\n}\n"
    )
    return fragment, witness, name, witness_class, identities


def build_private_original_owner_fields(
    original_jar, owner_entry, output, *, original_sha256, javac="javac",
):
    original_jar, output = Path(original_jar), Path(output)
    need(not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "FRESH_PRIVATE_SOURCE_OUTPUT_REQUIRED")
    need(isinstance(original_sha256, str) and
         re.fullmatch(r"[a-fA-F0-9]{64}", original_sha256)
         and original_jar.is_file() and not original_jar.is_symlink()
         and digest(original_jar) == original_sha256.lower(),
         "PINNED_ORIGINAL_COMPLETE_JAR_SHA256_MISMATCH")
    need(type(owner_entry) is str and owner_entry.endswith(".class")
         and not owner_entry.startswith("/")
         and "\\" not in owner_entry
         and all(part not in ("", ".", "..")
                 for part in owner_entry.split("/")),
         "ORIGINAL_OWNER_CLASS_ENTRY_UNSAFE")
    with ZipFile(original_jar) as source:
        names = source.namelist()
        need(len(names) == len(set(names)) and
             names.count(owner_entry) == 1,
             "ORIGINAL_OWNER_CLASSFILE_NOT_UNIQUE")
    profile = profile_jar_class(original_jar, owner_entry)
    need(profile.get("internal_name") + ".class" == owner_entry,
         "ORIGINAL_OWNER_INTERNAL_CLASS_IDENTITY_DIFFERENT")
    fragment, witness, name, witness_class, expected = (
        source_from_original_owner(profile))
    package_parts = name.split("/")[:-1]
    with tempfile.TemporaryDirectory(
        prefix="v309-private-fields-r108-", dir=output.parent,
    ) as temporary:
        work = Path(temporary)
        package_path = Path(*package_parts)
        src = work / "source" / package_path
        src.mkdir(parents=True, exist_ok=True)
        compiled_dir = work / "compiled"
        compiled_dir.mkdir()
        field_src = src / (name.rsplit("/", 1)[-1] + ".fields.PRIVATE.java.inc")
        proof_src = src / (witness_class + ".java")
        field_src.write_text(fragment, encoding="utf-8")
        proof_src.write_text(witness, encoding="utf-8")
        try:
            javac_result = subprocess.run(
                [str(javac), "--release", "9", "-g:none", "-proc:none",
                 "-d", str(compiled_dir), str(proof_src)],
                capture_output=True, text=True, timeout=90, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OriginalOwnerFieldSourceError(
                "PRIVATE_JAVAC9_CONSTANT_PROOF_NOT_AVAILABLE") from exc
        need(javac_result.returncode == 0,
             "PRIVATE_JAVAC9_CONSTANT_PROOF_COMPILATION_FAILED")
        private_class = compiled_dir / package_path / (witness_class + ".class")
        generated = [p for p in compiled_dir.rglob("*.class")]
        need(len(generated) == 1 and generated[0] == private_class
             and private_class.is_file(),
             "JAVA9_CONSTANT_PROOF_UNEXPECTED_CLASSFILES")
        with ZipFile(work / "constantproof.jar", "w") as z:
            z.write(private_class,
                    ("/".join(package_parts + [witness_class]) + ".class"))
        candidate = profile_jar_class(
            work / "constantproof.jar",
            "/".join(package_parts + [witness_class]) + ".class")
        need(candidate.get("classfile_major") == 53
             and len(candidate.get("fields", [])) == 33,
             "JAVA9_CONSTANT_PROOF_FIELD_COUNT_NOT_33")
        actual = [
            (f["name"], f["descriptor"], f["access"], f["constant_value"])
            for f in candidate["fields"]
        ]
        need(actual == expected,
             "ORIGINAL_33_CONSTANTVALUE_FIELDS_NOT_RECOMPILED_EXACTLY")
        need(digest(original_jar) == original_sha256.lower(),
             "ORIGINAL_SOURCE_JAR_CHANGED_DURING_PRIVATE_PROOF")
        result = {
            "schema_version": 1,
            "kind": "private_v309_owner_126_source_fields_and_java9_constant_parity",
            "original_complete_jar_sha256": original_sha256.lower(),
            "private_field_source_sha256": hashlib.sha256(
                fragment.encode("utf-8")).hexdigest(),
            "private_javac9_field_constant_class_sha256": hashlib.sha256(
                private_class.read_bytes()).hexdigest(),
            "original_owner_fields_recovered": 126,
            "original_owner_public_static_fields": 85,
            "original_owner_public_static_final_fields": 41,
            "original_owner_ConstantValue_initializers_recovered": 33,
            "javac9_ConstantValue_field_metadata_exact": 33,
            "original_final_fields_needing_clinit_assignments": 8,
            "original_owner_static_initializer_recovered": False,
            "original_owner_ten_method_bodies_recovered": False,
            "original_complete_java9_owner_source_compiled": False,
            "whole_client_runtime_equivalence_certified": False,
        }
        accepted = work / "accepted"
        accepted.mkdir()
        dest = accepted / "private-source" / package_path
        dest.mkdir(parents=True)
        shutil.copyfile(field_src, dest / field_src.name)
        shutil.copyfile(proof_src, dest / proof_src.name)
        shutil.copyfile(
            private_class, accepted / "private-field-constants-java9.class")
        with (accepted / "field-source.aggregate.json").open(
            "x", encoding="utf-8", newline="\n",
        ) as f:
            json.dump(result, f, sort_keys=True, indent=2)
            f.write("\n")
        need(not output.exists() and not output.is_symlink(),
             "PRIVATE_OUTPUT_OCCUPIED_AFTER_JAVA9_VERIFICATION")
        os.rename(accepted, output)
        return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("original_jar", "owner_entry", "new_private_output"):
        p.add_argument(field)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--javac", default="javac")
    args = p.parse_args(argv)
    try:
        print(json.dumps(build_private_original_owner_fields(
            args.original_jar, args.owner_entry,
            args.new_private_output, original_sha256=args.original_sha256,
            javac=args.javac), sort_keys=True))
    except (OriginalOwnerFieldSourceError, BytecodeProfileError,
            ValueError, OSError, KeyError, IndexError, TypeError):
        p.error("PRIVATE_V309_OWNER_FIELD_SOURCE_NOT_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
