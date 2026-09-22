from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

SCHEMA_VERSION = 1
NAMESPACE = "spawnpk-client"
LOGICAL_ID_RE = re.compile(r"^CLIENT_CLASS_(\d{6})$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_AUTHORITIES = {
    "EXACT_CURRENT_CLIENT",
    "EXACT_HISTORICAL_CLIENT",
    "CROSS_BUILD",
    "RESEARCH",
    "INFERENCE",
}
ALLOWED_RELATIONS = {
    "BASELINE",
    "EXACT_HASH",
    "STRUCTURAL",
    "SEMANTIC",
    "MANUAL",
}
ALLOWED_SEMANTIC_STATUS = {"UNKNOWN", "CANDIDATE", "ACCEPTED"}


class LineageValidationError(ValueError):
    pass


def _sha(value: str, *, label: str) -> str:
    value = value.lower()
    if not SHA256_RE.fullmatch(value):
        raise LineageValidationError(f"{label}: expected lowercase/uppercase 64-char SHA-256, got {value!r}")
    return value


def _confidence(value: Any, *, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise LineageValidationError(f"{label}: confidence must be numeric")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise LineageValidationError(f"{label}: confidence must be in [0, 1], got {value}")
    return value


def _baseline_records(index: dict[str, Any], prefix: str) -> list[tuple[str, dict[str, Any]]]:
    classes = index.get("classes")
    if not isinstance(classes, dict):
        raise LineageValidationError("index.classes must be an object")
    rows: list[tuple[str, dict[str, Any]]] = []
    for entry_path, record in classes.items():
        if prefix and not entry_path.startswith(prefix):
            continue
        internal_name = record.get("internal_name")
        if not isinstance(internal_name, str) or not internal_name:
            raise LineageValidationError(f"index class {entry_path!r} has no internal_name")
        rows.append((entry_path, record))
    rows.sort(key=lambda row: (row[1]["internal_name"], row[0]))
    return rows


def seed_lineage(
    index: dict[str, Any],
    *,
    build_id: str,
    build_number: int | None,
    authority: str,
    prefix: str = "rs/",
) -> dict[str, Any]:
    if not build_id or not isinstance(build_id, str):
        raise LineageValidationError("build_id must be a non-empty string")
    if authority not in ALLOWED_AUTHORITIES:
        raise LineageValidationError(f"unsupported authority {authority!r}")
    source_sha = _sha(str(index.get("sha256", "")), label="index.sha256")
    source_name = str(index.get("source_name", ""))
    records = _baseline_records(index, prefix)

    classes: list[dict[str, Any]] = []
    for ordinal, (entry_path, source) in enumerate(records, start=1):
        logical_id = f"CLIENT_CLASS_{ordinal:06d}"
        entry_sha = index.get("entries", {}).get(entry_path, {}).get("sha256")
        if not isinstance(entry_sha, str):
            raise LineageValidationError(f"index entry {entry_path!r} has no sha256")
        structural_sha = source.get("structural_sha256")
        if not isinstance(structural_sha, str):
            raise LineageValidationError(f"index class {entry_path!r} has no structural_sha256")
        classes.append(
            {
                "logical_id": logical_id,
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": build_id,
                        "internal_name": source["internal_name"],
                        "entry_path": entry_path,
                        "entry_sha256": _sha(entry_sha, label=f"{entry_path}.sha256"),
                        "structural_sha256": _sha(structural_sha, label=f"{entry_path}.structural_sha256"),
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [
                            {
                                "authority": authority,
                                "source": "baseline-seed",
                                "note": "Deterministic identity assigned from immutable baseline ordering.",
                            }
                        ],
                    }
                ],
                "semantic_provenance": [],
            }
        )

    doc = {
        "schema_version": SCHEMA_VERSION,
        "namespace": NAMESPACE,
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": build_id,
        "builds": [
            {
                "build_id": build_id,
                "build_number": build_number,
                "sha256": source_sha,
                "source_name": source_name,
                "authority": authority,
            }
        ],
        "classes": classes,
        "unresolved": [],
    }
    validate_lineage(doc)
    return doc


