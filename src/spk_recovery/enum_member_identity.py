"""Fail-closed JVM enum member identity restoration in copied Java9 classfiles.

Only enum field declarations, owner Fieldref/Methodref NameAndType entries,
and javac's generated $values helper are rewritten. Enum String constants,
code, original source and nonowner symbols are never changed.
"""
from __future__ import annotations
import re
import struct


def restore_enum_member_identity(blob: bytes, owner: str,
                                 fields: dict[str, str], helper_name: str) -> bytes:
    if not isinstance(blob, bytes) or blob[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("NOT_A_JVM_CLASSFILE")
    if not re.fullmatch(r"[\w$]+(?:/[\w$]+)+", owner) or not fields or "$VALUES" not in fields:
        raise ValueError("ENUM_MEMBER_ALIAS_INVALID")
    if not isinstance(helper_name, str) or not re.fullmatch(r"[a-zA-Z_$][\w$]*", helper_name):
        raise ValueError("ENUM_HELPER_ALIAS_INVALID")
    if any(
        not isinstance(k, str) or not isinstance(v, str)
        or not re.fullmatch(r"[a-zA-Z_$][\w$]*", v)
        for k, v in fields.items()
    ):
        raise ValueError("ENUM_MEMBER_ALIAS_INVALID")

    def get16(buf, p):
        return struct.unpack_from(">H", buf, p)[0]

    def put16(buf, p, value):
        struct.pack_into(">H", buf, p, value)

    total = get16(blob, 8)
    p = 10
    idx = 1
    cp = [None] * total
    order = []
    while idx < total:
        start = p
        tag = blob[p]
        p += 1
        if tag == 1:
            p += 2 + get16(blob, p)
        elif tag in (3, 4):
            p += 4
        elif tag in (5, 6):
            p += 8
        elif tag in (7, 8, 16, 19, 20):
            p += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            p += 4
        elif tag == 15:
            p += 3
        else:
            raise ValueError("UNSUPPORTED_CLASSFILE_TAG")
        if p > len(blob):
            raise ValueError("TRUNCATED_CLASSFILE")
        cp[idx] = [tag, bytearray(blob[start:p])]
        order.append(idx)
        if tag in (5, 6):
            idx += 1
        idx += 1

    def utf(n):
        if n < 1 or n >= len(cp) or cp[n] is None or cp[n][0] != 1:
            raise ValueError("BAD_JVM_UTF8_INDEX")
        return bytes(cp[n][1][3:]).decode("utf-8")

    originals = set(fields)
    new_names = {}
    for value in sorted(set(fields.values()) | {helper_name}):
        j = len(cp)
        raw = value.encode("utf-8")
        cp.append([1, bytearray(b"\x01" + struct.pack(">H", len(raw)) + raw)])
        order.append(j)
        new_names[value] = j

    body = bytearray(blob[p:])
    pos = 6
    interface_count = get16(body, pos)
    pos += 2 + 2 * interface_count
    field_count = get16(body, pos)
    pos += 2
    seen = set()
    for _ in range(field_count):
        name = utf(get16(body, pos + 2))
        if name in fields:
            if name in seen:
                raise ValueError("DUPLICATE_ENUM_MEMBER")
            seen.add(name)
            put16(body, pos + 2, new_names[fields[name]])
        attributes = get16(body, pos + 6)
        pos += 8
        for _ in range(attributes):
            pos += 6 + struct.unpack_from(">I", body, pos + 2)[0]
    if seen != originals:
        raise ValueError("MISSING_ORIGINAL_ENUM_MEMBER")

    method_count = get16(body, pos)
    pos += 2
    helpers = 0
    for _ in range(method_count):
        name = utf(get16(body, pos + 2))
        if name == "$values":
            helpers += 1
            put16(body, pos + 2, new_names[helper_name])
        attributes = get16(body, pos + 6)
        pos += 8
        for _ in range(attributes):
            pos += 6 + struct.unpack_from(">I", body, pos + 2)[0]
    if helpers != 1:
        raise ValueError("MISSING_GENERATED_ENUM_HELPER")

    classes = {
        n for n in order
        if cp[n][0] == 7 and utf(get16(cp[n][1], 1)) == owner
    }
    if len(classes) != 1:
        raise ValueError("ENUM_OWNER_NOT_FOUND")
    for n in order:
        tag, data = cp[n]
        if tag not in (9, 10) or get16(data, 1) not in classes:
            continue
        nt = cp[get16(data, 3)]
        if nt[0] != 12:
            raise ValueError("INVALID_NAME_AND_TYPE")
        name = utf(get16(nt[1], 1))
        rename = (
            fields.get(name) if tag == 9
            else (helper_name if name == "$values" else None)
        )
        if rename:
            put16(nt[1], 1, new_names[rename])

    return (
        blob[:8] + struct.pack(">H", len(cp))
        + b"".join(cp[n][1] for n in order) + body
    )
