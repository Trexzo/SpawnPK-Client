from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct
from typing import Iterable
import zipfile

from .classfile import ClassFormatError, parse_class


class ClassfileRemapError(ValueError):
    pass


@dataclass(frozen=True)
class RemapResult:
    data: bytes
    utf8_entry_count: int
    changed_utf8_entry_count: int
    replacement_count: int


def _u1(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 1 > len(data):
        raise ClassfileRemapError("unexpected EOF reading u1")
    return data[offset], offset + 1


def _u2(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 2 > len(data):
        raise ClassfileRemapError("unexpected EOF reading u2")
    return struct.unpack_from(">H", data, offset)[0], offset + 2


def _take(
    data: bytes,
    offset: int,
    size: int,
) -> tuple[bytes, int]:
    end = offset + size
    if end > len(data):
        raise ClassfileRemapError(
            f"unexpected EOF reading {size} bytes"
        )
    return data[offset:end], end


def _mapping_bytes(
    mapping: dict[str, str],
) -> list[tuple[bytes, bytes]]:
    rows: list[tuple[bytes, bytes]] = []
    seen_targets: set[str] = set()

    for old, new in sorted(
        mapping.items(),
        key=lambda item: (-len(item[0]), item[0]),
    ):
        if not old or not new:
            raise ClassfileRemapError(
                "class remap names must be non-empty"
            )
        if old == new:
            continue
        if old.startswith("/") or old.endswith("/"):
            raise ClassfileRemapError(
                "class remap identity must not start/end with '/'"
            )
        if new.startswith("/") or new.endswith("/"):
            raise ClassfileRemapError(
                "class remap target must not start/end with '/'"
            )
        try:
            old_b = old.encode("ascii")
            new_b = new.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ClassfileRemapError(
                "class remap identities must be ASCII"
            ) from exc
        if new in seen_targets:
            raise ClassfileRemapError(
                "class remap targets must be unique"
            )
        seen_targets.add(new)
        rows.append((old_b, new_b))

    return rows


_LEFT_BOUNDARY = frozenset(b"L[(:;+-")
_RIGHT_BOUNDARY = frozenset(b";<.$:)")


def _replace_identity(
    payload: bytes,
    old: bytes,
    new: bytes,
) -> tuple[bytes, int]:
    if payload == old:
        return new, 1

    out = bytearray()
    cursor = 0
    replacements = 0

    while True:
        index = payload.find(old, cursor)
        if index < 0:
            out += payload[cursor:]
            break

        end = index + len(old)
        left_ok = (
            index == 0
            or payload[index - 1] in _LEFT_BOUNDARY
        )
        right_ok = (
            end == len(payload)
            or payload[end] in _RIGHT_BOUNDARY
        )

        if left_ok and right_ok:
            out += payload[cursor:index]
            out += new
            cursor = end
            replacements += 1
        else:
            out += payload[cursor:index + 1]
            cursor = index + 1

    return bytes(out), replacements


def _remap_utf8_payload(
    payload: bytes,
    mapping: list[tuple[bytes, bytes]],
) -> tuple[bytes, int]:
    current = payload
    total = 0
    for old, new in mapping:
        current, count = _replace_identity(
            current,
            old,
            new,
        )
        total += count
    return current, total


def _constant_string_utf8_indexes(
    data: bytes,
) -> set[int]:
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        raise ClassfileRemapError("not a JVM classfile")

    cp_count = struct.unpack_from(">H", data, 8)[0]
    offset = 10
    index = 1
    string_utf8_indexes: set[int] = set()

    while index < cp_count:
        tag, offset = _u1(data, offset)

        if tag == 1:
            size, offset = _u2(data, offset)
            _payload, offset = _take(data, offset, size)
        elif tag in (3, 4):
            _raw, offset = _take(data, offset, 4)
        elif tag in (5, 6):
            _raw, offset = _take(data, offset, 8)
            index += 1
        elif tag in (7, 16, 19, 20):
            _raw, offset = _take(data, offset, 2)
        elif tag == 8:
            utf8_index, offset = _u2(data, offset)
            string_utf8_indexes.add(utf8_index)
        elif tag in (9, 10, 11, 12, 17, 18):
            _raw, offset = _take(data, offset, 4)
        elif tag == 15:
            _raw, offset = _take(data, offset, 3)
        else:
            raise ClassfileRemapError(
                f"unknown constant-pool tag {tag} at #{index}"
            )

        index += 1

    return string_utf8_indexes


def remap_classfile_utf8(
    data: bytes,
    mapping: dict[str, str],
) -> RemapResult:
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        raise ClassfileRemapError("not a JVM classfile")

    rows = _mapping_bytes(mapping)
    if not rows:
        return RemapResult(
            data=data,
            utf8_entry_count=0,
            changed_utf8_entry_count=0,
            replacement_count=0,
        )

    cp_count = struct.unpack_from(">H", data, 8)[0]
    string_utf8_indexes = _constant_string_utf8_indexes(data)
    offset = 10
    out = bytearray(data[:10])
    index = 1
    utf8_count = 0
    changed_utf8_count = 0
    replacement_count = 0

    while index < cp_count:
        tag, offset = _u1(data, offset)
        out.append(tag)

        if tag == 1:
            utf8_count += 1
            size, offset = _u2(data, offset)
            payload, offset = _take(data, offset, size)
            remapped, count = _remap_utf8_payload(
                payload,
                rows,
            )
            if len(remapped) > 0xFFFF:
                raise ClassfileRemapError(
                    "remapped UTF8 constant exceeds u2 length"
                )
            if count:
                if index in string_utf8_indexes:
                    raise ClassfileRemapError(
                        "refusing to rewrite class identity inside "
                        "CONSTANT_String literal"
                    )
                changed_utf8_count += 1
                replacement_count += count
            out += struct.pack(">H", len(remapped))
            out += remapped
        elif tag in (3, 4):
            raw, offset = _take(data, offset, 4)
            out += raw
        elif tag in (5, 6):
            raw, offset = _take(data, offset, 8)
            out += raw
            index += 1
        elif tag in (7, 8, 16, 19, 20):
            raw, offset = _take(data, offset, 2)
            out += raw
        elif tag in (9, 10, 11, 12, 17, 18):
            raw, offset = _take(data, offset, 4)
            out += raw
        elif tag == 15:
            raw, offset = _take(data, offset, 3)
            out += raw
        else:
            raise ClassfileRemapError(
                f"unknown constant-pool tag {tag} at #{index}"
            )

        index += 1

    out += data[offset:]
    result = bytes(out)

    try:
        parse_class(result)
    except ClassFormatError as exc:
        raise ClassfileRemapError(
            f"remapped classfile failed to parse: {exc}"
        ) from exc

    return RemapResult(
        data=result,
        utf8_entry_count=utf8_count,
        changed_utf8_entry_count=changed_utf8_count,
        replacement_count=replacement_count,
    )


def _remap_internal_name(
    name: str,
    mapping: dict[str, str],
) -> str:
    if name in mapping:
        return mapping[name]

    for old, new in sorted(
        mapping.items(),
        key=lambda item: (-len(item[0]), item[0]),
    ):
        if name.startswith(old + "$"):
            return new + name[len(old):]
    return name


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name)
    info.date_time = (1980, 1, 1, 0, 0, 0)
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o644 << 16
    return info


def remap_jar(
    source: Path,
    destination: Path,
    mapping: dict[str, str],
) -> dict[str, int | str]:
    source = source.resolve()
    destination = destination.resolve()
    if not source.is_file():
        raise ClassfileRemapError(
            f"source JAR does not exist: {source}"
        )

    rows = _mapping_bytes(mapping)
    if not rows:
        raise ClassfileRemapError(
            "JAR remap requires at least one changed identity"
        )

    output_entries: dict[str, bytes] = {}
    class_count = 0
    changed_class_count = 0
    replacement_count = 0

    try:
        with zipfile.ZipFile(source) as z:
            infos = [
                info
                for info in z.infolist()
                if not info.is_dir()
            ]
            source_class_names = {
                info.filename[:-6]
                for info in infos
                if (
                    info.filename.endswith(".class")
                    and not info.filename.startswith("META-INF/")
                )
            }
            missing_sources = sorted(
                old
                for old in mapping
                if old not in source_class_names
            )
            if missing_sources:
                raise ClassfileRemapError(
                    "remap source identities absent from JAR: "
                    + str(len(missing_sources))
                )

            for info in sorted(
                infos,
                key=lambda row: row.filename,
            ):
                name = info.filename
                data = z.read(info)

                if (
                    name.endswith(".class")
                    and not name.startswith("META-INF/")
                ):
                    class_count += 1
                    internal = name[:-6]
                    target_internal = _remap_internal_name(
                        internal,
                        mapping,
                    )
                    remapped = remap_classfile_utf8(
                        data,
                        mapping,
                    )
                    data = remapped.data
                    replacement_count += (
                        remapped.replacement_count
                    )
                    target_name = target_internal + ".class"
                    if (
                        target_name != name
                        or remapped.replacement_count
                    ):
                        changed_class_count += 1
                    name = target_name

                if name in output_entries:
                    raise ClassfileRemapError(
                        f"remap output entry collision: {name}"
                    )
                output_entries[name] = data
    except zipfile.BadZipFile as exc:
        raise ClassfileRemapError(
            f"invalid source JAR: {source}"
        ) from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        destination,
        "w",
        zipfile.ZIP_STORED,
    ) as z:
        for name in sorted(output_entries):
            z.writestr(
                _zip_info(name),
                output_entries[name],
            )

    return {
        "source_sha256": hashlib.sha256(
            source.read_bytes()
        ).hexdigest(),
        "destination_sha256": hashlib.sha256(
            destination.read_bytes()
        ).hexdigest(),
        "class_count": class_count,
        "changed_class_count": changed_class_count,
        "replacement_count": replacement_count,
    }


