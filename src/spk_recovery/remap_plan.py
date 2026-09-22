from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .lineage import LineageValidationError, validate_lineage


class RemapPlanError(LineageValidationError):
    pass


_INTERNAL_SEGMENT = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
_FORBIDDEN_PREFIXES = ("java/", "javax/", "jdk/", "sun/")


def _validate_internal_name(name: Any, *, label: str) -> str:
    if (
        not isinstance(name, str)
        or not name
        or name.startswith("/")
        or name.endswith("/")
    ):
        raise RemapPlanError(
            f"{label}: invalid JVM internal class name {name!r}"
        )
    if "." in name:
        raise RemapPlanError(
            f"{label}: use JVM internal '/' separators, not dotted names"
        )
    parts = name.split("/")
    if any(not _INTERNAL_SEGMENT.fullmatch(part) for part in parts):
        raise RemapPlanError(
            f"{label}: invalid JVM internal class name {name!r}"
        )
    if name.startswith(_FORBIDDEN_PREFIXES):
        raise RemapPlanError(
            f"{label}: target package is reserved: {name!r}"
        )
    return name


def _build(
    lineage: dict[str, Any],
    build_id: str,
) -> dict[str, Any]:
    hits = [
        b
        for b in lineage.get("builds", [])
        if b.get("build_id") == build_id
    ]
    if len(hits) != 1:
        raise RemapPlanError(
            f"expected one canonical build {build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _logical_map(
    lineage: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        record["logical_id"]: record
        for record in lineage.get("classes", [])
    }


def _entry_for_build(
    record: dict[str, Any],
    build_id: str,
) -> dict[str, Any]:
    hits = [
        entry
        for entry in record.get("lineage", [])
        if entry.get("build_id") == build_id
    ]
    if len(hits) != 1:
        raise RemapPlanError(
            f"logical class {record.get('logical_id')} has {len(hits)} "
            f"entries for {build_id!r}"
        )
    return hits[0]


