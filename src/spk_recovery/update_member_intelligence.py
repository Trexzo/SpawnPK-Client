from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .field_relationship_audit import (
    audit_member_identity_candidate_set,
)
from .lineage import validate_lineage
from .member_identity import build_member_identity_candidates


class UpdateMemberIntelligenceError(ValueError):
    pass


def _build(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, Any]:
    hits = [
        row
        for row in class_lineage.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(hits) != 1:
        raise UpdateMemberIntelligenceError(
            f"expected one canonical build {build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _entry_for_build(
    record: dict[str, Any],
    build_id: str,
) -> dict[str, Any] | None:
    hits = [
        row
        for row in record.get("lineage", [])
        if row.get("build_id") == build_id
    ]
    if len(hits) > 1:
        raise UpdateMemberIntelligenceError(
            f"{record.get('logical_id')} has duplicate {build_id!r} entries"
        )
    return hits[0] if hits else None


def _verify_class_entry(
    index: dict[str, Any],
    entry: dict[str, Any],
    *,
    label: str,
) -> str:
    internal = entry.get("internal_name")
    path = entry.get("entry_path")
    if (
        not isinstance(internal, str)
        or not internal
        or path != internal + ".class"
    ):
        raise UpdateMemberIntelligenceError(
            f"{label}: invalid canonical class coordinate"
        )

    exact_entry = index.get("entries", {}).get(path)
    exact_class = index.get("classes", {}).get(path)
    if not isinstance(exact_entry, dict) or not isinstance(exact_class, dict):
        raise UpdateMemberIntelligenceError(
            f"{label}: exact index missing canonical class {path!r}"
        )
    if exact_class.get("internal_name") != internal:
        raise UpdateMemberIntelligenceError(
            f"{label}: exact index internal name mismatch for {path!r}"
        )

    expected_sha = str(entry.get("entry_sha256", "")).lower()
    actual_sha = str(exact_entry.get("sha256", "")).lower()
    if expected_sha != actual_sha:
        raise UpdateMemberIntelligenceError(
            f"{label}: canonical entry SHA does not match exact index"
        )

    expected_structural = str(
        entry.get("structural_sha256", "")
    ).lower()
    actual_structural = str(
        exact_class.get("structural_sha256", "")
    ).lower()
    if expected_structural != actual_structural:
        raise UpdateMemberIntelligenceError(
            f"{label}: canonical structural SHA does not match exact index"
        )
    return path


def build_canonical_member_identity_candidates(
    class_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
) -> dict[str, Any]:
    """Build R3C-ready member candidates from canonical class pairs only.

    This function does not mutate class or member lineage. It uses canonical
    class lineage as owner-identity authority and emits the existing research
    member_identity_candidates shape consumed by R3C.
    """
    validate_lineage(class_lineage)
    if old_build_id == new_build_id:
        raise UpdateMemberIntelligenceError(
            "old_build_id and new_build_id must differ"
        )

    old_build = _build(class_lineage, old_build_id)
    new_build = _build(class_lineage, new_build_id)
    old_sha = str(old_index.get("sha256", "")).lower()
    new_sha = str(new_index.get("sha256", "")).lower()

    if str(old_build.get("sha256", "")).lower() != old_sha:
        raise UpdateMemberIntelligenceError(
            "old exact index SHA does not match canonical old build"
        )
    if str(new_build.get("sha256", "")).lower() != new_sha:
        raise UpdateMemberIntelligenceError(
            "new exact index SHA does not match canonical new build"
        )

    matches: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for record in class_lineage.get("classes", []):
        logical_id = record.get("logical_id")
        old_entry = _entry_for_build(record, old_build_id)
        new_entry = _entry_for_build(record, new_build_id)

        if old_entry is None and new_entry is None:
            continue
        if old_entry is None or new_entry is None:
            skipped.append(
                {
                    "logical_id": logical_id,
                    "old": (
                        old_entry.get("entry_path")
                        if old_entry is not None
                        else None
                    ),
                    "new": (
                        new_entry.get("entry_path")
                        if new_entry is not None
                        else None
                    ),
                    "strategy": "canonical_lineage",
                    "reason": "canonical_class_missing_in_one_build",
                }
            )
            continue

        old_path = _verify_class_entry(
            old_index,
            old_entry,
            label=f"{logical_id}.{old_build_id}",
        )
        new_path = _verify_class_entry(
            new_index,
            new_entry,
            label=f"{logical_id}.{new_build_id}",
        )

        matches.append(
            {
                "old": old_path,
                "new": new_path,
                "strategy": "canonical_lineage",
                "score": 1.0,
                "confidence": "CANONICAL",
                "evidence": {
                    "logical_id": logical_id,
                    "old_relation": old_entry.get("relation"),
                    "new_relation": new_entry.get("relation"),
                    "old_confidence": old_entry.get("confidence"),
                    "new_confidence": new_entry.get("confidence"),
                },
            }
        )

    class_report = {
        "schema_version": 1,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "scope_prefix": None,
        "matches": matches,
        "ambiguous": [],
        "unmatched_old": [],
        "unmatched_new": [],
    }
    candidates = build_member_identity_candidates(
        old_index,
        new_index,
        class_report,
    )
    candidates["class_authority"] = "canonical_lineage"
    candidates["old_build_id"] = old_build_id
    candidates["new_build_id"] = new_build_id
    candidates["canonical_class_pairs"] = len(matches)

    existing_skipped = list(candidates.get("skipped_classes", []))
    candidates["skipped_classes"] = sorted(
        existing_skipped + copy.deepcopy(skipped),
        key=lambda row: (
            str(row.get("logical_id", "")),
            str(row.get("old", "")),
            str(row.get("new", "")),
        ),
    )
    candidates["summary"]["canonical_class_pairs"] = len(matches)
    candidates["summary"]["canonical_classes_skipped"] = len(skipped)
    return candidates


def build_audited_canonical_member_identity_workspace(
    class_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    *,
    old_build_id: str,
    new_build_id: str,
    min_field_position_observations: int = 2,
) -> dict[str, Any]:
    """Build canonical member candidates plus exact-JAR field conflict audit.

    This remains research-only. It gives R3 integration a single object that
    distinguishes gross candidate coverage from field relationships that are
    contradicted by stronger exact matched-method bytecode positions.
    """
    candidates = build_canonical_member_identity_candidates(
        class_lineage,
        old_index,
        new_index,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    field_audit = audit_member_identity_candidate_set(
        old_jar,
        new_jar,
        candidates,
        min_observations=min_field_position_observations,
    )

    gross_fields = int(
        candidates.get("summary", {}).get(
            "field_matched",
            0,
        )
    )
    conflicts = int(field_audit.get("conflict_count", 0))
    conservative_fields = max(0, gross_fields - conflicts)

    return {
        "schema_version": 1,
        "kind": "audited_member_identity_workspace",
        "canonical": False,
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": candidates.get("old_sha256"),
        "new_sha256": candidates.get("new_sha256"),
        "member_candidates": candidates,
        "field_position_audit": field_audit,
        "summary": {
            "method_candidates": int(
                candidates.get("summary", {}).get(
                    "method_matched",
                    0,
                )
            ),
            "gross_field_candidates": gross_fields,
            "field_position_conflicts": conflicts,
            "conflict_free_field_candidates_lower_bound": (
                conservative_fields
            ),
            "exact_position_field_matches": int(
                field_audit.get(
                    "exact_position_matches",
                    0,
                )
            ),
            "field_identity_requires_reconciliation": (
                conflicts > 0
            ),
        },
    }
