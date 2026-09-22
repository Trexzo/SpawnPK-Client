from __future__ import annotations

from collections import Counter
from typing import Any

from .classfile import _descriptor_shape


def _freeze(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    return value


def _multiset(values: list[Any]) -> Counter:
    return Counter(_freeze(v) for v in values)


def _declaration_payload(cls: dict[str, Any]) -> dict[str, Any]:
    return {
        "major": cls.get("major"),
        "minor": cls.get("minor"),
        "access": cls.get("access"),
        "super_name": cls.get("super_name"),
        "interfaces": list(cls.get("interfaces", [])),
        "attributes": sorted(cls.get("attributes", [])),
        "fields": sorted(
            (
                f.get("name"),
                f.get("descriptor"),
                f.get("access"),
                tuple(sorted(f.get("attributes", []))),
            )
            for f in cls.get("fields", [])
        ),
        "methods": sorted(
            (
                m.get("name"),
                m.get("descriptor"),
                m.get("access"),
                m.get("code_length"),
                tuple(sorted(m.get("attributes", []))),
            )
            for m in cls.get("methods", [])
        ),
    }


def classify_class_pair(
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    match: dict[str, Any],
) -> dict[str, Any]:
    old_path = str(match["old"])
    new_path = str(match["new"])
    old_entry = old_index.get("entries", {}).get(old_path, {})
    new_entry = new_index.get("entries", {}).get(new_path, {})
    old_cls = old_index.get("classes", {}).get(old_path, {})
    new_cls = new_index.get("classes", {}).get(new_path, {})

    old_sha = old_entry.get("sha256")
    new_sha = new_entry.get("sha256")
    structural_equal = (
        bool(old_cls.get("structural_sha256"))
        and old_cls.get("structural_sha256")
        == new_cls.get("structural_sha256")
    )
    declarations_equal = (
        _declaration_payload(old_cls)
        == _declaration_payload(new_cls)
    )
    literal_equal = (
        _multiset(list(old_cls.get("literal_strings", [])))
        == _multiset(list(new_cls.get("literal_strings", [])))
    )
    numeric_equal = (
        _multiset(list(old_cls.get("numeric_constants", [])))
        == _multiset(list(new_cls.get("numeric_constants", [])))
    )

    if old_sha and old_sha == new_sha:
        delta = "byte_identical"
    elif structural_equal:
        delta = "structurally_equivalent"
    elif (
        declarations_equal
        and (not literal_equal or not numeric_equal)
    ):
        # Conservative: the index proves declaration stability plus constant-pool
        # payload change, but does not retain full instruction semantics.
        delta = "constant_payload_candidate"
    else:
        delta = "modified_class"

    return {
        "old": old_path,
        "new": new_path,
        "identity_strategy": match.get("strategy"),
        "identity_score": match.get("score"),
        "delta": delta,
        "path_moved": old_path != new_path,
        "entry_sha_equal": bool(old_sha) and old_sha == new_sha,
        "structural_equal": structural_equal,
        "declarations_equal": declarations_equal,
        "literal_constants_equal": literal_equal,
        "numeric_constants_equal": numeric_equal,
    }


def classify_class_deltas(
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    matcher_report: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        classify_class_pair(old_index, new_index, match)
        for match in matcher_report.get("matches", [])
    ]
    rows.sort(key=lambda r: (r["old"], r["new"]))

    counts: dict[str, int] = {}
    moved = 0
    for row in rows:
        counts[row["delta"]] = counts.get(row["delta"], 0) + 1
        if row["path_moved"]:
            moved += 1

    return {
        "schema_version": 1,
        "kind": "class_delta_report",
        "old_sha256": old_index.get("sha256"),
        "new_sha256": new_index.get("sha256"),
        "summary": {
            **dict(sorted(counts.items())),
            "matched_classes": len(rows),
            "path_moved": moved,
            "ambiguous_classes": len(
                matcher_report.get("ambiguous", [])
            ),
            "unmatched_old_classes": len(
                matcher_report.get("unmatched_old", [])
            ),
            "unmatched_new_classes": len(
                matcher_report.get("unmatched_new", [])
            ),
        },
        "classes": rows,
        "ambiguous": matcher_report.get("ambiguous", []),
        "unmatched_old": matcher_report.get("unmatched_old", []),
        "unmatched_new": matcher_report.get("unmatched_new", []),
    }


def _member_delta(rel: dict[str, Any]) -> str:
    old = rel.get("old", {})
    new = rel.get("new", {})

    same_name = old.get("name") == new.get("name")
    same_descriptor = (
        old.get("descriptor") == new.get("descriptor")
    )
    same_descriptor_shape = (
        _descriptor_shape(str(old.get("descriptor", "")))
        == _descriptor_shape(str(new.get("descriptor", "")))
    )
    same_access = old.get("access") == new.get("access")
    same_code_length = (
        old.get("code_length") == new.get("code_length")
    )

    if (
        not same_name
        and same_descriptor_shape
        and same_access
        and same_code_length
    ):
        return "member_only_obfuscation_rename"
    if (
        same_name
        and same_descriptor
        and same_access
        and same_code_length
    ):
        return "member_shape_unchanged"
    return "modified_member"


def classify_member_deltas(
    candidates: dict[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    new_members: list[dict[str, Any]] = []
    removed_members: list[dict[str, Any]] = []

    for group in candidates.get("classes", []):
        old_owner = group.get("old_owner")
        new_owner = group.get("new_owner")
        for collection, kind in (
            ("fields", "field"),
            ("methods", "method"),
        ):
            section = group.get(collection, {})
            for rel in section.get("relationships", []):
                rows.append(
                    {
                        "kind": kind,
                        "old_owner": old_owner,
                        "new_owner": new_owner,
                        "old": rel.get("old"),
                        "new": rel.get("new"),
                        "strategy": rel.get("strategy"),
                        "score": rel.get("score"),
                        "delta": _member_delta(rel),
                    }
                )
            for member in section.get("unmatched_old", []):
                removed_members.append(
                    {
                        "kind": kind,
                        "owner": old_owner,
                        "member": member,
                        "classification": "removed_member_candidate",
                    }
                )
            for member in section.get("unmatched_new", []):
                new_members.append(
                    {
                        "kind": kind,
                        "owner": new_owner,
                        "member": member,
                        "classification": "new_member_candidate",
                    }
                )

    rows.sort(
        key=lambda r: (
            str(r["old_owner"]),
            r["kind"],
            str((r.get("old") or {}).get("name")),
            str((r.get("old") or {}).get("descriptor")),
        )
    )
    new_members.sort(
        key=lambda r: (
            str(r["owner"]),
            r["kind"],
            str((r["member"] or {}).get("name")),
            str((r["member"] or {}).get("descriptor")),
        )
    )
    removed_members.sort(
        key=lambda r: (
            str(r["owner"]),
            r["kind"],
            str((r["member"] or {}).get("name")),
            str((r["member"] or {}).get("descriptor")),
        )
    )

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["delta"]] = counts.get(row["delta"], 0) + 1

    return {
        "schema_version": 1,
        "kind": "member_delta_report",
        "old_sha256": candidates.get("old_sha256"),
        "new_sha256": candidates.get("new_sha256"),
        "summary": {
            **dict(sorted(counts.items())),
            "matched_members": len(rows),
            "new_member_candidates": len(new_members),
            "removed_member_candidates": len(removed_members),
            "skipped_classes": len(
                candidates.get("skipped_classes", [])
            ),
        },
        "members": rows,
        "new_member_candidates": new_members,
        "removed_member_candidates": removed_members,
        "skipped_classes": candidates.get("skipped_classes", []),
    }
