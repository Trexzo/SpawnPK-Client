from __future__ import annotations

from typing import Any

from .lineage import validate_lineage
from .member_lineage import validate_member_lineage


class CandidateCarryForwardError(ValueError):
    pass


def _has_build(record: dict[str, Any], build_id: str) -> bool:
    return any(
        row.get("build_id") == build_id
        for row in record.get("lineage", [])
    )


def project_candidate_carryforward(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    review: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
) -> dict[str, Any]:
    """Classify reviewed candidate semantics across canonical identity lineage.

    This is a research projection only. It does not copy names, change semantic
    status, or invoke the ACCEPTED R4E carry-forward path.
    """
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )
    if old_build_id == new_build_id:
        raise CandidateCarryForwardError(
            "old and new build IDs must differ"
        )
    if (
        review.get("schema_version") != 1
        or review.get("kind") != "semantic_review_set"
        or review.get("canonical") is not False
    ):
        raise CandidateCarryForwardError(
            "expected explicit non-canonical semantic_review_set"
        )
    if review.get("source_build") != old_build_id:
        raise CandidateCarryForwardError(
            "review source build does not match old build"
        )
    unresolved = review.get("unresolved")
    if not isinstance(unresolved, list):
        raise CandidateCarryForwardError(
            "review unresolved must be an array"
        )
    if unresolved:
        raise CandidateCarryForwardError(
            "review has unresolved candidates"
        )

    builds = {
        row.get("build_id"): row
        for row in class_lineage.get("builds", [])
        if isinstance(row, dict)
    }
    if old_build_id not in builds or new_build_id not in builds:
        raise CandidateCarryForwardError(
            "old/new build must exist in canonical class lineage"
        )
    old_sha = str(builds[old_build_id].get("sha256", "")).lower()
    new_sha = str(builds[new_build_id].get("sha256", "")).lower()
    if str(review.get("source_sha256", "")).lower() != old_sha:
        raise CandidateCarryForwardError(
            "review SHA-256 does not match old canonical build"
        )

    class_by_id = {
        str(row.get("logical_id")): row
        for row in class_lineage.get("classes", [])
        if isinstance(row, dict)
    }
    member_by_id = {
        str(row.get("member_id")): row
        for row in member_lineage.get("members", [])
        if isinstance(row, dict)
    }

    partitions = {
        "classes": {
            "carried": [],
            "blocked_missing_new_identity": [],
        },
        "fields": {
            "carried": [],
            "blocked_missing_new_identity": [],
        },
        "methods": {
            "carried": [],
            "blocked_missing_new_identity": [],
        },
    }
    seen: set[str] = set()

    proposals = review.get("proposals")
    if not isinstance(proposals, list):
        raise CandidateCarryForwardError(
            "review proposals must be an array"
        )

    for proposal in proposals:
        if not isinstance(proposal, dict):
            raise CandidateCarryForwardError(
                "review proposal must be an object"
            )
        proposal_id = proposal.get("proposal_id")
        if not isinstance(proposal_id, str) or not proposal_id:
            raise CandidateCarryForwardError(
                "review proposal has no proposal_id"
            )
        if proposal_id in seen:
            raise CandidateCarryForwardError(
                f"duplicate proposal_id {proposal_id!r}"
            )
        seen.add(proposal_id)

        kind = proposal.get("target_kind")
        stable_id = str(proposal.get("stable_id", ""))
        if kind == "class":
            record = class_by_id.get(stable_id)
            partition = partitions["classes"]
        elif kind in {"field", "method"}:
            record = member_by_id.get(stable_id)
            partition = partitions[kind + "s"]
            if record is not None and record.get("kind") != kind:
                raise CandidateCarryForwardError(
                    f"{stable_id}: proposal/member kind mismatch"
                )
        else:
            raise CandidateCarryForwardError(
                f"unsupported proposal target kind {kind!r}"
            )

        if record is None:
            raise CandidateCarryForwardError(
                f"unknown stable target {stable_id!r}"
            )
        if not _has_build(record, old_build_id):
            raise CandidateCarryForwardError(
                f"{stable_id}: reviewed target has no old-build identity"
            )

        row = {
            "proposal_id": proposal_id,
            "stable_id": stable_id,
            "proposed_name": proposal.get("proposed_name"),
            "confidence": proposal.get("confidence"),
        }
        if _has_build(record, new_build_id):
            partition["carried"].append(row)
        else:
            partition["blocked_missing_new_identity"].append(row)

    for partition in partitions.values():
        for key in partition:
            partition[key].sort(
                key=lambda row: (
                    str(row.get("stable_id", "")),
                    str(row.get("proposal_id", "")),
                )
            )

    carried = sum(
        len(partition["carried"])
        for partition in partitions.values()
    )
    blocked = sum(
        len(partition["blocked_missing_new_identity"])
        for partition in partitions.values()
    )

    return {
        "schema_version": 1,
        "kind": "semantic_candidate_carryforward_projection",
        "canonical": False,
        "review_id": review.get("review_id"),
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "proposal_count": len(proposals),
        "all_reviewed_candidates_have_new_identity": blocked == 0,
        "summary": {
            "candidate_carried": carried,
            "candidate_blocked_missing_new_identity": blocked,
            "classes_carried": len(partitions["classes"]["carried"]),
            "classes_blocked": len(
                partitions["classes"][
                    "blocked_missing_new_identity"
                ]
            ),
            "fields_carried": len(partitions["fields"]["carried"]),
            "fields_blocked": len(
                partitions["fields"][
                    "blocked_missing_new_identity"
                ]
            ),
            "methods_carried": len(partitions["methods"]["carried"]),
            "methods_blocked": len(
                partitions["methods"][
                    "blocked_missing_new_identity"
                ]
            ),
        },
        **partitions,
    }
