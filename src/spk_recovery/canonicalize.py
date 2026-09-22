from __future__ import annotations

import copy
from typing import Any

from .lineage import (
    ALLOWED_AUTHORITIES,
    LineageValidationError,
    validate_lineage,
)


class CandidateApplicationError(LineageValidationError):
    pass


def _require_sha_match(actual: Any, expected: Any, *, label: str) -> None:
    if not isinstance(actual, str) or not isinstance(expected, str):
        raise CandidateApplicationError(f"{label}: missing SHA-256")
    if actual.lower() != expected.lower():
        raise CandidateApplicationError(
            f"{label}: SHA-256 mismatch actual={actual} expected={expected}"
        )


def _build(doc: dict[str, Any], build_id: str) -> dict[str, Any]:
    matches = [b for b in doc.get("builds", []) if b.get("build_id") == build_id]
    if len(matches) != 1:
        raise CandidateApplicationError(
            f"expected exactly one canonical build {build_id!r}, found {len(matches)}"
        )
    return matches[0]


def _logical_path_map(doc: dict[str, Any], build_id: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for record in doc.get("classes", []):
        for entry in record.get("lineage", []):
            if entry.get("build_id") != build_id:
                continue
            path = entry.get("entry_path")
            if path in out:
                raise CandidateApplicationError(
                    f"canonical lineage has duplicate path for {build_id}: {path}"
                )
            out[path] = record
    return out


def _class_and_hashes(
    index: dict[str, Any], path: str, *, label: str
) -> tuple[dict[str, Any], str, str]:
    cls = index.get("classes", {}).get(path)
    if not isinstance(cls, dict):
        raise CandidateApplicationError(f"{label}: class path not present in index: {path}")
    entry = index.get("entries", {}).get(path)
    if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str):
        raise CandidateApplicationError(f"{label}: entry SHA missing for {path}")
    structural = cls.get("structural_sha256")
    if not isinstance(structural, str):
        raise CandidateApplicationError(f"{label}: structural SHA missing for {path}")
    return cls, entry["sha256"].lower(), structural.lower()


def _strategy_relation_and_authority(strategy: str) -> tuple[str, str]:
    if strategy == "exact_sha256":
        return "EXACT_HASH", "CROSS_BUILD"
    if strategy == "structural_unique":
        return "STRUCTURAL", "CROSS_BUILD"
    if strategy == "weighted_mutual_best":
        return "STRUCTURAL", "INFERENCE"
    raise CandidateApplicationError(f"unsupported matcher strategy {strategy!r}")


