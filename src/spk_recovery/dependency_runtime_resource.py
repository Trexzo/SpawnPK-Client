from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile


class DependencyRuntimeResourceError(ValueError):
    pass


_NATIVE_SUFFIXES = (
    ".dll",
    ".so",
    ".dylib",
    ".jnilib",
)


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


def _load_private_closure(path: Path) -> dict[str, Any]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRuntimeResourceError(
            "invalid runtime closure authority"
        ) from exc

    if report.get("kind") != "dependency_runtime_closure":
        raise DependencyRuntimeResourceError(
            "unexpected runtime closure kind"
        )
    if report.get("identifiers_included") is not True:
        raise DependencyRuntimeResourceError(
            "resource equivalence requires private identifier-bearing closure"
        )
    return report


def _service_trailing_newline_equivalent(
    bundled: bytes,
    official: bytes,
) -> bool:
    try:
        left = bundled.decode("utf-8")
        right = official.decode("utf-8")
    except UnicodeDecodeError:
        return False

    if left == right:
        return False

    def split_ending(value: str) -> tuple[str, str]:
        if value.endswith("\r\n"):
            return value[:-2], "\r\n"
        if value.endswith("\n"):
            return value[:-1], "\n"
        return value, ""

    left_body, left_ending = split_ending(left)
    right_body, right_ending = split_ending(right)
    if left_body != right_body:
        return False
    if left_ending == right_ending:
        return False
    return bool(left_ending or right_ending)


def _is_native_path(entry: str) -> bool:
    lowered = entry.lower()
    return (
        lowered.endswith(_NATIVE_SUFFIXES)
        or "/natives/" in lowered
        or lowered.startswith("natives/")
        or lowered.startswith("meta-inf/native/")
    )


def _resource_entries(path: Path) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(path) as archive:
            result: dict[str, bytes] = {}
            for info in archive.infolist():
                if (
                    info.is_dir()
                    or info.filename.endswith(".class")
                ):
                    continue
                if info.filename in result:
                    raise DependencyRuntimeResourceError(
                        f"duplicate resource entry in JAR: "
                        f"{path.name}:{info.filename}"
                    )
                result[info.filename] = archive.read(info)
            return result
    except zipfile.BadZipFile as exc:
        raise DependencyRuntimeResourceError(
            f"invalid JAR/ZIP: {path}"
        ) from exc


