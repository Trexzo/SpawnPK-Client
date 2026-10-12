"""R105: exact original synthetic-accessor member-name rebind then R104/R95.

Map two Java9-generated accessor methods to the original obfuscated JVM method
names by the *exact private String field* each getter reads. Rewrite only:
  1. the two candidate fourth-enum method_info.name_index references;
  2. CONSTANT_Methodref NameAndType indices targeting those methods.
Append new CP Utf8/NameAndType entries without mutating shared old strings
or any method Code bytes. Then R104 performs the post-javac type/metadata
transforms and REQUIRES R95 exact four-enum acceptance on the same JAR.
Private client JAR/source identifiers must never be published.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZipFile

from .bytecode_profile import (
    BytecodeProfileError, _Reader, _constant_pool, _utf8, _class_name,
    profile_jar_class,
)
from .private_original_fourth_enum_accessors import (
    OriginalEnumAccessorError, _accessors, digest,
)
from .private_all_four_enum_postjavac_acceptance_r104 import (
    AllFourPrivateEnumAcceptanceError, assemble_private_four_enum_candidate,
)


class SyntheticAccessorMemberRebindError(ValueError):
    pass


def need(ok, error):
    if not ok:
        raise SyntheticAccessorMemberRebindError(error)


def _u2(value):
    need(type(value) is int and 0 <= value <= 65535,
         "INVALID_JVM_CP_U2")
    return value.to_bytes(2, "big")


def _cp_layout(classfile):
    reader = _Reader(classfile)
    need(reader.u4() == 0xCAFEBABE, "CLASSFILE_MAGIC_INVALID")
    reader.take(4)  # minor and major
    cp = _constant_pool(reader)
    end = reader.offset
    raw = _Reader(classfile)
    raw.take(8)
    n = raw.u2()
    need(n == len(cp), "CP_COUNT_NOT_COHERENT")
    offsets = {}
    i = 1
    while i < n:
        pos = raw.offset
        tag = raw.u1()
        offsets[i] = pos
        if tag == 1:
            raw.take(raw.u2())
        elif tag in (3, 4):
            raw.take(4)
        elif tag in (5, 6):
            raw.take(8)
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            raw.take(2)
        elif tag in (9, 10, 11, 12, 17, 18):
            raw.take(4)
        elif tag == 15:
            raw.take(3)
        else:
            raise SyntheticAccessorMemberRebindError(
                "UNSUPPORTED_JVM_CONSTANT_POOL_TAG")
        i += 1
    need(raw.offset == end, "CP_BYTE_BOUNDARY_DIFFERENCE")
    raw.u2()  # class flags
    this = _class_name(cp, raw.u2())
    raw.u2()  # super
    raw.take(2 * raw.u2())  # interfaces
    for _ in range(raw.u2()):  # fields
        raw.take(6)
        for __ in range(raw.u2()):
            raw.u2()
            raw.take(raw.u4())
    methods = []
    for _ in range(raw.u2()):
        start = raw.offset
        access, name_idx, descriptor_idx = raw.u2(), raw.u2(), raw.u2()
        for __ in range(raw.u2()):
            raw.u2()
            raw.take(raw.u4())
        methods.append({
            "header_offset": start,
            "access": access,
            "name": _utf8(cp, name_idx),
            "descriptor": _utf8(cp, descriptor_idx),
        })
    for _ in range(raw.u2()):
        raw.u2()
        raw.take(raw.u4())
    need(raw.offset == len(classfile), "CLASSFILE_ATTRIBUTE_TAIL_INVALID")
    return cp, offsets, end, methods, this


def rebind_member_references(
    classfile, *, target_owner, name_aliases, rewrite_declarations=False,
):
    """Rewrite only proven accessor method name references; no Code edits."""
    need(type(target_owner) is str and
         re.fullmatch(r"[A-Za-z0-9_$/]+", target_owner)
         and isinstance(name_aliases, dict)
         and len(name_aliases) == 2
         and len(set(name_aliases.values())) == 2
         and all(type(a) is str and type(b) is str
                 and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", a)
                 and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", b)
                 for a, b in name_aliases.items()),
         "ACCESSOR_MEMBER_NAME_ALIASES_NOT_TWO_UNIQUE_SAFE")
    cp, offsets, end, methods, this = _cp_layout(classfile)
    name_index = {cp[i][1]: i for i in range(1, len(cp))
                  if cp[i] is not None and cp[i][0] == 1}
    nt_index = {}
    for i in range(1, len(cp)):
        row = cp[i]
        if row is not None and row[0] == 12:
            nt_index.setdefault((_utf8(cp, row[1]),
                                 _utf8(cp, row[2])), i)
    new_raw = bytearray()
    pool_count = len(cp)

    def utf8(s):
        nonlocal pool_count
        if s in name_index:
            return name_index[s]
        need(s.isascii() and "\x00" not in s and
             pool_count < 65535,
             "CANNOT_APPEND_NEW_METHOD_UTF8")
        encoded = s.encode("ascii")
        index = pool_count
        pool_count += 1
        new_raw.extend(b"\x01" + _u2(len(encoded)) + encoded)
        name_index[s] = index
        return index

    def named_type(name, descriptor):
        nonlocal pool_count
        pair = (name, descriptor)
        if pair in nt_index:
            return nt_index[pair]
        # Allocation order matters: ensure referenced Utf8 entries BEFORE
        # allocating/appending the NameAndType entry itself.
        nidx, didx = utf8(name), utf8(descriptor)
        need(pool_count < 65535, "CANNOT_APPEND_NEW_METHOD_NAMEANDTYPE")
        index = pool_count
        pool_count += 1
        new_raw.extend(b"\x0c" + _u2(nidx) + _u2(didx))
        nt_index[pair] = index
        return index

    oldpool = bytearray(classfile[10:end])
    body = bytearray(classfile[end:])
    decl_changed = 0
    callsite_changed = 0
    expected_descriptor = "(L" + target_owner + ";)Ljava/lang/String;"

    if rewrite_declarations:
        need(this == target_owner, "SYNTHETIC_METHOD_CLASS_OWNER_MISMATCH")
        found = []
        for method in methods:
            if method["access"] != 0x1008 or
               method["descriptor"] != expected_descriptor:
                continue
            if method["name"] not in name_aliases:
                continue
            found.append(method["name"])
            replacement = utf8(name_aliases[method["name"]])
            position = method["header_offset"] + 2 - end
            body[position:position + 2] = _u2(replacement)
            decl_changed += 1
        need(set(found) == set(name_aliases)
             and decl_changed == 2,
             "EXACT_TWO_GENERATED_ACCESSOR_DECLARATIONS_NOT_RENAMED")

    for i, row in enumerate(cp):
        if row is None or row[0] not in (10, 11):
            continue
        owner_ref = _class_name(cp, row[1])
        if owner_ref != target_owner:
            continue
        nt = cp[row[2]]
        need(nt is not None and nt[0] == 12,
             "INVALID_SYNTHETIC_METHOD_NAMETYPE")
        name, descriptor = _utf8(cp, nt[1]), _utf8(cp, nt[2])
        if name not in name_aliases or descriptor != expected_descriptor:
            continue
        replacement = named_type(name_aliases[name], descriptor)
        position = offsets[i] + 3 - 10
        oldpool[position:position + 2] = _u2(replacement)
        callsite_changed += 1

    rewritten = (classfile[:8] + _u2(pool_count) +
                 oldpool + new_raw + body)
    _, _, _, output_methods, output_owner = _cp_layout(rewritten)
    need(output_owner == this and
         len(output_methods) == len(methods) and
         [(m["access"], m["descriptor"]) for m in methods] ==
         [(m["access"], m["descriptor"]) for m in output_methods],
         "REBOUND_METHOD_DECLARATION_SHAPE_CHANGED")
    return rewritten, decl_changed, callsite_changed


def private_accessor_aliases(original_profile, candidate_profile):
    try:
        originals, candidates = (
            _accessors(original_profile),
            _accessors(candidate_profile),
        )
    except (OriginalEnumAccessorError, BytecodeProfileError,
            ValueError, KeyError, IndexError) as exc:
        raise SyntheticAccessorMemberRebindError(
            "R99_ORIGINAL_CANDIDATE_ACCESSOR_SHAPES_NOT_EXACT") from exc
    need(len(originals) == len(candidates) == 2
         and set(originals) == set(candidates),
         "EXACT_ORIGINAL_PRIVATE_STRING_FIELD_IDENTITIES_REQUIRED")
    name_map = {
        candidates[field]["name"]: originals[field]["name"]
        for field in originals
    }
    need(len(name_map) == 2 and len(set(name_map.values())) == 2,
         "ORIGINAL_SYNTHETIC_METHOD_ALIASES_NOT_INJECTIVE")
    return name_map


def assemble_original_accessor_and_r95_candidate(
    original_jar, candidate_jar, owner_entry, surrogate_simple, output,
    *, original_sha256, candidate_sha256,
):
    original_jar, candidate_jar, output = map(
        Path, (original_jar, candidate_jar, output))
    need(output.parent.is_dir() and not output.parent.is_symlink()
         and not output.exists() and not output.is_symlink(),
         "PRIVATE_OUTPUT_MUST_NOT_EXIST")
    need(original_jar.resolve() != candidate_jar.resolve(),
         "ORIGINAL_AND_CANDIDATE_JAR_SHOULD_BE_SEPARATE")
    for path, pin in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        need(path.is_file() and not path.is_symlink()
             and isinstance(pin, str) and
             re.fullmatch(r"[a-fA-F0-9]{64}", pin)
             and digest(path) == pin.lower(),
             "PINNED_ORIGINAL_CANDIDATE_SHA256_MISMATCH")
    need(type(owner_entry) is str and owner_entry.endswith(".class")
         and not owner_entry.startswith("/")
         and "\\" not in owner_entry
         and all(x not in ("", ".", "..")
                 for x in owner_entry.split("/"))
         and type(surrogate_simple) is str
         and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", surrogate_simple),
         "UNSAFE_OWNER_OR_SURROGATE_BINARY_NAME")
    owner = owner_entry[:-6]
    original_inner = owner + "$" + owner.rsplit("/", 1)[-1]
    candidate_inner = owner + "$" + surrogate_simple
    original_enum_entry = original_inner + ".class"
    candidate_enum_entry = candidate_inner + ".class"
    original_profile = profile_jar_class(original_jar, original_enum_entry)
    candidate_profile = profile_jar_class(candidate_jar, candidate_enum_entry)
    aliases = private_accessor_aliases(original_profile, candidate_profile)
    with ZipFile(candidate_jar) as candidate:
        names = candidate.namelist()
        need(len(names) == len(set(names))
             and names.count(owner_entry) == 1
             and names.count(candidate_enum_entry) == 1,
             "CANDIDATE_OWNER_OR_FOURTH_ENUM_ENTRY_NOT_UNIQUE")
        with tempfile.TemporaryDirectory(
            prefix="v309-accessor-rebind-r105-", dir=output.parent,
        ) as working:
            root = Path(working)
            patched = root / "private-javac-accessors-rebound.jar"
            changed_decls, changed_calls = 0, 0
            with ZipFile(patched, "w") as dest:
                for entry in candidate.infolist():
                    name = entry.filename
                    need(not name.startswith("/")
                         and "\\" not in name
                         and all(x not in ("", ".", "..")
                                 for x in name.split("/")),
                         "UNSAFE_CANDIDATE_ARCHIVE_ENTRY")
                    data = candidate.read(entry)
                    if name.endswith(".class"):
                        data, decls, calls = rebind_member_references(
                            data,
                            target_owner=candidate_inner,
                            name_aliases=aliases,
                            rewrite_declarations=(name == candidate_enum_entry),
                        )
                        changed_decls += decls
                        changed_calls += calls
                    dest.writestr(entry, data)
            need(changed_decls == 2 and changed_calls >= 2,
                 "CANDIDATE_TWO_ACCESSORS_OR_OUTER_CALLS_NOT_REBOUND")
            patched_hash = digest(patched)
            try:
                final = assemble_private_four_enum_candidate(
                    original_jar, patched, owner_entry, surrogate_simple,
                    root / "r104",
                    original_sha256=original_sha256,
                    candidate_sha256=patched_hash,
                )
            except (AllFourPrivateEnumAcceptanceError, ValueError,
                    OSError, KeyError, IndexError) as exc:
                raise SyntheticAccessorMemberRebindError(
                    "R104_R95_ALL_FOUR_PRIVATE_ENUM_ACCEPTANCE_FAILED") from exc
            need(final.get("R95_all_four_enums_exact_parity_passed") is True,
                 "R95_ORIGINAL_FOUR_ENUM_PROOF_MISSING")
            need(digest(original_jar) == original_sha256.lower()
                 and digest(candidate_jar) == candidate_sha256.lower(),
                 "ORIGINAL_OR_CANDIDATE_CHANGED_DURING_ACCEPTANCE")
            report = {
                "schema_version": 1,
                "kind": "v309_four_original_nested_enums_after_exact_accessor_and_metadata_rebind",
                "original_complete_jar_sha256": original_sha256.lower(),
                "source_compiled_candidate_sha256": candidate_sha256.lower(),
                "accessor_aligned_candidate_sha256": patched_hash,
                "r95_accepted_candidate_sha256":
                    final["r95_accepted_candidate_sha256"],
                "exact_original_private_field_accessor_aliases": 2,
                "source_javac_synthetic_method_declarations_rebound": changed_decls,
                "candidate_original_accessor_methodref_callsites_rebound": changed_calls,
                "all_four_original_nested_enums_R95_passed": True,
                "six_original_owner_InnerClasses_rows_equal": True,
                "original_executable_classfile_Code_transferred": False,
                "R97_complete_126field_10method_owner_certified": False,
                "original_client_runtime_equivalence_certified": False,
            }
            accepted = root / "accepted"
            accepted.mkdir()
            shutil.copyfile(
                root / "r104" / "all-four-enums-r95-accepted.private.jar",
                accepted / "all-four-R95-r105-accepted.private.jar",
            )
            with (accepted / "R105-original-four-enums.aggregate.json").open(
                "x", encoding="utf-8", newline="\n",
            ) as stream:
                json.dump(report, stream, sort_keys=True, indent=2)
                stream.write("\n")
            need(not output.exists() and not output.is_symlink(),
                 "OUTPUT_OCCUPIED_AFTER_PRIVATE_REPLAY")
            os.rename(accepted, output)
            return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("original_jar", "candidate_jar", "owner_entry",
                  "surrogate_simple", "new_private_output"):
        p.add_argument(field)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(assemble_original_accessor_and_r95_candidate(
            a.original_jar, a.candidate_jar, a.owner_entry,
            a.surrogate_simple, a.new_private_output,
            original_sha256=a.original_sha256,
            candidate_sha256=a.candidate_sha256,
        ), sort_keys=True))
    except (SyntheticAccessorMemberRebindError, OriginalEnumAccessorError,
            BytecodeProfileError, ValueError, OSError, EOFError):
        p.error("PRIVATE_R105_FOUR_ENUM_ORIGINAL_R95_NOT_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
