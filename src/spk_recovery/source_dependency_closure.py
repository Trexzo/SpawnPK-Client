"""Conservative explicit classfile dependency closure for private source islands.

Only constant-pool Class references and NameAndType/MethodType descriptors
are checked. Reflection, ServiceLoader, resources, strings and invokedynamic
bootstrap semantics are not declared closed by this check.
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


def explicit_class_references(data: bytes) -> set[str]:
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        raise SourceClosureError("PROJECT_CLOSURE_NOT_CLASSFILE")
    count = struct.unpack_from(">H", data, 8)[0]
    cursor = 10
    index = 1
    utf8: dict[int, str] = {}
    class_indexes: list[int] = []
    descriptor_indexes: list[int] = []

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
        "dynamic_class_loading_or_reflection_closed": False,
        "resources_or_native_dependencies_closed": False,
    }
