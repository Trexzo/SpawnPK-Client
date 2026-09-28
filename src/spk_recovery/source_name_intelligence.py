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


def _safe_proposed_name(value: str) -> bool:
    return (
        re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", value) is not None
        and value not in _JAVA_RESERVED
    )


def _lower_camel(value: str) -> str:
    if not value:
        return value
    if value.isupper():
        return value.lower()

    acronym = re.match(
        r"^([A-Z]+)(?=[A-Z][a-z]|$)",
        value,
    )
    if acronym is not None:
        prefix = acronym.group(1)
        return prefix.lower() + value[len(prefix):]

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




_TYPE_ROLE_EXCLUDED = {
    "Object", "String", "Integer", "Long", "Boolean",
    "Double", "Float", "Short", "Byte", "Character",
    "int", "long", "boolean", "double", "float",
    "short", "byte", "char",
}


def _informative_reference_role(
    declared_type: str,
) -> str | None:
    if "<" in declared_type or "[]" in declared_type:
        return None
    simple = _simple_type_name(declared_type)
    if simple is None or simple in _TYPE_ROLE_EXCLUDED:
        return None
    if not simple[:1].isupper():
        return None
    proposed = _lower_camel(simple)
    return proposed or None

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


def _accepted_fields_by_id(
    member_lineage: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        str(row["member_id"]): row
        for row in member_lineage.get("members", [])
        if isinstance(row, dict)
        and row.get("kind") == "field"
        and row.get("semantic_status") == "ACCEPTED"
        and isinstance(row.get("member_id"), str)
        and row.get("member_id")
        and isinstance(row.get("semantic_name"), str)
        and row.get("semantic_name")
    }


