from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

from .decompiler import sha256_file
from .dependency_artifact_proof import (
    DependencyArtifactProofError,
    _artifact_index,
)
from .dependency_remap_proof import (
    DependencyRemapProofError,
    _bundled_index,
    _class_mappings,
)


class DependencyReplacementPlanError(ValueError):
    pass


_ACCEPTED_MEMBER_STATUSES = {
    "accepted_identity",
    "accepted_remap",
    "official_unbundled_direct",
}

_UNRESOLVED_MEMBER_STATUSES = {
    "bundled_unresolved_class",
    "bundled_member_unresolved",
    "bundled_member_not_declared",
    "bundled_member_ambiguous",
    "external_hierarchy_member",
}


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_json(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyReplacementPlanError(
            f"invalid JSON authority: {path}"
        ) from exc
    if data.get("kind") != kind:
        raise DependencyReplacementPlanError(
            f"{path}: expected kind {kind!r}, "
            f"got {data.get('kind')!r}"
        )
    return data


def _artifact_rows_key(
    rows: list[dict[str, Any]],
) -> list[tuple[str, str, int, int | None]]:
    return sorted(
        (
            str(row.get("artifact")),
            str(row.get("sha256")),
            int(row.get("multi_release_class_count", 0)),
            (
                int(row["java_release"])
                if row.get("java_release") is not None
                else None
            ),
        )
        for row in rows
    )


def _normalize_prefixes(values: list[str]) -> tuple[str, ...]:
    out: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise DependencyReplacementPlanError(
                "project prefix must be a non-empty string"
            )
        normalized = value.replace("\\", "/").lstrip("/")
        if not normalized.endswith("/"):
            normalized += "/"
        out.append(normalized)
    if not out:
        raise DependencyReplacementPlanError(
            "project prefix set must not be empty"
        )
    return tuple(sorted(set(out)))


def _is_project(
    internal: str,
    prefixes: tuple[str, ...],
) -> bool:
    return any(internal.startswith(prefix) for prefix in prefixes)


def _retained_owner_set(
    retention: dict[str, Any] | None,
) -> set[str]:
    if retention is None:
        return set()
    return {
        str(row["class"])
        for row in retention.get("classifications", [])
    }


def build_dependency_replacement_plan(
    reference_surface_path: Path,
    dependency_remap_report_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    retention_report_path: Path | None = None,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    reference_surface_path = reference_surface_path.resolve()
    dependency_remap_report_path = (
        dependency_remap_report_path.resolve()
    )
    bundled_jar = bundled_jar.resolve()
    retention_report_path = (
        retention_report_path.resolve()
        if retention_report_path is not None
        else None
    )

    surface = _load_json(
        reference_surface_path,
        kind="project_non_project_reference_surface",
    )
    remap = _load_json(
        dependency_remap_report_path,
        kind="dependency_structural_remap_proof",
    )
    retention = (
        _load_json(
            retention_report_path,
            kind="dependency_source_retention_classification",
        )
        if retention_report_path is not None
        else None
    )

    if remap.get("reference_surface_id") != surface.get(
        "reference_surface_id"
    ):
        raise DependencyReplacementPlanError(
            "DEPREMAP is bound to a different DEPREF"
        )
    bundled_sha = sha256_file(bundled_jar)
    if remap.get("bundled_jar_sha256") != bundled_sha:
        raise DependencyReplacementPlanError(
            "DEPREMAP is bound to a different bundled JAR"
        )

    release = remap.get("java_release")
    if (
        not isinstance(release, int)
        or isinstance(release, bool)
        or release < 1
    ):
        raise DependencyReplacementPlanError(
            "DEPREMAP has invalid java_release"
        )

    prefixes = _normalize_prefixes(
        list(remap.get("project_prefixes", []))
    )

    try:
        official, artifact_by_class, artifact_rows = _artifact_index(
            official_artifacts,
            java_release=release,
        )
        bundled = _bundled_index(
            bundled_jar,
            project_prefixes=prefixes,
        )
    except (
        DependencyArtifactProofError,
        DependencyRemapProofError,
    ) as exc:
        raise DependencyReplacementPlanError(str(exc)) from exc

    if _artifact_rows_key(
        list(remap.get("official_artifacts", []))
    ) != _artifact_rows_key(artifact_rows):
        raise DependencyReplacementPlanError(
            "official artifact set disagrees with DEPREMAP authority"
        )

    if retention is not None:
        if retention.get("reference_surface_id") != surface.get(
            "reference_surface_id"
        ):
            raise DependencyReplacementPlanError(
                "DEPRETAIN is bound to a different DEPREF"
            )
        if retention.get("dependency_remap_proof_id") != remap.get(
            "dependency_remap_proof_id"
        ):
            raise DependencyReplacementPlanError(
                "DEPRETAIN is bound to a different DEPREMAP"
            )
        if retention.get("bundled_jar_sha256") != bundled_sha:
            raise DependencyReplacementPlanError(
                "DEPRETAIN is bound to a different bundled JAR"
            )
        if int(retention.get("java_release", -1)) != release:
            raise DependencyReplacementPlanError(
                "DEPRETAIN java_release disagrees"
            )
        if _artifact_rows_key(
            list(retention.get("official_artifacts", []))
        ) != _artifact_rows_key(artifact_rows):
            raise DependencyReplacementPlanError(
                "DEPRETAIN official artifact set disagrees"
            )

    member_rows_by_owner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in remap.get("member_results", []):
        owner = str(row.get("old_owner"))
        if not owner or owner == "None":
            raise DependencyReplacementPlanError(
                "DEPREMAP member row lacks old_owner"
            )
        member_rows_by_owner[owner].append(row)

    class_reference_owners = {
        str(row["target"])
        for row in surface.get("class_references", [])
    }
    member_reference_owners = {
        str(row["owner"])
        for row in surface.get("member_references", [])
    }
    referenced_owners = sorted(
        class_reference_owners | member_reference_owners
    )

    if any(_is_project(owner, prefixes) for owner in referenced_owners):
        raise DependencyReplacementPlanError(
            "DEPREF contains project-owned owner"
        )

    mapped_member_owner_names = set(member_rows_by_owner)
    if mapped_member_owner_names != member_reference_owners:
        missing = sorted(
            member_reference_owners - mapped_member_owner_names
        )
        extra = sorted(
            mapped_member_owner_names - member_reference_owners
        )
        raise DependencyReplacementPlanError(
            "DEPREMAP member-owner surface differs from DEPREF: "
            f"missing={missing[:5]!r} extra={extra[:5]!r}"
        )

    try:
        mappings, _mapping_summary = _class_mappings(
            bundled,
            official,
            artifact_by_class,
            package_api_candidate_names=member_reference_owners,
        )
    except DependencyRemapProofError as exc:
        raise DependencyReplacementPlanError(str(exc)) from exc

    retained = _retained_owner_set(retention)

    classifications: list[tuple[str, dict[str, Any]]] = []
    for owner in referenced_owners:
        rows = member_rows_by_owner.get(owner, [])
        statuses = sorted(
            {str(row.get("status")) for row in rows}
        )
        weighted = sum(
            int(row.get("reference_count", 0))
            for row in rows
        )

        owner_is_bundled = owner in bundled
        owner_is_official = owner in official
        mapping = mappings.get(owner)

        if owner in retained:
            if mapping is not None:
                raise DependencyReplacementPlanError(
                    "DEPRETAIN owner also has accepted official mapping"
                )
            classification = "project_retained"
            artifact = None
            new_owner = None
        elif not owner_is_bundled:
            if owner_is_official:
                if any(
                    status not in _ACCEPTED_MEMBER_STATUSES
                    for status in statuses
                ):
                    raise DependencyReplacementPlanError(
                        "unbundled official owner has non-accepted member status"
                    )
                classification = "official_replaceable"
                artifact = artifact_by_class.get(owner)
                new_owner = owner
            else:
                if any(
                    status != "platform_runtime"
                    for status in statuses
                ):
                    raise DependencyReplacementPlanError(
                        "non-bundled/non-official owner is not platform_runtime"
                    )
                classification = "platform_runtime"
                artifact = None
                new_owner = None
        else:
            unresolved = [
                status
                for status in statuses
                if status not in _ACCEPTED_MEMBER_STATUSES
            ]
            if mapping is not None and not unresolved:
                classification = "official_replaceable"
                artifact = mapping.get("artifact")
                new_owner = str(mapping.get("new_name"))
                if not artifact or new_owner not in official:
                    raise DependencyReplacementPlanError(
                        "accepted mapping lacks official artifact target"
                    )
            else:
                if any(
                    status not in _UNRESOLVED_MEMBER_STATUSES
                    and status not in _ACCEPTED_MEMBER_STATUSES
                    for status in statuses
                ):
                    raise DependencyReplacementPlanError(
                        "unsupported DEPREMAP member status"
                    )
                classification = "residual_bundled"
                artifact = None
                new_owner = None

        classifications.append(
            (
                owner,
                {
                    "classification": classification,
                    "class_reference_present": (
                        owner in class_reference_owners
                    ),
                    "member_reference_row_count": len(rows),
                    "weighted_member_reference_count": weighted,
                    "member_statuses": statuses,
                    "artifact": artifact,
                    "new_owner": new_owner,
                },
            )
        )

    artifact_names = sorted(
        {
            str(row["artifact"])
            for _owner, row in classifications
            if row["classification"] == "official_replaceable"
            and row["artifact"] is not None
        }
    )
    artifact_ids = {
        name: f"DEPARTIFACT_{index:04d}"
        for index, name in enumerate(artifact_names, start=1)
    }

    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    for index, (owner, row) in enumerate(
        classifications,
        start=1,
    ):
        public = {
            "owner_id": f"DEPOWNER_{index:05d}",
            "classification": row["classification"],
            "class_reference_present": row[
                "class_reference_present"
            ],
            "member_reference_row_count": row[
                "member_reference_row_count"
            ],
            "weighted_member_reference_count": row[
                "weighted_member_reference_count"
            ],
            "member_statuses": row["member_statuses"],
            "artifact_id": (
                artifact_ids.get(str(row["artifact"]))
                if row["artifact"] is not None
                else None
            ),
            "owner_remapped": (
                row["new_owner"] is not None
                and row["new_owner"] != owner
            ),
        }
        public_rows.append(public)

        if include_identifiers:
            private_rows.append(
                {
                    **public,
                    "old_owner": owner,
                    "new_owner": row["new_owner"],
                    "artifact": row["artifact"],
                }
            )

    class_counts = Counter(
        row["classification"]
        for row in public_rows
    )
    weighted_counts = Counter()
    for row in public_rows:
        weighted_counts[row["classification"]] += int(
            row["weighted_member_reference_count"]
        )

    artifact_usage = Counter(
        row["artifact_id"]
        for row in public_rows
        if row["artifact_id"] is not None
    )

    artifact_set_material = [
        {
            "artifact": row["artifact"],
            "sha256": row["sha256"],
            "multi_release_class_count": row.get(
                "multi_release_class_count",
                0,
            ),
            "java_release": row.get("java_release"),
        }
        for row in sorted(
            artifact_rows,
            key=lambda item: str(item["artifact"]),
        )
    ]
    artifact_set_sha256 = _stable_digest(
        artifact_set_material
    )

    public_material = {
        "reference_surface_id": surface["reference_surface_id"],
        "dependency_remap_proof_id": remap[
            "dependency_remap_proof_id"
        ],
        "retention_report_id": (
            retention.get("retention_report_id")
            if retention is not None
            else None
        ),
        "bundled_jar_sha256": bundled_sha,
        "java_release": release,
        "official_artifact_set_sha256": artifact_set_sha256,
        "project_prefixes": list(prefixes),
        "owners": public_rows,
        "artifact_usage": dict(sorted(artifact_usage.items())),
    }

    report: dict[str, Any] = {
        "schema_version": 1,
        "kind": "dependency_replacement_boundary_plan",
        "replacement_plan_id": (
            "DEPREPLACE_"
            + _stable_digest(public_material)[:20].upper()
        ),
        "reference_surface_id": surface["reference_surface_id"],
        "dependency_remap_proof_id": remap[
            "dependency_remap_proof_id"
        ],
        "retention_report_id": (
            retention.get("retention_report_id")
            if retention is not None
            else None
        ),
        "bundled_jar_sha256": bundled_sha,
        "java_release": release,
        "project_prefixes": list(prefixes),
        "official_artifact_set_sha256": artifact_set_sha256,
        "summary": {
            "referenced_owner_count": len(public_rows),
            "classification_counts": dict(
                sorted(class_counts.items())
            ),
            "weighted_member_reference_counts": dict(
                sorted(weighted_counts.items())
            ),
            "official_artifact_count": len(artifact_rows),
            "used_official_artifact_count": len(artifact_usage),
            "official_replaceable_owner_count": class_counts.get(
                "official_replaceable",
                0,
            ),
            "residual_bundled_owner_count": class_counts.get(
                "residual_bundled",
                0,
            ),
            "project_retained_owner_count": class_counts.get(
                "project_retained",
                0,
            ),
            "platform_runtime_owner_count": class_counts.get(
                "platform_runtime",
                0,
            ),
        },
        "artifact_usage": dict(sorted(artifact_usage.items())),
        "owners": (
            private_rows
            if include_identifiers
            else public_rows
        ),
        "identifiers_included": include_identifiers,
    }

    if include_identifiers:
        report["official_artifacts"] = artifact_set_material
        report["artifact_ids"] = artifact_ids
    else:
        report["official_artifacts"] = None
        report["artifact_ids"] = None

    return report


def write_dependency_replacement_plan(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
