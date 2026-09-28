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
from .decompiler import sha256_file


class DependencyRuntimeExtendedClosureError(ValueError):
    pass


_PLATFORM_PREFIXES = (
    "java/",
    "jdk/",
    "sun/",
)


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
        raise DependencyRuntimeExtendedClosureError(
            f"invalid {label} authority"
        ) from exc
    if value.get("kind") != kind:
        raise DependencyRuntimeExtendedClosureError(
            f"unexpected {label} authority kind"
        )
    if value.get("identifiers_included") is not True:
        raise DependencyRuntimeExtendedClosureError(
            f"{label} authority must include private identifiers"
        )
    return value


def build_dependency_runtime_extended_closure(
    private_replacement_plan_path: Path,
    private_replacement_extension_path: Path,
    private_runtime_closure_path: Path,
    private_dynamic_target_path: Path,
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
        raise DependencyRuntimeExtendedClosureError(str(exc)) from exc

    extension = _load_private(
        private_replacement_extension_path.resolve(),
        kind="dependency_replacement_extension",
        label="replacement extension",
    )
    static = _load_private(
        private_runtime_closure_path.resolve(),
        kind="dependency_runtime_closure",
        label="runtime closure",
    )
    dynamic = _load_private(
        private_dynamic_target_path.resolve(),
        kind="dependency_runtime_dynamic_target_classification",
        label="dynamic target",
    )

    bundled_jar = bundled_jar.resolve()
    if not bundled_jar.is_file():
        raise DependencyRuntimeExtendedClosureError(
            "bundled/readable JAR does not exist"
        )
    bundled_sha = sha256_file(bundled_jar)
    replacement_id = plan.get("replacement_plan_id")

    for label, value in (
        ("DEPREPLACE", plan),
        ("replacement extension", extension),
        ("runtime closure", static),
        ("dynamic target", dynamic),
    ):
        if value.get("bundled_jar_sha256") != bundled_sha:
            raise DependencyRuntimeExtendedClosureError(
                f"{label} is bound to a different bundled JAR"
            )
        if label != "DEPREPLACE" and value.get(
            "replacement_plan_id"
        ) != replacement_id:
            raise DependencyRuntimeExtendedClosureError(
                f"{label} is bound to a different DEPREPLACE"
            )

    prefixes = _normalize_prefixes(plan.get("project_prefixes"))

    original_rows_raw = plan.get("owners")
    if not isinstance(original_rows_raw, list):
        raise DependencyRuntimeExtendedClosureError(
            "private DEPREPLACE lacks owner rows"
        )

    combined: dict[str, dict[str, Any]] = {}
    source_by_owner: dict[str, str] = {}
    for row in original_rows_raw:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("old_owner"), str)
        ):
            raise DependencyRuntimeExtendedClosureError(
                "malformed DEPREPLACE owner row"
            )
        owner = str(row["old_owner"])
        if owner in combined:
            raise DependencyRuntimeExtendedClosureError(
                "duplicate DEPREPLACE owner row"
            )
        combined[owner] = row
        source_by_owner[owner] = "depreplace"

    promoted_rows = extension.get("promoted_rows")
    if not isinstance(promoted_rows, list):
        raise DependencyRuntimeExtendedClosureError(
            "private replacement extension lacks promoted rows"
        )
    promoted_owners: set[str] = set()
    for row in promoted_rows:
        if (
            not isinstance(row, dict)
            or row.get("status") != "promotion_eligible"
            or row.get("classification") != "official_replaceable"
            or row.get("member_transport_complete") is not True
            or not isinstance(row.get("old_owner"), str)
            or not isinstance(row.get("new_owner"), str)
            or not isinstance(row.get("artifact"), str)
        ):
            raise DependencyRuntimeExtendedClosureError(
                "invalid promoted replacement-extension row"
            )
        owner = str(row["old_owner"])
        candidate = {
            "classification": "official_replaceable",
            "old_owner": owner,
            "new_owner": str(row["new_owner"]),
            "artifact": str(row["artifact"]),
            "owner_id": row.get("extension_row_id"),
        }
        prior = combined.get(owner)
        if prior is not None:
            if (
                prior.get("classification")
                != candidate["classification"]
                or prior.get("new_owner") != candidate["new_owner"]
                or prior.get("artifact") != candidate["artifact"]
            ):
                raise DependencyRuntimeExtendedClosureError(
                    "replacement extension conflicts with DEPREPLACE"
                )
            continue
        combined[owner] = candidate
        source_by_owner[owner] = "replacement_extension"
        promoted_owners.add(owner)

    try:
        owner_artifact, _artifact_paths, artifact_rows = (
            _official_authority(
                plan,
                official_artifacts,
            )
        )
    except DependencyRuntimeClosureError as exc:
        raise DependencyRuntimeExtendedClosureError(str(exc)) from exc

    artifact_sha = sorted(
        str(row["sha256"]).lower()
        for row in artifact_rows
    )
    for label, value in (
        ("replacement extension", extension),
        ("runtime closure", static),
    ):
        if sorted(
            str(item).lower()
            for item in value.get("official_artifact_sha256", [])
        ) != artifact_sha:
            raise DependencyRuntimeExtendedClosureError(
                f"{label} official artifact authority drifted"
            )

    static_rows = static.get("owners")
    if not isinstance(static_rows, list):
        raise DependencyRuntimeExtendedClosureError(
            "private runtime closure lacks owner rows"
        )
    static_owner_names = {
        str(row["owner"])
        for row in static_rows
        if isinstance(row, dict)
        and isinstance(row.get("owner"), str)
    }

    targets = dynamic.get("targets")
    if not isinstance(targets, list):
        raise DependencyRuntimeExtendedClosureError(
            "private dynamic target authority lacks target rows"
        )

    class_targets: list[dict[str, Any]] = []
    resource_requirement_count = 0
    native_requirement_count = 0
    for row in targets:
        if not isinstance(row, dict):
            raise DependencyRuntimeExtendedClosureError(
                "malformed dynamic target row"
            )
        category = row.get("category")
        if category in {"class_loading", "service_loading"}:
            if (
                row.get("literal_target_proven") is True
                and isinstance(
                    row.get("normalized_class_target"),
                    str,
                )
                and row.get("normalized_class_target")
            ):
                class_targets.append(row)
        elif category == "resource_loading":
            resource_requirement_count += 1
        elif category == "native_loading":
            native_requirement_count += 1

    try:
        with zipfile.ZipFile(bundled_jar) as archive:
            class_entries: dict[str, zipfile.ZipInfo] = {}
            for info in archive.infolist():
                if (
                    info.is_dir()
                    or not info.filename.endswith(".class")
                    or info.filename.startswith("META-INF/versions/")
                ):
                    continue
                owner = info.filename[:-6]
                if owner in class_entries:
                    raise DependencyRuntimeExtendedClosureError(
                        "duplicate base class entry: " + owner
                    )
                class_entries[owner] = info

            root_rows: list[dict[str, Any]] = []
            added_roots: list[str] = []
            already_static_count = 0
            extension_promoted_root_owners: set[str] = set()
            prior_gap_resolved_owners: set[str] = set()
            root_mapping_gap_owners: set[str] = set()
            protected_root_count = 0

            for index, target_row in enumerate(
                class_targets,
                start=1,
            ):
                owner = str(
                    target_row["normalized_class_target"]
                )
                prior_classification = str(
                    target_row.get("classification")
                )
                authority = combined.get(owner)

                if owner in static_owner_names:
                    status = "already_in_static_closure"
                    already_static_count += 1
                elif (
                    authority is not None
                    and authority.get("classification")
                    == "official_replaceable"
                    and owner in class_entries
                ):
                    new_owner = authority.get("new_owner")
                    artifact = authority.get("artifact")
                    if (
                        not isinstance(new_owner, str)
                        or not isinstance(artifact, str)
                        or owner_artifact.get(new_owner) != artifact
                    ):
                        raise DependencyRuntimeExtendedClosureError(
                            "dynamic root official target disagrees with artifact authority"
                        )
                    status = "authorized_dynamic_root"
                    added_roots.append(owner)
                    if source_by_owner.get(owner) == "replacement_extension":
                        extension_promoted_root_owners.add(owner)
                        if prior_classification in {
                            "bundled_unclassified",
                            "service_bundled_unclassified",
                        }:
                            prior_gap_resolved_owners.add(owner)
                elif owner in class_entries and authority is None:
                    status = "remaining_mapping_authority_gap"
                    root_mapping_gap_owners.add(owner)
                else:
                    status = "protected_or_nontraversable_dynamic_target"
                    protected_root_count += 1

                public = {
                    "extended_root_id": f"DEPEXTCLOSUREROOT_{index:05d}",
                    "source_dynamic_target_id": target_row.get(
                        "dynamic_target_id"
                    ),
                    "status": status,
                    "prior_classification": prior_classification,
                    "authority_source": (
                        source_by_owner.get(owner)
                        if authority is not None
                        else None
                    ),
                }
                if include_identifiers:
                    public["owner"] = owner
                root_rows.append(public)

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
                    raise DependencyRuntimeExtendedClosureError(
                        "authorized dynamic root missing bundled class entry"
                    )

                try:
                    refs = _profile_references(archive.read(info))
                except DependencyRuntimeClosureError as exc:
                    raise DependencyRuntimeExtendedClosureError(
                        str(exc)
                    ) from exc

                for target in sorted(refs):
                    edge_rows.append(
                        {"source": source, "target": target}
                    )
                    if target not in static_owner_names:
                        new_reachable.add(target)

                    authority = combined.get(target)
                    if (
                        target in class_entries
                        and target not in visited
                        and target not in static_owner_names
                        and not any(
                            target.startswith(prefix)
                            for prefix in prefixes
                        )
                        and authority is not None
                        and authority.get("classification")
                        == "official_replaceable"
                    ):
                        queue.append(target)
    except zipfile.BadZipFile as exc:
        raise DependencyRuntimeExtendedClosureError(
            "invalid bundled/readable JAR"
        ) from exc

    owner_rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    blocker_count = 0
    reachable_mapping_gap_owners: set[str] = set()

    for owner in sorted(new_reachable):
        authority = combined.get(owner)
        authority_source = source_by_owner.get(owner)

        if any(owner.startswith(prefix) for prefix in prefixes):
            status = "project_retained"
        elif authority is not None:
            classification = authority.get("classification")
            if classification == "official_replaceable":
                new_owner = authority.get("new_owner")
                artifact = authority.get("artifact")
                if (
                    not isinstance(new_owner, str)
                    or not isinstance(artifact, str)
                    or owner_artifact.get(new_owner) != artifact
                ):
                    raise DependencyRuntimeExtendedClosureError(
                        "extended closure official target disagrees with artifact authority"
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
            status = "remaining_mapping_authority_gap"
            reachable_mapping_gap_owners.add(owner)
        elif owner.startswith(_PLATFORM_PREFIXES):
            status = "platform_runtime"
        else:
            status = "unresolved"

        if status in {
            "residual_bundled",
            "project_retained",
            "remaining_mapping_authority_gap",
            "unresolved",
        }:
            blocker_count += 1

        status_counts[status] += 1
        public = {
            "extended_owner_id": (
                "DEPEXTCLOSUREOWNER_"
                + hashlib.sha256(
                    owner.encode("utf-8")
                ).hexdigest()[:16].upper()
            ),
            "status": status,
            "authority_source": authority_source,
            "bundled_class_present": owner in class_entries,
        }
        if include_identifiers:
            public["owner"] = owner
        owner_rows.append(public)

    edge_public = [
        {
            "source_id": (
                "DEPEXTCLOSUREOWNER_"
                + hashlib.sha256(
                    row["source"].encode("utf-8")
                ).hexdigest()[:16].upper()
            ),
            "target_id": (
                "DEPEXTCLOSUREOWNER_"
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
        for row in root_rows
    ]
    material_owners = [
        {
            key: value
            for key, value in row.items()
            if key != "owner"
        }
        for row in owner_rows
    ]
    material_edges = [
        {
            key: value
            for key, value in row.items()
            if key not in {"source", "target"}
        }
        for row in edge_public
    ]

    remaining_mapping_gap_owners = (
        root_mapping_gap_owners
        | reachable_mapping_gap_owners
    )
    remaining_mapping_gap_count = len(
        remaining_mapping_gap_owners
    )

    material = {
        "replacement_plan_id": replacement_id,
        "replacement_extension_id": extension.get(
            "replacement_extension_id"
        ),
        "runtime_closure_id": static.get("runtime_closure_id"),
        "runtime_dynamic_target_id": dynamic.get(
            "runtime_dynamic_target_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": artifact_sha,
        "roots": material_roots,
        "owners": material_owners,
        "edges": material_edges,
        "runtime_capsule_mutation_ready": False,
    }
    closure_id = (
        "DEPRUNTIMEEXTCLOSURE_"
        + _stable_digest(material)[:20].upper()
    )

    static_summary = static.get("summary", {})
    return {
        "schema_version": 1,
        "kind": "dependency_runtime_extended_closure",
        "runtime_extended_closure_id": closure_id,
        "replacement_plan_id": replacement_id,
        "replacement_extension_id": extension.get(
            "replacement_extension_id"
        ),
        "runtime_closure_id": static.get("runtime_closure_id"),
        "runtime_dynamic_target_id": dynamic.get(
            "runtime_dynamic_target_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": artifact_sha,
        "summary": {
            "static_root_count": int(
                static_summary.get("root_count", 0)
            ),
            "proven_dynamic_class_target_count": len(class_targets),
            "dynamic_target_already_in_static_closure_count": (
                already_static_count
            ),
            "authorized_dynamic_root_count": len(set(added_roots)),
            "extension_promoted_dynamic_root_count": len(
                extension_promoted_root_owners
            ),
            "prior_mapping_gap_resolved_count": len(
                prior_gap_resolved_owners
            ),
            "remaining_mapping_gap_count": (
                remaining_mapping_gap_count
            ),
            "protected_dynamic_target_count": protected_root_count,
            "newly_reachable_owner_count": len(owner_rows),
            "new_edge_count": len(edge_public),
            "new_status_counts": dict(
                sorted(status_counts.items())
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
        "dynamic_roots": root_rows,
        "new_owners": owner_rows,
        "new_edges": edge_public,
        "identifiers_included": include_identifiers,
        "note": (
            "The extended closure consumes R8DEP33 additively and never "
            "rewrites DEPREPLACE. Runtime capsule mutation remains disabled."
        ),
    }


def write_dependency_runtime_extended_closure(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
