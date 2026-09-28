from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .bytecode_profile import (
    BytecodeProfileError,
    _Reader,
    _class_name,
    _constant_pool,
    _instruction_length,
    _member_ref,
    _skip_attributes,
    _utf8,
)


class DependencyRuntimeDynamicError(ValueError):
    pass


_LITERAL_TARGET_APIS: dict[
    tuple[str, str, str],
    str,
] = {
    (
        "java/lang/Class",
        "forName",
        "(Ljava/lang/String;)Ljava/lang/Class;",
    ): "string",
    (
        "java/lang/ClassLoader",
        "loadClass",
        "(Ljava/lang/String;)Ljava/lang/Class;",
    ): "string",
    (
        "java/lang/invoke/MethodHandles$Lookup",
        "findClass",
        "(Ljava/lang/String;)Ljava/lang/Class;",
    ): "string",
    (
        "java/lang/System",
        "load",
        "(Ljava/lang/String;)V",
    ): "string",
    (
        "java/lang/System",
        "loadLibrary",
        "(Ljava/lang/String;)V",
    ): "string",
    (
        "java/lang/Class",
        "getResource",
        "(Ljava/lang/String;)Ljava/net/URL;",
    ): "string",
    (
        "java/lang/Class",
        "getResourceAsStream",
        "(Ljava/lang/String;)Ljava/io/InputStream;",
    ): "string",
    (
        "java/lang/ClassLoader",
        "getResource",
        "(Ljava/lang/String;)Ljava/net/URL;",
    ): "string",
    (
        "java/lang/ClassLoader",
        "getResourceAsStream",
        "(Ljava/lang/String;)Ljava/io/InputStream;",
    ): "string",
    (
        "java/lang/ClassLoader",
        "getResources",
        "(Ljava/lang/String;)Ljava/util/Enumeration;",
    ): "string",
    (
        "java/util/ServiceLoader",
        "load",
        "(Ljava/lang/Class;)Ljava/util/ServiceLoader;",
    ): "class",
}


