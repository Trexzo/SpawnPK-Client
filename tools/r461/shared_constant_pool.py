"""R461 ephemeral immutable JVM constant-pool index for reconstructed Java 11.

Pure in-memory decoding; no filesystem, cache, Java loading or private names
are serialized. The input bytes MUST be the same exact immutable bytes object
supplied to each consuming parser. Independent legacy decoders are unchanged
when an index is not supplied.
"""
from __future__ import annotations

from dataclasses import dataclass

MAX_BYTES = 32 * 1024 * 1024


class Refused(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise Refused(code)


@dataclass(frozen=True)
class Index:
    raw: bytes
    count: int
    tags: tuple[int, ...]
    entries: tuple[object | None, ...]
    end_offset: int


def decode(raw: bytes) -> Index:
    need(type(raw) is bytes and 10 <= len(raw) <= MAX_BYTES
         and raw[:4] == b"\xca\xfe\xba\xbe"
         and int.from_bytes(raw[6:8], "big") == 55,
         "R461_JAVA11_CLASS_REQUIRED")
    pos = 8

    def take(n: int) -> bytes:
        nonlocal pos
        need(0 <= n <= len(raw) - pos, "R461_TRUNCATED_CONSTANT_POOL")
        result = raw[pos:pos + n]
        pos += n
        return result

    def u1() -> int:
        return take(1)[0]

    def u2() -> int:
        return int.from_bytes(take(2), "big")

    count = u2()
    need(1 <= count <= 65535, "R461_INVALID_CP_COUNT")
    tags = [0] * count
    entries: list[object | None] = [None] * count
    i = 1
    while i < count:
        tag = u1()
        tags[i] = tag
        if tag == 1:
            entries[i] = take(u2()).decode("utf-8", "replace")
        elif tag in (3, 4):
            take(4)
        elif tag in (5, 6):
            take(8)
            i += 1  # second slot reserved, same representation as R450/453/458
        elif tag in (7, 8, 16, 19, 20):
            entries[i] = u2()
        elif tag in (9, 10, 11, 12, 17, 18):
            entries[i] = (u2(), u2())
        elif tag == 15:
            entries[i] = (u1(), u2())
        else:
            raise Refused("R461_UNKNOWN_CP_TAG")
        i += 1
    return Index(raw, count, tuple(tags), tuple(entries), pos)


def admit(index: Index, raw: bytes) -> tuple[int, tuple[int, ...],
                                             tuple[object | None, ...], int]:
    """Reject wrong/stale/mutable/cross-class indices before reuse.

    Identity is intentionally stronger than equality: only the exact bytes
    object initially scanned and SHA-admitted by R459 can reuse this index.
    """
    need(type(index) is Index and type(raw) is bytes
         and raw is index.raw and 10 <= index.end_offset <= len(raw)
         and index.count == int.from_bytes(raw[8:10], "big")
         and index.count == len(index.tags) == len(index.entries)
         and index.tags[0] == 0,
         "R461_SHARED_INDEX_INPUT_MISMATCH")
    return index.count, index.tags, index.entries, index.end_offset
