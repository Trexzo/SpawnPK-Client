from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import struct
from typing import Any
import zipfile

from .member_identity import _descriptor_identity_shape


class BytecodeProfileError(ValueError):
    pass


_FIELD_OPS = {
    0xB2: "getstatic",
    0xB3: "putstatic",
    0xB4: "getfield",
    0xB5: "putfield",
}


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def take(self, n: int) -> bytes:
        end = self.offset + n
        if end > len(self.data):
            raise BytecodeProfileError("unexpected EOF")
        value = self.data[self.offset:end]
        self.offset = end
        return value

    def u1(self) -> int:
        return self.take(1)[0]

    def u2(self) -> int:
        return struct.unpack(">H", self.take(2))[0]

    def u4(self) -> int:
        return struct.unpack(">I", self.take(4))[0]


def _constant_pool(r: _Reader) -> list[Any]:
    count = r.u2()
    cp: list[Any] = [None] * count
    i = 1
    while i < count:
        tag = r.u1()
        if tag == 1:
            cp[i] = (tag, r.take(r.u2()).decode("utf-8", "replace"))
        elif tag in (3, 4):
            cp[i] = (tag, r.take(4))
        elif tag in (5, 6):
            cp[i] = (tag, r.take(8))
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            cp[i] = (tag, r.u2())
        elif tag in (9, 10, 11, 12, 17, 18):
            cp[i] = (tag, r.u2(), r.u2())
        elif tag == 15:
            cp[i] = (tag, r.u1(), r.u2())
        else:
            raise BytecodeProfileError(
                f"unknown constant-pool tag {tag}"
            )
        i += 1
    return cp


def _utf8(cp: list[Any], index: int) -> str:
    value = cp[index]
    if not value or value[0] != 1:
        raise BytecodeProfileError(
            f"constant pool #{index} is not Utf8"
        )
    return value[1]


def _class_name(cp: list[Any], index: int) -> str:
    value = cp[index]
    if not value or value[0] != 7:
        raise BytecodeProfileError(
            f"constant pool #{index} is not Class"
        )
    return _utf8(cp, value[1])


def _member_ref(
    cp: list[Any],
    index: int,
) -> tuple[str, str, str]:
    value = cp[index]
    if not value or value[0] not in (9, 10, 11):
        raise BytecodeProfileError(
            f"constant pool #{index} is not a member ref"
        )
    owner = _class_name(cp, value[1])
    nt = cp[value[2]]
    if not nt or nt[0] != 12:
        raise BytecodeProfileError(
            f"constant pool #{value[2]} is not NameAndType"
        )
    return owner, _utf8(cp, nt[1]), _utf8(cp, nt[2])


def _skip_attributes(
    r: _Reader,
    cp: list[Any],
) -> None:
    for _ in range(r.u2()):
        _utf8(cp, r.u2())
        r.take(r.u4())


def _instruction_length(
    code: bytes,
    offset: int,
) -> int:
    opcode = code[offset]
    if opcode == 0xAA:
        padding = (4 - ((offset + 1) % 4)) % 4
        base = offset + 1 + padding
        if base + 12 > len(code):
            raise BytecodeProfileError("truncated tableswitch")
        low = struct.unpack_from(">i", code, base + 4)[0]
        high = struct.unpack_from(">i", code, base + 8)[0]
        return 1 + padding + 12 + 4 * (high - low + 1)
    if opcode == 0xAB:
        padding = (4 - ((offset + 1) % 4)) % 4
        base = offset + 1 + padding
        if base + 8 > len(code):
            raise BytecodeProfileError("truncated lookupswitch")
        pairs = struct.unpack_from(">i", code, base + 4)[0]
        return 1 + padding + 8 + 8 * pairs
    if opcode == 0xC4:
        if offset + 1 >= len(code):
            raise BytecodeProfileError("truncated wide")
        return 6 if code[offset + 1] == 0x84 else 4

    if opcode in {
        0x10, 0x12,
        0x15, 0x16, 0x17, 0x18, 0x19,
        0x36, 0x37, 0x38, 0x39, 0x3A,
        0xA9, 0xBC,
    }:
        return 2
    if opcode in {
        0x11, 0x13, 0x14, 0x84,
        *range(0x99, 0xA9),
        0xB2, 0xB3, 0xB4, 0xB5,
        0xB6, 0xB7, 0xB8,
        0xBB, 0xBD, 0xC0, 0xC1,
        0xC6, 0xC7,
    }:
        return 3
    if opcode == 0xC5:
        return 4
    if opcode in {0xB9, 0xBA, 0xC8, 0xC9}:
        return 5
    return 1


def _field_accesses(
    code: bytes,
    cp: list[Any],
) -> list[dict[str, str]]:
    result = []
    offset = 0
    while offset < len(code):
        opcode = code[offset]
        if opcode in _FIELD_OPS:
            if offset + 3 > len(code):
                raise BytecodeProfileError(
                    "truncated field instruction"
                )
            cp_index = struct.unpack_from(
                ">H",
                code,
                offset + 1,
            )[0]
            owner, name, descriptor = _member_ref(
                cp,
                cp_index,
            )
            result.append(
                {
                    "operation": _FIELD_OPS[opcode],
                    "owner": owner,
                    "name": name,
                    "descriptor": descriptor,
                }
            )
        length = _instruction_length(code, offset)
        if length <= 0 or offset + length > len(code):
            raise BytecodeProfileError(
                f"invalid instruction length at {offset}"
            )
        offset += length
    return result


