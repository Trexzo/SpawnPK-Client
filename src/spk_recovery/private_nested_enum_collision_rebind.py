"""R98: collision-safe candidate rename for the fourth original-v309 enum.

A Java nested enum cannot have the same simple name as its enclosing Java class.
This module performs an explicitly bounded post-javac *binary* rebinding of a
surrogate enum name, then requires R95 full four-enum JVM + InnerClasses
acceptance against a SHA-pinned original JAR before retaining an artifact.
It is NOT a claim of Java source identity or full client runtime equivalence.
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

from .bytecode_profile import _Reader, _constant_pool, _utf8, _class_name
from .private_four_nested_enum_acceptance import (
    FourNestedEnumAcceptanceError, nested_entries,
    symbolic_innerclasses_table, replay_private_four_enum_gate,
)


class CollisionRebindError(ValueError):
    pass


def need(value, reason):
    if not value:
        raise CollisionRebindError(reason)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def _inner_simple_and_member_names(data, old_internal, outer_internal):
    """Only InnerClasses' exact matching simple-name CP index may be renamed."""
    r = _Reader(data)
    need(r.u4() == 0xCAFEBABE, "INVALID_CANDIDATE_CLASSFILE")
    r.u2()
    r.u2()
    cp = _constant_pool(r)
    r.u2()
    r.u2()
    r.u2()
    r.take(2 * r.u2())
    members = set()
    for _ in range(2):
        for __ in range(r.u2()):
            r.u2()
            members.add(r.u2())
            r.u2()
            for ___ in range(r.u2()):
                r.u2()
                r.take(r.u4())
    allowed = set()
    for _ in range(r.u2()):
        name = _utf8(cp, r.u2())
        raw = r.take(r.u4())
        if name != "InnerClasses":
            continue
        q = _Reader(raw)
        for __ in range(q.u2()):
            inner, outer, simple, flags = q.u2(), q.u2(), q.u2(), q.u2()
            if (_class_name(cp, inner) == old_internal
                    and _class_name(cp, outer) == outer_internal and simple):
                allowed.add(simple)
        need(q.offset == len(raw), "INVALID_INNERCLASSES_BODY")
    need(r.offset == len(data), "CLASSFILE_TAIL_INVALID")
    return allowed, members


def rebind_classfile(data, outer_internal, surrogate_simple):
    """Rewrite only vetted JVM class/descriptor and InnerClasses identities.

    Unsupported generic signatures and ambiguous pooled string/member names
    fail closed. The entire original bytecode and method Code remain untouched.
    """
    need(isinstance(outer_internal, str)
         and re.fullmatch(r"[A-Za-z0-9_$/]+", outer_internal)
         and isinstance(surrogate_simple, str)
         and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", surrogate_simple),
         "UNSAFE_CLASS_IDENTITY")
    old = (outer_internal + "$" + surrogate_simple).encode("ascii")
    original_simple = outer_internal.rsplit("/", 1)[-1]
    need(surrogate_simple != original_simple,
         "SURROGATE_MUST_DIFFER_FROM_ENCLOSING_NAME")
    new = (outer_internal + "$" + original_simple).encode("ascii")
    allowed, members = _inner_simple_and_member_names(
        data, old.decode(), outer_internal)
    r = _Reader(data)
    head = r.take(8)
    n = r.u2()
    out = bytearray(head + n.to_bytes(2, "big"))
    string_indices = set()
    patched = []
    occurrences = 0
    i = 1
    while i < n:
        tag = r.u1()
        out.append(tag)
        if tag == 1:
            raw = r.take(r.u2())
            replacement = raw
            if raw == surrogate_simple.encode("ascii"):
                need(i in allowed and i not in members,
                     "AMBIGUOUS_SURROGATE_SIMPLE_NAME")
                replacement = original_simple.encode("ascii")
            elif old in raw:
                # Only JVM class names and complete L...; descriptors,
                # not arbitrary literals or unknown signature shapes.
                if raw == old:
                    replacement = new
                elif b"L" + old + b";" in raw:
                    replacement = raw.replace(b"L" + old + b";",
                                              b"L" + new + b";")
                    need(old not in replacement, "UNSUPPORTED_TYPE_REFERENCE")
                else:
                    raise CollisionRebindError("UNSUPPORTED_SURROGATE_REFERENCE")
            if replacement != raw:
                occurrences += 1
                patched.append(i)
            need(len(replacement) <= 65535, "REWRITTEN_UTF8_TOO_LONG")
            out.extend(len(replacement).to_bytes(2, "big"))
            out.extend(replacement)
        elif tag in (3, 4):
            out.extend(r.take(4))
        elif tag in (5, 6):
            out.extend(r.take(8))
            i += 1
        elif tag in (7, 16, 19, 20):
            out.extend(r.take(2))
        elif tag == 8:
            idx = r.u2()
            string_indices.add(idx)
            out.extend(idx.to_bytes(2, "big"))
        elif tag in (9, 10, 11, 12, 17, 18):
            out.extend(r.take(4))
        elif tag == 15:
            out.extend(r.take(3))
        else:
            raise CollisionRebindError("UNKNOWN_CONSTANT_POOL_TAG")
        i += 1
    need(not (string_indices & set(patched)),
         "SURROGATE_NAME_REUSED_AS_STRING_LITERAL")
    out.extend(r.take(len(data) - r.offset))
    need(len(out) >= 10, "EMPTY_CLASSFILE_REBIND")
    return bytes(out), occurrences


