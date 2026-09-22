from __future__ import annotations

from collections import defaultdict
from typing import Any

from .lineage import validate_lineage
from .semantic_candidates import validate_semantic_candidate


class MemberSemanticBridgeError(ValueError):
    pass


def _owner_map(
    lineage: dict[str, Any],
    build_id: str,
) -> dict[str, str]:
    owners = {}
    for record in lineage.get("classes", []):
        logical_id = record.get("logical_id")
        for entry in record.get("lineage", []):
            if entry.get("build_id") != build_id:
                continue
            internal = entry.get("internal_name")
            if not isinstance(internal, str):
                continue
            if internal in owners:
                raise MemberSemanticBridgeError(
                    f"duplicate owner {internal!r} in {build_id!r}"
                )
            owners[internal] = logical_id
    return owners


def build_member_remap_proposals(
    lineage: dict[str, Any],
    semantic_set: dict[str, Any],
    *,
    build_id: str,
    minimum_confidence: float = 0.90,
) -> dict[str, Any]:
    """Resolve member semantic candidates to stable owner logical IDs.

    Output is research-only. It is deliberately not an executable R2C plan.
    """
    validate_lineage(lineage)
    if (
        semantic_set.get("schema_version") != 1
        or semantic_set.get("kind") != "semantic_candidate_set"
        or semantic_set.get("canonical") is not False
    ):
        raise MemberSemanticBridgeError(
            "expected explicit non-canonical semantic_candidate_set"
        )
    if (
        not isinstance(minimum_confidence, (int, float))
        or isinstance(minimum_confidence, bool)
        or not 0.0 <= float(minimum_confidence) <= 1.0
    ):
        raise MemberSemanticBridgeError(
            "minimum_confidence must be numeric in [0,1]"
        )

    builds = {
        row.get("build_id"): row
        for row in lineage.get("builds", [])
        if isinstance(row, dict)
    }
    if build_id not in builds:
        raise MemberSemanticBridgeError(
            f"unknown build {build_id!r}"
        )

    owners = _owner_map(lineage, build_id)
    proposals = []
    unresolved = []
    method_targets: set[tuple[str, str, str]] = set()
    field_targets: set[tuple[str, str]] = set()

    for candidate in semantic_set.get("candidates", []):
        validate_semantic_candidate(candidate)
        target = candidate["target"]
        kind = target.get("kind")
        if kind not in {"method", "field"}:
            continue
        if candidate.get("source_build") != build_id:
            unresolved.append(
                {
                    "reason": "candidate_build_mismatch",
                    "candidate": candidate,
                }
            )
            continue
        confidence = float(candidate["confidence"])
        if confidence < float(minimum_confidence):
            unresolved.append(
                {
                    "reason": "below_minimum_confidence",
                    "candidate": candidate,
                }
            )
            continue

        owner = target.get("owner")
        logical_id = owners.get(owner)
        if logical_id is None:
            unresolved.append(
                {
                    "reason": "owner_not_in_canonical_build",
                    "candidate": candidate,
                }
            )
            continue

        source_name = target.get("name")
        descriptor = target.get("descriptor")
        proposed_name = candidate["proposed_name"]

        if kind == "method":
            collision_key = (
                logical_id,
                proposed_name,
                descriptor,
            )
            if collision_key in method_targets:
                unresolved.append(
                    {
                        "reason": "method_target_collision",
                        "candidate": candidate,
                    }
                )
                continue
            method_targets.add(collision_key)
        else:
            collision_key = (
                logical_id,
                proposed_name,
            )
            if collision_key in field_targets:
                unresolved.append(
                    {
                        "reason": "field_target_collision",
                        "candidate": candidate,
                    }
                )
                continue
            field_targets.add(collision_key)

        proposals.append(
            {
                "owner_logical_id": logical_id,
                "owner_internal_name": owner,
                "member_kind": kind,
                "source_name": source_name,
                "source_descriptor": descriptor,
                "proposed_name": proposed_name,
                "confidence": confidence,
                "provenance": [
                    {
                        "source": "semantic_name_candidate",
                        "source_build": candidate["source_build"],
                        "source_sha256": candidate["source_sha256"],
                        "evidence": candidate["evidence"],
                    }
                ],
            }
        )

    proposals.sort(
        key=lambda row: (
            row["owner_logical_id"],
            row["member_kind"],
            row["source_name"],
            row["source_descriptor"],
        )
    )
    return {
        "schema_version": 1,
        "kind": "member_remap_proposals",
        "canonical": False,
        "build_id": build_id,
        "source_sha256": builds[build_id]["sha256"],
        "minimum_confidence": float(minimum_confidence),
        "proposal_count": len(proposals),
        "proposals": proposals,
        "unresolved": unresolved,
    }
