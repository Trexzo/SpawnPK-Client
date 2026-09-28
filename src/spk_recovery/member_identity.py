from __future__ import annotations

from collections import defaultdict
import hashlib
from typing import Any

from .classfile import _descriptor_shape


_ALLOWED_CLASS_STRATEGIES = {
    "exact_sha256",
    "structural_unique",
    "weighted_mutual_best",
    "canonical_lineage",
}


def _descriptor_identity_shape(
    descriptor: str,
    aliases: dict[str, str] | None,
) -> str:
    """Preserve useful type distinctions while surviving known class renames.

    Known rs/** classes are rewritten to the same research token on both builds.
    External/JDK classes retain their exact internal name. Unknown rs/** classes
    are conservatively collapsed because their obfuscated path may have moved.
    """
    aliases = aliases or {}
    out: list[str] = []
    i = 0
    while i < len(descriptor):
        ch = descriptor[i]
        if ch == "L":
            semi = descriptor.find(";", i)
            if semi < 0:
                return descriptor
            internal = descriptor[i + 1 : semi]
            if internal in aliases:
                token = "@" + aliases[internal]
            elif internal.startswith("rs/"):
                token = "rs/?"
            else:
                token = internal
            out.append("L" + token + ";")
            i = semi + 1
        elif ch == "[":
            out.append("[")
            i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _member_id(
    old_owner: str,
    kind: str,
    old_name: str,
    old_descriptor: str,
    new_owner: str,
    new_name: str,
    new_descriptor: str,
) -> str:
    raw = (
        f"{old_owner}:{kind}:{old_name}:{old_descriptor}"
        f"->{new_owner}:{new_name}:{new_descriptor}"
    ).encode("utf-8")
    return "MEMREL_" + hashlib.sha256(raw).hexdigest()[:16].upper()


def _members(cls: dict, kind: str) -> list[dict]:
    values = list(cls.get(kind, []))
    if kind == "methods":
        values = [
            value
            for value in values
            if value.get("name") not in ("<init>", "<clinit>")
        ]
    return values


def _stable_key(
    member: dict,
    kind: str,
    aliases: dict[str, str] | None,
) -> tuple[Any, ...]:
    key: tuple[Any, ...] = (
        member.get("name"),
        _descriptor_identity_shape(
            str(member.get("descriptor", "")),
            aliases,
        ),
        int(member.get("access", 0)),
    )
    if kind == "methods":
        key += (member.get("code_length"),)
    return key


def _structural_key(
    member: dict,
    kind: str,
    aliases: dict[str, str] | None,
) -> tuple[Any, ...]:
    key: tuple[Any, ...] = (
        int(member.get("access", 0)),
        _descriptor_identity_shape(
            str(member.get("descriptor", "")),
            aliases,
        ),
        tuple(sorted(member.get("attributes", []))),
    )
    if kind == "methods":
        key += (member.get("code_length"),)
    return key


def _unique_buckets(
    members: list[dict],
    key_fn,
    excluded: set[int] | None = None,
) -> dict[tuple[Any, ...], int]:
    excluded = excluded or set()
    buckets: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    for index, member in enumerate(members):
        if index in excluded:
            continue
        buckets[key_fn(member)].append(index)
    return {
        key: indexes[0]
        for key, indexes in buckets.items()
        if len(indexes) == 1
    }


def _record(
    old_owner: str,
    new_owner: str,
    kind: str,
    old_member: dict,
    new_member: dict,
    strategy: str,
) -> dict:
    renamed = old_member.get("name") != new_member.get("name")
    if strategy == "stable_symbol":
        score = 0.999
        confidence = "CROSS_BUILD"
    elif kind == "methods":
        score = 0.990
        confidence = "INFERRED_HIGH"
    else:
        score = 0.970
        confidence = "INFERRED_HIGH"

    return {
        "relationship_id": _member_id(
            old_owner,
            kind,
            str(old_member.get("name", "")),
            str(old_member.get("descriptor", "")),
            new_owner,
            str(new_member.get("name", "")),
            str(new_member.get("descriptor", "")),
        ),
        "kind": kind[:-1],
        "old_owner": old_owner,
        "new_owner": new_owner,
        "old": {
            "name": old_member.get("name"),
            "descriptor": old_member.get("descriptor"),
            "access": old_member.get("access"),
            "code_length": old_member.get("code_length"),
        },
        "new": {
            "name": new_member.get("name"),
            "descriptor": new_member.get("descriptor"),
            "access": new_member.get("access"),
            "code_length": new_member.get("code_length"),
        },
        "strategy": strategy,
        "score": score,
        "confidence": confidence,
        "renamed": renamed,
        "evidence": {
            "descriptor_shape_equal": (
                _descriptor_shape(str(old_member.get("descriptor", "")))
                == _descriptor_shape(str(new_member.get("descriptor", "")))
            ),
            "access_equal": old_member.get("access") == new_member.get("access"),
            "attributes_equal": sorted(old_member.get("attributes", []))
            == sorted(new_member.get("attributes", [])),
            "code_length_equal": (
                old_member.get("code_length") == new_member.get("code_length")
                if kind == "methods"
                else None
            ),
        },
    }


