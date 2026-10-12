"""R101: emit actual original-derived fourth nested enum Java9 source privately.

The original owner simple name collides with the fourth enum's nested simple
name, so this emits a *surrogate* Java nested enum under the exact original
owner's package/name. Never publish generated source or its literals.

Acceptance here: pinned exact original JAR, R99/R100 method shapes, six exact
original initializer strings, original private field/getter identities, Java9
compiler success and all nine opcode sequences against the compiled candidate.
It is NOT R95 binary alias or whole-owner runtime acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import keyword
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .bytecode_profile import profile_jar_class
from .private_four_nested_enum_acceptance import nested_entries
from .private_fourth_enum_nine_shape_witness import (
    FourthEnumSourceShapeError, classify, prove_fourth_enum_source_shapes,
)
from .private_original_fourth_enum_accessors import (
    OriginalEnumAccessorError, _accessors, digest,
)


class OriginalFourthEnumSourceError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise OriginalFourthEnumSourceError(reason)


JAVA_RESERVED = frozenset(
    "abstract assert boolean break byte case catch char class const continue "
    "default do double else enum extends final finally float for goto if "
    "implements import instanceof int interface long native new package "
    "private protected public return short static strictfp super switch "
    "synchronized this throw throws transient try void volatile while "
    "true false null _ var yield record sealed permits non-sealed".split()
)


def java_identifier(text):
    return (isinstance(text, str)
            and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", text)
            and text not in JAVA_RESERVED and not keyword.iskeyword(text))


def safe_literal(text):
    # v309's actual six strings are printable ASCII. Deliberately reject
    # Unicode escapes, backslashes, line breaks and control characters here:
    # Java performs Unicode-escape translation even inside String tokens.
    need(isinstance(text, str)
         and all(0x20 <= ord(c) <= 0x7e and c not in '"\\'
                 for c in text),
         "UNSUPPORTED_OR_UNSAFE_ORIGINAL_JAVA_STRING_LITERAL")
    return json.dumps(text, ensure_ascii=True)


def literal_six(profile):
    methods = [m for m in profile["methods"]
               if m.get("name") == "<clinit>" and m.get("descriptor") == "()V"]
    need(len(methods) == 1, "ORIGINAL_FOURTH_ENUM_INITIALIZER_NOT_UNIQUE")
    ins = methods[0]["instructions"]
    need(len(ins) == 19, "ORIGINAL_FOURTH_ENUM_INITIALIZER_LENGTH_NOT_19")
    positions = (2, 4, 5, 10, 12, 13)
    strings = []
    for i in positions:
        row = ins[i]
        need(row.get("opcode") == "0x12"
             and row.get("constant_pool_tag") == 8
             and isinstance(row.get("constant"), str),
             "ORIGINAL_FOURTH_ENUM_CONSTANT_NOT_JVM_STRING")
        strings.append(row["constant"])
    need(strings[0] != strings[3]
         and java_identifier(strings[0])
         and java_identifier(strings[3]),
         "ORIGINAL_ENUM_CONSTANT_NAMES_NOT_VALID_JAVA")
    for s in strings:
        safe_literal(s)
    return strings


def source_parts(original, surrogate_simple):
    try:
        classify(original)
        accessors = _accessors(original)
    except (FourthEnumSourceShapeError, OriginalEnumAccessorError) as exc:
        raise OriginalFourthEnumSourceError(
            "EXACT_ORIGINAL_R99_R100_SOURCE_SHAPES_NOT_PROVEN") from exc
    owner = original["internal_name"]
    need("$" in owner, "ORIGINAL_ENUM_NOT_NESTED")
    outer = owner.rsplit("$", 1)[0]
    outer_simple = outer.rsplit("/", 1)[-1]
    need(owner == outer + "$" + outer_simple,
         "ORIGINAL_ENUM_SIMPLE_NAME_NOT_COLLIDING")
    need(java_identifier(outer_simple) and java_identifier(surrogate_simple)
         and surrogate_simple != outer_simple
         and all(java_identifier(n) for n in outer.split("/")[:-1]),
         "ORIGINAL_OR_SURROGATE_JAVA_NAME_UNSAFE")
    labels = literal_six(original)
    ordered_fields = [f["name"] for f in original["fields"]
                      if f.get("access") == 0x0002
                      and f.get("descriptor") == "Ljava/lang/String;"]
    need(len(ordered_fields) == 2 and set(ordered_fields) == set(accessors),
         "PRIVATE_STRING_FIELD_SOURCE_NOT_UNIQUE")
    getters = []
    for method in original["methods"]:
        if (method.get("descriptor") != "()Ljava/lang/String;"
                or method.get("access") != 0x0001):
            continue
        ins = method["instructions"]
        need(len(ins) == 3 and [x["opcode"] for x in ins]
             == ["0x2a", "0xb4", "0xb0"],
             "ORIGINAL_GETTER_THREE_OPCODE_PATTERN_CHANGED")
        ref = ins[1]
        need(ref.get("owner") == owner
             and ref.get("name") in ordered_fields
             and ref.get("descriptor") == "Ljava/lang/String;",
             "ORIGINAL_GETTER_PRIVATE_FIELD_NOT_RESOLVED")
        getters.append((method["name"], ref["name"]))
    need(len(getters) == 2
         and {ref for _, ref in getters} == set(ordered_fields)
         and len({name for name, _ in getters}) == 2
         and all(java_identifier(name) for name, _ in getters)
         and len(set(ordered_fields + [x[0] for x in getters])) == 4,
         "ORIGINAL_GETTERS_NOT_DISTINCT_JAVA_NAMES")
    need(not (set(labels[::3]) & set(ordered_fields))
         and surrogate_simple not in labels
         and all(surrogate_simple != name for name, _ in getters),
         "SURROGATE_OR_SOURCE_FIELD_ENUM_NAME_COLLISION")
    pkg = ".".join(outer.split("/")[:-1])
    return outer, outer_simple, pkg, labels, ordered_fields, getters


def private_java_source(original, surrogate_simple="ReconstructedEnum"):
    outer, outer_simple, package, labels, fields, getters = source_parts(
        original, surrogate_simple)
    lines = []
    if package:
        lines.append("package " + package + ";")
    lines.extend([
        "public final class " + outer_simple + " {",
        "  public enum " + surrogate_simple + " {",
        "    " + labels[0] + "(" + safe_literal(labels[1]) + ","
        + safe_literal(labels[2]) + "),",
        "    " + labels[3] + "(" + safe_literal(labels[4]) + ","
        + safe_literal(labels[5]) + ");",
        "    private String " + fields[0] + ", " + fields[1] + ";",
        "    " + surrogate_simple + "(String x, String y) { this."
        + fields[0] + " = x; this." + fields[1] + " = y; }",
    ])
    for name, field in getters:
        lines.append("    public String " + name
                     + "() { return this." + field + "; }")
    lines.extend([
        "  }",
        "  public static String r101ProbeA(" + surrogate_simple
        + " x) { return x." + fields[0] + "; }",
        "  public static String r101ProbeB(" + surrogate_simple
        + " x) { return x." + fields[1] + "; }",
        "}",
        "",
    ])
    return "\n".join(lines), outer, surrogate_simple


def compile_private_original_enum_source(
    original_jar, original_owner_entry, output, *,
    original_sha256, surrogate_simple="ReconstructedEnum", javac="javac",
):
    jar, output = Path(original_jar), Path(output)
    need(output.parent.is_dir() and not output.parent.is_symlink()
         and not output.exists() and not output.is_symlink(),
         "FRESH_PRIVATE_SOURCE_OUTPUT_REQUIRED")
    need(jar.is_file() and not jar.is_symlink()
         and isinstance(original_sha256, str)
         and re.fullmatch(r"[a-fA-F0-9]{64}", original_sha256)
         and digest(jar) == original_sha256.lower(),
         "ORIGINAL_COMPLETE_JAR_SHA256_NOT_PINNED")
    need(isinstance(original_owner_entry, str)
         and original_owner_entry.endswith(".class")
         and not original_owner_entry.startswith("/")
         and "\\" not in original_owner_entry
         and all(x not in ("", ".", "..")
                 for x in original_owner_entry.split("/")),
         "ORIGINAL_OWNER_CLASS_ENTRY_UNSAFE")
    owner = original_owner_entry[:-6]
    original_enum_entry = owner + "$" + owner.rsplit("/", 1)[-1] + ".class"
    with ZipFile(jar) as z:
        names = z.namelist()
        need(len(names) == len(set(names)) and
             names.count(original_owner_entry) == 1 and
             names.count(original_enum_entry) == 1,
             "ORIGINAL_JAR_DUPLICATE_OR_OWNER_MISSING")
        nested = [n for n in names if n.startswith(owner + "$")
                  and n.endswith(".class")]
        need(len(nested) == 4 and original_enum_entry in nested,
             "ORIGINAL_FOUR_ENUM_ENTRIES_NOT_EXACT")
    original = profile_jar_class(jar, original_enum_entry)
    source, outer, inner = private_java_source(original, surrogate_simple)
    outer_simple = outer.rsplit("/", 1)[-1]
    with tempfile.TemporaryDirectory(
        prefix="v309-r101-", dir=output.parent,
    ) as temporary:
        root = Path(temporary)
        src = root / "private-source"
        classes = root / "classes"
        relative = Path(*outer.split("/"))
        source_file = src / relative.parent / (outer_simple + ".java")
        source_file.parent.mkdir(parents=True, exist_ok=True)
        classes.mkdir()
        source_file.write_text(source, encoding="utf-8")
        try:
            process = subprocess.run(
                [str(javac), "--release", "9", "-g:none", "-proc:none",
                 "-d", str(classes), str(source_file)],
                capture_output=True, text=True, timeout=90, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OriginalFourthEnumSourceError(
                "PRIVATE_JAVA9_COMPILER_UNAVAILABLE") from exc
        need(process.returncode == 0,
             "PRIVATE_ORIGINAL_ENUM_JAVA9_SOURCE_COMPILATION_FAILED")
        compiled_enum_entry = outer + "$" + inner + ".class"
        expected = {
            outer + ".class", compiled_enum_entry,
        }
        produced = {p.relative_to(classes).as_posix()
                    for p in classes.rglob("*.class")}
        need(produced == expected, "PRIVATE_SOURCE_COMPILER_UNEXPECTED_CLASSES")
        private_jar = root / "private-java9-source-candidate.jar"
        with ZipFile(private_jar, "w") as archive:
            for name in sorted(expected):
                archive.write(classes / name, name)
        candidate = profile_jar_class(private_jar, compiled_enum_entry)
        try:
            proof = prove_fourth_enum_source_shapes(original, candidate)
        except FourthEnumSourceShapeError as exc:
            raise OriginalFourthEnumSourceError(
                "REAL_ORIGINAL_FOURTH_ENUM_NINE_SHAPES_NOT_EQUAL") from exc
        need(literal_six(original) == literal_six(candidate),
             "PRIVATE_SOURCE_SIX_INITIALIZER_LITERALS_CHANGED")
        orig_fields = [f["name"] for f in original["fields"]
                       if f.get("access") == 0x0002
                       and f.get("descriptor") == "Ljava/lang/String;"]
        cand_fields = [f["name"] for f in candidate["fields"]
                       if f.get("access") == 0x0002
                       and f.get("descriptor") == "Ljava/lang/String;"]
        need(orig_fields == cand_fields,
             "ORIGINAL_TWO_PRIVATE_STRING_FIELD_IDENTITIES_CHANGED")
        orig_getters = [(m["name"], m["instructions"][1].get("name"))
                        for m in original["methods"]
                        if m.get("descriptor") == "()Ljava/lang/String;"
                        and m.get("access") == 0x0001]
        cand_getters = [(m["name"], m["instructions"][1].get("name"))
                        for m in candidate["methods"]
                        if m.get("descriptor") == "()Ljava/lang/String;"
                        and m.get("access") == 0x0001]
        need(orig_getters == cand_getters,
             "ORIGINAL_TWO_GETTER_FIELD_RELATIONSHIPS_CHANGED")
        need(digest(jar) == original_sha256.lower(),
             "PINNED_ORIGINAL_JAR_CHANGED_DURING_COMPILATION")
        result = {
            "schema_version": 1,
            "kind": "v309_private_original_fourth_enum_source_derived_java9",
            "original_complete_jar_sha256": original_sha256.lower(),
            "private_java_source_sha256": hashlib.sha256(
                source.encode("utf-8")).hexdigest(),
            "compiled_candidate_jar_sha256": digest(private_jar),
            "original_enum_methods_compiled_and_shapes_matched": 9,
            "original_six_initializer_literal_values_preserved": True,
            "original_two_private_string_field_identifiers_preserved": True,
            "original_two_getter_to_field_relations_preserved": True,
            "R95_original_nested_enum_parity_certified": False,
            "R97_whole_owner_source_acceptance_certified": False,
            "original_authorial_source_identity_proven": False,
            "whole_client_runtime_equivalence_certified": False,
        }
        accepted = root / "accepted"
        accepted.mkdir()
        dest_source = accepted / "private-java-source" / relative.parent
        dest_source.mkdir(parents=True)
        shutil.copyfile(source_file, dest_source / (outer_simple + ".java"))
        shutil.copyfile(private_jar, accepted / "private-java9-source-candidate.jar")
        with (accepted / "source-recovery.aggregate.json").open(
            "x", encoding="utf-8", newline="\n",
        ) as file:
            json.dump(result, file, sort_keys=True, indent=2)
            file.write("\n")
        need(not output.exists() and not output.is_symlink(),
             "PRIVATE_OUTPUT_OCCUPIED_AFTER_PROOF")
        os.rename(accepted, output)
        return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar")
    p.add_argument("original_owner_entry")
    p.add_argument("new_private_output")
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--surrogate-simple", default="ReconstructedEnum")
    p.add_argument("--javac", default="javac")
    a = p.parse_args(argv)
    try:
        result = compile_private_original_enum_source(
            a.original_jar, a.original_owner_entry, a.new_private_output,
            original_sha256=a.original_sha256,
            surrogate_simple=a.surrogate_simple, javac=a.javac)
        print(json.dumps(result, sort_keys=True))
    except (OriginalFourthEnumSourceError, OSError, ValueError) as exc:
        p.error("PRIVATE_V309_FOURTH_ENUM_SOURCE_RECOVERY_NOT_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
