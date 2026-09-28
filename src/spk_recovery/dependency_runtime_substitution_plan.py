from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile


class DependencyRuntimeSubstitutionPlanError(ValueError):
    pass


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


def _load_json(
    path: Path,
    *,
    kind: str,
    label: str,
    identifiers_required: bool = False,
) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRuntimeSubstitutionPlanError(
            f"invalid {label} authority"
        ) from exc
    if value.get("kind") != kind:
        raise DependencyRuntimeSubstitutionPlanError(
            f"unexpected {label} authority kind"
        )
    if identifiers_required and value.get("identifiers_included") is not True:
        raise DependencyRuntimeSubstitutionPlanError(
            f"{label} authority must include private identifiers"
        )
    return value


def _redacted_id(prefix: str, *parts: str) -> str:
    raw = "\0".join(parts).encode("utf-8")
    return prefix + hashlib.sha256(raw).hexdigest()[:18].upper()


def _required_id(
    report: dict[str, Any],
    key: str,
    *,
    label: str,
) -> str:
    value = report.get(key)
    if not isinstance(value, str) or not value:
        raise DependencyRuntimeSubstitutionPlanError(
            f"{label} lacks valid {key}"
        )
    return value


def _zip_entries(path: Path) -> dict[str, zipfile.ZipInfo]:
    try:
        with zipfile.ZipFile(path) as archive:
            out: dict[str, zipfile.ZipInfo] = {}
            for info in archive.infolist():
                if info.is_dir():
                    continue
                if info.filename in out:
                    raise DependencyRuntimeSubstitutionPlanError(
                        f"duplicate ZIP entry: {info.filename}"
                    )
                out[info.filename] = info
            return out
    except zipfile.BadZipFile as exc:
        raise DependencyRuntimeSubstitutionPlanError(
            f"invalid JAR/ZIP: {path}"
        ) from exc


