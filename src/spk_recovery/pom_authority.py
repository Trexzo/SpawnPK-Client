from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any
import xml.etree.ElementTree as ET
import zipfile

from .decompiler import sha256_file


class PomAuthorityError(ValueError):
    pass


_PROPERTY_RE = re.compile(r"\$\{([^{}]+)\}")
_DEFAULT_PROJECT_PREFIXES = ("rs/", "tools/")
_DEFAULT_PROJECT_METADATA = (
    "pom.xml",
    "Client.iml",
    "build.xml",
    "build_pre.xml",
)


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element | None, name: str) -> list[ET.Element]:
    if element is None:
        return []
    return [child for child in element if _local(child.tag) == name]


def _child(element: ET.Element | None, name: str) -> ET.Element | None:
    rows = _children(element, name)
    return rows[0] if rows else None


def _text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _child_text(element: ET.Element | None, name: str) -> str | None:
    return _text(_child(element, name))


def _resolve_value(
    value: str | None,
    properties: dict[str, str],
) -> dict[str, Any]:
    if value is None:
        return {
            "raw": None,
            "resolved": None,
            "unresolved_properties": [],
        }

    current = value
    seen: set[str] = set()
    for _ in range(32):
        matches = _PROPERTY_RE.findall(current)
        if not matches:
            break
        changed = False
        for key in matches:
            if key in properties:
                token = "${" + key + "}"
                replacement = properties[key]
                next_value = current.replace(token, replacement)
                if next_value != current:
                    current = next_value
                    changed = True
        if not changed or current in seen:
            break
        seen.add(current)

    unresolved = sorted(set(_PROPERTY_RE.findall(current)))
    return {
        "raw": value,
        "resolved": current if not unresolved else None,
        "unresolved_properties": unresolved,
    }


def _dependency_row(
    element: ET.Element,
    *,
    index: int,
    properties: dict[str, str],
) -> dict[str, Any]:
    fields = {
        name: _child_text(element, name)
        for name in (
            "groupId",
            "artifactId",
            "version",
            "type",
            "classifier",
            "scope",
            "optional",
        )
    }
    return {
        "index": index,
        **{
            name: _resolve_value(value, properties)
            for name, value in fields.items()
        },
    }


def _repository_row(element: ET.Element, *, index: int) -> dict[str, Any]:
    snapshots = _child(element, "snapshots")
    releases = _child(element, "releases")
    return {
        "index": index,
        "id": _child_text(element, "id"),
        "name": _child_text(element, "name"),
        "url": _child_text(element, "url"),
        "layout": _child_text(element, "layout"),
        "snapshots": {
            "enabled": _child_text(snapshots, "enabled"),
            "update_policy": _child_text(snapshots, "updatePolicy"),
            "checksum_policy": _child_text(snapshots, "checksumPolicy"),
        },
        "releases": {
            "enabled": _child_text(releases, "enabled"),
            "update_policy": _child_text(releases, "updatePolicy"),
            "checksum_policy": _child_text(releases, "checksumPolicy"),
        },
    }


def _plugin_row(
    element: ET.Element,
    *,
    index: int,
    properties: dict[str, str],
) -> dict[str, Any]:
    configuration = _child(element, "configuration")
    config_rows: list[dict[str, Any]] = []
    if configuration is not None:
        for child in configuration:
            value = _text(child)
            config_rows.append(
                {
                    "name": _local(child.tag),
                    "value": _resolve_value(value, properties),
                }
            )
    return {
        "index": index,
        "group_id": _resolve_value(
            _child_text(element, "groupId"),
            properties,
        ),
        "artifact_id": _resolve_value(
            _child_text(element, "artifactId"),
            properties,
        ),
        "version": _resolve_value(
            _child_text(element, "version"),
            properties,
        ),
        "configuration": config_rows,
    }


