from __future__ import annotations

from collections import Counter, deque
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .dependency_runtime_closure import (
    DependencyRuntimeClosureError,
    _official_authority,
    _profile_references,
)
from .dependency_runtime_frontier import (
    DependencyRuntimeFrontierError,
    _load_private_plan,
    _normalize_prefixes,
)


class DependencyRuntimeAugmentedClosureError(ValueError):
    pass


_PLATFORM_PREFIXES = (
    "java/",
    "jdk/",
    "sun/",
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


def _load_private(
    path: Path,
    *,
    kind: str,
    label: str,
) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRuntimeAugmentedClosureError(
            f"invalid {label} authority"
        ) from exc
    if value.get("kind") != kind:
        raise DependencyRuntimeAugmentedClosureError(
            f"unexpected {label} authority kind"
        )
    if value.get("identifiers_included") is not True:
        raise DependencyRuntimeAugmentedClosureError(
            f"{label} authority must include private identifiers"
        )
    return value


def build_dependency_runtime_augmented_closure(
    private_replacement_plan_path: Path,
    private_runtime_closure_path: Path,
    private_dynamic_target_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    private_replacement_plan_path = (
        private_replacement_plan_path.resolve()
    )
    private_runtime_closure_path = (
        private_runtime_closure_path.resolve()
    )
    private_dynamic_target_path = (
        private_dynamic_target_path.resolve()
    )
    bundled_jar = bundled_jar.resolve()

    try:
        plan = _load_private_plan(
            private_replacement_plan_path
        )
    except DependencyRuntimeFrontierError as exc:
        raise DependencyRuntimeAugmentedClosureError(
            str(exc)
        ) from exc

    static = _load_private(
        private_runtime_closure_path,
        kind="dependency_runtime_closure",
        label="runtime closure",
    )
    dynamic = _load_private(
        private_dynamic_target_path,
        kind=(
            "dependency_runtime_dynamic_target_classification"
        ),
        label="dynamic target",
    )

    if not bundled_jar.is_file():
        raise DependencyRuntimeAugmentedClosureError(
            "bundled/readable JAR does not exist"
        )
    bundled_sha = _sha256_file(bundled_jar)

    for label, value in (
        ("DEPREPLACE", plan),
        ("runtime closure", static),
        ("dynamic target", dynamic),
    ):
        if value.get("bundled_jar_sha256") != bundled_sha:
            raise DependencyRuntimeAugmentedClosureError(
                f"{label} is bound to a different bundled JAR"
            )

    replacement_id = plan.get("replacement_plan_id")
    if static.get("replacement_plan_id") != replacement_id:
        raise DependencyRuntimeAugmentedClosureError(
            "runtime closure is bound to a different DEPREPLACE"
        )
    if dynamic.get("replacement_plan_id") != replacement_id:
        raise DependencyRuntimeAugmentedClosureError(
            "dynamic target authority is bound to a different DEPREPLACE"
        )

    prefixes = _normalize_prefixes(
        plan.get("project_prefixes")
    )
    owner_rows_raw = plan.get("owners")
    if not isinstance(owner_rows_raw, list):
        raise DependencyRuntimeAugmentedClosureError(
            "private DEPREPLACE lacks owner rows"
        )
    owner_rows = {
        str(row["old_owner"]): row
        for row in owner_rows_raw
        if isinstance(row, dict)
        and isinstance(row.get("old_owner"), str)
    }

    static_owner_rows = static.get("owners")
    if not isinstance(static_owner_rows, list):
        raise DependencyRuntimeAugmentedClosureError(
            "private runtime closure lacks owner rows"
        )
    static_owner_names = {
        str(row["owner"])
        for row in static_owner_rows
        if isinstance(row, dict)
        and isinstance(row.get("owner"), str)
    }

    target_rows = dynamic.get("targets")
    if not isinstance(target_rows, list):
        raise DependencyRuntimeAugmentedClosureError(
            "private dynamic target authority lacks target rows"
        )

    class_targets: list[dict[str, Any]] = []
    resource_requirement_count = 0
    native_requirement_count = 0

    for row in target_rows:
        if not isinstance(row, dict):
            raise DependencyRuntimeAugmentedClosureError(
                "malformed dynamic target row"
            )
        category = row.get("category")
        if category in {"class_loading", "service_loading"}:
            normalized = row.get("normalized_class_target")
            if isinstance(normalized, str) and normalized:
                class_targets.append(row)
        elif category == "resource_loading":
            resource_requirement_count += 1
        elif category == "native_loading":
            native_requirement_count += 1

    try:
        owner_artifact, _artifact_paths, artifact_rows = (
            _official_authority(
                plan,
                official_artifacts,
            )
        )
    except DependencyRuntimeClosureError as exc:
        raise DependencyRuntimeAugmentedClosureError(
            str(exc)
        ) from exc

    artifact_sha = sorted(
        str(row["sha256"]).lower()
        for row in artifact_rows
    )
    static_artifact_sha = sorted(
        str(value).lower()
        for value in static.get(
            "official_artifact_sha256",
            [],
        )
    )
    if artifact_sha != static_artifact_sha:
        raise DependencyRuntimeAugmentedClosureError(
            "official artifact authority differs from runtime closure"
        )

    try:
        with zipfile.ZipFile(bundled_jar) as archive:
            class_entries: dict[str, zipfile.ZipInfo] = {}
            for info in archive.infolist():
                if (
                    info.is_dir()
                    or not info.filename.endswith(".class")
                    or info.filename.startswith(
                        "META-INF/versions/"
                    )
                ):
                    continue
                owner = info.filename[:-6]
                if owner in class_entries:
                    raise DependencyRuntimeAugmentedClosureError(
                        "duplicate base class entry: " + owner
                    )
                class_entries[owner] = info

            dynamic_root_rows: list[dict[str, Any]] = []
            added_roots: list[str] = []
            mapping_gap_count = 0
            already_static_count = 0
            protected_dynamic_count = 0

            for index, target_row in enumerate(
                class_targets,
                start=1,
            ):
                owner = str(
                    target_row["normalized_class_target"]
                )
                classification = str(
                    target_row.get("classification")
                )
                plan_row = owner_rows.get(owner)
                if owner in static_owner_names:
                    status = "already_in_static_closure"
                    already_static_count += 1
                elif (
                    plan_row is not None
                    and plan_row.get("classification")
                    == "official_replaceable"
                    and owner in class_entries
                ):
                    status = "authorized_dynamic_root"
                    added_roots.append(owner)
                elif owner in class_entries and plan_row is None:
                    status = "dynamic_mapping_authority_gap"
                    mapping_gap_count += 1
                else:
                    status = "protected_or_nontraversable_dynamic_target"
                    protected_dynamic_count += 1

                public = {
                    "dynamic_root_id": (
                        f"DEPAUGROOT_{index:05d}"
                    ),
                    "source_dynamic_target_id": target_row.get(
                        "dynamic_target_id"
                    ),
                    "status": status,
                    "source_classification": classification,
                }
                if include_identifiers:
                    public["owner"] = owner
                dynamic_root_rows.append(public)

            queue = deque(sorted(set(added_roots)))
            visited: set[str] = set()
            new_reachable: set[str] = set()
            edge_rows: list[dict[str, Any]] = []

            while queue:
                source = queue.popleft()
                if source in visited:
                    continue
                visited.add(source)
                info = class_entries.get(source)
                if info is None:
                    raise DependencyRuntimeAugmentedClosureError(
                        "authorized dynamic root is absent from base bundled classes"
                    )

                refs = _profile_references(
                    archive.read(info)
                )
                for target in sorted(refs):
                    edge_rows.append(
                        {"source": source, "target": target}
                    )
                    if target not in static_owner_names:
                        new_reachable.add(target)

                    target_plan = owner_rows.get(target)
                    if (
                        target in class_entries
                        and target not in visited
                        and target not in static_owner_names
                        and not any(
                            target.startswith(prefix)
                            for prefix in prefixes
                        )
                        and target_plan is not None
                        and target_plan.get("classification")
                        == "official_replaceable"
                    ):
                        queue.append(target)
    except zipfile.BadZipFile as exc:
        raise DependencyRuntimeAugmentedClosureError(
            "invalid bundled/readable JAR"
        ) from exc
    except DependencyRuntimeClosureError as exc:
        raise DependencyRuntimeAugmentedClosureError(
            str(exc)
        ) from exc

    new_owner_rows: list[dict[str, Any]] = []
    blocker_count = 0
    status_counts: Counter[str] = Counter()
    for owner in sorted(new_reachable):
        plan_row = owner_rows.get(owner)
        if any(owner.startswith(prefix) for prefix in prefixes):
            status = "project_retained"
        elif plan_row is not None:
            classification = plan_row.get("classification")
            if classification == "official_replaceable":
                new_owner = plan_row.get("new_owner")
                artifact = plan_row.get("artifact")
                if (
                    not isinstance(new_owner, str)
                    or not isinstance(artifact, str)
                    or owner_artifact.get(new_owner)
                    != artifact
                ):
                    raise DependencyRuntimeAugmentedClosureError(
                        "dynamic closure official target disagrees with artifact authority"
                    )
                status = "official_closure_mapped"
            elif classification == "residual_bundled":
                status = "residual_bundled"
            elif classification == "project_retained":
                status = "project_retained"
            elif classification == "platform_runtime":
                status = "platform_runtime"
            else:
                status = "unresolved"
        elif owner in class_entries:
            status = "dynamic_mapping_authority_gap"
        elif owner.startswith(_PLATFORM_PREFIXES):
            status = "platform_runtime"
        else:
            status = "unresolved"

        if status in {
            "residual_bundled",
            "project_retained",
            "dynamic_mapping_authority_gap",
            "unresolved",
        }:
            blocker_count += 1
        status_counts[status] += 1

        public = {
            "augmented_owner_id": (
                "DEPAUGOWNER_"
                + hashlib.sha256(
                    owner.encode("utf-8")
                ).hexdigest()[:16].upper()
            ),
            "status": status,
            "bundled_class_present": (
                owner in class_entries
            ),
        }
        if include_identifiers:
            public["owner"] = owner
        new_owner_rows.append(public)

    edge_public = [
        {
            "source_id": (
                "DEPAUGOWNER_"
                + hashlib.sha256(
                    row["source"].encode("utf-8")
                ).hexdigest()[:16].upper()
            ),
            "target_id": (
                "DEPAUGOWNER_"
                + hashlib.sha256(
                    row["target"].encode("utf-8")
                ).hexdigest()[:16].upper()
            ),
            **(
                {
                    "source": row["source"],
                    "target": row["target"],
                }
                if include_identifiers
                else {}
            ),
        }
        for row in sorted(
            edge_rows,
            key=lambda value: (
                value["source"],
                value["target"],
            ),
        )
    ]

    material_roots = [
        {
            key: value
            for key, value in row.items()
            if key != "owner"
        }
        for row in dynamic_root_rows
    ]
    material_owners = [
        {
            key: value
            for key, value in row.items()
            if key != "owner"
        }
        for row in new_owner_rows
    ]
    material_edges = [
        {
            key: value
            for key, value in row.items()
            if key not in {"source", "target"}
        }
        for row in edge_public
    ]

    material = {
        "runtime_closure_id": static.get(
            "runtime_closure_id"
        ),
        "runtime_dynamic_target_id": dynamic.get(
            "runtime_dynamic_target_id"
        ),
        "replacement_plan_id": replacement_id,
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": artifact_sha,
        "dynamic_roots": material_roots,
        "new_owners": material_owners,
        "new_edges": material_edges,
        "runtime_capsule_mutation_ready": False,
    }
    augmented_id = (
        "DEPRUNTIMEAUGCLOSURE_"
        + _stable_digest(material)[:20].upper()
    )

    static_summary = static.get("summary", {})
    return {
        "schema_version": 1,
        "kind": "dependency_runtime_augmented_closure",
        "runtime_augmented_closure_id": augmented_id,
        "runtime_closure_id": static.get(
            "runtime_closure_id"
        ),
        "runtime_dynamic_target_id": dynamic.get(
            "runtime_dynamic_target_id"
        ),
        "replacement_plan_id": replacement_id,
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": artifact_sha,
        "summary": {
            "static_root_count": int(
                static_summary.get("root_count", 0)
            ),
            "proven_dynamic_class_target_count": len(
                class_targets
            ),
            "dynamic_target_already_in_static_closure_count": (
                already_static_count
            ),
            "added_authorized_dynamic_root_count": len(
                set(added_roots)
            ),
            "dynamic_mapping_authority_gap_count": (
                mapping_gap_count
                + status_counts.get(
                    "dynamic_mapping_authority_gap",
                    0,
                )
            ),
            "protected_dynamic_target_count": (
                protected_dynamic_count
            ),
            "newly_reachable_owner_count": len(
                new_owner_rows
            ),
            "new_edge_count": len(edge_public),
            "new_status_counts": dict(
                sorted(status_counts.items())
            ),
            "static_class_closure_blocker_count": int(
                static_summary.get(
                    "class_closure_blocker_count",
                    0,
                )
            ),
            "dynamic_closure_blocker_count": blocker_count,
            "resource_dynamic_requirement_count": (
                resource_requirement_count
            ),
            "native_dynamic_requirement_count": (
                native_requirement_count
            ),
            "runtime_capsule_mutation_ready": False,
        },
        "dynamic_roots": dynamic_root_rows,
        "new_owners": new_owner_rows,
        "new_edges": edge_public,
        "identifiers_included": include_identifiers,
        "note": (
            "Dynamic-only bundled targets without accepted DEPREPLACE "
            "authority are mapping gaps, not inferred replacement roots."
        ),
    }


def write_dependency_runtime_augmented_closure(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
