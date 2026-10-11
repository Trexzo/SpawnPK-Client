"""Cross-build JVM nested-enum dependency closure for private Java recovery.

Measure only original *missing* field references to nested enum classfiles.
Require SHA-pinned complete old/current/candidate JARs. Original class
names, field names, source text and nested bytes never leave private inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from zipfile import BadZipFile, ZipFile

from .bytecode_profile import BytecodeProfileError, profile_class_field_accesses


class NestedEnumClosureError(ValueError):
    """Nested original-class source identity cannot be safely inferred."""


def _need(condition: bool, reason: str) -> None:
    if not condition:
        raise NestedEnumClosureError(reason)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _pin(path: Path, sha256: str) -> None:
    _need(type(sha256) is str
          and re.fullmatch(r"[a-fA-F0-9]{64}", sha256) is not None,
          "INVALID_WHOLE_JAR_SHA256")
    _need(path.is_file() and not path.is_symlink(), "JAR_MISSING_OR_SYMLINK")
    _need(_hash_file(path) == sha256.lower(), "WHOLE_JAR_SHA256_MISMATCH")


def _read_class(archive: ZipFile, entry: str) -> bytes:
    infos = [i for i in archive.infolist() if i.filename == entry]
    _need(len(infos) == 1 and not infos[0].is_dir(),
          "EXACT_NESTED_CLASS_ENTRY_MISSING_OR_DUPLICATE")
    content = archive.read(infos[0])
    _need(content[:4] == b"\xca\xfe\xba\xbe",
          "CLASSFILE_MAGIC_MISMATCH")
    return content


def analyze_nested_enum_closure(
    original: dict, candidate: dict, *,
    original_jar: ZipFile, previous_jar: ZipFile,
    original_sha256: str,
) -> dict[str, Any]:
    owner = original.get("internal_name")
    _need(type(owner) is str and bool(owner)
          and owner == candidate.get("internal_name"),
          "NO_ACCEPTED_CROSS_CLASS_ALIAS")
    fields = original.get("fields")
    candidate_fields = candidate.get("fields")
    _need(isinstance(fields, list) and isinstance(candidate_fields, list),
          "FIELD_INVENTORY_MISSING")
    def declared(rows: list) -> dict:
        result = {}
        for row in rows:
            _need(isinstance(row, dict), "INVALID_FIELD_INVENTORY")
            key = row.get("name"), row.get("descriptor")
            _need(all(isinstance(x, str) and bool(x) for x in key)
                  and key not in result, "DUPLICATE_JVM_FIELD")
            result[key] = row
        return result

    present = declared(candidate_fields)
    original_fields = declared(fields)
    missing = [key for key in original_fields if key not in present]
    nested_prefix = "L" + owner + "$"
    dependent = [(n, desc) for (n, desc) in missing
                 if desc.startswith(nested_prefix) and desc.endswith(";")
                 and "/" not in desc[len(nested_prefix):-1]]
    _need(len(dependent) <= len(missing), "NESTED_FIELD_COUNT_INVALID")
    targets: dict[str, list] = {}
    for name, descriptor in dependent:
        inner = descriptor[1:-1]
        _need(inner.startswith(owner + "$"), "NESTED_OWNER_INVALID")
        targets.setdefault(inner, []).append((name, descriptor))
    class_rows = []
    owner_leaf = owner.rsplit("/", 1)[-1]
    for inner in sorted(targets):
        path = inner + ".class"
        original_bytes = _read_class(original_jar, path)
        previous_bytes = _read_class(previous_jar, path)
        profile = profile_class_field_accesses(original_bytes)
        _need(profile.get("internal_name") == inner,
              "NESTED_CLASS_OWNER_MISMATCH")
        _need(
            profile.get("super_name") == "java/lang/Enum"
            and type(profile.get("class_access")) is int
            and bool(profile["class_access"] & 0x4000),
            "NESTED_TYPE_NOT_JVM_ENUM",
        )
        class_id = _sha(json.dumps(
            [original_sha256.lower(), inner],
            separators=(",", ":"),
        ).encode("utf-8"))[:20].upper()
        class_rows.append({
            "nested_class_id": "NESTED_" + class_id,
            "original_exact_class_sha256": _sha(original_bytes),
            "previous_version_class_byte_identical":
                original_bytes == previous_bytes,
            "referencing_missing_original_field_count": len(targets[inner]),
            "nested_simple_name_collides_with_enclosing":
                inner.rsplit("$", 1)[-1] == owner_leaf,
            "jvm_enum_flag_present": True,
            "source_java_enum_recovered": False,
            "canonical_owner_identity_accepted": False,
        })
    _need(sum(x["referencing_missing_original_field_count"]
              for x in class_rows) == len(dependent),
          "NESTED_FIELD_DEPENDENCY_TOTAL_DRIFT")
    return {
        "schema_version": 1,
        "kind": "private_original_nested_enum_source_dependency_closure",
        "research_only": True,
        "original_missing_field_declarations": len(missing),
        "missing_nested_enum_typed_field_declarations": len(dependent),
        "unique_nested_jvm_enum_types": len(class_rows),
        "byte_identical_nested_enum_type_count": sum(
            r["previous_version_class_byte_identical"] for r in class_rows
        ),
        "nested_java_source_name_collision_count": sum(
            r["nested_simple_name_collides_with_enclosing"] for r in class_rows
        ),
        "nested_enum_types": class_rows,
        "source_equivalence_certified": False,
        "source_code_generated": False,
        "original_nested_class_bytes_published": False,
        "canonical_identity_accepted": False,
    }


def verify_nested_enum_closure(
    original_jar: Path, previous_jar: Path, candidate_jar: Path, *,
    original_sha256: str, previous_sha256: str, candidate_sha256: str,
    class_entry: str,
) -> dict[str, Any]:
    paths = [Path(original_jar), Path(previous_jar), Path(candidate_jar)]
    pins = [original_sha256, previous_sha256, candidate_sha256]
    for path, pin in zip(paths, pins):
        _pin(path, pin)
    _need(type(class_entry) is str and class_entry.endswith(".class")
          and not class_entry.startswith("/") and "\\" not in class_entry
          and all(part not in ("", ".", "..") and ":" not in part
                  for part in class_entry.split("/")),
          "INVALID_EXACT_CLASS_ENTRY")
    try:
        with ZipFile(paths[0]) as original, ZipFile(paths[1]) as previous, ZipFile(paths[2]) as candidate:
            old_profile = profile_class_field_accesses(
                _read_class(original, class_entry)
            )
            source_profile = profile_class_field_accesses(
                _read_class(candidate, class_entry)
            )
            result = analyze_nested_enum_closure(
                old_profile, source_profile,
                original_jar=original, previous_jar=previous,
                original_sha256=original_sha256,
            )
    except (BadZipFile, BytecodeProfileError, OSError, ValueError,
            KeyError, IndexError):
        raise NestedEnumClosureError(
            "NESTED_ENUM_EVIDENCE_UNEVALUABLE"
        ) from None
    for path, pin in zip(paths, pins):
        _need(_hash_file(path) == pin.lower(), "JAR_INPUT_CHANGED_DURING_REPLAY")
    report = {
        "original_jar_sha256": original_sha256.lower(),
        "previous_jar_sha256": previous_sha256.lower(),
        "candidate_jar_sha256": candidate_sha256.lower(),
        **result,
    }
    fingerprint = _sha(json.dumps(
        report, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8"))[:20].upper()
    return {"report_id": "NESTEDCLOSURE_" + fingerprint, **report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("previous_jar", type=Path)
    parser.add_argument("candidate_jar", type=Path)
    parser.add_argument("class_entry")
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--previous-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = verify_nested_enum_closure(
            args.original_jar, args.previous_jar, args.candidate_jar,
            original_sha256=args.original_sha256,
            previous_sha256=args.previous_sha256,
            candidate_sha256=args.candidate_sha256,
            class_entry=args.class_entry,
        )
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, sort_keys=True, indent=2)
                stream.write("\n")
        print(json.dumps({
            "report_id": report["report_id"],
            "missing_nested_enum_typed_field_declarations":
                report["missing_nested_enum_typed_field_declarations"],
            "unique_nested_jvm_enum_types":
                report["unique_nested_jvm_enum_types"],
            "byte_identical_nested_enum_type_count":
                report["byte_identical_nested_enum_type_count"],
            "nested_java_source_name_collision_count":
                report["nested_java_source_name_collision_count"],
            "source_equivalence_certified": False,
        }, sort_keys=True))
        return 0
    except NestedEnumClosureError as exc:
        parser.error(str(exc))
    except (OSError, ValueError):
        parser.error("NESTED_ENUM_CLOSURE_FAILED")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