def match_members_in_class(
    old_owner: str,
    old_class: dict,
    new_owner: str,
    new_class: dict,
    *,
    kind: str,
    old_type_aliases: dict[str, str] | None = None,
    new_type_aliases: dict[str, str] | None = None,
) -> dict:
    """Match methods or fields inside one already-correlated class pair.

    This is deliberately conservative. It first transfers unique stable symbols and
    then resolves unique name-insensitive structural shapes. Remaining collisions are
    reported instead of guessed.
    """
    if kind not in {"methods", "fields"}:
        raise ValueError("kind must be 'methods' or 'fields'")

    old_members = _members(old_class, kind)
    new_members = _members(new_class, kind)
    used_old: set[int] = set()
    used_new: set[int] = set()
    relationships: list[dict] = []

    old_stable = _unique_buckets(
        old_members,
        lambda m: _stable_key(m, kind, old_type_aliases),
    )
    new_stable = _unique_buckets(
        new_members,
        lambda m: _stable_key(m, kind, new_type_aliases),
    )
    for key in sorted(set(old_stable) & set(new_stable), key=repr):
        old_i, new_i = old_stable[key], new_stable[key]
        relationships.append(
            _record(
                old_owner,
                new_owner,
                kind,
                old_members[old_i],
                new_members[new_i],
                "stable_symbol",
            )
        )
        used_old.add(old_i)
        used_new.add(new_i)

    old_structural = _unique_buckets(
        old_members,
        lambda m: _structural_key(
            m,
            kind,
            old_type_aliases,
        ),
        used_old,
    )
    new_structural = _unique_buckets(
        new_members,
        lambda m: _structural_key(
            m,
            kind,
            new_type_aliases,
        ),
        used_new,
    )
    for key in sorted(
        set(old_structural) & set(new_structural),
        key=repr,
    ):
        old_i, new_i = old_structural[key], new_structural[key]
        relationships.append(
            _record(
                old_owner,
                new_owner,
                kind,
                old_members[old_i],
                new_members[new_i],
                "structural_unique",
            )
        )
        used_old.add(old_i)
        used_new.add(new_i)

    unmatched_old = [
        {
            "name": member.get("name"),
            "descriptor": member.get("descriptor"),
            "access": member.get("access"),
            "code_length": member.get("code_length"),
        }
        for index, member in enumerate(old_members)
        if index not in used_old
    ]
    unmatched_new = [
        {
            "name": member.get("name"),
            "descriptor": member.get("descriptor"),
            "access": member.get("access"),
            "code_length": member.get("code_length"),
        }
        for index, member in enumerate(new_members)
        if index not in used_new
    ]

    relationships.sort(
        key=lambda item: (
            str(item["old"]["name"]),
            str(item["old"]["descriptor"]),
            str(item["new"]["name"]),
            str(item["new"]["descriptor"]),
        )
    )
    return {
        "kind": kind,
        "old_owner": old_owner,
        "new_owner": new_owner,
        "summary": {
            "old_count": len(old_members),
            "new_count": len(new_members),
            "matched": len(relationships),
            "stable_symbol": sum(
                1
                for item in relationships
                if item["strategy"] == "stable_symbol"
            ),
            "structural_unique": sum(
                1
                for item in relationships
                if item["strategy"] == "structural_unique"
            ),
            "renamed": sum(
                1
                for item in relationships
                if item["renamed"]
            ),
            "unmatched_old": len(unmatched_old),
            "unmatched_new": len(unmatched_new),
        },
        "relationships": relationships,
        "unmatched_old": unmatched_old,
        "unmatched_new": unmatched_new,
    }


