from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .bytecode_profile import (
    BytecodeProfileError,
    profile_class_constant_pool_references,
)
from .decompiler import sha256_file


class DependencyReferenceSurfaceError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _normalized_prefixes(
    project_prefixes: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        prefix if prefix.endswith("/") else prefix + "/"
        for prefix in project_prefixes
    )


def _is_project(
    internal_name: str,
    project_prefixes: tuple[str, ...],
) -> bool:
    return any(
        internal_name.startswith(prefix)
        for prefix in project_prefixes
    )


def _namespace(internal_name: str) -> str:
    package_parts = internal_name.split("/")[:-1]
    if len(package_parts) >= 2:
        return "/".join(package_parts[:2])
    if package_parts:
        return package_parts[0]
    return "<default>"


def scan_project_reference_surface(
    jar_path: Path,
    *,
    project_prefixes: tuple[str, ...] = ("rs/",),
) -> dict[str, Any]:
    jar_path = jar_path.resolve()
    if not jar_path.is_file():
        raise DependencyReferenceSurfaceError(
            f"JAR does not exist: {jar_path}"
        )

    prefixes = _normalized_prefixes(project_prefixes)
    class_sources: dict[str, set[str]] = {}
    member_counts: dict[
        tuple[str, str, str, str],
        int,
    ] = {}
    member_sources: dict[
        tuple[str, str, str, str],
        set[str],
    ] = {}
    owner_counts: dict[str, int] = {}
    namespace_counts: dict[str, int] = {}

    try:
        with zipfile.ZipFile(jar_path) as archive:
            project_entries = sorted(
                name
                for name in archive.namelist()
                if name.endswith(".class")
                and any(
                    name.startswith(prefix)
                    for prefix in prefixes
                )
            )

            for entry in project_entries:
                try:
                    profile = profile_class_constant_pool_references(
                        archive.read(entry)
                    )
                except BytecodeProfileError as exc:
                    raise DependencyReferenceSurfaceError(
                        f"{entry}: constant-pool reference profile failed: "
                        f"{exc}"
                    ) from exc

                source_class = str(profile["internal_name"])
                if source_class + ".class" != entry:
                    raise DependencyReferenceSurfaceError(
                        f"{entry}: class identity mismatch: "
                        f"{source_class}"
                    )

                for target in profile["class_references"]:
                    target = str(target)
                    if _is_project(target, prefixes):
                        continue
                    class_sources.setdefault(target, set()).add(
                        source_class
                    )

                for row in profile["member_references"]:
                    owner = str(row["owner"])
                    if _is_project(owner, prefixes):
                        continue
                    key = (
                        str(row["kind"]),
                        owner,
                        str(row["name"]),
                        str(row["descriptor"]),
                    )
                    member_counts[key] = member_counts.get(key, 0) + 1
                    member_sources.setdefault(key, set()).add(
                        source_class
                    )
                    owner_counts[owner] = owner_counts.get(owner, 0) + 1
                    namespace = _namespace(owner)
                    namespace_counts[namespace] = (
                        namespace_counts.get(namespace, 0) + 1
                    )
    except zipfile.BadZipFile as exc:
        raise DependencyReferenceSurfaceError(
            f"invalid JAR/ZIP: {jar_path}"
        ) from exc

    class_rows = [
        {
            "target": target,
            "source_class_count": len(sources),
            "source_classes": sorted(sources),
        }
        for target, sources in sorted(class_sources.items())
    ]
    member_rows = [
        {
            "kind": key[0],
            "owner": key[1],
            "name": key[2],
            "descriptor": key[3],
            "reference_count": member_counts[key],
            "source_class_count": len(member_sources[key]),
            "source_classes": sorted(member_sources[key]),
        }
        for key in sorted(member_counts)
    ]
    owner_rows = [
        {"owner": owner, "reference_count": count}
        for owner, count in sorted(
            owner_counts.items(),
            key=lambda row: (-row[1], row[0]),
        )
    ]
    namespace_rows = [
        {"namespace": namespace, "reference_count": count}
        for namespace, count in sorted(
            namespace_counts.items(),
            key=lambda row: (-row[1], row[0]),
        )
    ]

    material = {
        "jar_sha256": sha256_file(jar_path),
        "project_prefixes": list(prefixes),
        "project_class_count": len(project_entries),
        "non_project_class_reference_count": sum(
            len(sources)
            for sources in class_sources.values()
        ),
        "unique_non_project_class_reference_count": len(class_rows),
        "non_project_member_reference_count": sum(
            member_counts.values()
        ),
        "unique_non_project_member_reference_count": len(member_rows),
        "class_references": class_rows,
        "member_references": member_rows,
        "owner_reference_counts": owner_rows,
        "namespace_reference_counts": namespace_rows,
    }
    return {
        "schema_version": 1,
        "kind": "project_non_project_reference_surface",
        "reference_surface_id": (
            "DEPREF_" + _stable_digest(material)[:20].upper()
        ),
        **material,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract exact project-to-non-project JVM class/member "
            "reference authority from a client JAR."
        )
    )
    parser.add_argument("jar", type=Path)
    parser.add_argument(
        "--project-prefix",
        action="append",
        default=None,
        help="Project-owned class prefix; repeatable. Default: rs/",
    )
    args = parser.parse_args()

    prefixes = tuple(args.project_prefix or ["rs/"])
    report = scan_project_reference_surface(
        args.jar,
        project_prefixes=prefixes,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
