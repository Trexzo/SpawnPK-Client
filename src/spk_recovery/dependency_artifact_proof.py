from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .classfile import ClassFormatError, ParsedClass, parse_class
from .decompiler import sha256_file


class DependencyArtifactProofError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_reference_surface(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyArtifactProofError(
            f"invalid dependency reference surface: {path}"
        ) from exc
    if data.get("kind") != "project_non_project_reference_surface":
        raise DependencyArtifactProofError(
            "reference surface has unexpected kind"
        )
    return data


def _artifact_index(
    jar_paths: list[Path],
    *,
    java_release: int | None,
) -> tuple[dict[str, ParsedClass], dict[str, str], list[dict[str, Any]]]:
    classes: dict[str, ParsedClass] = {}
    owners: dict[str, str] = {}
    artifacts: list[dict[str, Any]] = []

    for raw_path in jar_paths:
        path = raw_path.resolve()
        if not path.is_file():
            raise DependencyArtifactProofError(
                f"official artifact does not exist: {path}"
            )
        artifact_id = path.name
        artifacts.append(
            {
                "artifact": artifact_id,
                "sha256": sha256_file(path),
            }
        )
        try:
            with zipfile.ZipFile(path) as archive:
                variants: dict[str, list[tuple[int, str]]] = {}
                for entry in sorted(
                    name
                    for name in archive.namelist()
                    if name.endswith(".class")
                ):
                    release = 0
                    logical_entry = entry
                    if entry.startswith("META-INF/versions/"):
                        parts = entry.split("/", 3)
                        if len(parts) != 4 or not parts[2].isdigit():
                            raise DependencyArtifactProofError(
                                f"{artifact_id}:{entry}: invalid multi-release class path"
                            )
                        release = int(parts[2])
                        logical_entry = parts[3]
                    if logical_entry == "module-info.class":
                        continue
                    variants.setdefault(logical_entry, []).append(
                        (release, entry)
                    )

                multi_release_class_count = sum(
                    any(release > 0 for release, _ in rows)
                    for rows in variants.values()
                )
                if multi_release_class_count and java_release is None:
                    raise DependencyArtifactProofError(
                        f"{artifact_id}: multi-release JAR requires explicit java_release"
                    )

                selected_entries: list[tuple[str, str]] = []
                for logical_entry, rows in sorted(variants.items()):
                    eligible = [
                        row
                        for row in rows
                        if row[0] == 0
                        or (
                            java_release is not None
                            and row[0] <= java_release
                        )
                    ]
                    if not eligible:
                        continue
                    release, selected = max(
                        eligible,
                        key=lambda row: row[0],
                    )
                    selected_entries.append(
                        (logical_entry, selected)
                    )

                artifacts[-1]["multi_release_class_count"] = (
                    multi_release_class_count
                )
                artifacts[-1]["java_release"] = java_release

                for logical_entry, entry in selected_entries:
                    try:
                        parsed = parse_class(archive.read(entry))
                    except ClassFormatError as exc:
                        raise DependencyArtifactProofError(
                            f"{artifact_id}:{entry}: class parse failed: {exc}"
                        ) from exc
                    if parsed.name + ".class" != logical_entry:
                        raise DependencyArtifactProofError(
                            f"{artifact_id}:{entry}: class identity mismatch"
                        )
                    if parsed.name in classes:
                        prior = owners[parsed.name]
                        raise DependencyArtifactProofError(
                            f"duplicate class {parsed.name} in {prior} and {artifact_id}"
                        )
                    classes[parsed.name] = parsed
                    owners[parsed.name] = artifact_id
        except zipfile.BadZipFile as exc:
            raise DependencyArtifactProofError(
                f"invalid official artifact JAR: {path}"
            ) from exc

    return classes, owners, artifacts


def _hierarchy(
    owner: str,
    classes: dict[str, ParsedClass],
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    queue = [owner]
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


def _member_rows(
    parsed: ParsedClass,
    *,
    kind: str,
) -> list[dict[str, Any]]:
    if kind == "field":
        return parsed.fields
    if kind in {"method", "interface_method"}:
        return parsed.methods
    return []


def _resolve_member(
    *,
    kind: str,
    owner: str,
    name: str,
    descriptor: str,
    classes: dict[str, ParsedClass],
) -> dict[str, Any]:
    if owner not in classes:
        return {
            "status": "missing_owner",
            "resolved_owner": None,
            "descriptor_candidates": [],
        }

    descriptor_candidates: list[dict[str, str]] = []
    for current in _hierarchy(owner, classes):
        parsed = classes[current]
        for row in _member_rows(parsed, kind=kind):
            row_name = str(row.get("name", ""))
            row_desc = str(row.get("descriptor", ""))
            if row_name == name and row_desc == descriptor:
                return {
                    "status": "direct",
                    "resolved_owner": current,
                    "descriptor_candidates": [],
                }
            if row_desc == descriptor:
                descriptor_candidates.append(
                    {
                        "owner": current,
                        "name": row_name,
                    }
                )

    if descriptor_candidates:
        return {
            "status": "structural_remap_required",
            "resolved_owner": None,
            "descriptor_candidates": sorted(
                descriptor_candidates,
                key=lambda row: (row["owner"], row["name"]),
            ),
        }

    return {
        "status": "missing_member",
        "resolved_owner": None,
        "descriptor_candidates": [],
    }


def prove_official_artifact_compatibility(
    reference_surface_path: Path,
    official_artifacts: list[Path],
    *,
    java_release: int | None = None,
) -> dict[str, Any]:
    reference_surface_path = reference_surface_path.resolve()
    surface = _load_reference_surface(reference_surface_path)
    classes, artifact_by_class, artifacts = _artifact_index(
        official_artifacts,
        java_release=java_release,
    )

    class_results: list[dict[str, Any]] = []
    for row in surface.get("class_references", []):
        target = str(row["target"])
        present = target in classes
        class_results.append(
            {
                "target": target,
                "status": "direct" if present else "missing_owner",
                "artifact": artifact_by_class.get(target),
                "source_class_count": int(row.get("source_class_count", 0)),
            }
        )

    member_results: list[dict[str, Any]] = []
    for row in surface.get("member_references", []):
        kind = str(row["kind"])
        owner = str(row["owner"])
        name = str(row["name"])
        descriptor = str(row["descriptor"])
        resolved = _resolve_member(
            kind=kind,
            owner=owner,
            name=name,
            descriptor=descriptor,
            classes=classes,
        )
        member_results.append(
            {
                "kind": kind,
                "owner": owner,
                "name": name,
                "descriptor": descriptor,
                "status": resolved["status"],
                "artifact": artifact_by_class.get(owner),
                "resolved_owner": resolved["resolved_owner"],
                "descriptor_candidates": resolved[
                    "descriptor_candidates"
                ],
                "reference_count": int(row.get("reference_count", 0)),
                "source_class_count": int(row.get("source_class_count", 0)),
            }
        )

    status_counts: dict[str, int] = {}
    weighted_status_counts: dict[str, int] = {}
    for row in member_results:
        status = row["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        weighted_status_counts[status] = (
            weighted_status_counts.get(status, 0)
            + int(row["reference_count"])
        )

    artifact_summary: dict[str, dict[str, int]] = {}
    for row in member_results:
        artifact = row["artifact"] or "<unresolved>"
        bucket = artifact_summary.setdefault(artifact, {})
        status = row["status"]
        bucket[status] = bucket.get(status, 0) + 1

    artifact_rows = [
        {
            "artifact": artifact,
            "member_status_counts": dict(sorted(counts.items())),
        }
        for artifact, counts in sorted(artifact_summary.items())
    ]

    material = {
        "reference_surface_id": surface["reference_surface_id"],
        "reference_surface_sha256": hashlib.sha256(
            reference_surface_path.read_bytes()
        ).hexdigest(),
        "official_artifacts": artifacts,
        "java_release": java_release,
        "class_results": class_results,
        "member_results": member_results,
    }
    return {
        "schema_version": 1,
        "kind": "official_dependency_artifact_proof",
        "artifact_proof_id": (
            "DEPAPIPROOF_" + _stable_digest(material)[:20].upper()
        ),
        "reference_surface_id": surface["reference_surface_id"],
        "official_artifacts": artifacts,
        "java_release": java_release,
        "summary": {
            "class_reference_count": len(class_results),
            "direct_class_reference_count": sum(
                row["status"] == "direct"
                for row in class_results
            ),
            "member_reference_count": len(member_results),
            "member_status_counts": dict(sorted(status_counts.items())),
            "weighted_member_status_counts": dict(
                sorted(weighted_status_counts.items())
            ),
            "artifact_count": len(artifacts),
        },
        "artifact_summary": artifact_rows,
        "class_results": class_results,
        "member_results": member_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prove exact project dependency references against official "
            "dependency artifact JVM APIs."
        )
    )
    parser.add_argument("reference_surface", type=Path)
    parser.add_argument(
        "artifact",
        type=Path,
        nargs="+",
        help="Official dependency JAR; repeat by passing multiple paths.",
    )
    parser.add_argument(
        "--java-release",
        type=int,
        default=None,
        help=(
            "Target Java release used to select multi-release JAR classes. "
            "Required when any supplied artifact is multi-release."
        ),
    )
    args = parser.parse_args()

    report = prove_official_artifact_compatibility(
        args.reference_surface,
        args.artifact,
        java_release=args.java_release,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
