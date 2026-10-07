from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import zipfile

from .classfile import parse_class
from .indexer import sha256_file
from .lineage import LineageValidationError, load_lineage, validate_lineage
from .member_identity import _descriptor_identity_shape
from .member_lineage import (
    MemberLineageError,
    load_member_lineage,
    validate_member_lineage,
)


class EmptyFieldDeclarationEvidenceError(MemberLineageError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EmptyFieldDeclarationEvidenceError(
            f"JSON root must be object: {path}"
        )
    return value


def _build(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, Any]:
    hits = [
        row
        for row in class_lineage.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(hits) != 1:
        raise EmptyFieldDeclarationEvidenceError(
            f"expected one canonical build {build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _owner_map(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for record in class_lineage.get("classes", []):
        logical_id = record.get("logical_id")
        for entry in record.get("lineage", []):
            if entry.get("build_id") != build_id:
                continue
            internal = entry.get("internal_name")
            if (
                not isinstance(logical_id, str)
                or not logical_id
                or not isinstance(internal, str)
                or not internal
            ):
                raise EmptyFieldDeclarationEvidenceError(
                    f"invalid canonical owner in build {build_id!r}"
                )
            if internal in out:
                raise EmptyFieldDeclarationEvidenceError(
                    f"duplicate canonical owner {internal!r} in {build_id!r}"
                )
            out[internal] = logical_id
    return out


def _aliases(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, str]:
    return _owner_map(class_lineage, build_id)


def _coord(
    value: Any,
    *,
    label: str,
) -> tuple[str, str, int]:
    if not isinstance(value, dict):
        raise EmptyFieldDeclarationEvidenceError(
            f"{label} must be an object"
        )
    name = value.get("name")
    descriptor = value.get("descriptor")
    access = value.get("access")
    if not isinstance(name, str) or not name:
        raise EmptyFieldDeclarationEvidenceError(
            f"{label}.name must be non-empty"
        )
    if not isinstance(descriptor, str) or not descriptor:
        raise EmptyFieldDeclarationEvidenceError(
            f"{label}.descriptor must be non-empty"
        )
    if not isinstance(access, int) or isinstance(access, bool):
        raise EmptyFieldDeclarationEvidenceError(
            f"{label}.access must be an integer"
        )
    return name, descriptor, access


def _unresolved_reviews(
    member_lineage: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in member_lineage.get("unresolved", []):
        if not isinstance(item, dict):
            continue
        if (
            item.get("kind") != "member_identity_review"
            or item.get("member_kind") != "field"
            or item.get("source") != "member_identity_candidates"
            or item.get("old_build_id") != old_build_id
            or item.get("new_build_id") != new_build_id
        ):
            continue
        candidate = item.get("candidate")
        if not isinstance(candidate, dict):
            continue
        if candidate.get("strategy") != "stable_symbol":
            continue
        relationship_id = candidate.get("relationship_id")
        if not isinstance(relationship_id, str) or not relationship_id:
            raise EmptyFieldDeclarationEvidenceError(
                "stable_symbol unresolved review lacks relationship_id"
            )
        if relationship_id in out:
            raise EmptyFieldDeclarationEvidenceError(
                f"duplicate unresolved relationship_id {relationship_id!r}"
            )
        out[relationship_id] = candidate
    return out


def _paired_field_maps(
    member_lineage: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
) -> tuple[
    dict[tuple[str, str, str], str],
    dict[tuple[str, str, str], str],
]:
    old: dict[tuple[str, str, str], str] = {}
    new: dict[tuple[str, str, str], str] = {}

    for record in member_lineage.get("members", []):
        if record.get("kind") != "field":
            continue
        member_id = record.get("member_id")
        if not isinstance(member_id, str) or not member_id:
            raise EmptyFieldDeclarationEvidenceError(
                "canonical field record lacks member_id"
            )
        old_hits = [
            row
            for row in record.get("lineage", [])
            if row.get("build_id") == old_build_id
        ]
        new_hits = [
            row
            for row in record.get("lineage", [])
            if row.get("build_id") == new_build_id
        ]
        if len(old_hits) > 1 or len(new_hits) > 1:
            raise EmptyFieldDeclarationEvidenceError(
                f"{member_id}: duplicate old/new field relation"
            )
        if not old_hits or not new_hits:
            continue

        old_entry = old_hits[0]
        new_entry = new_hits[0]
        old_key = (
            str(old_entry.get("owner_internal_name")),
            str(old_entry.get("name")),
            str(old_entry.get("descriptor")),
        )
        new_key = (
            str(new_entry.get("owner_internal_name")),
            str(new_entry.get("name")),
            str(new_entry.get("descriptor")),
        )
        if old_key in old:
            raise EmptyFieldDeclarationEvidenceError(
                f"duplicate paired old field coordinate {old_key!r}"
            )
        if new_key in new:
            raise EmptyFieldDeclarationEvidenceError(
                f"duplicate paired new field coordinate {new_key!r}"
            )
        old[old_key] = member_id
        new[new_key] = member_id

    return old, new


def _jar_field_table(
    jar_path: Path,
    *,
    owner: str,
) -> list[dict[str, Any]]:
    entry = owner + ".class"
    try:
        with zipfile.ZipFile(jar_path, "r") as archive:
            try:
                data = archive.read(entry)
            except KeyError as exc:
                raise EmptyFieldDeclarationEvidenceError(
                    f"exact JAR missing owner {owner!r}"
                ) from exc
    except zipfile.BadZipFile as exc:
        raise EmptyFieldDeclarationEvidenceError(
            f"invalid JAR: {jar_path}"
        ) from exc

    parsed = parse_class(data)
    if parsed.name != owner:
        raise EmptyFieldDeclarationEvidenceError(
            f"exact JAR owner mismatch for {entry!r}"
        )

    out: list[dict[str, Any]] = []
    for i, row in enumerate(parsed.fields):
        if not isinstance(row, dict):
            raise EmptyFieldDeclarationEvidenceError(
                f"{owner}.fields[{i}] must be an object"
            )
        name = row.get("name")
        descriptor = row.get("descriptor")
        access = row.get("access")
        attrs = row.get("attributes", [])
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(descriptor, str)
            or not descriptor
            or not isinstance(access, int)
            or isinstance(access, bool)
            or not isinstance(attrs, list)
            or any(not isinstance(value, str) for value in attrs)
        ):
            raise EmptyFieldDeclarationEvidenceError(
                f"{owner}.fields[{i}] is invalid"
            )
        out.append(
            {
                "name": name,
                "descriptor": descriptor,
                "access": access,
                "attributes": list(attrs),
            }
        )
    return out


def _field_index(
    fields: list[dict[str, Any]],
    coord: tuple[str, str, int],
    *,
    label: str,
) -> int:
    name, descriptor, access = coord
    hits = [
        i
        for i, row in enumerate(fields)
        if row["name"] == name
        and row["descriptor"] == descriptor
        and row["access"] == access
    ]
    if len(hits) != 1:
        raise EmptyFieldDeclarationEvidenceError(
            f"{label}: expected one exact field coordinate, found {len(hits)}"
        )
    return hits[0]


def _paired_anchor_id(
    fields: list[dict[str, Any]],
    paired: dict[tuple[str, str, str], str],
    *,
    owner: str,
    target_index: int,
    direction: int,
) -> tuple[str, int] | None:
    i = target_index + direction
    while 0 <= i < len(fields):
        row = fields[i]
        member_id = paired.get(
            (owner, row["name"], row["descriptor"])
        )
        if member_id is not None:
            return member_id, i
        i += direction
    return None


def _declaration_signature(
    row: dict[str, Any],
    aliases: dict[str, str],
) -> tuple[Any, ...]:
    return (
        row["name"],
        int(row["access"]),
        _descriptor_identity_shape(
            str(row["descriptor"]),
            aliases,
        ),
        tuple(sorted(str(value) for value in row["attributes"])),
    )


def _segment_signatures(
    fields: list[dict[str, Any]],
    aliases: dict[str, str],
    *,
    left_index: int,
    right_index: int,
) -> list[tuple[Any, ...]]:
    return [
        _declaration_signature(row, aliases)
        for row in fields[left_index + 1:right_index]
    ]


def build_empty_field_declaration_evidence(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
) -> dict[str, Any]:
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    if (
        global_usage_report.get("schema_version") != 1
        or global_usage_report.get("kind")
        != "global_field_usage_identity_candidates"
        or global_usage_report.get("canonical") is not False
    ):
        raise EmptyFieldDeclarationEvidenceError(
            "unsupported global field usage report"
        )

    old_build_id = global_usage_report.get("old_build_id")
    new_build_id = global_usage_report.get("new_build_id")
    if (
        not isinstance(old_build_id, str)
        or not old_build_id
        or not isinstance(new_build_id, str)
        or not new_build_id
        or old_build_id == new_build_id
    ):
        raise EmptyFieldDeclarationEvidenceError(
            "report build binding is invalid"
        )

    old_jar = old_jar.resolve()
    new_jar = new_jar.resolve()
    old_jar_sha = sha256_file(old_jar)
    new_jar_sha = sha256_file(new_jar)
    old_sha = str(old_index.get("sha256", "")).lower()
    new_sha = str(new_index.get("sha256", "")).lower()
    if old_jar_sha.lower() != old_sha:
        raise EmptyFieldDeclarationEvidenceError(
            "old JAR SHA does not match exact old index"
        )
    if new_jar_sha.lower() != new_sha:
        raise EmptyFieldDeclarationEvidenceError(
            "new JAR SHA does not match exact new index"
        )
    if old_sha != str(
        _build(class_lineage, old_build_id).get("sha256", "")
    ).lower():
        raise EmptyFieldDeclarationEvidenceError(
            "old index SHA does not match canonical old build"
        )
    if new_sha != str(
        _build(class_lineage, new_build_id).get("sha256", "")
    ).lower():
        raise EmptyFieldDeclarationEvidenceError(
            "new index SHA does not match canonical new build"
        )
    if str(global_usage_report.get("old_sha256", "")).lower() != old_sha:
        raise EmptyFieldDeclarationEvidenceError(
            "report old SHA does not match exact old index"
        )
    if str(global_usage_report.get("new_sha256", "")).lower() != new_sha:
        raise EmptyFieldDeclarationEvidenceError(
            "report new SHA does not match exact new index"
        )

    member_digest = _stable_digest(member_lineage)
    if global_usage_report.get("member_lineage_digest") != member_digest:
        raise EmptyFieldDeclarationEvidenceError(
            "report member lineage digest does not match exact input lineage"
        )

    summary = global_usage_report.get("summary")
    outcomes = global_usage_report.get("review_outcomes")
    if not isinstance(summary, dict) or not isinstance(outcomes, list):
        raise EmptyFieldDeclarationEvidenceError(
            "report summary/review_outcomes shape is invalid"
        )
    input_count = summary.get("input_stable_symbol_reviews")
    reported_outcomes = summary.get("review_outcomes")
    empty_count = summary.get("empty_both")
    if (
        not isinstance(input_count, int)
        or isinstance(input_count, bool)
        or input_count < 0
        or not isinstance(reported_outcomes, int)
        or isinstance(reported_outcomes, bool)
        or reported_outcomes != input_count
        or len(outcomes) != input_count
        or not isinstance(empty_count, int)
        or isinstance(empty_count, bool)
        or empty_count < 0
    ):
        raise EmptyFieldDeclarationEvidenceError(
            "report outcome accounting is invalid"
        )

    outcome_ids: set[str] = set()
    empty_rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for i, row in enumerate(outcomes):
        if not isinstance(row, dict):
            raise EmptyFieldDeclarationEvidenceError(
                f"review_outcomes[{i}] must be an object"
            )
        relationship_id = row.get("relationship_id")
        outcome = row.get("outcome")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in outcome_ids
            or not isinstance(outcome, str)
            or not outcome
        ):
            raise EmptyFieldDeclarationEvidenceError(
                f"review_outcomes[{i}] identity/outcome is invalid"
            )
        outcome_ids.add(relationship_id)
        counts[outcome] += 1
        if outcome == "empty_both":
            empty_rows.append(row)

    if len(empty_rows) != empty_count:
        raise EmptyFieldDeclarationEvidenceError(
            "empty_both outcome detail count mismatch"
        )

    unresolved = _unresolved_reviews(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    if set(unresolved) != outcome_ids:
        raise EmptyFieldDeclarationEvidenceError(
            "outcome ledger does not cover the exact unresolved stable-symbol frontier"
        )

    old_owners = _owner_map(class_lineage, old_build_id)
    new_owners = _owner_map(class_lineage, new_build_id)
    old_aliases = _aliases(class_lineage, old_build_id)
    new_aliases = _aliases(class_lineage, new_build_id)
    old_paired, new_paired = _paired_field_maps(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()

    for row in sorted(
        empty_rows,
        key=lambda value: str(value["relationship_id"]),
    ):
        relationship_id = str(row["relationship_id"])
        original = unresolved[relationship_id]
        old_owner = str(row.get("old_owner", "")).removesuffix(".class")
        new_owner = str(row.get("new_owner", "")).removesuffix(".class")
        if (
            old_owner != str(original.get("old_owner", "")).removesuffix(".class")
            or new_owner != str(original.get("new_owner", "")).removesuffix(".class")
        ):
            raise EmptyFieldDeclarationEvidenceError(
                f"{relationship_id}: outcome owner differs from unresolved review"
            )

        old_logical = old_owners.get(old_owner)
        new_logical = new_owners.get(new_owner)
        if old_logical is None or new_logical is None or old_logical != new_logical:
            raise EmptyFieldDeclarationEvidenceError(
                f"{relationship_id}: owner is not one canonical logical class"
            )
        if row.get("logical_class_id") != old_logical:
            raise EmptyFieldDeclarationEvidenceError(
                f"{relationship_id}: logical class binding drift"
            )

        old_coord = _coord(row.get("old"), label=f"{relationship_id}.old")
        new_coord = _coord(row.get("new"), label=f"{relationship_id}.new")
        original_old = _coord(
            original.get("old"),
            label=f"{relationship_id}.unresolved.old",
        )
        original_new = _coord(
            original.get("new"),
            label=f"{relationship_id}.unresolved.new",
        )
        if old_coord != original_old or new_coord != original_new:
            raise EmptyFieldDeclarationEvidenceError(
                f"{relationship_id}: outcome coordinate differs from unresolved review"
            )

        old_fields = _jar_field_table(old_jar, owner=old_owner)
        new_fields = _jar_field_table(new_jar, owner=new_owner)
        old_index_pos = _field_index(
            old_fields,
            old_coord,
            label=f"{relationship_id}.old",
        )
        new_index_pos = _field_index(
            new_fields,
            new_coord,
            label=f"{relationship_id}.new",
        )

        old_left = _paired_anchor_id(
            old_fields,
            old_paired,
            owner=old_owner,
            target_index=old_index_pos,
            direction=-1,
        )
        old_right = _paired_anchor_id(
            old_fields,
            old_paired,
            owner=old_owner,
            target_index=old_index_pos,
            direction=1,
        )
        new_left = _paired_anchor_id(
            new_fields,
            new_paired,
            owner=new_owner,
            target_index=new_index_pos,
            direction=-1,
        )
        new_right = _paired_anchor_id(
            new_fields,
            new_paired,
            owner=new_owner,
            target_index=new_index_pos,
            direction=1,
        )

        def reject(reason: str, **evidence: Any) -> None:
            reason_counts[reason] += 1
            rejected.append(
                {
                    "relationship_id": relationship_id,
                    "logical_class_id": old_logical,
                    "old_owner": old_owner,
                    "new_owner": new_owner,
                    "reason": reason,
                    **evidence,
                }
            )

        if old_left is None or old_right is None or new_left is None or new_right is None:
            reject(
                "missing_two_sided_canonical_anchor",
                old_left=old_left,
                old_right=old_right,
                new_left=new_left,
                new_right=new_right,
            )
            continue

        if old_left[0] != new_left[0] or old_right[0] != new_right[0]:
            reject(
                "canonical_anchor_identity_mismatch",
                old_left_member_id=old_left[0],
                new_left_member_id=new_left[0],
                old_right_member_id=old_right[0],
                new_right_member_id=new_right[0],
            )
            continue

        old_segment = _segment_signatures(
            old_fields,
            old_aliases,
            left_index=old_left[1],
            right_index=old_right[1],
        )
        new_segment = _segment_signatures(
            new_fields,
            new_aliases,
            left_index=new_left[1],
            right_index=new_right[1],
        )
        if len(old_segment) != len(new_segment):
            reject(
                "declaration_interval_length_mismatch",
                old_interval_length=len(old_segment),
                new_interval_length=len(new_segment),
            )
            continue
        if old_segment != new_segment:
            reject(
                "declaration_interval_shape_mismatch",
                old_interval_digest=_stable_digest(old_segment),
                new_interval_digest=_stable_digest(new_segment),
            )
            continue

        old_offset = old_index_pos - old_left[1] - 1
        new_offset = new_index_pos - new_left[1] - 1
        if old_offset != new_offset:
            reject(
                "target_interval_offset_mismatch",
                old_offset=old_offset,
                new_offset=new_offset,
            )
            continue

        target_signature = old_segment[old_offset]
        if sum(1 for value in old_segment if value == target_signature) != 1:
            reject(
                "target_declaration_signature_not_unique",
                interval_length=len(old_segment),
                target_offset=old_offset,
            )
            continue

        candidates.append(
            {
                "relationship_id": relationship_id,
                "logical_class_id": old_logical,
                "old_owner": old_owner,
                "new_owner": new_owner,
                "old": {
                    "name": old_coord[0],
                    "descriptor": old_coord[1],
                    "access": old_coord[2],
                },
                "new": {
                    "name": new_coord[0],
                    "descriptor": new_coord[1],
                    "access": new_coord[2],
                },
                "strategy": "canonical_anchor_declaration_interval_exact",
                "confidence": "INFERRED_HIGH",
                "score": 0.99,
                "supports_existing_review": True,
                "left_anchor_member_id": old_left[0],
                "right_anchor_member_id": old_right[0],
                "old_field_ordinal": old_index_pos,
                "new_field_ordinal": new_index_pos,
                "interval_offset": old_offset,
                "interval_length": len(old_segment),
                "interval_digest": _stable_digest(old_segment),
            }
        )

    candidates.sort(key=lambda row: row["relationship_id"])
    rejected.sort(key=lambda row: row["relationship_id"])
    if len(candidates) + len(rejected) != len(empty_rows):
        raise EmptyFieldDeclarationEvidenceError(
            "empty-field declaration outcome accounting mismatch"
        )

    material = {
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "member_lineage_digest": member_digest,
        "global_usage_report_id": global_usage_report.get("report_id"),
        "candidates": candidates,
        "rejected": rejected,
    }
    return {
        "schema_version": 1,
        "kind": "empty_field_declaration_identity_candidates",
        "canonical": False,
        "report_id": (
            "EMPTYFIELDDECL_"
            + _stable_digest(material)[:20].upper()
        ),
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "member_lineage_digest": member_digest,
        "global_usage_report_id": global_usage_report.get("report_id"),
        "summary": {
            "input_empty_both_reviews": len(empty_rows),
            "candidate_fields": len(candidates),
            "remaining_without_declaration_proof": len(rejected),
            "missing_two_sided_canonical_anchor": reason_counts[
                "missing_two_sided_canonical_anchor"
            ],
            "canonical_anchor_identity_mismatch": reason_counts[
                "canonical_anchor_identity_mismatch"
            ],
            "declaration_interval_length_mismatch": reason_counts[
                "declaration_interval_length_mismatch"
            ],
            "declaration_interval_shape_mismatch": reason_counts[
                "declaration_interval_shape_mismatch"
            ],
            "target_interval_offset_mismatch": reason_counts[
                "target_interval_offset_mismatch"
            ],
            "target_declaration_signature_not_unique": reason_counts[
                "target_declaration_signature_not_unique"
            ],
        },
        "candidates": candidates,
        "rejected": rejected,
        "note": (
            "Research-only exact-JAR-bound evidence. canonical=false. Only empty_both residual "
            "stable-symbol reviews are considered. A candidate requires the same "
            "paired canonical field IDs immediately bracketing the target in both "
            "exact JVM field tables, an identical ordered declaration-signature "
            "interval between those anchors, the same target offset, and a unique "
            "target declaration signature within that interval. No one-sided or "
            "class-boundary-only anchor is accepted and no lineage relation is "
            "appended by this report."
        ),
    }


def write_report(report: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-empty-field-declaration-evidence"
    )
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("old_index", type=Path)
    p.add_argument("new_index", type=Path)
    p.add_argument("old_jar", type=Path)
    p.add_argument("new_jar", type=Path)
    p.add_argument("global_usage_report", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = build_empty_field_declaration_evidence(
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.old_index),
            _load(args.new_index),
            args.old_jar,
            args.new_jar,
            _load(args.global_usage_report),
        )
        write_report(report, args.out)
    except (
        EmptyFieldDeclarationEvidenceError,
        LineageValidationError,
        MemberLineageError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_EMPTY_FIELD_DECLARATION_EVIDENCE_PASS")
    print(f"report_id={report['report_id']}")
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