def build_dependency_runtime_substitution_plan(
    readiness_path: Path,
    private_replacement_plan_path: Path,
    private_replacement_extension_path: Path,
    private_extended_closure_path: Path,
    private_extended_resource_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    readiness = _load_json(
        readiness_path.resolve(),
        kind="dependency_runtime_substitution_readiness",
        label="runtime readiness",
    )
    plan = _load_json(
        private_replacement_plan_path.resolve(),
        kind="dependency_replacement_boundary_plan",
        label="replacement plan",
        identifiers_required=True,
    )
    extension = _load_json(
        private_replacement_extension_path.resolve(),
        kind="dependency_replacement_extension",
        label="replacement extension",
        identifiers_required=True,
    )
    closure = _load_json(
        private_extended_closure_path.resolve(),
        kind="dependency_runtime_extended_closure",
        label="extended closure",
        identifiers_required=True,
    )
    resource = _load_json(
        private_extended_resource_path.resolve(),
        kind="dependency_runtime_extended_resource_equivalence",
        label="extended resource",
        identifiers_required=True,
    )

    bundled_jar = bundled_jar.resolve()
    if not bundled_jar.is_file():
        raise DependencyRuntimeSubstitutionPlanError(
            "bundled/readable JAR does not exist"
        )
    bundled_sha = _sha256_file(bundled_jar)

    for label, value in (
        ("runtime readiness", readiness),
        ("replacement plan", plan),
        ("replacement extension", extension),
        ("extended closure", closure),
        ("extended resource", resource),
    ):
        if value.get("bundled_jar_sha256") != bundled_sha:
            raise DependencyRuntimeSubstitutionPlanError(
                f"{label} is bound to a different bundled JAR"
            )

    readiness_summary = readiness.get("summary")
    if not isinstance(readiness_summary, dict):
        raise DependencyRuntimeSubstitutionPlanError(
            "runtime readiness lacks summary"
        )
    required_ready = (
        "runtime_dependency_substitution_ready",
        "class_closure_ready",
        "dynamic_target_ready",
        "resource_equivalence_ready",
        "native_runtime_ready",
    )
    for key in required_ready:
        if readiness_summary.get(key) is not True:
            raise DependencyRuntimeSubstitutionPlanError(
                f"runtime readiness is not fully ready: {key}"
            )

    replacement_id = _required_id(
        plan,
        "replacement_plan_id",
        label="replacement plan",
    )
    readiness_id = _required_id(
        readiness,
        "runtime_readiness_id",
        label="runtime readiness",
    )
    extension_id = _required_id(
        extension,
        "replacement_extension_id",
        label="replacement extension",
    )
    closure_id = _required_id(
        closure,
        "runtime_extended_closure_id",
        label="extended closure",
    )
    resource_id = _required_id(
        resource,
        "runtime_extended_resource_id",
        label="extended resource",
    )

    if extension.get("replacement_plan_id") != replacement_id:
        raise DependencyRuntimeSubstitutionPlanError(
            "replacement extension is bound to a different DEPREPLACE"
        )
    if readiness.get("replacement_plan_id") != replacement_id:
        raise DependencyRuntimeSubstitutionPlanError(
            "runtime readiness is bound to a different DEPREPLACE"
        )
    if closure.get("replacement_plan_id") != replacement_id:
        raise DependencyRuntimeSubstitutionPlanError(
            "extended closure is bound to a different DEPREPLACE"
        )
    closure_extension_id = _required_id(
        closure,
        "replacement_extension_id",
        label="extended closure",
    )
    if closure_extension_id != extension_id:
        raise DependencyRuntimeSubstitutionPlanError(
            "extended closure is bound to a different replacement extension"
        )
    readiness_closure_id = _required_id(
        readiness,
        "runtime_extended_closure_id",
        label="runtime readiness",
    )
    if closure_id != readiness_closure_id:
        raise DependencyRuntimeSubstitutionPlanError(
            "runtime readiness is bound to a different extended closure"
        )
    resource_closure_id = _required_id(
        resource,
        "runtime_extended_closure_id",
        label="extended resource",
    )
    if resource_closure_id != readiness_closure_id:
        raise DependencyRuntimeSubstitutionPlanError(
            "extended resource is bound to a different extended closure"
        )
    readiness_resource_id = _required_id(
        readiness,
        "runtime_extended_resource_id",
        label="runtime readiness",
    )
    if resource_id != readiness_resource_id:
        raise DependencyRuntimeSubstitutionPlanError(
            "runtime readiness is bound to a different extended resource"
        )

    supplied: dict[str, Path] = {}
    supplied_sha: dict[str, str] = {}
    for raw in official_artifacts:
        path = raw.resolve()
        if not path.is_file():
            raise DependencyRuntimeSubstitutionPlanError(
                f"official artifact missing: {path}"
            )
        if path.name in supplied:
            raise DependencyRuntimeSubstitutionPlanError(
                f"duplicate official artifact basename: {path.name}"
            )
        supplied[path.name] = path
        supplied_sha[path.name] = _sha256_file(path)

    expected_sha = sorted(
        str(value).lower()
        for value in readiness.get("official_artifact_sha256", [])
    )
    actual_sha = sorted(supplied_sha.values())
    if expected_sha != actual_sha:
        raise DependencyRuntimeSubstitutionPlanError(
            "official artifact SHA set differs from runtime readiness"
        )
    if sorted(
        str(value).lower()
        for value in closure.get("official_artifact_sha256", [])
    ) != actual_sha:
        raise DependencyRuntimeSubstitutionPlanError(
            "extended closure official artifact authority drifted"
        )
    if sorted(
        str(value).lower()
        for value in resource.get("official_artifact_sha256", [])
    ) != actual_sha:
        raise DependencyRuntimeSubstitutionPlanError(
            "extended resource official artifact authority drifted"
        )

    original_rows = plan.get("owners")
    promoted_rows = extension.get("promoted_rows")
    combined_rows = extension.get("combined_owner_rows")
    if not isinstance(original_rows, list):
        raise DependencyRuntimeSubstitutionPlanError(
            "replacement plan lacks owner rows"
        )
    if not isinstance(promoted_rows, list):
        raise DependencyRuntimeSubstitutionPlanError(
            "replacement extension lacks promoted rows"
        )
    if not isinstance(combined_rows, list):
        raise DependencyRuntimeSubstitutionPlanError(
            "replacement extension lacks combined owner rows"
        )

    def owner_key(row: dict[str, Any]) -> tuple[str, str, str | None, str | None]:
        owner = row.get("old_owner")
        classification = row.get("classification")
        if not isinstance(owner, str) or not isinstance(classification, str):
            raise DependencyRuntimeSubstitutionPlanError(
                "replacement owner row lacks private authority"
            )
        new_owner = row.get("new_owner")
        artifact = row.get("artifact")
        return (
            owner,
            classification,
            str(new_owner) if new_owner is not None else None,
            str(artifact) if artifact is not None else None,
        )

    expected_combined: list[tuple[str, str, str | None, str | None]] = []
    seen_expected: set[str] = set()
    for row in original_rows:
        if not isinstance(row, dict):
            raise DependencyRuntimeSubstitutionPlanError(
                "malformed DEPREPLACE owner row"
            )
        key = owner_key(row)
        if key[0] in seen_expected:
            raise DependencyRuntimeSubstitutionPlanError(
                "duplicate DEPREPLACE owner row"
            )
        seen_expected.add(key[0])
        expected_combined.append(key)

    for row in promoted_rows:
        if not isinstance(row, dict):
            raise DependencyRuntimeSubstitutionPlanError(
                "malformed replacement extension promoted row"
            )
        if row.get("status") != "promotion_eligible":
            raise DependencyRuntimeSubstitutionPlanError(
                "replacement extension promoted row is not promotion eligible"
            )
        key = owner_key(row)
        if key[1] != "official_replaceable":
            raise DependencyRuntimeSubstitutionPlanError(
                "replacement extension promoted row is not official replaceable"
            )
        if key[0] in seen_expected:
            raise DependencyRuntimeSubstitutionPlanError(
                "replacement extension duplicates an existing owner"
            )
        seen_expected.add(key[0])
        expected_combined.append(key)

    actual_combined: list[tuple[str, str, str | None, str | None]] = []
    seen_actual: set[str] = set()
    for row in combined_rows:
        if not isinstance(row, dict):
            raise DependencyRuntimeSubstitutionPlanError(
                "malformed replacement extension combined owner row"
            )
        key = owner_key(row)
        if key[0] in seen_actual:
            raise DependencyRuntimeSubstitutionPlanError(
                "duplicate combined replacement owner row"
            )
        seen_actual.add(key[0])
        actual_combined.append(key)

    if sorted(expected_combined) != sorted(actual_combined):
        raise DependencyRuntimeSubstitutionPlanError(
            "combined replacement authority differs from DEPREPLACE plus extension"
        )

    class_removals: list[dict[str, Any]] = []
    required_artifacts: set[str] = set()
    protected_owner_counts: Counter[str] = Counter()

    for row in combined_rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("classification"), str)
        ):
            raise DependencyRuntimeSubstitutionPlanError(
                "malformed replacement-extension owner row"
            )
        classification = str(row["classification"])
        if classification == "official_replaceable":
            old_owner = row.get("old_owner")
            new_owner = row.get("new_owner")
            artifact = row.get("artifact")
            if (
                not isinstance(old_owner, str)
                or not isinstance(new_owner, str)
                or not isinstance(artifact, str)
            ):
                raise DependencyRuntimeSubstitutionPlanError(
                    "official replacement row lacks private identifiers"
                )
            if artifact not in supplied:
                raise DependencyRuntimeSubstitutionPlanError(
                    f"required official artifact was not supplied: {artifact}"
                )
            required_artifacts.add(artifact)
            class_removals.append(
                {
                    "old_owner": old_owner,
                    "new_owner": new_owner,
                    "artifact": artifact,
                    "entry": old_owner + ".class",
                }
            )
        else:
            protected_owner_counts[classification] += 1

    resource_rows = resource.get("resources")
    if not isinstance(resource_rows, list):
        raise DependencyRuntimeSubstitutionPlanError(
            "extended resource authority lacks resource rows"
        )

    resource_removals: list[dict[str, Any]] = []
    for row in resource_rows:
        if not isinstance(row, dict):
            raise DependencyRuntimeSubstitutionPlanError(
                "malformed extended resource row"
            )
        status = row.get("status")
        entry = row.get("entry")
        providers = row.get("providers")
        if status not in {
            "exact_byte_match",
            "service_trailing_newline_equivalent",
        }:
            continue
        if not isinstance(entry, str) or not isinstance(providers, list):
            raise DependencyRuntimeSubstitutionPlanError(
                "equivalent resource row lacks private entry/provider authority"
            )
        provider_names = sorted(
            str(provider.get("artifact"))
            for provider in providers
            if isinstance(provider, dict)
            and isinstance(provider.get("artifact"), str)
        )
        if len(provider_names) != 1:
            raise DependencyRuntimeSubstitutionPlanError(
                "equivalent resource row is not bound to exactly one provider"
            )
        artifact = provider_names[0]
        if artifact not in supplied:
            raise DependencyRuntimeSubstitutionPlanError(
                "resource provider artifact was not supplied"
            )
        required_artifacts.add(artifact)
        resource_removals.append(
            {
                "entry": entry,
                "artifact": artifact,
                "equivalence": status,
                "service_entry": bool(row.get("service_entry")),
            }
        )

    bundled_entries = _zip_entries(bundled_jar)
    class_removal_entries = {row["entry"] for row in class_removals}
    resource_removal_entries = {row["entry"] for row in resource_removals}

    missing_class_entries = sorted(
        entry
        for entry in class_removal_entries
        if entry not in bundled_entries
    )
    missing_resource_entries = sorted(
        entry
        for entry in resource_removal_entries
        if entry not in bundled_entries
    )
    if missing_class_entries or missing_resource_entries:
        raise DependencyRuntimeSubstitutionPlanError(
            "planned removals are absent from bundled preimage"
        )

    removal_entries = class_removal_entries | resource_removal_entries
    retained_entries = set(bundled_entries) - removal_entries

    official_entries: dict[str, str] = {}
    official_entry_count = 0
    collisions: list[dict[str, str]] = []
    resource_overlaps: list[dict[str, str]] = []
    for artifact in sorted(required_artifacts):
        for entry in _zip_entries(supplied[artifact]):
            official_entry_count += 1
            prior = official_entries.get(entry)
            if prior is not None and prior != artifact:
                target = (
                    collisions
                    if entry.endswith(".class")
                    else resource_overlaps
                )
                target.append(
                    {
                        "entry": entry,
                        "kind": "official_official",
                        "left": prior,
                        "right": artifact,
                    }
                )
            else:
                official_entries[entry] = artifact
            if entry in retained_entries:
                target = (
                    collisions
                    if entry.endswith(".class")
                    else resource_overlaps
                )
                target.append(
                    {
                        "entry": entry,
                        "kind": "retained_bundled_official",
                        "left": "bundled",
                        "right": artifact,
                    }
                )

    collision_free = len(collisions) == 0
    preimage_verified = True
    official_artifacts_verified = True

    private_class_rows = sorted(
        class_removals,
        key=lambda row: row["entry"],
    )
    private_resource_rows = sorted(
        resource_removals,
        key=lambda row: row["entry"],
    )

    public_class_rows = [
        {
            "class_removal_id": _redacted_id(
                "DEPSUBCLASS_",
                row["old_owner"],
                row["new_owner"],
                row["artifact"],
                row["entry"],
            ),
            "owner_remapped": row["old_owner"] != row["new_owner"],
        }
        for row in private_class_rows
    ]
    public_resource_rows = [
        {
            "resource_removal_id": _redacted_id(
                "DEPSUBRESOURCE_",
                row["entry"],
                row["artifact"],
                row["equivalence"],
            ),
            "equivalence": row["equivalence"],
            "service_entry": row["service_entry"],
        }
        for row in private_resource_rows
    ]
    public_collision_rows = [
        {
            "collision_id": _redacted_id(
                "DEPSUBCOLLISION_",
                row["entry"],
                row["kind"],
                row["left"],
                row["right"],
            ),
            "kind": row["kind"],
        }
        for row in sorted(
            collisions,
            key=lambda row: (
                row["entry"],
                row["kind"],
                row["left"],
                row["right"],
            ),
        )
    ]

    public_resource_overlap_rows = [
        {
            "resource_overlap_id": _redacted_id(
                "DEPSUBRESOURCEOVERLAP_",
                row["entry"],
                row["kind"],
                row["left"],
                row["right"],
            ),
            "kind": row["kind"],
        }
        for row in sorted(
            resource_overlaps,
            key=lambda row: (
                row["entry"],
                row["kind"],
                row["left"],
                row["right"],
            ),
        )
    ]

    summary = {
        "class_removal_count": len(private_class_rows),
        "resource_removal_count": len(private_resource_rows),
        "required_official_artifact_count": len(required_artifacts),
        "retained_bundled_entry_count": len(retained_entries),
        "postimage_official_entry_count": len(official_entries),
        "runtime_official_entry_count": official_entry_count,
        "collision_count": len(collisions),
        "resource_overlap_count": len(resource_overlaps),
        "protected_owner_classification_counts": dict(
            sorted(protected_owner_counts.items())
        ),
        "expected_bundled_entry_delta": -len(removal_entries),
        "preimage_verified": preimage_verified,
        "official_artifacts_verified": official_artifacts_verified,
        "collision_free": collision_free,
        "apply_authorized": False,
    }

    material = {
        "runtime_readiness_id": readiness_id,
        "replacement_plan_id": replacement_id,
        "replacement_extension_id": extension_id,
        "runtime_extended_closure_id": closure_id,
        "runtime_extended_resource_id": resource_id,
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": actual_sha,
        "required_artifact_ids": [
            _redacted_id(
                "DEPSUBARTIFACT_",
                artifact,
                supplied_sha[artifact],
            )
            for artifact in sorted(required_artifacts)
        ],
        "class_removals": public_class_rows,
        "resource_removals": public_resource_rows,
        "collisions": public_collision_rows,
        "resource_overlaps": public_resource_overlap_rows,
        "summary": summary,
    }
    substitution_plan_id = (
        "DEPRUNTIMESUBPLAN_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 2,
        "kind": "dependency_runtime_substitution_plan",
        "runtime_substitution_plan_id": substitution_plan_id,
        "runtime_readiness_id": readiness_id,
        "replacement_plan_id": replacement_id,
        "replacement_extension_id": extension_id,
        "runtime_extended_closure_id": closure_id,
        "runtime_extended_resource_id": resource_id,
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": actual_sha,
        "summary": summary,
        "required_artifacts": [
            {
                "artifact_id": _redacted_id(
                    "DEPSUBARTIFACT_",
                    artifact,
                    supplied_sha[artifact],
                ),
                **(
                    {
                        "artifact": artifact,
                        "sha256": supplied_sha[artifact],
                    }
                    if include_identifiers
                    else {}
                ),
            }
            for artifact in sorted(required_artifacts)
        ],
        "class_removals": (
            private_class_rows
            if include_identifiers
            else public_class_rows
        ),
        "resource_removals": (
            private_resource_rows
            if include_identifiers
            else public_resource_rows
        ),
        "collisions": (
            sorted(
                collisions,
                key=lambda row: (
                    row["entry"],
                    row["kind"],
                    row["left"],
                    row["right"],
                ),
            )
            if include_identifiers
            else public_collision_rows
        ),
        "resource_overlaps": (
            sorted(
                resource_overlaps,
                key=lambda row: (
                    row["entry"],
                    row["kind"],
                    row["left"],
                    row["right"],
                ),
            )
            if include_identifiers
            else public_resource_overlap_rows
        ),
        "identifiers_included": include_identifiers,
        "apply_authorized": False,
        "note": (
            "This authority is a read-only mutation plan. It never edits the "
            "bundled runtime JAR and does not authorize an apply step."
        ),
    }


def write_dependency_runtime_substitution_plan(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
