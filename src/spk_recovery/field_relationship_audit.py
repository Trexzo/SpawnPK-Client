from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .bytecode_context import profile_jar_class
from .indexer import sha256_file
from .member_identity import _descriptor_identity_shape


class FieldRelationshipAuditError(ValueError):
    pass


def _coord(row: dict[str, Any]) -> tuple[str, str]:
    return (
        str(row.get("name", "")),
        str(row.get("descriptor", "")),
    )


def _method_relation_maps(
    member_class_record: dict[str, Any],
) -> tuple[
    dict[tuple[str, str], str],
    dict[tuple[str, str], str],
]:
    old_map: dict[tuple[str, str], str] = {}
    new_map: dict[tuple[str, str], str] = {}

    methods = member_class_record.get("methods", {})
    for relation in methods.get("relationships", []):
        relation_id = relation.get("relationship_id")
        old = relation.get("old", {})
        new = relation.get("new", {})
        if not isinstance(relation_id, str) or not relation_id:
            continue
        old_map[_coord(old)] = relation_id
        new_map[_coord(new)] = relation_id

    return old_map, new_map


def _access_position_signatures(
    profile: dict[str, Any],
    method_relations: dict[tuple[str, str], str],
    *,
    aliases: dict[str, str],
) -> dict[
    tuple[int, str, tuple[tuple[str, str, int, int], ...]],
    list[tuple[str, str]],
]:
    """Build exact matched-method field-access-position signatures.

    Only accesses to fields declared by the profiled owner participate. The
    access ordinal is included as well as the bytecode offset so the signal
    remains fail-closed when instruction layout changes.
    """
    owner = profile.get("internal_name")
    if not isinstance(owner, str) or not owner:
        raise FieldRelationshipAuditError(
            "profile has no internal_name"
        )

    declared: dict[tuple[str, str], dict[str, Any]] = {
        _coord(field): field
        for field in profile.get("fields", [])
        if isinstance(field, dict)
    }
    contexts: dict[
        tuple[str, str],
        Counter[tuple[str, str, int, int]],
    ] = defaultdict(Counter)

    for method in profile.get("methods", []):
        if not isinstance(method, dict):
            continue
        method_id = method_relations.get(
            (
                str(method.get("name", "")),
                str(method.get("descriptor", "")),
            )
        )
        if method_id is None:
            continue

        own_ordinal = 0
        for access in method.get("field_accesses", []):
            if not isinstance(access, dict):
                continue
            if access.get("owner") != owner:
                continue
            key = (
                str(access.get("name", "")),
                str(access.get("descriptor", "")),
            )
            if key not in declared:
                continue

            offset = access.get("offset")
            if not isinstance(offset, int):
                own_ordinal += 1
                continue

            contexts[key][
                (
                    method_id,
                    str(access.get("operation", "")),
                    own_ordinal,
                    offset,
                )
            ] += 1
            own_ordinal += 1

    groups: dict[
        tuple[int, str, tuple[tuple[str, str, int, int], ...]],
        list[tuple[str, str]],
    ] = defaultdict(list)
    for key, field in declared.items():
        context = contexts.get(key)
        if not context:
            continue
        signature = (
            int(field.get("access", 0)),
            _descriptor_identity_shape(
                str(field.get("descriptor", "")),
                aliases,
            ),
            tuple(
                sorted(
                    (
                        method_id,
                        operation,
                        ordinal,
                        offset,
                    )
                    for (
                        method_id,
                        operation,
                        ordinal,
                        offset,
                    ), count in context.items()
                    for _ in range(count)
                )
            ),
        )
        groups[signature].append(key)

    return groups


