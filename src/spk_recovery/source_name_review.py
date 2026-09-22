from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


class SourceNameCandidateError(ValueError):
    pass


_IDENTIFIER = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
_JAVA_RESERVED = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch",
    "char", "class", "const", "continue", "default", "do", "double",
    "else", "enum", "extends", "final", "finally", "float", "for",
    "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private",
    "protected", "public", "return", "short", "static", "strictfp",
    "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "_", "var",
    "yield", "record", "sealed", "permits",
}


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _valid_identifier(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not _IDENTIFIER.fullmatch(value)
        or value in _JAVA_RESERVED
    ):
        raise SourceNameCandidateError(
            f"proposed source name is not a valid non-reserved Java identifier: {value!r}"
        )
    return value


def _evidence(rows: Any) -> list[dict[str, str]]:
    if not isinstance(rows, list) or not rows:
        raise SourceNameCandidateError("candidate evidence must be a non-empty array")
    out: list[dict[str, str]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SourceNameCandidateError(f"evidence[{i}] must be an object")
        family = row.get("family")
        detail = row.get("detail")
        if not isinstance(family, str) or not family:
            raise SourceNameCandidateError(f"evidence[{i}].family must be non-empty")
        if not isinstance(detail, str) or not detail:
            raise SourceNameCandidateError(f"evidence[{i}].detail must be non-empty")
        out.append({"family": family, "detail": detail})
    return sorted(
        {json.dumps(row, sort_keys=True): row for row in out}.values(),
        key=lambda row: (row["family"], row["detail"]),
    )


def resolve_source_name_candidates(
    inventory: dict[str, Any],
    candidate_set: dict[str, Any],
) -> dict[str, Any]:
    if (
        inventory.get("schema_version") != 1
        or inventory.get("kind") != "source_symbol_inventory"
    ):
        raise SourceNameCandidateError("unsupported source symbol inventory")
    inventory_id = inventory.get("inventory_id")
    source_tree_sha = inventory.get("source_tree_sha256")
    if not isinstance(inventory_id, str) or not inventory_id:
        raise SourceNameCandidateError("inventory has no inventory_id")
    if not isinstance(source_tree_sha, str) or not source_tree_sha:
        raise SourceNameCandidateError("inventory has no source_tree_sha256")

    if candidate_set.get("schema_version") != 1:
        raise SourceNameCandidateError("candidate set schema_version must be 1")
    if candidate_set.get("kind") != "source_name_candidate_set":
        raise SourceNameCandidateError(
            "candidate set kind must be source_name_candidate_set"
        )
    if candidate_set.get("canonical") is not False:
        raise SourceNameCandidateError("candidate set must be explicitly non-canonical")
    if candidate_set.get("inventory_id") != inventory_id:
        raise SourceNameCandidateError("candidate set inventory_id mismatch")
    if candidate_set.get("source_tree_sha256") != source_tree_sha:
        raise SourceNameCandidateError("candidate set source_tree_sha256 mismatch")

    symbols = {
        row["source_symbol_id"]: row
        for row in inventory.get("symbols", [])
        if isinstance(row, dict)
        and isinstance(row.get("source_symbol_id"), str)
    }
    rows = candidate_set.get("candidates")
    if not isinstance(rows, list):
        raise SourceNameCandidateError("candidates must be an array")

    normalized: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SourceNameCandidateError(f"candidates[{i}] must be an object")
        symbol_id = row.get("source_symbol_id")
        symbol = symbols.get(symbol_id)
        if symbol is None:
            raise SourceNameCandidateError(
                f"candidates[{i}] targets unknown source symbol {symbol_id!r}"
            )
        proposed = _valid_identifier(row.get("proposed_name"))
        if proposed == symbol.get("current_name"):
            raise SourceNameCandidateError(
                f"{symbol_id}: proposed name equals current source name"
            )
        confidence = row.get("confidence")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= float(confidence) < 1.0
        ):
            raise SourceNameCandidateError(
                f"{symbol_id}: inferred-name confidence must be in [0, 1)"
            )
        evidence = _evidence(row.get("evidence"))
        note = row.get("note")
        if note is not None and not isinstance(note, str):
            raise SourceNameCandidateError(
                f"{symbol_id}: note must be string or null"
            )

        material = {
            "inventory_id": inventory_id,
            "source_symbol_id": symbol_id,
            "proposed_name": proposed,
            "confidence": float(confidence),
            "evidence": evidence,
            "note": note,
        }
        normalized.append(
            {
                "candidate_id": (
                    "SRCCAND_" + _digest(material)[:20].upper()
                ),
                "source_symbol_id": symbol_id,
                "proposed_name": proposed,
                "confidence": float(confidence),
                "evidence": evidence,
                "note": note,
            }
        )

    # Exact duplicate candidate rows collapse deterministically.
    unique = {
        row["candidate_id"]: row
        for row in normalized
    }
    normalized = sorted(
        unique.values(),
        key=lambda row: (
            row["source_symbol_id"],
            row["proposed_name"],
            -row["confidence"],
            row["candidate_id"],
        ),
    )

    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for row in normalized:
        by_symbol.setdefault(row["source_symbol_id"], []).append(row)

    proposals: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for symbol_id in sorted(by_symbol):
        options = by_symbol[symbol_id]
        names = sorted({row["proposed_name"] for row in options})
        symbol = symbols[symbol_id]
        if len(names) != 1:
            conflicts.append(
                {
                    "source_symbol_id": symbol_id,
                    "current_name": symbol.get("current_name"),
                    "kind": symbol.get("kind"),
                    "reason": "conflicting_proposed_names",
                    "options": [
                        {
                            "candidate_id": row["candidate_id"],
                            "proposed_name": row["proposed_name"],
                            "confidence": row["confidence"],
                        }
                        for row in options
                    ],
                }
            )
            continue

        name = names[0]
        candidate_ids = sorted(row["candidate_id"] for row in options)
        combined_evidence = _evidence(
            [
                evidence
                for row in options
                for evidence in row["evidence"]
            ]
        )
        confidence = max(row["confidence"] for row in options)
        material = {
            "inventory_id": inventory_id,
            "source_symbol_id": symbol_id,
            "proposed_name": name,
            "candidate_ids": candidate_ids,
        }
        proposals.append(
            {
                "proposal_id": (
                    "SRCPROP_" + _digest(material)[:20].upper()
                ),
                "source_symbol_id": symbol_id,
                "source_method_id": symbol.get("source_method_id"),
                "canonical_method_id": symbol.get("canonical_method_id"),
                "kind": symbol.get("kind"),
                "current_name": symbol.get("current_name"),
                "declared_type": symbol.get("declared_type"),
                "proposed_name": name,
                "confidence": confidence,
                "candidate_ids": candidate_ids,
                "evidence": combined_evidence,
                "status": "REVIEWABLE",
            }
        )

    review_material = {
        "inventory_id": inventory_id,
        "source_tree_sha256": source_tree_sha,
        "proposals": [
            (row["proposal_id"], row["source_symbol_id"], row["proposed_name"])
            for row in proposals
        ],
        "conflicts": [
            (
                row["source_symbol_id"],
                tuple(
                    sorted(
                        option["proposed_name"]
                        for option in row["options"]
                    )
                ),
            )
            for row in conflicts
        ],
    }
    return {
        "schema_version": 1,
        "kind": "source_name_review",
        "canonical": False,
        "review_id": (
            "SRCREVIEW_" + _digest(review_material)[:20].upper()
        ),
        "inventory_id": inventory_id,
        "workspace_id": inventory.get("workspace_id"),
        "build_id": inventory.get("build_id"),
        "source_tree_sha256": source_tree_sha,
        "summary": {
            "candidate_rows": len(normalized),
            "symbols_targeted": len(by_symbol),
            "reviewable_proposals": len(proposals),
            "conflicts": len(conflicts),
        },
        "proposals": proposals,
        "conflicts": conflicts,
    }


def write_source_name_review(
    review: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            review,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