def assert_no_literal_alias_mentions(
    classfiles: Iterable[bytes],
    aliases: Iterable[str],
) -> None:
    alias_values = tuple(sorted(set(aliases)))
    for data in classfiles:
        try:
            parsed = parse_class(data)
        except ClassFormatError as exc:
            raise ClassfileRemapError(
                f"generated class parse failed: {exc}"
            ) from exc

        for literal in parsed.literal_strings:
            for alias in alias_values:
                if (
                    alias in literal
                    or alias.replace("/", ".") in literal
                ):
                    raise ClassfileRemapError(
                        "generated class literal contains compile-only alias"
                    )



def assert_no_utf8_alias_references(
    classfiles: Iterable[bytes],
    aliases: Iterable[str],
) -> None:
    alias_values = tuple(sorted(set(aliases)))
    for data in classfiles:
        try:
            parsed = parse_class(data)
        except ClassFormatError as exc:
            raise ClassfileRemapError(
                f"generated class parse failed: {exc}"
            ) from exc

        for value in parsed.utf8_strings:
            payload = value.encode(
                "utf-8",
                errors="surrogatepass",
            )
            for alias in alias_values:
                old = alias.encode("ascii")
                _ignored, count = _replace_identity(
                    payload,
                    old,
                    old,
                )
                if count:
                    raise ClassfileRemapError(
                        "generated class retains compile-only alias reference"
                    )
