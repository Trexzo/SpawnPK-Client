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
    profile_class_member_accesses,
)
from .classfile import ClassFormatError, ParsedClass, parse_class
from .decompiler import sha256_file


class DependencyApiCompatibilityError(ValueError):
    pass


_ACC_PUBLIC = 0x0001
_ACC_PRIVATE = 0x0002
_ACC_PROTECTED = 0x0004
_ACC_STATIC = 0x0008


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _normalized_prefix(value: str) -> str:
    return value if value.endswith("/") else value + "/"


def _load_manifest(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DependencyApiCompatibilityError(
            f"invalid artifact manifest: {exc}"
        ) from exc
    if value.get("schema_version") != 1:
        raise DependencyApiCompatibilityError(
            "artifact manifest schema_version must be 1"
        )
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise DependencyApiCompatibilityError(
            "artifact manifest must contain a non-empty artifacts list"
        )
    return value, hashlib.sha256(raw).hexdigest()


def _artifact_path(manifest_path: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve()


def _expected_static(operation: str) -> bool:
    return operation in {"getstatic", "putstatic", "invokestatic"}


def _declaration_access_status(
    access: int,
) -> str | None:
    if access & _ACC_PUBLIC:
        return None
    if access & _ACC_PROTECTED:
        return "protected_access_context_unresolved"
    if access & _ACC_PRIVATE:
        return "non_public_member"
    return "package_private_member"


def _matching_declaration(
    parsed: ParsedClass,
    *,
    kind: str,
    name: str,
    descriptor: str,
) -> dict[str, Any] | None:
    rows = parsed.fields if kind == "field" else parsed.methods
    for row in rows:
        if (
            row.get("name") == name
            and row.get("descriptor") == descriptor
        ):
            return row
    return None


def _resolve_member(
    classes: dict[str, dict[str, Any]],
    *,
    owner: str,
    kind: str,
    operation: str,
    name: str,
    descriptor: str,
) -> dict[str, Any]:
    owner_record = classes.get(owner)
    if owner_record is None:
        return {
            "status": "owner_absent",
            "declaring_owner": None,
            "artifact": None,
            "external_ancestors": [],
        }

    owner_class: ParsedClass = owner_record["parsed"]
    if not (owner_class.access & _ACC_PUBLIC):
        return {
            "status": "owner_non_public",
            "declaring_owner": owner,
            "artifact": owner_record["artifact_label"],
            "external_ancestors": [],
        }

    if name == "<init>":
        declaration = _matching_declaration(
            owner_class,
            kind="method",
            name=name,
            descriptor=descriptor,
        )
        if declaration is None:
            return {
                "status": "member_absent",
                "declaring_owner": None,
                "artifact": owner_record["artifact_label"],
                "external_ancestors": [],
            }
        if int(declaration.get("access", 0)) & _ACC_STATIC:
            return {
                "status": "invocation_shape_mismatch",
                "declaring_owner": owner,
                "artifact": owner_record["artifact_label"],
                "external_ancestors": [],
            }
        access_status = _declaration_access_status(
            int(declaration.get("access", 0))
        )
        return {
            "status": access_status or "resolved_exact",
            "declaring_owner": owner,
            "artifact": owner_record["artifact_label"],
            "external_ancestors": [],
        }

    queue = [owner]
    visited: set[str] = set()
    external_ancestors: set[str] = set()
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        record = classes.get(current)
        if record is None:
            if current != "java/lang/Object":
                external_ancestors.add(current)
            continue

        parsed: ParsedClass = record["parsed"]
        declaration = _matching_declaration(
            parsed,
            kind=kind,
            name=name,
            descriptor=descriptor,
        )
        if declaration is not None:
            access = int(declaration.get("access", 0))
            declaration_static = bool(access & _ACC_STATIC)
            if declaration_static != _expected_static(operation):
                return {
                    "status": "invocation_shape_mismatch",
                    "declaring_owner": current,
                    "artifact": record["artifact_label"],
                    "external_ancestors": sorted(
                        external_ancestors
                    ),
                }
            access_status = _declaration_access_status(access)
            if not (parsed.access & _ACC_PUBLIC):
                access_status = "declaring_class_non_public"
            return {
                "status": access_status or "resolved_exact",
                "declaring_owner": current,
                "artifact": record["artifact_label"],
                "external_ancestors": sorted(external_ancestors),
            }

        next_names: list[str] = []
        if parsed.super_name:
            next_names.append(parsed.super_name)
        next_names.extend(parsed.interfaces)
        for next_name in next_names:
            if next_name not in visited:
                queue.append(next_name)

    return {
        "status": (
            "external_ancestor_unresolved"
            if external_ancestors
            else "member_absent"
        ),
        "declaring_owner": None,
        "artifact": owner_record["artifact_label"],
        "external_ancestors": sorted(external_ancestors),
    }


def _family_for_owner(
    owner: str,
    *,
    classes: dict[str, dict[str, Any]],
    prefix_rows: list[tuple[str, str]],
) -> str | None:
    record = classes.get(owner)
    if record is not None:
        return str(record["family"])

    matches = [
        (prefix, family)
        for prefix, family in prefix_rows
        if owner.startswith(prefix)
    ]
    if not matches:
        return None
    max_length = max(len(prefix) for prefix, _ in matches)
    families = {
        family
        for prefix, family in matches
        if len(prefix) == max_length
    }
    if len(families) != 1:
        raise DependencyApiCompatibilityError(
            f"ambiguous family prefixes for owner {owner!r}: "
            + ", ".join(sorted(families))
        )
    return next(iter(families))


def analyze_dependency_api_compatibility(
    client_jar: Path,
    artifact_manifest: Path,
    *,
    project_prefixes: tuple[str, ...] = ("rs/",),
) -> dict[str, Any]:
    client_jar = client_jar.resolve()
    artifact_manifest = artifact_manifest.resolve()
    if not client_jar.is_file():
        raise DependencyApiCompatibilityError(
            f"client JAR does not exist: {client_jar}"
        )
    if not artifact_manifest.is_file():
        raise DependencyApiCompatibilityError(
            f"artifact manifest does not exist: {artifact_manifest}"
        )

    manifest, manifest_sha = _load_manifest(artifact_manifest)
    normalized_project_prefixes = tuple(
        _normalized_prefix(prefix)
        for prefix in project_prefixes
    )

    classes: dict[str, dict[str, Any]] = {}
    prefix_rows: list[tuple[str, str]] = []
    artifact_rows: list[dict[str, Any]] = []

    for index, spec in enumerate(manifest["artifacts"]):
        if not isinstance(spec, dict):
            raise DependencyApiCompatibilityError(
                f"artifact row {index} is not an object"
            )
        family = str(spec.get("family", "")).strip()
        coordinate = str(spec.get("coordinate", "")).strip()
        jar_value = str(spec.get("path", "")).strip()
        expected_sha = str(spec.get("sha256", "")).lower().strip()
        prefixes = spec.get("namespace_prefixes")
        if (
            not family
            or not coordinate
            or not jar_value
            or len(expected_sha) != 64
            or not isinstance(prefixes, list)
            or not prefixes
        ):
            raise DependencyApiCompatibilityError(
                f"artifact row {index} is incomplete"
            )

        jar_path = _artifact_path(artifact_manifest, jar_value)
        if not jar_path.is_file():
            raise DependencyApiCompatibilityError(
                f"artifact is absent: {jar_path}"
            )
        actual_sha = sha256_file(jar_path)
        if actual_sha.lower() != expected_sha:
            raise DependencyApiCompatibilityError(
                f"artifact SHA mismatch for {coordinate}: "
                f"expected {expected_sha}, got {actual_sha}"
            )

        normalized_family_prefixes = [
            _normalized_prefix(str(prefix))
            for prefix in prefixes
        ]
        prefix_rows.extend(
            (prefix, family)
            for prefix in normalized_family_prefixes
        )
        artifact_label = f"{coordinate}@{actual_sha}"

        class_count = 0
        try:
            with zipfile.ZipFile(jar_path) as archive:
                for entry in sorted(archive.namelist()):
                    if not entry.endswith(".class"):
                        continue
                    try:
                        parsed = parse_class(archive.read(entry))
                    except ClassFormatError as exc:
                        raise DependencyApiCompatibilityError(
                            f"{coordinate}:{entry}: class parse failed: "
                            f"{exc}"
                        ) from exc
                    if not parsed.name:
                        continue
                    existing = classes.get(parsed.name)
                    if existing is not None:
                        raise DependencyApiCompatibilityError(
                            "duplicate official class ownership: "
                            f"{parsed.name} in "
                            f"{existing['artifact_label']} and "
                            f"{artifact_label}"
                        )
                    classes[parsed.name] = {
                        "parsed": parsed,
                        "family": family,
                        "artifact_label": artifact_label,
                    }
                    class_count += 1
        except zipfile.BadZipFile as exc:
            raise DependencyApiCompatibilityError(
                f"invalid artifact JAR: {jar_path}"
            ) from exc

        artifact_rows.append(
            {
                "index": index,
                "family": family,
                "coordinate": coordinate,
                "sha256": actual_sha,
                "namespace_prefixes": normalized_family_prefixes,
                "class_count": class_count,
            }
        )

    prefix_rows.sort(
        key=lambda row: (-len(row[0]), row[0], row[1])
    )

    access_rows: list[dict[str, Any]] = []
    class_reference_rows: list[dict[str, Any]] = []
    family_counts: dict[str, dict[str, int]] = {}

    def add_family_count(
        family: str,
        key: str,
        count: int = 1,
    ) -> None:
        row = family_counts.setdefault(family, {})
        row[key] = row.get(key, 0) + count

    try:
        with zipfile.ZipFile(client_jar) as archive:
            project_entries = sorted(
                entry
                for entry in archive.namelist()
                if entry.endswith(".class")
                and any(
                    entry.startswith(prefix)
                    for prefix in normalized_project_prefixes
                )
            )
            for entry in project_entries:
                data = archive.read(entry)
                try:
                    cp_profile = profile_class_constant_pool_references(
                        data
                    )
                    member_profile = profile_class_member_accesses(data)
                except BytecodeProfileError as exc:
                    raise DependencyApiCompatibilityError(
                        f"{entry}: bytecode profile failed: {exc}"
                    ) from exc

                source_class = str(member_profile["internal_name"])
                for target in cp_profile["class_references"]:
                    target = str(target)
                    family = _family_for_owner(
                        target,
                        classes=classes,
                        prefix_rows=prefix_rows,
                    )
                    if family is None:
                        continue
                    present = target in classes
                    class_reference_rows.append(
                        {
                            "source_class": source_class,
                            "target_class": target,
                            "family": family,
                            "status": (
                                "class_present"
                                if present
                                else "class_absent"
                            ),
                        }
                    )
                    add_family_count(
                        family,
                        (
                            "class_present"
                            if present
                            else "class_absent"
                        ),
                    )

                for access in member_profile["member_accesses"]:
                    owner = str(access["owner"])
                    family = _family_for_owner(
                        owner,
                        classes=classes,
                        prefix_rows=prefix_rows,
                    )
                    if family is None:
                        continue
                    resolution = _resolve_member(
                        classes,
                        owner=owner,
                        kind=str(access["kind"]),
                        operation=str(access["operation"]),
                        name=str(access["name"]),
                        descriptor=str(access["descriptor"]),
                    )
                    row = {
                        "source_class": source_class,
                        "source_method_name": access[
                            "source_method_name"
                        ],
                        "source_method_descriptor": access[
                            "source_method_descriptor"
                        ],
                        "family": family,
                        "kind": access["kind"],
                        "operation": access["operation"],
                        "owner": owner,
                        "name": access["name"],
                        "descriptor": access["descriptor"],
                        **resolution,
                    }
                    access_rows.append(row)
                    add_family_count(
                        family,
                        str(resolution["status"]),
                    )
    except zipfile.BadZipFile as exc:
        raise DependencyApiCompatibilityError(
            f"invalid client JAR: {client_jar}"
        ) from exc

    family_rows: list[dict[str, Any]] = []
    families = sorted(
        {
            str(row["family"])
            for row in artifact_rows
        }
        | set(family_counts)
    )
    blocking_statuses = {
        "class_absent",
        "owner_absent",
        "member_absent",
        "invocation_shape_mismatch",
        "owner_non_public",
        "declaring_class_non_public",
        "non_public_member",
        "package_private_member",
        "protected_access_context_unresolved",
        "external_ancestor_unresolved",
    }
    for family in families:
        counts = dict(
            sorted(family_counts.get(family, {}).items())
        )
        in_scope = sum(counts.values())
        blocking = sum(
            value
            for key, value in counts.items()
            if key in blocking_statuses
        )
        if in_scope == 0:
            classification = "no_project_references"
        elif blocking == 0:
            classification = "direct_api_compatible"
        elif counts.get("external_ancestor_unresolved", 0) and (
            blocking
            == counts.get("external_ancestor_unresolved", 0)
        ):
            classification = "external_ancestor_proof_required"
        else:
            classification = "remap_or_additional_proof_required"
        family_rows.append(
            {
                "family": family,
                "classification": classification,
                "counts": counts,
            }
        )

    access_rows.sort(
        key=lambda row: (
            row["family"],
            row["source_class"],
            row["source_method_name"],
            row["owner"],
            row["kind"],
            row["operation"],
            row["name"],
            row["descriptor"],
        )
    )
    class_reference_rows.sort(
        key=lambda row: (
            row["family"],
            row["source_class"],
            row["target_class"],
        )
    )

    material = {
        "client_jar_sha256": sha256_file(client_jar),
        "artifact_manifest_sha256": manifest_sha,
        "project_prefixes": list(normalized_project_prefixes),
        "artifacts": artifact_rows,
        "official_class_count": len(classes),
        "project_class_count": len(project_entries),
        "family_summary": family_rows,
        "class_references": class_reference_rows,
        "member_accesses": access_rows,
    }
    return {
        "schema_version": 1,
        "kind": "dependency_api_compatibility",
        "dependency_api_compatibility_id": (
            "DEPAPICOMPAT_" + _stable_digest(material)[:20].upper()
        ),
        **material,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare exact project dependency accesses against "
            "hash-bound official dependency artifacts."
        )
    )
    parser.add_argument("client_jar", type=Path)
    parser.add_argument("artifact_manifest", type=Path)
    parser.add_argument(
        "--project-prefix",
        action="append",
        default=None,
        help="Project-owned class prefix; repeatable. Default: rs/.",
    )
    args = parser.parse_args()
    prefixes = tuple(args.project_prefix or ["rs/"])
    report = analyze_dependency_api_compatibility(
        args.client_jar,
        args.artifact_manifest,
        project_prefixes=prefixes,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
