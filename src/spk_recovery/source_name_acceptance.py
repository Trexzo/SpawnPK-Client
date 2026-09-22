from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class SourceNameAcceptanceError(ValueError):
    pass


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_source_rename_plan(
    inventory: dict[str, Any],
    review: dict[str, Any],
    acceptance: dict[str, Any],
) -> dict[str, Any]:
    if (
        inventory.get("schema_version") != 1
        or inventory.get("kind") != "source_symbol_inventory"
    ):
        raise SourceNameAcceptanceError("unsupported source symbol inventory")
    if (
        review.get("schema_version") != 1
        or review.get("kind") != "source_name_review"
        or review.get("canonical") is not False
    ):
        raise SourceNameAcceptanceError("unsupported source name review")
    if (
        acceptance.get("schema_version") != 1
        or acceptance.get("kind") != "source_name_acceptance"
    ):
        raise SourceNameAcceptanceError("unsupported source name acceptance")

    inventory_id = inventory.get("inventory_id")
    review_id = review.get("review_id")
    source_tree_sha = inventory.get("source_tree_sha256")

    if review.get("inventory_id") != inventory_id:
        raise SourceNameAcceptanceError("review inventory_id mismatch")
    if review.get("source_tree_sha256") != source_tree_sha:
        raise SourceNameAcceptanceError("review source tree mismatch")
    if acceptance.get("inventory_id") != inventory_id:
        raise SourceNameAcceptanceError("acceptance inventory_id mismatch")
    if acceptance.get("review_id") != review_id:
        raise SourceNameAcceptanceError("acceptance review_id mismatch")

    requested = acceptance.get("accepted_proposal_ids")
    if not isinstance(requested, list):
        raise SourceNameAcceptanceError(
            "accepted_proposal_ids must be an array"
        )
    if len(requested) != len(set(requested)):
        raise SourceNameAcceptanceError(
            "accepted_proposal_ids contains duplicates"
        )

    proposals = {
        row.get("proposal_id"): row
        for row in review.get("proposals", [])
        if isinstance(row, dict)
        and isinstance(row.get("proposal_id"), str)
    }
    symbols = {
        row.get("source_symbol_id"): row
        for row in inventory.get("symbols", [])
        if isinstance(row, dict)
        and isinstance(row.get("source_symbol_id"), str)
    }

    rows: list[dict[str, Any]] = []
    for proposal_id in sorted(requested):
        proposal = proposals.get(proposal_id)
        if proposal is None:
            raise SourceNameAcceptanceError(
                f"unknown or conflicted proposal {proposal_id!r}"
            )
        symbol_id = proposal.get("source_symbol_id")
        symbol = symbols.get(symbol_id)
        if symbol is None:
            raise SourceNameAcceptanceError(
                f"proposal {proposal_id} targets unknown symbol {symbol_id!r}"
            )
        if proposal.get("current_name") != symbol.get("current_name"):
            raise SourceNameAcceptanceError(
                f"{proposal_id}: review current_name drifted from inventory"
            )
        if proposal.get("kind") != symbol.get("kind"):
            raise SourceNameAcceptanceError(
                f"{proposal_id}: review symbol kind drifted from inventory"
            )

        rows.append(
            {
                "proposal_id": proposal_id,
                "source_symbol_id": symbol_id,
                "source_method_id": symbol.get("source_method_id"),
                "canonical_method_id": symbol.get("canonical_method_id"),
                "owner_logical_id": symbol.get("owner_logical_id"),
                "source_file": symbol.get("source_file"),
                "owner_internal_name": symbol.get("owner_internal_name"),
                "method_name": symbol.get("method_name"),
                "method_arity": symbol.get("method_arity"),
                "kind": symbol.get("kind"),
                "ordinal": symbol.get("ordinal"),
                "declaration_start": symbol.get("start"),
                "declaration_end": symbol.get("end"),
                "current_name": symbol.get("current_name"),
                "new_name": proposal.get("proposed_name"),
                "declared_type": symbol.get("declared_type"),
                "confidence": proposal.get("confidence"),
                "evidence": proposal.get("evidence", []),
                "acceptance_note": acceptance.get("note"),
            }
        )

    # Deliberately conservative source-scope collision policy. We reject names
    # that are already occupied anywhere in the same source method, even when
    # Java might permit reuse in disjoint sibling blocks. R6 can relax this only
    # with an explicit scope graph later.
    by_method: dict[str, list[dict[str, Any]]] = {}
    all_symbols_by_method: dict[str, list[dict[str, Any]]] = {}
    for symbol in symbols.values():
        method_id = symbol.get("source_method_id")
        if isinstance(method_id, str):
            all_symbols_by_method.setdefault(method_id, []).append(symbol)
    for row in rows:
        method_id = row.get("source_method_id")
        if not isinstance(method_id, str):
            raise SourceNameAcceptanceError(
                f"{row['source_symbol_id']}: source_method_id missing"
            )
        by_method.setdefault(method_id, []).append(row)

    accepted_ids = {row["source_symbol_id"] for row in rows}
    for method_id, accepted_rows in by_method.items():
        proposed_seen: dict[str, str] = {}
        existing = all_symbols_by_method.get(method_id, [])
        for row in accepted_rows:
            new_name = row["new_name"]
            prior = proposed_seen.get(new_name)
            if prior is not None and prior != row["source_symbol_id"]:
                raise SourceNameAcceptanceError(
                    f"{method_id}: accepted proposals collide on {new_name!r}"
                )
            proposed_seen[new_name] = row["source_symbol_id"]

            for other in existing:
                if other.get("source_symbol_id") == row["source_symbol_id"]:
                    continue
                # If another symbol is itself being renamed away, its old name
                # still cannot safely be reused in this conservative stage.
                if other.get("current_name") == new_name:
                    raise SourceNameAcceptanceError(
                        f"{method_id}: proposed name {new_name!r} collides with "
                        f"existing source symbol {other.get('source_symbol_id')}"
                    )

    rows.sort(
        key=lambda row: (
            str(row["source_file"]),
            int(row["declaration_start"]),
            str(row["source_symbol_id"]),
        )
    )
    material = {
        "inventory_id": inventory_id,
        "review_id": review_id,
        "source_tree_sha256": source_tree_sha,
        "rows": [
            (
                row["source_symbol_id"],
                row["current_name"],
                row["new_name"],
            )
            for row in rows
        ],
    }
    return {
        "schema_version": 1,
        "kind": "source_rename_plan",
        "plan_id": "SRCPLAN_" + _digest(material)[:20].upper(),
        "inventory_id": inventory_id,
        "review_id": review_id,
        "workspace_id": inventory.get("workspace_id"),
        "build_id": inventory.get("build_id"),
        "source_tree_sha256": source_tree_sha,
        "accepted_proposal_count": len(rows),
        "renames": rows,
    }


def write_source_rename_plan(
    plan: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            plan,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
