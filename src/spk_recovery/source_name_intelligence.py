from __future__ import annotations

import re
from typing import Any


class SourceNameIntelligenceError(ValueError):
    pass


_SPECIAL_SINGLE_PARAMETER_NAMES = {
    "addFriend": "nameKey",
    "removeFriend": "nameKey",
    "addIgnore": "nameKey",
    "removeIgnore": "nameKey",
}

_SETTER = re.compile(r"^set([A-Z][A-Za-z0-9_$]*)$")


def _lower_camel(value: str) -> str:
    if not value:
        return value
    if len(value) >= 2 and value[0].isupper() and value[1].isupper():
        return value
    return value[0].lower() + value[1:]


def _accepted_methods(
    member_lineage: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in member_lineage.get("members", []):
        if not isinstance(row, dict):
            continue
        if row.get("kind") != "method":
            continue
        if row.get("semantic_status") != "ACCEPTED":
            continue
        member_id = row.get("member_id")
        semantic = row.get("semantic_name")
        if (
            isinstance(member_id, str)
            and member_id
            and isinstance(semantic, str)
            and semantic
        ):
            out[member_id] = row
    return out


def _simple_type_name(declared_type: str) -> str | None:
    text = declared_type.strip()
    if not text:
        return None
    text = re.sub(r"<.*>", "", text)
    text = text.replace("[]", "").strip()
    if not text:
        return None
    simple = text.rsplit(".", 1)[-1].rsplit("$", 1)[-1]
    if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", simple):
        return None
    return simple


def _structural_symbol_proposal(
    symbol: dict[str, Any],
) -> tuple[str, float, list[dict[str, str]], str] | None:
    kind = symbol.get("kind")
    declared = str(symbol.get("declared_type", ""))
    simple = _simple_type_name(declared)
    if simple is None:
        return None

    if kind == "catch":
        if simple.endswith("Exception"):
            return (
                "exception",
                0.94,
                [
                    {
                        "family": "source_symbol_kind",
                        "detail": "R6A identifies this source symbol as a catch variable.",
                    },
                    {
                        "family": "declared_type_role",
                        "detail": f"Declared catch type is {declared!r}.",
                    },
                ],
                (
                    "Conventional catch-variable role name inferred from the "
                    "R6A symbol kind and declared exception type."
                ),
            )
        if simple.endswith("Error"):
            return (
                "error",
                0.94,
                [
                    {
                        "family": "source_symbol_kind",
                        "detail": "R6A identifies this source symbol as a catch variable.",
                    },
                    {
                        "family": "declared_type_role",
                        "detail": f"Declared catch type is {declared!r}.",
                    },
                ],
                "Conventional catch-variable role name inferred from declared error type.",
            )
        if simple == "Throwable":
            return (
                "throwable",
                0.92,
                [
                    {
                        "family": "source_symbol_kind",
                        "detail": "R6A identifies this source symbol as a catch variable.",
                    },
                    {
                        "family": "declared_type_role",
                        "detail": "Declared catch type is Throwable.",
                    },
                ],
                "Conventional catch-variable role name inferred from declared type.",
            )

    if kind == "resource":
        excluded = {
            "Object", "String", "Integer", "Long", "Boolean",
            "Double", "Float", "Short", "Byte", "Character",
        }
        if simple not in excluded:
            proposed = _lower_camel(simple)
            if proposed:
                return (
                    proposed,
                    0.88,
                    [
                        {
                            "family": "source_symbol_kind",
                            "detail": (
                                "R6A identifies this source symbol as a "
                                "try-with-resources variable."
                            ),
                        },
                        {
                            "family": "declared_type_role",
                            "detail": f"Declared resource type is {declared!r}.",
                        },
                    ],
                    (
                        "Readable resource name derived from the declared "
                        "try-with-resources type; inferred, not original text."
                    ),
                )

    if kind == "enhanced_for":
        excluded = {
            "Object", "String", "Integer", "Long", "Boolean",
            "Double", "Float", "Short", "Byte", "Character",
            "int", "long", "boolean", "double", "float",
            "short", "byte", "char",
        }
        if simple not in excluded:
            proposed = _lower_camel(simple)
            if proposed:
                return (
                    proposed,
                    0.86,
                    [
                        {
                            "family": "source_symbol_kind",
                            "detail": (
                                "R6A identifies this source symbol as an "
                                "enhanced-for element variable."
                            ),
                        },
                        {
                            "family": "declared_type_role",
                            "detail": (
                                f"Enhanced-for element type is {declared!r}."
                            ),
                        },
                    ],
                    (
                        "Element-role name derived from an informative declared "
                        "enhanced-for type; inferred, not original text."
                    ),
                )

    return None


def _parameter_groups(
    inventory: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in inventory.get("symbols", []):
        if not isinstance(row, dict):
            continue
        if row.get("kind") != "parameter":
            continue
        method_id = row.get("canonical_method_id")
        if not isinstance(method_id, str) or not method_id:
            continue
        groups.setdefault(method_id, []).append(row)

    for rows in groups.values():
        rows.sort(
            key=lambda row: (
                int(row.get("ordinal", 0)),
                str(row.get("source_symbol_id", "")),
            )
        )
    return groups


def _proposal_for_method(
    method: dict[str, Any],
    parameters: list[dict[str, Any]],
) -> tuple[str, float, list[dict[str, str]], str] | None:
    semantic = str(method.get("semantic_name", ""))

    if len(parameters) == 1 and semantic in _SPECIAL_SINGLE_PARAMETER_NAMES:
        proposed = _SPECIAL_SINGLE_PARAMETER_NAMES[semantic]
        return (
            proposed,
            0.97,
            [
                {
                    "family": "accepted_method_semantics",
                    "detail": (
                        f"Canonical method has accepted semantic name "
                        f"{semantic!r}."
                    ),
                },
                {
                    "family": "single_parameter_role",
                    "detail": (
                        "Method has exactly one recovered source parameter; "
                        "exact client behavior uses it as the encoded player "
                        "name key."
                    ),
                },
            ],
            (
                "High-confidence role name derived from accepted canonical "
                "method semantics; not claimed as original source text."
            ),
        )

    match = _SETTER.fullmatch(semantic)
    if len(parameters) == 1 and match is not None:
        proposed = _lower_camel(match.group(1))
        if not proposed:
            return None
        return (
            proposed,
            0.93,
            [
                {
                    "family": "accepted_method_semantics",
                    "detail": (
                        f"Canonical method has accepted setter semantic name "
                        f"{semantic!r}."
                    ),
                },
                {
                    "family": "setter_parameter_role",
                    "detail": (
                        "Single parameter supplies the value named by the "
                        "accepted setter property."
                    ),
                },
            ],
            (
                "Setter-derived readable parameter name; inferred, not "
                "recovered original text."
            ),
        )

    return None


def build_source_name_candidates(
    inventory: dict[str, Any],
    member_lineage: dict[str, Any],
) -> dict[str, Any]:
    """Produce conservative R6B source-parameter naming candidates.

    Only source parameters tied to canonical methods with ACCEPTED semantic
    method names are eligible. Locals/catch/resource/loop variables are not
    guessed by this stage.
    """
    if (
        inventory.get("schema_version") != 1
        or inventory.get("kind") != "source_symbol_inventory"
    ):
        raise SourceNameIntelligenceError(
            "unsupported source symbol inventory"
        )
    inventory_id = inventory.get("inventory_id")
    tree_sha = inventory.get("source_tree_sha256")
    if not isinstance(inventory_id, str) or not inventory_id:
        raise SourceNameIntelligenceError(
            "inventory has no inventory_id"
        )
    if not isinstance(tree_sha, str) or not tree_sha:
        raise SourceNameIntelligenceError(
            "inventory has no source_tree_sha256"
        )

    methods = _accepted_methods(member_lineage)
    parameters = _parameter_groups(inventory)
    candidates: list[dict[str, Any]] = []

    for member_id in sorted(parameters):
        method = methods.get(member_id)
        if method is None:
            continue
        rows = parameters[member_id]
        proposal = _proposal_for_method(method, rows)
        if proposal is None:
            continue
        if len(rows) != 1:
            continue

        proposed, confidence, evidence, note = proposal
        symbol = rows[0]
        if proposed == symbol.get("current_name"):
            continue

        candidates.append(
            {
                "source_symbol_id": symbol["source_symbol_id"],
                "proposed_name": proposed,
                "confidence": confidence,
                "evidence": evidence,
                "note": note,
            }
        )

    for symbol in inventory.get("symbols", []):
        if not isinstance(symbol, dict):
            continue
        if symbol.get("kind") not in {"catch", "resource", "enhanced_for"}:
            continue
        proposal = _structural_symbol_proposal(symbol)
        if proposal is None:
            continue
        proposed, confidence, evidence, note = proposal
        if proposed == symbol.get("current_name"):
            continue
        candidates.append(
            {
                "source_symbol_id": symbol["source_symbol_id"],
                "proposed_name": proposed,
                "confidence": confidence,
                "evidence": evidence,
                "note": note,
            }
        )
    candidates.sort(
        key=lambda row: (
            row["source_symbol_id"],
            row["proposed_name"],
        )
    )
    return {
        "schema_version": 1,
        "kind": "source_name_candidate_set",
        "canonical": False,
        "inventory_id": inventory_id,
        "source_tree_sha256": tree_sha,
        "candidates": candidates,
    }


def build_source_name_candidate_diagnostics(
    inventory: dict[str, Any],
    member_lineage: dict[str, Any],
    candidate_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return producer diagnostics separately from the strict R6B schema."""
    if candidate_set is None:
        candidate_set = build_source_name_candidates(
            inventory,
            member_lineage,
        )
    symbols = {
        row.get("source_symbol_id"): row
        for row in inventory.get("symbols", [])
        if isinstance(row, dict)
    }
    kinds: dict[str, int] = {}
    for row in candidate_set.get("candidates", []):
        symbol = symbols.get(row.get("source_symbol_id"))
        kind = (
            str(symbol.get("kind"))
            if isinstance(symbol, dict)
            else "unknown"
        )
        kinds[kind] = kinds.get(kind, 0) + 1

    return {
        "schema_version": 1,
        "kind": "source_name_candidate_diagnostics",
        "canonical": False,
        "inventory_id": inventory.get("inventory_id"),
        "source_tree_sha256": inventory.get(
            "source_tree_sha256"
        ),
        "accepted_methods_available": len(
            _accepted_methods(member_lineage)
        ),
        "parameter_methods_seen": len(
            _parameter_groups(inventory)
        ),
        "candidate_count": len(
            candidate_set.get("candidates", [])
        ),
        "candidate_kinds": dict(sorted(kinds.items())),
        "ordinary_locals_considered": 0,
    }
