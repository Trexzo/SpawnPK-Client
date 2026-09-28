from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


class DependencyRuntimeReadinessError(ValueError):
    pass


_READY_ROOT_STATUSES = {
    "already_in_static_closure",
    "authorized_dynamic_root",
    "project_dynamic_target",
}

_SAFE_DIRECT_CLASSIFICATIONS = {
    "project_class",
    "platform_runtime",
    "dependency_platform_runtime",
    "service_project_class_token",
    "service_platform_class_token",
    "service_dependency_platform_runtime",
}


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


def _required_nonnegative_int(
    summary: dict[str, Any],
    key: str,
    *,
    label: str,
) -> int:
    value = summary.get(key)
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise DependencyRuntimeReadinessError(
            f"{label} lacks valid {key}"
        )
    return value


def _required_bool(
    summary: dict[str, Any],
    key: str,
    *,
    label: str,
) -> bool:
    value = summary.get(key)
    if not isinstance(value, bool):
        raise DependencyRuntimeReadinessError(
            f"{label} lacks valid {key}"
        )
    return value


def _load_report(
    path: Path,
    *,
    kind: str,
    label: str,
) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRuntimeReadinessError(
            f"invalid {label} authority"
        ) from exc
    if value.get("kind") != kind:
        raise DependencyRuntimeReadinessError(
            f"unexpected {label} authority kind"
        )
    return value