def profile_class_field_accesses(
    data: bytes,
) -> dict[str, Any]:
    """Extract declared fields and per-method field GET/PUT observations."""
    r = _Reader(data)
    if r.u4() != 0xCAFEBABE:
        raise BytecodeProfileError("not a JVM class")
    r.u2()
    r.u2()
    cp = _constant_pool(r)

    r.u2()
    this_class = r.u2()
    r.u2()
    internal_name = _class_name(cp, this_class)

    for _ in range(r.u2()):
        r.u2()

    fields = []
    for _ in range(r.u2()):
        access = r.u2()
        name = _utf8(cp, r.u2())
        descriptor = _utf8(cp, r.u2())
        fields.append(
            {
                "name": name,
                "descriptor": descriptor,
                "access": access,
            }
        )
        _skip_attributes(r, cp)

    methods = []
    for _ in range(r.u2()):
        access = r.u2()
        name = _utf8(cp, r.u2())
        descriptor = _utf8(cp, r.u2())
        accesses: list[dict[str, str]] = []
        code_length = None
        for _ in range(r.u2()):
            attr_name = _utf8(cp, r.u2())
            attr_length = r.u4()
            payload = r.take(attr_length)
            if attr_name != "Code":
                continue
            cr = _Reader(payload)
            cr.u2()
            cr.u2()
            code_length = cr.u4()
            code = cr.take(code_length)
            accesses = _field_accesses(code, cp)

        methods.append(
            {
                "name": name,
                "descriptor": descriptor,
                "access": access,
                "code_length": code_length,
                "field_accesses": accesses,
            }
        )

    return {
        "internal_name": internal_name,
        "fields": fields,
        "methods": methods,
    }


def _method_relations(
    member_class_record: dict[str, Any],
) -> tuple[dict[tuple[str, str], str], dict[tuple[str, str], str]]:
    old_map = {}
    new_map = {}
    methods = member_class_record.get("methods", {})
    for relation in methods.get("relationships", []):
        relation_id = relation.get("relationship_id")
        old = relation.get("old", {})
        new = relation.get("new", {})
        if not isinstance(relation_id, str):
            continue
        old_map[(old.get("name"), old.get("descriptor"))] = relation_id
        new_map[(new.get("name"), new.get("descriptor"))] = relation_id
    return old_map, new_map


def _usage_signatures(
    profile: dict[str, Any],
    method_map: dict[tuple[str, str], str],
    fields: list[dict[str, Any]],
    aliases: dict[str, str],
) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    owner = profile["internal_name"]
    contexts: dict[
        tuple[str, str],
        Counter[tuple[str, str]],
    ] = defaultdict(Counter)

    for method in profile.get("methods", []):
        relation_id = method_map.get(
            (method.get("name"), method.get("descriptor"))
        )
        if relation_id is None:
            continue
        for access in method.get("field_accesses", []):
            if access.get("owner") != owner:
                continue
            key = (
                access.get("name"),
                access.get("descriptor"),
            )
            contexts[key][
                (
                    relation_id,
                    access.get("operation"),
                )
            ] += 1

    grouped: dict[
        tuple[Any, ...],
        list[dict[str, Any]],
    ] = defaultdict(list)
    for field in fields:
        key = (
            field.get("name"),
            field.get("descriptor"),
        )
        context = contexts.get(key, Counter())
        if not context:
            continue
        signature = (
            int(field.get("access", 0)),
            _descriptor_identity_shape(
                str(field.get("descriptor", "")),
                aliases,
            ),
            tuple(
                sorted(
                    (
                        method_id,
                        operation,
                        count,
                    )
                    for (
                        method_id,
                        operation,
                    ), count in context.items()
                )
            ),
        )
        grouped[signature].append(field)
    return grouped


def match_unresolved_fields_by_usage(
    old_profile: dict[str, Any],
    new_profile: dict[str, Any],
    member_class_record: dict[str, Any],
    *,
    old_type_aliases: dict[str, str],
    new_type_aliases: dict[str, str],
) -> dict[str, Any]:
    """Recover only fields with a unique matched-method access signature."""
    old_method_map, new_method_map = _method_relations(
        member_class_record
    )
    fields = member_class_record.get("fields", {})
    old_unmatched = list(fields.get("unmatched_old", []))
    new_unmatched = list(fields.get("unmatched_new", []))

    old_groups = _usage_signatures(
        old_profile,
        old_method_map,
        old_unmatched,
        old_type_aliases,
    )
    new_groups = _usage_signatures(
        new_profile,
        new_method_map,
        new_unmatched,
        new_type_aliases,
    )

    relationships = []
    for signature in set(old_groups) & set(new_groups):
        old_rows = old_groups[signature]
        new_rows = new_groups[signature]
        if len(old_rows) != 1 or len(new_rows) != 1:
            continue
        relationships.append(
            {
                "old": old_rows[0],
                "new": new_rows[0],
                "strategy": "matched_method_field_usage",
                "confidence": "INFERRED_HIGH",
                "score": 0.985,
                "usage_signature": {
                    "access": signature[0],
                    "descriptor_shape": signature[1],
                    "matched_method_accesses": [
                        {
                            "method_relationship_id": row[0],
                            "operation": row[1],
                            "count": row[2],
                        }
                        for row in signature[2]
                    ],
                },
            }
        )

    relationships.sort(
        key=lambda row: (
            str(row["old"].get("name")),
            str(row["old"].get("descriptor")),
        )
    )
    return {
        "schema_version": 1,
        "kind": "field_usage_identity_candidates",
        "canonical": False,
        "old_owner": member_class_record.get("old_owner"),
        "new_owner": member_class_record.get("new_owner"),
        "matched": len(relationships),
        "relationships": relationships,
    }


def profile_jar_class(
    jar_path: Path,
    entry_path: str,
) -> dict[str, Any]:
    with zipfile.ZipFile(jar_path, "r") as archive:
        return profile_class_field_accesses(
            archive.read(entry_path)
        )
