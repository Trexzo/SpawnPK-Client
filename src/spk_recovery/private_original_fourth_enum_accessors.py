"""R99: derive only independently proven v309 fourth-enum synthetic accessors.

Build an explicit PRIVATE obfuscated-accessor -> javac-generated-accessor
mapping by the uniquely accessed private String field and identical 3-op
method body. Does not alter candidate bytecode or relax R95 acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile

from .bytecode_profile import profile_jar_class


class OriginalEnumAccessorError(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise OriginalEnumAccessorError(code)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _private_strings(p):
    data = p.get("fields", [])
    need(isinstance(data, list) and len(data) == 5,
         "EXPECTED_FIVE_ENUM_FIELDS")
    strings = [f for f in data
               if f.get("descriptor") == "Ljava/lang/String;"
               and f.get("access") == 0x0002]
    need(len(strings) == 2 and len({f["name"] for f in strings}) == 2,
         "EXPECTED_TWO_UNIQUE_PRIVATE_STRING_FIELDS")
    return {f["name"]: f for f in strings}


def _accessors(profile):
    owner = profile.get("internal_name")
    need(isinstance(owner, str) and "$" in owner and
         profile.get("class_access") == 0x4031 and
         profile.get("super_name") == "java/lang/Enum" and
         profile.get("classfile_major") == 53,
         "ORIGINAL_OR_CANDIDATE_JAVA9_ENUM_IDENTITY_NOT_PROVEN")
    private = _private_strings(profile)
    methods = profile.get("methods", [])
    need(isinstance(methods, list) and len(methods) == 9 and
         len({(m.get("name"), m.get("descriptor")) for m in methods}) == 9,
         "EXPECTED_NINE_UNIQUE_ENUM_METHODS")
    signature = "(L" + owner + ";)Ljava/lang/String;"
    synthetic = [m for m in methods
                 if m.get("access") == 0x1008
                 and m.get("descriptor") == signature]
    need(len(synthetic) == 2, "EXPECTED_TWO_SYNTHETIC_ENUM_ACCESSORS")
    by_field = {}
    for method in synthetic:
        rows = method.get("instructions")
        need(isinstance(rows, list) and len(rows) == 3 and
             [x.get("opcode") for x in rows] == ["0x2a", "0xb4", "0xb0"],
             "SYNTHETIC_ACCESSOR_THREE_OPCODE_PATTERN_NOT_EXACT")
        fld = rows[1]
        name = fld.get("name")
        need(fld.get("owner") == owner and
             fld.get("descriptor") == "Ljava/lang/String;" and
             name in private and name not in by_field and
             isinstance(method.get("name"), str) and method["name"],
             "SYNTHETIC_ACCESSOR_PRIVATE_STRING_FIELD_NOT_UNIQUE")
        need(method.get("exception_handlers") in (None, []) and
             method.get("max_stack") == 1 and
             method.get("max_locals") == 1,
             "SYNTHETIC_ACCESSOR_FRAME_OR_HANDLERS_DIFFER")
        by_field[name] = method
    need(set(by_field) == set(private),
         "BOTH_PRIVATE_STRING_FIELDS_NOT_COVERED")
    return by_field


def derive_private_fourth_enum_accessor_aliases(original, candidate):
    old = _accessors(original)
    new = _accessors(candidate)
    need(set(old) == set(new),
         "PRIVATE_STRING_FIELD_IDENTITIES_NOT_RECONSTRUCTED_EXACTLY")
    mappings = []
    for field in sorted(old):
        a = old[field]
        b = new[field]
        need(a["descriptor"].replace(
                 original["internal_name"], "@enum"
             ) == b["descriptor"].replace(
                 candidate["internal_name"], "@enum"
             ), "SYNTHETIC_ACCESSOR_DESCRIPTOR_MISMATCH")
        mappings.append({
            "private_field_identity": field,
            "original_method_name": a["name"],
            "candidate_method_name": b["name"],
            "original_descriptor": a["descriptor"],
            "candidate_descriptor": b["descriptor"],
        })
    need(len({a["original_method_name"] for a in mappings}) == 2
         and len({a["candidate_method_name"] for a in mappings}) == 2,
         "SYNTHETIC_ACCESSOR_NAMES_NOT_ONE_TO_ONE")
    return {
        "private_accessor_aliases": mappings,
        "original_synthetic_accessor_count": 2,
        "candidate_synthetic_accessor_count": 2,
        "original_synthetic_accessor_jvm_instructions_compared": 6,
        "exact_private_field_source_identity_required": True,
        "original_synthetic_accessor_pattern_verified": True,
        "candidate_javac9_accessor_pattern_verified": True,
        "R95_method_parity_passed_by_this_tool": False,
        "original_outer_owner_method_parity_proven": False,
        "original_client_runtime_equivalence_proven": False,
    }


def replay_private_fourth_enum_accessors(
    original_jar, candidate_jar, original_entry, surrogate_entry,
    output, *, original_sha256, candidate_sha256,
):
    original_jar, candidate_jar, output = map(
        Path, (original_jar, candidate_jar, output))
    need(not output.exists() and not output.is_symlink() and
         output.parent.is_dir() and not output.parent.is_symlink(),
         "PRIVATE_OUTPUT_MUST_BE_NEW")
    for p, pin in ((original_jar, original_sha256),
                   (candidate_jar, candidate_sha256)):
        need(p.is_file() and not p.is_symlink()
             and isinstance(pin, str) and
             re.fullmatch(r"[a-fA-F0-9]{64}", pin) and
             digest(p) == pin.lower(),
             "EXACT_COMPLETE_JAR_SHA256_MISMATCH")
    need(original_jar.resolve() != candidate_jar.resolve(),
         "ORIGINAL_AND_CANDIDATE_MUST_BE_SEPARATE")
    for entry in (original_entry, surrogate_entry):
        need(isinstance(entry, str) and entry.endswith(".class")
             and not entry.startswith("/") and "\\" not in entry
             and all(x not in ("", ".", "..") for x in entry.split("/")),
             "INVALID_ENUM_CLASS_ENTRY")
    prefix = original_entry[:-6].rsplit("$", 1)[0]
    outer_simple = prefix.rsplit("/", 1)[-1]
    need(original_entry == prefix + "$" + outer_simple + ".class" and
         surrogate_entry.startswith(prefix + "$") and
         surrogate_entry != original_entry,
         "REAL_ORIGINAL_NESTED_COLLISION_AND_SURROGATE_REQUIRED")
    with ZipFile(original_jar) as a, ZipFile(candidate_jar) as b:
        need(a.namelist().count(original_entry) == 1
             and b.namelist().count(surrogate_entry) == 1,
             "ORIGINAL_OR_SURROGATE_ENUM_CLASSFILE_MISSING")
    original = profile_jar_class(original_jar, original_entry)
    candidate = profile_jar_class(candidate_jar, surrogate_entry)
    proof = derive_private_fourth_enum_accessor_aliases(original, candidate)
    need(digest(original_jar) == original_sha256.lower()
         and digest(candidate_jar) == candidate_sha256.lower(),
         "ORIGINAL_OR_CANDIDATE_CHANGED_DURING_PROOF")
    private = proof.pop("private_accessor_aliases")
    public = {
        "schema_version": 1,
        "kind": "private_v309_fourth_enum_javac9_synthetic_accessor_pairing",
        "research_only": True,
        "original_sha256": original_sha256.lower(),
        "candidate_sha256": candidate_sha256.lower(),
        **proof,
    }
    # Private original names and descriptors must not enter public GitHub.
    output.mkdir(parents=True, exist_ok=False)
    (output / "synthetic-accessors.private.json").write_text(
        json.dumps(private, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "synthetic-accessors.aggregate.json").write_text(
        json.dumps(public, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return public


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for field in (
        "original_jar", "candidate_jar", "original_enum_entry",
        "surrogate_enum_entry", "new_private_output",
    ):
        p.add_argument(field)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(replay_private_fourth_enum_accessors(
            a.original_jar, a.candidate_jar, a.original_enum_entry,
            a.surrogate_enum_entry, a.new_private_output,
            original_sha256=a.original_sha256,
            candidate_sha256=a.candidate_sha256,
        ), sort_keys=True))
    except OriginalEnumAccessorError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
