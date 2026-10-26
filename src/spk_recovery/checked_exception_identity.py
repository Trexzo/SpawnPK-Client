"""Strict copied-classfile correction of one Java9 checked-exception declaration.

Does not alter constant pool, fields, method Code, exception handler tables, or
caller-owned input. The original binary is never modified in place.
"""
from __future__ import annotations
import re
import struct


def strip_exact_exception_attribute(binary: bytes, *, method: str,
                                    descriptor: str, exception: str) -> bytes:
    if not isinstance(binary, bytes) or binary[:8] != bytes.fromhex("cafebabe00000035"):
        raise ValueError("NOT_A_JAVA9_CLASSFILE")
    if not all(isinstance(x, str) and x for x in (method, descriptor, exception)):
        raise ValueError("INVALID_METHOD_OR_EXCEPTION_SELECTION")
    if not re.fullmatch(r"[a-zA-Z_$][a-zA-Z0-9_$]*", method):
        raise ValueError("INVALID_METHOD_NAME")
    if not re.fullmatch(r"[A-Za-z0-9_/$]+", exception):
        raise ValueError("INVALID_EXCEPTION_TYPE")
    u2 = lambda raw, pos: struct.unpack_from(">H", raw, pos)[0]
    u4 = lambda raw, pos: struct.unpack_from(">I", raw, pos)[0]
    total = u2(binary, 8)
    offset = 10
    entries = {}
    index = 1
    while index < total:
        tag = binary[offset]
        offset += 1
        if tag == 1:
            n = u2(binary, offset)
            offset += 2
            entries[index] = ("utf", binary[offset:offset + n].decode("utf-8"))
            offset += n
        elif tag in (3, 4):
            offset += 4
        elif tag in (5, 6):
            offset += 8
            index += 1
        elif tag == 7:
            entries[index] = ("class", u2(binary, offset))
            offset += 2
        elif tag in (8, 16, 19, 20):
            offset += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            offset += 4
        elif tag == 15:
            offset += 3
        else:
            raise ValueError("UNKNOWN_CONSTANT_POOL_TAG")
        if offset > len(binary):
            raise ValueError("TRUNCATED_CONSTANT_POOL")
        index += 1
    tail = bytearray(binary[offset:])
    position = 6
    position += 2 + 2 * u2(tail, position)

    def next_member(start):
        end = start + 8
        for _ in range(u2(tail, start + 6)):
            end += 6 + u4(tail, end + 2)
        return end

    fields = u2(tail, position)
    position += 2
    for _ in range(fields):
        position = next_member(position)
    methods = u2(tail, position)
    position += 2
    changed = 0
    for _ in range(methods):
        start = position
        name = entries[u2(tail, start + 2)][1]
        desc = entries[u2(tail, start + 4)][1]
        if (name, desc) != (method, descriptor):
            position = next_member(position)
            continue
        attrs = u2(tail, start + 6)
        cursor = start + 8
        matches = []
        for _ in range(attrs):
            attr = entries[u2(tail, cursor)][1]
            length = u4(tail, cursor + 2)
            if attr == "Exceptions":
                if length != 4 or u2(tail, cursor + 6) != 1:
                    raise ValueError("UNREVIEWED_EXCEPTION_ATTRIBUTE_SHAPE")
                clazz = entries[u2(tail, cursor + 8)]
                if clazz[0] != "class":
                    raise ValueError("INVALID_EXCEPTION_CLASS_REFERENCE")
                actual = entries[clazz[1]][1]
                if actual != exception:
                    raise ValueError("WRONG_CHECKED_EXCEPTION_TYPE")
                matches.append((cursor, 6 + length))
            cursor += 6 + length
        if len(matches) != 1:
            raise ValueError("EXACT_EXCEPTION_ATTRIBUTE_NOT_FOUND")
        where, size = matches[0]
        del tail[where:where + size]
        struct.pack_into(">H", tail, start + 6, attrs - 1)
        position = cursor - size
        changed += 1
    if changed != 1:
        raise ValueError("EXACT_METHOD_NOT_FOUND_OR_AMBIGUOUS")
    return binary[:offset] + tail
