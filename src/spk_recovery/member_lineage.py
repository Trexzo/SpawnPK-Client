from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .lineage import LineageValidationError, validate_lineage

MEMBER_SCHEMA_VERSION = 1
MEMBER_KIND = "member_lineage"
FIELD_ID_RE = re.compile(r"^CLIENT_FIELD_(\d{6})$")
METHOD_ID_RE = re.compile(r"^CLIENT_METHOD_(\d{6})$")
ALLOWED_RELATIONS = {"BASELINE", "EXACT_HASH", "STRUCTURAL", "SEMANTIC", "MANUAL"}


class MemberLineageError(LineageValidationError):
    pass


def _class_build(lineage: dict[str, Any], build_id: str) -> dict[str, Any]:
    hits = [b for b in lineage.get("builds", []) if b.get("build_id") == build_id]
    if len(hits) != 1:
        raise MemberLineageError(
            f"expected exactly one class-lineage build {build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _owners(lineage: dict[str, Any], build_id: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for record in lineage.get("classes", []):
        logical_id = record["logical_id"]
        for entry in record.get("lineage", []):
            if entry.get("build_id") != build_id:
                continue
            internal = entry.get("internal_name")
            if internal in out:
                raise MemberLineageError(
                    f"duplicate class owner {internal!r} in build {build_id!r}"
                )
            out[internal] = logical_id
    return out


def _source_members(index: dict[str, Any], owners: dict[str, str]) -> tuple[list[tuple], list[tuple]]:
    fields: list[tuple] = []
    methods: list[tuple] = []
    classes = index.get("classes", {})

    for owner_internal, owner_logical_id in owners.items():
        path = owner_internal + ".class"
        cls = classes.get(path)
        if not isinstance(cls, dict):
            raise MemberLineageError(f"exact index missing class {path!r}")

        for member in cls.get("fields", []):
            fields.append(
                (
                    owner_logical_id,
                    owner_internal,
                    str(member.get("name", "")),
                    str(member.get("descriptor", "")),
                    int(member.get("access", 0)),
                )
            )

        for member in cls.get("methods", []):
            name = str(member.get("name", ""))
            if name in {"<init>", "<clinit>"}:
                continue
            methods.append(
                (
                    owner_logical_id,
                    owner_internal,
                    name,
                    str(member.get("descriptor", "")),
                    int(member.get("access", 0)),
                    member.get("code_length"),
                )
            )

    fields.sort(key=lambda row: (row[0], row[2], row[3], row[1]))
    methods.sort(key=lambda row: (row[0], row[2], row[3], row[1]))
    return fields, methods


def seed_member_lineage(
    class_lineage: dict[str, Any],
    index: dict[str, Any],
    *,
    build_id: str,
) -> dict[str, Any]:
    validate_lineage(class_lineage)
    build = _class_build(class_lineage, build_id)

    if str(index.get("sha256", "")).lower() != str(build.get("sha256", "")).lower():
        raise MemberLineageError(
            "member baseline index SHA-256 does not match canonical class-lineage build"
        )

    owners = _owners(class_lineage, build_id)
    fields, methods = _source_members(index, owners)
    records: list[dict[str, Any]] = []

    for ordinal, row in enumerate(fields, start=1):
        owner_id, owner, name, desc, access = row
        records.append(
            {
                "member_id": f"CLIENT_FIELD_{ordinal:06d}",
                "owner_logical_id": owner_id,
                "kind": "field",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": build_id,
                        "owner_internal_name": owner,
                        "name": name,
                        "descriptor": desc,
                        "access": access,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [
                            {
                                "authority": build["authority"],
                                "source": "member-baseline-seed",
                                "note": "Deterministic member identity assigned from exact baseline ordering.",
                            }
                        ],
                    }
                ],
                "semantic_provenance": [],
            }
        )

    for ordinal, row in enumerate(methods, start=1):
        owner_id, owner, name, desc, access, code_length = row
        records.append(
            {
                "member_id": f"CLIENT_METHOD_{ordinal:06d}",
                "owner_logical_id": owner_id,
                "kind": "method",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": build_id,
                        "owner_internal_name": owner,
                        "name": name,
                        "descriptor": desc,
                        "access": access,
                        "code_length": code_length,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [
                            {
                                "authority": build["authority"],
                                "source": "member-baseline-seed",
                                "note": "Deterministic member identity assigned from exact baseline ordering.",
                            }
                        ],
                    }
                ],
                "semantic_provenance": [],
            }
        )

    doc = {
        "schema_version": MEMBER_SCHEMA_VERSION,
        "kind": MEMBER_KIND,
        "class_namespace": class_lineage["namespace"],
        "baseline_build_id": build_id,
        "source_sha256": str(build["sha256"]).lower(),
        "members": records,
        "unresolved": [],
    }
    validate_member_lineage(doc, class_lineage=class_lineage)
    return doc


