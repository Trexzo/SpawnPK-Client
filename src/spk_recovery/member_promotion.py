from __future__ import annotations

import copy
import re
from typing import Any

from .lineage import ALLOWED_AUTHORITIES, validate_lineage
from .member_lineage import (
    MemberLineageError,
    validate_member_lineage,
)


class NewMemberPromotionError(MemberLineageError):
    pass


_FIELD_ID_RE = re.compile(r"^CLIENT_FIELD_(\d{6})$")
_METHOD_ID_RE = re.compile(r"^CLIENT_METHOD_(\d{6})$")


def _owner_for_build(
    class_lineage: dict[str, Any],
    *,
    build_id: str,
    owner_logical_id: str,
) -> str:
    hits = []
    for record in class_lineage.get("classes", []):
        if record.get("logical_id") != owner_logical_id:
            continue
        for entry in record.get("lineage", []):
            if entry.get("build_id") == build_id:
                hits.append(entry.get("internal_name"))
    if len(hits) != 1 or not isinstance(hits[0], str):
        raise NewMemberPromotionError(
            f"expected one owner path for {owner_logical_id} in {build_id!r}, "
            f"found {len(hits)}"
        )
    return hits[0]


def _next_ordinal(
    member_lineage: dict[str, Any],
    *,
    kind: str,
) -> int:
    pattern = _FIELD_ID_RE if kind == "field" else _METHOD_ID_RE
    highest = 0
    for record in member_lineage.get("members", []):
        if record.get("kind") != kind:
            continue
        member_id = record.get("member_id")
        if not isinstance(member_id, str):
            continue
        match = pattern.fullmatch(member_id)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def _candidate_coord(
    item: dict[str, Any],
    *,
    build_id: str,
) -> tuple[str, str, str, str] | None:
    if (
        item.get("kind") != "member_unmatched_new"
        or item.get("new_build_id") != build_id
    ):
        return None

    owner_id = item.get("owner_logical_id")
    kind = item.get("member_kind")
    candidate = item.get("candidate")
    if (
        not isinstance(owner_id, str)
        or kind not in {"field", "method"}
        or not isinstance(candidate, dict)
    ):
        return None

    name = candidate.get("name")
    descriptor = candidate.get("descriptor")
    if not isinstance(name, str) or not isinstance(descriptor, str):
        return None
    return owner_id, kind, name, descriptor


def _spec_coord(
    item: Any,
    *,
    label: str,
) -> tuple[str, str, str, str]:
    if not isinstance(item, dict):
        raise NewMemberPromotionError(f"{label} must be an object")
    owner_id = item.get("owner_logical_id")
    kind = item.get("kind")
    name = item.get("name")
    descriptor = item.get("descriptor")
    if not isinstance(owner_id, str) or not owner_id:
        raise NewMemberPromotionError(
            f"{label}.owner_logical_id must be non-empty"
        )
    if kind not in {"field", "method"}:
        raise NewMemberPromotionError(
            f"{label}.kind must be field or method"
        )
    if not isinstance(name, str) or not name:
        raise NewMemberPromotionError(
            f"{label}.name must be non-empty"
        )
    if not isinstance(descriptor, str) or not descriptor:
        raise NewMemberPromotionError(
            f"{label}.descriptor must be non-empty"
        )
    if kind == "method" and name in {"<init>", "<clinit>"}:
        raise NewMemberPromotionError(
            f"{label}: constructors cannot be promoted as renamable members"
        )
    return owner_id, kind, name, descriptor


def _exact_member(
    index: dict[str, Any],
    *,
    owner: str,
    kind: str,
    name: str,
    descriptor: str,
) -> dict[str, Any]:
    cls = index.get("classes", {}).get(owner + ".class")
    if not isinstance(cls, dict):
        raise NewMemberPromotionError(
            f"target index missing owner class {owner!r}"
        )
    collection = "fields" if kind == "field" else "methods"
    hits = [
        member
        for member in cls.get(collection, [])
        if member.get("name") == name
        and member.get("descriptor") == descriptor
    ]
    if len(hits) != 1:
        raise NewMemberPromotionError(
            f"expected exactly one target {kind} "
            f"{owner}.{name}{descriptor}, found {len(hits)}"
        )
    return hits[0]


