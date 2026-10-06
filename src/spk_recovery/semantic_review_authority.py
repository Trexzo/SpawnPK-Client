from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from .lineage import LineageValidationError, validate_lineage
from .member_lineage import MemberLineageError, validate_member_lineage
from .semantic_authority import (
    SEMANTIC_PROPOSAL_ID_RE,
    SEMANTIC_REVIEW_ID_RE,
    is_semantic_identifier,
    semantic_proposal_id,
)
from .semantic_review import semantic_review_id


class SemanticReviewAuthorityError(ValueError):
    pass


_REGISTRY_ID_RE = re.compile(r"^SEMREGAUTH_[0-9A-F]{20}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _registry_id(reviews: list[dict[str, Any]]) -> str:
    canonical = sorted(
        reviews,
        key=lambda row: row["review_set"]["review_id"],
    )
    return (
        "SEMREGAUTH_"
        + hashlib.sha256(_stable_json(canonical)).hexdigest()[:20].upper()
    )


def _validate_review_authority_entry(
    entry: Any,
    *,
    label: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(entry, dict):
        raise SemanticReviewAuthorityError(f"{label} must be an object")

    review = entry.get("review_set")
    acceptance = entry.get("acceptance_spec")
    if not isinstance(review, dict):
        raise SemanticReviewAuthorityError(
            f"{label}.review_set must be an object"
        )
    if not isinstance(acceptance, dict):
        raise SemanticReviewAuthorityError(
            f"{label}.acceptance_spec must be an object"
        )

    if review.get("schema_version") != 1:
        raise SemanticReviewAuthorityError(
            f"{label}.review_set schema_version must be 1"
        )
    if review.get("kind") != "semantic_review_set":
        raise SemanticReviewAuthorityError(
            f"{label}.review_set kind must be semantic_review_set"
        )
    if review.get("canonical") is not False:
        raise SemanticReviewAuthorityError(
            f"{label}.review_set must be explicitly non-canonical"
        )

    source_build = review.get("source_build")
    source_sha = str(review.get("source_sha256", "")).lower()
    if not isinstance(source_build, str) or not source_build:
        raise SemanticReviewAuthorityError(
            f"{label}.review_set source_build must be non-empty"
        )
    if _SHA256_RE.fullmatch(source_sha) is None:
        raise SemanticReviewAuthorityError(
            f"{label}.review_set source_sha256 is invalid"
        )

    proposals = review.get("proposals")
    unresolved = review.get("unresolved")
    if not isinstance(proposals, list):
        raise SemanticReviewAuthorityError(
            f"{label}.review_set proposals must be an array"
        )
    if not isinstance(unresolved, list):
        raise SemanticReviewAuthorityError(
            f"{label}.review_set unresolved must be an array"
        )
    if unresolved:
        raise SemanticReviewAuthorityError(
            f"{label}.review_set must have zero unresolved candidates"
        )
    if review.get("proposal_count") != len(proposals):
        raise SemanticReviewAuthorityError(
            f"{label}.review_set proposal_count mismatch"
        )

    seen_proposals: set[str] = set()
    for ordinal, proposal in enumerate(proposals):
        plabel = f"{label}.review_set.proposals[{ordinal}]"
        if not isinstance(proposal, dict):
            raise SemanticReviewAuthorityError(
                f"{plabel} must be an object"
            )

        proposal_id = proposal.get("proposal_id")
        target_kind = proposal.get("target_kind")
        stable_id = proposal.get("stable_id")
        proposed_name = proposal.get("proposed_name")
        confidence = proposal.get("confidence")
        proposal_source_build = proposal.get("source_build")
        proposal_source_sha = str(
            proposal.get("source_sha256", "")
        ).lower()
        source_coordinate = proposal.get("source_coordinate")
        evidence = proposal.get("evidence")

        if (
            not isinstance(proposal_id, str)
            or SEMANTIC_PROPOSAL_ID_RE.fullmatch(proposal_id) is None
        ):
            raise SemanticReviewAuthorityError(
                f"{plabel}.proposal_id is invalid"
            )
        if proposal_id in seen_proposals:
            raise SemanticReviewAuthorityError(
                f"{label}.review_set contains duplicate proposal "
                f"{proposal_id}"
            )
        seen_proposals.add(proposal_id)

        if target_kind not in {"class", "field", "method"}:
            raise SemanticReviewAuthorityError(
                f"{plabel}.target_kind is unsupported"
            )
        if not isinstance(stable_id, str) or not stable_id:
            raise SemanticReviewAuthorityError(
                f"{plabel}.stable_id must be non-empty"
            )
        owner_logical_id = proposal.get("owner_logical_id")
        if (
            not isinstance(owner_logical_id, str)
            or not owner_logical_id
        ):
            raise SemanticReviewAuthorityError(
                f"{plabel}.owner_logical_id must be non-empty"
            )
        if (
            target_kind == "class"
            and owner_logical_id != stable_id
        ):
            raise SemanticReviewAuthorityError(
                f"{plabel}.owner_logical_id does not match class stable ID"
            )
        if not is_semantic_identifier(proposed_name):
            raise SemanticReviewAuthorityError(
                f"{plabel}.proposed_name is invalid"
            )
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= float(confidence) <= 1.0
        ):
            raise SemanticReviewAuthorityError(
                f"{plabel}.confidence is invalid"
            )
        if proposal_source_build != source_build:
            raise SemanticReviewAuthorityError(
                f"{plabel}.source_build does not match review"
            )
        if proposal_source_sha != source_sha:
            raise SemanticReviewAuthorityError(
                f"{plabel}.source_sha256 does not match review"
            )
        if not isinstance(source_coordinate, dict):
            raise SemanticReviewAuthorityError(
                f"{plabel}.source_coordinate must be an object"
            )
        if not isinstance(evidence, list):
            raise SemanticReviewAuthorityError(
                f"{plabel}.evidence must be an array"
            )

        expected_proposal = semantic_proposal_id(
            source_sha,
            str(target_kind),
            stable_id,
            str(proposed_name),
        )
        if proposal_id != expected_proposal:
            raise SemanticReviewAuthorityError(
                f"{plabel}.proposal_id does not match proposal material"
            )

    review_id = review.get("review_id")
    if (
        not isinstance(review_id, str)
        or SEMANTIC_REVIEW_ID_RE.fullmatch(review_id) is None
    ):
        raise SemanticReviewAuthorityError(
            f"{label}.review_set review_id is invalid"
        )
    if semantic_review_id(proposals) != review_id:
        raise SemanticReviewAuthorityError(
            f"{label}.review_set review_id does not match complete proposals"
        )

    if acceptance.get("schema_version") != 1:
        raise SemanticReviewAuthorityError(
            f"{label}.acceptance_spec schema_version must be 1"
        )
    if acceptance.get("kind") != "semantic_acceptance_spec":
        raise SemanticReviewAuthorityError(
            f"{label}.acceptance_spec kind must be semantic_acceptance_spec"
        )
    if acceptance.get("review_id") != review_id:
        raise SemanticReviewAuthorityError(
            f"{label}.acceptance_spec review_id mismatch"
        )

    accepted = acceptance.get("accept")
    if (
        not isinstance(accepted, list)
        or not accepted
        or any(not isinstance(value, str) for value in accepted)
    ):
        raise SemanticReviewAuthorityError(
            f"{label}.acceptance_spec accept must be a non-empty "
            "string array"
        )
    if len(set(accepted)) != len(accepted):
        raise SemanticReviewAuthorityError(
            f"{label}.acceptance_spec contains duplicate proposal IDs"
        )
    unknown = sorted(set(accepted) - seen_proposals)
    if unknown:
        raise SemanticReviewAuthorityError(
            f"{label}.acceptance_spec references unknown proposals: "
            f"{unknown}"
        )

    return review, acceptance


def build_semantic_review_authority_registry(
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a deterministic registry from complete reviews and acceptances."""
    if not isinstance(entries, list) or not entries:
        raise SemanticReviewAuthorityError(
            "semantic review authority entries must be non-empty"
        )

    trusted: list[dict[str, Any]] = []
    seen_reviews: set[str] = set()
    for ordinal, entry in enumerate(entries):
        review, acceptance = _validate_review_authority_entry(
            entry,
            label=f"entries[{ordinal}]",
        )
        review_id = str(review["review_id"])
        if review_id in seen_reviews:
            raise SemanticReviewAuthorityError(
                f"duplicate trusted semantic review {review_id}"
            )
        seen_reviews.add(review_id)
        trusted.append(
            {
                "review_set": copy.deepcopy(review),
                "acceptance_spec": copy.deepcopy(acceptance),
            }
        )

    trusted.sort(key=lambda row: row["review_set"]["review_id"])
    return {
        "schema_version": 1,
        "kind": "semantic_review_authority_registry",
        "registry_id": _registry_id(trusted),
        "review_count": len(trusted),
        "accepted_proposal_count": sum(
            len(row["acceptance_spec"]["accept"])
            for row in trusted
        ),
        "reviews": trusted,
    }


def validate_semantic_review_authority_registry(
    registry: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(registry, dict):
        raise SemanticReviewAuthorityError(
            "semantic review authority registry must be an object"
        )
    if registry.get("schema_version") != 1:
        raise SemanticReviewAuthorityError(
            "semantic review authority registry schema_version must be 1"
        )
    if registry.get("kind") != "semantic_review_authority_registry":
        raise SemanticReviewAuthorityError(
            "semantic review authority registry kind mismatch"
        )

    reviews = registry.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        raise SemanticReviewAuthorityError(
            "semantic review authority registry reviews must be non-empty"
        )

    seen_reviews: set[str] = set()
    accepted_count = 0
    review_ids: list[str] = []
    for ordinal, entry in enumerate(reviews):
        review, acceptance = _validate_review_authority_entry(
            entry,
            label=f"reviews[{ordinal}]",
        )
        review_id = str(review["review_id"])
        if review_id in seen_reviews:
            raise SemanticReviewAuthorityError(
                f"duplicate trusted semantic review {review_id}"
            )
        seen_reviews.add(review_id)
        review_ids.append(review_id)
        accepted_count += len(acceptance["accept"])

    if review_ids != sorted(review_ids):
        raise SemanticReviewAuthorityError(
            "semantic review authority registry reviews are not canonical"
        )
    if registry.get("review_count") != len(reviews):
        raise SemanticReviewAuthorityError(
            "semantic review authority registry review_count mismatch"
        )
    if registry.get("accepted_proposal_count") != accepted_count:
        raise SemanticReviewAuthorityError(
            "semantic review authority registry accepted proposal count "
            "mismatch"
        )

    registry_id = registry.get("registry_id")
    if (
        not isinstance(registry_id, str)
        or _REGISTRY_ID_RE.fullmatch(registry_id) is None
    ):
        raise SemanticReviewAuthorityError(
            "semantic review authority registry_id is invalid"
        )
    if registry_id != _registry_id(reviews):
        raise SemanticReviewAuthorityError(
            "semantic review authority registry_id does not match contents"
        )

    return {
        "registry_id": registry_id,
        "review_count": len(reviews),
        "accepted_proposal_count": accepted_count,
        "review_ids": review_ids,
    }


def _trusted_accepted_proposals(
    registry: dict[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
    validate_semantic_review_authority_registry(registry)
    trusted: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in registry["reviews"]:
        review = entry["review_set"]
        accepted = set(entry["acceptance_spec"]["accept"])
        for proposal in review["proposals"]:
            if proposal["proposal_id"] not in accepted:
                continue
            key = (review["review_id"], proposal["proposal_id"])
            trusted[key] = proposal
    return trusted


def _verify_record_provenance(
    *,
    record: dict[str, Any],
    stable_id: str,
    target_kind: str,
    owner_logical_id: str | None,
    trusted: dict[tuple[str, str], dict[str, Any]],
    label: str,
) -> tuple[int, set[str]]:
    if record.get("semantic_status") != "ACCEPTED":
        return 0, set()

    semantic_name = record.get("semantic_name")
    semantic_confidence = float(record.get("semantic_confidence"))
    provenance = record.get("semantic_provenance", [])
    verified_rows = 0
    review_ids: set[str] = set()

    for ordinal, row in enumerate(provenance):
        plabel = f"{label}.semantic_provenance[{ordinal}]"
        key = (row.get("review_id"), row.get("proposal_id"))
        proposal = trusted.get(key)
        if proposal is None:
            raise SemanticReviewAuthorityError(
                f"{plabel} is not covered by trusted accepted review authority"
            )

        if proposal.get("target_kind") != target_kind:
            raise SemanticReviewAuthorityError(
                f"{plabel} target kind does not match trusted proposal"
            )
        if proposal.get("stable_id") != stable_id:
            raise SemanticReviewAuthorityError(
                f"{plabel} stable ID does not match trusted proposal"
            )
        if (
            owner_logical_id is not None
            and proposal.get("owner_logical_id") != owner_logical_id
        ):
            raise SemanticReviewAuthorityError(
                f"{plabel} owner logical ID does not match trusted proposal"
            )
        if proposal.get("proposed_name") != semantic_name:
            raise SemanticReviewAuthorityError(
                f"{plabel} semantic name does not match trusted proposal"
            )
        if float(proposal.get("confidence")) != semantic_confidence:
            raise SemanticReviewAuthorityError(
                f"{plabel} semantic confidence does not match trusted proposal"
            )
        if proposal.get("source_build") != row.get("source_build"):
            raise SemanticReviewAuthorityError(
                f"{plabel} source build does not match trusted proposal"
            )
        if (
            str(proposal.get("source_sha256", "")).lower()
            != str(row.get("source_sha256", "")).lower()
        ):
            raise SemanticReviewAuthorityError(
                f"{plabel} source SHA does not match trusted proposal"
            )
        if proposal.get("source_coordinate") != row.get("source_coordinate"):
            raise SemanticReviewAuthorityError(
                f"{plabel} source coordinate does not match trusted proposal"
            )
        if proposal.get("evidence") != row.get("evidence"):
            raise SemanticReviewAuthorityError(
                f"{plabel} evidence does not match trusted proposal"
            )
        if proposal.get("note") != row.get("note"):
            raise SemanticReviewAuthorityError(
                f"{plabel} note does not match trusted proposal"
            )

        verified_rows += 1
        review_ids.add(str(row["review_id"]))

    if verified_rows == 0:
        raise SemanticReviewAuthorityError(
            f"{label} has no trusted accepted semantic provenance"
        )
    return verified_rows, review_ids


def verify_accepted_semantic_lineage(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    """Authenticate every ACCEPTED semantic row against trusted full reviews."""
    try:
        validate_lineage(class_lineage)
        validate_member_lineage(
            member_lineage,
            class_lineage=class_lineage,
        )
    except (LineageValidationError, MemberLineageError) as exc:
        raise SemanticReviewAuthorityError(
            f"invalid semantic lineage authority: {exc}"
        ) from exc

    registry_summary = validate_semantic_review_authority_registry(registry)
    trusted = _trusted_accepted_proposals(registry)

    accepted_classes = 0
    accepted_members = 0
    provenance_rows = 0
    used_reviews: set[str] = set()

    for ordinal, record in enumerate(class_lineage.get("classes", [])):
        if record.get("semantic_status") != "ACCEPTED":
            continue
        accepted_classes += 1
        count, reviews = _verify_record_provenance(
            record=record,
            stable_id=str(record["logical_id"]),
            target_kind="class",
            owner_logical_id=str(record["logical_id"]),
            trusted=trusted,
            label=f"classes[{ordinal}]",
        )
        provenance_rows += count
        used_reviews.update(reviews)

    for ordinal, record in enumerate(member_lineage.get("members", [])):
        if record.get("semantic_status") != "ACCEPTED":
            continue
        accepted_members += 1
        count, reviews = _verify_record_provenance(
            record=record,
            stable_id=str(record["member_id"]),
            target_kind=str(record["kind"]),
            owner_logical_id=str(record["owner_logical_id"]),
            trusted=trusted,
            label=f"members[{ordinal}]",
        )
        provenance_rows += count
        used_reviews.update(reviews)

    return {
        "registry_id": registry_summary["registry_id"],
        "trusted_review_count": registry_summary["review_count"],
        "trusted_accepted_proposal_count": registry_summary[
            "accepted_proposal_count"
        ],
        "accepted_class_records": accepted_classes,
        "accepted_member_records": accepted_members,
        "accepted_records": accepted_classes + accepted_members,
        "verified_provenance_rows": provenance_rows,
        "used_review_ids": sorted(used_reviews),
    }
