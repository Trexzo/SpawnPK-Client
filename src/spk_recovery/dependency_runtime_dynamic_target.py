from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any
import zipfile

from .dependency_runtime_frontier import (
    DependencyRuntimeFrontierError,
    _load_private_plan,
    _normalize_prefixes,
)


class DependencyRuntimeDynamicTargetError(ValueError):
    pass


_BINARY_SEGMENT_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
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


def _load_private_json(
    path: Path,
    *,
    kind: str,
    label: str,
) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRuntimeDynamicTargetError(
            f"invalid {label} authority"
        ) from exc
    if value.get("kind") != kind:
        raise DependencyRuntimeDynamicTargetError(
            f"unexpected {label} authority kind"
        )
    if value.get("identifiers_included") is not True:
        raise DependencyRuntimeDynamicTargetError(
            f"{label} authority must include private identifiers"
        )
    return value


def _valid_internal_name(value: str) -> bool:
    if not value or value.startswith("/") or value.endswith("/"):
        return False
    parts = value.split("/")
    return all(
        bool(_BINARY_SEGMENT_RE.fullmatch(part))
        for part in parts
    )


def _binary_name_to_internal(value: str) -> str | None:
    if (
        not value
        or "/" in value
        or value.startswith("[")
        or value.endswith(".")
    ):
        return None
    parts = value.split(".")
    if not all(
        bool(_BINARY_SEGMENT_RE.fullmatch(part))
        for part in parts
    ):
        return None
    return "/".join(parts)


def _safe_resource_literal(value: str) -> bool:
    if not value or "\\" in value or "\x00" in value:
        return False
    parts = value.split("/")
    return all(part not in {".", ".."} for part in parts)


def _resource_entry_for_callsite(
    row: dict[str, Any],
) -> str | None:
    target = row.get("literal_target")
    owner = row.get("invoked_owner")
    name = row.get("invoked_name")
    caller = row.get("caller")
    if (
        not isinstance(target, str)
        or not isinstance(owner, str)
        or not isinstance(name, str)
        or not isinstance(caller, str)
    ):
        return None
    if not _safe_resource_literal(target):
        return None

    if owner == "java/lang/Class" and name in {
        "getResource",
        "getResourceAsStream",
    }:
        if target.startswith("/"):
            stripped = target[1:]
            return stripped if stripped else None
        package = (
            caller.rsplit("/", 1)[0]
            if "/" in caller
            else ""
        )
        return (
            package + "/" + target
            if package
            else target
        )

    if owner == "java/lang/ClassLoader" and name in {
        "getResource",
        "getResourceAsStream",
        "getResources",
    }:
        if target.startswith("/"):
            return None
        return target

    return None


def _jar_authority(
    bundled_jar: Path,
) -> tuple[set[str], set[str], set[str]]:
    base_classes: set[str] = set()
    versioned_classes: set[str] = set()
    resources: set[str] = set()
    try:
        with zipfile.ZipFile(bundled_jar) as archive:
            seen: set[str] = set()
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                if name in seen:
                    raise DependencyRuntimeDynamicTargetError(
                        "duplicate bundled JAR entry: " + name
                    )
                seen.add(name)
                if name.endswith(".class"):
                    if name.startswith("META-INF/versions/"):
                        parts = name.split("/", 3)
                        if len(parts) == 4 and parts[2].isdigit():
                            versioned_classes.add(parts[3][:-6])
                        continue
                    base_classes.add(name[:-6])
                else:
                    resources.add(name)
    except zipfile.BadZipFile as exc:
        raise DependencyRuntimeDynamicTargetError(
            "invalid bundled/readable JAR"
        ) from exc
    return base_classes, versioned_classes, resources


