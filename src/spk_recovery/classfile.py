from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import struct
from typing import Any


class ClassFormatError(ValueError):
    pass


def _u1(f: io.BytesIO) -> int:
    b = f.read(1)
    if len(b) != 1:
        raise ClassFormatError("unexpected EOF reading u1")
    return b[0]


def _u2(f: io.BytesIO) -> int:
    b = f.read(2)
    if len(b) != 2:
        raise ClassFormatError("unexpected EOF reading u2")
    return struct.unpack(">H", b)[0]


def _u4(f: io.BytesIO) -> int:
    b = f.read(4)
    if len(b) != 4:
        raise ClassFormatError("unexpected EOF reading u4")
    return struct.unpack(">I", b)[0]


def _take(f: io.BytesIO, n: int) -> bytes:
    b = f.read(n)
    if len(b) != n:
        raise ClassFormatError(f"unexpected EOF reading {n} bytes")
    return b


def _descriptor_shape(desc: str) -> str:
    """Normalize reference types so package/class renames do not dominate matching."""
    out: list[str] = []
    i = 0
    while i < len(desc):
        ch = desc[i]
        if ch == "L":
            semi = desc.find(";", i)
            if semi < 0:
                return desc
            out.append("L;")
            i = semi + 1
        elif ch == "[":
            out.append("[")
            i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


@dataclass
class ParsedClass:
    name: str
    major: int
    minor: int
    access: int
    super_name: str | None
    interfaces: list[str]
    utf8_strings: list[str]
    literal_strings: list[str]
    numeric_constants: list[int | float]
    fields: list[dict[str, Any]]
    methods: list[dict[str, Any]]
    attributes: list[str]
    inner_outer_name: str | None
    inner_simple_name: str | None
    enclosing_class_name: str | None

    def structural_payload(self) -> dict[str, Any]:
        # Deliberately excludes obfuscated class/member names.
        return {
            "major": self.major,
            "access": self.access,
            "interface_count": len(self.interfaces),
            "field_shapes": sorted((f["access"], _descriptor_shape(f["descriptor"])) for f in self.fields),
            "method_shapes": sorted(
                (m["access"], _descriptor_shape(m["descriptor"]), m.get("code_length"))
                for m in self.methods
                if m["name"] not in ("<init>", "<clinit>")
            ),
            "literal_strings": sorted(set(self.literal_strings)),
            "numeric_constants": sorted(self.numeric_constants, key=lambda x: (type(x).__name__, repr(x))),
        }

    def structural_sha256(self) -> str:
        import json
        raw = json.dumps(self.structural_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def parse_class(data: bytes) -> ParsedClass:
    f = io.BytesIO(data)
    if _u4(f) != 0xCAFEBABE:
        raise ClassFormatError("not a JVM class")
    minor = _u2(f)
    major = _u2(f)
    cp_count = _u2(f)
    cp: list[Any] = [None] * cp_count
    i = 1
    while i < cp_count:
        tag = _u1(f)
        if tag == 1:
            n = _u2(f)
            cp[i] = (tag, _take(f, n).decode("utf-8", errors="replace"))
        elif tag == 3:
            cp[i] = (tag, struct.unpack(">i", _take(f, 4))[0])
        elif tag == 4:
            cp[i] = (tag, struct.unpack(">f", _take(f, 4))[0])
        elif tag == 5:
            cp[i] = (tag, struct.unpack(">q", _take(f, 8))[0]); i += 1
        elif tag == 6:
            cp[i] = (tag, struct.unpack(">d", _take(f, 8))[0]); i += 1
        elif tag in (7, 8, 16, 19, 20):
            cp[i] = (tag, _u2(f))
        elif tag in (9, 10, 11, 12, 17, 18):
            cp[i] = (tag, _u2(f), _u2(f))
        elif tag == 15:
            cp[i] = (tag, _u1(f), _u2(f))
        else:
            raise ClassFormatError(f"unknown constant-pool tag {tag} at #{i}")
        i += 1

    def utf8(idx: int) -> str:
        x = cp[idx]
        if not x or x[0] != 1:
            raise ClassFormatError(f"cp#{idx} is not Utf8")
        return x[1]

    def class_name(idx: int) -> str | None:
        if idx == 0:
            return None
        x = cp[idx]
        if not x or x[0] != 7:
            raise ClassFormatError(f"cp#{idx} is not Class")
        return utf8(x[1])

    access = _u2(f)
    this_class = _u2(f)
    super_class = _u2(f)
    interface_count = _u2(f)
    interfaces = [class_name(_u2(f)) or "" for _ in range(interface_count)]

    def read_attributes() -> tuple[list[str], int | None]:
        names: list[str] = []
        code_length: int | None = None
        count = _u2(f)
        for _ in range(count):
            name = utf8(_u2(f))
            n = _u4(f)
            payload = _take(f, n)
            names.append(name)
            if name == "Code" and len(payload) >= 8:
                # max_stack:u2, max_locals:u2, code_length:u4
                code_length = struct.unpack_from(">I", payload, 4)[0]
        return names, code_length

    fields: list[dict[str, Any]] = []
    for _ in range(_u2(f)):
        a = _u2(f); name = utf8(_u2(f)); desc = utf8(_u2(f)); attrs, _ = read_attributes()
        fields.append({"access": a, "name": name, "descriptor": desc, "attributes": attrs})

    methods: list[dict[str, Any]] = []
    for _ in range(_u2(f)):
        a = _u2(f); name = utf8(_u2(f)); desc = utf8(_u2(f)); attrs, code_len = read_attributes()
        methods.append({"access": a, "name": name, "descriptor": desc, "attributes": attrs, "code_length": code_len})

    class_attrs: list[str] = []
    inner_outer_name: str | None = None
    inner_simple_name: str | None = None
    enclosing_class_name: str | None = None
    for _ in range(_u2(f)):
        attr_name = utf8(_u2(f))
        n = _u4(f)
        payload = _take(f, n)
        class_attrs.append(attr_name)
        if attr_name == "InnerClasses" and len(payload) >= 2:
            af = io.BytesIO(payload)
            for _ in range(_u2(af)):
                inner_index = _u2(af)
                outer_index = _u2(af)
                inner_name_index = _u2(af)
                _inner_access = _u2(af)
                inner_name = class_name(inner_index)
                if inner_name == (class_name(this_class) or ""):
                    inner_simple_name = (
                        utf8(inner_name_index) if inner_name_index else None
                    )
                    if outer_index:
                        inner_outer_name = class_name(outer_index)
        elif attr_name == "EnclosingMethod" and len(payload) == 4:
            af = io.BytesIO(payload)
            enclosing_class_name = class_name(_u2(af))
            _u2(af)

    utf8_values = [x[1] for x in cp if x and x[0] == 1]
    literal_strings: list[str] = []
    numeric: list[int | float] = []
    for x in cp:
        if not x:
            continue
        if x[0] == 8:
            try:
                literal_strings.append(utf8(x[1]))
            except ClassFormatError:
                pass
        elif x[0] in (3, 4, 5, 6):
            numeric.append(x[1])

    return ParsedClass(
        name=class_name(this_class) or "",
        major=major,
        minor=minor,
        access=access,
        super_name=class_name(super_class),
        interfaces=interfaces,
        utf8_strings=utf8_values,
        literal_strings=literal_strings,
        numeric_constants=numeric,
        fields=fields,
        methods=methods,
        attributes=class_attrs,
        inner_outer_name=inner_outer_name,
        inner_simple_name=inner_simple_name,
        enclosing_class_name=enclosing_class_name,
    )
