from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile


class DependencyRuntimeFrontierError(ValueError):
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


def _load_private_plan(path: Path) -> dict[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRuntimeFrontierError(
            "invalid private dependency replacement plan"
        ) from exc
    if plan.get("kind") != "dependency_replacement_boundary_plan":
        raise DependencyRuntimeFrontierError(
            "unexpected dependency replacement plan kind"
        )
    if plan.get("identifiers_included") is not True:
        raise DependencyRuntimeFrontierError(
            "runtime frontier requires private identifier-bearing DEPREPLACE"
        )
    return plan


def _normalize_prefixes(values: Any) -> tuple[str, ...]:
    if not isinstance(values, list) or not values:
        raise DependencyRuntimeFrontierError(
            "DEPREPLACE project_prefixes must be non-empty"
        )
    out: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise DependencyRuntimeFrontierError(
                "invalid DEPREPLACE project prefix"
            )
        normalized = value.replace("\\", "/").lstrip("/")
        if not normalized.endswith("/"):
            normalized += "/"
        out.append(normalized)
    return tuple(sorted(set(out)))


def _artifact_authority(
    plan: dict[str, Any],
    official_artifacts: list[Path],
) -> tuple[dict[str, Path], dict[str, str]]:
    rows = plan.get("official_artifacts")
    if not isinstance(rows, list) or not rows:
        raise DependencyRuntimeFrontierError(
            "private DEPREPLACE lacks official artifact authority"
        )

    expected: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise DependencyRuntimeFrontierError(
                "malformed DEPREPLACE official artifact row"
            )
        name = row.get("artifact")
        sha = row.get("sha256")
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(sha, str)
            or len(sha) != 64
        ):
            raise DependencyRuntimeFrontierError(
                "invalid DEPREPLACE official artifact row"
            )
        if name in expected:
            raise DependencyRuntimeFrontierError(
                "duplicate DEPREPLACE official artifact name"
            )
        expected[name] = sha.lower()

    supplied: dict[str, Path] = {}
    for raw in official_artifacts:
        path = raw.resolve()
        if not path.is_file():
            raise DependencyRuntimeFrontierError(
                f"official artifact missing: {path}"
            )
        name = path.name
        if name in supplied:
            raise DependencyRuntimeFrontierError(
                f"duplicate supplied artifact basename: {name}"
            )
        supplied[name] = path

    if set(supplied) != set(expected):
        raise DependencyRuntimeFrontierError(
            "supplied official artifact names differ from DEPREPLACE"
        )
    for name, path in supplied.items():
        actual = _sha256_file(path)
        if actual != expected[name]:
            raise DependencyRuntimeFrontierError(
                f"official artifact SHA drifted: {name}"
            )
    return supplied, expected


