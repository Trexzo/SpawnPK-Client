from __future__ import annotations

import copy
from typing import Any

from .lineage import validate_lineage
from .member_lineage import (
    MemberLineageError,
    validate_member_lineage,
)


class ReviewedMemberIdentityError(MemberLineageError):
    pass


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
        raise ReviewedMemberIdentityError(
            f"expected one canonical build {build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _owner_map(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for record in class_lineage.get("classes", []):
        logical_id = record.get("logical_id")
        for entry in record.get("lineage", []):
            if entry.get("build_id") != build_id:
                continue
            internal = entry.get("internal_name")
            if (
                not isinstance(logical_id, str)
                or not isinstance(internal, str)
                or not internal
            ):
                raise ReviewedMemberIdentityError(
                    f"invalid canonical owner in build {build_id!r}"
                )
            if internal in out:
                raise ReviewedMemberIdentityError(
                    f"duplicate canonical owner {internal!r} in {build_id!r}"
                )
            out[internal] = logical_id
    return out


def _coord(value: Any, *, label: str) -> tuple[str, str, int | None]:
    if not isinstance(value, dict):
        raise ReviewedMemberIdentityError(
            f"{label} must be an object"
        )
    name = value.get("name")
    descriptor = value.get("descriptor")
    access = value.get("access")
    if not isinstance(name, str) or not name:
        raise ReviewedMemberIdentityError(
            f"{label}.name must be non-empty"
        )
    if not isinstance(descriptor, str) or not descriptor:
        raise ReviewedMemberIdentityError(
            f"{label}.descriptor must be non-empty"
        )
    if access is not None and (
        not isinstance(access, int) or isinstance(access, bool)
    ):
        raise ReviewedMemberIdentityError(
            f"{label}.access must be an integer when present"
        )
    return name, descriptor, access


def _exact_field(
    index: dict[str, Any],
    *,
    owner: str,
    name: str,
    descriptor: str,
) -> dict[str, Any]:
    cls = index.get("classes", {}).get(owner + ".class")
    if not isinstance(cls, dict):
        raise ReviewedMemberIdentityError(
            f"exact index missing owner {owner!r}"
        )
    hits = [
        row
        for row in cls.get("fields", [])
        if row.get("name") == name
        and row.get("descriptor") == descriptor
    ]
    if len(hits) != 1:
        raise ReviewedMemberIdentityError(
            f"expected one exact field {owner}.{name}:{descriptor}, "
            f"found {len(hits)}"
        )
    return hits[0]


def _old_field_map(
    member_lineage: dict[str, Any],
    build_id: str,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    out: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in member_lineage.get("members", []):
        if record.get("kind") != "field":
            continue
        for entry in record.get("lineage", []):
            if entry.get("build_id") != build_id:
                continue
            key = (
                str(entry.get("owner_internal_name")),
                str(entry.get("name")),
                str(entry.get("descriptor")),
            )
            if key in out:
                raise ReviewedMemberIdentityError(
                    f"duplicate canonical old field coordinate {key!r}"
                )
            out[key] = record
    return out


def _target_field_owners(
    member_lineage: dict[str, Any],
    build_id: str,
) -> dict[tuple[str, str, str], str]:
    out: dict[tuple[str, str, str], str] = {}
    for record in member_lineage.get("members", []):
        member_id = str(record.get("member_id"))
        for entry in record.get("lineage", []):
            if entry.get("build_id") != build_id:
                continue
            if record.get("kind") != "field":
                continue
            key = (
                str(entry.get("owner_internal_name")),
                str(entry.get("name")),
                str(entry.get("descriptor")),
            )
            prior = out.get(key)
            if prior is not None and prior != member_id:
                raise ReviewedMemberIdentityError(
                    f"duplicate canonical target field coordinate {key!r}"
                )
            out[key] = member_id
    return out


def _review_rows(
    member_lineage: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in member_lineage.get("unresolved", []):
        if not isinstance(item, dict):
            continue
        if (
            item.get("kind") != "member_identity_review"
            or item.get("member_kind") != "field"
            or item.get("source") != "member_identity_candidates"
            or item.get("old_build_id") != old_build_id
            or item.get("new_build_id") != new_build_id
        ):
            continue
        candidate = item.get("candidate")
        if not isinstance(candidate, dict):
            continue
        relationship_id = candidate.get("relationship_id")
        if not isinstance(relationship_id, str) or not relationship_id:
            continue
        if relationship_id in out:
            raise ReviewedMemberIdentityError(
                f"duplicate unresolved relationship_id {relationship_id!r}"
            )
        out[relationship_id] = item
    return out


def accept_reviewed_member_identities(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    spec: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    """Accept explicitly reviewed existing field identities.

    The acceptance document names only existing unresolved relationship IDs.
    Candidate coordinates remain owned by the migration output and are
    independently re-verified against exact indexes and canonical lineage.
    """
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    if (
        spec.get("schema_version") != 1
        or spec.get("kind")
        != "reviewed_member_identity_acceptance_spec"
    ):
        raise ReviewedMemberIdentityError(
            "unsupported reviewed-member acceptance spec"
        )

    old_build_id = spec.get("old_build_id")
    new_build_id = spec.get("new_build_id")
    if (
        not isinstance(old_build_id, str)
        or not old_build_id
        or not isinstance(new_build_id, str)
        or not new_build_id
        or old_build_id == new_build_id
    ):
        raise ReviewedMemberIdentityError(
            "old/new build IDs must be distinct non-empty strings"
        )

    old_build = _build(class_lineage, old_build_id)
    new_build = _build(class_lineage, new_build_id)
    old_sha = str(old_index.get("sha256", "")).lower()
    new_sha = str(new_index.get("sha256", "")).lower()
    if old_sha != str(old_build.get("sha256", "")).lower():
        raise ReviewedMemberIdentityError(
            "old index SHA does not match canonical old build"
        )
    if new_sha != str(new_build.get("sha256", "")).lower():
        raise ReviewedMemberIdentityError(
            "new index SHA does not match canonical new build"
        )
    if str(spec.get("old_sha256", "")).lower() != old_sha:
        raise ReviewedMemberIdentityError(
            "acceptance old SHA does not match exact old index"
        )
    if str(spec.get("new_sha256", "")).lower() != new_sha:
        raise ReviewedMemberIdentityError(
            "acceptance new SHA does not match exact new index"
        )

    note = spec.get("note")
    if not isinstance(note, str) or not note.strip():
        raise ReviewedMemberIdentityError(
            "acceptance note must be non-empty"
        )
    evidence = spec.get("evidence")
    if (
        not isinstance(evidence, list)
        or not evidence
        or any(not isinstance(row, str) or not row.strip() for row in evidence)
    ):
        raise ReviewedMemberIdentityError(
            "acceptance evidence must be a non-empty string array"
        )

    requested = spec.get("relationship_ids")
    if (
        not isinstance(requested, list)
        or not requested
        or any(not isinstance(value, str) or not value for value in requested)
    ):
        raise ReviewedMemberIdentityError(
            "relationship_ids must be a non-empty string array"
        )
    if len(set(requested)) != len(requested):
        raise ReviewedMemberIdentityError(
            "duplicate relationship_id supplied"
        )

    reviews = _review_rows(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_owners = _owner_map(class_lineage, old_build_id)
    new_owners = _owner_map(class_lineage, new_build_id)
    old_fields = _old_field_map(member_lineage, old_build_id)
    target_owners = _target_field_owners(member_lineage, new_build_id)

    verified: list[
        tuple[
            str,
            dict[str, Any],
            dict[str, Any],
            str,
            str,
            dict[str, Any],
            dict[str, Any],
        ]
    ] = []
    planned_targets: dict[tuple[str, str, str], str] = {}
    planned_members: set[str] = set()

    for relationship_id in sorted(requested):
        item = reviews.get(relationship_id)
        if item is None:
            raise ReviewedMemberIdentityError(
                f"relationship_id {relationship_id!r} is not an unresolved "
                "field member_identity_review for the requested build pair"
            )
        candidate = item["candidate"]
        old_owner = str(candidate.get("old_owner", "")).removesuffix(".class")
        new_owner = str(candidate.get("new_owner", "")).removesuffix(".class")
        if not old_owner or not new_owner:
            raise ReviewedMemberIdentityError(
                f"{relationship_id}: candidate owner is invalid"
            )

        old_logical = old_owners.get(old_owner)
        new_logical = new_owners.get(new_owner)
        if old_logical is None or new_logical is None:
            raise ReviewedMemberIdentityError(
                f"{relationship_id}: owner is not canonical in old/new build"
            )
        if old_logical != new_logical:
            raise ReviewedMemberIdentityError(
                f"{relationship_id}: old/new owners resolve to different "
                "canonical logical classes"
            )

        old_name, old_desc, old_access = _coord(
            candidate.get("old"),
            label=f"{relationship_id}.old",
        )
        new_name, new_desc, new_access = _coord(
            candidate.get("new"),
            label=f"{relationship_id}.new",
        )

        old_decl = _exact_field(
            old_index,
            owner=old_owner,
            name=old_name,
            descriptor=old_desc,
        )
        new_decl = _exact_field(
            new_index,
            owner=new_owner,
            name=new_name,
            descriptor=new_desc,
        )
        if (
            old_access is not None
            and int(old_decl.get("access", 0)) != old_access
        ):
            raise ReviewedMemberIdentityError(
                f"{relationship_id}: old access disagrees with exact index"
            )
        if (
            new_access is not None
            and int(new_decl.get("access", 0)) != new_access
        ):
            raise ReviewedMemberIdentityError(
                f"{relationship_id}: new access disagrees with exact index"
            )

        old_key = (old_owner, old_name, old_desc)
        record = old_fields.get(old_key)
        if record is None:
            raise ReviewedMemberIdentityError(
                f"{relationship_id}: old coordinate is not a canonical field"
            )
        if record.get("owner_logical_id") != old_logical:
            raise ReviewedMemberIdentityError(
                f"{relationship_id}: old member owner logical ID mismatch"
            )

        target_key = (new_owner, new_name, new_desc)
        member_id = str(record.get("member_id"))
        occupied = target_owners.get(target_key)
        if occupied is not None and occupied != member_id:
            raise ReviewedMemberIdentityError(
                f"{relationship_id}: target coordinate already belongs to "
                f"{occupied}"
            )
        planned_owner = planned_targets.get(target_key)
        if planned_owner is not None and planned_owner != member_id:
            raise ReviewedMemberIdentityError(
                f"{relationship_id}: target coordinate is requested by "
                f"multiple canonical members"
            )
        if member_id in planned_members:
            raise ReviewedMemberIdentityError(
                f"{relationship_id}: canonical member is requested more than "
                f"once for build {new_build_id!r}"
            )
        if any(
            entry.get("build_id") == new_build_id
            for entry in record.get("lineage", [])
        ):
            raise ReviewedMemberIdentityError(
                f"{relationship_id}: canonical member already has a "
                f"{new_build_id!r} relation"
            )
        planned_targets[target_key] = member_id
        planned_members.add(member_id)

        verified.append(
            (
                relationship_id,
                item,
                record,
                new_owner,
                new_name,
                new_decl,
                candidate,
            )
        )

    out = copy.deepcopy(member_lineage)
    by_id = {
        row["member_id"]: row
        for row in out.get("members", [])
    }
    accepted_ids: set[str] = set()

    for (
        relationship_id,
        _item,
        old_record,
        new_owner,
        new_name,
        new_decl,
        candidate,
    ) in verified:
        target = by_id[old_record["member_id"]]
        new_desc = str(candidate["new"]["descriptor"])
        target["lineage"].append(
            {
                "build_id": new_build_id,
                "owner_internal_name": new_owner,
                "name": new_name,
                "descriptor": new_desc,
                "access": int(new_decl.get("access", 0)),
                "relation": "MANUAL",
                "confidence": 1.0,
                "provenance": [
                    {
                        "authority": "RESEARCH",
                        "source": relationship_id,
                        "note": note,
                        "evidence": list(evidence),
                    }
                ],
            }
        )
        accepted_ids.add(relationship_id)

    retained = []
    removed = 0
    for item in out.get("unresolved", []):
        candidate = (
            item.get("candidate")
            if isinstance(item, dict)
            else None
        )
        relationship_id = (
            candidate.get("relationship_id")
            if isinstance(candidate, dict)
            else None
        )
        if (
            isinstance(item, dict)
            and item.get("kind") == "member_identity_review"
            and item.get("member_kind") == "field"
            and item.get("source") == "member_identity_candidates"
            and item.get("old_build_id") == old_build_id
            and item.get("new_build_id") == new_build_id
            and relationship_id in accepted_ids
        ):
            removed += 1
            continue
        retained.append(item)
    out["unresolved"] = retained

    summary = dict(
        validate_member_lineage(
            out,
            class_lineage=class_lineage,
        )
    )
    summary.update(
        {
            "accepted_reviewed_member_identities": len(verified),
            "accepted_reviewed_fields": len(verified),
            "unresolved_removed": removed,
        }
    )
    return out, summary