def promote_new_members(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    new_index: dict[str, Any],
    spec: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    """Promote explicitly reviewed unmatched-new members into stable IDs."""
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    if (
        spec.get("schema_version") != 1
        or spec.get("kind") != "new_member_promotion_spec"
    ):
        raise NewMemberPromotionError(
            "unsupported new-member promotion spec"
        )

    build_id = spec.get("build_id")
    if not isinstance(build_id, str) or not build_id:
        raise NewMemberPromotionError(
            "promotion build_id must be non-empty"
        )

    builds = {
        row.get("build_id"): row
        for row in class_lineage.get("builds", [])
    }
    build = builds.get(build_id)
    if not isinstance(build, dict):
        raise NewMemberPromotionError(
            f"unknown canonical target build {build_id!r}"
        )
    if (
        str(build.get("sha256", "")).lower()
        != str(new_index.get("sha256", "")).lower()
    ):
        raise NewMemberPromotionError(
            "target index SHA does not match canonical target build"
        )

    authority = spec.get("authority", "RESEARCH")
    if authority not in ALLOWED_AUTHORITIES:
        raise NewMemberPromotionError(
            f"unsupported promotion authority {authority!r}"
        )
    note = spec.get(
        "note",
        "Explicitly reviewed and promoted from member_unmatched_new.",
    )
    if not isinstance(note, str) or not note.strip():
        raise NewMemberPromotionError(
            "promotion note must be non-empty"
        )

    requested = spec.get("members")
    if not isinstance(requested, list) or not requested:
        raise NewMemberPromotionError(
            "promotion members must be a non-empty array"
        )

    coords = [
        _spec_coord(item, label=f"members[{i}]")
        for i, item in enumerate(requested)
    ]
    if len(set(coords)) != len(coords):
        raise NewMemberPromotionError(
            "duplicate member promotion coordinate supplied"
        )

    unresolved_coords = {
        coord
        for item in member_lineage.get("unresolved", [])
        if isinstance(item, dict)
        for coord in [_candidate_coord(item, build_id=build_id)]
        if coord is not None
    }

    owned_coords = {
        (
            record.get("owner_logical_id"),
            record.get("kind"),
            entry.get("name"),
            entry.get("descriptor"),
        )
        for record in member_lineage.get("members", [])
        for entry in record.get("lineage", [])
        if entry.get("build_id") == build_id
    }

    verified: list[
        tuple[tuple[str, str, str, str], str, dict[str, Any]]
    ] = []
    for coord in sorted(coords):
        owner_id, kind, name, descriptor = coord
        if coord in owned_coords:
            raise NewMemberPromotionError(
                f"member coordinate {coord!r} is already canonical in {build_id}"
            )
        if coord not in unresolved_coords:
            raise NewMemberPromotionError(
                f"member coordinate {coord!r} is not recorded as "
                f"member_unmatched_new for {build_id!r}"
            )

        owner = _owner_for_build(
            class_lineage,
            build_id=build_id,
            owner_logical_id=owner_id,
        )
        declaration = _exact_member(
            new_index,
            owner=owner,
            kind=kind,
            name=name,
            descriptor=descriptor,
        )
        verified.append((coord, owner, declaration))

    out = copy.deepcopy(member_lineage)
    field_ordinal = _next_ordinal(out, kind="field")
    method_ordinal = _next_ordinal(out, kind="method")

    for coord, owner, declaration in verified:
        owner_id, kind, name, descriptor = coord
        if kind == "field":
            member_id = f"CLIENT_FIELD_{field_ordinal:06d}"
            field_ordinal += 1
        else:
            member_id = f"CLIENT_METHOD_{method_ordinal:06d}"
            method_ordinal += 1

        relation = {
            "build_id": build_id,
            "owner_internal_name": owner,
            "name": name,
            "descriptor": descriptor,
            "access": int(declaration.get("access", 0)),
            **(
                {"code_length": declaration.get("code_length")}
                if kind == "method"
                else {}
            ),
            "relation": "MANUAL",
            "confidence": 1.0,
            "provenance": [
                {
                    "authority": authority,
                    "source": "new-member-promotion",
                    "note": note,
                }
            ],
        }
        out["members"].append(
            {
                "member_id": member_id,
                "owner_logical_id": owner_id,
                "kind": kind,
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [relation],
                "semantic_provenance": [],
            }
        )

    requested_set = set(coords)
    retained = []
    removed = 0
    for item in out.get("unresolved", []):
        coord = (
            _candidate_coord(item, build_id=build_id)
            if isinstance(item, dict)
            else None
        )
        if coord in requested_set:
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
            "promoted_new_members": len(verified),
            "promoted_new_fields": sum(
                1 for coord, _, _ in verified if coord[1] == "field"
            ),
            "promoted_new_methods": sum(
                1 for coord, _, _ in verified if coord[1] == "method"
            ),
            "unresolved_removed": removed,
        }
    )
    return out, summary
