from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
from typing import Any
import zipfile

from .classfile import ClassFormatError, parse_class
from .namespace_collision import analyze_namespace_collisions


class CollisionBytecodeRemapError(ValueError):
    pass


_SIGNED_SUFFIXES = (".SF", ".RSA", ".DSA", ".EC")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _u2(data: bytes, offset: int) -> int:
    if offset + 2 > len(data):
        raise CollisionBytecodeRemapError(
            "unexpected EOF reading u2"
        )
    return struct.unpack_from(">H", data, offset)[0]


def _cp_layout(
    data: bytes,
) -> tuple[
    int,
    list[dict[str, Any] | None],
    set[int],
    int,
]:
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        raise CollisionBytecodeRemapError("not a JVM class")

    cp_count = _u2(data, 8)
    entries: list[dict[str, Any] | None] = [None] * cp_count
    string_utf8_indices: set[int] = set()
    offset = 10
    index = 1

    while index < cp_count:
        if offset >= len(data):
            raise CollisionBytecodeRemapError(
                "unexpected EOF in constant pool"
            )
        start = offset
        tag = data[offset]
        offset += 1

        if tag == 1:
            n = _u2(data, offset)
            offset += 2
            if offset + n > len(data):
                raise CollisionBytecodeRemapError(
                    "unexpected EOF in CONSTANT_Utf8"
                )
            payload = data[offset:offset + n]
            offset += n
            entries[index] = {
                "tag": tag,
                "raw": data[start:offset],
                "payload": payload,
            }
        elif tag in (3, 4):
            offset += 4
            entries[index] = {
                "tag": tag,
                "raw": data[start:offset],
            }
        elif tag in (5, 6):
            offset += 8
            entries[index] = {
                "tag": tag,
                "raw": data[start:offset],
            }
            index += 1
        elif tag == 7:
            utf8_index = _u2(data, offset)
            offset += 2
            entries[index] = {
                "tag": tag,
                "raw": data[start:offset],
                "utf8_index": utf8_index,
            }
        elif tag in (16, 19, 20):
            offset += 2
            entries[index] = {
                "tag": tag,
                "raw": data[start:offset],
            }
        elif tag == 8:
            utf8_index = _u2(data, offset)
            offset += 2
            string_utf8_indices.add(utf8_index)
            entries[index] = {
                "tag": tag,
                "raw": data[start:offset],
                "utf8_index": utf8_index,
            }
        elif tag in (9, 10, 11, 12, 17, 18):
            offset += 4
            entries[index] = {
                "tag": tag,
                "raw": data[start:offset],
            }
        elif tag == 15:
            offset += 3
            entries[index] = {
                "tag": tag,
                "raw": data[start:offset],
            }
        else:
            raise CollisionBytecodeRemapError(
                f"unsupported constant-pool tag {tag} at #{index}"
            )

        if offset > len(data):
            raise CollisionBytecodeRemapError(
                "unexpected EOF in constant pool"
            )
        index += 1

    return cp_count, entries, string_utf8_indices, offset


def _rewrite_utf8_payload(
    payload: bytes,
    mappings: dict[str, str],
    *,
    rewrite_exact: bool = True,
) -> bytes:
    result = payload

    # Longest source names first so an expanded nested family wins over
    # its outer-class prefix.
    ordered = sorted(
        mappings.items(),
        key=lambda item: (-len(item[0]), item[0]),
    )
    for old, new in ordered:
        old_b = old.encode("ascii")
        new_b = new.encode("ascii")

        if rewrite_exact and result == old_b:
            result = new_b
            continue

        for suffix in (b";", b"<", b".", b"$"):
            needle = b"L" + old_b + suffix
            replacement = b"L" + new_b + suffix
            result = result.replace(needle, replacement)

    return result