_DYNAMIC_APIS: dict[tuple[str, str], str] = {
    ("java/lang/Class", "forName"): "class_loading",
    ("java/lang/ClassLoader", "loadClass"): "class_loading",
    (
        "java/lang/invoke/MethodHandles$Lookup",
        "findClass",
    ): "class_loading",
    ("java/util/ServiceLoader", "load"): "service_loading",
    ("java/lang/System", "load"): "native_loading",
    ("java/lang/System", "loadLibrary"): "native_loading",
    ("java/lang/Class", "getResource"): "resource_loading",
    (
        "java/lang/Class",
        "getResourceAsStream",
    ): "resource_loading",
    (
        "java/lang/ClassLoader",
        "getResource",
    ): "resource_loading",
    (
        "java/lang/ClassLoader",
        "getResourceAsStream",
    ): "resource_loading",
    (
        "java/lang/ClassLoader",
        "getResources",
    ): "resource_loading",
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _load_resource_authority(path: Path) -> dict[str, Any]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRuntimeDynamicError(
            "invalid runtime resource authority"
        ) from exc
    if (
        report.get("kind")
        != "dependency_runtime_resource_equivalence"
    ):
        raise DependencyRuntimeDynamicError(
            "unexpected runtime resource authority kind"
        )
    return report


def _instruction_offsets(code: bytes) -> list[int]:
    offsets: list[int] = []
    offset = 0
    while offset < len(code):
        offsets.append(offset)
        length = _instruction_length(code, offset)
        if length <= 0 or offset + length > len(code):
            raise DependencyRuntimeDynamicError(
                f"invalid instruction length at bytecode offset {offset}"
            )
        offset += length
    if offset != len(code):
        raise DependencyRuntimeDynamicError(
            "instruction stream does not end at code boundary"
        )
    return offsets


def _branch_targets(
    code: bytes,
    offsets: list[int],
) -> set[int]:
    targets: set[int] = set()
    valid = set(offsets)

    def add_target(source: int, delta: int) -> None:
        target = source + delta
        if target not in valid:
            raise DependencyRuntimeDynamicError(
                f"invalid branch target {target} from {source}"
            )
        targets.add(target)

    for offset in offsets:
        opcode = code[offset]
        if opcode in set(range(0x99, 0xA9)) | {0xC6, 0xC7}:
            delta = int.from_bytes(
                code[offset + 1 : offset + 3],
                "big",
                signed=True,
            )
            add_target(offset, delta)
        elif opcode in {0xC8, 0xC9}:
            delta = int.from_bytes(
                code[offset + 1 : offset + 5],
                "big",
                signed=True,
            )
            add_target(offset, delta)
        elif opcode == 0xAA:
            padding = (4 - ((offset + 1) % 4)) % 4
            base = offset + 1 + padding
            default = int.from_bytes(
                code[base : base + 4],
                "big",
                signed=True,
            )
            low = int.from_bytes(
                code[base + 4 : base + 8],
                "big",
                signed=True,
            )
            high = int.from_bytes(
                code[base + 8 : base + 12],
                "big",
                signed=True,
            )
            add_target(offset, default)
            cursor = base + 12
            for _ in range(high - low + 1):
                delta = int.from_bytes(
                    code[cursor : cursor + 4],
                    "big",
                    signed=True,
                )
                add_target(offset, delta)
                cursor += 4
        elif opcode == 0xAB:
            padding = (4 - ((offset + 1) % 4)) % 4
            base = offset + 1 + padding
            default = int.from_bytes(
                code[base : base + 4],
                "big",
                signed=True,
            )
            pairs = int.from_bytes(
                code[base + 4 : base + 8],
                "big",
                signed=True,
            )
            add_target(offset, default)
            cursor = base + 8
            for _ in range(pairs):
                cursor += 4
                delta = int.from_bytes(
                    code[cursor : cursor + 4],
                    "big",
                    signed=True,
                )
                add_target(offset, delta)
                cursor += 4

    return targets


def _ldc_literal(
    code: bytes,
    offset: int,
    cp: list[Any],
) -> tuple[str, str] | None:
    opcode = code[offset]
    if opcode == 0x12:
        cp_index = code[offset + 1]
    elif opcode == 0x13:
        cp_index = int.from_bytes(
            code[offset + 1 : offset + 3],
            "big",
        )
    else:
        return None

    value = cp[cp_index]
    if not value:
        return None
    if value[0] == 8:
        return ("string", _utf8(cp, value[1]))
    if value[0] == 7:
        return ("class", _class_name(cp, cp_index))
    return None


def _literal_target_proof(
    *,
    code: bytes,
    cp: list[Any],
    offsets: list[int],
    branch_targets: set[int],
    handler_targets: set[int],
    invocation_offset: int,
    owner: str,
    name: str,
    descriptor: str,
) -> tuple[str, str] | None:
    expected = _LITERAL_TARGET_APIS.get(
        (owner, name, descriptor)
    )
    if expected is None:
        return None
    if (
        invocation_offset in branch_targets
        or invocation_offset in handler_targets
    ):
        return None

    try:
        index = offsets.index(invocation_offset)
    except ValueError:
        return None
    if index == 0:
        return None

    predecessor = offsets[index - 1]
    if (
        predecessor
        + _instruction_length(code, predecessor)
        != invocation_offset
    ):
        return None

    literal = _ldc_literal(code, predecessor, cp)
    if literal is None or literal[0] != expected:
        return None
    return literal


def _read_code_calls(
    code: bytes,
    cp: list[Any],
    *,
    handler_targets: set[int],
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    offsets = _instruction_offsets(code)
    branch_targets = _branch_targets(code, offsets)
    for offset in offsets:
        opcode = code[offset]
        if opcode in {0xB6, 0xB7, 0xB8, 0xB9}:
            if offset + 3 > len(code):
                raise DependencyRuntimeDynamicError(
                    "truncated invocation instruction"
                )
            cp_index = int.from_bytes(
                code[offset + 1 : offset + 3],
                "big",
            )
            try:
                owner, name, descriptor = _member_ref(
                    cp,
                    cp_index,
                )
            except BytecodeProfileError as exc:
                raise DependencyRuntimeDynamicError(
                    f"invalid invocation member reference: {exc}"
                ) from exc

            category = _DYNAMIC_APIS.get((owner, name))
            if category is not None:
                proof = _literal_target_proof(
                    code=code,
                    cp=cp,
                    offsets=offsets,
                    branch_targets=branch_targets,
                    handler_targets=handler_targets,
                    invocation_offset=offset,
                    owner=owner,
                    name=name,
                    descriptor=descriptor,
                )
                if proof is not None:
                    literal_kind, literal_target = proof
                    if category == "service_loading":
                        classification = "service_loader_class_token"
                    elif category == "native_loading":
                        classification = "native_load_literal"
                    else:
                        classification = "literal_target_proven"
                    proof_reason = (
                        "immediate_typed_constant_with_no_alternate_"
                        "branch_or_handler_entry"
                    )
                else:
                    literal_kind = None
                    literal_target = None
                    classification = (
                        "native_load_dynamic"
                        if category == "native_loading"
                        else "dynamic_target_unresolved"
                    )
                    proof_reason = None

                calls.append(
                    {
                        "offset": offset,
                        "opcode": opcode,
                        "invocation_kind": {
                            0xB6: "invokevirtual",
                            0xB7: "invokespecial",
                            0xB8: "invokestatic",
                            0xB9: "invokeinterface",
                        }[opcode],
                        "owner": owner,
                        "name": name,
                        "descriptor": descriptor,
                        "category": category,
                        "classification": classification,
                        "literal_target": literal_target,
                        "literal_kind": literal_kind,
                        "literal_target_proven": proof is not None,
                        "literal_proof_reason": proof_reason,
                    }
                )
    return calls


def _profile_class_dynamic_calls(
    data: bytes,
) -> dict[str, Any]:
    r = _Reader(data)
    if r.u4() != 0xCAFEBABE:
        raise DependencyRuntimeDynamicError(
            "not a JVM class"
        )
    r.u2()
    r.u2()
    try:
        cp = _constant_pool(r)
        r.u2()
        this_class = r.u2()
        r.u2()
        internal_name = _class_name(cp, this_class)

        for _ in range(r.u2()):
            r.u2()

        for _ in range(r.u2()):
            r.u2()
            r.u2()
            r.u2()
            _skip_attributes(r, cp)

        methods: list[dict[str, Any]] = []
        for _ in range(r.u2()):
            access = r.u2()
            name = _utf8(cp, r.u2())
            descriptor = _utf8(cp, r.u2())
            method_calls: list[dict[str, Any]] = []

            for _ in range(r.u2()):
                attr_name = _utf8(cp, r.u2())
                attr_length = r.u4()
                payload = r.take(attr_length)
                if attr_name != "Code":
                    continue

                cr = _Reader(payload)
                cr.u2()
                cr.u2()
                code_length = cr.u4()
                code = cr.take(code_length)
                handler_targets: set[int] = set()
                for _ in range(cr.u2()):
                    cr.u2()
                    cr.u2()
                    handler_pc = cr.u2()
                    cr.u2()
                    handler_targets.add(handler_pc)
                method_calls.extend(
                    _read_code_calls(
                        code,
                        cp,
                        handler_targets=handler_targets,
                    )
                )

            if method_calls:
                methods.append(
                    {
                        "access": access,
                        "name": name,
                        "descriptor": descriptor,
                        "calls": method_calls,
                    }
                )
    except BytecodeProfileError as exc:
        raise DependencyRuntimeDynamicError(
            f"class parse failed: {exc}"
        ) from exc

    return {
        "internal_name": internal_name,
        "methods": methods,
    }


def build_dependency_runtime_dynamic_inventory(
    runtime_resource_path: Path,
    bundled_jar: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    runtime_resource_path = runtime_resource_path.resolve()
    bundled_jar = bundled_jar.resolve()

    authority = _load_resource_authority(
        runtime_resource_path
    )
    if not bundled_jar.is_file():
        raise DependencyRuntimeDynamicError(
            "bundled/readable JAR does not exist"
        )

    bundled_sha = _sha256_file(bundled_jar)
    if authority.get("bundled_jar_sha256") != bundled_sha:
        raise DependencyRuntimeDynamicError(
            "runtime resource authority is bound to a different bundled JAR"
        )

    raw_rows: list[dict[str, Any]] = []
    scanned_class_count = 0

    try:
        with zipfile.ZipFile(bundled_jar) as archive:
            entries: list[zipfile.ZipInfo] = []
            seen_entries: set[str] = set()
            for info in archive.infolist():
                if (
                    info.is_dir()
                    or not info.filename.endswith(".class")
                ):
                    continue
                if info.filename in seen_entries:
                    raise DependencyRuntimeDynamicError(
                        "duplicate class entry in bundled/readable JAR: "
                        + info.filename
                    )
                seen_entries.add(info.filename)
                entries.append(info)

            for info in sorted(
                entries,
                key=lambda value: value.filename,
            ):
                entry = info.filename
                scanned_class_count += 1
                try:
                    profile = _profile_class_dynamic_calls(
                        archive.read(info)
                    )
                except DependencyRuntimeDynamicError as exc:
                    raise DependencyRuntimeDynamicError(
                        f"{entry}: {exc}"
                    ) from exc

                caller = str(profile["internal_name"])
                for method in profile["methods"]:
                    for call in method["calls"]:
                        raw_rows.append(
                            {
                                "entry": entry,
                                "caller": caller,
                                "caller_method": method["name"],
                                "caller_descriptor": method[
                                    "descriptor"
                                ],
                                **call,
                            }
                        )
    except zipfile.BadZipFile as exc:
        raise DependencyRuntimeDynamicError(
            "invalid bundled/readable JAR"
        ) from exc

    raw_rows.sort(
        key=lambda row: (
            row["entry"],
            row["caller"],
            row["caller_method"],
            row["caller_descriptor"],
            int(row["offset"]),
            row["owner"],
            row["name"],
            row["descriptor"],
        )
    )

    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    category_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()

    for index, row in enumerate(raw_rows, start=1):
        category = str(row["category"])
        classification = str(row["classification"])
        category_counts[category] += 1
        classification_counts[classification] += 1

        public = {
            "callsite_id": f"DEPRUNTIME_DYNAMIC_{index:05d}",
            "category": category,
            "classification": classification,
            "literal_target_proven": bool(
                row["literal_target_proven"]
            ),
            "invocation_kind": row["invocation_kind"],
        }
        public_rows.append(public)

        if include_identifiers:
            private_rows.append(
                {
                    **public,
                    "entry": row["entry"],
                    "caller": row["caller"],
                    "caller_method": row[
                        "caller_method"
                    ],
                    "caller_descriptor": row[
                        "caller_descriptor"
                    ],
                    "bytecode_offset": row["offset"],
                    "invoked_owner": row["owner"],
                    "invoked_name": row["name"],
                    "invoked_descriptor": row[
                        "descriptor"
                    ],
                    "literal_target": row[
                        "literal_target"
                    ],
                    "literal_kind": row[
                        "literal_kind"
                    ],
                    "literal_proof_reason": row[
                        "literal_proof_reason"
                    ],
                }
            )

    unresolved_count = sum(
        1
        for row in public_rows
        if not row["literal_target_proven"]
    )
    native_load_count = category_counts.get(
        "native_loading",
        0,
    )

    material = {
        "runtime_resource_id": authority.get(
            "runtime_resource_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "scanned_class_count": scanned_class_count,
        "callsites": public_rows,
        "dynamic_target_unresolved_count": (
            unresolved_count
        ),
        "runtime_capsule_mutation_ready": False,
    }
    dynamic_id = (
        "DEPRUNTIMEDYNAMIC_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "dependency_runtime_dynamic_inventory",
        "runtime_dynamic_id": dynamic_id,
        "runtime_resource_id": authority.get(
            "runtime_resource_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "summary": {
            "scanned_class_count": scanned_class_count,
            "dynamic_callsite_count": len(public_rows),
            "category_counts": dict(
                sorted(category_counts.items())
            ),
            "classification_counts": dict(
                sorted(classification_counts.items())
            ),
            "literal_target_proven_count": sum(
                1
                for row in public_rows
                if row["literal_target_proven"]
            ),
            "dynamic_target_unresolved_count": (
                unresolved_count
            ),
            "native_load_callsite_count": (
                native_load_count
            ),
            "external_or_native_reflection_absence_unproven": True,
            "runtime_capsule_mutation_ready": False,
        },
        "callsites": (
            private_rows
            if include_identifiers
            else public_rows
        ),
        "identifiers_included": include_identifiers,
        "note": (
            "This inventory records exact known dynamic-loading invocation "
            "sites. It does not infer targets from nearby strings and does "
            "not prove absence of reflective or native-driven loading."
        ),
    }


def write_dependency_runtime_dynamic_inventory(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