def build_dependency_runtime_resource_equivalence(
    private_runtime_closure_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    private_runtime_closure_path = (
        private_runtime_closure_path.resolve()
    )
    bundled_jar = bundled_jar.resolve()

    closure = _load_private_closure(
        private_runtime_closure_path
    )
    if not bundled_jar.is_file():
        raise DependencyRuntimeResourceError(
            "bundled/readable JAR does not exist"
        )

    bundled_sha = _sha256_file(bundled_jar)
    if closure.get("bundled_jar_sha256") != bundled_sha:
        raise DependencyRuntimeResourceError(
            "runtime closure is bound to a different bundled JAR"
        )

    supplied: dict[str, Path] = {}
    supplied_sha: dict[str, str] = {}
    for raw in official_artifacts:
        path = raw.resolve()
        if not path.is_file():
            raise DependencyRuntimeResourceError(
                f"official artifact missing: {path}"
            )
        if path.name in supplied:
            raise DependencyRuntimeResourceError(
                f"duplicate official artifact basename: {path.name}"
            )
        supplied[path.name] = path
        supplied_sha[path.name] = _sha256_file(path)

    expected_sha = sorted(
        str(value).lower()
        for value in closure.get(
            "official_artifact_sha256",
            [],
        )
    )
    actual_sha = sorted(supplied_sha.values())
    if expected_sha != actual_sha:
        raise DependencyRuntimeResourceError(
            "official artifact SHA set differs from runtime closure"
        )

    closure_owners = closure.get("owners")
    if not isinstance(closure_owners, list):
        raise DependencyRuntimeResourceError(
            "private runtime closure lacks owner rows"
        )
    owner_used_artifacts = {
        str(row["artifact"])
        for row in closure_owners
        if isinstance(row, dict)
        and row.get("status") == "official_closure_mapped"
        and isinstance(row.get("artifact"), str)
        and row.get("artifact")
    }

    resources = closure.get("resources")
    if not isinstance(resources, dict):
        raise DependencyRuntimeResourceError(
            "runtime closure lacks resource inventory"
        )
    closure_artifacts = resources.get("artifacts")
    if not isinstance(closure_artifacts, list):
        raise DependencyRuntimeResourceError(
            "runtime closure lacks artifact resource rows"
        )

    used_artifact_names: list[str] = []
    for row in closure_artifacts:
        if not isinstance(row, dict):
            raise DependencyRuntimeResourceError(
                "malformed runtime closure artifact row"
            )
        artifact = row.get("artifact")
        if not isinstance(artifact, str) or not artifact:
            raise DependencyRuntimeResourceError(
                "private runtime closure artifact row lacks artifact"
            )
        if artifact not in supplied:
            raise DependencyRuntimeResourceError(
                f"closure-used artifact was not supplied: {artifact}"
            )
        used_artifact_names.append(artifact)

    if len(set(used_artifact_names)) != len(used_artifact_names):
        raise DependencyRuntimeResourceError(
            "runtime closure repeats used artifact"
        )
    if set(used_artifact_names) != owner_used_artifacts:
        raise DependencyRuntimeResourceError(
            "runtime closure used-artifact inventory disagrees with "
            "official closure owner rows"
        )

    bundled_resources = _resource_entries(bundled_jar)
    official_resources: dict[str, dict[str, bytes]] = {
        name: _resource_entries(supplied[name])
        for name in sorted(used_artifact_names)
    }

    providers: dict[
        str,
        list[tuple[str, bytes]],
    ] = defaultdict(list)
    for artifact_name, entries in official_resources.items():
        for entry, payload in entries.items():
            providers[entry].append((artifact_name, payload))

    artifact_ids = {
        name: f"DEPRUNTIMEARTIFACT_{index:04d}"
        for index, name in enumerate(
            sorted(used_artifact_names),
            start=1,
        )
    }

    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    native_status_counts: Counter[str] = Counter()
    total_official_bytes = 0

    for index, entry in enumerate(
        sorted(providers),
        start=1,
    ):
        rows = sorted(
            providers[entry],
            key=lambda value: value[0],
        )
        provider_count = len(rows)
        provider_ids = [
            artifact_ids[name]
            for name, _payload in rows
        ]
        official_bytes = sum(
            len(payload)
            for _name, payload in rows
        )
        total_official_bytes += official_bytes

        bundled_payload = bundled_resources.get(entry)
        service_entry = entry.startswith(
            "META-INF/services/"
        )
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
                status = (
                    "service_trailing_newline_equivalent"
                )
            else:
                status = "byte_mismatch"

        status_counts[status] += 1
        if native_entry:
            native_status_counts[status] += 1

        public = {
            "resource_id": f"DEPRUNTIME_RESOURCE_{index:05d}",
            "status": status,
            "provider_count": provider_count,
            "provider_artifact_ids": provider_ids,
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

    blocker_statuses = {
        "ambiguous_official_path",
        "missing_from_bundled",
        "byte_mismatch",
    }
    resource_blocker_count = sum(
        status_counts.get(status, 0)
        for status in blocker_statuses
    )
    native_entry_count = sum(
        1 for row in public_rows
        if row["native_entry"]
    )
    native_runtime_safety_unproven = (
        native_entry_count > 0
    )

    material = {
        "runtime_closure_id": closure.get(
            "runtime_closure_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": actual_sha,
        "used_artifact_ids": [
            artifact_ids[name]
            for name in sorted(used_artifact_names)
        ],
        "resources": public_rows,
        "resource_blocker_count": resource_blocker_count,
        "native_runtime_safety_unproven": (
            native_runtime_safety_unproven
        ),
        "runtime_capsule_mutation_ready": False,
    }
    resource_id = (
        "DEPRUNTIMERESOURCE_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "dependency_runtime_resource_equivalence",
        "runtime_resource_id": resource_id,
        "runtime_closure_id": closure.get(
            "runtime_closure_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": actual_sha,
        "summary": {
            "used_official_artifact_count": len(
                used_artifact_names
            ),
            "resource_entry_count": len(public_rows),
            "official_resource_bytes": total_official_bytes,
            "status_counts": dict(
                sorted(status_counts.items())
            ),
            "resource_blocker_count": (
                resource_blocker_count
            ),
            "service_entry_count": sum(
                1 for row in public_rows
                if row["service_entry"]
            ),
            "native_entry_count": native_entry_count,
            "native_status_counts": dict(
                sorted(native_status_counts.items())
            ),
            "native_runtime_safety_unproven": (
                native_runtime_safety_unproven
            ),
            "reflection_dynamic_loading_unproven": bool(
                closure.get("summary", {}).get(
                    "reflection_dynamic_loading_unproven",
                    True,
                )
            ),
            "runtime_capsule_mutation_ready": False,
        },
        "artifacts": [
            {
                "artifact_id": artifact_ids[name],
                **(
                    {
                        "artifact": name,
                        "sha256": supplied_sha[name],
                    }
                    if include_identifiers
                    else {}
                ),
            }
            for name in sorted(used_artifact_names)
        ],
        "resources": (
            private_rows
            if include_identifiers
            else public_rows
        ),
        "identifiers_included": include_identifiers,
        "note": (
            "Resource equivalence is read-only authority. Native payload "
            "byte equality does not prove platform/classifier/runtime safety, "
            "and this lane cannot clear the separate dynamic-loading boundary."
        ),
    }


def write_dependency_runtime_resource_equivalence(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
