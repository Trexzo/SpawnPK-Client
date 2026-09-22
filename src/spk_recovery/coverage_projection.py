from __future__ import annotations

import copy
from typing import Any

from .coverage import build_coverage_report
from .lineage import validate_lineage
from .member_lineage import validate_member_lineage


class CoverageProjectionError(ValueError):
    pass


def _has_build(record: dict[str, Any], build_id: str) -> bool:
    return any(
        row.get("build_id") == build_id
        for row in record.get("lineage", [])
    )


def _apply_candidate(
    record: dict[str, Any],
    proposal: dict[str, Any],
    *,
    review_id: str,
) -> str:
    proposed_name = proposal.get("proposed_name")
    confidence = proposal.get("confidence")
    if not isinstance(proposed_name, str) or not proposed_name:
        raise CoverageProjectionError(
            "proposal has no semantic name"
        )
    if (
        not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or not 0.0 <= float(confidence) <= 1.0
    ):
        raise CoverageProjectionError(
            "proposal confidence is invalid"
        )

    status = record.get("semantic_status")
    current_name = record.get("semantic_name")
    if status == "ACCEPTED":
        if current_name != proposed_name:
            raise CoverageProjectionError(
                "review proposal conflicts with an ACCEPTED semantic name"
            )
        return "accepted_unchanged"

    if status == "CANDIDATE":
        if current_name not in (None, proposed_name):
            raise CoverageProjectionError(
                "review proposal conflicts with an existing CANDIDATE name"
            )
        return "candidate_unchanged"

    if status != "UNKNOWN":
        raise CoverageProjectionError(
            f"unsupported semantic status {status!r}"
        )

    record["semantic_name"] = proposed_name
    record["semantic_status"] = "CANDIDATE"
    record["semantic_confidence"] = float(confidence)
    record["semantic_provenance"] = [
        {
            "family": "semantic_review_projection",
            "review_id": review_id,
            "proposal_id": proposal.get("proposal_id"),
            "source_build": proposal.get("source_build"),
            "source_sha256": proposal.get("source_sha256"),
            "evidence": proposal.get("evidence", []),
        }
    ]
    return "projected_candidate"


def project_semantic_review_coverage(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    review: dict[str, Any],
    *,
    build_id: str,
) -> dict[str, Any]:
    """Project reviewed semantic proposals into R4D coverage without acceptance.

    The canonical inputs are never mutated. UNKNOWN records are changed to
    CANDIDATE only in deep copies used for the projected coverage report.
    """
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )
    if review.get("schema_version") != 1:
        raise CoverageProjectionError(
            "semantic review schema_version must be 1"
        )
    if review.get("kind") != "semantic_review_set":
        raise CoverageProjectionError(
            "expected semantic_review_set"
        )
    if review.get("canonical") is not False:
        raise CoverageProjectionError(
            "semantic review must be explicitly non-canonical"
        )
    if review.get("source_build") != build_id:
        raise CoverageProjectionError(
            "semantic review build does not match projection build"
        )
    unresolved = review.get("unresolved")
    if not isinstance(unresolved, list):
        raise CoverageProjectionError(
            "semantic review unresolved must be an array"
        )
    if unresolved:
        raise CoverageProjectionError(
            "semantic review has unresolved candidates"
        )

    builds = [
        row
        for row in class_lineage.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(builds) != 1:
        raise CoverageProjectionError(
            f"expected one canonical build {build_id!r}"
        )
    source_sha = str(builds[0].get("sha256", "")).lower()
    if str(review.get("source_sha256", "")).lower() != source_sha:
        raise CoverageProjectionError(
            "semantic review SHA-256 does not match canonical build"
        )

    base = build_coverage_report(
        class_lineage,
        member_lineage,
        build_id=build_id,
    )
    projected_classes = copy.deepcopy(class_lineage)
    projected_members = copy.deepcopy(member_lineage)

    class_by_id = {
        row.get("logical_id"): row
        for row in projected_classes.get("classes", [])
        if isinstance(row, dict)
    }
    member_by_id = {
        row.get("member_id"): row
        for row in projected_members.get("members", [])
        if isinstance(row, dict)
    }

    counts = {
        "projected_candidate": 0,
        "candidate_unchanged": 0,
        "accepted_unchanged": 0,
        "classes": 0,
        "fields": 0,
        "methods": 0,
    }
    seen_ids: set[str] = set()

    proposals = review.get("proposals")
    if not isinstance(proposals, list):
        raise CoverageProjectionError(
            "semantic review proposals must be an array"
        )

    for proposal in proposals:
        if not isinstance(proposal, dict):
            raise CoverageProjectionError(
                "semantic review proposal must be an object"
            )
        proposal_id = proposal.get("proposal_id")
        if not isinstance(proposal_id, str) or not proposal_id:
            raise CoverageProjectionError(
                "semantic review proposal has no proposal_id"
            )
        if proposal_id in seen_ids:
            raise CoverageProjectionError(
                f"duplicate proposal_id {proposal_id!r}"
            )
        seen_ids.add(proposal_id)

        kind = proposal.get("target_kind")
        stable_id = proposal.get("stable_id")
        if kind == "class":
            record = class_by_id.get(stable_id)
            counts["classes"] += 1
        elif kind in {"field", "method"}:
            record = member_by_id.get(stable_id)
            counts[kind + "s"] += 1
            if record is not None and record.get("kind") != kind:
                raise CoverageProjectionError(
                    f"{stable_id}: proposal kind does not match member kind"
                )
        else:
            raise CoverageProjectionError(
                f"unsupported proposal target kind {kind!r}"
            )

        if record is None:
            raise CoverageProjectionError(
                f"unknown stable semantic target {stable_id!r}"
            )
        if not _has_build(record, build_id):
            raise CoverageProjectionError(
                f"{stable_id}: target has no {build_id!r} lineage entry"
            )

        outcome = _apply_candidate(
            record,
            proposal,
            review_id=str(review.get("review_id", "")),
        )
        counts[outcome] += 1

    projected = build_coverage_report(
        projected_classes,
        projected_members,
        build_id=build_id,
    )

    return {
        "schema_version": 1,
        "kind": "semantic_coverage_projection",
        "canonical": False,
        "build_id": build_id,
        "source_sha256": source_sha,
        "review_id": review.get("review_id"),
        "proposal_count": len(proposals),
        "application": counts,
        "base": base,
        "projected": projected,
    }
