from __future__ import annotations

from typing import Any

from .lineage import validate_lineage
from .semantic_candidates import validate_semantic_candidate


class SemanticBridgeError(ValueError):
    pass


def _class_owner_map(
    lineage: dict[str, Any],
    build_id: str,
) -> dict[str, str]:
    owners: dict[str, str] = {}
    for record in lineage.get("classes", []):
        logical_id = record.get("logical_id")
        for entry in record.get("lineage", []):
            if entry.get("build_id") != build_id:
                continue
            internal = entry.get("internal_name")
            if not isinstance(internal, str) or not internal:
                continue
            if internal in owners:
                raise SemanticBridgeError(
                    f"duplicate class owner {internal!r} in build {build_id!r}"
                )
            owners[internal] = logical_id
    return owners


def build_class_remap_proposals(
    lineage: dict[str, Any],
    semantic_set: dict[str, Any],
    *,
    build_id: str,
    target_package: str = "recovered/spawnpk/client",
    minimum_confidence: float = 0.90,
) -> dict[str, Any]:
    """Bridge semantic class names to stable logical IDs as research proposals.

    The returned document is intentionally not a remap_spec. It cannot be
    consumed by the core R2A remap resolver without an explicit integration step.
    """
    validate_lineage(lineage)
    if semantic_set.get("schema_version") != 1:
        raise SemanticBridgeError("semantic set schema_version must be 1")
    if semantic_set.get("kind") != "semantic_candidate_set":
        raise SemanticBridgeError(
            "semantic set kind must be semantic_candidate_set"
        )
    if semantic_set.get("canonical") is not False:
        raise SemanticBridgeError(
            "semantic candidate set must be explicitly non-canonical"
        )
    if not isinstance(build_id, str) or not build_id:
        raise SemanticBridgeError("build_id must be non-empty")
    if (
        not isinstance(minimum_confidence, (int, float))
        or isinstance(minimum_confidence, bool)
        or not 0.0 <= float(minimum_confidence) <= 1.0
    ):
        raise SemanticBridgeError(
            "minimum_confidence must be numeric in [0,1]"
        )

    builds = {
        build.get("build_id"): build
        for build in lineage.get("builds", [])
        if isinstance(build, dict)
    }
    if build_id not in builds:
        raise SemanticBridgeError(
            f"unknown canonical build {build_id!r}"
        )

    owners = _class_owner_map(lineage, build_id)
    proposals = []
    unresolved = []
    targets: dict[str, str] = {}

    for candidate in semantic_set.get("candidates", []):
        validate_semantic_candidate(candidate)
        target = candidate["target"]
        if target.get("kind") != "class":
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
                    "reason": "class_owner_not_in_canonical_build",
                    "candidate": candidate,
                }
            )
            continue

        semantic_name = candidate["proposed_name"]
        proposed_target = (
            target_package.rstrip("/") + "/" + semantic_name
        )
        prior = targets.get(proposed_target)
        if prior is not None and prior != logical_id:
            unresolved.append(
                {
                    "reason": "proposed_target_collision",
                    "logical_id": logical_id,
                    "collides_with": prior,
                    "proposed_target_internal_name": proposed_target,
                    "candidate": candidate,
                }
            )
            continue
        targets[proposed_target] = logical_id

        proposals.append(
            {
                "logical_id": logical_id,
                "source_internal_name": owner,
                "semantic_name": semantic_name,
                "proposed_target_internal_name": proposed_target,
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

    proposals.sort(key=lambda row: row["logical_id"])
    return {
        "schema_version": 1,
        "kind": "remap_spec_proposals",
        "canonical": False,
        "build_id": build_id,
        "source_sha256": builds[build_id]["sha256"],
        "target_package": target_package.rstrip("/"),
        "minimum_confidence": float(minimum_confidence),
        "proposal_count": len(proposals),
        "proposals": proposals,
        "unresolved": unresolved,
    }
