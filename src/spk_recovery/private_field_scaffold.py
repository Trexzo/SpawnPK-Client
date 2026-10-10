"""Stage *declarations only* for missing JVM fields in a private Java slice.

This never fills in a field initializer, invents its runtime value, edits a
candidate Java source file, or changes accepted class/field identities.
Detailed private identifiers are written only to the caller's local output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .source_class_method_matrix import (
    ClassMethodMatrixError, build_class_method_matrix,
)


class FieldDeclarationScaffoldError(ValueError):
    """Exact private JVM declaration evidence is incomplete or unsafe."""


_KEYWORDS = frozenset("""
abstract assert boolean break byte case catch char class const continue
default do double else enum extends final finally float for goto if implements
import instanceof int interface long native new package private protected
public return short static strictfp super switch synchronized this throw throws
transient try void volatile while true false null _ module open requires
transitive exports opens to uses provides with var yield record sealed permits
non-sealed when
""".split())
_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")
_PRIMITIVES = {
    "B": "byte", "C": "char", "D": "double", "F": "float",
    "I": "int", "J": "long", "S": "short", "Z": "boolean",
}
# The only JVM field flags with directly representable Java modifiers.
_JAVA_FIELD_FLAGS = 0x0001 | 0x0002 | 0x0004 | 0x0008 | 0x0010 | 0x0040 | 0x0080


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise FieldDeclarationScaffoldError(reason)


def _identifier(name: str) -> bool:
    return (
        type(name) is str and _IDENTIFIER.fullmatch(name) is not None
        and name not in _KEYWORDS
    )


def descriptor_java_type(descriptor: str) -> tuple[str, str]:
    """Return (Java lexical type, kind); no guessing malformed descriptors."""
    _require(type(descriptor) is str and bool(descriptor), "INVALID_FIELD_DESCRIPTOR")
    array_depth = len(descriptor) - len(descriptor.lstrip("["))
    _require(array_depth <= 255, "INVALID_FIELD_ARRAY_DIMENSIONS")
    tail = descriptor[array_depth:]
    if tail in _PRIMITIVES:
        base = _PRIMITIVES[tail]
        kind = "primitive"
    else:
        _require(tail.startswith("L") and tail.endswith(";"),
                 "UNSUPPORTED_FIELD_DESCRIPTOR")
        internal = tail[1:-1]
        parts = internal.split("/")
        _require(bool(parts) and all(_identifier(part) for part in parts),
                 "FIELD_REFERENCE_NAME_CANNOT_BE_SAFELY_EMITTED")
        base = ".".join(parts)
        kind = "reference"
    if array_depth:
        kind = "array"
    return base + "[]" * array_depth, kind


def _modifiers(access: int) -> tuple[str, bool]:
    _require(type(access) is int and 0 <= access <= 65535,
             "INVALID_FIELD_ACCESS")
    _require((access & ~_JAVA_FIELD_FLAGS) == 0,
             "FIELD_ACCESS_HAS_NON_JAVA_FLAGS")
    visibility = [bit for bit in (0x0001, 0x0002, 0x0004) if access & bit]
    _require(len(visibility) <= 1, "FIELD_VISIBILITY_CONFLICT")
    _require(not (access & 0x0010 and access & 0x0040),
             "FINAL_AND_VOLATILE_CONFLICT")
    words = []
    for bit, label in (
        (0x0001, "public"), (0x0002, "private"),
        (0x0004, "protected"), (0x0008, "static"),
        (0x0010, "final"), (0x0040, "volatile"),
        (0x0080, "transient"),
    ):
        if access & bit:
            words.append(label)
    return " ".join(words), bool(access & 0x0010)


def _fields(profile: dict) -> dict[tuple[str, str], dict[str, Any]]:
    rows = profile.get("fields")
    _require(isinstance(rows, list), "FIELD_INVENTORY_MISSING")
    output = {}
    names = set()
    for row in rows:
        _require(isinstance(row, dict), "INVALID_FIELD_METADATA")
        name, descriptor = row.get("name"), row.get("descriptor")
        _require(_identifier(name), "NON_JAVA_FIELD_IDENTIFIER")
        _require(name not in names, "DUPLICATE_JAVA_FIELD_NAME")
        descriptor_java_type(descriptor)
        _modifiers(row.get("access"))
        _require("signature" in row and "constant_value" in row,
                 "FIELD_ATTRIBUTE_EVIDENCE_MISSING")
        key = name, descriptor
        _require(key not in output, "DUPLICATE_JVM_FIELD_DECLARATION")
        output[key] = row
        names.add(name)
    return output


def plan_missing_field_declarations(original: dict, candidate: dict,
                                    matrix: dict) -> dict[str, Any]:
    """Build source fragment in memory; callers keep it private, not GitHub."""
    _require(
        original.get("internal_name") == candidate.get("internal_name")
        and type(original.get("internal_name")) is str,
        "CLASS_OWNER_DOES_NOT_MATCH",
    )
    _require(matrix.get("research_only") is True
             and matrix.get("source_equivalence_certified") is False
             and matrix.get("canonical_identity_accepted") is False,
             "STRICT_MATRIX_AUTHORITY_UNEXPECTED")
    orig, cand = _fields(original), _fields(candidate)
    candidate_names = {name for name, _ in cand}
    missing = [(key, row) for key, row in orig.items() if key not in cand]
    changed = [
        key for key in orig.keys() & cand.keys()
        if any(orig[key].get(x) != cand[key].get(x)
               for x in ("access", "signature", "constant_value"))
    ]
    _require(
        len(missing) == matrix["field_counts"]["missing_field"]
        and len(changed) == matrix["field_counts"]["shared_metadata_difference"]
        and len(orig) == matrix["original_declared_field_count"]
        and len(cand) == matrix["candidate_declared_field_count"],
        "FIELD_MATRIX_COUNTS_DISAGREE",
    )
    _require(
        not any(name in candidate_names for (name, _), _ in missing),
        "JAVA_FIELD_NAME_COLLISION_WITH_DIFFERENT_DESCRIPTOR",
    )
    declarations = []
    finals = 0
    finals_with_constant_value = 0
    static_fields = 0
    kinds = {"primitive": 0, "array": 0, "reference": 0}
    for (name, descriptor), row in missing:
        # Signature can encode generics that cannot be reproduced by a
        # descriptor-only source declaration. Never erase that evidence.
        _require(row["signature"] is None,
                 "GENERIC_FIELD_SIGNATURE_NEEDS_MANUAL_RECOVERY")
        java_type, kind = descriptor_java_type(descriptor)
        modifiers, is_final = _modifiers(row["access"])
        kinds[kind] += 1
        finals += int(is_final)
        if is_final and row["constant_value"] is not None:
            finals_with_constant_value += 1
        static_fields += int(bool(row["access"] & 0x0008))
        declarations.append(
            ("    " + modifiers + " " if modifiers else "    ")
            + java_type + " " + name + ";"
        )
    intro = (
        "// PRIVATE ORIGINAL-JVM FIELD DECLARATIONS — REVIEW-ONLY FRAGMENT\n"
        "// Do not commit; not a standalone class or a reconstructed initializer.\n"
        "// No default values or source initializer behavior has been inferred.\n"
        "// Especially: unassigned final fields may prevent javac compilation.\n\n"
    )
    body = intro + "\n".join(declarations) + "\n"
    return {
        "snippet": body,
        "original_field_count": len(orig),
        "candidate_field_count": len(cand),
        "declarations_staged": len(declarations),
        "shared_metadata_differences_unmodified": len(changed),
        "final_fields_needing_initializer_review": finals,
        "final_fields_with_exact_constant_value_evidence": finals_with_constant_value,
        "final_fields_without_constant_value_evidence": finals - finals_with_constant_value,
        "static_fields_staged": static_fields,
        "java_type_counts": kinds,
        "source_compilation_certified": False,
        "runtime_field_initialization_recovered": False,
        "canonical_identity_accepted": False,
    }


def _hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def scaffold_missing_fields(
    original_jar: Path, candidate_jar: Path, out_root: Path, *,
    original_sha256: str, candidate_sha256: str, class_entry: str,
) -> dict[str, Any]:
    """Create private fragment and aggregate JSON, exclusively and atomically.

    A stale/invalid original or candidate class cannot be used as a field
    source. Detailed fragment output must never be uploaded to public CI.
    """
    original_jar, candidate_jar, out_root = map(
        Path, (original_jar, candidate_jar, out_root)
    )
    _require(original_jar != candidate_jar, "DISTINCT_INPUT_JARS_REQUIRED")
    _require(not out_root.exists() and not out_root.is_symlink(),
             "OUTPUT_ROOT_ALREADY_EXISTS")
    _require(
        original_jar.is_file() and candidate_jar.is_file()
        and not original_jar.is_symlink() and not candidate_jar.is_symlink(),
        "ORIGINAL_OR_CANDIDATE_JAR_MISSING_OR_SYMLINK",
    )
    try:
        matrix = build_class_method_matrix(
            original_jar, candidate_jar,
            original_sha256=original_sha256,
            candidate_sha256=candidate_sha256,
            class_entry=class_entry,
        )
        old = profile_jar_class(original_jar, class_entry)
        rebuilt = profile_jar_class(candidate_jar, class_entry)
        plan = plan_missing_field_declarations(old, rebuilt, matrix)
    except (ClassMethodMatrixError, BytecodeProfileError,
            OSError, KeyError, IndexError, ValueError):
        raise FieldDeclarationScaffoldError("PRIVATE_FIELD_EVIDENCE_UNEVALUABLE") from None
    _require(
        _hash(original_jar) == original_sha256.lower()
        and _hash(candidate_jar) == candidate_sha256.lower(),
        "JAR_INPUT_CHANGED_DURING_REPLAY",
    )
    manifest = {
        "schema_version": 1,
        "kind": "private_missing_jvm_field_declarations",
        "research_only": True,
        "original_jar_sha256": original_sha256.lower(),
        "candidate_jar_sha256": candidate_sha256.lower(),
        "class_method_matrix_report_id": matrix["report_id"],
        "snippet_sha256": hashlib.sha256(plan["snippet"].encode("utf-8")).hexdigest(),
        **{key: value for key, value in plan.items() if key != "snippet"},
    }
    out_root.mkdir(parents=True, exist_ok=False)
    # A .txt fragment is deliberately not discovered by javac -sourcepath.
    with (out_root / "missing-fields.fragment.txt").open(
        "x", encoding="utf-8", newline="\n"
    ) as file:
        file.write(plan["snippet"])
    with (out_root / "private-field-scaffold-manifest.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as file:
        json.dump(manifest, file, indent=2, sort_keys=True)
        file.write("\n")
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
        report = scaffold_missing_fields(
            args.original_jar, args.candidate_jar, args.output_root,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
            class_entry=args.class_entry,
        )
        # Do not print Java source, obfuscated names, or local file paths.
        print(json.dumps(report, indent=2, sort_keys=True))
    except FieldDeclarationScaffoldError as exc:
        parser.error(str(exc))
    except (OSError, ValueError):
        parser.error("PRIVATE_FIELD_SCAFFOLD_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
