from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any
import zipfile

from .classfile import ClassFormatError, ParsedClass, parse_class
from .decompiler import sha256_file
from .dependency_artifact_proof import (
    DependencyArtifactProofError,
    _artifact_index,
)


class DependencyRemapProofError(ValueError):
    pass


_SPECIAL_METHODS = {"<init>", "<clinit>"}
_OBJECT_DESCRIPTOR_RE = re.compile(r"L([^;]+);")


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _descriptor_shape(desc: str) -> str:
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
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _load_reference_surface(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRemapProofError(
            f"invalid dependency reference surface: {path}"
        ) from exc
    if data.get("kind") != "project_non_project_reference_surface":
        raise DependencyRemapProofError(
            "reference surface has unexpected kind"
        )
    return data


def _is_project(
    internal_name: str,
    project_prefixes: tuple[str, ...],
) -> bool:
    return any(
        internal_name.startswith(prefix)
        for prefix in project_prefixes
    )


def _bundled_index(
    jar_path: Path,
    *,
    project_prefixes: tuple[str, ...],
) -> dict[str, ParsedClass]:
    jar_path = jar_path.resolve()
    if not jar_path.is_file():
        raise DependencyRemapProofError(
            f"bundled client JAR does not exist: {jar_path}"
        )

    classes: dict[str, ParsedClass] = {}
    try:
        with zipfile.ZipFile(jar_path) as archive:
            for entry in sorted(
                name
                for name in archive.namelist()
                if name.endswith(".class")
                and name != "module-info.class"
                and not name.startswith("META-INF/versions/")
            ):
                internal_name = entry[:-6]
                if _is_project(internal_name, project_prefixes):
                    continue
                try:
                    parsed = parse_class(archive.read(entry))
                except ClassFormatError as exc:
                    raise DependencyRemapProofError(
                        f"{entry}: bundled class parse failed: {exc}"
                    ) from exc
                if parsed.name != internal_name:
                    raise DependencyRemapProofError(
                        f"{entry}: bundled class identity mismatch"
                    )
                classes[parsed.name] = parsed
    except zipfile.BadZipFile as exc:
        raise DependencyRemapProofError(
            f"invalid bundled JAR/ZIP: {jar_path}"
        ) from exc
    return classes


def _structural_groups(
    classes: dict[str, ParsedClass],
) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for name, parsed in classes.items():
        groups.setdefault(
            parsed.structural_sha256(),
            [],
        ).append(name)
    for names in groups.values():
        names.sort()
    return groups


def _api_identity_payload(
    parsed: ParsedClass,
) -> tuple[Any, ...]:
    return (
        parsed.major,
        parsed.minor,
        parsed.access,
        parsed.super_name,
        tuple(parsed.interfaces),
        tuple(
            (
                int(row["access"]),
                str(row["name"]),
                str(row["descriptor"]),
                tuple(row.get("attributes", [])),
            )
            for row in parsed.fields
        ),
        tuple(
            (
                int(row["access"]),
                str(row["name"]),
                str(row["descriptor"]),
                tuple(row.get("attributes", [])),
            )
            for row in parsed.methods
        ),
        tuple(
            attribute
            for attribute in parsed.attributes
            if attribute != "SourceFile"
        ),
        tuple(sorted(parsed.literal_strings)),
        tuple(
            sorted(
                (
                    type(value).__name__,
                    repr(value),
                )
                for value in parsed.numeric_constants
            )
        ),
        parsed.inner_outer_name,
        parsed.inner_simple_name,
        parsed.enclosing_class_name,
    )


def _package_name(internal_name: str) -> str:
    return (
        internal_name.rsplit("/", 1)[0]
        if "/" in internal_name
        else ""
    )


def _package_api_shape_payload(
    parsed: ParsedClass,
) -> tuple[Any, ...]:
    return (
        parsed.major,
        parsed.minor,
        parsed.access,
        len(parsed.interfaces),
        tuple(
            (
                int(row["access"]),
                _descriptor_shape(str(row["descriptor"])),
            )
            for row in parsed.fields
        ),
        tuple(
            (
                int(row["access"]),
                _descriptor_shape(str(row["descriptor"])),
            )
            for row in parsed.methods
        ),
        tuple(sorted(parsed.literal_strings)),
        tuple(
            sorted(
                (
                    type(value).__name__,
                    repr(value),
                )
                for value in parsed.numeric_constants
            )
        ),
    )


def _class_mappings(
    bundled: dict[str, ParsedClass],
    official: dict[str, ParsedClass],
    artifact_by_class: dict[str, str],
    *,
    package_api_candidate_names: set[str] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    bundled_groups = _structural_groups(bundled)
    official_groups = _structural_groups(official)
    mappings: dict[str, dict[str, Any]] = {}

    for old_name, old_class in sorted(bundled.items()):
        structural = old_class.structural_sha256()
        same = official.get(old_name)
        if (
            same is not None
            and same.structural_sha256() == structural
        ):
            mappings[old_name] = {
                "old_name": old_name,
                "new_name": old_name,
                "strategy": "identity_structural",
                "structural_sha256": structural,
                "artifact": artifact_by_class.get(old_name),
            }
            continue

        if (
            same is not None
            and _api_identity_payload(old_class)
            == _api_identity_payload(same)
        ):
            mappings[old_name] = {
                "old_name": old_name,
                "new_name": old_name,
                "strategy": "identity_api_surface",
                "structural_sha256": structural,
                "artifact": artifact_by_class.get(old_name),
            }
            continue

        old_candidates = bundled_groups.get(structural, [])
        new_candidates = official_groups.get(structural, [])
        if len(old_candidates) == 1 and len(new_candidates) == 1:
            new_name = new_candidates[0]
            mappings[old_name] = {
                "old_name": old_name,
                "new_name": new_name,
                "strategy": "unique_structural",
                "structural_sha256": structural,
                "artifact": artifact_by_class.get(new_name),
            }

    package_targets: dict[str, dict[str, int]] = {}
    for old_name, mapping in mappings.items():
        old_package = _package_name(old_name)
        new_package = _package_name(str(mapping["new_name"]))
        bucket = package_targets.setdefault(old_package, {})
        bucket[new_package] = bucket.get(new_package, 0) + 1

    used_targets = {
        str(mapping["new_name"])
        for mapping in mappings.values()
    }
    official_by_package: dict[str, list[str]] = {}
    for name in official:
        official_by_package.setdefault(
            _package_name(name),
            [],
        ).append(name)
    for names in official_by_package.values():
        names.sort()

    initial_mapped_names = set(mappings)
    for old_name, old_class in sorted(bundled.items()):
        if old_name in initial_mapped_names:
            continue
        if (
            package_api_candidate_names is None
            or old_name not in package_api_candidate_names
        ):
            continue
        package_counts = package_targets.get(
            _package_name(old_name),
            {},
        )
        package_support = sum(package_counts.values())
        if package_support < 3 or len(package_counts) != 1:
            continue
        target_package = next(iter(package_counts))
        payload = _package_api_shape_payload(old_class)
        candidates = [
            name
            for name in official_by_package.get(
                target_package,
                [],
            )
            if name not in used_targets
            and _package_api_shape_payload(official[name]) == payload
        ]
        if len(candidates) != 1:
            continue
        new_name = candidates[0]
        mappings[old_name] = {
            "old_name": old_name,
            "new_name": new_name,
            "strategy": "package_api_shape",
            "structural_sha256": old_class.structural_sha256(),
            "package_authority": {
                "old_package": _package_name(old_name),
                "new_package": target_package,
                "support_count": package_support,
                "purity": 1.0,
            },
            "api_shape_sha256": _stable_digest(payload),
            "artifact": artifact_by_class.get(new_name),
        }
        used_targets.add(new_name)

    topology_initial_mapped_names = set(mappings)
    for old_name, old_class in sorted(bundled.items()):
        if old_name in topology_initial_mapped_names:
            continue
        if (
            package_api_candidate_names is None
            or old_name not in package_api_candidate_names
        ):
            continue

        package_counts = package_targets.get(
            _package_name(old_name),
            {},
        )
        package_support = sum(package_counts.values())
        if package_support < 3 or len(package_counts) != 1:
            continue
        target_package = next(iter(package_counts))

        known_super: str | None = None
        super_is_known = old_class.super_name is None
        if old_class.super_name is not None:
            mapped_super = mappings.get(old_class.super_name)
            if mapped_super is not None:
                known_super = str(mapped_super["new_name"])
                super_is_known = True
            elif old_class.super_name not in bundled:
                known_super = old_class.super_name
                super_is_known = True

        translated_interfaces: list[str] = []
        interfaces_are_known = True
        for interface in old_class.interfaces:
            mapped_interface = mappings.get(interface)
            if mapped_interface is not None:
                translated_interfaces.append(
                    str(mapped_interface["new_name"])
                )
            elif interface not in bundled:
                translated_interfaces.append(interface)
            else:
                interfaces_are_known = False
                break

        old_field_sequence = tuple(
            (
                int(row["access"]),
                _descriptor_shape(str(row["descriptor"])),
            )
            for row in old_class.fields
        )
        old_literals = tuple(sorted(old_class.literal_strings))
        old_numbers = tuple(
            sorted(
                (
                    type(value).__name__,
                    repr(value),
                )
                for value in old_class.numeric_constants
            )
        )

        candidates: list[str] = []
        for candidate in official_by_package.get(
            target_package,
            [],
        ):
            if candidate in used_targets:
                continue
            official_class = official[candidate]
            if (
                official_class.major != old_class.major
                or official_class.minor != old_class.minor
                or official_class.access != old_class.access
                or len(official_class.interfaces)
                != len(old_class.interfaces)
                or len(official_class.methods)
                != len(old_class.methods)
            ):
                continue
            if tuple(
                (
                    int(row["access"]),
                    _descriptor_shape(str(row["descriptor"])),
                )
                for row in official_class.fields
            ) != old_field_sequence:
                continue
            if (
                tuple(sorted(official_class.literal_strings))
                != old_literals
            ):
                continue
            if tuple(
                sorted(
                    (
                        type(value).__name__,
                        repr(value),
                    )
                    for value in official_class.numeric_constants
                )
            ) != old_numbers:
                continue
            if (
                super_is_known
                and official_class.super_name != known_super
            ):
                continue
            if (
                interfaces_are_known
                and tuple(official_class.interfaces)
                != tuple(translated_interfaces)
            ):
                continue
            candidates.append(candidate)

        if len(candidates) != 1:
            continue

        new_name = candidates[0]
        mappings[old_name] = {
            "old_name": old_name,
            "new_name": new_name,
            "strategy": "package_api_topology",
            "structural_sha256": old_class.structural_sha256(),
            "package_authority": {
                "old_package": _package_name(old_name),
                "new_package": target_package,
                "support_count": package_support,
                "purity": 1.0,
            },
            "topology_proof": {
                "major": old_class.major,
                "minor": old_class.minor,
                "access": old_class.access,
                "field_sequence": [
                    {
                        "access": access,
                        "descriptor_shape": descriptor_shape,
                    }
                    for access, descriptor_shape
                    in old_field_sequence
                ],
                "method_count": len(old_class.methods),
                "interface_count": len(old_class.interfaces),
                "super_constraint_available": super_is_known,
                "translated_super": known_super,
                "interfaces_constraint_available": (
                    interfaces_are_known
                ),
                "translated_interfaces": (
                    translated_interfaces
                    if interfaces_are_known
                    else []
                ),
                "literal_strings_sha256": _stable_digest(
                    list(old_literals)
                ),
                "numeric_constants_sha256": _stable_digest(
                    list(old_numbers)
                ),
            },
            "artifact": artifact_by_class.get(new_name),
        }
        used_targets.add(new_name)

    summary = {
        "accepted_class_mapping_count": len(mappings),
        "identity_structural_count": sum(
            row["strategy"] == "identity_structural"
            for row in mappings.values()
        ),
        "identity_api_surface_count": sum(
            row["strategy"] == "identity_api_surface"
            for row in mappings.values()
        ),
        "unique_structural_count": sum(
            row["strategy"] == "unique_structural"
            for row in mappings.values()
        ),
        "package_api_shape_count": sum(
            row["strategy"] == "package_api_shape"
            for row in mappings.values()
        ),
        "package_api_topology_count": sum(
            row["strategy"] == "package_api_topology"
            for row in mappings.values()
        ),
        "renamed_class_mapping_count": sum(
            old != row["new_name"]
            for old, row in mappings.items()
        ),
    }
    return mappings, summary


def _field_sequence(parsed: ParsedClass) -> list[tuple[int, str]]:
    return [
        (int(row["access"]), _descriptor_shape(str(row["descriptor"])))
        for row in parsed.fields
    ]


def _ordinary_method_sequence(
    parsed: ParsedClass,
) -> list[tuple[int, str, int | None]]:
    return [
        (
            int(row["access"]),
            _descriptor_shape(str(row["descriptor"])),
            row.get("code_length"),
        )
        for row in parsed.methods
        if row["name"] not in _SPECIAL_METHODS
    ]


def _member_alignment(
    bundled: dict[str, ParsedClass],
    official: dict[str, ParsedClass],
    mappings: dict[str, dict[str, Any]],
) -> dict[str, dict[str, bool]]:
    result: dict[str, dict[str, bool]] = {}
    for old_name, mapping in mappings.items():
        new_name = str(mapping["new_name"])
        old_class = bundled[old_name]
        new_class = official[new_name]
        result[old_name] = {
            "field_sequence_equal": (
                _field_sequence(old_class)
                == _field_sequence(new_class)
            ),
            "ordinary_method_sequence_equal": (
                _ordinary_method_sequence(old_class)
                == _ordinary_method_sequence(new_class)
            ),
        }
    return result


def _hierarchy_names(
    start: str,
    classes: dict[str, ParsedClass],
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    queue = [start]
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        parsed = classes.get(current)
        if parsed is None:
            continue
        result.append(current)
        if parsed.super_name:
            queue.append(parsed.super_name)
        queue.extend(parsed.interfaces)
    return result


def _external_hierarchy_boundaries(
    owner: str,
    classes: dict[str, ParsedClass],
) -> list[str]:
    boundaries: set[str] = set()
    seen: set[str] = set()
    queue = [owner]
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        parsed = classes.get(current)
        if parsed is None:
            boundaries.add(current)
            continue
        parents: list[str] = []
        if parsed.super_name:
            parents.append(parsed.super_name)
        parents.extend(parsed.interfaces)
        for parent in parents:
            if parent in classes:
                queue.append(parent)
            else:
                boundaries.add(parent)
    return sorted(boundaries)


def _declarations(
    *,
    kind: str,
    owner: str,
    name: str,
    descriptor: str,
    classes: dict[str, ParsedClass],
) -> list[tuple[str, dict[str, Any]]]:
    if kind == "field":
        member_key = "fields"
    elif kind in {"method", "interface_method"}:
        member_key = "methods"
    else:
        return []

    declarations: list[tuple[str, dict[str, Any]]] = []
    search_names = (
        [owner]
        if name in _SPECIAL_METHODS
        else _hierarchy_names(owner, classes)
    )
    for declaring in search_names:
        parsed = classes.get(declaring)
        if parsed is None:
            continue
        rows = getattr(parsed, member_key)
        for row in rows:
            if (
                str(row["name"]) == name
                and str(row["descriptor"]) == descriptor
            ):
                declarations.append((declaring, row))
    return declarations


def _translate_descriptor(
    descriptor: str,
    *,
    class_mappings: dict[str, dict[str, Any]],
    bundled_classes: dict[str, ParsedClass],
) -> str | None:
    failed = False

    def replace(match: re.Match[str]) -> str:
        nonlocal failed
        old_name = match.group(1)
        mapped = class_mappings.get(old_name)
        if mapped is not None:
            return "L" + str(mapped["new_name"]) + ";"
        if old_name in bundled_classes:
            failed = True
        return match.group(0)

    translated = _OBJECT_DESCRIPTOR_RE.sub(replace, descriptor)
    return None if failed else translated


def _map_declared_member(
    *,
    kind: str,
    declaring_owner: str,
    member: dict[str, Any],
    bundled: dict[str, ParsedClass],
    official: dict[str, ParsedClass],
    mappings: dict[str, dict[str, Any]],
    alignments: dict[str, dict[str, bool]],
) -> dict[str, Any] | None:
    class_mapping = mappings.get(declaring_owner)
    if class_mapping is None:
        return None
    official_owner = str(class_mapping["new_name"])
    old_class = bundled[declaring_owner]
    new_class = official[official_owner]
    name = str(member["name"])
    descriptor = str(member["descriptor"])

    if class_mapping["strategy"] == "identity_api_surface":
        official_rows = (
            new_class.fields
            if kind == "field"
            else new_class.methods
        )
        exact = [
            row
            for row in official_rows
            if (
                str(row["name"]) == name
                and str(row["descriptor"]) == descriptor
            )
        ]
        if len(exact) != 1:
            return None
        return {
            "declaring_old_owner": declaring_owner,
            "declaring_new_owner": official_owner,
            "new_name": name,
            "new_descriptor": descriptor,
            "strategy": "identity_api_surface_exact_member",
        }

    if class_mapping["strategy"] in {
        "package_api_shape",
        "package_api_topology",
    }:
        if name in _SPECIAL_METHODS:
            return None
        official_rows = (
            new_class.fields
            if kind == "field"
            else new_class.methods
        )
        access = int(member["access"])
        exact = [
            row
            for row in official_rows
            if (
                int(row["access"]) == access
                and str(row["name"]) == name
                and str(row["descriptor"]) == descriptor
            )
        ]
        if len(exact) == 1:
            return {
                "declaring_old_owner": declaring_owner,
                "declaring_new_owner": official_owner,
                "new_name": name,
                "new_descriptor": descriptor,
                "strategy": (
                    str(class_mapping["strategy"])
                    + "_exact_member"
                ),
            }
        descriptor_matches = [
            row
            for row in official_rows
            if (
                int(row["access"]) == access
                and str(row["descriptor"]) == descriptor
            )
        ]
        if len(descriptor_matches) != 1:
            return None
        official_member = descriptor_matches[0]
        return {
            "declaring_old_owner": declaring_owner,
            "declaring_new_owner": official_owner,
            "new_name": str(official_member["name"]),
            "new_descriptor": descriptor,
            "strategy": (
                str(class_mapping["strategy"])
                + "_unique_descriptor_member"
            ),
        }

    if kind == "field":
        if not alignments[declaring_owner]["field_sequence_equal"]:
            return None
        matches = [
            index
            for index, row in enumerate(old_class.fields)
            if (
                str(row["name"]) == name
                and str(row["descriptor"]) == descriptor
            )
        ]
        if len(matches) != 1:
            return None
        official_member = new_class.fields[matches[0]]
        return {
            "declaring_old_owner": declaring_owner,
            "declaring_new_owner": official_owner,
            "new_name": str(official_member["name"]),
            "new_descriptor": str(official_member["descriptor"]),
            "strategy": "field_declaration_position",
        }

    if name not in _SPECIAL_METHODS:
        if not alignments[declaring_owner][
            "ordinary_method_sequence_equal"
        ]:
            return None
        old_methods = [
            row
            for row in old_class.methods
            if row["name"] not in _SPECIAL_METHODS
        ]
        new_methods = [
            row
            for row in new_class.methods
            if row["name"] not in _SPECIAL_METHODS
        ]
        matches = [
            index
            for index, row in enumerate(old_methods)
            if (
                str(row["name"]) == name
                and str(row["descriptor"]) == descriptor
            )
        ]
        if len(matches) != 1:
            return None
        official_member = new_methods[matches[0]]
        return {
            "declaring_old_owner": declaring_owner,
            "declaring_new_owner": official_owner,
            "new_name": str(official_member["name"]),
            "new_descriptor": str(official_member["descriptor"]),
            "strategy": "ordinary_method_declaration_position",
        }

    if name != "<init>":
        return None

    translated = _translate_descriptor(
        descriptor,
        class_mappings=mappings,
        bundled_classes=bundled,
    )
    if translated is None:
        return None
    candidates = [
        row
        for row in new_class.methods
        if (
            row["name"] == "<init>"
            and str(row["descriptor"]) == translated
        )
    ]
    if len(candidates) != 1:
        return None
    return {
        "declaring_old_owner": declaring_owner,
        "declaring_new_owner": official_owner,
        "new_name": "<init>",
        "new_descriptor": translated,
        "strategy": "constructor_mapped_descriptor",
    }


def _map_reference(
    row: dict[str, Any],
    *,
    bundled: dict[str, ParsedClass],
    official: dict[str, ParsedClass],
    artifact_by_class: dict[str, str],
    mappings: dict[str, dict[str, Any]],
    alignments: dict[str, dict[str, bool]],
) -> dict[str, Any]:
    kind = str(row["kind"])
    owner = str(row["owner"])
    name = str(row["name"])
    descriptor = str(row["descriptor"])
    base = {
        "kind": kind,
        "old_owner": owner,
        "old_name": name,
        "old_descriptor": descriptor,
        "reference_count": int(row.get("reference_count", 0)),
        "source_class_count": int(row.get("source_class_count", 0)),
    }

    if owner not in bundled:
        official_owner = official.get(owner)
        if official_owner is not None:
            declarations = _declarations(
                kind=kind,
                owner=owner,
                name=name,
                descriptor=descriptor,
                classes=official,
            )
            if declarations:
                return {
                    **base,
                    "status": "official_unbundled_direct",
                    "new_owner": owner,
                    "new_name": name,
                    "new_descriptor": descriptor,
                    "artifact": artifact_by_class.get(owner),
                    "proof": {
                        "strategy": "exact_official_api_unbundled",
                    },
                }
        return {
            **base,
            "status": "platform_runtime",
            "new_owner": None,
            "new_name": None,
            "new_descriptor": None,
            "artifact": None,
            "proof": {
                "strategy": "owner_absent_from_bundled_and_official_sets",
            },
        }

    owner_mapping = mappings.get(owner)
    if owner_mapping is None:
        return {
            **base,
            "status": "bundled_unresolved_class",
            "new_owner": None,
            "new_name": None,
            "new_descriptor": None,
            "artifact": None,
            "proof": {
                "strategy": "no_accepted_class_mapping",
            },
        }

    declarations = _declarations(
        kind=kind,
        owner=owner,
        name=name,
        descriptor=descriptor,
        classes=bundled,
    )
    if not declarations:
        boundaries = _external_hierarchy_boundaries(
            owner,
            bundled,
        )
        if boundaries:
            return {
                **base,
                "status": "external_hierarchy_member",
                "new_owner": str(owner_mapping["new_name"]),
                "new_name": None,
                "new_descriptor": None,
                "artifact": owner_mapping.get("artifact"),
                "proof": {
                    "strategy": (
                        "member_absent_before_non_bundled_hierarchy_boundary"
                    ),
                    "external_hierarchy_boundaries": boundaries,
                },
            }
        return {
            **base,
            "status": "bundled_member_not_declared",
            "new_owner": str(owner_mapping["new_name"]),
            "new_name": None,
            "new_descriptor": None,
            "artifact": owner_mapping.get("artifact"),
            "proof": {
                "strategy": "exact_bundled_hierarchy_lookup_failed",
            },
        }

    mapped_declarations: list[dict[str, Any]] = []
    for declaring_owner, member in declarations:
        mapped = _map_declared_member(
            kind=kind,
            declaring_owner=declaring_owner,
            member=member,
            bundled=bundled,
            official=official,
            mappings=mappings,
            alignments=alignments,
        )
        if mapped is not None:
            mapped_declarations.append(mapped)

    if not mapped_declarations:
        return {
            **base,
            "status": "bundled_member_unresolved",
            "new_owner": str(owner_mapping["new_name"]),
            "new_name": None,
            "new_descriptor": None,
            "artifact": owner_mapping.get("artifact"),
            "proof": {
                "strategy": "declaration_transfer_failed_closed",
                "declaration_count": len(declarations),
            },
        }

    targets = {
        (
            str(mapped["new_name"]),
            str(mapped["new_descriptor"]),
        )
        for mapped in mapped_declarations
    }
    if len(targets) != 1:
        return {
            **base,
            "status": "bundled_member_ambiguous",
            "new_owner": str(owner_mapping["new_name"]),
            "new_name": None,
            "new_descriptor": None,
            "artifact": owner_mapping.get("artifact"),
            "proof": {
                "strategy": "multiple_hierarchy_paths_do_not_converge",
                "candidate_targets": [
                    {"name": item[0], "descriptor": item[1]}
                    for item in sorted(targets)
                ],
            },
        }

    new_name, new_descriptor = next(iter(targets))
    strategies = sorted(
        {str(mapped["strategy"]) for mapped in mapped_declarations}
    )
    changed = (
        owner != str(owner_mapping["new_name"])
        or name != new_name
        or descriptor != new_descriptor
    )
    return {
        **base,
        "status": "accepted_remap" if changed else "accepted_identity",
        "new_owner": str(owner_mapping["new_name"]),
        "new_name": new_name,
        "new_descriptor": new_descriptor,
        "artifact": owner_mapping.get("artifact"),
        "proof": {
            "strategy": "hierarchy_convergent_declaration_transfer",
            "owner_mapping_strategy": owner_mapping["strategy"],
            "declaration_count": len(declarations),
            "mapped_declaration_count": len(mapped_declarations),
            "member_transfer_strategies": strategies,
        },
    }


def prove_dependency_remaps(
    reference_surface_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    java_release: int,
    project_prefixes: tuple[str, ...] = ("rs/", "tools/"),
) -> dict[str, Any]:
    reference_surface_path = reference_surface_path.resolve()
    bundled_jar = bundled_jar.resolve()
    prefixes = tuple(
        prefix if prefix.endswith("/") else prefix + "/"
        for prefix in project_prefixes
    )
    surface = _load_reference_surface(reference_surface_path)

    try:
        official, artifact_by_class, artifacts = _artifact_index(
            official_artifacts,
            java_release=java_release,
        )
    except DependencyArtifactProofError as exc:
        raise DependencyRemapProofError(str(exc)) from exc

    bundled = _bundled_index(
        bundled_jar,
        project_prefixes=prefixes,
    )
    referenced_owners = {
        str(row["owner"])
        for row in surface.get("member_references", [])
    }
    mappings, class_summary = _class_mappings(
        bundled,
        official,
        artifact_by_class,
        package_api_candidate_names=referenced_owners,
    )
    alignments = _member_alignment(
        bundled,
        official,
        mappings,
    )

    referenced_class_rows = [
        {
            **mappings[owner],
            **alignments[owner],
        }
        for owner in sorted(referenced_owners)
        if owner in mappings
    ]

    member_results = [
        _map_reference(
            row,
            bundled=bundled,
            official=official,
            artifact_by_class=artifact_by_class,
            mappings=mappings,
            alignments=alignments,
        )
        for row in surface.get("member_references", [])
    ]

    status_counts: dict[str, int] = {}
    weighted_status_counts: dict[str, int] = {}
    for row in member_results:
        status = str(row["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
        weighted_status_counts[status] = (
            weighted_status_counts.get(status, 0)
            + int(row["reference_count"])
        )

    referenced_owner_summary = {
        "referenced_owner_count": len(referenced_owners),
        "accepted_class_mapping_owner_count": sum(
            owner in mappings for owner in referenced_owners
        ),
        "bundled_unresolved_owner_count": sum(
            owner in bundled and owner not in mappings
            for owner in referenced_owners
        ),
        "non_bundled_owner_count": sum(
            owner not in bundled for owner in referenced_owners
        ),
    }

    material = {
        "reference_surface_id": surface["reference_surface_id"],
        "reference_surface_sha256": hashlib.sha256(
            reference_surface_path.read_bytes()
        ).hexdigest(),
        "bundled_jar_sha256": sha256_file(bundled_jar),
        "java_release": java_release,
        "project_prefixes": list(prefixes),
        "official_artifacts": artifacts,
        "referenced_class_mappings": referenced_class_rows,
        "member_results": member_results,
    }
    return {
        "schema_version": 1,
        "kind": "dependency_structural_remap_proof",
        "dependency_remap_proof_id": (
            "DEPREMAP_" + _stable_digest(material)[:20].upper()
        ),
        "reference_surface_id": surface["reference_surface_id"],
        "bundled_jar_sha256": material["bundled_jar_sha256"],
        "java_release": java_release,
        "project_prefixes": list(prefixes),
        "official_artifacts": artifacts,
        "summary": {
            **class_summary,
            **referenced_owner_summary,
            "member_reference_count": len(member_results),
            "weighted_member_reference_count": sum(
                int(row["reference_count"])
                for row in member_results
            ),
            "member_status_counts": dict(sorted(status_counts.items())),
            "weighted_member_status_counts": dict(
                sorted(weighted_status_counts.items())
            ),
            "referenced_class_mapping_count": len(
                referenced_class_rows
            ),
            "referenced_field_sequence_equal_count": sum(
                row["field_sequence_equal"]
                for row in referenced_class_rows
            ),
            "referenced_ordinary_method_sequence_equal_count": sum(
                row["ordinary_method_sequence_equal"]
                for row in referenced_class_rows
            ),
        },
        "referenced_class_mappings": referenced_class_rows,
        "member_results": member_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prove bundled-obfuscated dependency class/member remaps "
            "against exact official dependency artifacts."
        )
    )
    parser.add_argument("reference_surface", type=Path)
    parser.add_argument("bundled_jar", type=Path)
    parser.add_argument("artifact", type=Path, nargs="+")
    parser.add_argument("--java-release", type=int, required=True)
    parser.add_argument(
        "--project-prefix",
        action="append",
        default=None,
        help=(
            "Project-owned internal-name prefix; repeatable. "
            "Defaults: rs/ and tools/."
        ),
    )
    args = parser.parse_args()

    report = prove_dependency_remaps(
        args.reference_surface,
        args.bundled_jar,
        args.artifact,
        java_release=args.java_release,
        project_prefixes=tuple(
            args.project_prefix or ["rs/", "tools/"]
        ),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
