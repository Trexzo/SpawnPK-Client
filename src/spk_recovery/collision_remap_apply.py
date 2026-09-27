from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import struct
from typing import Any
import zipfile

from .bytecode_profile import (
    BytecodeProfileError,
    profile_class_constant_pool_references,
)
from .classfile import ClassFormatError, parse_class


class CollisionRemapApplyError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
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


def _load_private_remap_plan(path: Path) -> dict[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CollisionRemapApplyError(
            f"invalid remap plan: {path}"
        ) from exc

    if (
        plan.get("kind") != "package_class_collision_remap_plan"
        or plan.get("identifiers_included") is not True
    ):
        raise CollisionRemapApplyError(
            "requires identifier-bearing collision remap plan"
        )

    remaps = plan.get("remaps")
    if not isinstance(remaps, list) or not remaps:
        raise CollisionRemapApplyError(
            "private remap plan has no remaps"
        )
    return plan


def _mapping(plan: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    targets: set[str] = set()

    for row in plan["remaps"]:
        old = row.get("old_internal_name")
        new = row.get("new_internal_name")
        if not isinstance(old, str) or not old:
            raise CollisionRemapApplyError(
                "remap row lacks old_internal_name"
            )
        if not isinstance(new, str) or not new:
            raise CollisionRemapApplyError(
                "remap row lacks new_internal_name"
            )
        if old == new:
            raise CollisionRemapApplyError(
                "identity remap is not allowed"
            )
        if old in mapping and mapping[old] != new:
            raise CollisionRemapApplyError(
                "old identity has conflicting targets"
            )
        if new in targets:
            raise CollisionRemapApplyError(
                "multiple blockers map to same target"
            )
        mapping[old] = new
        targets.add(new)

    return dict(sorted(mapping.items()))


def _rewrite_utf8_value(
    raw: bytes,
    mapping: dict[str, str],
) -> tuple[bytes, list[dict[str, str]]]:
    changed = raw
    events: list[dict[str, str]] = []

    for old, new in mapping.items():
        old_b = old.encode("ascii")
        new_b = new.encode("ascii")
        old_dot = old.replace("/", ".").encode("ascii")
        new_dot = new.replace("/", ".").encode("ascii")

        before = changed

        # Exact class identity or nested-class identity.
        if changed == old_b:
            changed = new_b
        elif changed.startswith(old_b + b"$"):
            changed = new_b + changed[len(old_b):]

        # Exact dotted binary-name strings used by reflection/config.
        if changed == old_dot:
            changed = new_dot
        elif changed.startswith(old_dot + b"$"):
            changed = new_dot + changed[len(old_dot):]

        # JVM descriptors / signatures.  Do not rewrite raw package
        # prefixes such as old + "/child"; only type-token boundaries.
        changed = changed.replace(
            b"L" + old_b + b";",
            b"L" + new_b + b";",
        )
        changed = changed.replace(
            b"L" + old_b + b"$",
            b"L" + new_b + b"$",
        )
        changed = changed.replace(
            b"L" + old_b + b"<",
            b"L" + new_b + b"<",
        )

        if changed != before:
            events.append(
                {
                    "old_internal_name": old,
                    "new_internal_name": new,
                }
            )

    return changed, events


def rewrite_classfile(
    data: bytes,
    mapping: dict[str, str],
) -> tuple[bytes, dict[str, Any]]:
    if len(data) < 10 or data[:4] != b"\xCA\xFE\xBA\xBE":
        raise CollisionRemapApplyError(
            "input is not a JVM classfile"
        )

    source = io.BytesIO(data)
    out = io.BytesIO()

    header = source.read(8)
    out.write(header)

    cp_count_raw = source.read(2)
    if len(cp_count_raw) != 2:
        raise CollisionRemapApplyError(
            "truncated constant_pool_count"
        )
    out.write(cp_count_raw)
    cp_count = struct.unpack(">H", cp_count_raw)[0]

    utf8_changes = 0
    remap_events: list[dict[str, str]] = []

    index = 1
    while index < cp_count:
        tag_raw = source.read(1)
        if len(tag_raw) != 1:
            raise CollisionRemapApplyError(
                "truncated constant-pool tag"
            )
        tag = tag_raw[0]
        out.write(tag_raw)

        if tag == 1:
            length_raw = source.read(2)
            if len(length_raw) != 2:
                raise CollisionRemapApplyError(
                    "truncated CONSTANT_Utf8 length"
                )
            length = struct.unpack(">H", length_raw)[0]
            payload = source.read(length)
            if len(payload) != length:
                raise CollisionRemapApplyError(
                    "truncated CONSTANT_Utf8 payload"
                )

            rewritten, events = _rewrite_utf8_value(
                payload,
                mapping,
            )
            if len(rewritten) > 0xFFFF:
                raise CollisionRemapApplyError(
                    "rewritten CONSTANT_Utf8 exceeds JVM limit"
                )
            out.write(struct.pack(">H", len(rewritten)))
            out.write(rewritten)
            if rewritten != payload:
                utf8_changes += 1
                remap_events.extend(events)

        elif tag in (3, 4):
            payload = source.read(4)
            if len(payload) != 4:
                raise CollisionRemapApplyError(
                    "truncated numeric constant"
                )
            out.write(payload)

        elif tag in (5, 6):
            payload = source.read(8)
            if len(payload) != 8:
                raise CollisionRemapApplyError(
                    "truncated wide numeric constant"
                )
            out.write(payload)
            index += 1

        elif tag in (7, 8, 16, 19, 20):
            payload = source.read(2)
            if len(payload) != 2:
                raise CollisionRemapApplyError(
                    "truncated constant-pool entry"
                )
            out.write(payload)

        elif tag in (9, 10, 11, 12, 17, 18):
            payload = source.read(4)
            if len(payload) != 4:
                raise CollisionRemapApplyError(
                    "truncated constant-pool entry"
                )
            out.write(payload)

        elif tag == 15:
            payload = source.read(3)
            if len(payload) != 3:
                raise CollisionRemapApplyError(
                    "truncated MethodHandle constant"
                )
            out.write(payload)

        else:
            raise CollisionRemapApplyError(
                f"unsupported constant-pool tag {tag}"
            )

        index += 1

    out.write(source.read())
    rewritten_data = out.getvalue()

    try:
        parsed = parse_class(rewritten_data)
    except ClassFormatError as exc:
        raise CollisionRemapApplyError(
            f"rewritten class failed parse: {exc}"
        ) from exc

    return rewritten_data, {
        "utf8_change_count": utf8_changes,
        "remap_event_count": len(remap_events),
        "parsed_internal_name": parsed.name,
    }


def _entry_target(
    entry: str,
    mapping: dict[str, str],
) -> str:
    if not entry.endswith(".class"):
        return entry

    internal = entry[:-6]
    for old, new in mapping.items():
        if internal == old:
            return new + ".class"
        if internal.startswith(old + "$"):
            return new + internal[len(old):] + ".class"
    return entry


def _remaining_old_references(
    jar_path: Path,
    mapping: dict[str, str],
) -> list[dict[str, str]]:
    old_names = set(mapping)
    rows: list[dict[str, str]] = []

    try:
        with zipfile.ZipFile(jar_path) as archive:
            for entry in sorted(
                name
                for name in archive.namelist()
                if name.endswith(".class")
            ):
                data = archive.read(entry)
                try:
                    parsed = parse_class(data)
                    profile = profile_class_constant_pool_references(
                        data
                    )
                except (
                    ClassFormatError,
                    BytecodeProfileError,
                ) as exc:
                    raise CollisionRemapApplyError(
                        f"{entry}: verification parse failed: {exc}"
                    ) from exc

                if parsed.name in old_names:
                    rows.append(
                        {
                            "entry": entry,
                            "kind": "class_identity",
                            "old_internal_name": parsed.name,
                        }
                    )

                refs = set(profile.get("class_references", []))
                refs.update(
                    str(row["owner"])
                    for row in profile.get(
                        "member_references",
                        [],
                    )
                )
                for field in parsed.fields:
                    descriptor = str(field["descriptor"])
                    for old in old_names:
                        if (
                            f"L{old};" in descriptor
                            or f"L{old}$" in descriptor
                        ):
                            refs.add(old)
                for method in parsed.methods:
                    descriptor = str(method["descriptor"])
                    for old in old_names:
                        if (
                            f"L{old};" in descriptor
                            or f"L{old}$" in descriptor
                        ):
                            refs.add(old)

                for old in sorted(old_names & refs):
                    rows.append(
                        {
                            "entry": entry,
                            "kind": "type_reference",
                            "old_internal_name": old,
                        }
                    )
    except zipfile.BadZipFile as exc:
        raise CollisionRemapApplyError(
            f"invalid output JAR: {jar_path}"
        ) from exc

    return rows


def apply_collision_remap_plan(
    private_plan_path: Path,
    input_jar: Path,
    output_jar: Path,
) -> dict[str, Any]:
    private_plan_path = private_plan_path.resolve()
    input_jar = input_jar.resolve()
    output_jar = output_jar.resolve()

    plan = _load_private_remap_plan(private_plan_path)
    mapping = _mapping(plan)

    if plan.get("jar_sha256") != _sha256_file(input_jar):
        raise CollisionRemapApplyError(
            "remap plan is bound to a different input JAR"
        )

    changed_classes: list[dict[str, Any]] = []
    unchanged_entries = 0
    output_names: set[str] = set()

    output_jar.parent.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(input_jar, "r") as src, zipfile.ZipFile(
            output_jar,
            "w",
        ) as dst:
            original_names = set(src.namelist())

            for info in src.infolist():
                original_name = info.filename
                target_name = _entry_target(
                    original_name,
                    mapping,
                )

                if target_name in output_names:
                    raise CollisionRemapApplyError(
                        f"output entry collision: {target_name}"
                    )
                if (
                    target_name != original_name
                    and target_name in original_names
                ):
                    raise CollisionRemapApplyError(
                        f"remap target already exists: {target_name}"
                    )
                output_names.add(target_name)

                payload = src.read(info)
                rewritten = payload
                rewrite_meta = None

                if original_name.endswith(".class"):
                    rewritten, rewrite_meta = rewrite_classfile(
                        payload,
                        mapping,
                    )

                if (
                    rewritten == payload
                    and target_name == original_name
                ):
                    unchanged_entries += 1
                else:
                    changed_classes.append(
                        {
                            "old_entry": original_name,
                            "new_entry": target_name,
                            "old_sha256": _sha256(payload),
                            "new_sha256": _sha256(rewritten),
                            "utf8_change_count": (
                                rewrite_meta[
                                    "utf8_change_count"
                                ]
                                if rewrite_meta is not None
                                else 0
                            ),
                        }
                    )

                new_info = copy.copy(info)
                new_info.filename = target_name
                dst.writestr(new_info, rewritten)

    except zipfile.BadZipFile as exc:
        raise CollisionRemapApplyError(
            f"invalid input JAR: {input_jar}"
        ) from exc

    remaining = _remaining_old_references(
        output_jar,
        mapping,
    )
    if remaining:
        raise CollisionRemapApplyError(
            "output JAR retains old class identity/reference surface"
        )

    # Verify every requested remap target exists as a class identity.
    output_class_names: set[str] = set()
    with zipfile.ZipFile(output_jar) as archive:
        for entry in archive.namelist():
            if not entry.endswith(".class"):
                continue
            try:
                parsed = parse_class(archive.read(entry))
            except ClassFormatError as exc:
                raise CollisionRemapApplyError(
                    f"{entry}: output class parse failed: {exc}"
                ) from exc
            if parsed.name + ".class" != entry:
                raise CollisionRemapApplyError(
                    f"{entry}: output class identity/path mismatch"
                )
            output_class_names.add(parsed.name)

    missing_targets = sorted(
        target
        for target in mapping.values()
        if target not in output_class_names
    )
    if missing_targets:
        raise CollisionRemapApplyError(
            "output JAR missing requested remap target"
        )

    material = {
        "remap_plan_id": plan["remap_plan_id"],
        "input_jar_sha256": _sha256_file(input_jar),
        "output_jar_sha256": _sha256_file(output_jar),
        "mapping_count": len(mapping),
        "changed_classes": changed_classes,
    }

    return {
        "schema_version": 1,
        "kind": "package_class_collision_remap_application",
        "application_id": (
            "JCOLLISIONAPPLY_"
            + _stable_digest(material)[:20].upper()
        ),
        "remap_plan_id": plan["remap_plan_id"],
        "collision_topology_id": plan[
            "collision_topology_id"
        ],
        "input_jar_sha256": material[
            "input_jar_sha256"
        ],
        "output_jar_sha256": material[
            "output_jar_sha256"
        ],
        "summary": {
            "mapping_count": len(mapping),
            "changed_class_entry_count": len(
                changed_classes
            ),
            "unchanged_entry_count": unchanged_entries,
            "remaining_old_reference_count": 0,
            "verified_target_count": len(mapping),
        },
        "changed_classes": changed_classes,
    }


def write_collision_remap_application(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
