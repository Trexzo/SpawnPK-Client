from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from .dependency_artifact_proof import (
    DependencyArtifactProofError,
    _artifact_index,
)
from .dependency_runtime_frontier import (
    DependencyRuntimeFrontierError,
    _artifact_rows_key,
    _load_private_plan,
)
from .decompiler import sha256_file


class DependencyReplacementExtensionError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _load_private(
    path: Path,
    *,
    kind: str,
    label: str,
) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyReplacementExtensionError(
            f"invalid {label} authority"
        ) from exc
    if value.get("kind") != kind:
        raise DependencyReplacementExtensionError(
            f"unexpected {label} authority kind"
        )
    if value.get("identifiers_included") is not True:
        raise DependencyReplacementExtensionError(
            f"{label} authority must include private identifiers"
        )
    return value


def build_dependency_replacement_extension(
    private_replacement_plan_path: Path,
    private_dynamic_mapping_path: Path,
    private_dynamic_member_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    try:
        plan = _load_private_plan(
            private_replacement_plan_path.resolve()
        )
    except DependencyRuntimeFrontierError as exc:
        raise DependencyReplacementExtensionError(str(exc)) from exc

    dynamic = _load_private(
        private_dynamic_mapping_path.resolve(),
        kind="dependency_runtime_dynamic_mapping_proof",
        label="dynamic mapping",
    )
    member = _load_private(
        private_dynamic_member_path.resolve(),
        kind="dependency_runtime_dynamic_member_proof",
        label="dynamic member",
    )

    bundled_jar = bundled_jar.resolve()
    if not bundled_jar.is_file():
        raise DependencyReplacementExtensionError(
            "bundled/readable JAR does not exist"
        )
    bundled_sha = sha256_file(bundled_jar)

    replacement_id = plan.get("replacement_plan_id")
    for label, value in (
        ("DEPREPLACE", plan),
        ("dynamic mapping", dynamic),
        ("dynamic member", member),
    ):
        if value.get("bundled_jar_sha256") != bundled_sha:
            raise DependencyReplacementExtensionError(
                f"{label} is bound to a different bundled JAR"
            )
        if label != "DEPREPLACE" and value.get(
            "replacement_plan_id"
        ) != replacement_id:
            raise DependencyReplacementExtensionError(
                f"{label} is bound to a different DEPREPLACE"
            )

    if member.get("runtime_dynamic_mapping_id") != dynamic.get(
        "runtime_dynamic_mapping_id"
    ):
        raise DependencyReplacementExtensionError(
            "dynamic member authority is bound to a different dynamic mapping"
        )

    release = plan.get("java_release")
    if (
        not isinstance(release, int)
        or isinstance(release, bool)
        or release < 1
    ):
        raise DependencyReplacementExtensionError(
            "private DEPREPLACE has invalid java_release"
        )

    try:
        _official, artifact_by_class, artifact_rows = _artifact_index(
            [path.resolve() for path in official_artifacts],
            java_release=release,
        )
    except DependencyArtifactProofError as exc:
        raise DependencyReplacementExtensionError(str(exc)) from exc

    expected_rows = plan.get("official_artifacts")
    if (
        not isinstance(expected_rows, list)
        or _artifact_rows_key(expected_rows)
        != _artifact_rows_key(artifact_rows)
    ):
        raise DependencyReplacementExtensionError(
            "official artifact authority differs from DEPREPLACE"
        )

    artifact_sha = sorted(
        str(row["sha256"]).lower()
        for row in artifact_rows
    )
    for label, value in (
        ("dynamic mapping", dynamic),
        ("dynamic member", member),
    ):
        if sorted(
            str(item).lower()
            for item in value.get("official_artifact_sha256", [])
        ) != artifact_sha:
            raise DependencyReplacementExtensionError(
                f"{label} official artifact authority drifted"
            )

    original_rows_raw = plan.get("owners")
    if not isinstance(original_rows_raw, list):
        raise DependencyReplacementExtensionError(
            "private DEPREPLACE lacks owner rows"
        )

    original_by_owner: dict[str, dict[str, Any]] = {}
    for row in original_rows_raw:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("old_owner"), str)
        ):
            raise DependencyReplacementExtensionError(
                "malformed DEPREPLACE owner row"
            )
        old_owner = str(row["old_owner"])
        if old_owner in original_by_owner:
            raise DependencyReplacementExtensionError(
                "duplicate DEPREPLACE old owner"
            )
        original_by_owner[old_owner] = row

    member_classes_raw = member.get("classes")
    if not isinstance(member_classes_raw, list):
        raise DependencyReplacementExtensionError(
            "dynamic member authority lacks class rows"
        )
    member_by_mapping_id: dict[str, dict[str, Any]] = {}
    for row in member_classes_raw:
        if (
            not isinstance(row, dict)
            or not isinstance(
                row.get("source_dynamic_mapping_id"),
                str,
            )
        ):
            raise DependencyReplacementExtensionError(
                "malformed dynamic member class row"
            )
        source_id = str(row["source_dynamic_mapping_id"])
        if source_id in member_by_mapping_id:
            raise DependencyReplacementExtensionError(
                "duplicate dynamic member mapping binding"
            )
        member_by_mapping_id[source_id] = row

    dynamic_rows_raw = dynamic.get("rows")
    if not isinstance(dynamic_rows_raw, list):
        raise DependencyReplacementExtensionError(
            "dynamic mapping authority lacks rows"
        )

    accepted_rows = [
        row
        for row in dynamic_rows_raw
        if isinstance(row, dict)
        and row.get("status") == "accepted_class_mapping"
    ]
    accepted_rows.sort(key=lambda row: str(row.get("old_owner", "")))

    public_promoted: list[dict[str, Any]] = []
    private_promoted: list[dict[str, Any]] = []
    public_blocked: list[dict[str, Any]] = []
    private_blocked: list[dict[str, Any]] = []
    public_existing: list[dict[str, Any]] = []
    private_existing: list[dict[str, Any]] = []
    conflict_count = 0
    status_counts: Counter[str] = Counter()

    for index, row in enumerate(accepted_rows, start=1):
        old_owner = row.get("old_owner")
        new_owner = row.get("new_owner")
        artifact = row.get("artifact")
        mapping_id = row.get("dynamic_mapping_id")
        if (
            not isinstance(old_owner, str)
            or not isinstance(new_owner, str)
            or not isinstance(artifact, str)
            or not isinstance(mapping_id, str)
        ):
            raise DependencyReplacementExtensionError(
                "accepted dynamic mapping lacks private identifiers"
            )

        if artifact_by_class.get(new_owner) != artifact:
            raise DependencyReplacementExtensionError(
                "dynamic mapping target disagrees with official artifact authority"
            )

        member_row = member_by_mapping_id.get(mapping_id)
        if member_row is None:
            raise DependencyReplacementExtensionError(
                "accepted dynamic mapping lacks matching member proof row"
            )

        extension_row_id = f"DEPREPLACEEXTROW_{index:05d}"
        complete = (
            member_row.get("member_transport_complete") is True
        )

        prior = original_by_owner.get(old_owner)
        if prior is not None:
            if (
                prior.get("classification")
                != "official_replaceable"
                or prior.get("new_owner") != new_owner
                or prior.get("artifact") != artifact
            ):
                conflict_count += 1
                raise DependencyReplacementExtensionError(
                    "dynamic promotion conflicts with existing DEPREPLACE owner"
                )

            status_counts["already_authorized"] += 1
            public = {
                "extension_row_id": extension_row_id,
                "source_dynamic_mapping_id": mapping_id,
                "source_dynamic_member_class_id": member_row.get(
                    "class_id"
                ),
                "status": "already_authorized",
                "member_transport_complete": complete,
            }
            public_existing.append(public)
            if include_identifiers:
                private_existing.append(
                    {
                        **public,
                        "old_owner": old_owner,
                        "new_owner": new_owner,
                        "artifact": artifact,
                    }
                )
            continue

        if not complete:
            status_counts["promotion_blocked"] += 1
            public = {
                "extension_row_id": extension_row_id,
                "source_dynamic_mapping_id": mapping_id,
                "source_dynamic_member_class_id": member_row.get(
                    "class_id"
                ),
                "status": "promotion_blocked",
                "member_transport_complete": False,
            }
            public_blocked.append(public)
            if include_identifiers:
                private_blocked.append(
                    {
                        **public,
                        "old_owner": old_owner,
                        "new_owner": new_owner,
                        "artifact": artifact,
                    }
                )
            continue

        status_counts["promotion_eligible"] += 1
        public = {
            "extension_row_id": extension_row_id,
            "source_dynamic_mapping_id": mapping_id,
            "source_dynamic_member_class_id": member_row.get(
                "class_id"
            ),
            "classification": "official_replaceable",
            "status": "promotion_eligible",
            "member_transport_complete": True,
            "official_artifact_bound": True,
        }
        public_promoted.append(public)
        if include_identifiers:
            private_promoted.append(
                {
                    **public,
                    "old_owner": old_owner,
                    "new_owner": new_owner,
                    "artifact": artifact,
                }
            )

    ready = (
        conflict_count == 0
        and status_counts.get("promotion_blocked", 0) == 0
        and len(accepted_rows)
        == (
            len(public_promoted)
            + len(public_existing)
        )
    )

    original_public = [
        {
            "owner_id": row.get("owner_id"),
            "classification": row.get("classification"),
        }
        for row in original_rows_raw
    ]

    combined_public = [
        *original_public,
        *[
            {
                "owner_id": row["extension_row_id"],
                "classification": "official_replaceable",
            }
            for row in public_promoted
        ],
    ]
    combined_private = [
        *original_rows_raw,
        *[
            {
                "owner_id": row["extension_row_id"],
                "classification": "official_replaceable",
                "old_owner": row["old_owner"],
                "new_owner": row["new_owner"],
                "artifact": row["artifact"],
                "source_dynamic_mapping_id": row[
                    "source_dynamic_mapping_id"
                ],
                "source_dynamic_member_class_id": row[
                    "source_dynamic_member_class_id"
                ],
            }
            for row in private_promoted
        ],
    ]

    original_official_count = sum(
        row.get("classification") == "official_replaceable"
        for row in original_rows_raw
    )
    combined_official_count = (
        original_official_count + len(public_promoted)
    )

    material = {
        "replacement_plan_id": replacement_id,
        "runtime_dynamic_mapping_id": dynamic.get(
            "runtime_dynamic_mapping_id"
        ),
        "runtime_dynamic_member_id": member.get(
            "runtime_dynamic_member_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": artifact_sha,
        "promoted_rows": public_promoted,
        "blocked_rows": public_blocked,
        "already_authorized_rows": public_existing,
        "ready_for_augmented_closure_reaudit": ready,
    }
    extension_id = (
        "DEPREPLACEEXT_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "dependency_replacement_extension",
        "replacement_extension_id": extension_id,
        "replacement_plan_id": replacement_id,
        "runtime_dynamic_mapping_id": dynamic.get(
            "runtime_dynamic_mapping_id"
        ),
        "runtime_dynamic_member_id": member.get(
            "runtime_dynamic_member_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": artifact_sha,
        "summary": {
            "original_owner_count": len(original_rows_raw),
            "original_official_replaceable_owner_count": (
                original_official_count
            ),
            "accepted_dynamic_class_mapping_count": len(
                accepted_rows
            ),
            "promotion_eligible_count": len(public_promoted),
            "promotion_blocked_count": len(public_blocked),
            "already_authorized_count": len(public_existing),
            "conflict_count": conflict_count,
            "combined_owner_count": len(combined_public),
            "combined_official_replaceable_owner_count": (
                combined_official_count
            ),
            "ready_for_augmented_closure_reaudit": ready,
        },
        "promoted_rows": (
            private_promoted
            if include_identifiers
            else public_promoted
        ),
        "blocked_rows": (
            private_blocked
            if include_identifiers
            else public_blocked
        ),
        "already_authorized_rows": (
            private_existing
            if include_identifiers
            else public_existing
        ),
        "combined_owner_rows": (
            combined_private
            if include_identifiers
            else combined_public
        ),
        "identifiers_included": include_identifiers,
        "note": (
            "This authority extends DEPREPLACE additively for analysis only. "
            "The original DEPREPLACE rows remain unchanged and no runtime "
            "dependency capsule mutation is authorized."
        ),
    }


def write_dependency_replacement_extension(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
