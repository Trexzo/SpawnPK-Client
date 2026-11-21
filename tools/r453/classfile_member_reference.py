"""R453 pure Java11 JVM constant-pool member reference/definition census.

This module reads bytes only: never loads or executes Java classes. It finds
CONSTANT_Fieldref, CONSTANT_Methodref, and CONSTANT_InterfaceMethodref
owner/name/descriptor triples and compares them with *direct declarations*
inside classfiles. It does NOT implement the JVM's inherited method/field
resolution rules, dynamic invokedynamic linking or binary compatibility.
A member not directly declared may legitimately be inherited.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from tools.r449 import audit_descriptor_resource_gaps as r449
from tools.r447 import audit_original_class_asset_coverage as r447

MAX_CLASS_BYTES = 32 * 1024 * 1024
MAX_CP_ENTRIES = 65535
MAX_MEMBERS = 60000
MAX_ATTRIBUTES = 4000
MAX_ATTRIBUTE_BYTES = 16 * 1024 * 1024
MAX_UTF_BYTES = 65535

@dataclass(frozen=True, order=True)
class Member:
    owner: str
    name: str
    descriptor: str
    kind: str  # field, method, interface_method


@dataclass(frozen=True)
class ClassMembers:
    class_name: str
    superclass_name: str | None
    declared_fields: frozenset[tuple[str, str]]
    declared_methods: frozenset[tuple[str, str]]
    references: frozenset[Member]
    # R454: preserve declared direct interfaces and member access metadata
    # without altering R453's positional ClassMembers fixture constructor.
    interfaces: frozenset[str] = frozenset()
    declared_field_access: tuple[tuple[str, str, int], ...] = ()
    declared_method_access: tuple[tuple[str, str, int], ...] = ()
    access_flags: int = 0


class Refused(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def valid_internal_name(name: str) -> str:
    need(type(name) is str and 1 <= len(name) <= 4096
         and name.isascii() and "\\" not in name
         and re.fullmatch(r"[A-Za-z0-9_$]+(?:/[A-Za-z0-9_$]+)*", name)
         is not None, "R453_INVALID_CLASS_INTERNAL_NAME")
    path = name + ".class"
    try:
        r447.zip_path(path)
    except r447.Refused:
        raise Refused("R453_UNSAFE_CLASS_OWNER_NAME") from None
    return path


def valid_member_name(name: str, kind: str) -> str:
    need(type(name) is str and name and len(name) <= 255
         and name.isascii(), "R453_BAD_MEMBER_NAME")
    if kind == "field":
        need(re.fullmatch(r"[A-Za-z0-9_$]+", name) is not None,
             "R453_INVALID_FIELD_NAME")
    else:
        need(name in ("<init>", "<clinit>") or
             re.fullmatch(r"[A-Za-z0-9_$]+", name) is not None,
             "R453_INVALID_METHOD_NAME")
    return name


def validate_descriptor(value: str, kind: str) -> None:
    need((kind == "field" and not value.startswith("("))
         or (kind in ("method", "interface_method")
             and value.startswith("(")),
         "R453_WRONG_MEMBER_DESCRIPTOR_KIND")
    try:
        r449.descriptor_classes(value)
    except r449.Refused:
        raise Refused("R453_MALFORMED_MEMBER_DESCRIPTOR") from None


def parse_class(raw: bytes) -> ClassMembers:
    need(type(raw) is bytes and 10 <= len(raw) <= MAX_CLASS_BYTES
         and raw[:4] == b"\xca\xfe\xba\xbe"
         and int.from_bytes(raw[6:8], "big") == 55,
         "R453_JAVA11_CLASSFILE_REQUIRED")
    pos = 8

    def take(n: int) -> bytes:
        nonlocal pos
        need(0 <= n <= len(raw)-pos, "R453_TRUNCATED_CLASSFILE")
        result = raw[pos:pos+n]
        pos += n
        return result

    def u1() -> int:
        return take(1)[0]

    def u2() -> int:
        return int.from_bytes(take(2), "big")

    def u4() -> int:
        return int.from_bytes(take(4), "big")

    count = u2()
    need(1 <= count <= MAX_CP_ENTRIES, "R453_INVALID_CP_COUNT")
    tags = [0] * count
    cp: list[object | None] = [None] * count
    i = 1
    while i < count:
        tag = u1()
        tags[i] = tag
        if tag == 1:
            length = u2()
            need(length <= MAX_UTF_BYTES, "R453_UTF_CONSTANT_TOO_LONG")
            cp[i] = take(length).decode("utf-8", "replace")
        elif tag in (3, 4):
            take(4)
        elif tag in (5, 6):
            take(8)
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            cp[i] = u2()
        elif tag in (9, 10, 11, 12, 17, 18):
            cp[i] = (u2(), u2())
        elif tag == 15:
            cp[i] = (u1(), u2())
        else:
            raise Refused("R453_UNKNOWN_CONSTANT_POOL_TAG")
        i += 1

    def utf(index: int) -> str:
        need(type(index) is int and 0 < index < count
             and tags[index] == 1 and type(cp[index]) is str,
             "R453_CP_UTF_INDEX_INVALID")
        return cp[index]

    def cls(index: int) -> str:
        need(type(index) is int and 0 < index < count
             and tags[index] == 7, "R453_CP_CLASS_INDEX_INVALID")
        return valid_internal_name(utf(cp[index]))

    def nat(index: int, kind: str) -> tuple[str, str]:
        need(type(index) is int and 0 < index < count
             and tags[index] == 12, "R453_CP_NAME_AND_TYPE_INVALID")
        ni, di = cp[index]
        name = valid_member_name(utf(ni), kind)
        descriptor = utf(di)
        validate_descriptor(descriptor, kind)
        return name, descriptor

    references = set()
    for index in range(1, count):
        tag = tags[index]
        if tag in (9, 10, 11):
            owner_idx, nat_idx = cp[index]
            kind = {9: "field", 10: "method", 11: "interface_method"}[tag]
            owner = cls(owner_idx)
            name, descriptor = nat(nat_idx, kind)
            references.add(Member(owner, name, descriptor, kind))

    class_access_flags = u2()
    class_name = cls(u2())
    super_index = u2()
    superclass = cls(super_index) if super_index else None
    interfaces = u2()
    need(interfaces <= MAX_MEMBERS, "R453_INTERFACE_COUNT_LIMIT")
    directly_implemented = set()
    for _ in range(interfaces):
        interface_name = cls(u2())
        need(interface_name not in directly_implemented,
             "R454_DUPLICATE_INTERFACE_EDGE")
        directly_implemented.add(interface_name)

    def attributes() -> None:
        num = u2()
        need(num <= MAX_ATTRIBUTES, "R453_ATTRIBUTE_COUNT_LIMIT")
        for _ in range(num):
            utf(u2())
            length = u4()
            need(length <= MAX_ATTRIBUTE_BYTES,
                 "R453_ATTRIBUTE_BYTE_BUDGET")
            take(length)

    declared_fields: set[tuple[str, str]] = set()
    declared_methods: set[tuple[str, str]] = set()
    field_flags: list[tuple[str, str, int]] = []
    method_flags: list[tuple[str, str, int]] = []
    for kind, destination in (("field", declared_fields),
                              ("method", declared_methods)):
        members = u2()
        need(members <= MAX_MEMBERS, "R453_MEMBER_COUNT_LIMIT")
        for _ in range(members):
            flags = u2()
            name = valid_member_name(utf(u2()), kind)
            desc = utf(u2())
            validate_descriptor(desc, kind)
            need((name, desc) not in destination,
                 "R453_DUPLICATE_CLASS_DECLARATION")
            destination.add((name, desc))
            (field_flags if kind == "field" else method_flags).append(
                (name, desc, flags))
            attributes()
    attributes()
    need(pos == len(raw), "R453_TRAILING_CLASSFILE_BYTES")
    return ClassMembers(
        class_name, superclass,
        frozenset(declared_fields), frozenset(declared_methods),
        frozenset(references), frozenset(directly_implemented),
        tuple(sorted(field_flags)), tuple(sorted(method_flags)),
        class_access_flags)
