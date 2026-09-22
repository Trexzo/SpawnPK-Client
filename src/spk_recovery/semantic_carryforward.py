from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .lineage import validate_lineage
from .member_lineage import validate_member_lineage
from .semantic_namespace import build_semantic_namespace, SemanticNamespaceError


class SemanticCarryForwardError(ValueError):
    pass


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_stable_json(value)).hexdigest()


def _validate_authority(
    snapshot: dict[str, Any],
    *,
    label: str,
) -> None:
    if (
        snapshot.get("schema_version") != 1
        or snapshot.get("kind") != "authority_snapshot"
    ):
        raise SemanticCarryForwardError(
            f"{label}: unsupported authority snapshot"
        )
    if snapshot.get("state") != "EXACT_CURRENT_CLIENT":
        raise SemanticCarryForwardError(
            f"{label}: authority state is not EXACT_CURRENT_CLIENT"
        )


def _has_build(
    record: dict[str, Any],
    build_id: str,
) -> bool:
    return any(
        row.get("build_id") == build_id
        for row in record.get("lineage", [])
    )


def _accepted_partition(
    records: list[dict[str, Any]],
    *,
    old_build_id: str,
    new_build_id: str,
    id_key: str,
) -> dict[str, list[str]]:
    carried: list[str] = []
    old_only: list[str] = []
    new_only: list[str] = []

    for record in records:
        if record.get("semantic_status") != "ACCEPTED":
            continue
        identifier = str(record.get(id_key))
        old = _has_build(record, old_build_id)
        new = _has_build(record, new_build_id)
        if old and new:
            carried.append(identifier)
        elif old:
            old_only.append(identifier)
        elif new:
            new_only.append(identifier)

    return {
        "carried": sorted(carried),
        "blocked_missing_new_identity": sorted(old_only),
        "available_new_only": sorted(new_only),
    }


def build_semantic_carryforward(
    previous_authority: dict[str, Any],
    new_authority: dict[str, Any],
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    new_index: dict[str, Any],
    *,
    target_package: str = "recovered/spawnpk/client",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Prove which ACCEPTED semantic names survive into one promoted authority.

    Semantic names are not copied or mutated here. R3 already transfers canonical
    identity relations. R4E only proves whether each accepted record has both the
    previous and new build identity needed for safe carry-forward.
    """
    _validate_authority(previous_authority, label="previous_authority")
    _validate_authority(new_authority, label="new_authority")
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    old_build_id = str(previous_authority.get("build_id", ""))
    new_build_id = str(new_authority.get("build_id", ""))
    if not old_build_id or not new_build_id:
        raise SemanticCarryForwardError(
            "authority snapshots must declare build_id"
        )
    if old_build_id == new_build_id:
        raise SemanticCarryForwardError(
            "previous and new authority build IDs must differ"
        )

    class_sha = _sha256_json(class_lineage)
    member_sha = _sha256_json(member_lineage)
    if (
        str(new_authority.get("class_lineage_sha256", "")).lower()
        != class_sha
    ):
        raise SemanticCarryForwardError(
            "new authority class lineage digest does not match supplied lineage"
        )
    if (
        str(new_authority.get("member_lineage_sha256", "")).lower()
        != member_sha
    ):
        raise SemanticCarryForwardError(
            "new authority member lineage digest does not match supplied lineage"
        )

    new_sha = str(new_authority.get("sha256", "")).lower()
    if str(new_index.get("sha256", "")).lower() != new_sha:
        raise SemanticCarryForwardError(
            "new exact index SHA-256 does not match new authority"
        )

    classes = _accepted_partition(
        list(class_lineage.get("classes", [])),
        old_build_id=old_build_id,
        new_build_id=new_build_id,
        id_key="logical_id",
    )
    fields = _accepted_partition(
        [
            row
            for row in member_lineage.get("members", [])
            if row.get("kind") == "field"
        ],
        old_build_id=old_build_id,
        new_build_id=new_build_id,
        id_key="member_id",
    )
    methods = _accepted_partition(
        [
            row
            for row in member_lineage.get("members", [])
            if row.get("kind") == "method"
        ],
        old_build_id=old_build_id,
        new_build_id=new_build_id,
        id_key="member_id",
    )

    try:
        namespace, class_plan, member_plan = build_semantic_namespace(
            class_lineage,
            member_lineage,
            new_index,
            build_id=new_build_id,
            target_package=target_package,
        )
    except SemanticNamespaceError as exc:
        raise SemanticCarryForwardError(str(exc)) from exc

    blockers = (
        len(classes["blocked_missing_new_identity"])
        + len(fields["blocked_missing_new_identity"])
        + len(methods["blocked_missing_new_identity"])
    )
    carried = (
        len(classes["carried"])
        + len(fields["carried"])
        + len(methods["carried"])
    )

    material = {
        "previous_authority_id": previous_authority["authority_id"],
        "new_authority_id": new_authority["authority_id"],
        "namespace_id": namespace["namespace_id"],
        "carried": carried,
        "blockers": blockers,
    }
    report_id = (
        "SEMCARRY_"
        + hashlib.sha256(_stable_json(material)).hexdigest()[:20].upper()
    )

    report = {
        "schema_version": 1,
        "kind": "semantic_carryforward_report",
        "report_id": report_id,
        "previous_authority_id": previous_authority["authority_id"],
        "new_authority_id": new_authority["authority_id"],
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": str(previous_authority.get("sha256", "")).lower(),
        "new_sha256": new_sha,
        "namespace_id": namespace["namespace_id"],
        "target_package": namespace["target_package"],
        "ready_for_readable_build": blockers == 0,
        "summary": {
            "accepted_carried": carried,
            "accepted_blocked_missing_new_identity": blockers,
            "classes_carried": len(classes["carried"]),
            "fields_carried": len(fields["carried"]),
            "methods_carried": len(methods["carried"]),
            "classes_new_only": len(classes["available_new_only"]),
            "fields_new_only": len(fields["available_new_only"]),
            "methods_new_only": len(methods["available_new_only"]),
        },
        "classes": classes,
        "fields": fields,
        "methods": methods,
    }
    return report, namespace, class_plan, member_plan


def write_json(doc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
