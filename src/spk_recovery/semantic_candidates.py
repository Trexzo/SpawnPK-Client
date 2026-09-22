from __future__ import annotations

from collections import defaultdict
import math
import re
from typing import Any


_IDENTIFIER = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")

_EVIDENCE_STRENGTH = {
    "exact_packet_behavior": 0.92,
    "exact_command_behavior": 0.92,
    "exact_literal_role": 0.78,
    "exact_resource_role": 0.82,
    "exact_renderer_join": 0.88,
    "exact_field_flow": 0.90,
    "structural_lineage": 0.82,
    "cross_build_persistence": 0.78,
    "research_crosslink": 0.75,
    "type_shape": 0.45,
    "nearby_string": 0.35,
}


class SemanticCandidateError(ValueError):
    pass


def score_semantic_evidence(evidence: list[dict[str, Any]]) -> float:
    """Combine independent evidence families without claiming certainty.

    Repeated evidence from the same family contributes only its strongest signal.
    Scores are capped below 1.0 because proposed English names are inferred names,
    not recovered original identifiers.
    """
    strongest: dict[str, float] = {}
    for item in evidence:
        family = str(item.get("family", ""))
        if family not in _EVIDENCE_STRENGTH:
            raise SemanticCandidateError(
                f"unsupported semantic evidence family {family!r}"
            )
        weight = float(item.get("weight", _EVIDENCE_STRENGTH[family]))
        if not 0.0 <= weight <= 1.0:
            raise SemanticCandidateError(
                f"evidence weight outside [0,1]: {weight}"
            )
        strongest[family] = max(strongest.get(family, 0.0), weight)

    miss_probability = 1.0
    for weight in strongest.values():
        miss_probability *= 1.0 - weight
    return round(min(0.995, 1.0 - miss_probability), 6)


def _target_key(target: dict[str, Any]) -> tuple[Any, ...]:
    return (
        target.get("kind"),
        target.get("owner"),
        target.get("name"),
        target.get("descriptor"),
    )


def validate_semantic_candidate(candidate: dict[str, Any]) -> None:
    if candidate.get("schema_version") != 1:
        raise SemanticCandidateError("schema_version must be 1")
    if candidate.get("kind") != "semantic_name_candidate":
        raise SemanticCandidateError(
            "kind must be semantic_name_candidate"
        )
    target = candidate.get("target")
    if not isinstance(target, dict):
        raise SemanticCandidateError("target must be an object")
    if target.get("kind") not in {"class", "method", "field"}:
        raise SemanticCandidateError("unsupported target kind")
    if not isinstance(target.get("owner"), str) or not target["owner"]:
        raise SemanticCandidateError("target owner must be non-empty")
    if target["kind"] != "class":
        if not isinstance(target.get("name"), str) or not target["name"]:
            raise SemanticCandidateError(
                "member target name must be non-empty"
            )
        if not isinstance(target.get("descriptor"), str):
            raise SemanticCandidateError(
                "member descriptor must be a string"
            )

    proposed = candidate.get("proposed_name")
    if not isinstance(proposed, str) or not _IDENTIFIER.fullmatch(proposed):
        raise SemanticCandidateError(
            f"invalid proposed Java identifier {proposed!r}"
        )
    if candidate.get("status") != "CANDIDATE":
        raise SemanticCandidateError(
            "Chat 2 semantic output must remain CANDIDATE"
        )
    evidence = candidate.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise SemanticCandidateError(
            "semantic candidate needs evidence"
        )
    expected = score_semantic_evidence(evidence)
    score = candidate.get("confidence")
    if not isinstance(score, (int, float)):
        raise SemanticCandidateError("confidence must be numeric")
    if abs(float(score) - expected) > 1e-9:
        raise SemanticCandidateError(
            f"confidence {score} != evidence score {expected}"
        )


def make_semantic_candidate(
    *,
    target: dict[str, Any],
    proposed_name: str,
    evidence: list[dict[str, Any]],
    source_build: str,
    source_sha256: str,
    note: str = "",
) -> dict[str, Any]:
    candidate = {
        "schema_version": 1,
        "kind": "semantic_name_candidate",
        "canonical": False,
        "status": "CANDIDATE",
        "source_build": source_build,
        "source_sha256": source_sha256,
        "target": dict(target),
        "proposed_name": proposed_name,
        "confidence": score_semantic_evidence(evidence),
        "evidence": list(evidence),
        "note": note,
    }
    validate_semantic_candidate(candidate)
    return candidate


def merge_semantic_candidates(
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge identical proposals and expose conflicts instead of choosing."""
    grouped: dict[
        tuple[tuple[Any, ...], str],
        list[dict[str, Any]],
    ] = defaultdict(list)
    target_names: dict[tuple[Any, ...], set[str]] = defaultdict(set)

    for candidate in candidates:
        validate_semantic_candidate(candidate)
        target_key = _target_key(candidate["target"])
        proposed = candidate["proposed_name"]
        grouped[(target_key, proposed)].append(candidate)
        target_names[target_key].add(proposed)

    merged = []
    for (target_key, proposed), rows in grouped.items():
        all_evidence = []
        seen = set()
        for row in rows:
            for item in row["evidence"]:
                marker = repr(sorted(item.items()))
                if marker in seen:
                    continue
                seen.add(marker)
                all_evidence.append(item)
        first = rows[0]
        merged.append(
            make_semantic_candidate(
                target=first["target"],
                proposed_name=proposed,
                evidence=all_evidence,
                source_build=first["source_build"],
                source_sha256=first["source_sha256"],
                note=first.get("note", ""),
            )
        )

    conflicts = [
        {
            "target": {
                "kind": key[0],
                "owner": key[1],
                "name": key[2],
                "descriptor": key[3],
            },
            "proposals": sorted(names),
        }
        for key, names in target_names.items()
        if len(names) > 1
    ]
    merged.sort(
        key=lambda row: (
            row["target"]["owner"],
            row["target"].get("kind", ""),
            str(row["target"].get("name", "")),
            str(row["target"].get("descriptor", "")),
            row["proposed_name"],
        )
    )
    return {
        "schema_version": 1,
        "kind": "semantic_candidate_set",
        "canonical": False,
        "candidates": merged,
        "conflicts": conflicts,
    }
