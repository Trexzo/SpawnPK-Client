from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

from .dependency_runtime_resource import (
    DependencyRuntimeResourceError,
    _is_native_path,
    _resource_entries,
    _service_trailing_newline_equivalent,
    _sha256_file,
)


class DependencyRuntimeExtendedResourceError(ValueError):
    pass


_BLOCKER_STATUSES = {
    "ambiguous_official_path",
    "missing_from_bundled",
    "byte_mismatch",
}


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
        raise DependencyRuntimeExtendedResourceError(
            f"invalid {label} authority"
        ) from exc
    if value.get("kind") != kind:
        raise DependencyRuntimeExtendedResourceError(
            f"unexpected {label} authority kind"
        )
    if value.get("identifiers_included") is not True:
        raise DependencyRuntimeExtendedResourceError(
            f"{label} authority must include private identifiers"
        )
    return value


def _provider_names(row: dict[str, Any]) -> tuple[str, ...]:
    providers = row.get("providers")
    if not isinstance(providers, list):
        raise DependencyRuntimeExtendedResourceError(
            "private resource row lacks provider authority"
        )
    names: list[str] = []
    for provider in providers:
        if (
            not isinstance(provider, dict)
            or not isinstance(provider.get("artifact"), str)
        ):
            raise DependencyRuntimeExtendedResourceError(
                "malformed resource provider row"
            )
        names.append(str(provider["artifact"]))
    return tuple(sorted(names))


