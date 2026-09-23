from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile


class DependencyAuthorityError(ValueError):
    pass


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


def _parse_properties(data: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in data.decode("utf-8", "replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def scan_dependency_authority(
    jar_path: Path,
    *,
    project_prefixes: tuple[str, ...] = ("rs/",),
) -> dict[str, Any]:
    jar_path = jar_path.resolve()
    if not jar_path.is_file():
        raise DependencyAuthorityError(f"JAR does not exist: {jar_path}")

    normalized_prefixes = tuple(
        prefix if prefix.endswith("/") else prefix + "/"
        for prefix in project_prefixes
    )

    try:
        with zipfile.ZipFile(jar_path) as archive:
            names = archive.namelist()
            coordinates: dict[tuple[str, str, str], dict[str, str]] = {}
            for name in names:
                if (
                    not name.startswith("META-INF/maven/")
                    or not name.endswith("/pom.properties")
                ):
                    continue
                props = _parse_properties(archive.read(name))
                required = ("groupId", "artifactId", "version")
                if not all(props.get(key) for key in required):
                    continue
                key = (
                    props["groupId"],
                    props["artifactId"],
                    props["version"],
                )
                coordinates[key] = {
                    "group_id": key[0],
                    "artifact_id": key[1],
                    "version": key[2],
                    "source_entry": name,
                }

            class_entries = sorted(
                name for name in names if name.endswith(".class")
            )
            project_classes = [
                name
                for name in class_entries
                if any(name.startswith(prefix) for prefix in normalized_prefixes)
            ]
            non_project_classes = [
                name
                for name in class_entries
                if name not in set(project_classes)
            ]

            namespace_counts: dict[str, int] = {}
            for name in non_project_classes:
                parts = name.split("/")
                namespace = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
                namespace_counts[namespace] = (
                    namespace_counts.get(namespace, 0) + 1
                )

    except zipfile.BadZipFile as exc:
        raise DependencyAuthorityError(
            f"invalid JAR/ZIP: {jar_path}"
        ) from exc

    coordinate_rows = [
        coordinates[key] for key in sorted(coordinates)
    ]
    namespace_rows = [
        {"namespace": namespace, "class_count": count}
        for namespace, count in sorted(
            namespace_counts.items(),
            key=lambda row: (-row[1], row[0]),
        )
    ]

    material = {
        "jar_sha256": _sha256_file(jar_path),
        "project_prefixes": list(normalized_prefixes),
        "maven_coordinates": coordinate_rows,
        "class_count": len(class_entries),
        "project_class_count": len(project_classes),
        "non_project_class_count": len(non_project_classes),
        "non_project_namespaces": namespace_rows,
    }
    return {
        "schema_version": 1,
        "kind": "dependency_authority",
        "dependency_authority_id": (
            "DEPAUTH_" + _stable_digest(material)[:20].upper()
        ),
        **material,
    }


def compare_external_class_surfaces(
    left_jar: Path,
    right_jar: Path,
    *,
    project_prefixes: tuple[str, ...] = ("rs/",),
) -> dict[str, Any]:
    normalized_prefixes = tuple(
        prefix if prefix.endswith("/") else prefix + "/"
        for prefix in project_prefixes
    )

    def non_project_map(path: Path) -> dict[str, str]:
        try:
            with zipfile.ZipFile(path) as archive:
                result: dict[str, str] = {}
                for name in archive.namelist():
                    if not name.endswith(".class"):
                        continue
                    if any(
                        name.startswith(prefix)
                        for prefix in normalized_prefixes
                    ):
                        continue
                    result[name] = hashlib.sha256(
                        archive.read(name)
                    ).hexdigest()
                return result
        except zipfile.BadZipFile as exc:
            raise DependencyAuthorityError(
                f"invalid JAR/ZIP: {path}"
            ) from exc

    left = non_project_map(left_jar.resolve())
    right = non_project_map(right_jar.resolve())
    common = sorted(set(left) & set(right))
    equal = [name for name in common if left[name] == right[name]]
    different = [name for name in common if left[name] != right[name]]

    return {
        "left_jar_sha256": _sha256_file(left_jar.resolve()),
        "right_jar_sha256": _sha256_file(right_jar.resolve()),
        "common_non_project_class_count": len(common),
        "byte_identical_common_non_project_class_count": len(equal),
        "different_common_non_project_class_count": len(different),
        "left_only_non_project_classes": sorted(set(left) - set(right)),
        "right_only_non_project_classes": sorted(set(right) - set(left)),
        "different_common_non_project_classes": different,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract exact non-project/dependency authority from a fat client JAR."
        )
    )
    parser.add_argument("jar", type=Path)
    parser.add_argument(
        "--compare",
        type=Path,
        help="Optional second JAR for non-project-class byte comparison.",
    )
    parser.add_argument(
        "--project-prefix",
        action="append",
        default=None,
        help="Project-owned class prefix; repeatable. Default: rs/",
    )
    args = parser.parse_args()

    prefixes = tuple(args.project_prefix or ["rs/"])
    report = scan_dependency_authority(
        args.jar,
        project_prefixes=prefixes,
    )
    if args.compare is not None:
        report["comparison"] = compare_external_class_surfaces(
            args.jar,
            args.compare,
            project_prefixes=prefixes,
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
