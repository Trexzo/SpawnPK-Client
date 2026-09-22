from __future__ import annotations

import hashlib


_CANONICALIZER_SUPPORTED = {
    "exact_sha256",
    "structural_unique",
    "weighted_mutual_best",
}


def _relationship_id(
    old_build: str,
    old_path: str,
    new_build: str,
    new_path: str,
) -> str:
    raw = f"{old_build}:{old_path}->{new_build}:{new_path}".encode("utf-8")
    return "REL_" + hashlib.sha256(raw).hexdigest()[:16].upper()


def _research_only(match: dict) -> dict:
    return {
        "old": match["old"],
        "proposed_new": match["new"],
        "reason": "strategy_requires_integration_review",
        "strategy": match["strategy"],
        "score": match["score"],
        "confidence": match["confidence"],
        "evidence": match["evidence"],
    }


def build_lineage_candidates(
    old_index: dict,
    new_index: dict,
    match_report: dict,
    *,
    old_build: str | int,
    new_build: str | int,
) -> dict:
    """Translate matcher output into research candidates, not canonical IDs.

    The integration chat owns canonical logical IDs and persistent schema. Chat 2
    emits deterministic identity relationships plus evidence for canonicalization.

    Strategies not yet supported by the main-chat canonicalizer are deliberately
    withheld from relationships and retained as research/unresolved evidence.
    """
    old_build_s, new_build_s = str(old_build), str(new_build)
    relationships = []
    research_only = []
    unresolved = list(match_report.get("ambiguous", []))

    for match in match_report.get("matches", []):
        if match.get("strategy") not in _CANONICALIZER_SUPPORTED:
            item = _research_only(match)
            research_only.append(item)
            unresolved.append(item)
            continue

        old_path, new_path = match["old"], match["new"]
        renamed = old_path != new_path
        old_entry = old_index.get("entries", {}).get(old_path, {})
        new_entry = new_index.get("entries", {}).get(new_path, {})
        byte_identical = bool(old_entry.get("sha256")) and (
            old_entry.get("sha256") == new_entry.get("sha256")
        )
        relationships.append(
            {
                "relationship_id": _relationship_id(
                    old_build_s,
                    old_path,
                    new_build_s,
                    new_path,
                ),
                "canonical_logical_id": None,
                "from": {"build": old_build_s, "path": old_path},
                "to": {"build": new_build_s, "path": new_path},
                "classification": (
                    "unchanged"
                    if byte_identical and not renamed
                    else "renamed_only"
                    if byte_identical and renamed
                    else "modified_or_reobfuscated"
                ),
                "strategy": match["strategy"],
                "confidence": match["confidence"],
                "score": match["score"],
                "evidence": match["evidence"],
            }
        )

    relationships.sort(
        key=lambda r: (r["from"]["path"], r["to"]["path"])
    )
    research_only.sort(
        key=lambda r: (r["old"], r["proposed_new"])
    )
    return {
        "schema_version": 1,
        "kind": "lineage_candidates",
        "canonicalization_owner": "main_integration_chat",
        "old_sha256": old_index.get("sha256"),
        "new_sha256": new_index.get("sha256"),
        "old_build": old_build_s,
        "new_build": new_build_s,
        "relationships": relationships,
        "research_only": research_only,
        "ambiguous": unresolved,
        "unmatched_old": match_report.get("unmatched_old", []),
        "unmatched_new": match_report.get("unmatched_new", []),
    }
