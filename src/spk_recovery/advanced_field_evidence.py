from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from .bytecode_profile import profile_jar_class
from .field_identity_advanced import (
    match_constant_values,
    match_unique_contexts,
    remove_resolved_fields,
    select_dominant_alignment_votes,
)
from .indexer import sha256_file
from .lineage import load_lineage, validate_lineage
from .member_identity import _descriptor_identity_shape
from .member_lineage import load_member_lineage, validate_member_lineage


class AdvancedFieldEvidenceError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _build(class_lineage: dict[str, Any], build_id: str) -> dict[str, Any]:
    hits = [
        row
        for row in class_lineage.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(hits) != 1:
        raise AdvancedFieldEvidenceError(
            f"expected one canonical build {build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _class_entries(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for record in class_lineage.get("classes", []):
        logical_id = str(record.get("logical_id"))
        for entry in record.get("lineage", []):
            if entry.get("build_id") != build_id:
                continue
            internal = entry.get("internal_name")
            if not isinstance(internal, str) or not internal:
                raise AdvancedFieldEvidenceError(
                    f"{logical_id}.{build_id}: invalid internal class name"
                )
            out[logical_id] = (internal, logical_id)
    return out


def _owner_to_logical(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, str]:
    return {
        internal: logical_id
        for logical_id, (internal, _same) in _class_entries(
            class_lineage,
            build_id,
        ).items()
    }


def _aliases(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, str]:
    return _owner_to_logical(class_lineage, build_id)


def _method_maps(
    member_lineage: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
) -> tuple[
    dict[str, dict[tuple[str, str], str]],
    dict[str, dict[tuple[str, str], str]],
]:
    old: dict[str, dict[tuple[str, str], str]] = defaultdict(dict)
    new: dict[str, dict[tuple[str, str], str]] = defaultdict(dict)

    for record in member_lineage.get("members", []):
        if record.get("kind") != "method":
            continue
        member_id = str(record.get("member_id"))
        old_hits = [
            entry
            for entry in record.get("lineage", [])
            if entry.get("build_id") == old_build_id
        ]
        new_hits = [
            entry
            for entry in record.get("lineage", [])
            if entry.get("build_id") == new_build_id
        ]
        if len(old_hits) != 1 or len(new_hits) != 1:
            continue

        old_entry, new_entry = old_hits[0], new_hits[0]
        old_owner = str(old_entry.get("owner_internal_name"))
        new_owner = str(new_entry.get("owner_internal_name"))
        old[old_owner][
            (
                str(old_entry.get("name")),
                str(old_entry.get("descriptor")),
            )
        ] = member_id
        new[new_owner][
            (
                str(new_entry.get("name")),
                str(new_entry.get("descriptor")),
            )
        ] = member_id

    return dict(old), dict(new)


def _coord(value: Any, *, label: str) -> tuple[str, str]:
    if not isinstance(value, dict):
        raise AdvancedFieldEvidenceError(f"{label} must be an object")
    name = value.get("name")
    descriptor = value.get("descriptor")
    if not isinstance(name, str) or not isinstance(descriptor, str):
        raise AdvancedFieldEvidenceError(
            f"{label} requires name and descriptor strings"
        )
    return name, descriptor


def _frontier(
    member_lineage: dict[str, Any],
    *,
    new_build_id: str,
) -> dict[
    tuple[str, str],
    dict[str, set[tuple[str, str]]],
]:
    groups: dict[
        tuple[str, str],
        dict[str, set[tuple[str, str]]],
    ] = {}

    for item in member_lineage.get("unresolved", []):
        if not isinstance(item, dict):
            continue
        if item.get("new_build_id") != new_build_id:
            continue
        if item.get("kind") != "member_identity_review":
            continue
        if item.get("member_kind") != "field":
            continue
        candidate = item.get("candidate")
        if not isinstance(candidate, dict):
            continue

        old_owner = str(candidate.get("old_owner", "")).removesuffix(
            ".class"
        )
        new_owner = str(candidate.get("new_owner", "")).removesuffix(
            ".class"
        )
        if not old_owner or not new_owner:
            raise AdvancedFieldEvidenceError(
                "field frontier candidate lacks owner"
            )

        group = groups.setdefault(
            (old_owner, new_owner),
            {"old": set(), "new": set()},
        )
        group["old"].add(_coord(candidate.get("old"), label="candidate.old"))
        group["new"].add(_coord(candidate.get("new"), label="candidate.new"))

    return groups


def _field_lookup(profile: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (
            str(field.get("name")),
            str(field.get("descriptor")),
        ): field
        for field in profile.get("fields", [])
        if isinstance(field, dict)
    }


def _method_lookup(profile: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (
            str(method.get("name")),
            str(method.get("descriptor")),
        ): method
        for method in profile.get("methods", [])
        if isinstance(method, dict)
    }


def _instruction_contexts(
    profile: dict[str, Any],
    method_map: dict[tuple[str, str], str],
    allowed: set[tuple[str, str]],
) -> dict[tuple[str, str], Any]:
    out: dict[tuple[str, str], list[Any]] = defaultdict(list)
    owner = str(profile.get("internal_name", ""))

    for method in profile.get("methods", []):
        if not isinstance(method, dict):
            continue
        method_id = method_map.get(
            (
                str(method.get("name")),
                str(method.get("descriptor")),
            )
        )
        if method_id is None:
            continue

        instructions = [
            row
            for row in method.get("instructions", [])
            if isinstance(row, dict)
        ]
        by_offset = {
            row.get("offset"): index
            for index, row in enumerate(instructions)
        }

        own_ordinal = 0
        for access in method.get("field_accesses", []):
            if not isinstance(access, dict):
                continue
            if access.get("owner") != owner:
                continue
            coord = (
                str(access.get("name")),
                str(access.get("descriptor")),
            )
            index = by_offset.get(access.get("offset"))
            if coord in allowed and isinstance(index, int):
                before = tuple(
                    str(row.get("mnemonic"))
                    for row in instructions[max(0, index - 2):index]
                )
                after = tuple(
                    str(row.get("mnemonic"))
                    for row in instructions[index + 1:index + 3]
                )
                out[coord].append(
                    (
                        method_id,
                        str(access.get("operation")),
                        own_ordinal,
                        before,
                        after,
                    )
                )
            own_ordinal += 1

    return {
        coord: tuple(sorted(rows, key=repr))
        for coord, rows in out.items()
        if len(rows) >= 2
    }


def _alignment_votes(
    old_profile: dict[str, Any],
    new_profile: dict[str, Any],
    old_methods: dict[tuple[str, str], str],
    new_methods: dict[tuple[str, str], str],
    old_allowed: set[tuple[str, str]],
    new_allowed: set[tuple[str, str]],
    old_aliases: dict[str, str],
    new_aliases: dict[str, str],
) -> list[dict[str, Any]]:
    old_by_id = {
        member_id: method
        for coord, member_id in old_methods.items()
        if (method := _method_lookup(old_profile).get(coord)) is not None
    }
    new_by_id = {
        member_id: method
        for coord, member_id in new_methods.items()
        if (method := _method_lookup(new_profile).get(coord)) is not None
    }

    counts: Counter[tuple[tuple[str, str], tuple[str, str]]] = Counter()
    old_owner = str(old_profile.get("internal_name", ""))
    new_owner = str(new_profile.get("internal_name", ""))

    for member_id in sorted(set(old_by_id) & set(new_by_id)):
        old_seq = [
            row
            for row in old_by_id[member_id].get("field_accesses", [])
            if isinstance(row, dict)
            and row.get("owner") == old_owner
        ]
        new_seq = [
            row
            for row in new_by_id[member_id].get("field_accesses", [])
            if isinstance(row, dict)
            and row.get("owner") == new_owner
        ]
        if not old_seq or len(old_seq) != len(new_seq):
            continue

        pairs = list(zip(old_seq, new_seq))
        if any(
            old_row.get("operation") != new_row.get("operation")
            or _descriptor_identity_shape(
                str(old_row.get("descriptor", "")),
                old_aliases,
            ) != _descriptor_identity_shape(
                str(new_row.get("descriptor", "")),
                new_aliases,
            )
            for old_row, new_row in pairs
        ):
            continue

        for old_row, new_row in pairs:
            old_coord = (
                str(old_row.get("name")),
                str(old_row.get("descriptor")),
            )
            new_coord = (
                str(new_row.get("name")),
                str(new_row.get("descriptor")),
            )
            if old_coord not in old_allowed or new_coord not in new_allowed:
                continue
            counts[(old_coord, new_coord)] += 1

    rows = [
        {"old": old, "new": new, "count": count}
        for (old, new), count in counts.items()
    ]
    return select_dominant_alignment_votes(rows)


def _candidate(
    logical_id: str,
    old_owner: str,
    new_owner: str,
    row: dict[str, Any],
) -> dict[str, Any]:
    return {
        "logical_class_id": logical_id,
        "old_owner": old_owner,
        "new_owner": new_owner,
        "old": {
            "name": str(row["old"].get("name")),
            "descriptor": str(row["old"].get("descriptor")),
        },
        "new": {
            "name": str(row["new"].get("name")),
            "descriptor": str(row["new"].get("descriptor")),
        },
        "strategy": str(row.get("strategy")),
        "score": float(row.get("score", 0.0)),
        "confidence": str(row.get("confidence", "INFERRED_HIGH")),
        "evidence": {
            key: copy.deepcopy(value)
            for key, value in row.items()
            if key not in {"old", "new", "strategy", "score", "confidence"}
        },
    }


def build_advanced_field_evidence(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    *,
    old_build_id: str,
    new_build_id: str,
) -> dict[str, Any]:
    validate_lineage(class_lineage)
    validate_member_lineage(member_lineage, class_lineage=class_lineage)

    old_sha = sha256_file(old_jar.resolve())
    new_sha = sha256_file(new_jar.resolve())
    if old_sha.lower() != str(old_index.get("sha256", "")).lower():
        raise AdvancedFieldEvidenceError("old JAR SHA does not match old index")
    if new_sha.lower() != str(new_index.get("sha256", "")).lower():
        raise AdvancedFieldEvidenceError("new JAR SHA does not match new index")
    if old_sha.lower() != str(
        _build(class_lineage, old_build_id).get("sha256", "")
    ).lower():
        raise AdvancedFieldEvidenceError(
            "old JAR SHA does not match canonical old build"
        )
    if new_sha.lower() != str(
        _build(class_lineage, new_build_id).get("sha256", "")
    ).lower():
        raise AdvancedFieldEvidenceError(
            "new JAR SHA does not match canonical new build"
        )

    frontier = _frontier(member_lineage, new_build_id=new_build_id)
    old_owner_ids = _owner_to_logical(class_lineage, old_build_id)
    new_owner_ids = _owner_to_logical(class_lineage, new_build_id)
    old_aliases = _aliases(class_lineage, old_build_id)
    new_aliases = _aliases(class_lineage, new_build_id)
    old_method_maps, new_method_maps = _method_maps(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )

    candidates: list[dict[str, Any]] = []
    strategy_counts: Counter[str] = Counter()
    input_fields = sum(len(group["old"]) for group in frontier.values())

    for (old_owner, new_owner), group in sorted(frontier.items()):
        logical_id = old_owner_ids.get(old_owner)
        if logical_id is None or new_owner_ids.get(new_owner) != logical_id:
            raise AdvancedFieldEvidenceError(
                "frontier owner pair is not one canonical logical class"
            )

        old_profile = profile_jar_class(old_jar, old_owner + ".class")
        new_profile = profile_jar_class(new_jar, new_owner + ".class")
        old_lookup = _field_lookup(old_profile)
        new_lookup = _field_lookup(new_profile)

        old_fields = [
            old_lookup[coord]
            for coord in sorted(group["old"])
            if coord in old_lookup
        ]
        new_fields = [
            new_lookup[coord]
            for coord in sorted(group["new"])
            if coord in new_lookup
        ]
        if len(old_fields) != len(group["old"]) or len(new_fields) != len(group["new"]):
            raise AdvancedFieldEvidenceError(
                "frontier field coordinate missing from exact JAR profile"
            )

        constant = match_constant_values(
            old_fields,
            new_fields,
            old_aliases=old_aliases,
            new_aliases=new_aliases,
        )
        remaining_old = remove_resolved_fields(old_fields, constant, side="old")
        remaining_new = remove_resolved_fields(new_fields, constant, side="new")

        old_remaining_coords = {
            (str(row.get("name")), str(row.get("descriptor")))
            for row in remaining_old
        }
        new_remaining_coords = {
            (str(row.get("name")), str(row.get("descriptor")))
            for row in remaining_new
        }
        old_contexts = _instruction_contexts(
            old_profile,
            old_method_maps.get(old_owner, {}),
            old_remaining_coords,
        )
        new_contexts = _instruction_contexts(
            new_profile,
            new_method_maps.get(new_owner, {}),
            new_remaining_coords,
        )
        context = match_unique_contexts(
            remaining_old,
            remaining_new,
            old_contexts=old_contexts,
            new_contexts=new_contexts,
            old_aliases=old_aliases,
            new_aliases=new_aliases,
            strategy="canonical_method_instruction_context",
            score=0.99,
        )

        remaining_old = remove_resolved_fields(remaining_old, context, side="old")
        remaining_new = remove_resolved_fields(remaining_new, context, side="new")
        old_remaining_coords = {
            (str(row.get("name")), str(row.get("descriptor")))
            for row in remaining_old
        }
        new_remaining_coords = {
            (str(row.get("name")), str(row.get("descriptor")))
            for row in remaining_new
        }

        voted = _alignment_votes(
            old_profile,
            new_profile,
            old_method_maps.get(old_owner, {}),
            new_method_maps.get(new_owner, {}),
            old_remaining_coords,
            new_remaining_coords,
            old_aliases,
            new_aliases,
        )
        alignment = [
            {
                **row,
                "old": old_lookup[row["old"]],
                "new": new_lookup[row["new"]],
            }
            for row in voted
            if row["old"] in old_lookup and row["new"] in new_lookup
        ]

        for row in [*constant, *context, *alignment]:
            candidates.append(
                _candidate(
                    logical_id,
                    old_owner,
                    new_owner,
                    row,
                )
            )
            strategy_counts[str(row.get("strategy"))] += 1

    candidates.sort(
        key=lambda row: (
            row["logical_class_id"],
            row["old_owner"],
            row["old"]["name"],
            row["old"]["descriptor"],
        )
    )
    resolved = len(candidates)
    material = {
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "input_unresolved_fields": input_fields,
        "candidates": candidates,
    }
    return {
        "schema_version": 1,
        "kind": "advanced_field_identity_candidates",
        "canonical": False,
        "report_id": (
            "ADVFIELDCAND_"
            + _stable_digest(material)[:20].upper()
        ),
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "summary": {
            "input_unresolved_fields": input_fields,
            "class_pairs": len(frontier),
            "candidate_fields": resolved,
            "remaining_unresolved_fields": input_fields - resolved,
            "constant_value_exact": strategy_counts["constant_value_exact"],
            "canonical_method_instruction_context": strategy_counts[
                "canonical_method_instruction_context"
            ],
            "aligned_instruction_votes": strategy_counts[
                "aligned_instruction_votes"
            ],
        },
        "candidates": candidates,
        "note": (
            "Research-only evidence. canonical=false. No member lineage "
            "relationship is appended by this report."
        ),
    }


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AdvancedFieldEvidenceError(f"JSON root must be object: {path}")
    return value


def write_report(report: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-advanced-field-evidence")
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("old_index", type=Path)
    p.add_argument("new_index", type=Path)
    p.add_argument("old_jar", type=Path)
    p.add_argument("new_jar", type=Path)
    p.add_argument("--old-build-id", required=True)
    p.add_argument("--new-build-id", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = build_advanced_field_evidence(
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.old_index),
            _load(args.new_index),
            args.old_jar,
            args.new_jar,
            old_build_id=args.old_build_id,
            new_build_id=args.new_build_id,
        )
        write_report(report, args.out)
    except Exception as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_ADVANCED_FIELD_EVIDENCE_PASS")
    print(f"report_id={report['report_id']}")
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