def build_dependency_runtime_frontier(
    private_replacement_plan_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    private_replacement_plan_path = (
        private_replacement_plan_path.resolve()
    )
    bundled_jar = bundled_jar.resolve()

    if not bundled_jar.is_file():
        raise DependencyRuntimeFrontierError(
            "bundled/readable JAR does not exist"
        )

    plan = _load_private_plan(private_replacement_plan_path)
    prefixes = _normalize_prefixes(plan.get("project_prefixes"))
    bundled_sha = _sha256_file(bundled_jar)
    if str(plan.get("bundled_jar_sha256", "")).lower() != bundled_sha:
        raise DependencyRuntimeFrontierError(
            "bundled/readable JAR SHA differs from DEPREPLACE"
        )

    artifacts, expected_artifacts = _artifact_authority(
        plan,
        official_artifacts,
    )
    artifact_ids = plan.get("artifact_ids")
    if not isinstance(artifact_ids, dict):
        raise DependencyRuntimeFrontierError(
            "private DEPREPLACE lacks artifact_ids"
        )

    with zipfile.ZipFile(bundled_jar) as archive:
        bundled_entries = {
            info.filename: info.file_size
            for info in archive.infolist()
            if not info.is_dir() and info.filename.endswith(".class")
        }

    official_entries: dict[str, set[str]] = {}
    for name, path in artifacts.items():
        with zipfile.ZipFile(path) as archive:
            official_entries[name] = {
                info.filename
                for info in archive.infolist()
                if not info.is_dir() and info.filename.endswith(".class")
            }

    allowed = {
        "official_replaceable",
        "residual_bundled",
        "project_retained",
        "platform_runtime",
    }
    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []

    owners = plan.get("owners")
    if not isinstance(owners, list):
        raise DependencyRuntimeFrontierError(
            "private DEPREPLACE lacks owners"
        )

    for row in owners:
        if not isinstance(row, dict):
            raise DependencyRuntimeFrontierError(
                "malformed DEPREPLACE owner row"
            )
        owner_id = row.get("owner_id")
        classification = row.get("classification")
        old_owner = row.get("old_owner")
        if (
            not isinstance(owner_id, str)
            or not isinstance(classification, str)
            or classification not in allowed
            or not isinstance(old_owner, str)
            or not old_owner
        ):
            raise DependencyRuntimeFrontierError(
                "invalid DEPREPLACE owner row"
            )
        if any(old_owner.startswith(prefix) for prefix in prefixes):
            raise DependencyRuntimeFrontierError(
                "DEPREPLACE runtime owner overlaps project prefixes"
            )

        entry = old_owner + ".class"
        bundled_present = entry in bundled_entries
        bundled_bytes = bundled_entries.get(entry, 0)

        artifact_name = row.get("artifact")
        new_owner = row.get("new_owner")
        artifact_id = (
            artifact_ids.get(artifact_name)
            if isinstance(artifact_name, str)
            else None
        )
        official_target_present: bool | None = None

        if classification == "official_replaceable":
            if (
                not isinstance(artifact_name, str)
                or artifact_name not in artifacts
                or not isinstance(artifact_id, str)
                or not isinstance(new_owner, str)
                or not new_owner
            ):
                raise DependencyRuntimeFrontierError(
                    "official-replaceable owner lacks exact artifact target"
                )
            official_target_present = (
                new_owner + ".class"
                in official_entries[artifact_name]
            )
            if not official_target_present:
                raise DependencyRuntimeFrontierError(
                    "official-replaceable target class missing from artifact"
                )
        elif artifact_name is not None or new_owner is not None:
            raise DependencyRuntimeFrontierError(
                "non-replaceable owner unexpectedly carries official target"
            )

        public = {
            "owner_id": owner_id,
            "classification": classification,
            "bundled_class_entry_present": bundled_present,
            "bundled_class_bytes": bundled_bytes,
            "artifact_id": artifact_id,
            "official_target_present": official_target_present,
            "owner_remapped": (
                isinstance(new_owner, str)
                and new_owner != old_owner
            ),
        }
        public_rows.append(public)
        if include_identifiers:
            private_rows.append(
                {
                    **public,
                    "old_owner": old_owner,
                    "new_owner": new_owner,
                    "artifact": artifact_name,
                }
            )

    public_rows.sort(key=lambda row: row["owner_id"])
    if include_identifiers:
        private_rows.sort(key=lambda row: row["owner_id"])

    class_counts = Counter(
        row["classification"] for row in public_rows
    )
    byte_counts = Counter()
    entry_counts = Counter()
    for row in public_rows:
        if row["bundled_class_entry_present"]:
            byte_counts[row["classification"]] += int(
                row["bundled_class_bytes"]
            )
            entry_counts[row["classification"]] += 1

    material = {
        "replacement_plan_id": plan.get("replacement_plan_id"),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": sorted(
            expected_artifacts.values()
        ),
        "owners": public_rows,
        "runtime_capsule_mutation_ready": False,
        "requires_dependency_closure_proof": True,
    }
    frontier_id = (
        "DEPRUNTIMEFRONTIER_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "dependency_runtime_frontier",
        "runtime_frontier_id": frontier_id,
        "replacement_plan_id": plan.get("replacement_plan_id"),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": sorted(
            expected_artifacts.values()
        ),
        "summary": {
            "referenced_owner_count": len(public_rows),
            "classification_counts": dict(
                sorted(class_counts.items())
            ),
            "bundled_class_entry_counts": dict(
                sorted(entry_counts.items())
            ),
            "bundled_class_byte_counts": dict(
                sorted(byte_counts.items())
            ),
            "official_replaceable_bundled_class_entry_count": (
                entry_counts.get("official_replaceable", 0)
            ),
            "official_replaceable_bundled_class_bytes": (
                byte_counts.get("official_replaceable", 0)
            ),
            "protected_bundled_class_entry_count": (
                entry_counts.get("residual_bundled", 0)
                + entry_counts.get("project_retained", 0)
            ),
            "protected_bundled_class_bytes": (
                byte_counts.get("residual_bundled", 0)
                + byte_counts.get("project_retained", 0)
            ),
            "runtime_capsule_mutation_ready": False,
            "requires_dependency_closure_proof": True,
        },
        "owners": private_rows if include_identifiers else public_rows,
        "identifiers_included": include_identifiers,
        "note": (
            "This frontier quantifies directly project-referenced bundled "
            "dependency class bytes only. It does not prove transitive "
            "dependency closure, reflective/resource/native safety, or "
            "runtime removability."
        ),
    }


def write_dependency_runtime_frontier(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
