from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .lineage import LineageValidationError, validate_lineage
from .member_lineage import (
    MemberLineageError,
    validate_member_lineage,
    write_member_lineage,
)


class UpdateMemberTransferError(MemberLineageError):
    pass


_TRUSTED_MEMBER_STRATEGIES = {
    "stable_symbol",
    "structural_unique",
}


def _canonical_owner_map(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, str]:
    owners: dict[str, str] = {}
    for record in class_lineage.get("classes", []):
        logical_id = record.get("logical_id")
        for entry in record.get("lineage", []):
            if entry.get("build_id") != build_id:
                continue
            internal = entry.get("internal_name")
            if not isinstance(internal, str) or not internal:
                raise UpdateMemberTransferError(
                    f"invalid class owner in canonical build {build_id!r}"
                )
            if internal in owners:
                raise UpdateMemberTransferError(
                    f"duplicate canonical class owner {internal!r} in {build_id!r}"
                )
            owners[internal] = str(logical_id)
    return owners


def _member_old_map(
    member_lineage: dict[str, Any],
    build_id: str,
) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    out: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for record in member_lineage.get("members", []):
        kind = record.get("kind")
        for entry in record.get("lineage", []):
            if entry.get("build_id") != build_id:
                continue
            key = (
                str(entry.get("owner_internal_name")),
                str(kind),
                str(entry.get("name")),
                str(entry.get("descriptor")),
            )
            if key in out:
                raise UpdateMemberTransferError(
                    f"duplicate canonical old member coordinate {key!r}"
                )
            out[key] = record
    return out


def _index_member(
    index: dict[str, Any],
    *,
    owner: str,
    kind: str,
    name: str,
    descriptor: str,
) -> dict[str, Any]:
    cls = index.get("classes", {}).get(owner + ".class")
    if not isinstance(cls, dict):
        raise UpdateMemberTransferError(
            f"exact index missing member owner {owner!r}"
        )
    collection = "fields" if kind == "field" else "methods"
    hits = [
        member
        for member in cls.get(collection, [])
        if member.get("name") == name
        and member.get("descriptor") == descriptor
    ]
    if len(hits) != 1:
        raise UpdateMemberTransferError(
            f"expected exactly one {kind} {owner}.{name}{descriptor}, "
            f"found {len(hits)}"
        )
    return hits[0]