def audit_field_relationships_by_exact_positions(
    old_profile: dict[str, Any],
    new_profile: dict[str, Any],
    member_class_record: dict[str, Any],
    *,
    old_type_aliases: dict[str, str],
    new_type_aliases: dict[str, str],
    min_observations: int = 2,
) -> dict[str, Any]:
    """Detect field relationships contradicted by exact bytecode positions.

    This is a validator, not a mutator. It never rewrites a relationship.
    Exact-position matches are emitted only when the complete matched-method
    access signature is unique on both sides and has at least the configured
    minimum number of observations.
    """
    if min_observations < 1:
        raise FieldRelationshipAuditError(
            "min_observations must be >= 1"
        )

    old_methods, new_methods = _method_relation_maps(
        member_class_record
    )
    old_groups = _access_position_signatures(
        old_profile,
        old_methods,
        aliases=old_type_aliases,
    )
    new_groups = _access_position_signatures(
        new_profile,
        new_methods,
        aliases=new_type_aliases,
    )

    exact_matches: list[dict[str, Any]] = []
    exact_by_old: dict[tuple[str, str], tuple[str, str]] = {}
    for signature in set(old_groups) & set(new_groups):
        old_rows = old_groups[signature]
        new_rows = new_groups[signature]
        if len(old_rows) != 1 or len(new_rows) != 1:
            continue

        observations = len(signature[2])
        if observations < min_observations:
            continue

        old_coord = old_rows[0]
        new_coord = new_rows[0]
        exact_by_old[old_coord] = new_coord
        exact_matches.append(
            {
                "old": {
                    "name": old_coord[0],
                    "descriptor": old_coord[1],
                },
                "new": {
                    "name": new_coord[0],
                    "descriptor": new_coord[1],
                },
                "strategy": "exact_matched_method_access_positions",
                "confidence": "EXACT_CONTEXT",
                "score": 0.9995,
                "observations": observations,
            }
        )

    current_by_old: dict[
        tuple[str, str],
        dict[str, Any],
    ] = {}
    for relationship in (
        member_class_record
        .get("fields", {})
        .get("relationships", [])
    ):
        if not isinstance(relationship, dict):
            continue
        current_by_old[_coord(relationship.get("old", {}))] = (
            relationship
        )

    conflicts: list[dict[str, Any]] = []
    for old_coord, proven_new in exact_by_old.items():
        current = current_by_old.get(old_coord)
        if current is None:
            continue
        current_new = _coord(current.get("new", {}))
        if current_new == proven_new:
            continue

        conflicts.append(
            {
                "relationship_id": current.get(
                    "relationship_id"
                ),
                "current_strategy": current.get("strategy"),
                "old": {
                    "name": old_coord[0],
                    "descriptor": old_coord[1],
                },
                "current_new": {
                    "name": current_new[0],
                    "descriptor": current_new[1],
                },
                "exact_context_new": {
                    "name": proven_new[0],
                    "descriptor": proven_new[1],
                },
                "reason": (
                    "current field relationship contradicts a unique "
                    "exact matched-method access-position signature"
                ),
            }
        )

    exact_matches.sort(
        key=lambda row: (
            row["old"]["name"],
            row["old"]["descriptor"],
            row["new"]["name"],
            row["new"]["descriptor"],
        )
    )
    conflicts.sort(
        key=lambda row: (
            row["old"]["name"],
            row["old"]["descriptor"],
        )
    )

    return {
        "schema_version": 1,
        "kind": "field_relationship_position_audit",
        "canonical": False,
        "old_owner": member_class_record.get("old_owner"),
        "new_owner": member_class_record.get("new_owner"),
        "min_observations": min_observations,
        "exact_position_matches": len(exact_matches),
        "conflict_count": len(conflicts),
        "matches": exact_matches,
        "conflicts": conflicts,
    }


