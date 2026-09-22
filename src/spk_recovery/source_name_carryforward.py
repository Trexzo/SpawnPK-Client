from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .lineage import validate_lineage
from .member_lineage import validate_member_lineage
from .source_name_acceptance import build_source_rename_plan
from .source_name_review import resolve_source_name_candidates


class SourceNameCarryForwardError(ValueError):
    pass


_ALLOWED_CLASS_DELTAS = {
    "byte_identical",
    "structurally_equivalent",
}
_ALLOWED_METHOD_DELTAS = {
    "member_shape_unchanged",
    "member_only_obfuscation_rename",
}


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _validate_inventory(doc: dict[str, Any], label: str) -> None:
    if (
        doc.get("schema_version") != 1
        or doc.get("kind") != "source_symbol_inventory"
    ):
        raise SourceNameCarryForwardError(
            f"{label}: unsupported source symbol inventory"
        )
    if not isinstance(doc.get("inventory_id"), str):
        raise SourceNameCarryForwardError(
            f"{label}: missing inventory_id"
        )
    if not isinstance(doc.get("source_tree_sha256"), str):
        raise SourceNameCarryForwardError(
            f"{label}: missing source_tree_sha256"
        )


def _build_entry(
    record: dict[str, Any],
    build_id: str,
) -> dict[str, Any] | None:
    hits = [
        row
        for row in record.get("lineage", [])
        if row.get("build_id") == build_id
    ]
    if len(hits) == 1:
        return hits[0]
    return None


def _class_delta_map(
    report: dict[str, Any],
) -> dict[tuple[str, str], str]:
    return {
        (str(row.get("old")), str(row.get("new"))): str(
            row.get("delta")
        )
        for row in report.get("classes", [])
        if isinstance(row, dict)
    }


def _member_delta_key(
    owner: Any,
    member: Any,
) -> tuple[str, str, str]:
    owner_s = str(owner or "")
    if not owner_s.endswith(".class"):
        owner_s += ".class"
    member_d = member if isinstance(member, dict) else {}
    return (
        owner_s,
        str(member_d.get("name", "")),
        str(member_d.get("descriptor", "")),
    )


def _member_delta_map(
    report: dict[str, Any],
) -> dict[
    tuple[
        tuple[str, str, str],
        tuple[str, str, str],
    ],
    str,
]:
    out: dict[
        tuple[
            tuple[str, str, str],
            tuple[str, str, str],
        ],
        str,
    ] = {}
    for row in report.get("members", []):
        if not isinstance(row, dict) or row.get("kind") != "method":
            continue
        key = (
            _member_delta_key(row.get("old_owner"), row.get("old")),
            _member_delta_key(row.get("new_owner"), row.get("new")),
        )
        out[key] = str(row.get("delta"))
    return out