def parse_root_pom_authority(
    jar_path: Path,
    *,
    pom_entry: str = "pom.xml",
) -> dict[str, Any]:
    jar_path = jar_path.resolve()
    if not jar_path.is_file():
        raise PomAuthorityError(f"JAR does not exist: {jar_path}")

    try:
        with zipfile.ZipFile(jar_path) as archive:
            try:
                pom_bytes = archive.read(pom_entry)
            except KeyError as exc:
                raise PomAuthorityError(
                    f"root POM entry is absent: {pom_entry}"
                ) from exc
    except zipfile.BadZipFile as exc:
        raise PomAuthorityError(
            f"invalid JAR/ZIP: {jar_path}"
        ) from exc

    try:
        root = ET.fromstring(pom_bytes)
    except ET.ParseError as exc:
        raise PomAuthorityError(
            f"invalid root POM XML: {exc}"
        ) from exc

    if _local(root.tag) != "project":
        raise PomAuthorityError("root POM document is not a Maven project")

    properties_element = _child(root, "properties")
    property_rows: list[dict[str, str]] = []
    properties: dict[str, str] = {}
    if properties_element is not None:
        for child in properties_element:
            key = _local(child.tag)
            value = _text(child) or ""
            property_rows.append({"name": key, "value": value})
            properties[key] = value

    repositories_element = _child(root, "repositories")
    repositories = [
        _repository_row(element, index=index)
        for index, element in enumerate(
            _children(repositories_element, "repository")
        )
    ]

    dependency_management = _child(
        _child(root, "dependencyManagement"),
        "dependencies",
    )
    managed_dependencies = [
        _dependency_row(
            element,
            index=index,
            properties=properties,
        )
        for index, element in enumerate(
            _children(dependency_management, "dependency")
        )
    ]

    dependencies_element = _child(root, "dependencies")
    dependencies = [
        _dependency_row(
            element,
            index=index,
            properties=properties,
        )
        for index, element in enumerate(
            _children(dependencies_element, "dependency")
        )
    ]

    build = _child(root, "build")
    resources_element = _child(build, "resources")
    resources = [
        {
            "index": index,
            "directory": _resolve_value(
                _child_text(resource, "directory"),
                properties,
            ),
            "filtering": _resolve_value(
                _child_text(resource, "filtering"),
                properties,
            ),
        }
        for index, resource in enumerate(
            _children(resources_element, "resource")
        )
    ]

    plugins_element = _child(build, "plugins")
    plugins = [
        _plugin_row(
            plugin,
            index=index,
            properties=properties,
        )
        for index, plugin in enumerate(
            _children(plugins_element, "plugin")
        )
    ]

    material = {
        "source_jar_sha256": sha256_file(jar_path),
        "pom_entry": pom_entry,
        "pom_sha256": _sha256_bytes(pom_bytes),
        "pom_size_bytes": len(pom_bytes),
        "model_version": _child_text(root, "modelVersion"),
        "project": {
            "group_id": _resolve_value(
                _child_text(root, "groupId"),
                properties,
            ),
            "artifact_id": _resolve_value(
                _child_text(root, "artifactId"),
                properties,
            ),
            "version": _resolve_value(
                _child_text(root, "version"),
                properties,
            ),
            "packaging": _resolve_value(
                _child_text(root, "packaging"),
                properties,
            ),
        },
        "properties": property_rows,
        "repositories": repositories,
        "dependency_management": managed_dependencies,
        "dependencies": dependencies,
        "build": {
            "output_directory": _resolve_value(
                _child_text(build, "outputDirectory"),
                properties,
            ),
            "resources": resources,
            "plugins": plugins,
        },
    }
    return {
        "schema_version": 1,
        "kind": "root_pom_authority",
        "pom_authority_id": (
            "POMAUTH_" + _stable_digest(material)[:20].upper()
        ),
        **material,
    }


def _normalized_prefixes(
    prefixes: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        prefix if prefix.endswith("/") else prefix + "/"
        for prefix in prefixes
    )


def _is_project_entry(
    name: str,
    prefixes: tuple[str, ...],
) -> bool:
    return any(name.startswith(prefix) for prefix in prefixes)


def _entry_map(
    jar_path: Path,
    *,
    project_prefixes: tuple[str, ...],
    excluded_entries: set[str],
    classes_only: bool,
) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(jar_path) as archive:
            result: dict[str, bytes] = {}
            for name in archive.namelist():
                if name.endswith("/"):
                    continue
                if name in excluded_entries:
                    continue
                if _is_project_entry(name, project_prefixes):
                    continue
                if classes_only and not name.endswith(".class"):
                    continue
                result[name] = archive.read(name)
            return result
    except zipfile.BadZipFile as exc:
        raise PomAuthorityError(
            f"invalid JAR/ZIP: {jar_path}"
        ) from exc


def _service_trailing_newline_equivalent(
    entry: str,
    left: bytes,
    right: bytes,
) -> bool:
    if not entry.startswith("META-INF/services/"):
        return False
    if left == right:
        return False
    for longer, shorter in ((left, right), (right, left)):
        if longer == shorter + b"\n" or longer == shorter + b"\r\n":
            try:
                longer.decode("utf-8")
                shorter.decode("utf-8")
            except UnicodeDecodeError:
                return False
            return True
    return False