def build_remap_plan(
    lineage: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Resolve an explicit logical-ID remap specification for one build."""
    validate_lineage(lineage)
    if (
        spec.get("schema_version") != 1
        or spec.get("kind") != "remap_spec"
    ):
        raise RemapPlanError("unsupported remap spec schema/kind")

    build_id = spec.get("build_id")
    if not isinstance(build_id, str) or not build_id:
        raise RemapPlanError("remap spec build_id must be non-empty")

    build = _build(lineage, build_id)
    source_sha = spec.get("source_sha256")
    if (
        not isinstance(source_sha, str)
        or source_sha.lower()
        != str(build.get("sha256", "")).lower()
    ):
        raise RemapPlanError(
            "remap spec source_sha256 does not match canonical build"
        )

    requested = spec.get("classes")
    if not isinstance(requested, dict) or not requested:
        raise RemapPlanError(
            "remap spec classes must be a non-empty object"
        )

    logical = _logical_map(lineage)
    all_source_names: dict[str, str] = {}
    for logical_id, record in logical.items():
        for entry in record.get("lineage", []):
            if entry.get("build_id") == build_id:
                all_source_names[entry["internal_name"]] = logical_id

    targets: set[str] = set()
    rows: list[dict[str, Any]] = []
    for logical_id in sorted(requested):
        cfg = requested[logical_id]
        if logical_id not in logical:
            raise RemapPlanError(
                f"unknown logical class {logical_id!r}"
            )
        if not isinstance(cfg, dict):
            raise RemapPlanError(
                f"{logical_id}: mapping entry must be an object"
            )

        target = _validate_internal_name(
            cfg.get("target_internal_name"),
            label=f"{logical_id}.target_internal_name",
        )
        if target in targets:
            raise RemapPlanError(
                f"duplicate target internal name {target!r}"
            )
        targets.add(target)

        entry = _entry_for_build(
            logical[logical_id],
            build_id,
        )
        source = entry["internal_name"]
        if target == source:
            raise RemapPlanError(
                f"{logical_id}: target equals source; omit no-op remaps"
            )

        occupant = all_source_names.get(target)
        if occupant is not None and occupant != logical_id:
            raise RemapPlanError(
                f"{logical_id}: target {target!r} collides with "
                f"existing build class {occupant}"
            )

        confidence = cfg.get("confidence")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
        ):
            raise RemapPlanError(
                f"{logical_id}.confidence must be numeric"
            )
        confidence = float(confidence)
        if not 0.0 <= confidence <= 1.0:
            raise RemapPlanError(
                f"{logical_id}.confidence must be in [0,1]"
            )

        provenance = cfg.get("provenance")
        if not isinstance(provenance, list) or not provenance:
            raise RemapPlanError(
                f"{logical_id}.provenance must be a non-empty array"
            )

        rows.append(
            {
                "logical_id": logical_id,
                "source_internal_name": source,
                "source_entry_path": entry["entry_path"],
                "source_entry_sha256": entry["entry_sha256"],
                "target_internal_name": target,
                "target_entry_path": target + ".class",
                "confidence": confidence,
                "provenance": provenance,
            }
        )

    return {
        "schema_version": 1,
        "kind": "remap_plan",
        "build_id": build_id,
        "source_sha256": str(build["sha256"]).lower(),
        "class_count": len(rows),
        "classes": rows,
    }


def remap_risk_scan(
    index: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    if (
        plan.get("schema_version") != 1
        or plan.get("kind") != "remap_plan"
    ):
        raise RemapPlanError(
            "unsupported remap plan schema/kind"
        )
    if (
        str(index.get("sha256", "")).lower()
        != str(plan.get("source_sha256", "")).lower()
    ):
        raise RemapPlanError(
            "index SHA does not match remap plan source"
        )

    mappings = {
        row["source_internal_name"]: row["target_internal_name"]
        for row in plan.get("classes", [])
    }

    literal_hits: list[dict[str, Any]] = []
    package_resource_hits: list[dict[str, Any]] = []
    service_entries = sorted(
        path
        for path in index.get("entries", {})
        if path.startswith("META-INF/services/")
    )

    for class_path, cls in sorted(
        index.get("classes", {}).items()
    ):
        strings = cls.get("literal_strings", [])
        if not isinstance(strings, list):
            continue
        for source, target in mappings.items():
            forms = {
                source,
                source.replace("/", "."),
            }
            hits = sorted(
                {
                    value
                    for value in strings
                    if isinstance(value, str)
                    and value in forms
                }
            )
            if hits:
                literal_hits.append(
                    {
                        "class_path": class_path,
                        "source_internal_name": source,
                        "target_internal_name": target,
                        "literals": hits,
                    }
                )

    non_class_entries = [
        path
        for path in index.get("entries", {})
        if not path.endswith(".class")
    ]
    for source, target in sorted(mappings.items()):
        source_pkg = (
            source.rsplit("/", 1)[0] + "/"
            if "/" in source
            else ""
        )
        if not source_pkg:
            continue
        hits = sorted(
            path
            for path in non_class_entries
            if path.startswith(source_pkg)
        )
        if hits:
            package_resource_hits.append(
                {
                    "source_internal_name": source,
                    "target_internal_name": target,
                    "source_package": source_pkg,
                    "resource_entries": hits,
                }
            )

    manifest_requires_review = (
        "META-INF/MANIFEST.MF" in index.get("entries", {})
        and bool(mappings)
    )

    return {
        "schema_version": 1,
        "kind": "remap_risk_report",
        "source_sha256": plan["source_sha256"],
        "mapped_classes": len(mappings),
        "literal_class_name_hits": literal_hits,
        "package_resource_hits": package_resource_hits,
        "service_descriptor_entries": service_entries,
        "manifest_requires_review": manifest_requires_review,
        "summary": {
            "literal_class_name_hit_count": len(
                literal_hits
            ),
            "package_resource_hit_count": len(
                package_resource_hits
            ),
            "service_descriptor_count": len(
                service_entries
            ),
            "manifest_requires_review": (
                manifest_requires_review
            ),
        },
    }


def write_json(
    doc: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            doc,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