def _score(value: Any, *, strategy: str, minimum_weighted_score: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise CandidateApplicationError(f"{strategy}: candidate score must be numeric")
    score = float(value)
    if not 0.0 <= score <= 1.0:
        raise CandidateApplicationError(
            f"{strategy}: candidate score outside [0,1]: {score}"
        )
    if strategy == "exact_sha256" and score != 1.0:
        raise CandidateApplicationError("exact_sha256 candidate must have score 1.0")
    if strategy == "structural_unique" and score < 0.99:
        raise CandidateApplicationError(
            f"structural_unique score is unexpectedly weak: {score}"
        )
    if strategy == "weighted_mutual_best" and score < minimum_weighted_score:
        raise CandidateApplicationError(
            f"weighted candidate score {score} is below minimum {minimum_weighted_score}"
        )
    return score


def apply_lineage_candidates(
    lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    candidates: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
    new_build_number: int | None,
    new_authority: str,
    minimum_weighted_score: float = 0.88,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Apply matcher candidates to a canonical lineage document.

    Candidate reports are treated as untrusted research output: all referenced paths,
    exact hashes, structural hashes and baseline ownership are re-verified against the
    supplied indexes and canonical lineage before any relation is added.
    """
    validate_lineage(lineage)
    if (
        candidates.get("schema_version") != 1
        or candidates.get("kind") != "lineage_candidates"
    ):
        raise CandidateApplicationError("unsupported candidate report schema/kind")
    if new_authority not in ALLOWED_AUTHORITIES:
        raise CandidateApplicationError(
            f"unsupported new build authority {new_authority!r}"
        )
    if new_build_id == old_build_id:
        raise CandidateApplicationError("new_build_id must differ from old_build_id")
    if any(b.get("build_id") == new_build_id for b in lineage.get("builds", [])):
        raise CandidateApplicationError(
            f"build {new_build_id!r} already exists in canonical lineage"
        )

    old_build = _build(lineage, old_build_id)
    _require_sha_match(
        old_index.get("sha256"),
        old_build.get("sha256"),
        label="old index vs canonical build",
    )
    _require_sha_match(
        candidates.get("old_sha256"),
        old_index.get("sha256"),
        label="candidate old index",
    )
    _require_sha_match(
        candidates.get("new_sha256"),
        new_index.get("sha256"),
        label="candidate new index",
    )

    out = copy.deepcopy(lineage)
    old_paths = _logical_path_map(out, old_build_id)
    used_new_paths: set[str] = set()
    used_logical_ids: set[str] = set()
    applied = 0

    relationships = candidates.get("relationships")
    if not isinstance(relationships, list):
        raise CandidateApplicationError("candidate relationships must be an array")

    for i, rel in enumerate(relationships):
        label = f"relationships[{i}]"
        if not isinstance(rel, dict):
            raise CandidateApplicationError(f"{label} must be an object")
        from_obj, to_obj = rel.get("from"), rel.get("to")
        if not isinstance(from_obj, dict) or not isinstance(to_obj, dict):
            raise CandidateApplicationError(f"{label}: from/to must be objects")
        old_path, new_path = from_obj.get("path"), to_obj.get("path")
        if not isinstance(old_path, str) or not isinstance(new_path, str):
            raise CandidateApplicationError(
                f"{label}: from/to paths must be strings"
            )
        record = old_paths.get(old_path)
        if record is None:
            raise CandidateApplicationError(
                f"{label}: old path {old_path!r} is not owned by canonical build "
                f"{old_build_id!r}"
            )
        logical_id = record["logical_id"]
        if logical_id in used_logical_ids:
            raise CandidateApplicationError(
                f"{label}: logical class {logical_id} matched more than once"
            )
        if new_path in used_new_paths:
            raise CandidateApplicationError(
                f"{label}: new path {new_path!r} matched more than once"
            )

        _, old_entry_sha, old_structural = _class_and_hashes(
            old_index, old_path, label=label + ".old"
        )
        new_class, new_entry_sha, new_structural = _class_and_hashes(
            new_index, new_path, label=label + ".new"
        )
        strategy = rel.get("strategy")
        if not isinstance(strategy, str):
            raise CandidateApplicationError(f"{label}: strategy must be a string")
        relation, evidence_authority = _strategy_relation_and_authority(strategy)
        score = _score(
            rel.get("score"),
            strategy=strategy,
            minimum_weighted_score=minimum_weighted_score,
        )

        if strategy == "exact_sha256" and old_entry_sha != new_entry_sha:
            raise CandidateApplicationError(
                f"{label}: exact_sha256 candidate bytes are not equal"
            )
        if strategy == "structural_unique" and old_structural != new_structural:
            raise CandidateApplicationError(
                f"{label}: structural_unique fingerprints are not equal"
            )

        internal_name = new_class.get("internal_name")
        if not isinstance(internal_name, str) or new_path != internal_name + ".class":
            raise CandidateApplicationError(
                f"{label}: new index internal name/path mismatch"
            )

        record["lineage"].append(
            {
                "build_id": new_build_id,
                "internal_name": internal_name,
                "entry_path": new_path,
                "entry_sha256": new_entry_sha,
                "structural_sha256": new_structural,
                "relation": relation,
                "confidence": score,
                "provenance": [
                    {
                        "authority": evidence_authority,
                        "source": str(
                            rel.get("relationship_id") or f"candidate-{i}"
                        ),
                        "note": (
                            f"Imported from matcher strategy {strategy}; "
                            "canonicalizer re-verified source indexes."
                        ),
                    }
                ],
            }
        )
        used_logical_ids.add(logical_id)
        used_new_paths.add(new_path)
        applied += 1

    out["builds"].append(
        {
            "build_id": new_build_id,
            "build_number": new_build_number,
            "sha256": str(new_index.get("sha256", "")).lower(),
            "source_name": str(new_index.get("source_name", "")),
            "authority": new_authority,
        }
    )

    unresolved_added = 0
    for kind in ("ambiguous", "unmatched_old", "unmatched_new"):
        values = candidates.get(kind, [])
        if not isinstance(values, list):
            raise CandidateApplicationError(
                f"candidate {kind} must be an array"
            )
        for value in values:
            out["unresolved"].append(
                {
                    "old_build_id": old_build_id,
                    "new_build_id": new_build_id,
                    "kind": kind,
                    "candidate": copy.deepcopy(value),
                    "source": "lineage_candidates",
                }
            )
            unresolved_added += 1

    summary = dict(validate_lineage(out))
    summary.update(
        {
            "applied_relationships": applied,
            "unresolved_added": unresolved_added,
        }
    )
    return out, summary