def _apply_flow_evidence(
    candidates: list[dict[str, Any]],
    inventory: dict[str, Any],
    member_lineage: dict[str, Any],
    flow_evidence: dict[str, Any],
) -> None:
    if (
        flow_evidence.get("schema_version") != 1
        or flow_evidence.get("kind")
        != "source_name_flow_evidence"
        or flow_evidence.get("canonical") is not False
    ):
        raise SourceNameIntelligenceError(
            "unsupported source name flow evidence"
        )
    if flow_evidence.get("inventory_id") != inventory.get(
        "inventory_id"
    ):
        raise SourceNameIntelligenceError(
            "flow evidence inventory_id does not match"
        )
    if flow_evidence.get(
        "source_tree_sha256"
    ) != inventory.get("source_tree_sha256"):
        raise SourceNameIntelligenceError(
            "flow evidence source tree does not match"
        )

    symbols = {
        str(row["source_symbol_id"]): row
        for row in inventory.get("symbols", [])
        if isinstance(row, dict)
        and isinstance(row.get("source_symbol_id"), str)
        and row.get("source_symbol_id")
    }
    siblings: dict[str, list[dict[str, Any]]] = {}
    for row in symbols.values():
        source_method_id = row.get("source_method_id")
        if (
            isinstance(source_method_id, str)
            and source_method_id
        ):
            siblings.setdefault(
                source_method_id,
                [],
            ).append(row)

    fields = _accepted_fields_by_id(member_lineage)
    by_symbol = {
        str(row["source_symbol_id"]): row
        for row in candidates
        if isinstance(row.get("source_symbol_id"), str)
    }
    seen_bindings: set[str] = set()

    for binding in sorted(
        (
            row
            for row in flow_evidence.get("bindings", [])
            if isinstance(row, dict)
        ),
        key=lambda row: str(
            row.get("source_symbol_id", "")
        ),
    ):
        symbol_id = binding.get("source_symbol_id")
        if not isinstance(symbol_id, str) or not symbol_id:
            raise SourceNameIntelligenceError(
                "flow binding lacks source_symbol_id"
            )
        if symbol_id in seen_bindings:
            raise SourceNameIntelligenceError(
                f"duplicate flow binding for {symbol_id}"
            )
        seen_bindings.add(symbol_id)

        symbol = symbols.get(symbol_id)
        if symbol is None:
            raise SourceNameIntelligenceError(
                f"flow binding references unknown symbol {symbol_id}"
            )
        if symbol.get("kind") not in {
            "parameter",
            "local",
        }:
            continue

        field_id = binding.get("field_member_id")
        field = (
            fields.get(field_id)
            if isinstance(field_id, str)
            else None
        )
        if field is None:
            raise SourceNameIntelligenceError(
                f"flow binding references unaccepted field {field_id!r}"
            )
        proposed = field.get("semantic_name")
        if not isinstance(proposed, str):
            raise SourceNameIntelligenceError(
                "accepted flow field lacks semantic_name"
            )
        if (
            proposed != binding.get(
                "field_semantic_name"
            )
            or field.get("owner_logical_id")
            != symbol.get("owner_logical_id")
            or binding.get("owner_logical_id")
            != symbol.get("owner_logical_id")
        ):
            raise SourceNameIntelligenceError(
                f"flow binding authority mismatch for {symbol_id}"
            )
        if not _safe_proposed_name(proposed):
            continue
        if proposed == symbol.get("current_name"):
            continue

        source_method_id = symbol.get(
            "source_method_id"
        )
        if (
            isinstance(source_method_id, str)
            and any(
                row.get("source_symbol_id") != symbol_id
                and row.get("current_name") == proposed
                for row in siblings.get(
                    source_method_id,
                    [],
                )
            )
        ):
            continue

        confidence = binding.get("confidence")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= float(confidence) < 1.0
        ):
            raise SourceNameIntelligenceError(
                f"flow binding has invalid confidence for {symbol_id}"
            )
        relations = binding.get("relations")
        if (
            not isinstance(relations, list)
            or not relations
            or any(
                relation
                not in {
                    "direct_this_field_assignment",
                    "direct_this_field_initializer",
                }
                for relation in relations
            )
        ):
            raise SourceNameIntelligenceError(
                f"flow binding has unsupported relations for {symbol_id}"
            )

        evidence = [
            {
                "family": "accepted_field_semantics",
                "detail": (
                    f"Canonical field {field_id} has accepted semantic "
                    f"name {proposed!r} on the same canonical owner."
                ),
            }
        ]
        if "direct_this_field_assignment" in relations:
            evidence.append(
                {
                    "family": "direct_this_field_assignment",
                    "detail": (
                        "Recovered AST contains a direct assignment "
                        "this.<acceptedField> = <sourceSymbol> with no "
                        "cast, transformation, or intermediate expression."
                    ),
                }
            )
        if "direct_this_field_initializer" in relations:
            evidence.append(
                {
                    "family": "direct_this_field_initializer",
                    "detail": (
                        "Recovered AST declares this ordinary local as a "
                        "direct alias of this.<acceptedField>, matched by "
                        "its exact R6A declaration position."
                    ),
                }
            )
        existing = by_symbol.get(symbol_id)
        if existing is not None:
            if existing.get("proposed_name") != proposed:
                candidates.remove(existing)
                del by_symbol[symbol_id]
                continue
            current_evidence = existing.setdefault(
                "evidence",
                [],
            )
            for row in evidence:
                if row not in current_evidence:
                    current_evidence.append(row)
            existing["confidence"] = max(
                float(existing.get("confidence", 0.0)),
                float(confidence),
            )
            existing["note"] = (
                str(existing.get("note", "")).rstrip()
                + " Direct same-owner accepted-field flow "
                "independently corroborates the role."
            ).strip()
            continue

        candidate = {
            "source_symbol_id": symbol_id,
            "proposed_name": proposed,
            "confidence": float(confidence),
            "evidence": evidence,
            "note": (
                "Role name inferred from direct same-owner accepted-field "
                "flow; inferred, not recovered original source text."
            ),
        }
        candidates.append(candidate)
        by_symbol[symbol_id] = candidate