def reconcile_field_relationships_by_exact_positions(
    member_class_record: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, Any]:
    """Return a research-only field section with exact-position precedence.

    Existing relationships contradicted by an exact-position match are removed.
    Existing relationships that already agree are retained. Exact-position
    matches are then overlaid one-to-one. Canonical lineage is never mutated.
    """
    if audit.get("kind") != "field_relationship_position_audit":
        raise FieldRelationshipAuditError(
            "audit kind must be field_relationship_position_audit"
        )
    if audit.get("canonical") is not False:
        raise FieldRelationshipAuditError(
            "audit must be explicitly non-canonical"
        )

    fields = member_class_record.get("fields", {})
    current = [
        row
        for row in fields.get("relationships", [])
        if isinstance(row, dict)
    ]
    exact = [
        row
        for row in audit.get("matches", [])
        if isinstance(row, dict)
    ]

    exact_by_old = {
        _coord(row.get("old", {})): _coord(row.get("new", {}))
        for row in exact
    }
    exact_by_new = {
        _coord(row.get("new", {})): _coord(row.get("old", {}))
        for row in exact
    }
    if len(exact_by_old) != len(exact) or len(exact_by_new) != len(exact):
        raise FieldRelationshipAuditError(
            "exact-position matches must be one-to-one"
        )

    old_details: dict[tuple[str, str], dict[str, Any]] = {}
    new_details: dict[tuple[str, str], dict[str, Any]] = {}
    for row in current:
        old_details[_coord(row.get("old", {}))] = dict(
            row.get("old", {})
        )
        new_details[_coord(row.get("new", {}))] = dict(
            row.get("new", {})
        )
    for row in fields.get("unmatched_old", []):
        if isinstance(row, dict):
            old_details[_coord(row)] = dict(row)
    for row in fields.get("unmatched_new", []):
        if isinstance(row, dict):
            new_details[_coord(row)] = dict(row)

    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for row in current:
        old_coord = _coord(row.get("old", {}))
        new_coord = _coord(row.get("new", {}))
        expected_new = exact_by_old.get(old_coord)
        expected_old = exact_by_new.get(new_coord)

        contradicted = (
            expected_new is not None
            and expected_new != new_coord
        ) or (
            expected_old is not None
            and expected_old != old_coord
        )
        if contradicted:
            dropped.append(row)
        else:
            kept.append(row)

    kept_pairs = {
        (
            _coord(row.get("old", {})),
            _coord(row.get("new", {})),
        )
        for row in kept
    }
    added: list[dict[str, Any]] = []
    for row in exact:
        old_coord = _coord(row.get("old", {}))
        new_coord = _coord(row.get("new", {}))
        if (old_coord, new_coord) in kept_pairs:
            continue

        old_row = dict(
            old_details.get(
                old_coord,
                {
                    "name": old_coord[0],
                    "descriptor": old_coord[1],
                },
            )
        )
        new_row = dict(
            new_details.get(
                new_coord,
                {
                    "name": new_coord[0],
                    "descriptor": new_coord[1],
                },
            )
        )
        added.append(
            {
                "relationship_id": (
                    "FIELDREL_EXACTPOS_"
                    + old_coord[0]
                    + "_"
                    + new_coord[0]
                ),
                "kind": "field",
                "old_owner": member_class_record.get(
                    "old_owner"
                ),
                "new_owner": member_class_record.get(
                    "new_owner"
                ),
                "old": old_row,
                "new": new_row,
                "strategy": (
                    "exact_matched_method_access_positions"
                ),
                "score": float(row.get("score", 0.9995)),
                "confidence": "EXACT_CONTEXT",
                "renamed": old_coord[0] != new_coord[0],
                "evidence": {
                    "observations": row.get("observations"),
                    "source_audit": (
                        "field_relationship_position_audit"
                    ),
                },
            }
        )

    relationships = kept + added
    relationships.sort(
        key=lambda row: (
            str(row.get("old", {}).get("name")),
            str(row.get("old", {}).get("descriptor")),
            str(row.get("new", {}).get("name")),
        )
    )

    used_old = {
        _coord(row.get("old", {}))
        for row in relationships
    }
    used_new = {
        _coord(row.get("new", {}))
        for row in relationships
    }
    unmatched_old = [
        row
        for key, row in sorted(old_details.items())
        if key not in used_old
    ]
    unmatched_new = [
        row
        for key, row in sorted(new_details.items())
        if key not in used_new
    ]

    return {
        "schema_version": 1,
        "kind": "field_relationship_reconciliation",
        "canonical": False,
        "old_owner": member_class_record.get("old_owner"),
        "new_owner": member_class_record.get("new_owner"),
        "summary": {
            "current_relationships": len(current),
            "dropped_conflicting": len(dropped),
            "exact_position_added": len(added),
            "reconciled_relationships": len(relationships),
            "unmatched_old": len(unmatched_old),
            "unmatched_new": len(unmatched_new),
        },
        "relationships": relationships,
        "dropped": dropped,
        "added": added,
        "unmatched_old": unmatched_old,
        "unmatched_new": unmatched_new,
    }