def validate_lineage(doc: dict[str, Any]) -> dict[str, int]:
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise LineageValidationError(f"schema_version must be {SCHEMA_VERSION}")
    if doc.get("namespace") != NAMESPACE:
        raise LineageValidationError(f"namespace must be {NAMESPACE!r}")
    if doc.get("id_format") != "CLIENT_CLASS_%06d":
        raise LineageValidationError("id_format must be CLIENT_CLASS_%06d")

    builds = doc.get("builds")
    if not isinstance(builds, list) or not builds:
        raise LineageValidationError("builds must be a non-empty array")
    build_ids: set[str] = set()
    for i, build in enumerate(builds):
        label = f"builds[{i}]"
        if not isinstance(build, dict):
            raise LineageValidationError(f"{label} must be an object")
        build_id = build.get("build_id")
        if not isinstance(build_id, str) or not build_id:
            raise LineageValidationError(f"{label}.build_id must be a non-empty string")
        if build_id in build_ids:
            raise LineageValidationError(f"duplicate build_id {build_id!r}")
        build_ids.add(build_id)
        _sha(str(build.get("sha256", "")), label=f"{label}.sha256")
        if build.get("authority") not in ALLOWED_AUTHORITIES:
            raise LineageValidationError(f"{label}.authority is unsupported")
        number = build.get("build_number")
        if number is not None and (not isinstance(number, int) or isinstance(number, bool)):
            raise LineageValidationError(f"{label}.build_number must be integer or null")

    baseline = doc.get("baseline_build_id")
    if baseline not in build_ids:
        raise LineageValidationError("baseline_build_id must reference a declared build")

    classes = doc.get("classes")
    if not isinstance(classes, list):
        raise LineageValidationError("classes must be an array")

    logical_ids: set[str] = set()
    build_names: set[tuple[str, str]] = set()
    build_paths: set[tuple[str, str]] = set()
    lineage_count = 0
    semantic_named = 0

    for i, record in enumerate(classes):
        label = f"classes[{i}]"
        if not isinstance(record, dict):
            raise LineageValidationError(f"{label} must be an object")
        logical_id = record.get("logical_id")
        if not isinstance(logical_id, str) or not LOGICAL_ID_RE.fullmatch(logical_id):
            raise LineageValidationError(f"{label}.logical_id is invalid")
        if logical_id in logical_ids:
            raise LineageValidationError(f"duplicate logical_id {logical_id}")
        logical_ids.add(logical_id)

        status = record.get("semantic_status")
        if status not in ALLOWED_SEMANTIC_STATUS:
            raise LineageValidationError(f"{label}.semantic_status is unsupported")
        semantic_name = record.get("semantic_name")
        if semantic_name is not None and (not isinstance(semantic_name, str) or not semantic_name.strip()):
            raise LineageValidationError(f"{label}.semantic_name must be null or non-empty string")
        semantic_conf = _confidence(record.get("semantic_confidence"), label=f"{label}.semantic_confidence")
        if status == "UNKNOWN" and semantic_name is not None:
            raise LineageValidationError(f"{label}: UNKNOWN semantic status cannot have semantic_name")
        if status in {"CANDIDATE", "ACCEPTED"} and semantic_name is None:
            raise LineageValidationError(f"{label}: {status} semantic status requires semantic_name")
        if semantic_name is None and semantic_conf != 0.0:
            raise LineageValidationError(f"{label}: unnamed semantic record must have confidence 0.0")
        if semantic_name is not None:
            semantic_named += 1

        lineage = record.get("lineage")
        if not isinstance(lineage, list) or not lineage:
            raise LineageValidationError(f"{label}.lineage must be a non-empty array")
        seen_builds_for_class: set[str] = set()
        for j, entry in enumerate(lineage):
            elabel = f"{label}.lineage[{j}]"
            if not isinstance(entry, dict):
                raise LineageValidationError(f"{elabel} must be an object")
            build_id = entry.get("build_id")
            if build_id not in build_ids:
                raise LineageValidationError(f"{elabel}.build_id references unknown build")
            if build_id in seen_builds_for_class:
                raise LineageValidationError(f"{label} contains two lineage entries for build {build_id!r}")
            seen_builds_for_class.add(build_id)
            internal_name = entry.get("internal_name")
            entry_path = entry.get("entry_path")
            if not isinstance(internal_name, str) or not internal_name:
                raise LineageValidationError(f"{elabel}.internal_name must be non-empty")
            if entry_path != internal_name + ".class":
                raise LineageValidationError(f"{elabel}.entry_path must equal internal_name + '.class'")
            key = (build_id, internal_name)
            if key in build_names:
                raise LineageValidationError(f"duplicate class identity in build {build_id}: {internal_name}")
            build_names.add(key)
            pkey = (build_id, entry_path)
            if pkey in build_paths:
                raise LineageValidationError(f"duplicate entry path in build {build_id}: {entry_path}")
            build_paths.add(pkey)
            _sha(str(entry.get("entry_sha256", "")), label=f"{elabel}.entry_sha256")
            _sha(str(entry.get("structural_sha256", "")), label=f"{elabel}.structural_sha256")
            if entry.get("relation") not in ALLOWED_RELATIONS:
                raise LineageValidationError(f"{elabel}.relation is unsupported")
            _confidence(entry.get("confidence"), label=f"{elabel}.confidence")
            provenance = entry.get("provenance")
            if not isinstance(provenance, list):
                raise LineageValidationError(f"{elabel}.provenance must be an array")
            for k, prov in enumerate(provenance):
                plabel = f"{elabel}.provenance[{k}]"
                if not isinstance(prov, dict):
                    raise LineageValidationError(f"{plabel} must be an object")
                if prov.get("authority") not in ALLOWED_AUTHORITIES:
                    raise LineageValidationError(f"{plabel}.authority is unsupported")
                if not isinstance(prov.get("source"), str) or not prov["source"]:
                    raise LineageValidationError(f"{plabel}.source must be non-empty")
            lineage_count += 1

        semantic_provenance = record.get("semantic_provenance")
        if not isinstance(semantic_provenance, list):
            raise LineageValidationError(f"{label}.semantic_provenance must be an array")

    unresolved = doc.get("unresolved")
    if not isinstance(unresolved, list):
        raise LineageValidationError("unresolved must be an array")

    return {
        "builds": len(builds),
        "logical_classes": len(classes),
        "lineage_entries": lineage_count,
        "semantic_named": semantic_named,
        "unresolved": len(unresolved),
    }


def write_lineage(doc: dict[str, Any], out: Path) -> None:
    validate_lineage(doc)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def load_lineage(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise LineageValidationError("lineage document root must be an object")
    return doc
