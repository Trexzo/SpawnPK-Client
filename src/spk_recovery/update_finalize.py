from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .lineage import LineageValidationError, validate_lineage
from .member_lineage import (
    MemberLineageError,
    validate_member_lineage,
)


class UpdateFinalizeError(MemberLineageError):
    pass


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _build(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, Any]:
    hits = [
        row
        for row in class_lineage.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(hits) != 1:
        raise UpdateFinalizeError(
            f"expected one canonical build {build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _target_class_paths(
    class_lineage: dict[str, Any],
    build_id: str,
    prefix: str,
) -> tuple[set[str], int]:
    paths: set[str] = set()
    accepted = 0
    for record in class_lineage.get("classes", []):
        target_entries = [
            entry
            for entry in record.get("lineage", [])
            if entry.get("build_id") == build_id
        ]
        if not target_entries:
            continue
        if len(target_entries) != 1:
            raise UpdateFinalizeError(
                f"logical class {record.get('logical_id')} has multiple "
                f"entries for {build_id!r}"
            )
        path = target_entries[0].get("entry_path")
        if not isinstance(path, str):
            raise UpdateFinalizeError(
                "canonical target class entry path must be a string"
            )
        if prefix and not path.startswith(prefix):
            continue
        paths.add(path)
        if record.get("semantic_status") == "ACCEPTED":
            accepted += 1
    return paths, accepted


def _expected_member_coords(
    index: dict[str, Any],
    *,
    class_paths: set[str],
) -> tuple[
    set[tuple[str, str, str, str]],
    int,
    int,
]:
    coords: set[tuple[str, str, str, str]] = set()
    fields = 0
    methods = 0

    for path in sorted(class_paths):
        cls = index.get("classes", {}).get(path)
        if not isinstance(cls, dict):
            raise UpdateFinalizeError(
                f"exact target index missing class {path!r}"
            )
        owner = cls.get("internal_name")
        if not isinstance(owner, str) or path != owner + ".class":
            raise UpdateFinalizeError(
                f"target class internal-name/path mismatch at {path!r}"
            )

        for member in cls.get("fields", []):
            coord = (
                owner,
                "field",
                str(member.get("name", "")),
                str(member.get("descriptor", "")),
            )
            coords.add(coord)
            fields += 1

        for member in cls.get("methods", []):
            name = str(member.get("name", ""))
            if name in {"<init>", "<clinit>"}:
                continue
            coord = (
                owner,
                "method",
                name,
                str(member.get("descriptor", "")),
            )
            coords.add(coord)
            methods += 1

    return coords, fields, methods


def _canonical_member_coords(
    member_lineage: dict[str, Any],
    *,
    build_id: str,
    prefix: str,
) -> tuple[
    set[tuple[str, str, str, str]],
    int,
    int,
    int,
]:
    coords: set[tuple[str, str, str, str]] = set()
    fields = 0
    methods = 0
    accepted = 0

    for record in member_lineage.get("members", []):
        entries = [
            entry
            for entry in record.get("lineage", [])
            if entry.get("build_id") == build_id
        ]
        if not entries:
            continue
        if len(entries) != 1:
            raise UpdateFinalizeError(
                f"member {record.get('member_id')} has multiple "
                f"entries for {build_id!r}"
            )
        entry = entries[0]
        owner = entry.get("owner_internal_name")
        if not isinstance(owner, str):
            raise UpdateFinalizeError(
                "canonical target member owner must be a string"
            )
        if prefix and not (owner + ".class").startswith(prefix):
            continue

        kind = record.get("kind")
        coord = (
            owner,
            str(kind),
            str(entry.get("name", "")),
            str(entry.get("descriptor", "")),
        )
        coords.add(coord)
        if kind == "field":
            fields += 1
        elif kind == "method":
            methods += 1
        else:
            raise UpdateFinalizeError(
                f"unsupported canonical member kind {kind!r}"
            )
        if record.get("semantic_status") == "ACCEPTED":
            accepted += 1

    return coords, fields, methods, accepted


def _relevant_unresolved(
    items: Any,
    *,
    build_id: str,
    informational_kinds: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(items, list):
        raise UpdateFinalizeError("unresolved must be an array")

    blockers: list[dict[str, Any]] = []
    informational: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("new_build_id") != build_id:
            continue
        target = (
            informational
            if item.get("kind") in informational_kinds
            else blockers
        )
        target.append(item)

    def key(row: dict[str, Any]) -> str:
        return json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    blockers.sort(key=key)
    informational.sort(key=key)
    return blockers, informational


def build_authority_candidate_report(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    target_index: dict[str, Any],
    intake_report: dict[str, Any],
    *,
    build_id: str,
    scope_prefix: str | None = None,
) -> dict[str, Any]:
    """Prove target-side canonical coverage before authority promotion."""
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    if (
        intake_report.get("schema_version") != 1
        or intake_report.get("kind") != "update_intake_report"
    ):
        raise UpdateFinalizeError(
            "unsupported update intake report schema/kind"
        )
    if intake_report.get("new_build_id") != build_id:
        raise UpdateFinalizeError(
            "intake report new_build_id does not match finalization build"
        )

    build = _build(class_lineage, build_id)
    target_sha = str(target_index.get("sha256", "")).lower()
    canonical_sha = str(build.get("sha256", "")).lower()
    intake_sha = str(intake_report.get("new_sha256", "")).lower()
    if target_sha != canonical_sha or target_sha != intake_sha:
        raise UpdateFinalizeError(
            "target index, canonical build and intake report SHA-256 "
            "must all match exactly"
        )

    prefix = (
        scope_prefix
        if scope_prefix is not None
        else str(intake_report.get("scope_prefix", "rs/"))
    )
    if not isinstance(prefix, str):
        raise UpdateFinalizeError("scope_prefix must be a string")

    parse_errors = int(
        target_index.get("summary", {}).get(
            "class_parse_error_count",
            0,
        )
    )

    expected_classes = {
        path
        for path in target_index.get("classes", {})
        if not prefix or path.startswith(prefix)
    }
    canonical_classes, accepted_classes = _target_class_paths(
        class_lineage,
        build_id,
        prefix,
    )
    missing_classes = sorted(
        expected_classes - canonical_classes
    )
    stale_classes = sorted(
        canonical_classes - expected_classes
    )

    expected_members, expected_fields, expected_methods = (
        _expected_member_coords(
            target_index,
            class_paths=expected_classes,
        )
    )
    (
        canonical_members,
        canonical_fields,
        canonical_methods,
        accepted_members,
    ) = _canonical_member_coords(
        member_lineage,
        build_id=build_id,
        prefix=prefix,
    )
    missing_members = sorted(
        expected_members - canonical_members
    )
    stale_members = sorted(
        canonical_members - expected_members
    )

    class_blockers, class_info = _relevant_unresolved(
        class_lineage.get("unresolved", []),
        build_id=build_id,
        informational_kinds={"unmatched_old"},
    )
    member_blockers, member_info = _relevant_unresolved(
        member_lineage.get("unresolved", []),
        build_id=build_id,
        informational_kinds={"member_unmatched_old"},
    )

    blockers: list[dict[str, Any]] = []
    if parse_errors:
        blockers.append(
            {
                "kind": "class_parse_errors",
                "count": parse_errors,
            }
        )
    if missing_classes:
        blockers.append(
            {
                "kind": "missing_canonical_classes",
                "count": len(missing_classes),
            }
        )
    if stale_classes:
        blockers.append(
            {
                "kind": "stale_canonical_classes",
                "count": len(stale_classes),
            }
        )
    if missing_members:
        blockers.append(
            {
                "kind": "missing_canonical_members",
                "count": len(missing_members),
            }
        )
    if stale_members:
        blockers.append(
            {
                "kind": "stale_canonical_members",
                "count": len(stale_members),
            }
        )
    if class_blockers:
        blockers.append(
            {
                "kind": "class_unresolved_blockers",
                "count": len(class_blockers),
            }
        )
    if member_blockers:
        blockers.append(
            {
                "kind": "member_unresolved_blockers",
                "count": len(member_blockers),
            }
        )

    class_coverage = (
        round(
            len(canonical_classes & expected_classes)
            / len(expected_classes)
            * 100.0,
            4,
        )
        if expected_classes
        else 100.0
    )
    member_coverage = (
        round(
            len(canonical_members & expected_members)
            / len(expected_members)
            * 100.0,
            4,
        )
        if expected_members
        else 100.0
    )

    summary = {
        "target_classes": len(expected_classes),
        "canonical_target_classes": len(
            canonical_classes & expected_classes
        ),
        "class_coverage_percent": class_coverage,
        "target_fields": expected_fields,
        "canonical_target_fields": canonical_fields,
        "target_methods": expected_methods,
        "canonical_target_methods": canonical_methods,
        "target_members": len(expected_members),
        "canonical_target_members": len(
            canonical_members & expected_members
        ),
        "member_coverage_percent": member_coverage,
        "accepted_semantic_classes_carried": accepted_classes,
        "accepted_semantic_members_carried": accepted_members,
        "class_parse_errors": parse_errors,
        "blocking_unresolved_classes": len(class_blockers),
        "blocking_unresolved_members": len(member_blockers),
        "informational_removed_class_items": len(class_info),
        "informational_removed_member_items": len(member_info),
        "blocker_count": len(blockers),
    }

    report_material = {
        "migration_id": intake_report.get("migration_id"),
        "build_id": build_id,
        "target_sha256": target_sha,
        "scope_prefix": prefix,
        "summary": summary,
        "missing_classes": missing_classes,
        "stale_classes": stale_classes,
        "missing_members": missing_members,
        "stale_members": stale_members,
        "class_blockers": class_blockers,
        "member_blockers": member_blockers,
    }
    report_id = (
        "AUTHCAND_"
        + hashlib.sha256(
            _stable_json(report_material)
        ).hexdigest()[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "authority_candidate_report",
        "report_id": report_id,
        "migration_id": intake_report.get("migration_id"),
        "build_id": build_id,
        "target_sha256": target_sha,
        "scope_prefix": prefix,
        "ready_for_authority": len(blockers) == 0,
        "summary": summary,
        "blockers": blockers,
        "missing_classes": missing_classes,
        "stale_classes": stale_classes,
        "missing_members": [
            {
                "owner": row[0],
                "kind": row[1],
                "name": row[2],
                "descriptor": row[3],
            }
            for row in missing_members
        ],
        "stale_members": [
            {
                "owner": row[0],
                "kind": row[1],
                "name": row[2],
                "descriptor": row[3],
            }
            for row in stale_members
        ],
        "blocking_class_unresolved": class_blockers,
        "blocking_member_unresolved": member_blockers,
        "informational_class_removals": class_info,
        "informational_member_removals": member_info,
    }


def write_authority_candidate_report(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