def _source_method_counts(
    inventory: dict[str, Any],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in inventory.get("methods", []):
        if not isinstance(row, dict):
            continue
        method_id = row.get("canonical_method_id")
        if isinstance(method_id, str) and method_id:
            counts[method_id] = counts.get(method_id, 0) + 1
    return counts


def _target_symbols(
    inventory: dict[str, Any],
    *,
    canonical_method_id: str,
    kind: str,
    ordinal: int,
    declared_type: str,
) -> list[dict[str, Any]]:
    return [
        row
        for row in inventory.get("symbols", [])
        if isinstance(row, dict)
        and row.get("canonical_method_id") == canonical_method_id
        and row.get("kind") == kind
        and row.get("ordinal") == ordinal
        and row.get("declared_type") == declared_type
    ]


def carry_forward_source_names(
    previous_plan: dict[str, Any],
    old_inventory: dict[str, Any],
    new_inventory: dict[str, Any],
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    *,
    class_delta_report: dict[str, Any] | None = None,
    member_delta_report: dict[str, Any] | None = None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any] | None,
    dict[str, Any] | None,
]:
    """Carry previously accepted inferred source names into a regenerated workspace.

    The function never treats declaration offsets or old SRC_* IDs as persistent
    identity. Stable CLIENT_METHOD_* identity is required. Cross-build transfer
    additionally requires conservative R3 class/member delta evidence.
    """
    if (
        previous_plan.get("schema_version") != 1
        or previous_plan.get("kind") != "source_rename_plan"
    ):
        raise SourceNameCarryForwardError(
            "unsupported previous source rename plan"
        )
    _validate_inventory(old_inventory, "old_inventory")
    _validate_inventory(new_inventory, "new_inventory")
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    if previous_plan.get("inventory_id") != old_inventory.get(
        "inventory_id"
    ):
        raise SourceNameCarryForwardError(
            "previous plan inventory_id does not match old inventory"
        )
    if previous_plan.get("source_tree_sha256") != old_inventory.get(
        "source_tree_sha256"
    ):
        raise SourceNameCarryForwardError(
            "previous plan source tree does not match old inventory"
        )

    old_build = str(old_inventory.get("build_id") or "")
    new_build = str(new_inventory.get("build_id") or "")
    if not old_build or not new_build:
        raise SourceNameCarryForwardError(
            "both source inventories must declare build_id"
        )

    old_authority = str(
        old_inventory.get("source_authority_sha256") or ""
    ).lower()
    new_authority = str(
        new_inventory.get("source_authority_sha256") or ""
    ).lower()
    same_build = old_build == new_build

    if same_build:
        if not old_authority or old_authority != new_authority:
            raise SourceNameCarryForwardError(
                "same-build regeneration requires the same exact binary authority"
            )
        class_deltas: dict[tuple[str, str], str] = {}
        member_deltas: dict[
            tuple[
                tuple[str, str, str],
                tuple[str, str, str],
            ],
            str,
        ] = {}
    else:
        if class_delta_report is None or member_delta_report is None:
            raise SourceNameCarryForwardError(
                "cross-build source-name carry-forward requires class and member delta reports"
            )
        if (
            class_delta_report.get("schema_version") != 1
            or class_delta_report.get("kind")
            != "class_delta_report"
        ):
            raise SourceNameCarryForwardError(
                "unsupported class delta report"
            )
        if (
            member_delta_report.get("schema_version") != 1
            or member_delta_report.get("kind")
            != "member_delta_report"
        ):
            raise SourceNameCarryForwardError(
                "unsupported member delta report"
            )
        for label, report in (
            ("class_delta_report", class_delta_report),
            ("member_delta_report", member_delta_report),
        ):
            if (
                str(report.get("old_sha256") or "").lower()
                != old_authority
                or str(report.get("new_sha256") or "").lower()
                != new_authority
            ):
                raise SourceNameCarryForwardError(
                    f"{label}: exact authority SHA pair does not match source inventories"
                )
        class_deltas = _class_delta_map(class_delta_report)
        member_deltas = _member_delta_map(member_delta_report)

    classes = {
        row["logical_id"]: row
        for row in class_lineage.get("classes", [])
        if isinstance(row, dict)
        and isinstance(row.get("logical_id"), str)
    }
    members = {
        row["member_id"]: row
        for row in member_lineage.get("members", [])
        if isinstance(row, dict)
        and isinstance(row.get("member_id"), str)
    }
    new_method_counts = _source_method_counts(new_inventory)

    new_symbols_by_method: dict[str, list[dict[str, Any]]] = {}
    for row in new_inventory.get("symbols", []):
        if not isinstance(row, dict):
            continue
        source_method_id = row.get("source_method_id")
        if isinstance(source_method_id, str):
            new_symbols_by_method.setdefault(
                source_method_id,
                [],
            ).append(row)

    carried: list[dict[str, Any]] = []
    already_applied: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    proposed_names_by_method: dict[
        tuple[str, str],
        str,
    ] = {}

    for old_row in sorted(
        previous_plan.get("renames", []),
        key=lambda row: str(row.get("source_symbol_id")),
    ):
        old_symbol_id = str(old_row.get("source_symbol_id") or "")
        desired_name = str(old_row.get("new_name") or "")
        method_id = old_row.get("canonical_method_id")
        owner_id = old_row.get("owner_logical_id")

        def block(reason: str, detail: str) -> None:
            blocked.append(
                {
                    "previous_source_symbol_id": old_symbol_id,
                    "canonical_method_id": method_id,
                    "owner_logical_id": owner_id,
                    "desired_name": desired_name,
                    "reason": reason,
                    "detail": detail,
                }
            )

        if not isinstance(method_id, str) or not method_id:
            block(
                "missing_canonical_method_identity",
                "Previously accepted source symbol has no stable CLIENT_METHOD identity.",
            )
            continue
        if new_method_counts.get(method_id) != 1:
            block(
                "new_source_method_ambiguous_or_missing",
                "New source inventory does not map exactly one source method to the canonical method.",
            )
            continue

        member_record = members.get(method_id)
        if (
            member_record is None
            or member_record.get("kind") != "method"
        ):
            block(
                "canonical_method_missing",
                "Canonical member lineage does not contain this method.",
            )
            continue

        owner_record = classes.get(str(owner_id))
        if owner_record is None:
            block(
                "canonical_owner_missing",
                "Canonical class lineage does not contain the source symbol owner.",
            )
            continue

        old_member_entry = _build_entry(
            member_record,
            old_build,
        )
        new_member_entry = _build_entry(
            member_record,
            new_build,
        )
        old_class_entry = _build_entry(
            owner_record,
            old_build,
        )
        new_class_entry = _build_entry(
            owner_record,
            new_build,
        )
        if (
            old_member_entry is None
            or new_member_entry is None
            or old_class_entry is None
            or new_class_entry is None
        ):
            block(
                "canonical_lineage_missing_build_relation",
                "Stable class/method identity is not present in both source builds.",
            )
            continue

        if not same_build:
            class_key = (
                str(old_class_entry["entry_path"]),
                str(new_class_entry["entry_path"]),
            )
            class_delta = class_deltas.get(class_key)
            if class_delta not in _ALLOWED_CLASS_DELTAS:
                block(
                    "owner_class_modified_or_unproven",
                    f"Owner class delta is {class_delta!r}, not safe for automatic source-name carry-forward.",
                )
                continue

            member_key = (
                _member_delta_key(
                    old_member_entry.get("owner_internal_name"),
                    old_member_entry,
                ),
                _member_delta_key(
                    new_member_entry.get("owner_internal_name"),
                    new_member_entry,
                ),
            )
            method_delta = member_deltas.get(member_key)
            if method_delta not in _ALLOWED_METHOD_DELTAS:
                block(
                    "method_modified_or_unproven",
                    f"Canonical method delta is {method_delta!r}, not safe for automatic source-name carry-forward.",
                )
                continue

        kind = old_row.get("kind")
        ordinal = old_row.get("ordinal")
        declared_type = old_row.get("declared_type")
        if (
            not isinstance(kind, str)
            or not isinstance(ordinal, int)
            or isinstance(ordinal, bool)
            or not isinstance(declared_type, str)
        ):
            block(
                "previous_symbol_shape_invalid",
                "Previous accepted plan lacks stable kind/ordinal/type shape.",
            )
            continue

        targets = _target_symbols(
            new_inventory,
            canonical_method_id=method_id,
            kind=kind,
            ordinal=ordinal,
            declared_type=declared_type,
        )
        if len(targets) != 1:
            block(
                "target_symbol_ambiguous_or_missing",
                "New source inventory does not contain exactly one matching kind/ordinal/type source symbol.",
            )
            continue
        target = targets[0]

        target_method = str(target.get("source_method_id") or "")
        if not target_method:
            block(
                "target_source_method_missing",
                "Target source symbol has no source method identity.",
            )
            continue

        collision = next(
            (
                other
                for other in new_symbols_by_method.get(
                    target_method,
                    [],
                )
                if other.get("source_symbol_id")
                != target.get("source_symbol_id")
                and other.get("current_name") == desired_name
            ),
            None,
        )
        if collision is not None:
            block(
                "target_name_collision",
                "Previously accepted name is already occupied by another source symbol in the regenerated method.",
            )
            continue

        proposal_key = (target_method, desired_name)
        prior_symbol = proposed_names_by_method.get(proposal_key)
        if (
            prior_symbol is not None
            and prior_symbol != target.get("source_symbol_id")
        ):
            block(
                "carried_name_collision",
                "Two carried source symbols would claim the same name in one source method.",
            )
            continue
        proposed_names_by_method[proposal_key] = str(
            target.get("source_symbol_id")
        )

        base = {
            "previous_source_symbol_id": old_symbol_id,
            "source_symbol_id": target.get("source_symbol_id"),
            "canonical_method_id": method_id,
            "owner_logical_id": owner_id,
            "kind": kind,
            "ordinal": ordinal,
            "declared_type": declared_type,
            "previous_name": old_row.get("current_name"),
            "desired_name": desired_name,
            "current_name": target.get("current_name"),
            "confidence": old_row.get("confidence"),
            "carry_mode": (
                "same_exact_build_regeneration"
                if same_build
                else "cross_build_stable_delta"
            ),
        }
        if target.get("current_name") == desired_name:
            already_applied.append(base)
        else:
            carried.append(base)

    candidates: list[dict[str, Any]] = []
    previous_by_symbol = {
        str(row.get("source_symbol_id")): row
        for row in previous_plan.get("renames", [])
        if isinstance(row, dict)
    }
    for row in carried:
        previous = previous_by_symbol[
            row["previous_source_symbol_id"]
        ]
        confidence = previous.get("confidence")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= float(confidence) < 1.0
        ):
            raise SourceNameCarryForwardError(
                "previous accepted inferred-name confidence is outside [0,1)"
            )
        evidence = list(previous.get("evidence", []))
        evidence.append(
            {
                "family": "accepted_source_name_carryforward",
                "detail": (
                    "Previously explicitly accepted inferred name carried through "
                    + (
                        "the same exact binary authority and stable canonical method identity."
                        if same_build
                        else "stable canonical class/method lineage with non-modified R3 delta evidence."
                    )
                ),
            }
        )
        candidates.append(
            {
                "source_symbol_id": row["source_symbol_id"],
                "proposed_name": row["desired_name"],
                "confidence": float(confidence),
                "evidence": evidence,
                "note": (
                    "Automatic carry-forward of a previously explicitly accepted "
                    "inferred source name; still not an original recovered identifier."
                ),
            }
        )

    candidate_set = {
        "schema_version": 1,
        "kind": "source_name_candidate_set",
        "canonical": False,
        "inventory_id": new_inventory["inventory_id"],
        "source_tree_sha256": new_inventory[
            "source_tree_sha256"
        ],
        "candidates": candidates,
    }
    review = resolve_source_name_candidates(
        new_inventory,
        candidate_set,
    )

    acceptance: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    if review.get("proposals"):
        acceptance = {
            "schema_version": 1,
            "kind": "source_name_acceptance",
            "inventory_id": new_inventory["inventory_id"],
            "review_id": review["review_id"],
            "accepted_proposal_ids": [
                row["proposal_id"]
                for row in review["proposals"]
            ],
            "note": (
                "Automatically re-accept previously explicit inferred names only "
                "after R6E carry-forward proof."
            ),
        }
        plan = build_source_rename_plan(
            new_inventory,
            review,
            acceptance,
        )

    material = {
        "previous_plan_id": previous_plan.get("plan_id"),
        "old_inventory_id": old_inventory.get("inventory_id"),
        "new_inventory_id": new_inventory.get("inventory_id"),
        "old_build_id": old_build,
        "new_build_id": new_build,
        "carried": [
            (row["source_symbol_id"], row["desired_name"])
            for row in carried
        ],
        "already_applied": [
            (row["source_symbol_id"], row["desired_name"])
            for row in already_applied
        ],
        "blocked": [
            (
                row["previous_source_symbol_id"],
                row["desired_name"],
                row["reason"],
            )
            for row in blocked
        ],
    }
    report_id = (
        "SRCCARRY_"
        + _stable_digest(material)[:20].upper()
    )
    report = {
        "schema_version": 1,
        "kind": "source_name_carryforward_report",
        "report_id": report_id,
        "previous_plan_id": previous_plan.get("plan_id"),
        "old_inventory_id": old_inventory.get("inventory_id"),
        "new_inventory_id": new_inventory.get("inventory_id"),
        "old_build_id": old_build,
        "new_build_id": new_build,
        "old_source_authority_sha256": old_authority,
        "new_source_authority_sha256": new_authority,
        "same_exact_build": same_build,
        "full_carryforward_ready": len(blocked) == 0,
        "safe_rewrite_plan_available": plan is not None,
        "ready_without_rewrite": (
            len(blocked) == 0
            and not carried
            and bool(already_applied)
        ),
        "summary": {
            "previously_accepted_names": len(
                previous_plan.get("renames", [])
            ),
            "carried_to_new_symbol": len(carried),
            "already_applied": len(already_applied),
            "blocked_for_review": len(blocked),
        },
        "carried": carried,
        "already_applied": already_applied,
        "blocked": blocked,
        "generated_candidate_set": (
            "source-name-candidates.json"
            if candidates
            else None
        ),
        "generated_review": (
            "source-name-review.json"
            if candidates
            else None
        ),
        "generated_acceptance": (
            "source-name-acceptance.json"
            if acceptance is not None
            else None
        ),
        "generated_plan": (
            "source-rename-plan.json"
            if plan is not None
            else None
        ),
        "note": (
            "Carried names remain explicitly inferred replacements. Modified, "
            "ambiguous, missing, type-shifted, or colliding symbols are blocked "
            "for fresh semantic review."
        ),
    }
    return report, candidate_set, review, acceptance, plan


def write_carryforward_outputs(
    report: dict[str, Any],
    candidate_set: dict[str, Any],
    review: dict[str, Any],
    acceptance: dict[str, Any] | None,
    plan: dict[str, Any] | None,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    def write(name: str, value: dict[str, Any]) -> None:
        (out_dir / name).write_text(
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    write("source-name-carryforward.json", report)
    if candidate_set.get("candidates"):
        write("source-name-candidates.json", candidate_set)
        write("source-name-review.json", review)
    if acceptance is not None:
        write("source-name-acceptance.json", acceptance)
    if plan is not None:
        write("source-rename-plan.json", plan)