def validate_member_lineage(
    doc: dict[str, Any],
    *,
    class_lineage: dict[str, Any] | None = None,
) -> dict[str, int]:
    if doc.get("schema_version") != MEMBER_SCHEMA_VERSION:
        raise MemberLineageError(f"schema_version must be {MEMBER_SCHEMA_VERSION}")
    if doc.get("kind") != MEMBER_KIND:
        raise MemberLineageError(f"kind must be {MEMBER_KIND!r}")

    known_classes: set[str] | None = None
    known_builds: set[str] | None = None
    if class_lineage is not None:
        validate_lineage(class_lineage)
        known_classes = {r["logical_id"] for r in class_lineage.get("classes", [])}
        known_builds = {b["build_id"] for b in class_lineage.get("builds", [])}
        baseline = _class_build(class_lineage, doc.get("baseline_build_id"))
        if str(doc.get("source_sha256", "")).lower() != str(baseline["sha256"]).lower():
            raise MemberLineageError(
                "member lineage source SHA-256 does not match class-lineage baseline"
            )

    members = doc.get("members")
    if not isinstance(members, list):
        raise MemberLineageError("members must be an array")

    ids: set[str] = set()
    coordinates: set[tuple[str, str, str, str, str]] = set()
    field_count = 0
    method_count = 0
    lineage_entries = 0

    for i, record in enumerate(members):
        label = f"members[{i}]"
        if not isinstance(record, dict):
            raise MemberLineageError(f"{label} must be an object")

        kind = record.get("kind")
        member_id = record.get("member_id")
        pattern = FIELD_ID_RE if kind == "field" else METHOD_ID_RE if kind == "method" else None
        if pattern is None or not isinstance(member_id, str) or not pattern.fullmatch(member_id):
            raise MemberLineageError(f"{label}: invalid member kind/id")
        if member_id in ids:
            raise MemberLineageError(f"duplicate member_id {member_id}")
        ids.add(member_id)

        owner_id = record.get("owner_logical_id")
        if known_classes is not None and owner_id not in known_classes:
            raise MemberLineageError(f"{label}: unknown owner logical class {owner_id!r}")

        semantic_name = record.get("semantic_name")
        status = record.get("semantic_status")
        confidence = record.get("semantic_confidence")
        if status not in {"UNKNOWN", "CANDIDATE", "ACCEPTED"}:
            raise MemberLineageError(f"{label}: unsupported semantic_status")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise MemberLineageError(f"{label}: semantic_confidence must be numeric")
        confidence = float(confidence)
        if not 0.0 <= confidence <= 1.0:
            raise MemberLineageError(f"{label}: semantic_confidence outside [0,1]")
        if status == "UNKNOWN" and semantic_name is not None:
            raise MemberLineageError(f"{label}: UNKNOWN cannot have semantic_name")
        if status != "UNKNOWN" and (not isinstance(semantic_name, str) or not semantic_name):
            raise MemberLineageError(f"{label}: named semantic status requires semantic_name")
        if semantic_name is None and confidence != 0.0:
            raise MemberLineageError(f"{label}: unnamed semantic record must have 0 confidence")

        lineage = record.get("lineage")
        if not isinstance(lineage, list) or not lineage:
            raise MemberLineageError(f"{label}.lineage must be non-empty")
        seen_builds: set[str] = set()
        for j, entry in enumerate(lineage):
            elabel = f"{label}.lineage[{j}]"
            build_id = entry.get("build_id")
            if known_builds is not None and build_id not in known_builds:
                raise MemberLineageError(f"{elabel}: unknown build {build_id!r}")
            if build_id in seen_builds:
                raise MemberLineageError(f"{label}: duplicate build relation {build_id!r}")
            seen_builds.add(build_id)

            owner = entry.get("owner_internal_name")
            name = entry.get("name")
            desc = entry.get("descriptor")
            if not all(isinstance(x, str) and x for x in (owner, name, desc)):
                raise MemberLineageError(f"{elabel}: owner/name/descriptor must be non-empty strings")
            if kind == "method" and name in {"<init>", "<clinit>"}:
                raise MemberLineageError(f"{elabel}: constructors are not canonical renamable members")
            relation = entry.get("relation")
            if relation not in ALLOWED_RELATIONS:
                raise MemberLineageError(f"{elabel}: unsupported relation")
            rel_conf = entry.get("confidence")
            if not isinstance(rel_conf, (int, float)) or isinstance(rel_conf, bool):
                raise MemberLineageError(f"{elabel}: confidence must be numeric")
            if not 0.0 <= float(rel_conf) <= 1.0:
                raise MemberLineageError(f"{elabel}: confidence outside [0,1]")
            provenance = entry.get("provenance")
            if not isinstance(provenance, list):
                raise MemberLineageError(f"{elabel}.provenance must be an array")

            coord = (build_id, owner, kind, name, desc)
            if coord in coordinates:
                raise MemberLineageError(f"duplicate build member coordinate {coord!r}")
            coordinates.add(coord)
            lineage_entries += 1

        if not isinstance(record.get("semantic_provenance"), list):
            raise MemberLineageError(f"{label}.semantic_provenance must be an array")

        if kind == "field":
            field_count += 1
        else:
            method_count += 1

    if not isinstance(doc.get("unresolved"), list):
        raise MemberLineageError("unresolved must be an array")

    return {
        "members": len(members),
        "fields": field_count,
        "methods": method_count,
        "lineage_entries": lineage_entries,
        "unresolved": len(doc["unresolved"]),
    }


def write_member_lineage(doc: dict[str, Any], out: Path) -> None:
    validate_member_lineage(doc)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_member_lineage(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise MemberLineageError("member lineage root must be an object")
    return doc
