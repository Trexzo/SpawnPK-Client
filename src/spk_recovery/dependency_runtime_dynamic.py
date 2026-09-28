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


def _read_code_calls(
    code: bytes,
    cp: list[Any],
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    offset = 0
    while offset < len(code):
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
                classification = (
                    "native_load_dynamic"
                    if category == "native_loading"
                    else "dynamic_target_unresolved"
                )
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
                        "literal_target": None,
                        "literal_target_proven": False,
                    }
                )

        length = _instruction_length(code, offset)
        if length <= 0 or offset + length > len(code):
            raise DependencyRuntimeDynamicError(
                f"invalid instruction length at bytecode offset {offset}"
            )
        offset += length
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
                method_calls.extend(
                    _read_code_calls(code, cp)
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
            entries = sorted(
                info.filename
                for info in archive.infolist()
                if not info.is_dir()
                and info.filename.endswith(".class")
            )
            for entry in entries:
                scanned_class_count += 1
                try:
                    profile = _profile_class_dynamic_calls(
                        archive.read(entry)
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