def build_dependency_runtime_extended_resource(
    private_extended_closure_path: Path,
    private_original_resource_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    extended = _load_private(
        private_extended_closure_path.resolve(),
        kind="dependency_runtime_extended_closure",
        label="extended runtime closure",
    )
    original = _load_private(
        private_original_resource_path.resolve(),
        kind="dependency_runtime_resource_equivalence",
        label="original runtime resource",
    )

    bundled_jar = bundled_jar.resolve()
    if not bundled_jar.is_file():
        raise DependencyRuntimeExtendedResourceError(
            "bundled/readable JAR does not exist"
        )
    bundled_sha = _sha256_file(bundled_jar)
    for label, value in (
        ("extended runtime closure", extended),
        ("original runtime resource", original),
    ):
        if value.get("bundled_jar_sha256") != bundled_sha:
            raise DependencyRuntimeExtendedResourceError(
                f"{label} is bound to a different bundled JAR"
            )

    if original.get("runtime_closure_id") != extended.get(
        "runtime_closure_id"
    ):
        raise DependencyRuntimeExtendedResourceError(
            "original resource authority is bound to a different static closure"
        )

    supplied: dict[str, Path] = {}
    supplied_sha: dict[str, str] = {}
    for raw in official_artifacts:
        path = raw.resolve()
        if not path.is_file():
            raise DependencyRuntimeExtendedResourceError(
                f"official artifact missing: {path}"
            )
        if path.name in supplied:
            raise DependencyRuntimeExtendedResourceError(
                f"duplicate official artifact basename: {path.name}"
            )
        supplied[path.name] = path
        supplied_sha[path.name] = _sha256_file(path)

    expected_sha = sorted(
        str(value).lower()
        for value in extended.get(
            "official_artifact_sha256",
            [],
        )
    )
    actual_sha = sorted(supplied_sha.values())
    if expected_sha != actual_sha:
        raise DependencyRuntimeExtendedResourceError(
            "official artifact SHA set differs from extended closure"
        )
    if sorted(
        str(value).lower()
        for value in original.get(
            "official_artifact_sha256",
            [],
        )
    ) != actual_sha:
        raise DependencyRuntimeExtendedResourceError(
            "original resource official artifact authority drifted"
        )

    original_artifact_rows = original.get("artifacts")
    if not isinstance(original_artifact_rows, list):
        raise DependencyRuntimeExtendedResourceError(
            "original resource authority lacks artifact rows"
        )
    original_used_artifacts: set[str] = set()
    for row in original_artifact_rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("artifact"), str)
            or not isinstance(row.get("sha256"), str)
        ):
            raise DependencyRuntimeExtendedResourceError(
                "private original resource artifact row is malformed"
            )
        name = str(row["artifact"])
        if name in original_used_artifacts:
            raise DependencyRuntimeExtendedResourceError(
                "original resource authority repeats artifact"
            )
        if name not in supplied:
            raise DependencyRuntimeExtendedResourceError(
                f"original resource artifact was not supplied: {name}"
            )
        if supplied_sha[name] != str(row["sha256"]).lower():
            raise DependencyRuntimeExtendedResourceError(
                "original resource artifact SHA drifted"
            )
        original_used_artifacts.add(name)

    extended_used_artifacts = set(original_used_artifacts)
    for collection_name in ("dynamic_roots", "new_owners"):
        rows = extended.get(collection_name)
        if not isinstance(rows, list):
            raise DependencyRuntimeExtendedResourceError(
                f"extended closure lacks {collection_name} rows"
            )
        for row in rows:
            if not isinstance(row, dict):
                raise DependencyRuntimeExtendedResourceError(
                    f"malformed extended closure {collection_name} row"
                )
            if (
                row.get("status")
                not in {
                    "authorized_dynamic_root",
                    "official_closure_mapped",
                }
            ):
                continue
            artifact = row.get("artifact")
            if not isinstance(artifact, str) or not artifact:
                raise DependencyRuntimeExtendedResourceError(
                    "private extended closure mapped row lacks artifact"
                )
            if artifact not in supplied:
                raise DependencyRuntimeExtendedResourceError(
                    f"extended closure used artifact was not supplied: {artifact}"
                )
            extended_used_artifacts.add(artifact)

    new_artifacts = (
        extended_used_artifacts - original_used_artifacts
    )

    original_resource_rows = original.get("resources")
    if not isinstance(original_resource_rows, list):
        raise DependencyRuntimeExtendedResourceError(
            "original resource authority lacks resource rows"
        )
    original_by_entry: dict[str, dict[str, Any]] = {}
    for row in original_resource_rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("entry"), str)
        ):
            raise DependencyRuntimeExtendedResourceError(
                "private original resource row lacks entry"
            )
        entry = str(row["entry"])
        if entry in original_by_entry:
            raise DependencyRuntimeExtendedResourceError(
                "original resource authority repeats entry"
            )
        _provider_names(row)
        original_by_entry[entry] = row

    try:
        bundled_resources = _resource_entries(bundled_jar)
        official_resources = {
            name: _resource_entries(supplied[name])
            for name in sorted(extended_used_artifacts)
        }
    except DependencyRuntimeResourceError as exc:
        raise DependencyRuntimeExtendedResourceError(
            str(exc)
        ) from exc

    providers: dict[str, list[tuple[str, bytes]]] = defaultdict(list)
    for artifact_name, entries in official_resources.items():
        for entry, payload in entries.items():
            providers[entry].append((artifact_name, payload))

    artifact_ids = {
        name: f"DEPEXTRUNTIMEARTIFACT_{index:04d}"
        for index, name in enumerate(
            sorted(extended_used_artifacts),
            start=1,
        )
    }

    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    audit_source_counts: Counter[str] = Counter()
    newly_introduced_blocker_count = 0

    for index, entry in enumerate(sorted(providers), start=1):
        rows = sorted(
            providers[entry],
            key=lambda value: value[0],
        )
        provider_names = tuple(
            name for name, _payload in rows
        )
        provider_count = len(rows)
        official_bytes = sum(
            len(payload)
            for _name, payload in rows
        )
        bundled_payload = bundled_resources.get(entry)
        service_entry = entry.startswith("META-INF/services/")
        native_entry = _is_native_path(entry)

        if provider_count > 1:
            status = "ambiguous_official_path"
        else:
            official_payload = rows[0][1]
            if bundled_payload is None:
                status = "missing_from_bundled"
            elif bundled_payload == official_payload:
                status = "exact_byte_match"
            elif (
                service_entry
                and _service_trailing_newline_equivalent(
                    bundled_payload,
                    official_payload,
                )
            ):
                status = "service_trailing_newline_equivalent"
            else:
                status = "byte_mismatch"

        old = original_by_entry.get(entry)
        preserved = False
        if old is not None:
            old_providers = _provider_names(old)
            if (
                old_providers == tuple(sorted(provider_names))
                and old.get("status") == status
                and bool(old.get("service_entry"))
                == service_entry
                and bool(old.get("native_entry"))
                == native_entry
            ):
                preserved = True

        if preserved:
            audit_source = "preserved_r8dep26"
        elif any(name in new_artifacts for name in provider_names):
            audit_source = "new_or_extended_artifact"
        else:
            audit_source = "recomputed_existing_artifact"

        if (
            status in _BLOCKER_STATUSES
            and not (
                old is not None
                and old.get("status") in _BLOCKER_STATUSES
                and preserved
            )
        ):
            newly_introduced_blocker_count += 1

        status_counts[status] += 1
        audit_source_counts[audit_source] += 1

        public = {
            "resource_id": f"DEPEXTRUNTIME_RESOURCE_{index:05d}",
            "status": status,
            "audit_source": audit_source,
            "provider_count": provider_count,
            "provider_artifact_ids": [
                artifact_ids[name]
                for name in provider_names
            ],
            "official_bytes": official_bytes,
            "bundled_present": bundled_payload is not None,
            "bundled_bytes": (
                len(bundled_payload)
                if bundled_payload is not None
                else 0
            ),
            "service_entry": service_entry,
            "native_entry": native_entry,
        }
        public_rows.append(public)

        if include_identifiers:
            private_rows.append(
                {
                    **public,
                    "entry": entry,
                    "providers": [
                        {
                            "artifact": name,
                            "sha256": hashlib.sha256(
                                payload
                            ).hexdigest(),
                            "bytes": len(payload),
                        }
                        for name, payload in rows
                    ],
                    "bundled_sha256": (
                        hashlib.sha256(
                            bundled_payload
                        ).hexdigest()
                        if bundled_payload is not None
                        else None
                    ),
                }
            )

    non_native_blocker_count = sum(
        1
        for row in public_rows
        if (
            not row["native_entry"]
            and row["status"] in _BLOCKER_STATUSES
        )
    )
    native_entry_count = sum(
        1
        for row in public_rows
        if row["native_entry"]
    )
    resource_equivalence_complete = (
        non_native_blocker_count == 0
    )

    material = {
        "runtime_extended_closure_id": extended.get(
            "runtime_extended_closure_id"
        ),
        "runtime_resource_id": original.get(
            "runtime_resource_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": actual_sha,
        "used_artifact_ids": [
            artifact_ids[name]
            for name in sorted(extended_used_artifacts)
        ],
        "resources": public_rows,
        "resource_equivalence_complete": (
            resource_equivalence_complete
        ),
        "native_runtime_safety_unproven": (
            native_entry_count > 0
        ),
    }
    extended_resource_id = (
        "DEPRUNTIMEEXTRESOURCE_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "dependency_runtime_extended_resource_equivalence",
        "runtime_extended_resource_id": extended_resource_id,
        "runtime_extended_closure_id": extended.get(
            "runtime_extended_closure_id"
        ),
        "runtime_resource_id": original.get(
            "runtime_resource_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": actual_sha,
        "summary": {
            "original_audited_artifact_count": len(
                original_used_artifacts
            ),
            "extended_used_artifact_count": len(
                extended_used_artifacts
            ),
            "newly_audited_artifact_count": len(new_artifacts),
            "resource_entry_count": len(public_rows),
            "status_counts": dict(
                sorted(status_counts.items())
            ),
            "audit_source_counts": dict(
                sorted(audit_source_counts.items())
            ),
            "exact_or_service_equivalent_count": sum(
                status_counts.get(status, 0)
                for status in {
                    "exact_byte_match",
                    "service_trailing_newline_equivalent",
                }
            ),
            "service_equivalent_count": status_counts.get(
                "service_trailing_newline_equivalent",
                0,
            ),
            "missing_count": status_counts.get(
                "missing_from_bundled",
                0,
            ),
            "mismatch_count": status_counts.get(
                "byte_mismatch",
                0,
            ),
            "ambiguous_count": status_counts.get(
                "ambiguous_official_path",
                0,
            ),
            "native_entry_count": native_entry_count,
            "newly_introduced_blocker_count": (
                newly_introduced_blocker_count
            ),
            "non_native_blocker_count": (
                non_native_blocker_count
            ),
            "resource_equivalence_complete": (
                resource_equivalence_complete
            ),
            "native_runtime_safety_unproven": (
                native_entry_count > 0
            ),
            "runtime_capsule_mutation_ready": False,
        },
        "artifacts": [
            {
                "artifact_id": artifact_ids[name],
                "audit_source": (
                    "newly_audited"
                    if name in new_artifacts
                    else "preserved_or_recomputed"
                ),
                **(
                    {
                        "artifact": name,
                        "sha256": supplied_sha[name],
                    }
                    if include_identifiers
                    else {}
                ),
            }
            for name in sorted(extended_used_artifacts)
        ],
        "resources": (
            private_rows
            if include_identifiers
            else public_rows
        ),
        "identifiers_included": include_identifiers,
        "note": (
            "Extended resource equivalence is read-only. Native payload "
            "bytes never establish platform/classifier/runtime safety, and "
            "runtime capsule mutation remains disabled."
        ),
    }


def write_dependency_runtime_extended_resource(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