def _owner_internal(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise UpdateMemberTransferError(
            f"{label}: member owner must be a non-empty string"
        )
    return value[:-6] if value.endswith(".class") else value


def _candidate_coord(
    obj: Any,
    *,
    label: str,
) -> tuple[str, str, int | None]:
    if not isinstance(obj, dict):
        raise UpdateMemberTransferError(f"{label} must be an object")
    name = obj.get("name")
    descriptor = obj.get("descriptor")
    if not isinstance(name, str) or not name:
        raise UpdateMemberTransferError(
            f"{label}.name must be non-empty"
        )
    if not isinstance(descriptor, str) or not descriptor:
        raise UpdateMemberTransferError(
            f"{label}.descriptor must be non-empty"
        )
    access = obj.get("access")
    if access is not None and (
        not isinstance(access, int)
        or isinstance(access, bool)
    ):
        raise UpdateMemberTransferError(
            f"{label}.access must be integer or null"
        )
    return name, descriptor, access


def _score(value: Any, *, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise UpdateMemberTransferError(
            f"{label}: candidate score must be numeric"
        )
    score = float(value)
    if not 0.0 <= score <= 1.0:
        raise UpdateMemberTransferError(
            f"{label}: candidate score outside [0,1]"
        )
    return score


def transfer_member_identity_candidates(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    candidates: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Append trusted cross-build member identities to canonical member lineage.

    Candidate JSON is treated as untrusted research output. Owner-class identity,
    old canonical member ownership and the exact target declaration are all
    independently re-verified before any relation is appended.
    """
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    if (
        candidates.get("schema_version") != 1
        or candidates.get("kind") != "member_identity_candidates"
        or candidates.get("canonical") is not False
    ):
        raise UpdateMemberTransferError(
            "unsupported member identity candidate schema/kind"
        )

    old_sha = str(old_index.get("sha256", "")).lower()
    new_sha = str(new_index.get("sha256", "")).lower()
    if str(candidates.get("old_sha256", "")).lower() != old_sha:
        raise UpdateMemberTransferError(
            "candidate old SHA does not match exact old index"
        )
    if str(candidates.get("new_sha256", "")).lower() != new_sha:
        raise UpdateMemberTransferError(
            "candidate new SHA does not match exact new index"
        )

    builds = {
        str(row.get("build_id")): row
        for row in class_lineage.get("builds", [])
    }
    if old_build_id not in builds or new_build_id not in builds:
        raise UpdateMemberTransferError(
            "old/new builds must already exist in canonical class lineage"
        )
    if str(builds[old_build_id].get("sha256", "")).lower() != old_sha:
        raise UpdateMemberTransferError(
            "old index SHA does not match canonical old build"
        )
    if str(builds[new_build_id].get("sha256", "")).lower() != new_sha:
        raise UpdateMemberTransferError(
            "new index SHA does not match canonical new build"
        )

    old_owners = _canonical_owner_map(
        class_lineage,
        old_build_id,
    )
    new_owners = _canonical_owner_map(
        class_lineage,
        new_build_id,
    )
    old_members = _member_old_map(
        member_lineage,
        old_build_id,
    )

    out = copy.deepcopy(member_lineage)
    by_id = {
        record["member_id"]: record
        for record in out.get("members", [])
    }
    already_new_ids = {
        record["member_id"]
        for record in out.get("members", [])
        if any(
            entry.get("build_id") == new_build_id
            for entry in record.get("lineage", [])
        )
    }
    if already_new_ids:
        raise UpdateMemberTransferError(
            f"member lineage already contains {len(already_new_ids)} "
            f"relations for build {new_build_id!r}"
        )

    used_new_coords: set[
        tuple[str, str, str, str]
    ] = set()
    applied = 0
    review_only = 0
    unresolved_added = 0

    classes = candidates.get("classes")
    if not isinstance(classes, list):
        raise UpdateMemberTransferError(
            "candidate classes must be an array"
        )

    for class_i, class_row in enumerate(classes):
        label = f"classes[{class_i}]"
        if not isinstance(class_row, dict):
            raise UpdateMemberTransferError(
                f"{label} must be an object"
            )

        old_owner = _owner_internal(
            class_row.get("old_owner"),
            label=label + ".old_owner",
        )
        new_owner = _owner_internal(
            class_row.get("new_owner"),
            label=label + ".new_owner",
        )
        old_logical = old_owners.get(old_owner)
        new_logical = new_owners.get(new_owner)
        if old_logical is None or new_logical is None:
            out["unresolved"].append(
                {
                    "old_build_id": old_build_id,
                    "new_build_id": new_build_id,
                    "kind": "member_owner_not_canonical",
                    "candidate": copy.deepcopy(class_row),
                    "source": "member_identity_candidates",
                }
            )
            unresolved_added += 1
            continue
        if old_logical != new_logical:
            raise UpdateMemberTransferError(
                f"{label}: owner classes do not resolve to the same "
                f"canonical logical class ({old_logical} != {new_logical})"
            )

        for collection_name, kind in (
            ("fields", "field"),
            ("methods", "method"),
        ):
            group = class_row.get(collection_name)
            if not isinstance(group, dict):
                raise UpdateMemberTransferError(
                    f"{label}.{collection_name} must be an object"
                )
            relationships = group.get("relationships")
            if not isinstance(relationships, list):
                raise UpdateMemberTransferError(
                    f"{label}.{collection_name}.relationships "
                    "must be an array"
                )

            for rel_i, rel in enumerate(relationships):
                rlabel = (
                    f"{label}.{collection_name}"
                    f".relationships[{rel_i}]"
                )
                if not isinstance(rel, dict):
                    raise UpdateMemberTransferError(
                        f"{rlabel} must be an object"
                    )
                if rel.get("kind") != kind:
                    raise UpdateMemberTransferError(
                        f"{rlabel}: member kind mismatch"
                    )

                strategy = rel.get("strategy")
                if strategy not in _TRUSTED_MEMBER_STRATEGIES:
                    out["unresolved"].append(
                        {
                            "old_build_id": old_build_id,
                            "new_build_id": new_build_id,
                            "kind": "member_identity_review",
                            "candidate": copy.deepcopy(rel),
                            "source": "member_identity_candidates",
                        }
                    )
                    review_only += 1
                    unresolved_added += 1
                    continue

                rel_old_owner = _owner_internal(
                    rel.get("old_owner"),
                    label=rlabel + ".old_owner",
                )
                rel_new_owner = _owner_internal(
                    rel.get("new_owner"),
                    label=rlabel + ".new_owner",
                )
                if (
                    rel_old_owner != old_owner
                    or rel_new_owner != new_owner
                ):
                    raise UpdateMemberTransferError(
                        f"{rlabel}: relationship owner differs "
                        "from enclosing class pair"
                    )

                old_name, old_desc, old_access = _candidate_coord(
                    rel.get("old"),
                    label=rlabel + ".old",
                )
                new_name, new_desc, new_access = _candidate_coord(
                    rel.get("new"),
                    label=rlabel + ".new",
                )

                key = (
                    old_owner,
                    kind,
                    old_name,
                    old_desc,
                )
                old_record = old_members.get(key)
                if old_record is None:
                    raise UpdateMemberTransferError(
                        f"{rlabel}: old member coordinate is not "
                        "owned by canonical member lineage"
                    )
                if old_record.get("owner_logical_id") != old_logical:
                    raise UpdateMemberTransferError(
                        f"{rlabel}: canonical member owner ID mismatch"
                    )

                old_decl = _index_member(
                    old_index,
                    owner=old_owner,
                    kind=kind,
                    name=old_name,
                    descriptor=old_desc,
                )
                new_decl = _index_member(
                    new_index,
                    owner=new_owner,
                    kind=kind,
                    name=new_name,
                    descriptor=new_desc,
                )
                if (
                    old_access is not None
                    and int(old_decl.get("access", 0)) != old_access
                ):
                    raise UpdateMemberTransferError(
                        f"{rlabel}: candidate old access does not "
                        "match exact index"
                    )
                if (
                    new_access is not None
                    and int(new_decl.get("access", 0)) != new_access
                ):
                    raise UpdateMemberTransferError(
                        f"{rlabel}: candidate new access does not "
                        "match exact index"
                    )

                target_key = (
                    new_owner,
                    kind,
                    new_name,
                    new_desc,
                )
                if target_key in used_new_coords:
                    raise UpdateMemberTransferError(
                        f"{rlabel}: target member matched more than once"
                    )

                score = _score(
                    rel.get("score"),
                    label=rlabel,
                )
                member_id = old_record["member_id"]
                target_record = by_id[member_id]
                target_record["lineage"].append(
                    {
                        "build_id": new_build_id,
                        "owner_internal_name": new_owner,
                        "name": new_name,
                        "descriptor": new_desc,
                        "access": int(
                            new_decl.get("access", 0)
                        ),
                        **(
                            {
                                "code_length": new_decl.get(
                                    "code_length"
                                )
                            }
                            if kind == "method"
                            else {}
                        ),
                        "relation": "STRUCTURAL",
                        "confidence": score,
                        "provenance": [
                            {
                                "authority": "CROSS_BUILD",
                                "source": str(
                                    rel.get("relationship_id")
                                    or f"member-candidate-{class_i}-{rel_i}"
                                ),
                                "note": (
                                    "Imported from member identity strategy "
                                    f"{strategy}; core re-verified canonical "
                                    "owner identity and exact old/new member "
                                    "coordinates."
                                ),
                            }
                        ],
                    }
                )
                used_new_coords.add(target_key)
                applied += 1

            for unmatched_kind in (
                "unmatched_old",
                "unmatched_new",
            ):
                values = group.get(unmatched_kind, [])
                if not isinstance(values, list):
                    raise UpdateMemberTransferError(
                        f"{label}.{collection_name}.{unmatched_kind} "
                        "must be an array"
                    )
                for value in values:
                    out["unresolved"].append(
                        {
                            "old_build_id": old_build_id,
                            "new_build_id": new_build_id,
                            "kind": (
                                f"member_{unmatched_kind}"
                            ),
                            "owner_logical_id": old_logical,
                            "member_kind": kind,
                            "candidate": copy.deepcopy(value),
                            "source": "member_identity_candidates",
                        }
                    )
                    unresolved_added += 1

    skipped = candidates.get("skipped_classes", [])
    if not isinstance(skipped, list):
        raise UpdateMemberTransferError(
            "candidate skipped_classes must be an array"
        )
    for value in skipped:
        out["unresolved"].append(
            {
                "old_build_id": old_build_id,
                "new_build_id": new_build_id,
                "kind": "member_identity_skipped_class",
                "candidate": copy.deepcopy(value),
                "source": "member_identity_candidates",
            }
        )
        unresolved_added += 1

    summary = dict(
        validate_member_lineage(
            out,
            class_lineage=class_lineage,
        )
    )
    summary.update(
        {
            "applied_member_relationships": applied,
            "review_only_relationships": review_only,
            "unresolved_added": unresolved_added,
        }
    )
    return out, summary


def write_member_transfer_result(
    member_lineage: dict[str, Any],
    summary: dict[str, Any],
    *,
    lineage_out: Path,
    summary_out: Path | None = None,
) -> None:
    write_member_lineage(
        member_lineage,
        lineage_out,
    )
    if summary_out is not None:
        summary_out.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        summary_out.write_text(
            json.dumps(
                summary,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