def audit_member_identity_candidate_set(
    old_jar: Path,
    new_jar: Path,
    candidates: dict[str, Any],
    *,
    min_observations: int = 2,
) -> dict[str, Any]:
    """Audit an entire member-identity candidate set against exact JARs.

    The JAR hashes are bound to the candidate document before any profile is
    trusted. Class lineage from the candidate set supplies descriptor aliases.
    """
    if candidates.get("kind") != "member_identity_candidates":
        raise FieldRelationshipAuditError(
            "candidates kind must be member_identity_candidates"
        )
    if candidates.get("canonical") is not False:
        raise FieldRelationshipAuditError(
            "member identity candidates must be non-canonical"
        )

    old_sha = sha256_file(old_jar.resolve())
    new_sha = sha256_file(new_jar.resolve())
    if old_sha.lower() != str(
        candidates.get("old_sha256", "")
    ).lower():
        raise FieldRelationshipAuditError(
            "old JAR SHA-256 does not match candidate set"
        )
    if new_sha.lower() != str(
        candidates.get("new_sha256", "")
    ).lower():
        raise FieldRelationshipAuditError(
            "new JAR SHA-256 does not match candidate set"
        )

    class_rows = [
        row
        for row in candidates.get("classes", [])
        if isinstance(row, dict)
    ]
    old_aliases: dict[str, str] = {}
    new_aliases: dict[str, str] = {}
    for row in class_rows:
        old_owner = row.get("old_owner")
        new_owner = row.get("new_owner")
        if not isinstance(old_owner, str) or not isinstance(
            new_owner,
            str,
        ):
            continue
        old_internal = (
            old_owner[:-6]
            if old_owner.endswith(".class")
            else old_owner
        )
        new_internal = (
            new_owner[:-6]
            if new_owner.endswith(".class")
            else new_owner
        )
        old_aliases[old_internal] = old_internal
        new_aliases[new_internal] = old_internal

    audits: list[dict[str, Any]] = []
    exact_total = 0
    conflict_total = 0
    for row in class_rows:
        old_owner = row.get("old_owner")
        new_owner = row.get("new_owner")
        if not isinstance(old_owner, str) or not isinstance(
            new_owner,
            str,
        ):
            continue

        old_entry = (
            old_owner
            if old_owner.endswith(".class")
            else old_owner + ".class"
        )
        new_entry = (
            new_owner
            if new_owner.endswith(".class")
            else new_owner + ".class"
        )
        audit = audit_field_relationships_by_exact_positions(
            profile_jar_class(old_jar, old_entry),
            profile_jar_class(new_jar, new_entry),
            row,
            old_type_aliases=old_aliases,
            new_type_aliases=new_aliases,
            min_observations=min_observations,
        )
        if (
            audit["exact_position_matches"]
            or audit["conflict_count"]
        ):
            audits.append(audit)
        exact_total += int(audit["exact_position_matches"])
        conflict_total += int(audit["conflict_count"])

    audits.sort(
        key=lambda row: (
            str(row.get("old_owner", "")),
            str(row.get("new_owner", "")),
        )
    )
    return {
        "schema_version": 1,
        "kind": "field_relationship_position_audit_set",
        "canonical": False,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "min_observations": min_observations,
        "class_audits": len(audits),
        "exact_position_matches": exact_total,
        "conflict_count": conflict_total,
        "classes": audits,
    }