def build_dependency_runtime_dynamic_target_classification(
    private_dynamic_path: Path,
    private_replacement_plan_path: Path,
    private_runtime_resource_path: Path,
    bundled_jar: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    private_dynamic_path = private_dynamic_path.resolve()
    private_replacement_plan_path = (
        private_replacement_plan_path.resolve()
    )
    private_runtime_resource_path = (
        private_runtime_resource_path.resolve()
    )
    bundled_jar = bundled_jar.resolve()

    dynamic = _load_private_json(
        private_dynamic_path,
        kind="dependency_runtime_dynamic_inventory",
        label="runtime dynamic",
    )
    resource = _load_private_json(
        private_runtime_resource_path,
        kind="dependency_runtime_resource_equivalence",
        label="runtime resource",
    )
    try:
        replacement = _load_private_plan(
            private_replacement_plan_path
        )
    except DependencyRuntimeFrontierError as exc:
        raise DependencyRuntimeDynamicTargetError(
            str(exc)
        ) from exc

    if not bundled_jar.is_file():
        raise DependencyRuntimeDynamicTargetError(
            "bundled/readable JAR does not exist"
        )
    bundled_sha = _sha256_file(bundled_jar)

    for label, value in (
        ("runtime dynamic", dynamic),
        ("runtime resource", resource),
        ("DEPREPLACE", replacement),
    ):
        if value.get("bundled_jar_sha256") != bundled_sha:
            raise DependencyRuntimeDynamicTargetError(
                f"{label} is bound to a different bundled JAR"
            )

    if dynamic.get("runtime_resource_id") != resource.get(
        "runtime_resource_id"
    ):
        raise DependencyRuntimeDynamicTargetError(
            "runtime dynamic authority is bound to a different "
            "runtime resource authority"
        )

    prefixes = _normalize_prefixes(
        replacement.get("project_prefixes")
    )
    owner_rows_raw = replacement.get("owners")
    if not isinstance(owner_rows_raw, list):
        raise DependencyRuntimeDynamicTargetError(
            "private DEPREPLACE lacks owner rows"
        )
    replacement_by_owner = {
        str(row["old_owner"]): row
        for row in owner_rows_raw
        if isinstance(row, dict)
        and isinstance(row.get("old_owner"), str)
    }

    resource_rows_raw = resource.get("resources")
    if not isinstance(resource_rows_raw, list):
        raise DependencyRuntimeDynamicTargetError(
            "private runtime resource authority lacks resource rows"
        )
    resource_by_entry = {
        str(row["entry"]): row
        for row in resource_rows_raw
        if isinstance(row, dict)
        and isinstance(row.get("entry"), str)
    }

    (
        bundled_classes,
        versioned_classes,
        bundled_resources,
    ) = _jar_authority(bundled_jar)

    calls = dynamic.get("callsites")
    if not isinstance(calls, list):
        raise DependencyRuntimeDynamicTargetError(
            "private runtime dynamic authority lacks callsites"
        )

    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    classification_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()

    for index, row in enumerate(calls, start=1):
        if not isinstance(row, dict):
            raise DependencyRuntimeDynamicTargetError(
                "malformed dynamic callsite row"
            )
        callsite_id = row.get("callsite_id")
        category = row.get("category")
        dynamic_classification = row.get("classification")
        proven = row.get("literal_target_proven") is True
        literal = row.get("literal_target")

        if (
            not isinstance(callsite_id, str)
            or not isinstance(category, str)
            or not isinstance(dynamic_classification, str)
        ):
            raise DependencyRuntimeDynamicTargetError(
                "invalid dynamic callsite authority"
            )

        normalized_target: str | None = None
        resource_entry: str | None = None
        resource_status: str | None = None
        replacement_classification: str | None = None

        if not proven:
            classification = "dynamic_target_unresolved"
        elif category == "class_loading":
            if not isinstance(literal, str):
                classification = "class_target_malformed"
            else:
                normalized_target = _binary_name_to_internal(
                    literal
                )
                if normalized_target is None:
                    classification = "class_target_malformed"
                elif any(
                    normalized_target.startswith(prefix)
                    for prefix in prefixes
                ):
                    classification = "project_class"
                elif normalized_target in replacement_by_owner:
                    replacement_classification = str(
                        replacement_by_owner[
                            normalized_target
                        ].get("classification")
                    )
                    classification = (
                        "dependency_"
                        + replacement_classification
                    )
                elif normalized_target in bundled_classes:
                    classification = "bundled_unclassified"
                elif normalized_target in versioned_classes:
                    classification = (
                        "bundled_multi_release_unresolved"
                    )
                elif normalized_target.startswith(
                    _PLATFORM_PREFIXES
                ):
                    classification = "platform_runtime"
                else:
                    classification = "non_bundled_unresolved"

        elif category == "service_loading":
            if not isinstance(literal, str):
                classification = "service_class_token_malformed"
            elif not _valid_internal_name(literal):
                classification = "service_class_token_malformed"
            else:
                normalized_target = literal
                if any(
                    literal.startswith(prefix)
                    for prefix in prefixes
                ):
                    classification = "service_project_class_token"
                elif literal in replacement_by_owner:
                    replacement_classification = str(
                        replacement_by_owner[
                            literal
                        ].get("classification")
                    )
                    classification = (
                        "service_dependency_"
                        + replacement_classification
                    )
                elif literal in bundled_classes:
                    classification = (
                        "service_bundled_unclassified"
                    )
                elif literal.startswith(_PLATFORM_PREFIXES):
                    classification = (
                        "service_platform_class_token"
                    )
                else:
                    classification = (
                        "service_non_bundled_unresolved"
                    )

        elif category == "resource_loading":
            resource_entry = _resource_entry_for_callsite(row)
            if resource_entry is None:
                classification = (
                    "resource_semantics_unresolved"
                )
            else:
                authority_row = resource_by_entry.get(
                    resource_entry
                )
                if authority_row is not None:
                    resource_status = str(
                        authority_row.get("status")
                    )
                    if resource_status in {
                        "exact_byte_match",
                        "service_trailing_newline_equivalent",
                    }:
                        classification = (
                            "resource_official_equivalent"
                        )
                    else:
                        classification = (
                            "resource_official_blocked"
                        )
                elif resource_entry in bundled_resources:
                    classification = "resource_bundled_only"
                else:
                    classification = "resource_missing"

        elif category == "native_loading":
            classification = (
                "native_runtime_requirement"
                if isinstance(literal, str)
                and literal
                else "native_target_unresolved"
            )
        else:
            classification = "unsupported_dynamic_category"

        category_counts[category] += 1
        classification_counts[classification] += 1

        public = {
            "dynamic_target_id": (
                f"DEPRUNTIME_DYNAMIC_TARGET_{index:05d}"
            ),
            "source_callsite_id": callsite_id,
            "category": category,
            "classification": classification,
            "literal_target_proven": proven,
            "resource_authority_status": resource_status,
            "replacement_classification": (
                replacement_classification
            ),
        }
        public_rows.append(public)

        if include_identifiers:
            private_rows.append(
                {
                    **public,
                    "literal_target": literal,
                    "normalized_class_target": (
                        normalized_target
                    ),
                    "resource_entry": resource_entry,
                    "caller": row.get("caller"),
                    "caller_method": row.get(
                        "caller_method"
                    ),
                    "invoked_owner": row.get(
                        "invoked_owner"
                    ),
                    "invoked_name": row.get(
                        "invoked_name"
                    ),
                    "invoked_descriptor": row.get(
                        "invoked_descriptor"
                    ),
                }
            )

    blocker_classes = {
        "dynamic_target_unresolved",
        "class_target_malformed",
        "dependency_residual_bundled",
        "dependency_project_retained",
        "bundled_unclassified",
        "bundled_multi_release_unresolved",
        "non_bundled_unresolved",
        "service_class_token_malformed",
        "service_dependency_residual_bundled",
        "service_dependency_project_retained",
        "service_bundled_unclassified",
        "service_non_bundled_unresolved",
        "resource_semantics_unresolved",
        "resource_official_blocked",
        "resource_bundled_only",
        "resource_missing",
        "native_runtime_requirement",
        "native_target_unresolved",
        "unsupported_dynamic_category",
    }
    unresolved_or_blocked_count = sum(
        classification_counts.get(value, 0)
        for value in blocker_classes
    )

    material = {
        "runtime_dynamic_id": dynamic.get(
            "runtime_dynamic_id"
        ),
        "runtime_resource_id": resource.get(
            "runtime_resource_id"
        ),
        "replacement_plan_id": replacement.get(
            "replacement_plan_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "targets": public_rows,
        "unresolved_or_blocked_count": (
            unresolved_or_blocked_count
        ),
        "runtime_capsule_mutation_ready": False,
    }
    target_id = (
        "DEPRUNTIMEDYNAMICTARGET_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "dependency_runtime_dynamic_target_classification",
        "runtime_dynamic_target_id": target_id,
        "runtime_dynamic_id": dynamic.get(
            "runtime_dynamic_id"
        ),
        "runtime_resource_id": resource.get(
            "runtime_resource_id"
        ),
        "replacement_plan_id": replacement.get(
            "replacement_plan_id"
        ),
        "bundled_jar_sha256": bundled_sha,
        "summary": {
            "target_count": len(public_rows),
            "category_counts": dict(
                sorted(category_counts.items())
            ),
            "classification_counts": dict(
                sorted(classification_counts.items())
            ),
            "unresolved_or_blocked_count": (
                unresolved_or_blocked_count
            ),
            "service_provider_discovery_unproven": (
                category_counts.get("service_loading", 0)
                > 0
            ),
            "native_artifact_equivalence_unproven": (
                category_counts.get("native_loading", 0)
                > 0
            ),
            "runtime_capsule_mutation_ready": False,
        },
        "targets": (
            private_rows
            if include_identifiers
            else public_rows
        ),
        "identifiers_included": include_identifiers,
        "note": (
            "Proven dynamic literals are classified against exact runtime "
            "authority only. Service-provider discovery and native artifact "
            "equivalence remain separate fail-closed boundaries."
        ),
    }


def write_dependency_runtime_dynamic_target_classification(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