def build_dependency_runtime_readiness(
    extended_closure_path: Path,
    extended_resource_path: Path,
    dynamic_target_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
) -> dict[str, Any]:
    closure = _load_report(
        extended_closure_path.resolve(),
        kind="dependency_runtime_extended_closure",
        label="extended runtime closure",
    )
    resource = _load_report(
        extended_resource_path.resolve(),
        kind="dependency_runtime_extended_resource_equivalence",
        label="extended runtime resource",
    )
    dynamic = _load_report(
        dynamic_target_path.resolve(),
        kind="dependency_runtime_dynamic_target_classification",
        label="dynamic target",
    )

    bundled_jar = bundled_jar.resolve()
    if not bundled_jar.is_file():
        raise DependencyRuntimeReadinessError(
            "bundled/readable JAR does not exist"
        )
    bundled_sha = _sha256_file(bundled_jar)

    for label, value in (
        ("extended runtime closure", closure),
        ("extended runtime resource", resource),
        ("dynamic target", dynamic),
    ):
        if value.get("bundled_jar_sha256") != bundled_sha:
            raise DependencyRuntimeReadinessError(
                f"{label} is bound to a different bundled JAR"
            )

    if resource.get("runtime_extended_closure_id") != closure.get(
        "runtime_extended_closure_id"
    ):
        raise DependencyRuntimeReadinessError(
            "extended resource authority is bound to a different closure"
        )
    if closure.get("runtime_dynamic_target_id") != dynamic.get(
        "runtime_dynamic_target_id"
    ):
        raise DependencyRuntimeReadinessError(
            "extended closure is bound to a different dynamic target authority"
        )
    if closure.get("replacement_plan_id") != dynamic.get(
        "replacement_plan_id"
    ):
        raise DependencyRuntimeReadinessError(
            "dynamic target authority is bound to a different DEPREPLACE"
        )

    supplied_sha: list[str] = []
    seen_names: set[str] = set()
    for raw in official_artifacts:
        path = raw.resolve()
        if not path.is_file():
            raise DependencyRuntimeReadinessError(
                f"official artifact missing: {path}"
            )
        if path.name in seen_names:
            raise DependencyRuntimeReadinessError(
                f"duplicate official artifact basename: {path.name}"
            )
        seen_names.add(path.name)
        supplied_sha.append(_sha256_file(path))
    supplied_sha.sort()

    closure_sha = sorted(
        str(value).lower()
        for value in closure.get(
            "official_artifact_sha256",
            [],
        )
    )
    resource_sha = sorted(
        str(value).lower()
        for value in resource.get(
            "official_artifact_sha256",
            [],
        )
    )
    if closure_sha != supplied_sha:
        raise DependencyRuntimeReadinessError(
            "official artifact SHA set differs from extended closure"
        )
    if resource_sha != supplied_sha:
        raise DependencyRuntimeReadinessError(
            "official artifact SHA set differs from extended resource authority"
        )

    roots = closure.get("dynamic_roots")
    if not isinstance(roots, list):
        raise DependencyRuntimeReadinessError(
            "extended closure lacks dynamic root rows"
        )
    root_by_target_id: dict[str, dict[str, Any]] = {}
    for row in roots:
        if (
            not isinstance(row, dict)
            or not isinstance(
                row.get("source_dynamic_target_id"),
                str,
            )
        ):
            raise DependencyRuntimeReadinessError(
                "malformed extended closure root row"
            )
        target_id = str(row["source_dynamic_target_id"])
        if target_id in root_by_target_id:
            raise DependencyRuntimeReadinessError(
                "extended closure repeats dynamic target root"
            )
        root_by_target_id[target_id] = row

    targets = dynamic.get("targets")
    if not isinstance(targets, list):
        raise DependencyRuntimeReadinessError(
            "dynamic target authority lacks target rows"
        )

    target_resolution_rows: list[dict[str, Any]] = []
    blocker_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()

    for row in targets:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("dynamic_target_id"), str)
            or not isinstance(row.get("category"), str)
            or not isinstance(row.get("classification"), str)
        ):
            raise DependencyRuntimeReadinessError(
                "malformed dynamic target row"
            )

        target_id = str(row["dynamic_target_id"])
        category = str(row["category"])
        classification = str(row["classification"])
        proven = row.get("literal_target_proven") is True
        category_counts[category] += 1
        root = root_by_target_id.get(target_id)

        resolution = "ready"
        blocker: str | None = None

        if category in {"class_loading", "service_loading"}:
            if not proven:
                resolution = "blocked"
                blocker = "unresolved_dynamic_target"
            elif classification in _SAFE_DIRECT_CLASSIFICATIONS:
                resolution = "ready"
            elif root is None:
                resolution = "blocked"
                blocker = "missing_extended_root_authority"
            elif root.get("status") in _READY_ROOT_STATUSES:
                resolution = "ready"
            elif root.get("status") == "remaining_mapping_authority_gap":
                resolution = "blocked"
                blocker = "remaining_dynamic_mapping_gap"
            else:
                resolution = "blocked"
                blocker = "protected_or_unresolved_class_target"

            if category == "service_loading":
                blocker_counts["service_provider_discovery_unproven"] += 1

        elif category == "resource_loading":
            if (
                proven
                and classification == "resource_official_equivalent"
            ):
                resolution = "ready"
            else:
                resolution = "blocked"
                blocker = "dynamic_resource_target_blocked"

        elif category == "native_loading":
            resolution = "blocked"
            blocker = "native_dynamic_loading_requirement"

        else:
            resolution = "blocked"
            blocker = "unsupported_dynamic_category"

        if blocker is not None:
            blocker_counts[blocker] += 1

        target_resolution_rows.append(
            {
                "dynamic_target_id": target_id,
                "category": category,
                "source_classification": classification,
                "resolution": resolution,
                "blocker": blocker,
                "extended_root_status": (
                    root.get("status")
                    if root is not None
                    else None
                ),
            }
        )

    closure_summary = closure.get("summary")
    resource_summary = resource.get("summary")
    if not isinstance(closure_summary, dict):
        raise DependencyRuntimeReadinessError(
            "extended closure lacks summary"
        )
    if not isinstance(resource_summary, dict):
        raise DependencyRuntimeReadinessError(
            "extended resource authority lacks summary"
        )

    static_class_blockers = _required_nonnegative_int(
        closure_summary,
        "static_class_closure_blocker_count",
        label="extended closure summary",
    )
    dynamic_class_blockers = _required_nonnegative_int(
        closure_summary,
        "dynamic_closure_blocker_count",
        label="extended closure summary",
    )
    remaining_mapping_gaps = _required_nonnegative_int(
        closure_summary,
        "remaining_mapping_gap_count",
        label="extended closure summary",
    )
    native_dynamic_requirements = _required_nonnegative_int(
        closure_summary,
        "native_dynamic_requirement_count",
        label="extended closure summary",
    )
    non_native_resource_blockers = _required_nonnegative_int(
        resource_summary,
        "non_native_blocker_count",
        label="extended resource summary",
    )
    native_resource_count = _required_nonnegative_int(
        resource_summary,
        "native_entry_count",
        label="extended resource summary",
    )
    native_resource_blockers = _required_nonnegative_int(
        resource_summary,
        "native_blocker_count",
        label="extended resource summary",
    )
    resource_equivalence_complete = _required_bool(
        resource_summary,
        "resource_equivalence_complete",
        label="extended resource summary",
    )

    class_closure_ready = (
        static_class_blockers == 0
        and dynamic_class_blockers == 0
        and remaining_mapping_gaps == 0
    )

    dynamic_target_blocker_count = sum(
        count
        for name, count in blocker_counts.items()
        if name not in {
            "service_provider_discovery_unproven",
            "native_dynamic_loading_requirement",
        }
    )
    service_provider_blockers = blocker_counts.get(
        "service_provider_discovery_unproven",
        0,
    )
    native_dynamic_blockers = blocker_counts.get(
        "native_dynamic_loading_requirement",
        0,
    )

    dynamic_target_ready = (
        dynamic_target_blocker_count == 0
        and service_provider_blockers == 0
        and native_dynamic_blockers == 0
    )

    resource_equivalence_ready = (
        resource_equivalence_complete
        and non_native_resource_blockers == 0
    )

    native_runtime_ready = (
        native_resource_count == 0
        and native_resource_blockers == 0
        and native_dynamic_requirements == 0
        and native_dynamic_blockers == 0
    )

    runtime_ready = (
        class_closure_ready
        and dynamic_target_ready
        and resource_equivalence_ready
        and native_runtime_ready
    )

    summary = {
        "class_closure_ready": class_closure_ready,
        "dynamic_target_ready": dynamic_target_ready,
        "resource_equivalence_ready": resource_equivalence_ready,
        "native_runtime_ready": native_runtime_ready,
        "static_class_closure_blocker_count": static_class_blockers,
        "dynamic_class_closure_blocker_count": dynamic_class_blockers,
        "remaining_mapping_gap_count": remaining_mapping_gaps,
        "dynamic_target_blocker_count": dynamic_target_blocker_count,
        "service_provider_discovery_blocker_count": (
            service_provider_blockers
        ),
        "dynamic_resource_target_blocker_count": (
            blocker_counts.get(
                "dynamic_resource_target_blocked",
                0,
            )
        ),
        "native_dynamic_loading_blocker_count": (
            native_dynamic_blockers
        ),
        "non_native_resource_blocker_count": (
            non_native_resource_blockers
        ),
        "native_resource_entry_count": native_resource_count,
        "native_resource_blocker_count": native_resource_blockers,
        "native_dynamic_requirement_count": (
            native_dynamic_requirements
        ),
        "dynamic_category_counts": dict(
            sorted(category_counts.items())
        ),
        "dynamic_blocker_counts": dict(
            sorted(blocker_counts.items())
        ),
        "runtime_dependency_substitution_ready": runtime_ready,
    }

    material = {
        "runtime_extended_closure_id": closure.get(
            "runtime_extended_closure_id"
        ),
        "runtime_extended_resource_id": resource.get(
            "runtime_extended_resource_id"
        ),
        "runtime_dynamic_target_id": dynamic.get(
            "runtime_dynamic_target_id"
        ),
        "replacement_plan_id": closure.get(
            "replacement_plan_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": supplied_sha,
        "target_resolutions": target_resolution_rows,
        "summary": summary,
    }
    readiness_id = (
        "DEPRUNTIMEREADY_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "dependency_runtime_substitution_readiness",
        "runtime_readiness_id": readiness_id,
        "runtime_extended_closure_id": closure.get(
            "runtime_extended_closure_id"
        ),
        "runtime_extended_resource_id": resource.get(
            "runtime_extended_resource_id"
        ),
        "runtime_dynamic_target_id": dynamic.get(
            "runtime_dynamic_target_id"
        ),
        "replacement_plan_id": closure.get(
            "replacement_plan_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": supplied_sha,
        "summary": summary,
        "target_resolutions": target_resolution_rows,
        "note": (
            "This is a read-only readiness gate. A true result authorizes "
            "only a later explicit mutation lane; it performs no runtime "
            "dependency substitution or pruning."
        ),
    }


def write_dependency_runtime_readiness(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
