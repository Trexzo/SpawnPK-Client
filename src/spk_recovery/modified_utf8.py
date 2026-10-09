from __future__ import annotations

"""Strict JVM CONSTANT_Utf8 Modified UTF-8 decoder.

The JVM classfile encoding is NOT standard UTF-8: U+0000 is C0 80, and
supplementary characters are encoded as pairs of three-byte UTF-16 surrogate
code units. Never replace undecodable bytes: a replacement can silently
collapse distinct constant-pool member or String referents into one value.
"""


class ModifiedUtf8Error(ValueError):
    pass


def decode_modified_utf8(data: bytes) -> str:
    if not isinstance(data, bytes):
        raise ModifiedUtf8Error("modified UTF-8 input must be bytes")
    utf16 = bytearray()
    offset = 0
    while offset < len(data):
        first = data[offset]
        if 1 <= first <= 0x7F:
            code_unit = first
            offset += 1
        elif first == 0xC0:
            if offset + 1 >= len(data) or data[offset + 1] != 0x80:
                raise ModifiedUtf8Error("invalid modified NUL escape")
            code_unit = 0
            offset += 2
        elif 0xC2 <= first <= 0xDF:
            if offset + 1 >= len(data):
                raise ModifiedUtf8Error("truncated two-byte code unit")
            second = data[offset + 1]
            if second & 0xC0 != 0x80:
                raise ModifiedUtf8Error("invalid two-byte continuation")
            code_unit = ((first & 0x1F) << 6) | (second & 0x3F)
            offset += 2
        elif 0xE0 <= first <= 0xEF:
            if offset + 2 >= len(data):
                raise ModifiedUtf8Error("truncated three-byte code unit")
            second, third = data[offset + 1], data[offset + 2]
            if second & 0xC0 != 0x80 or third & 0xC0 != 0x80:
                raise ModifiedUtf8Error("invalid three-byte continuation")
            code_unit = (
                ((first & 0x0F) << 12)
                | ((second & 0x3F) << 6)
                | (third & 0x3F)
            )
            if code_unit < 0x800:
                raise ModifiedUtf8Error("overlong three-byte code unit")
            offset += 3
        else:
            # Includes raw zero, stray continuation bytes, C1 overlong
            # sequences, four-byte UTF-8 and all invalid lead bytes.
            raise ModifiedUtf8Error("invalid modified UTF-8 lead byte")
        utf16.extend(code_unit.to_bytes(2, "big"))

    try:
        # Reject lone surrogates instead of substituting a replacement
        # character. A class requiring unsupported lone surrogate content
        # is not eligible for exact identity-proof comparisons.
        return utf16.decode("utf-16-be", errors="strict")
    except UnicodeDecodeError as exc:
        raise ModifiedUtf8Error("unpaired UTF-16 surrogate code unit") from exc
