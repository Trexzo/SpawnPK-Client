from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .lineage import validate_lineage
from .member_lineage import validate_member_lineage


class MemberRemapPlanError(ValueError):
    pass


_IDENTIFIER = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


def _build(class_lineage: dict[str, Any], build_id: str) -> dict[str, Any]:
    hits = [
        row
        for row in class_lineage.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(hits) != 1:
        raise MemberRemapPlanError(
            f"expected one canonical build {build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _entry_for_build(
    record: dict[str, Any],
    build_id: str,
) -> dict[str, Any]:
    hits = [
        row
        for row in record.get("lineage", [])
        if row.get("build_id") == build_id
    ]
    if len(hits) != 1:
        raise MemberRemapPlanError(
            f"{record.get('member_id')} has {len(hits)} entries "
            f"for build {build_id!r}"
        )
    return hits[0]


def _accepted_target_name(record: dict[str, Any]) -> str | None:
    if record.get("semantic_status") != "ACCEPTED":
        return None
    name = record.get("semantic_name")
    if not isinstance(name, str) or not _IDENTIFIER.fullmatch(name):
        raise MemberRemapPlanError(
            f"{record.get('member_id')}: accepted semantic name is invalid"
        )
    if name in {"<init>", "<clinit>"}:
        raise MemberRemapPlanError(
            f"{record.get('member_id')}: constructor names are reserved"
        )
    confidence = record.get("semantic_confidence")
    if (
        not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or not 0.0 <= float(confidence) <= 1.0
    ):
        raise MemberRemapPlanError(
            f"{record.get('member_id')}: accepted semantic confidence invalid"
        )
    provenance = record.get("semantic_provenance")
    if not isinstance(provenance, list) or not provenance:
        raise MemberRemapPlanError(
            f"{record.get('member_id')}: accepted semantic name lacks provenance"
        )
    return name


def _index_member_exists(
    index: dict[str, Any],
    *,
    owner: str,
    kind: str,
    name: str,
    descriptor: str,
) -> bool:
    cls = index.get("classes", {}).get(owner + ".class")
    if not isinstance(cls, dict):
        return False
    collection = "fields" if kind == "field" else "methods"
    return any(
        member.get("name") == name
        and member.get("descriptor") == descriptor
        for member in cls.get(collection, [])
    )


def build_member_remap_plan(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    index: dict[str, Any],
    *,
    build_id: str,
) -> dict[str, Any]:
    """Resolve ACCEPTED semantic member names for one exact client build."""
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )
    build = _build(class_lineage, build_id)
    source_sha = str(build.get("sha256", "")).lower()
    if str(index.get("sha256", "")).lower() != source_sha:
        raise MemberRemapPlanError(
            "member remap index SHA does not match canonical build"
        )

    rows: list[dict[str, Any]] = []
    for record in member_lineage.get("members", []):
        target_name = _accepted_target_name(record)
        if target_name is None:
            continue

        entry = _entry_for_build(record, build_id)
        kind = record["kind"]
        owner = entry["owner_internal_name"]
        source_name = entry["name"]
        descriptor = entry["descriptor"]

        if target_name == source_name:
            continue
        if not _index_member_exists(
            index,
            owner=owner,
            kind=kind,
            name=source_name,
            descriptor=descriptor,
        ):
            raise MemberRemapPlanError(
                f"{record['member_id']}: exact source coordinate "
                f"{owner}.{source_name}{descriptor} is absent from index"
            )

        rows.append(
            {
                "member_id": record["member_id"],
                "owner_logical_id": record["owner_logical_id"],
                "kind": kind,
                "owner_internal_name": owner,
                "source_name": source_name,
                "descriptor": descriptor,
                "target_name": target_name,
                "confidence": float(record["semantic_confidence"]),
                "provenance": record["semantic_provenance"],
            }
        )

    rows.sort(
        key=lambda row: (
            row["owner_internal_name"],
            row["kind"],
            row["source_name"],
            row["descriptor"],
            row["member_id"],
        )
    )

    mapping = {
        (
            row["kind"],
            row["owner_internal_name"],
            row["source_name"],
            row["descriptor"],
        ): row["target_name"]
        for row in rows
    }

    # Validate the complete final member namespace, including unmapped members.
    for class_path, cls in index.get("classes", {}).items():
        owner = cls.get("internal_name")
        if not isinstance(owner, str):
            continue

        final_fields: set[str] = set()
        for field in cls.get("fields", []):
            source_name = str(field.get("name", ""))
            descriptor = str(field.get("descriptor", ""))
            final_name = mapping.get(
                ("field", owner, source_name, descriptor),
                source_name,
            )
            if final_name in final_fields:
                raise MemberRemapPlanError(
                    f"field target collision in {owner}: {final_name!r}"
                )
            final_fields.add(final_name)

        final_methods: set[tuple[str, str]] = set()
        for method in cls.get("methods", []):
            source_name = str(method.get("name", ""))
            descriptor = str(method.get("descriptor", ""))
            if source_name in {"<init>", "<clinit>"}:
                final_name = source_name
            else:
                final_name = mapping.get(
                    ("method", owner, source_name, descriptor),
                    source_name,
                )
            signature = (final_name, descriptor)
            if signature in final_methods:
                raise MemberRemapPlanError(
                    f"method target collision in {owner}: "
                    f"{final_name}{descriptor}"
                )
            final_methods.add(signature)

    return {
        "schema_version": 1,
        "kind": "member_remap_plan",
        "build_id": build_id,
        "source_sha256": source_sha,
        "field_count": sum(1 for row in rows if row["kind"] == "field"),
        "method_count": sum(1 for row in rows if row["kind"] == "method"),
        "member_count": len(rows),
        "members": rows,
    }


def write_json(doc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
