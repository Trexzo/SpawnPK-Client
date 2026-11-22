"""R463 read-only, one-class-lifetime Java 11 constant-pool byte decoding.

This module ONLY tokenizes constant-pool entries; R450, R453 and R458 must
continue independently validating each entry's semantic use (memberrefs,
signatures, bootstrap methods, handles and Code). No JVM execution, source
decompilation, owner path collection, archive mutation or persistent caching.

For the R459 evidence pass the very same immutable bytes object is given to
all three legacy parsers with an ephemeral CP view. A different-but-equal
bytes object or a different class is refused (no stale cache cross-talk).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MAX_CLASS_BYTES = 32 * 1024 * 1024
MAX_CP_COUNT = 65535
MAX_UTF8_BYTES = 65535
JAVA11_MAJOR = 55


class Refused(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


@dataclass(frozen=True, eq=False)
class Pool:
    """Unexported, immutable-indexed CP tokens tied to the original bytes."""
    raw: bytes
    major: int
    end: int
    count: int
    tags: tuple[int, ...]
    entries: tuple[Any, ...]

    def validate_for(self, raw: bytes) -> None:
        # Identity, not just equality: only one immutable byte source per
        # inspection. Never substitute a pool from another classfile.
        need(type(raw) is bytes and self.raw is raw and
             self.major == JAVA11_MAJOR and self.count == len(self.tags) ==
             len(self.entries) and 10 <= self.end <= len(raw),
             "R463_CONSTANT_POOL_VIEW_INPUT_MISMATCH")


def parse(raw: bytes) -> Pool:
    """Decode Java11 CP once with strict format/size bounds, no semantics.

    Constant-pool tags and placeholder slots are represented the same way
    as R450/R453/R458; float/int/long/double payloads are intentionally
    skipped because those parsers treat them as opaque (None). Original
    replaced-invalid-UTF8 decoding behavior is intentionally preserved.
    """
    need(type(raw) is bytes and 10 <= len(raw) <= MAX_CLASS_BYTES
         and raw[:4] == b"\xca\xfe\xba\xbe" and
         int.from_bytes(raw[6:8], "big") == JAVA11_MAJOR,
         "R463_EXACT_JAVA11_CLASS_BYTES_REQUIRED")
    pos = 8

    def read(size: int) -> bytes:
        nonlocal pos
        need(type(size) is int and 0 <= size <= len(raw) - pos,
             "R463_TRUNCATED_CONSTANT_POOL")
        piece = raw[pos:pos+size]
        pos += size
        return piece

    def u1() -> int:
        return read(1)[0]

    def u2() -> int:
        return int.from_bytes(read(2), "big")

    count = u2()
    need(1 <= count <= MAX_CP_COUNT, "R463_BAD_CONSTANT_POOL_COUNT")
    tags = [0] * count
    values: list[Any] = [None] * count
    idx = 1
    while idx < count:
        tag = u1()
        tags[idx] = tag
        if tag == 1:
            size = u2()
            need(size <= MAX_UTF8_BYTES, "R463_UTF8_TOO_LONG")
            values[idx] = read(size).decode("utf-8", "replace")
        elif tag in (3, 4):
            read(4)
        elif tag in (5, 6):
            read(8)
            need(idx + 1 < count, "R463_DOUBLE_SLOT_CP_OVERFLOW")
            idx += 1
        elif tag in (7, 8, 16, 19, 20):
            values[idx] = u2()
        elif tag in (9, 10, 11, 12, 17, 18):
            values[idx] = (u2(), u2())
        elif tag == 15:
            values[idx] = (u1(), u2())
        else:
            raise Refused("R463_UNSUPPORTED_CONSTANT_POOL_TAG")
        idx += 1
    return Pool(raw, JAVA11_MAJOR, pos, count, tuple(tags), tuple(values))
