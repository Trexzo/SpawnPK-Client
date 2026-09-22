from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .lineage import LineageValidationError, validate_lineage
from .member_lineage import (
    MemberLineageError,
    validate_member_lineage,
)


class SemanticReviewError(ValueError):
    pass


_IDENTIFIER = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _proposal_id(
    source_sha256: str,
    kind: str,
    stable_id: str,
    proposed_name: str,
) -> str:
    raw = (
        source_sha256.lower()
        + "|"
        + kind
        + "|"
        + stable_id
        + "|"
        + proposed_name
    ).encode("utf-8")
    return "SEMPROP_" + hashlib.sha256(raw).hexdigest()[:20].upper()


def _review_id(proposals: list[dict[str, Any]]) -> str:
    canonical = [
        {
            "proposal_id": row["proposal_id"],
            "target_kind": row["target_kind"],
            "stable_id": row["stable_id"],
            "proposed_name": row["proposed_name"],
            "confidence": row["confidence"],
        }
        for row in sorted(proposals, key=lambda r: r["proposal_id"])
    ]
    return "SEMREVIEW_" + hashlib.sha256(_stable_json(canonical)).hexdigest()[:20].upper()


def _validate_name(name: Any) -> str:
    if not isinstance(name, str) or not _IDENTIFIER.fullmatch(name):
        raise SemanticReviewError(
            f"semantic name must be one Java identifier, got {name!r}"
        )
    if name in {"<init>", "<clinit>"}:
        raise SemanticReviewError("constructor/static-initializer names are reserved")
    return name