def remap_class_bytes(
    data: bytes,
    mappings: dict[str, str],
) -> tuple[bytes, int]:
    cp_count, entries, string_utf8_indices, tail_offset = (
        _cp_layout(data)
    )

    # Exact internal class names are unsafe to rewrite by mutating their
    # shared CONSTANT_Utf8 in place. The same Utf8 value may also be used
    # as an ordinary field/method name. Instead, clone only the renamed
    # class identity and retarget CONSTANT_Class to the clone.
    class_alias_payload_by_utf8: dict[int, bytes] = {}
    for index in range(1, cp_count):
        entry = entries[index]
        if entry is None or entry["tag"] != 7:
            continue
        utf8_index = int(entry["utf8_index"])
        utf8_entry = entries[utf8_index]
        if utf8_entry is None or utf8_entry["tag"] != 1:
            raise CollisionBytecodeRemapError(
                "CONSTANT_Class does not reference CONSTANT_Utf8"
            )
        payload = utf8_entry["payload"]
        try:
            internal = payload.decode("ascii")
        except UnicodeDecodeError:
            continue
        replacement = mappings.get(internal)
        if replacement is None:
            continue
        new_payload = replacement.encode("ascii")
        if len(new_payload) > 0xFFFF:
            raise CollisionBytecodeRemapError(
                "rewritten class-name CONSTANT_Utf8 exceeds JVM u2 length"
            )
        existing = class_alias_payload_by_utf8.get(utf8_index)
        if existing is not None and existing != new_payload:
            raise CollisionBytecodeRemapError(
                "shared CONSTANT_Class Utf8 requires conflicting remaps"
            )
        class_alias_payload_by_utf8[utf8_index] = new_payload

    # Descriptors/signatures may contain class identities inside larger
    # Utf8 payloads. Rewrite those structurally, but do not exact-rewrite
    # a bare Utf8 token: bare class identities are handled above.
    rewrites: dict[int, bytes] = {}
    for index in range(1, cp_count):
        entry = entries[index]
        if entry is None or entry["tag"] != 1:
            continue

        old_payload = entry["payload"]
        new_payload = _rewrite_utf8_payload(
            old_payload,
            mappings,
            rewrite_exact=False,
        )
        if new_payload == old_payload:
            continue
        if len(new_payload) > 0xFFFF:
            raise CollisionBytecodeRemapError(
                "rewritten CONSTANT_Utf8 exceeds JVM u2 length"
            )
        rewrites[index] = new_payload

    # Descriptor/signature Utf8 constants can also be shared by
    # CONSTANT_String. Preserve runtime string literals by cloning the
    # original Utf8 and retargeting the string constant to the clone.
    string_alias_sources = sorted(
        set(rewrites) & string_utf8_indices
    )

    class_alias_sources = sorted(class_alias_payload_by_utf8)
    added_count = len(class_alias_sources) + len(string_alias_sources)
    if cp_count + added_count > 0xFFFF:
        raise CollisionBytecodeRemapError(
            "collision remap aliases exceed JVM constant-pool limit"
        )

    class_alias_index_by_utf8 = {
        source_index: cp_count + offset
        for offset, source_index in enumerate(class_alias_sources)
    }
    string_alias_base = cp_count + len(class_alias_sources)
    string_alias_index_by_utf8 = {
        source_index: string_alias_base + offset
        for offset, source_index in enumerate(string_alias_sources)
    }

    encoded_entries: list[bytes] = []
    for index in range(1, cp_count):
        entry = entries[index]
        if entry is None:
            continue

        if entry["tag"] == 1:
            new_payload = rewrites.get(index)
            if new_payload is None:
                encoded_entries.append(entry["raw"])
                continue
            encoded_entries.append(
                bytes([1])
                + struct.pack(">H", len(new_payload))
                + new_payload
            )
            continue

        if entry["tag"] == 7:
            source_index = int(entry["utf8_index"])
            alias_index = class_alias_index_by_utf8.get(source_index)
            if alias_index is not None:
                encoded_entries.append(
                    bytes([7])
                    + struct.pack(">H", alias_index)
                )
                continue

        if entry["tag"] == 8:
            source_index = int(entry["utf8_index"])
            alias_index = string_alias_index_by_utf8.get(source_index)
            if alias_index is not None:
                encoded_entries.append(
                    bytes([8])
                    + struct.pack(">H", alias_index)
                )
                continue

        encoded_entries.append(entry["raw"])

    alias_entries: list[bytes] = []

    for source_index in class_alias_sources:
        payload = class_alias_payload_by_utf8[source_index]
        alias_entries.append(
            bytes([1])
            + struct.pack(">H", len(payload))
            + payload
        )

    for source_index in string_alias_sources:
        entry = entries[source_index]
        if entry is None or entry["tag"] != 1:
            raise CollisionBytecodeRemapError(
                "CONSTANT_String alias source is not CONSTANT_Utf8"
            )
        payload = entry["payload"]
        alias_entries.append(
            bytes([1])
            + struct.pack(">H", len(payload))
            + payload
        )

    new_cp_count = cp_count + len(alias_entries)
    rebuilt = (
        data[:8]
        + struct.pack(">H", new_cp_count)
        + b"".join(encoded_entries)
        + b"".join(alias_entries)
        + data[tail_offset:]
    )
    try:
        parse_class(rebuilt)
    except ClassFormatError as exc:
        raise CollisionBytecodeRemapError(
            f"rewritten class failed to parse: {exc}"
        ) from exc

    return rebuilt, len(rewrites) + len(class_alias_sources)

