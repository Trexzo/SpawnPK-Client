"""Strict reversible identity mapping for javac-generated enum switch tables.

Operate on COPIED JVM classfile bytes. Only reviewed UTF8 constant-pool
entries and one compiler-owned EnclosingMethod class attribute are changed.
No Code instructions, enum runtime values, or original inputs are modified.
"""
from __future__ import annotations

import re
import struct


def restore_generated_switch_table(
    binary: bytes, *, source_class: str, target_class: str,
    source_field: str, target_field: str,
    enum_fields: dict[str, str] | None = None,
) -> bytes:
    if not isinstance(binary, bytes) or binary[:8] != bytes.fromhex("cafebabe00000035"):
        raise ValueError("SWITCH_TABLE_NOT_JAVA9_CLASS")
    valid_class = r"[A-Za-z_$][\w$]*(?:/[A-Za-z_$][\w$]*)+"
    valid_member = r"[A-Za-z_$][\w$]*"
    if (not re.fullmatch(valid_class, source_class)
        or not re.fullmatch(valid_class, target_class)
        or source_class == target_class
        or not re.fullmatch(valid_member, source_field)
        or not re.fullmatch(valid_member, target_field)):
        raise ValueError("UNREVIEWED_SWITCH_TABLE_IDENTITY")

    substitutions = {
        source_class.encode(): target_class.encode(),
        source_field.encode(): target_field.encode(),
    }
    for old, new in (enum_fields or {}).items():
        if not re.fullmatch(valid_member, old) or not re.fullmatch(valid_member, new):
            raise ValueError("UNREVIEWED_ENUM_FIELD_IDENTITY")
        key = old.encode()
        if key in substitutions or new.encode() in substitutions:
            raise ValueError("DUPLICATE_SWITCH_MEMBER_IDENTITY")
        substitutions[key] = new.encode()

    total = struct.unpack_from(">H", binary, 8)[0]
    out = bytearray(binary[:10])
    pos = 10
    index = 1
    original_utf = {}
    found = {key: 0 for key in substitutions}
    while index < total:
        tag = binary[pos]
        out.append(tag)
        pos += 1
        if tag == 1:
            length = struct.unpack_from(">H", binary, pos)[0]
            pos += 2
            raw = binary[pos:pos + length]
            pos += length
            original_utf[index] = raw
            if raw in substitutions:
                found[raw] += 1
                raw = substitutions[raw]
            out.extend(struct.pack(">H", len(raw)))
            out.extend(raw)
        elif tag in (3, 4):
            out.extend(binary[pos:pos + 4])
            pos += 4
        elif tag in (5, 6):
            out.extend(binary[pos:pos + 8])
            pos += 8
            index += 1
        elif tag in (7, 8, 16, 19, 20):
            out.extend(binary[pos:pos + 2])
            pos += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            out.extend(binary[pos:pos + 4])
            pos += 4
        elif tag == 15:
            out.extend(binary[pos:pos + 3])
            pos += 3
        else:
            raise ValueError("UNKNOWN_SWITCH_CLASSFILE_CONSTANT")
        index += 1
    if any(count != 1 for count in found.values()):
        raise ValueError("SWITCH_TABLE_EXPECTED_SYMBOL_MISSING_OR_AMBIGUOUS")

    tail = bytearray(binary[pos:])
    u2 = lambda offset: struct.unpack_from(">H", tail, offset)[0]
    p = 6
    interfaces = u2(p)
    p += 2 + 2 * interfaces
    for _section in ("field", "method"):
        count = u2(p)
        p += 2
        for _ in range(count):
            attrs = u2(p + 6)
            p += 8
            for _ in range(attrs):
                size = struct.unpack_from(">I", tail, p + 2)[0]
                p += 6 + size

    attrs = u2(p)
    start = p
    p += 2
    keep = []
    removed = 0
    for _ in range(attrs):
        name = original_utf[u2(p)]
        size = struct.unpack_from(">I", tail, p + 2)[0]
        if name == b"EnclosingMethod":
            removed += 1
        else:
            keep.append(bytes(tail[p:p + 6 + size]))
        p += 6 + size
    if p != len(tail) or removed != 1 or len(keep) != 1:
        raise ValueError("SWITCH_TABLE_UNEXPECTED_CLASS_ATTRIBUTES")
    tail[start:] = struct.pack(">H", len(keep)) + b"".join(keep)
    return bytes(out + tail)
