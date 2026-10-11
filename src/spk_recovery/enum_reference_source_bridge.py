"""Private source-only bridge for missing mutable fields of nested JVM enums.

Emit declaration fragments and clearly marked *empty* enum type shells.
These are compilation aids, NOT recovered enum constants or behavior.
The original and candidate JARs must be independently SHA-256 pinned.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from zipfile import BadZipFile, ZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .source_class_method_matrix import (
    ClassMethodMatrixError, build_class_method_matrix,
)


class EnumReferenceScaffoldError(ValueError):
    """Required class, field or enum-type source evidence is incomplete."""


_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")
_KEYWORDS = frozenset(
    "abstract assert boolean break byte case catch char class const continue "
    "default do double else enum extends final finally float for goto if "
    "implements import instanceof int interface long native new package "
    "private protected public return short static strictfp super switch "
    "synchronized this throw throws transient try void volatile while true "
    "false null _ var yield record sealed permits when".split()
)
_SHA = re.compile(r"[0-9a-fA-F]{64}\Z")


def _need(value: bool, reason: str) -> None:
    if not value:
        raise EnumReferenceScaffoldError(reason)


def _identifier(value: Any) -> bool:
    return (
        type(value) is str and _IDENTIFIER.fullmatch(value) is not None
        and value not in _KEYWORDS
    )


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _fields(profile: dict) -> dict[tuple[str, str], dict]:
    fields = profile.get("fields")
    _need(isinstance(fields, list), "FIELD_INVENTORY_MISSING")
    result: dict[tuple[str, str], dict] = {}
    names = set()
    for field in fields:
        _need(isinstance(field, dict), "FIELD_METADATA_INVALID")
        key = (field.get("name"), field.get("descriptor"))
        _need(
            all(type(x) is str and x for x in key)
            and key not in result and key[0] not in names,
            "DUPLICATE_OR_INVALID_FIELD",
        )
        _need(
            type(field.get("access")) is int
            and "constant_value" in field and "signature" in field,
            "INCOMPLETE_FIELD_METADATA",
        )
        result[key] = field
        names.add(key[0])
    return result


def _enum_binary_name(owner: str, descriptor: str) -> tuple[str, str] | None:
    if not (type(descriptor) is str and descriptor.startswith("L")
            and descriptor.endswith(";")):
        return None
    name = descriptor[1:-1]
    prefix = owner + "$"
    if not name.startswith(prefix):
        return None
    simple = name[len(prefix):]
    if not _identifier(simple) or "/" in simple or "$" in simple:
        return None
    return name, simple


def plan_nested_enum_field_references(
    original: dict, candidate: dict,
    original_enum_profiles: dict[str, dict], *,
    expected_missing_fields: int,
) -> dict[str, Any]:
    """Return private fragment texts and public aggregate-only measurements."""
    owner = original.get("internal_name")
    _need(type(owner) is str and owner and owner == candidate.get("internal_name"),
          "OWNER_ALIAS_NOT_ACCEPTED")
    _need(
        type(expected_missing_fields) is int and expected_missing_fields >= 0,
        "INVALID_MATRIX_FIELD_GAP",
    )
    a, b = _fields(original), _fields(candidate)
    missing = [(k, v) for k, v in a.items() if k not in b]
    _need(len(missing) == expected_missing_fields, "FIELD_GAP_MATRIX_DISAGREES")
    selected = []
    type_profiles: dict[str, dict] = {}
    skipped_final = 0
    for (name, descriptor), field in missing:
        parsed = _enum_binary_name(owner, descriptor)
        if parsed is None:
            continue
        full_name, simple = parsed
        if field["access"] == 0x0019:
            skipped_final += 1
            continue
        # Refuse static-final, modified, generic and unresolved reference
        # fields. Only ordinary mutable public/static declaration shapes.
        _need(
            field["access"] == 0x0009
            and field["signature"] is None
            and field["constant_value"] is None,
            "ENUM_REFERENCE_SOURCE_FLAGS_UNSUPPORTED",
        )
        _need(_identifier(name), "ENUM_FIELD_JAVA_IDENTIFIER_UNSAFE")
        _need(not any(n == name for n, _ in b), "CANDIDATE_JAVA_FIELD_NAME_CONFLICT")
        enum = original_enum_profiles.get(full_name)
        _need(isinstance(enum, dict), "ORIGINAL_ENUM_CLASS_PROFILE_MISSING")
        _need(
            enum.get("internal_name") == full_name
            and enum.get("super_name") == "java/lang/Enum"
            and type(enum.get("class_access")) is int
            and enum["class_access"] & 0x4000 == 0x4000
            and enum["class_access"] & 0x0010 == 0x0010,
            "ORIGINAL_DEPENDENCY_IS_NOT_EXACT_ENUM_CLASS",
        )
        type_profiles[full_name] = enum
        selected.append((name, simple))
    selected.sort()
    _need(len(selected) == len(set(n for n, _ in selected)),
          "DUPLICATE_JAVA_FIELD_DECLARATIONS")
    enum_names = sorted(
        (full_name[len(owner)+1:] for full_name in type_profiles)
    )
    # Java nested enum shells are compile-only placeholders. They declare
    # *no original enum constants*, constructors, fields or method bodies.
    # Never silently promote their classfiles to recovered source.
    field_text = (
        "// PRIVATE SOURCE FRAGMENT: exact JVM field type declarations ONLY.\n"
        "// Requires separately reviewed enum source; not runtime-equivalent.\n"
        + "".join(f"    public static {simple} {name};\n"
                  for name, simple in selected)
    )
    shells = (
        "// PRIVATE PLACEHOLDERS ONLY: NOT recovered original enum source.\n"
        "// Used solely to exercise javac type-closure for field descriptors.\n"
        "// Their constants, methods, class initialization and behavior are UNKNOWN.\n"
        + "".join(f"    public enum {simple} {{ ; }}\n"
                  for simple in enum_names)
    )
    return {
        "private_field_fragment": field_text,
        "private_enum_shell_fragment": shells,
        "selected_field_declaration_count": len(selected),
        "distinct_type_shell_count": len(enum_names),
        "unresolved_missing_fields_outside_this_scope":
            len(missing) - len(selected),
        "original_final_nested_enum_fields_excluded": skipped_final,
        "enum_constant_values_reconstructed": 0,
        "enum_method_bodies_reconstructed": 0,
        "original_enum_source_equivalence_certified": False,
        "initializer_values_reconstructed": False,
        "owner_source_equivalence_certified": False,
        "canonical_field_or_class_identity_accepted": False,
    }


def build_enum_reference_scaffold(
    original_jar: Path, candidate_jar: Path, out_root: Path, *,
    original_sha256: str, candidate_sha256: str, class_entry: str,
) -> dict[str, Any]:
    original_jar, candidate_jar, out_root = map(
        Path, (original_jar, candidate_jar, out_root)
    )
    _need(not out_root.exists() and not out_root.is_symlink(),
          "OUTPUT_ALREADY_EXISTS")
    _need(original_jar != candidate_jar, "DISTINCT_JARS_REQUIRED")
    for path, pin in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        _need(
            type(pin) is str and _SHA.fullmatch(pin) is not None,
            "INVALID_WHOLE_JAR_SHA256",
        )
        _need(path.is_file() and not path.is_symlink(),
              "ORIGINAL_OR_CANDIDATE_JAR_MISSING_OR_SYMLINK")
        _need(_digest(path) == pin.lower(), "WHOLE_JAR_SHA256_MISMATCH")
    _need(
        type(class_entry) is str and class_entry.endswith(".class")
        and not class_entry.startswith("/") and "\\" not in class_entry
        and all(part not in ("", ".", "..") and ":" not in part
                for part in class_entry.split("/")),
        "INVALID_CLASS_ENTRY",
    )
    try:
        matrix = build_class_method_matrix(
            original_jar, candidate_jar,
            original_sha256=original_sha256,
            candidate_sha256=candidate_sha256,
            class_entry=class_entry,
        )
        _need(
            matrix.get("research_only") is True
            and matrix.get("source_equivalence_certified") is False
            and matrix.get("canonical_identity_accepted") is False,
            "MATRIX_UNEXPECTED_AUTHORITY",
        )
        original = profile_jar_class(original_jar, class_entry)
        candidate = profile_jar_class(candidate_jar, class_entry)
        owner = original["internal_name"]
        refs = set()
        for field in original["fields"]:
            match = _enum_binary_name(owner, field.get("descriptor"))
            if match is not None and field.get("access") == 0x0009:
                refs.add(match[0])
        enum_profiles = {}
        with ZipFile(original_jar) as archive:
            names = [info.filename for info in archive.infolist()
                     if not info.is_dir()]
            for name in sorted(refs):
                entry = name + ".class"
                _need(names.count(entry) == 1,
                      "DEPENDENCY_ENUM_CLASS_MISSING_OR_DUPLICATE")
                enum_profiles[name] = profile_jar_class(original_jar, entry)
        plan = plan_nested_enum_field_references(
            original, candidate, enum_profiles,
            expected_missing_fields=matrix["field_counts"]["missing_field"],
        )
    except (
        ClassMethodMatrixError, BytecodeProfileError, BadZipFile, OSError,
        KeyError, IndexError,
    ):
        raise EnumReferenceScaffoldError("ENUM_SOURCE_EVIDENCE_UNEVALUABLE") from None
    for path, pin in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        _need(_digest(path) == pin.lower(), "JAR_CHANGED_DURING_SOURCE_PROOF")

    field_text = plan.pop("private_field_fragment")
    enum_text = plan.pop("private_enum_shell_fragment")
    manifest = {
        "schema_version": 1,
        "kind": "private_nested_enum_field_descriptor_source_bridge",
        "research_only": True,
        "original_jar_sha256": original_sha256.lower(),
        "candidate_jar_sha256": candidate_sha256.lower(),
        "strict_matrix_report_id": matrix["report_id"],
        "private_field_fragment_sha256": hashlib.sha256(
            field_text.encode("utf-8")).hexdigest(),
        "private_enum_shell_fragment_sha256": hashlib.sha256(
            enum_text.encode("utf-8")).hexdigest(),
        **plan,
    }
    out_root.mkdir(parents=True, exist_ok=False)
    for name, content in (
        ("owner-enum-reference-fields.fragment.txt", field_text),
        ("unverified-enum-type-shells.fragment.txt", enum_text),
    ):
        with (out_root / name).open("x", encoding="utf-8", newline="\n") as f:
            f.write(content)
    with (out_root / "aggregate-private-source-bridge.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("candidate_jar", type=Path)
    parser.add_argument("class_entry")
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        report = build_enum_reference_scaffold(
            args.original_jar, args.candidate_jar, args.output_root,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
            class_entry=args.class_entry,
        )
        print(json.dumps(report, sort_keys=True))
    except EnumReferenceScaffoldError as exc:
        parser.error(str(exc))
    except (OSError, ValueError):
        parser.error("ENUM_REFERENCE_SOURCE_BRIDGE_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