def _load_plan(path: Path) -> dict[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CollisionBytecodeRemapError(
            f"invalid private namespace collision plan: {path}"
        ) from exc

    if (
        plan.get("kind")
        != "class_package_namespace_collision_plan"
        or plan.get("schema_version") != 1
        or plan.get("identifiers_included") is not True
    ):
        raise CollisionBytecodeRemapError(
            "requires private identifier-bearing R8R collision plan"
        )
    return plan


def _class_names_from_jar(path: Path) -> set[str]:
    try:
        with zipfile.ZipFile(path) as z:
            return {
                name[:-6]
                for name in z.namelist()
                if name.endswith(".class")
                and not name.endswith("/")
                and name != "module-info.class"
            }
    except zipfile.BadZipFile as exc:
        raise CollisionBytecodeRemapError(
            f"invalid input JAR: {path}"
        ) from exc


def _expanded_mappings(
    class_names: set[str],
    plan: dict[str, Any],
) -> tuple[dict[str, str], int]:
    explicit: dict[str, str] = {}
    for row in plan.get("remaps", []):
        old = row.get("old_internal_name")
        new = row.get("new_internal_name")
        if (
            not isinstance(old, str)
            or not old
            or not isinstance(new, str)
            or not new
        ):
            raise CollisionBytecodeRemapError(
                "private plan remap lacks exact names"
            )
        if old in explicit and explicit[old] != new:
            raise CollisionBytecodeRemapError(
                f"conflicting explicit mapping for {old}"
            )
        explicit[old] = new

    for old in explicit:
        if old not in class_names:
            raise CollisionBytecodeRemapError(
                f"planned blocker class is absent from input JAR: {old}"
            )

    expanded = dict(explicit)
    nested_added = 0

    for old, new in sorted(explicit.items()):
        prefix = old + "$"
        for name in sorted(class_names):
            if not name.startswith(prefix):
                continue
            mapped = new + name[len(old):]
            prior = expanded.get(name)
            if prior is not None and prior != mapped:
                raise CollisionBytecodeRemapError(
                    f"nested family mapping conflict for {name}"
                )
            if prior is None:
                expanded[name] = mapped
                nested_added += 1

    targets = list(expanded.values())
    if len(targets) != len(set(targets)):
        raise CollisionBytecodeRemapError(
            "remap targets are not one-to-one"
        )

    unmapped = class_names - set(expanded)
    conflicts = sorted(set(targets) & unmapped)
    if conflicts:
        raise CollisionBytecodeRemapError(
            "remap target collides with unmapped class: "
            + conflicts[0]
        )

    return expanded, nested_added


def _is_signature_resource(name: str) -> bool:
    upper = name.upper()
    if not upper.startswith("META-INF/"):
        return False
    return upper.endswith(_SIGNED_SUFFIXES)


def _assert_unsigned_jar(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as z:
            signed = [
                name
                for name in z.namelist()
                if _is_signature_resource(name)
            ]
    except zipfile.BadZipFile as exc:
        raise CollisionBytecodeRemapError(
            f"invalid input JAR: {path}"
        ) from exc

    if signed:
        raise CollisionBytecodeRemapError(
            "refusing to rewrite signed JAR"
        )


def transform_collision_jar(
    input_jar: Path,
    private_plan_path: Path,
    output_jar: Path,
) -> dict[str, Any]:
    input_jar = input_jar.resolve()
    private_plan_path = private_plan_path.resolve()
    output_jar = output_jar.resolve()

    if not input_jar.is_file():
        raise CollisionBytecodeRemapError(
            f"input JAR does not exist: {input_jar}"
        )

    plan = _load_plan(private_plan_path)
    input_sha = _sha256_file(input_jar)
    if plan.get("readable_jar_sha256") != input_sha:
        raise CollisionBytecodeRemapError(
            "private R8R plan readable-JAR SHA mismatch"
        )

    _assert_unsigned_jar(input_jar)

    class_names = _class_names_from_jar(input_jar)
    mappings, nested_added = _expanded_mappings(
        class_names,
        plan,
    )

    pre = analyze_namespace_collisions(input_jar)
    if pre["report_id"] != plan.get("collision_report_id"):
        raise CollisionBytecodeRemapError(
            "private plan collision authority mismatch"
        )

    output_jar.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_jar.with_suffix(output_jar.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()

    rewritten_classes = 0
    changed_utf8_total = 0
    resource_count = 0
    output_names: set[str] = set()

    try:
        with zipfile.ZipFile(input_jar) as src:
            names = [
                info.filename
                for info in src.infolist()
                if not info.is_dir()
            ]
            rows: list[tuple[str, bytes]] = []
            for name in sorted(names):
                payload = src.read(name)
                out_name = name

                if name.endswith(".class"):
                    try:
                        parsed = parse_class(payload)
                    except ClassFormatError as exc:
                        raise CollisionBytecodeRemapError(
                            f"{name}: input class parse failed: {exc}"
                        ) from exc

                    if parsed.name != name[:-6]:
                        raise CollisionBytecodeRemapError(
                            f"{name}: entry/class identity mismatch"
                        )

                    rewritten, changed_utf8 = remap_class_bytes(
                        payload,
                        mappings,
                    )
                    changed_utf8_total += changed_utf8
                    new_name = mappings.get(
                        parsed.name,
                        parsed.name,
                    )
                    out_name = new_name + ".class"

                    reparsed = parse_class(rewritten)
                    if reparsed.name != new_name:
                        raise CollisionBytecodeRemapError(
                            f"{name}: rewritten identity mismatch "
                            f"{reparsed.name} != {new_name}"
                        )
                    if rewritten != payload:
                        rewritten_classes += 1
                    payload = rewritten
                else:
                    resource_count += 1

                if out_name in output_names:
                    raise CollisionBytecodeRemapError(
                        f"duplicate output entry: {out_name}"
                    )
                output_names.add(out_name)
                rows.append((out_name, payload))

        with zipfile.ZipFile(
            tmp,
            "w",
            compression=zipfile.ZIP_STORED,
        ) as dst:
            for name, payload in sorted(rows):
                info = zipfile.ZipInfo(
                    filename=name,
                    date_time=(1980, 1, 1, 0, 0, 0),
                )
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 0
                info.external_attr = 0
                dst.writestr(info, payload)

        post = analyze_namespace_collisions(tmp)
        if post["summary"]["collision_edge_count"] != 0:
            raise CollisionBytecodeRemapError(
                "transformed JAR still has class/package collisions"
            )

        with zipfile.ZipFile(tmp) as z:
            for name in sorted(
                entry
                for entry in z.namelist()
                if entry.endswith(".class")
            ):
                parsed = parse_class(z.read(name))
                if parsed.name != name[:-6]:
                    raise CollisionBytecodeRemapError(
                        f"{name}: post-transform entry/class mismatch"
                    )

        if output_jar.exists():
            output_jar.unlink()
        tmp.replace(output_jar)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise

    output_sha = _sha256_file(output_jar)
    public_material = {
        "plan_id": plan["plan_id"],
        "input_jar_sha256": input_sha,
        "output_jar_sha256": output_sha,
        "explicit_remap_count": len(plan.get("remaps", [])),
        "expanded_remap_count": len(mappings),
        "nested_family_added_count": nested_added,
        "rewritten_class_count": rewritten_classes,
        "changed_utf8_count": changed_utf8_total,
        "post_collision_edge_count": 0,
    }

    return {
        "schema_version": 1,
        "kind": "namespace_collision_bytecode_transform",
        "transform_id": (
            "JNSREWRITE_"
            + _stable_digest(public_material)[:20].upper()
        ),
        "plan_id": plan["plan_id"],
        "collision_report_id": plan["collision_report_id"],
        "input_jar_sha256": input_sha,
        "output_jar_sha256": output_sha,
        "summary": {
            "input_class_count": len(class_names),
            "explicit_remap_count": len(plan.get("remaps", [])),
            "expanded_remap_count": len(mappings),
            "nested_family_added_count": nested_added,
            "rewritten_class_count": rewritten_classes,
            "changed_utf8_count": changed_utf8_total,
            "resource_count": resource_count,
            "pre_collision_edge_count": pre["summary"][
                "collision_edge_count"
            ],
            "post_collision_edge_count": 0,
        },
    }


def write_transform_report(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