def reconcile_member_identity_candidate_set_by_exact_positions(
    candidates: dict[str, Any],
    audit_set: dict[str, Any],
) -> dict[str, Any]:
    """Reconcile all class field relationships using an exact-position audit set.

    Methods are copied unchanged. Field sections are reconciled only for class
    pairs present in the audit. The output remains non-canonical research.
    """
    if candidates.get("kind") != "member_identity_candidates":
        raise FieldRelationshipAuditError(
            "candidates kind must be member_identity_candidates"
        )
    if candidates.get("canonical") is not False:
        raise FieldRelationshipAuditError(
            "candidate set must be explicitly non-canonical"
        )
    if audit_set.get("kind") != "field_relationship_position_audit_set":
        raise FieldRelationshipAuditError(
            "audit kind must be field_relationship_position_audit_set"
        )
    if audit_set.get("canonical") is not False:
        raise FieldRelationshipAuditError(
            "audit set must be explicitly non-canonical"
        )

    for side in ("old_sha256", "new_sha256"):
        if str(candidates.get(side, "")).lower() != str(
            audit_set.get(side, "")
        ).lower():
            raise FieldRelationshipAuditError(
                f"{side} mismatch between candidates and audit"
            )

    audit_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for audit in audit_set.get("classes", []):
        if not isinstance(audit, dict):
            continue
        key = (
            str(audit.get("old_owner", "")),
            str(audit.get("new_owner", "")),
        )
        if not all(key):
            raise FieldRelationshipAuditError(
                "class audit has invalid owner coordinate"
            )
        if key in audit_by_pair:
            raise FieldRelationshipAuditError(
                f"duplicate class audit for {key!r}"
            )
        audit_by_pair[key] = audit

    class_rows: list[dict[str, Any]] = []
    reconciled_classes = 0
    dropped_conflicting = 0
    exact_position_added = 0
    method_matched = 0
    field_matched = 0
    field_old = 0
    field_new = 0
    field_unmatched_old = 0
    field_unmatched_new = 0

    for source in candidates.get("classes", []):
        if not isinstance(source, dict):
            continue
        row = dict(source)
        row["methods"] = dict(source.get("methods", {}))
        row["fields"] = dict(source.get("fields", {}))

        key = (
            str(source.get("old_owner", "")),
            str(source.get("new_owner", "")),
        )
        audit = audit_by_pair.get(key)
        if audit is not None:
            reconciled = reconcile_field_relationships_by_exact_positions(
                source,
                audit,
            )
            original_fields = source.get("fields", {})
            row["fields"] = {
                **dict(original_fields),
                "relationships": reconciled["relationships"],
                "unmatched_old": reconciled["unmatched_old"],
                "unmatched_new": reconciled["unmatched_new"],
                "summary": {
                    **dict(original_fields.get("summary", {})),
                    "matched": reconciled["summary"][
                        "reconciled_relationships"
                    ],
                    "unmatched_old": reconciled["summary"][
                        "unmatched_old"
                    ],
                    "unmatched_new": reconciled["summary"][
                        "unmatched_new"
                    ],
                    "exact_position_added": reconciled["summary"][
                        "exact_position_added"
                    ],
                    "dropped_conflicting": reconciled["summary"][
                        "dropped_conflicting"
                    ],
                },
            }
            row["field_position_reconciliation"] = {
                "dropped_conflicting": reconciled["summary"][
                    "dropped_conflicting"
                ],
                "exact_position_added": reconciled["summary"][
                    "exact_position_added"
                ],
            }
            reconciled_classes += 1
            dropped_conflicting += reconciled["summary"][
                "dropped_conflicting"
            ]
            exact_position_added += reconciled["summary"][
                "exact_position_added"
            ]

        methods = row.get("methods", {})
        fields = row.get("fields", {})
        method_matched += int(
            methods.get("summary", {}).get(
                "matched",
                len(methods.get("relationships", [])),
            )
        )
        field_matched += len(fields.get("relationships", []))
        field_old += int(
            fields.get("summary", {}).get(
                "old_count",
                len(fields.get("relationships", []))
                + len(fields.get("unmatched_old", [])),
            )
        )
        field_new += int(
            fields.get("summary", {}).get(
                "new_count",
                len(fields.get("relationships", []))
                + len(fields.get("unmatched_new", [])),
            )
        )
        field_unmatched_old += len(fields.get("unmatched_old", []))
        field_unmatched_new += len(fields.get("unmatched_new", []))
        class_rows.append(row)

    summary = dict(candidates.get("summary", {}))
    summary.update(
        {
            "method_matched": method_matched,
            "field_old": field_old,
            "field_new": field_new,
            "field_matched": field_matched,
            "field_unmatched_old": field_unmatched_old,
            "field_unmatched_new": field_unmatched_new,
            "field_coverage": (
                round(field_matched / field_old, 6)
                if field_old
                else 0.0
            ),
            "position_reconciled_classes": reconciled_classes,
            "position_dropped_conflicting": dropped_conflicting,
            "position_exact_added": exact_position_added,
        }
    )

    return {
        **{
            key: value
            for key, value in candidates.items()
            if key not in {"classes", "summary", "kind"}
        },
        "schema_version": 1,
        "kind": "reconciled_member_identity_candidates",
        "canonical": False,
        "summary": summary,
        "classes": class_rows,
        "skipped_classes": list(
            candidates.get("skipped_classes", [])
        ),
        "reconciliation": {
            "strategy": "exact_matched_method_access_positions",
            "audit_min_observations": audit_set.get(
                "min_observations"
            ),
            "audit_exact_position_matches": audit_set.get(
                "exact_position_matches"
            ),
            "audit_conflicts": audit_set.get("conflict_count"),
            "classes_reconciled": reconciled_classes,
            "relationships_dropped": dropped_conflicting,
            "relationships_added": exact_position_added,
        },
    }