def build_source_name_candidates(
    inventory: dict[str, Any],
    member_lineage: dict[str, Any],
    flow_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce conservative R6B source-name candidates.

    Candidate sources remain explicit and bounded: accepted method semantics,
    structural source roles, unique informative local types, and optional
    non-canonical direct-flow evidence tied to accepted same-owner fields.
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
        if not _safe_proposed_name(proposed):
            continue
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
        if not _safe_proposed_name(proposed):
            continue
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
    by_method: dict[str, list[dict[str, Any]]] = {}
    for symbol in inventory.get("symbols", []):
        if not isinstance(symbol, dict):
            continue
        source_method_id = symbol.get("source_method_id")
        if isinstance(source_method_id, str) and source_method_id:
            by_method.setdefault(source_method_id, []).append(symbol)

    for source_method_id in sorted(by_method):
        siblings = by_method[source_method_id]
        for symbol in siblings:
            if symbol.get("kind") != "local":
                continue
            declared = str(symbol.get("declared_type", ""))
            proposed = _informative_reference_role(declared)
            if proposed is None or not _safe_proposed_name(proposed):
                continue

            simple = _simple_type_name(declared)
            same_type = [
                row
                for row in siblings
                if _simple_type_name(
                    str(row.get("declared_type", ""))
                ) == simple
            ]
            if len(same_type) != 1:
                continue
            if any(
                row is not symbol
                and row.get("current_name") == proposed
                for row in siblings
            ):
                continue
            if symbol.get("current_name") == proposed:
                continue

            candidates.append(
                {
                    "source_symbol_id": symbol["source_symbol_id"],
                    "proposed_name": proposed,
                    "confidence": 0.82,
                    "evidence": [
                        {
                            "family": "source_symbol_kind",
                            "detail": (
                                "R6A identifies this source symbol as an "
                                "ordinary local variable."
                            ),
                        },
                        {
                            "family": "declared_type_role",
                            "detail": (
                                f"Local declared type is {declared!r}."
                            ),
                        },
                        {
                            "family": "method_type_uniqueness",
                            "detail": (
                                "This is the only source symbol with that "
                                "informative declared type in the method."
                            ),
                        },
                    ],
                    "note": (
                        "Unique typed-local role candidate; inferred, not "
                        "recovered original source text."
                    ),
                }
            )

    if flow_evidence is not None:
        _apply_flow_evidence(
            candidates,
            inventory,
            member_lineage,
            flow_evidence,
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


def _flow_comparison_counts(
    inventory: dict[str, Any],
    member_lineage: dict[str, Any],
    flow_evidence: dict[str, Any] | None,
) -> tuple[int, int]:
    if not isinstance(flow_evidence, dict):
        return 0, 0

    baseline = build_source_name_candidates(
        inventory,
        member_lineage,
    )
    base_by_symbol = {
        str(row["source_symbol_id"]): str(
            row["proposed_name"]
        )
        for row in baseline.get("candidates", [])
        if isinstance(row, dict)
        and isinstance(row.get("source_symbol_id"), str)
        and isinstance(row.get("proposed_name"), str)
    }
    corroborated = 0
    disagreements = 0
    for binding in flow_evidence.get("bindings", []):
        if not isinstance(binding, dict):
            continue
        symbol_id = binding.get("source_symbol_id")
        field_name = binding.get(
            "field_semantic_name"
        )
        if (
            not isinstance(symbol_id, str)
            or not isinstance(field_name, str)
            or symbol_id not in base_by_symbol
        ):
            continue
        if base_by_symbol[symbol_id] == field_name:
            corroborated += 1
        else:
            disagreements += 1
    return corroborated, disagreements


def build_source_name_candidate_diagnostics(
    inventory: dict[str, Any],
    member_lineage: dict[str, Any],
    candidate_set: dict[str, Any] | None = None,
    flow_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return producer diagnostics separately from the strict R6B schema."""
    if candidate_set is None:
        candidate_set = build_source_name_candidates(
            inventory,
            member_lineage,
            flow_evidence,
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

    flow_corroborated, flow_disagreements = (
        _flow_comparison_counts(
            inventory,
            member_lineage,
            flow_evidence,
        )
    )

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
        "ordinary_locals_considered": sum(
            1
            for row in inventory.get("symbols", [])
            if isinstance(row, dict)
            and row.get("kind") == "local"
        ),
        "flow_bindings_available": (
            len(flow_evidence.get("bindings", []))
            if isinstance(flow_evidence, dict)
            else 0
        ),
        "flow_ambiguities": (
            len(flow_evidence.get("ambiguities", []))
            if isinstance(flow_evidence, dict)
            else 0
        ),
        "flow_corroborated_candidates": (
            flow_corroborated
        ),
        "flow_semantic_disagreements": (
            flow_disagreements
        ),
    }


_CARRY_AMBIGUOUS_REASONS = {
    "new_source_method_ambiguous_or_missing",
    "target_symbol_ambiguous_or_missing",
    "target_name_collision",
    "carried_name_collision",
}

_CARRY_SOURCE_SHAPE_REASONS = {
    "source_symbol_shape_changed",
    "previous_symbol_shape_invalid",
    "target_source_method_missing",
}

_CARRY_METHOD_LINEAGE_REASONS = {
    "missing_canonical_method_identity",
    "canonical_method_missing",
    "canonical_owner_missing",
    "canonical_lineage_missing_build_relation",
    "owner_class_modified_or_unproven",
    "method_modified_or_unproven",
}


def build_source_name_carryforward_diagnostics(
    candidate_set: dict[str, Any],
    carryforward_report: dict[str, Any],
) -> dict[str, Any]:
    """Classify Chat 2 candidates against the canonical R6E carry-forward result.

    This is diagnostics only. It consumes R6E output and never transfers,
    accepts, or rewrites source names itself.
    """
    if (
        candidate_set.get("schema_version") != 1
        or candidate_set.get("kind") != "source_name_candidate_set"
    ):
        raise SourceNameIntelligenceError(
            "unsupported source name candidate set"
        )
    if (
        carryforward_report.get("schema_version") != 1
        or carryforward_report.get("kind")
        != "source_name_carryforward_report"
    ):
        raise SourceNameIntelligenceError(
            "unsupported source name carry-forward report"
        )

    transfer_by_symbol: dict[str, dict[str, Any]] = {}
    for transfer_state, key in (
        ("carried", "carried"),
        ("already_applied", "already_applied"),
    ):
        for row in carryforward_report.get(key, []):
            if not isinstance(row, dict):
                continue
            symbol_id = row.get("source_symbol_id")
            if not isinstance(symbol_id, str) or not symbol_id:
                continue
            transfer_by_symbol[symbol_id] = {
                "transfer_state": transfer_state,
                "row": row,
            }

    candidate_states: list[dict[str, Any]] = []
    candidate_summary = {
        "new_candidate": 0,
        "candidate_same_as_prior_accepted": 0,
        "candidate_changed": 0,
    }
    for candidate in sorted(
        (
            row
            for row in candidate_set.get("candidates", [])
            if isinstance(row, dict)
        ),
        key=lambda row: (
            str(row.get("source_symbol_id", "")),
            str(row.get("proposed_name", "")),
        ),
    ):
        symbol_id = str(candidate.get("source_symbol_id") or "")
        proposed_name = str(candidate.get("proposed_name") or "")
        transfer = transfer_by_symbol.get(symbol_id)
        if transfer is None:
            state = "new_candidate"
            previous_accepted_name = None
            transfer_state = None
        else:
            transfer_row = transfer["row"]
            previous_accepted_name = transfer_row.get("desired_name")
            transfer_state = transfer["transfer_state"]
            state = (
                "candidate_same_as_prior_accepted"
                if proposed_name == previous_accepted_name
                else "candidate_changed"
            )
        candidate_summary[state] += 1
        candidate_states.append(
            {
                "source_symbol_id": symbol_id,
                "proposed_name": proposed_name,
                "state": state,
                "previous_accepted_name": previous_accepted_name,
                "r6e_transfer_state": transfer_state,
            }
        )

    blocker_summary = {
        "candidate_blocked_by_source_shape_drift": 0,
        "candidate_blocked_by_method_lineage_drift": 0,
        "ambiguous_after_regeneration": 0,
        "blocked_requires_review": 0,
    }
    carryforward_blockers: list[dict[str, Any]] = []
    for row in sorted(
        (
            item
            for item in carryforward_report.get("blocked", [])
            if isinstance(item, dict)
        ),
        key=lambda item: (
            str(item.get("canonical_method_id", "")),
            str(item.get("previous_source_symbol_id", "")),
            str(item.get("reason", "")),
        ),
    ):
        reason = str(row.get("reason") or "")
        if reason in _CARRY_AMBIGUOUS_REASONS:
            state = "ambiguous_after_regeneration"
        elif reason in _CARRY_SOURCE_SHAPE_REASONS:
            state = "candidate_blocked_by_source_shape_drift"
        elif reason in _CARRY_METHOD_LINEAGE_REASONS:
            state = "candidate_blocked_by_method_lineage_drift"
        else:
            state = "blocked_requires_review"
        blocker_summary[state] += 1
        carryforward_blockers.append(
            {
                "previous_source_symbol_id": row.get(
                    "previous_source_symbol_id"
                ),
                "canonical_method_id": row.get("canonical_method_id"),
                "desired_name": row.get("desired_name"),
                "reason": reason,
                "state": state,
            }
        )

    return {
        "schema_version": 1,
        "kind": "source_name_carryforward_diagnostics",
        "canonical": False,
        "inventory_id": candidate_set.get("inventory_id"),
        "source_tree_sha256": candidate_set.get(
            "source_tree_sha256"
        ),
        "carryforward_report_id": carryforward_report.get(
            "report_id"
        ),
        "candidate_summary": candidate_summary,
        "blocker_summary": blocker_summary,
        "r6e_already_applied": len(
            carryforward_report.get("already_applied", [])
        ),
        "candidate_states": candidate_states,
        "carryforward_blockers": carryforward_blockers,
    }