def verify_pom_transfer(
    source_jar: Path,
    target_jar: Path,
    *,
    pom_entry: str = "pom.xml",
    project_prefixes: tuple[str, ...] = _DEFAULT_PROJECT_PREFIXES,
    source_project_metadata: tuple[str, ...] = _DEFAULT_PROJECT_METADATA,
) -> dict[str, Any]:
    source_jar = source_jar.resolve()
    target_jar = target_jar.resolve()
    prefixes = _normalized_prefixes(project_prefixes)

    pom_authority = parse_root_pom_authority(
        source_jar,
        pom_entry=pom_entry,
    )

    try:
        with zipfile.ZipFile(target_jar) as archive:
            target_has_pom = pom_entry in archive.namelist()
    except zipfile.BadZipFile as exc:
        raise PomAuthorityError(
            f"invalid target JAR/ZIP: {target_jar}"
        ) from exc

    class_source = _entry_map(
        source_jar,
        project_prefixes=prefixes,
        excluded_entries=set(),
        classes_only=True,
    )
    class_target = _entry_map(
        target_jar,
        project_prefixes=prefixes,
        excluded_entries=set(),
        classes_only=True,
    )
    class_common = sorted(set(class_source) & set(class_target))
    class_different = [
        name
        for name in class_common
        if class_source[name] != class_target[name]
    ]
    class_source_only = sorted(set(class_source) - set(class_target))
    class_target_only = sorted(set(class_target) - set(class_source))

    excluded = set(source_project_metadata)
    resource_source = _entry_map(
        source_jar,
        project_prefixes=prefixes,
        excluded_entries=excluded,
        classes_only=False,
    )
    resource_target = _entry_map(
        target_jar,
        project_prefixes=prefixes,
        excluded_entries=excluded,
        classes_only=False,
    )
    resource_common = sorted(
        set(resource_source) & set(resource_target)
    )
    resource_source_only = sorted(
        set(resource_source) - set(resource_target)
    )
    resource_target_only = sorted(
        set(resource_target) - set(resource_source)
    )

    byte_differences: list[dict[str, Any]] = []
    non_equivalent_differences: list[str] = []
    normalized_equivalent_differences: list[str] = []
    for name in resource_common:
        left = resource_source[name]
        right = resource_target[name]
        if left == right:
            continue
        equivalent = _service_trailing_newline_equivalent(
            name,
            left,
            right,
        )
        byte_differences.append(
            {
                "entry": name,
                "source_sha256": _sha256_bytes(left),
                "target_sha256": _sha256_bytes(right),
                "normalized_text_equivalent": equivalent,
                "equivalence_kind": (
                    "service_descriptor_single_trailing_newline"
                    if equivalent
                    else None
                ),
            }
        )
        if equivalent:
            normalized_equivalent_differences.append(name)
        else:
            non_equivalent_differences.append(name)

    class_surface_exact = (
        not class_source_only
        and not class_target_only
        and not class_different
    )
    resource_surface_equivalent = (
        not resource_source_only
        and not resource_target_only
        and not non_equivalent_differences
    )

    material = {
        "source_jar_sha256": sha256_file(source_jar),
        "target_jar_sha256": sha256_file(target_jar),
        "source_pom_authority_id": pom_authority[
            "pom_authority_id"
        ],
        "target_contains_pom_entry": target_has_pom,
        "project_prefixes": list(prefixes),
        "excluded_source_project_metadata": sorted(excluded),
        "dependency_class_surface": {
            "source_count": len(class_source),
            "target_count": len(class_target),
            "common_count": len(class_common),
            "byte_identical_common_count": (
                len(class_common) - len(class_different)
            ),
            "source_only": class_source_only,
            "target_only": class_target_only,
            "different_common": class_different,
            "exact": class_surface_exact,
        },
        "non_project_payload_surface": {
            "source_count": len(resource_source),
            "target_count": len(resource_target),
            "common_count": len(resource_common),
            "source_only": resource_source_only,
            "target_only": resource_target_only,
            "byte_differences": byte_differences,
            "normalized_text_equivalent_differences": (
                normalized_equivalent_differences
            ),
            "non_equivalent_differences": non_equivalent_differences,
            "equivalent": resource_surface_equivalent,
        },
        "transfer_accepted": (
            class_surface_exact and resource_surface_equivalent
        ),
    }
    return {
        "schema_version": 1,
        "kind": "root_pom_transfer_authority",
        "pom_transfer_id": (
            "POMTRANSFER_" + _stable_digest(material)[:20].upper()
        ),
        **material,
        "source_pom_authority": pom_authority,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract root POM authority and optionally verify its "
            "dependency-payload transfer to another fat client."
        )
    )
    parser.add_argument("source_jar", type=Path)
    parser.add_argument(
        "--target-jar",
        type=Path,
        help="Optional target JAR for transfer verification.",
    )
    parser.add_argument(
        "--pom-entry",
        default="pom.xml",
    )
    parser.add_argument(
        "--project-prefix",
        action="append",
        default=None,
        help=(
            "Project-owned class/resource prefix; repeatable. "
            "Transfer default: rs/, tools/."
        ),
    )
    args = parser.parse_args()

    if args.target_jar is None:
        report = parse_root_pom_authority(
            args.source_jar,
            pom_entry=args.pom_entry,
        )
    else:
        prefixes = tuple(
            args.project_prefix or _DEFAULT_PROJECT_PREFIXES
        )
        report = verify_pom_transfer(
            args.source_jar,
            args.target_jar,
            pom_entry=args.pom_entry,
            project_prefixes=prefixes,
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
