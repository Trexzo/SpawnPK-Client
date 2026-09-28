from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .member_identity import _descriptor_identity_shape


class AdvancedFieldIdentityError(ValueError):
    pass


def _shape(
    field: dict[str, Any],
    aliases: dict[str, str],
) -> tuple[int, str]:
    return (
        int(field.get("access", 0)),
        _descriptor_identity_shape(
            str(field.get("descriptor", "")),
            aliases,
        ),
    )


def _field_id(field: dict[str, Any]) -> tuple[str, str]:
    return (
        str(field.get("name", "")),
        str(field.get("descriptor", "")),
    )


def _unique_signature_matches(
    old_fields: list[dict[str, Any]],
    new_fields: list[dict[str, Any]],
    *,
    old_aliases: dict[str, str],
    new_aliases: dict[str, str],
    old_signature,
    new_signature,
    strategy: str,
    score: float,
) -> list[dict[str, Any]]:
    old_groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    new_groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)

    for field in old_fields:
        signature = old_signature(field)
        if signature is not None:
            old_groups[(_shape(field, old_aliases), signature)].append(field)
    for field in new_fields:
        signature = new_signature(field)
        if signature is not None:
            new_groups[(_shape(field, new_aliases), signature)].append(field)

    out: list[dict[str, Any]] = []
    for signature in set(old_groups) & set(new_groups):
        old_rows = old_groups[signature]
        new_rows = new_groups[signature]
        if len(old_rows) != 1 or len(new_rows) != 1:
            continue
        out.append(
            {
                "old": old_rows[0],
                "new": new_rows[0],
                "strategy": strategy,
                "confidence": "INFERRED_HIGH",
                "score": score,
                "signature": signature[1],
            }
        )

    out.sort(
        key=lambda row: (
            str(row["old"].get("name")),
            str(row["old"].get("descriptor")),
            str(row["new"].get("name")),
        )
    )
    return out


def match_constant_values(
    old_fields: list[dict[str, Any]],
    new_fields: list[dict[str, Any]],
    *,
    old_aliases: dict[str, str],
    new_aliases: dict[str, str],
) -> list[dict[str, Any]]:
    """Match only unique exact JVM ConstantValue identities.

    Field declaration order is deliberately ignored.
    """

    def signature(field: dict[str, Any]) -> Any:
        return field.get("constant_value")

    return _unique_signature_matches(
        old_fields,
        new_fields,
        old_aliases=old_aliases,
        new_aliases=new_aliases,
        old_signature=signature,
        new_signature=signature,
        strategy="constant_value_exact",
        score=0.995,
    )


def match_unique_contexts(
    old_fields: list[dict[str, Any]],
    new_fields: list[dict[str, Any]],
    *,
    old_contexts: dict[tuple[str, str], Any],
    new_contexts: dict[tuple[str, str], Any],
    old_aliases: dict[str, str],
    new_aliases: dict[str, str],
    strategy: str,
    score: float,
) -> list[dict[str, Any]]:
    """Match fields whose complete externally supplied context is unique.

    Context objects should already be normalized to stable class, method and
    member identities. Empty contexts carry no evidence and are ignored.
    """

    def old_signature(field: dict[str, Any]) -> Any:
        value = old_contexts.get(_field_id(field))
        return value if value else None

    def new_signature(field: dict[str, Any]) -> Any:
        value = new_contexts.get(_field_id(field))
        return value if value else None

    return _unique_signature_matches(
        old_fields,
        new_fields,
        old_aliases=old_aliases,
        new_aliases=new_aliases,
        old_signature=old_signature,
        new_signature=new_signature,
        strategy=strategy,
        score=score,
    )


def select_dominant_alignment_votes(
    votes: list[dict[str, Any]],
    *,
    min_votes: int = 2,
    min_outbound_dominance: float = 0.80,
    min_inbound_dominance: float = 0.80,
) -> list[dict[str, Any]]:
    """Select only mutually dominant instruction-alignment field votes.

    Each vote row contains old, new and count. A selected edge must dominate
    both all votes leaving its old field and all votes entering its new field.
    """
    if min_votes < 1:
        raise AdvancedFieldIdentityError("min_votes must be >= 1")
    for value, label in (
        (min_outbound_dominance, "min_outbound_dominance"),
        (min_inbound_dominance, "min_inbound_dominance"),
    ):
        if not 0.0 <= value <= 1.0:
            raise AdvancedFieldIdentityError(
                f"{label} must be in [0, 1]"
            )

    outgoing: dict[Any, Counter[Any]] = defaultdict(Counter)
    incoming: dict[Any, Counter[Any]] = defaultdict(Counter)
    details: dict[tuple[Any, Any], dict[str, Any]] = {}

    for row in votes:
        old = row.get("old")
        new = row.get("new")
        count = row.get("count")
        if (
            old is None
            or new is None
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 1
        ):
            raise AdvancedFieldIdentityError("invalid alignment vote")
        outgoing[old][new] += count
        incoming[new][old] += count
        details[(old, new)] = row

    selected: list[dict[str, Any]] = []
    for old, targets in outgoing.items():
        new, count = targets.most_common(1)[0]
        outbound_total = sum(targets.values())
        inbound_total = sum(incoming[new].values())
        out_dom = count / outbound_total
        in_dom = count / inbound_total

        reverse_old, reverse_count = incoming[new].most_common(1)[0]
        if reverse_old != old or reverse_count != count:
            continue
        if (
            count < min_votes
            or out_dom < min_outbound_dominance
            or in_dom < min_inbound_dominance
        ):
            continue

        source = details[(old, new)]
        selected.append(
            {
                **source,
                "strategy": "aligned_instruction_votes",
                "confidence": "INFERRED_HIGH",
                "score": round(
                    0.97 + 0.02 * min(out_dom, in_dom),
                    6,
                ),
                "votes": count,
                "outbound_dominance": round(out_dom, 6),
                "inbound_dominance": round(in_dom, 6),
            }
        )

    selected.sort(
        key=lambda row: (
            repr(row.get("old")),
            repr(row.get("new")),
        )
    )
    return selected


def remove_resolved_fields(
    fields: list[dict[str, Any]],
    matches: list[dict[str, Any]],
    *,
    side: str,
) -> list[dict[str, Any]]:
    """Return fields not consumed by supplied one-to-one candidates."""
    if side not in {"old", "new"}:
        raise AdvancedFieldIdentityError("side must be old or new")
    resolved = {
        _field_id(row[side])
        for row in matches
        if isinstance(row.get(side), dict)
    }
    return [
        field
        for field in fields
        if _field_id(field) not in resolved
    ]