def build_member_identity_candidates(
    old_index: dict,
    new_index: dict,
    class_match_report: dict,
) -> dict:
    """Build research-only member identity relationships.

    Class identity is treated as an input authority. Unsupported/research-only class
    strategies are skipped rather than used to bootstrap member claims.
    """
    class_relationships = []
    skipped_classes = []

    authoritative_matches = [
        match
        for match in class_match_report.get("matches", [])
        if match.get("strategy") in _ALLOWED_CLASS_STRATEGIES
        and isinstance(match.get("old"), str)
        and isinstance(match.get("new"), str)
    ]
    old_type_aliases: dict[str, str] = {}
    new_type_aliases: dict[str, str] = {}
    for match in authoritative_matches:
        old_internal = match["old"][:-6] if match["old"].endswith(".class") else match["old"]
        new_internal = match["new"][:-6] if match["new"].endswith(".class") else match["new"]
        old_type_aliases[old_internal] = old_internal
        new_type_aliases[new_internal] = old_internal

    totals = {
        "class_pairs": 0,
        "method_old": 0,
        "method_new": 0,
        "method_matched": 0,
        "method_renamed": 0,
        "field_old": 0,
        "field_new": 0,
        "field_matched": 0,
        "field_renamed": 0,
    }

    for class_match in class_match_report.get("matches", []):
        strategy = class_match.get("strategy")
        old_owner = class_match.get("old")
        new_owner = class_match.get("new")
        if (
            strategy not in _ALLOWED_CLASS_STRATEGIES
            or not isinstance(old_owner, str)
            or not isinstance(new_owner, str)
        ):
            skipped_classes.append(
                {
                    "old": old_owner,
                    "new": new_owner,
                    "strategy": strategy,
                    "reason": "class_strategy_not_member_authority",
                }
            )
            continue

        old_class = old_index.get("classes", {}).get(old_owner)
        new_class = new_index.get("classes", {}).get(new_owner)
        if not isinstance(old_class, dict) or not isinstance(new_class, dict):
            skipped_classes.append(
                {
                    "old": old_owner,
                    "new": new_owner,
                    "strategy": strategy,
                    "reason": "class_missing_from_index",
                }
            )
            continue

        methods = match_members_in_class(
            old_owner,
            old_class,
            new_owner,
            new_class,
            kind="methods",
            old_type_aliases=old_type_aliases,
            new_type_aliases=new_type_aliases,
        )
        fields = match_members_in_class(
            old_owner,
            old_class,
            new_owner,
            new_class,
            kind="fields",
            old_type_aliases=old_type_aliases,
            new_type_aliases=new_type_aliases,
        )
        totals["class_pairs"] += 1
        totals["method_old"] += methods["summary"]["old_count"]
        totals["method_new"] += methods["summary"]["new_count"]
        totals["method_matched"] += methods["summary"]["matched"]
        totals["method_renamed"] += methods["summary"]["renamed"]
        totals["field_old"] += fields["summary"]["old_count"]
        totals["field_new"] += fields["summary"]["new_count"]
        totals["field_matched"] += fields["summary"]["matched"]
        totals["field_renamed"] += fields["summary"]["renamed"]

        class_relationships.append(
            {
                "old_owner": old_owner,
                "new_owner": new_owner,
                "class_strategy": strategy,
                "class_score": class_match.get("score"),
                "methods": methods,
                "fields": fields,
            }
        )

    class_relationships.sort(
        key=lambda item: (item["old_owner"], item["new_owner"])
    )
    totals["method_coverage"] = (
        round(totals["method_matched"] / totals["method_old"], 6)
        if totals["method_old"]
        else 0.0
    )
    totals["field_coverage"] = (
        round(totals["field_matched"] / totals["field_old"], 6)
        if totals["field_old"]
        else 0.0
    )

    return {
        "schema_version": 1,
        "kind": "member_identity_candidates",
        "canonical": False,
        "old_sha256": old_index.get("sha256"),
        "new_sha256": new_index.get("sha256"),
        "summary": totals,
        "classes": class_relationships,
        "skipped_classes": skipped_classes,
    }
