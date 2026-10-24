"""Conservative explicit classfile dependency closure for private source islands.

Inspects constant-pool Class and NameAndType/MethodType references,
as well as OWN field/method declaration descriptors and generic Signature
attributes. Reflection, ServiceLoader, unparsed annotation formats, resources,
strings and invokedynamic bootstrap semantics are NOT declared closed.
"""
from __future__ import annotations

import re
import struct
from typing import Any
import zipfile

from .modified_utf8 import ModifiedUtf8Error, decode_modified_utf8


class SourceClosureError(ValueError):
    pass


_NAME = re.compile(
    r"rs/(?:[A-Za-z_$][A-Za-z_$0-9]*/)*[A-Za-z_$][A-Za-z_$0-9]*\Z"
)
_DESCRIPTOR = re.compile(
    r"L(rs/(?:[A-Za-z_$][A-Za-z_$0-9]*/)*[A-Za-z_$][A-Za-z_$0-9]*);"
)
# Generic Signature attributes may put '<...>' after the owner type; member
# signatures sometimes use '.' to denote an inner source class.
_GENERIC_TYPE = re.compile(
    r"L(rs/(?:[A-Za-z_$][A-Za-z_$0-9]*/)*[A-Za-z_$][A-Za-z_$0-9]*(?:\.[A-Za-z_$][A-Za-z_$0-9]*)*)(?=[;<])"
)


def explicit_class_references(data: bytes) -> set[str]:
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        raise SourceClosureError("PROJECT_CLOSURE_NOT_CLASSFILE")
    count = struct.unpack_from(">H", data, 8)[0]
    cursor = 10
    index = 1
    utf8: dict[int, str] = {}
    class_indexes: list[int] = []
    descriptor_indexes: list[int] = []
    signature_indexes: list[int] = []

    def take(size: int) -> bytes:
        nonlocal cursor
        if cursor + size > len(data):
            raise SourceClosureError("PROJECT_CLOSURE_TRUNCATED_CONSTANT_POOL")
        part = data[cursor:cursor + size]
        cursor += size
        return part

    def u2() -> int:
        return struct.unpack(">H", take(2))[0]

    while index < count:
        tag = take(1)[0]
        if tag == 1:
            size = u2()
            try:
                utf8[index] = decode_modified_utf8(take(size))
            except ModifiedUtf8Error as exc:
                raise SourceClosureError(
                    "PROJECT_CLOSURE_INVALID_MODIFIED_UTF8"
                ) from exc
        elif tag in (3, 4):
            take(4)
        elif tag in (5, 6):
            take(8)
            index += 1
        elif tag == 7:
            class_indexes.append(u2())
        elif tag in (8, 19, 20):
            take(2)
        elif tag in (9, 10, 11, 17, 18):
            take(4)
        elif tag == 12:
            take(2)
            descriptor_indexes.append(u2())
        elif tag == 16:
            descriptor_indexes.append(u2())
        elif tag == 15:
            take(3)
        else:
            raise SourceClosureError("PROJECT_CLOSURE_UNSUPPORTED_CP_TAG")
        index += 1

    # Classfile declaration descriptors do NOT need a CONSTANT_Class or
    # NameAndType entry. Missing this step can falsely declare e.g. original
    # rs/n.class closed, despite its own fields being Lrs/a/a;.
    take(2)  # class access_flags
    take(2)  # this_class
    take(2)  # super_class
    for _ in range(u2()):  # interfaces
        take(2)

    def read_attributes() -> None:
        for _ in range(u2()):
            name_index = u2()
            name = utf8.get(name_index)
            if name is None:
                raise SourceClosureError("PROJECT_CLOSURE_BAD_ATTRIBUTE_NAME")
            length = struct.unpack(">I", take(4))[0]
            if name == "Signature":
                if length != 2:
                    raise SourceClosureError("PROJECT_CLOSURE_BAD_SIGNATURE_ATTRIBUTE")
                signature_indexes.append(u2())
            else:
                take(length)

    for _ in range(u2()):  # fields
        take(2)  # access_flags
        take(2)  # name_index
        descriptor_indexes.append(u2())
        read_attributes()
    for _ in range(u2()):  # methods
        take(2)
        take(2)
        descriptor_indexes.append(u2())
        read_attributes()
    read_attributes()  # class Signature
    if cursor != len(data):
        raise SourceClosureError("PROJECT_CLOSURE_CLASSFILE_TRAILING_BYTES")

    refs: set[str] = set()
    for reference_index in class_indexes:
        name = utf8.get(reference_index)
        if name is None:
            raise SourceClosureError("PROJECT_CLOSURE_BAD_CLASS_INDEX")
        names = ([name] if name.startswith("rs/") else [])
        names += _DESCRIPTOR.findall(name)
        for internal_name in names:
            if not _NAME.fullmatch(internal_name):
                raise SourceClosureError("PROJECT_CLOSURE_BAD_INTERNAL_NAME")
            refs.add(internal_name + ".class")
    for reference_index in descriptor_indexes:
        desc = utf8.get(reference_index)
        if desc is None:
            raise SourceClosureError("PROJECT_CLOSURE_BAD_DESCRIPTOR_INDEX")
        for internal_name in _DESCRIPTOR.findall(desc):
            if not _NAME.fullmatch(internal_name):
                raise SourceClosureError("PROJECT_CLOSURE_BAD_INTERNAL_NAME")
            refs.add(internal_name + ".class")
    for reference_index in signature_indexes:
        signature = utf8.get(reference_index)
        if signature is None:
            raise SourceClosureError("PROJECT_CLOSURE_BAD_SIGNATURE_INDEX")
        for source_name in _GENERIC_TYPE.findall(signature):
            internal_name = source_name.replace(".", "$")
            if not _NAME.fullmatch(internal_name):
                raise SourceClosureError("PROJECT_CLOSURE_BAD_INTERNAL_NAME")
            refs.add(internal_name + ".class")
    return refs


def require_selected_source_closure(
    archive: zipfile.ZipFile, selected: set[str],
) -> dict[str, Any]:
    """Fail before javac on explicit rs/ references outside selected classes."""
    edges = 0
    for name in sorted(selected):
        try:
            references = explicit_class_references(archive.read(name)) - {name}
        except KeyError as exc:
            raise SourceClosureError(
                "PROJECT_CLOSURE_SELECTED_CLASS_MISSING"
            ) from exc
        edges += len(references)
        if references - selected:
            raise SourceClosureError(
                "PROJECT_SOURCE_DEPENDENCY_OUTSIDE_SELECTION"
            )
    return {
        "selected_classes": len(selected),
        "source_project_dependency_edges": edges,
        "explicit_project_class_closure": True,
        "member_declaration_descriptors_checked": True,
        "generic_signature_metadata_checked": True,
        "dynamic_class_loading_or_reflection_closed": False,
        "resources_or_native_dependencies_closed": False,
    }
