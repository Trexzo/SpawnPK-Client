"""R52: exact original JVM enum-reference initializer micro-slice.

Research-only: recognizes an immediate getstatic nested enum constant followed
by a putstatic of one original owner static-final enum field. This is a
bytecode *source form*, not Java source, classfile or runtime equivalence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, BadZipFile

from .boolean_join_witness import _edges
from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _clinit, _digest, _fields, _instructions,
)


class EnumFinalSourceError(ValueError):
    """Cannot accept an exact static-final enum-reference source form."""


_PIN = re.compile(r"[0-9a-fA-F]{64}\Z")
_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")


def _need(ok: bool, reason: str) -> None:
    if not ok:
        raise EnumFinalSourceError(reason)


def _valid_entry(entry: str) -> bool:
    return (type(entry) is str and entry.endswith(".class")
            and not entry.startswith("/") and "\\" not in entry
            and all(part not in ("", ".", "..") and ":" not in part
                    for part in entry.split("/")))


def _exact_class_entries(jar: Path, entries: list[str]) -> None:
    with ZipFile(jar) as archive:
        filenames = archive.namelist()
        for entry in entries:
            _need(filenames.count(entry) == 1,
                  "MISSING_OR_DUPLICATE_CLASSFILE_ENTRY")


def _source_field(row: dict) -> str:
    name = row.get("name")
    _need(type(name) is str and _IDENTIFIER.fullmatch(name) is not None,
          "FIELD_NAME_NOT_JAVA_REPRESENTABLE")
    return name


def plan_exact_enum_reference(
    owner_class: dict, enum_profiles: dict[str, dict]
) -> dict:
    """Review all enum-typed static final owner fields, never guess a source."""
    owner = owner_class.get("internal_name")
    _need(type(owner) is str and bool(owner), "INVALID_ORIGINAL_OWNER")
    originals = _fields(owner_class)
    targets = {
        key: f for key, f in originals.items()
        if (f["access"] & 0x0018) == 0x0018
        and f["constant_value"] is None
        and key[1].startswith("L" + owner + "$")
        and key[1].endswith(";")
        and "/" not in key[1][len("L" + owner + "$"):-1]
    }
    _need(bool(targets), "NO_ORIGINAL_NESTED_ENUM_FINAL_REFERENCE")
    init = _clinit(owner_class, required=True)
    rows = _instructions(init)
    offsets = {row["offset"]: i for i, row in enumerate(rows)}
    branches = _edges(rows)
    incoming = {target for _, target in branches}
    handlers = init.get("exception_handlers")
    _need(isinstance(handlers, list), "EXCEPTION_TABLE_MISSING")
    declarations = {}
    for (name, descriptor), field in targets.items():
        nested = descriptor[1:-1]
        profile = enum_profiles.get(nested)
        _need(isinstance(profile, dict)
              and profile.get("internal_name") == nested
              and profile.get("super_name") == "java/lang/Enum"
              and (profile.get("class_access", 0) & 0x4000) == 0x4000,
              "NESTED_SOURCE_TYPE_NOT_PROVEN_ENUM")
        ef = _fields(profile)
        declarations[(name, descriptor)] = ef
    writes = {k: [] for k in targets}
    for row in rows:
        key = row.get("name"), row.get("descriptor")
        if (row.get("opcode") == "0xb3"
                and row.get("owner") == owner and key in writes):
            writes[key].append(row)
    _need(all(len(value) == 1 for value in writes.values()),
          "STATIC_FINAL_ENUM_STORE_MISSING_OR_DUPLICATED")
    fragments = []
    rejected = 0
    for key, (store,) in writes.items():
        index = offsets[store["offset"]]
        before = rows[index - 1] if index > 0 else None
        nested = key[1][1:-1]
        if (before is None or before.get("opcode") != "0xb2"
                or before.get("owner") != nested
                or before.get("descriptor") != key[1]
                or before["offset"] + before["length"] != store["offset"]):
            rejected += 1
            continue
        enum_field = declarations[key].get(
            (before.get("name"), before.get("descriptor"))
        )
        if (enum_field is None
                or (enum_field.get("access", 0) & 0x4018) != 0x4018):
            rejected += 1
            continue
        if before["offset"] in incoming or store["offset"] in incoming:
            rejected += 1
            continue
        covered = False
        for h in handlers:
            _need(isinstance(h, dict)
                  and all(type(h.get(k)) is int for k in
                          ("start_pc", "end_pc", "handler_pc")),
                  "INVALID_EXCEPTION_HANDLER")
            if (h["handler_pc"] in (before["offset"], store["offset"])
                    or any(h["start_pc"] <= pc < h["end_pc"]
                           for pc in (before["offset"], store["offset"]))):
                covered = True
        if covered:
            rejected += 1
            continue
        target = _source_field({"name": key[0]})
        source = _source_field(before)
        # An actual inner-class/outer-class name collision can require a
        # top-level dollar-named enum source to compile this *expression*.
        qualifier = ".".join(nested.split("/"))
        _need(all(_IDENTIFIER.fullmatch(segment)
                  for segment in qualifier.split(".")),
              "ENUM_TYPE_NAME_NOT_JAVA_REPRESENTABLE")
        fragments.append((store["offset"],
                          f"    {target} = {qualifier}.{source};\n"))
    fragments.sort()
    snippet = (
        "// PRIVATE exact getstatic / putstatic micro-slice; not full <clinit>.\n"
        "// Referenced enum must be independently reconstructed before compile.\n"
        "static {\n" + "".join(fragment for _, fragment in fragments)
        + "}\n"
    )
    return {
        "private_source_fragment": snippet,
        "original_nested_enum_final_fields_examined": len(targets),
        "exact_direct_enum_reference_store_pairs": len(fragments),
        "unrecovered_enum_reference_fields": rejected,
        "nested_enum_source_name_collision_resolved": False,
        "original_nested_enum_source_equivalence_certified": False,
        "original_full_clinit_equivalence_certified": False,
        "compiler_equivalence_certified": False,
        "runtime_equivalence_certified": False,
        "canonical_field_identity_accepted": False,
    }


def build_private_enum_reference_source(
    original_jar: Path, class_entry: str, output_root: Path, *,
    original_sha256: str,
) -> dict:
    original_jar, out = Path(original_jar), Path(output_root)
    _need(not out.exists() and not out.is_symlink(),
          "OUTPUT_ALREADY_EXISTS")
    _need(type(original_sha256) is str and _PIN.fullmatch(original_sha256)
          is not None, "INVALID_ORIGINAL_JAR_PIN")
    _need(original_jar.is_file() and not original_jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(original_jar) == original_sha256.lower(),
          "ORIGINAL_COMPLETE_JAR_SHA256_MISMATCH")
    _need(_valid_entry(class_entry), "INVALID_OWNER_CLASS_ENTRY")
    try:
        _exact_class_entries(original_jar, [class_entry])
        owner = profile_jar_class(original_jar, class_entry)
        name = owner["internal_name"]
        fields = _fields(owner)
        referenced = {
            d[1:-1] for (_, d), field in fields.items()
            if (field["access"] & 0x0018) == 0x0018
            and d.startswith("L" + name + "$") and d.endswith(";")
            and field["constant_value"] is None
        }
        _need(bool(referenced), "NO_ORIGINAL_NESTED_ENUM_FINAL_REFERENCE")
        entries = [name + ".class" for name in sorted(referenced)]
        _exact_class_entries(original_jar, entries)
        enum_profiles = {
            name: profile_jar_class(original_jar, name + ".class")
            for name in referenced
        }
        proof = plan_exact_enum_reference(owner, enum_profiles)
    except (BadZipFile, BytecodeProfileError, ScalarInitializerRecoveryError,
            KeyError, OSError, IndexError):
        raise EnumFinalSourceError("ORIGINAL_CLASSFILE_UNEVALUABLE") from None
    _need(_digest(original_jar) == original_sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_REPLAY")
    snippet = proof.pop("private_source_fragment")
    report = {
        "schema_version": 1,
        "kind": "original_v309_direct_enum_final_reference_source_form",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "private_fragment_sha256":
            hashlib.sha256(snippet.encode("utf-8")).hexdigest(),
        **proof,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "enum-final-source.private.txt").open(
        "x", encoding="utf-8", newline="\n"
    ) as f:
        f.write(snippet)
    with (out / "enum-final-aggregate.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("class_entry")
    p.add_argument("output_root", type=Path)
    p.add_argument("--original-sha256", required=True)
    args = p.parse_args(argv)
    try:
        print(json.dumps(build_private_enum_reference_source(
            args.original_jar, args.class_entry, args.output_root,
            original_sha256=args.original_sha256,
        ), sort_keys=True))
    except EnumFinalSourceError as exc:
        p.error(str(exc))
    except (OSError, ValueError):
        p.error("ENUM_FINAL_SOURCE_REPLAY_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