def rebind_private_fourth_enum(
    original_jar, candidate_jar, owner_entry, surrogate_simple, output,
    *, original_sha256, candidate_sha256,
):
    original_jar, candidate_jar, output = map(
        Path, (original_jar, candidate_jar, output))
    need(not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "OUTPUT_NOT_FRESH")
    for p, pin in ((original_jar, original_sha256),
                   (candidate_jar, candidate_sha256)):
        need(p.is_file() and not p.is_symlink()
             and isinstance(pin, str) and re.fullmatch(r"[0-9a-fA-F]{64}", pin)
             and sha(p) == pin.lower(), "SOURCE_JAR_SHA256_MISMATCH")
    need(original_jar.resolve() != candidate_jar.resolve(),
         "ORIGINAL_CANDIDATE_JAR_MUST_BE_DISTINCT")
    need(isinstance(owner_entry, str) and owner_entry.endswith(".class")
         and not owner_entry.startswith("/") and ".." not in owner_entry
         and "\\" not in owner_entry, "UNSAFE_OWNER_ENTRY")
    owner = owner_entry[:-6]
    outer_simple = owner.rsplit("/", 1)[-1]
    need(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", outer_simple)
         and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", surrogate_simple)
         and surrogate_simple != outer_simple,
         "INVALID_COLLIDING_NESTED_IDENTITIES")
    exact_entry = owner + "$" + outer_simple + ".class"
    surrogate_entry = owner + "$" + surrogate_simple + ".class"
    with ZipFile(original_jar) as original, ZipFile(candidate_jar) as candidate:
        orig_names = original.namelist()
        cand_names = candidate.namelist()
        need(len(orig_names) == len(set(orig_names))
             and len(cand_names) == len(set(cand_names))
             and orig_names.count(owner_entry) == 1
             and cand_names.count(owner_entry) == 1
             and exact_entry in nested_entries(orig_names, owner_entry)
             and surrogate_entry in nested_entries(cand_names, owner_entry)
             and exact_entry not in cand_names,
             "REQUIRED_EXACT_ORIGINAL_COLLISION_OR_SURROGATE_MISSING")
        target = (owner, owner, outer_simple)
        original_ic = symbolic_innerclasses_table(original.read(owner_entry))
        need(any(x[:3] == (owner + "$" + outer_simple,
                            owner, outer_simple) for x in original_ic),
             "ORIGINAL_COLLIDING_INNERCLASSES_NOT_PRESENT")
        surrogate_ic = symbolic_innerclasses_table(candidate.read(owner_entry))
        need(any(x[:3] == (owner + "$" + surrogate_simple,
                            owner, surrogate_simple) for x in surrogate_ic),
             "CANDIDATE_SURROGATE_INNERCLASSES_NOT_PRESENT")
        with tempfile.TemporaryDirectory(
            prefix="v309-collision-r98-", dir=output.parent,
        ) as directory:
            stage = Path(directory)
            modified = 0
            with ZipFile(stage / "candidate-rebound.private.jar", "w") as dest:
                for entry in candidate.infolist():
                    name = entry.filename
                    need(not name.startswith("/") and ".." not in name.split("/")
                         and "\\" not in name, "UNSAFE_CANDIDATE_ARCHIVE_ENTRY")
                    data = candidate.read(entry)
                    if name.endswith(".class"):
                        data, changed = rebind_classfile(
                            data, owner, surrogate_simple)
                        modified += changed
                    if name == surrogate_entry:
                        entry.filename = exact_entry
                    dest.writestr(entry, data)
            need(modified >= 2, "NO_SURROGATE_CLASS_REBOUND")
            patched = stage / "candidate-rebound.private.jar"
            patched_pin = sha(patched)
            need(sha(original_jar) == original_sha256.lower()
                 and sha(candidate_jar) == candidate_sha256.lower(),
                 "PINNED_INPUT_JAR_CHANGED")
            try:
                proof = replay_private_four_enum_gate(
                    original_jar, patched, owner_entry, stage / "r95",
                    original_sha256=original_sha256,
                    candidate_sha256=patched_pin,
                )
            except (FourNestedEnumAcceptanceError, OSError, ValueError) as exc:
                raise CollisionRebindError(
                    "R95_ORIGINAL_FOUR_ENUM_PARITY_NOT_ACCEPTED") from exc
            need(proof["original_nested_enum_classes_verified"] == 4
                 and proof["symbolic_InnerClasses_tables_identical_all_four"]
                 and proof["original_candidate_owner_InnerClasses_tables_identical"],
                 "POST_REBIND_INNERCLASSES_NOT_EXACT")
            need(sha(patched) == patched_pin,
                 "REBOUND_CANDIDATE_CHANGED")
            result = {
                "schema_version": 1,
                "kind": "private_v309_fourth_enum_post_javac_collision_rebind",
                "original_sha256": original_sha256.lower(),
                "compiled_candidate_before_sha256": candidate_sha256.lower(),
                "rebound_candidate_sha256": patched_pin,
                "constant_pool_utf8_entries_rebound": modified,
                "four_nested_enum_R95_parity_passed": True,
                "java_authorial_source_identity_proven": False,
                "whole_client_runtime_equivalence_certified": False,
            }
            final = stage / "accepted"
            final.mkdir()
            shutil.copyfile(patched, final / "candidate-rebound.private.jar")
            with (final / "collision-rebind.aggregate.json").open(
                "x", encoding="utf-8", newline="\n",
            ) as f:
                json.dump(result, f, sort_keys=True, indent=2)
                f.write("\n")
            need(not output.exists() and not output.is_symlink(),
                 "OUTPUT_OCCUPIED_AFTER_VERIFICATION")
            os.rename(final, output)
            return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("original_jar", "candidate_jar",
                  "owner_class", "surrogate_simple_name", "new_private_output"):
        p.add_argument(field)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(rebind_private_fourth_enum(
            a.original_jar, a.candidate_jar, a.owner_class,
            a.surrogate_simple_name, a.new_private_output,
            original_sha256=a.original_sha256,
            candidate_sha256=a.candidate_sha256,
        ), sort_keys=True))
    except CollisionRebindError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