def _build(class_lineage: dict[str, Any], build_id: str) -> dict[str, Any]:
    hits = [
        row
        for row in class_lineage.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(hits) != 1:
        raise SemanticReviewError(
            f"expected one canonical build {build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _class_coordinates(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for record in class_lineage.get("classes", []):
        for entry in record.get("lineage", []):
            if entry.get("build_id") != build_id:
                continue
            owner = entry.get("internal_name")
            if owner in out:
                raise SemanticReviewError(
                    f"duplicate class coordinate {owner!r} in build {build_id!r}"
                )
            out[owner] = record
    return out


def _member_coordinates(
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
                str(kind),
                str(entry.get("owner_internal_name")),
                str(entry.get("name")),
                str(entry.get("descriptor")),
            )
            if key in out:
                raise SemanticReviewError(
                    f"duplicate member coordinate in build {build_id!r}: {key!r}"
                )
            out[key] = record
    return out


def resolve_semantic_candidates(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    candidate_set: dict[str, Any],
) -> dict[str, Any]:
    """Resolve research semantic candidates to stable canonical IDs without mutation."""
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    if candidate_set.get("schema_version") != 1:
        raise SemanticReviewError("candidate schema_version must be 1")
    if candidate_set.get("kind") != "semantic_candidate_set":
        raise SemanticReviewError(
            "candidate kind must be semantic_candidate_set"
        )
    if candidate_set.get("canonical") is not False:
        raise SemanticReviewError(
            "semantic input must be explicitly non-canonical"
        )

    source_build = candidate_set.get("source_build")
    source_sha = str(candidate_set.get("source_sha256", "")).lower()
    if not isinstance(source_build, str) or not source_build:
        raise SemanticReviewError("source_build must be non-empty")
    build = _build(class_lineage, source_build)
    if source_sha != str(build.get("sha256", "")).lower():
        raise SemanticReviewError(
            "semantic candidate source SHA does not match canonical build"
        )

    class_coords = _class_coordinates(class_lineage, source_build)
    member_coords = _member_coordinates(member_lineage, source_build)

    proposals: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    seen_proposals: set[str] = set()

    candidates = candidate_set.get("candidates")
    if not isinstance(candidates, list):
        raise SemanticReviewError("candidate set candidates must be an array")

    for ordinal, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            unresolved.append(
                {
                    "ordinal": ordinal,
                    "reason": "candidate_not_object",
                }
            )
            continue

        if candidate.get("source_build") != source_build:
            unresolved.append(
                {
                    "ordinal": ordinal,
                    "reason": "candidate_build_mismatch",
                    "candidate": candidate,
                }
            )
            continue
        if str(candidate.get("source_sha256", "")).lower() != source_sha:
            unresolved.append(
                {
                    "ordinal": ordinal,
                    "reason": "candidate_sha_mismatch",
                    "candidate": candidate,
                }
            )
            continue

        target = candidate.get("target")
        if not isinstance(target, dict):
            unresolved.append(
                {
                    "ordinal": ordinal,
                    "reason": "missing_target",
                    "candidate": candidate,
                }
            )
            continue

        kind = target.get("kind")
        try:
            proposed_name = _validate_name(candidate.get("proposed_name"))
        except SemanticReviewError as exc:
            unresolved.append(
                {
                    "ordinal": ordinal,
                    "reason": "invalid_proposed_name",
                    "detail": str(exc),
                    "candidate": candidate,
                }
            )
            continue

        confidence = candidate.get("confidence")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= float(confidence) <= 1.0
        ):
            unresolved.append(
                {
                    "ordinal": ordinal,
                    "reason": "invalid_confidence",
                    "candidate": candidate,
                }
            )
            continue
        confidence = float(confidence)

        stable_record: dict[str, Any] | None = None
        stable_id: str | None = None
        owner_logical_id: str | None = None

        if kind == "class":
            owner = target.get("owner")
            if not isinstance(owner, str):
                stable_record = None
            else:
                stable_record = class_coords.get(owner)
            if stable_record is not None:
                stable_id = stable_record["logical_id"]
                owner_logical_id = stable_id
        elif kind in {"field", "method"}:
            owner = target.get("owner")
            name = target.get("name")
            descriptor = target.get("descriptor")
            if all(isinstance(x, str) for x in (owner, name, descriptor)):
                stable_record = member_coords.get(
                    (kind, owner, name, descriptor)
                )
            if stable_record is not None:
                stable_id = stable_record["member_id"]
                owner_logical_id = stable_record["owner_logical_id"]
        else:
            unresolved.append(
                {
                    "ordinal": ordinal,
                    "reason": "unsupported_target_kind",
                    "candidate": candidate,
                }
            )
            continue

        if stable_record is None or stable_id is None:
            unresolved.append(
                {
                    "ordinal": ordinal,
                    "reason": "target_coordinate_not_canonical",
                    "candidate": candidate,
                }
            )
            continue

        proposal_id = _proposal_id(
            source_sha,
            str(kind),
            stable_id,
            proposed_name,
        )
        if proposal_id in seen_proposals:
            unresolved.append(
                {
                    "ordinal": ordinal,
                    "reason": "duplicate_semantic_proposal",
                    "proposal_id": proposal_id,
                    "candidate": candidate,
                }
            )
            continue
        seen_proposals.add(proposal_id)

        evidence = candidate.get("evidence")
        if not isinstance(evidence, list):
            evidence = []

        proposals.append(
            {
                "proposal_id": proposal_id,
                "target_kind": kind,
                "stable_id": stable_id,
                "owner_logical_id": owner_logical_id,
                "source_build": source_build,
                "source_sha256": source_sha,
                "source_coordinate": {
                    "owner": target.get("owner"),
                    "name": target.get("name"),
                    "descriptor": target.get("descriptor"),
                },
                "proposed_name": proposed_name,
                "confidence": confidence,
                "evidence": copy.deepcopy(evidence),
                "note": candidate.get("note"),
            }
        )

    proposals.sort(key=lambda row: row["proposal_id"])
    return {
        "schema_version": 1,
        "kind": "semantic_review_set",
        "canonical": False,
        "source_build": source_build,
        "source_sha256": source_sha,
        "proposal_count": len(proposals),
        "review_id": _review_id(proposals),
        "proposals": proposals,
        "unresolved": unresolved,
    }


def _accepted_name_collision(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    proposal: dict[str, Any],
) -> str | None:
    kind = proposal["target_kind"]
    proposed_name = proposal["proposed_name"]
    stable_id = proposal["stable_id"]

    if kind == "class":
        for record in class_lineage.get("classes", []):
            if record["logical_id"] == stable_id:
                continue
            if (
                record.get("semantic_status") == "ACCEPTED"
                and record.get("semantic_name") == proposed_name
            ):
                return (
                    f"class semantic name {proposed_name!r} already accepted "
                    f"by {record['logical_id']}"
                )
        return None

    owner_id = proposal["owner_logical_id"]
    source_descriptor = proposal["source_coordinate"].get("descriptor")
    for record in member_lineage.get("members", []):
        if record["member_id"] == stable_id:
            continue
        if record.get("owner_logical_id") != owner_id:
            continue
        if record.get("kind") != kind:
            continue
        if record.get("semantic_status") != "ACCEPTED":
            continue
        if record.get("semantic_name") != proposed_name:
            continue

        if kind == "field":
            return (
                f"field semantic name {proposed_name!r} already accepted "
                f"inside owner {owner_id}"
            )

        for entry in record.get("lineage", []):
            if entry.get("build_id") == proposal["source_build"]:
                if entry.get("descriptor") == source_descriptor:
                    return (
                        f"method semantic signature {proposed_name}"
                        f"{source_descriptor} already accepted inside owner {owner_id}"
                    )
    return None


def accept_semantic_proposals(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    review_set: dict[str, Any],
    acceptance_spec: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    """Promote explicitly selected reviewed proposals into canonical semantic state."""
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    if review_set.get("schema_version") != 1:
        raise SemanticReviewError("review schema_version must be 1")
    if review_set.get("kind") != "semantic_review_set":
        raise SemanticReviewError("review kind must be semantic_review_set")
    if review_set.get("canonical") is not False:
        raise SemanticReviewError("review set must be non-canonical")
    expected_review = _review_id(list(review_set.get("proposals", [])))
    if review_set.get("review_id") != expected_review:
        raise SemanticReviewError("semantic review_id does not match proposal contents")

    if acceptance_spec.get("schema_version") != 1:
        raise SemanticReviewError("acceptance schema_version must be 1")
    if acceptance_spec.get("kind") != "semantic_acceptance_spec":
        raise SemanticReviewError(
            "acceptance kind must be semantic_acceptance_spec"
        )
    if acceptance_spec.get("review_id") != review_set.get("review_id"):
        raise SemanticReviewError(
            "acceptance spec review_id does not match reviewed proposals"
        )

    accepted_ids = acceptance_spec.get("accept")
    if (
        not isinstance(accepted_ids, list)
        or not accepted_ids
        or any(not isinstance(x, str) for x in accepted_ids)
    ):
        raise SemanticReviewError(
            "acceptance spec accept must be a non-empty string array"
        )
    if len(set(accepted_ids)) != len(accepted_ids):
        raise SemanticReviewError("acceptance spec contains duplicate proposal IDs")

    by_id = {
        row["proposal_id"]: row
        for row in review_set.get("proposals", [])
    }
    missing = sorted(set(accepted_ids) - set(by_id))
    if missing:
        raise SemanticReviewError(
            f"acceptance references unknown proposal IDs: {missing}"
        )

    classes = copy.deepcopy(class_lineage)
    members = copy.deepcopy(member_lineage)
    class_map = {
        record["logical_id"]: record
        for record in classes.get("classes", [])
    }
    member_map = {
        record["member_id"]: record
        for record in members.get("members", [])
    }

    accepted_classes = 0
    accepted_members = 0
    already_accepted = 0

    for proposal_id in accepted_ids:
        proposal = by_id[proposal_id]
        collision = _accepted_name_collision(
            classes,
            members,
            proposal,
        )
        if collision:
            raise SemanticReviewError(collision)

        if proposal["target_kind"] == "class":
            record = class_map.get(proposal["stable_id"])
            if record is None:
                raise SemanticReviewError(
                    f"review target class vanished: {proposal['stable_id']}"
                )
            accepted_classes += 1
        else:
            record = member_map.get(proposal["stable_id"])
            if record is None:
                raise SemanticReviewError(
                    f"review target member vanished: {proposal['stable_id']}"
                )
            accepted_members += 1

        prior_status = record.get("semantic_status")
        prior_name = record.get("semantic_name")
        if prior_status == "ACCEPTED":
            if prior_name != proposal["proposed_name"]:
                raise SemanticReviewError(
                    f"{proposal['stable_id']} already accepted as {prior_name!r}"
                )
            already_accepted += 1
            continue

        record["semantic_name"] = proposal["proposed_name"]
        record["semantic_status"] = "ACCEPTED"
        record["semantic_confidence"] = float(proposal["confidence"])
        record.setdefault("semantic_provenance", []).append(
            {
                "proposal_id": proposal_id,
                "review_id": review_set["review_id"],
                "source_build": proposal["source_build"],
                "source_sha256": proposal["source_sha256"],
                "source_coordinate": copy.deepcopy(
                    proposal["source_coordinate"]
                ),
                "evidence": copy.deepcopy(proposal["evidence"]),
                "note": proposal.get("note"),
            }
        )

    validate_lineage(classes)
    validate_member_lineage(
        members,
        class_lineage=classes,
    )

    return (
        classes,
        members,
        {
            "accepted": len(accepted_ids),
            "accepted_classes": accepted_classes,
            "accepted_members": accepted_members,
            "already_accepted": already_accepted,
        },
    )


def write_json(doc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
