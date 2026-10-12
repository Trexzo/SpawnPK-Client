"""R103: private, exact original-v309 owner InnerClasses metadata rebuild.

Reconstruct the *symbolic* ordered six-entry owner InnerClasses attribute
from SHA-pinned original v309 evidence in a separately compiled candidate
class. Never transfer original classfile/Code bytes. The two nonlocal entries
are symbolic metadata references and are not proof of packaged implementations.
Actual R95 four-enum JVM instruction parity remains mandatory afterwards.
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
)
from .private_four_nested_enum_acceptance import (
    FourNestedEnumAcceptanceError, symbolic_innerclasses_table,
)


class OriginalOwnerInnerClassesError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise OriginalOwnerInnerClassesError(reason)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as file:
        for part in iter(lambda: file.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def _u2(value):
    need(type(value) is int and 0 <= value <= 65535,
         "JVM_U2_OUT_OF_RANGE")
    return value.to_bytes(2, "big")


def _safe_internal(value):
    return (type(value) is str and len(value) > 0 and
            len(value.encode("ascii", errors="ignore")) == len(value) and
            re.fullmatch(r"[A-Za-z0-9_$/]+", value) is not None and
            all(part not in ("", ".", "..") for part in value.split("/")))


def _validate_table(symbolic, owner):
    need(isinstance(symbolic, tuple) and len(symbolic) == 6,
         "ORIGINAL_OWNER_MUST_HAVE_SIX_INNERCLASSES_ROWS")
    need(len(set(symbolic)) == 6, "DUPLICATE_ORIGINAL_INNERCLASSES_ROWS")
    for inner, outer, simple, flags in symbolic:
        need(_safe_internal(inner)
             and (outer is None or _safe_internal(outer))
             and (simple is None or (
                 re.fullmatch(r"[A-Za-z0-9_$]+", simple) is not None
                 and simple.isascii()))
             and type(flags) is int and 0 <= flags <= 65535,
             "UNSAFE_ORIGINAL_INNERCLASSES_SYMBOLS")
    local = [r for r in symbolic if r[1] == owner]
    external = [r for r in symbolic if r[1] != owner]
    need(len(local) == 4 and len(external) == 2
         and len({r[0] for r in local}) == 4
         and all(x[0].startswith(owner + "$") for x in local),
         "FOUR_LOCAL_TWO_EXTERNAL_ORIGINAL_INNERCLASSES_REQUIRED")
    collision = owner + "$" + owner.rsplit("/", 1)[-1]
    need(sum(r[0] == collision and
             r[2] == owner.rsplit("/", 1)[-1] for r in local) == 1,
         "ORIGINAL_FOURTH_ENUM_JVM_NAME_COLLISION_REQUIRED")


def _class_structure(class_data):
    need(type(class_data) is bytes and class_data[:4] == b"\xca\xfe\xba\xbe",
         "INVALID_CANDIDATE_OWNER_CLASSFILE")
    r = _Reader(class_data)
    r.take(8)
    cp = _constant_pool(r)
    cp_end = r.offset
    r.u2()  # access
    this_index = r.u2()
    internal_name = _class_name(cp, this_index)
    r.u2()  # super
    r.take(2 * r.u2())  # interfaces
    for _ in range(2):
        for __ in range(r.u2()):
            r.take(6)  # field/method header
            for ___ in range(r.u2()):
                r.u2()
                r.take(r.u4())
    attributes_offset = r.offset
    attribute_count = r.u2()
    attributes = []
    for _ in range(attribute_count):
        name_idx = r.u2()
        body = r.take(r.u4())
        attributes.append((name_idx, _utf8(cp, name_idx), body))
    need(r.offset == len(class_data), "CANDIDATE_CLASSFILE_TRAILING_BYTES")
    need(sum(n == "InnerClasses" for _, n, _ in attributes) <= 1,
         "DUPLICATE_CANDIDATE_OWNER_INNERCLASSES")
    return cp, cp_end, attributes_offset, attributes, internal_name


def replace_owner_innerclasses(class_data, owner, original_table):
    """Update ONLY constant-pool additions + class-level InnerClasses.

    Keep old method/field bytes and every other class attribute byte-identical.
    """
    need(_safe_internal(owner), "UNSAFE_ORIGINAL_OWNER_NAME")
    _validate_table(original_table, owner)
    cp, cp_end, attributes_offset, attributes, candidate_name = _class_structure(class_data)
    need(candidate_name == owner, "CANDIDATE_OWNER_INTERNAL_NAME_MISMATCH")
    names = {i: _utf8(cp, i) for i in range(1, len(cp))
             if cp[i] is not None and cp[i][0] == 1}
    classes = {i: _class_name(cp, i) for i in range(1, len(cp))
               if cp[i] is not None and cp[i][0] == 7}
    added = bytearray()
    count = len(cp)

    def utf8_index(value):
        nonlocal count
        hits = [i for i, s in names.items() if s == value]
        if hits:
            return hits[0]
        need(value.isascii() and "\x00" not in value,
             "UNSUPPORTED_NEW_CONSTANT_POOL_UTF8")
        raw = value.encode("ascii")
        need(len(raw) <= 65535 and count < 65535,
             "NEW_CONSTANT_POOL_UTF8_TOO_LARGE")
        index = count
        count += 1
        added.extend(b"\x01" + _u2(len(raw)) + raw)
        names[index] = value
        return index

    def class_index(name):
        nonlocal count
        if name is None:
            return 0
        hits = [i for i, s in classes.items() if s == name]
        if hits:
            return hits[0]
        name_index = utf8_index(name)
        need(count < 65535, "NEW_CONSTANT_POOL_CLASS_OVERFLOW")
        index = count
        count += 1
        added.extend(b"\x07" + _u2(name_index))
        classes[index] = name
        return index

    body = bytearray(_u2(len(original_table)))
    for inner, outer, simple, flags in original_table:
        body.extend(_u2(class_index(inner)))
        body.extend(_u2(class_index(outer)))
        body.extend(_u2(utf8_index(simple) if simple is not None else 0))
        body.extend(_u2(flags))
    replacement_name = utf8_index("InnerClasses")
    rewritten_attrs = []
    seen = False
    for name_index, name, raw in attributes:
        if name == "InnerClasses":
            need(not seen, "DUPLICATE_INNERCLASSES_ATTRIBUTE")
            seen = True
            rewritten_attrs.append((name_index, bytes(body)))
        else:
            rewritten_attrs.append((name_index, raw))
    if not seen:
        rewritten_attrs.append((replacement_name, bytes(body)))
    need(len(rewritten_attrs) <= 65535, "JVM_ATTRIBUTE_COUNT_OVERFLOW")

    rebuilt = bytearray(
        class_data[:8] + _u2(count) +
        class_data[10:cp_end] + added +
        class_data[cp_end:attributes_offset] +
        _u2(len(rewritten_attrs))
    )
    for name_index, value in rewritten_attrs:
        rebuilt.extend(_u2(name_index))
        rebuilt.extend(len(value).to_bytes(4, "big"))
        rebuilt.extend(value)
    changed = bytes(rebuilt)
    try:
        need(symbolic_innerclasses_table(changed) == original_table,
             "REBUILT_ORIGINAL_INNERCLASSES_TABLE_DIFFERENT")
    except (FourNestedEnumAcceptanceError,
            BytecodeProfileError, UnicodeError, IndexError) as exc:
        raise OriginalOwnerInnerClassesError(
            "REBUILT_JVM_SYMBOLIC_TABLE_NOT_REPLAYABLE") from exc
    # Check classfile body containing all existing field/method bytecode was
    # copied without modification. Original classfile itself is never copied.
    _, next_cp_end, next_attr_offset, _, revised_name = _class_structure(changed)
    need(revised_name == owner, "REBUILT_OWNER_INTERNAL_NAME_CHANGED")
    need(changed[next_cp_end:next_attr_offset] ==
         class_data[cp_end:attributes_offset] and
         changed[:8] == class_data[:8],
         "NON_METADATA_CLASSFILE_CONTENT_CHANGED")
    return changed, count - len(cp)


def rebuild_private_owner_six_innerclasses(
    original_jar, candidate_jar, owner_entry, output, *,
    original_sha256, candidate_sha256,
):
    original_jar, candidate_jar, output = map(
        Path, (original_jar, candidate_jar, output))
    need(output.parent.is_dir() and not output.parent.is_symlink()
         and not output.exists() and not output.is_symlink(),
         "NEW_PRIVATE_OUTPUT_REQUIRED")
    need(isinstance(owner_entry, str) and owner_entry.endswith(".class")
         and _safe_internal(owner_entry[:-6]),
         "UNSAFE_ORIGINAL_OWNER_ARCHIVE_ENTRY")
    need(original_jar.resolve() != candidate_jar.resolve(),
         "ORIGINAL_CANDIDATE_JARS_MUST_DIFFER")
    for path, pin in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        need(path.is_file() and not path.is_symlink()
             and isinstance(pin, str) and
             re.fullmatch(r"[a-fA-F0-9]{64}", pin)
             and digest(path) == pin.lower(),
             "ORIGINAL_CANDIDATE_JAR_PIN_MISMATCH")

    with ZipFile(original_jar) as source, ZipFile(candidate_jar) as candidate:
        original_names, candidate_names = source.namelist(), candidate.namelist()
        need(len(original_names) == len(set(original_names))
             and len(candidate_names) == len(set(candidate_names))
             and original_names.count(owner_entry) == 1
             and candidate_names.count(owner_entry) == 1,
             "ORIGINAL_OR_CANDIDATE_OWNER_UNIQUE_ENTRY_MISSING")
        original_bytes = source.read(owner_entry)
        candidate_bytes = candidate.read(owner_entry)
        need(original_bytes[4:8] == candidate_bytes[4:8],
             "ORIGINAL_CANDIDATE_JVM_VERSION_DIFFERENT")
        table = symbolic_innerclasses_table(original_bytes)
        _validate_table(table, owner_entry[:-6])
        rewritten, new_pool_entries = replace_owner_innerclasses(
            candidate_bytes, owner_entry[:-6], table)
        with tempfile.TemporaryDirectory(
            prefix="v309-owner-innerclasses-r103-", dir=output.parent,
        ) as temp:
            root = Path(temp)
            modified = root / "owner-innerclasses-rebuilt.private.jar"
            with ZipFile(modified, "w") as dest:
                for entry in candidate.infolist():
                    need(not entry.filename.startswith("/")
                         and "\\" not in entry.filename
                         and all(x not in ("", ".", "..") for x in
                                 entry.filename.split("/")),
                         "CANDIDATE_ARCHIVE_ENTRY_UNSAFE")
                    data = (rewritten if entry.filename == owner_entry
                            else candidate.read(entry))
                    dest.writestr(entry, data)
            with ZipFile(modified) as z:
                need(symbolic_innerclasses_table(z.read(owner_entry)) == table,
                     "OUTPUT_OWNER_TABLE_NOT_EXACT")
            need(digest(original_jar) == original_sha256.lower()
                 and digest(candidate_jar) == candidate_sha256.lower(),
                 "PINNED_JARS_CHANGED_DURING_REPLAY")
            report = {
                "schema_version": 1,
                "kind": "private_original_v309_six_owner_innerclasses_metadata",
                "original_complete_jar_sha256": original_sha256.lower(),
                "candidate_complete_jar_sha256": candidate_sha256.lower(),
                "metadata_rebuilt_candidate_sha256": digest(modified),
                "exact_ordered_owner_innerclasses_entries": 6,
                "locally_nested_enum_entries": 4,
                "externally_referenced_innerclasses_entries": 2,
                "constant_pool_entries_added": new_pool_entries,
                "candidate_field_method_bytecode_preserved": True,
                "actual_original_classfile_body_transferred": False,
                "all_four_enum_method_R95_parity_certified": False,
                "complete_R97_source_compilation_certified": False,
                "whole_client_runtime_equivalence_certified": False,
            }
            accepted = root / "accepted"
            accepted.mkdir()
            shutil.copyfile(modified, accepted / modified.name)
            with (accepted / "owner-innerclasses.aggregate.json").open(
                "x", encoding="utf-8", newline="\n",
            ) as result:
                json.dump(report, result, sort_keys=True, indent=2)
                result.write("\n")
            need(not output.exists() and not output.is_symlink(),
                 "PRIVATE_OUTPUT_OCCUPIED_BEFORE_PROMOTION")
            os.rename(accepted, output)
            return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original_jar", "candidate_jar", "owner_entry",
                 "new_private_output"):
        parser.add_argument(name)
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = rebuild_private_owner_six_innerclasses(
            args.original_jar, args.candidate_jar,
            args.owner_entry, args.new_private_output,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
        )
        print(json.dumps(result, sort_keys=True))
    except (OriginalOwnerInnerClassesError,
            FourNestedEnumAcceptanceError, BytecodeProfileError,
            ValueError, OSError, EOFError):
        parser.error("PRIVATE_SIX_ORIGINAL_OWNER_INNERCLASSES_NOT_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
