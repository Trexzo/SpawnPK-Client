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

_JAVA_RESERVED_IDENTIFIERS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch",
    "char", "class", "const", "continue", "default", "do", "double",
    "else", "enum", "extends", "final", "finally", "float", "for",
    "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private",
    "protected", "public", "return", "short", "static", "strictfp",
    "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "_",
    "true", "false", "null",
}


def _is_java_source_identifier(name: str) -> bool:
    return bool(_IDENTIFIER.fullmatch(name)) and name not in _JAVA_RESERVED_IDENTIFIERS


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
    if not isinstance(name, str) or not _is_java_source_identifier(name):
        raise MemberRemapPlanError(
            f"{record.get('member_id')}: accepted semantic name is not a legal Java source identifier"
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
    source_safe_member_fallback: bool = False,
    member_fallback_name_prefix: str = "Recovered_",
) -> dict[str, Any]:
    """Resolve ACCEPTED semantics plus optional non-semantic source-safety member names."""
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

    if (
        not isinstance(member_fallback_name_prefix, str)
        or not member_fallback_name_prefix
        or not _is_java_source_identifier(member_fallback_name_prefix + "X")
    ):
        raise MemberRemapPlanError(
            f"invalid member fallback name prefix {member_fallback_name_prefix!r}"
        )

    rows: list[dict[str, Any]] = []
    for record in member_lineage.get("members", []):
        entry = _entry_for_build(record, build_id)
        target_name = _accepted_target_name(record)
        source_name = entry["name"]
        provenance: list[dict[str, Any]] | None = None
        confidence: float | None = None

        if target_name is not None:
            provenance = record["semantic_provenance"]
            confidence = float(record["semantic_confidence"])
        elif source_safe_member_fallback and not _is_java_source_identifier(source_name):
            target_name = member_fallback_name_prefix + str(record["member_id"])
            if not _is_java_source_identifier(target_name):
                raise MemberRemapPlanError(
                    f"{record.get('member_id')}: generated member fallback is not Java-source safe"
                )
            provenance = [
                {
                    "kind": "source_safety",
                    "reason": "java_reserved_member_name",
                    "strategy": "stable_member_id_rename",
                    "source_name": source_name,
                }
            ]
            confidence = 1.0
        else:
            continue

        kind = record["kind"]
        owner = entry["owner_internal_name"]
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
                "confidence": confidence,
                "provenance": provenance,
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
