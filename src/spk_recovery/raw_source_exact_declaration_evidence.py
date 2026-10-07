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
from .empty_field_declaration_evidence import (
    EmptyFieldDeclarationEvidenceError,
    _aliases,
    _coord,
    _field_index,
    _jar_field_table,
    _paired_anchor_id,
    _paired_field_maps,
    _segment_signatures,
    _stable_digest,
    _unresolved_reviews,
    build_empty_field_declaration_evidence,
)
from .lineage import LineageValidationError, load_lineage
from .member_lineage import (
    MemberLineageError,
    load_member_lineage,
)


class RawSourceExactDeclarationEvidenceError(MemberLineageError):
    pass


_ALLOWED_OPERATIONS = {
    "getstatic",
    "putstatic",
    "getfield",
    "putfield",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RawSourceExactDeclarationEvidenceError(
            f"JSON root must be object: {path}"
        )
    return value


def _topology(
    rows: Any,
    *,
    label: str,
) -> Counter[tuple[str, str]]:
    if not isinstance(rows, list):
        raise RawSourceExactDeclarationEvidenceError(
            f"{label} must be an array"
        )

    out: Counter[tuple[str, str]] = Counter()
    seen: set[tuple[str, str]] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RawSourceExactDeclarationEvidenceError(
                f"{label}[{i}] must be an object"
            )
        source_class = row.get("source_class")
        operation = row.get("operation")
        count = row.get("count")
        if (
            not isinstance(source_class, str)
            or not source_class
            or not isinstance(operation, str)
            or operation not in _ALLOWED_OPERATIONS
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count <= 0
        ):
            raise RawSourceExactDeclarationEvidenceError(
                f"{label}[{i}] is invalid"
            )
        key = (source_class, operation)
        if key in seen:
            raise RawSourceExactDeclarationEvidenceError(
                f"{label} contains duplicate topology key {key!r}"
            )
        seen.add(key)
        out[key] = count
    return out


def _topology_rows(
    topology: Counter[tuple[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "source_class": source_class,
            "operation": operation,
            "count": count,
        }
        for (source_class, operation), count in sorted(topology.items())
    ]


def _raw_class_profile(
    jar_path: Path,
    raw_source: str,
) -> dict[str, Any] | None:
    if not raw_source.startswith("RAW:"):
        raise RawSourceExactDeclarationEvidenceError(
            f"not a RAW source class: {raw_source!r}"
        )
    internal_name = raw_source[4:]
    if not internal_name:
        raise RawSourceExactDeclarationEvidenceError(
            "RAW source class has empty internal name"
        )
    entry = internal_name + ".class"

    try:
        with zipfile.ZipFile(jar_path, "r") as archive:
            try:
                data = archive.read(entry)
            except KeyError:
                return None
    except zipfile.BadZipFile as exc:
        raise RawSourceExactDeclarationEvidenceError(
            f"invalid JAR: {jar_path}"
        ) from exc

    parsed = parse_class(data)
    if parsed.name != internal_name:
        raise RawSourceExactDeclarationEvidenceError(
            f"RAW class entry/name mismatch: {entry!r} -> {parsed.name!r}"
        )

    return {
        "source_class": raw_source,
        "internal_name": internal_name,
        "entry": entry,
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_length": len(data),
    }


def build_raw_source_exact_declaration_evidence(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
) -> dict[str, Any]:
    base = build_empty_field_declaration_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
    )

    old_build_id = base.get("old_build_id")
    new_build_id = base.get("new_build_id")
    old_sha = str(base.get("old_sha256", "")).lower()
    new_sha = str(base.get("new_sha256", "")).lower()
    member_digest = base.get("member_lineage_digest")
    global_report_id = base.get("global_usage_report_id")
    if (
        not isinstance(old_build_id, str)
        or not old_build_id
        or not isinstance(new_build_id, str)
        or not new_build_id
        or old_build_id == new_build_id
        or len(old_sha) != 64
        or len(new_sha) != 64
        or not isinstance(member_digest, str)
        or len(member_digest) != 64
        or not isinstance(global_report_id, str)
        or not global_report_id
    ):
        raise RawSourceExactDeclarationEvidenceError(
            "base declaration report binding is invalid"
        )

    raw_rows = [
        row
        for row in base.get("rejected", [])
        if isinstance(row, dict)
        and row.get("reason") == "raw_source_guard_rejected"
    ]

    unresolved = _unresolved_reviews(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_paired, new_paired = _paired_field_maps(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    old_aliases = _aliases(class_lineage, old_build_id)
    new_aliases = _aliases(class_lineage, new_build_id)

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    reason_counts = {
        "raw_source_topology_mismatch": 0,
        "raw_source_class_missing": 0,
        "raw_source_class_bytes_mismatch": 0,
        "missing_two_sided_canonical_anchor": 0,
        "canonical_anchor_identity_mismatch": 0,
        "declaration_interval_length_mismatch": 0,
        "declaration_interval_shape_mismatch": 0,
        "target_interval_offset_mismatch": 0,
        "target_declaration_signature_not_unique": 0,
    }

    seen_ids: set[str] = set()
    seen_old: set[tuple[str, str, str]] = set()
    seen_new: set[tuple[str, str, str]] = set()

    for i, row in enumerate(raw_rows):
        relationship_id = row.get("relationship_id")
        logical_class_id = row.get("logical_class_id")
        old_owner = str(row.get("old_owner", "")).removesuffix(".class")
        new_owner = str(row.get("new_owner", "")).removesuffix(".class")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in seen_ids
            or not isinstance(logical_class_id, str)
            or not logical_class_id
            or not old_owner
            or not new_owner
        ):
            raise RawSourceExactDeclarationEvidenceError(
                f"base RAW row {i} is invalid/duplicate"
            )
        seen_ids.add(relationship_id)

        original = unresolved.get(relationship_id)
        if original is None:
            raise RawSourceExactDeclarationEvidenceError(
                f"{relationship_id}: missing from exact unresolved frontier"
            )
        if original.get("strategy") != "stable_symbol":
            raise RawSourceExactDeclarationEvidenceError(
                f"{relationship_id}: unresolved source is not stable_symbol"
            )

        old_coord = _coord(
            original.get("old"),
            label=f"{relationship_id}.old",
        )
        new_coord = _coord(
            original.get("new"),
            label=f"{relationship_id}.new",
        )
        original_old_owner = str(
            original.get("old_owner", "")
        ).removesuffix(".class")
        original_new_owner = str(
            original.get("new_owner", "")
        ).removesuffix(".class")
        if (
            old_owner != original_old_owner
            or new_owner != original_new_owner
        ):
            raise RawSourceExactDeclarationEvidenceError(
                f"{relationship_id}: base owner differs from unresolved review"
            )

        old_key = (old_owner, old_coord[0], old_coord[1])
        new_key = (new_owner, new_coord[0], new_coord[1])
        if old_key in seen_old:
            raise RawSourceExactDeclarationEvidenceError(
                f"{relationship_id}: duplicate old residual coordinate"
            )
        if new_key in seen_new:
            raise RawSourceExactDeclarationEvidenceError(
                f"{relationship_id}: duplicate new residual coordinate"
            )
        seen_old.add(old_key)
        seen_new.add(new_key)

        old_topology = _topology(
            row.get("old_global_source_class_topology"),
            label=f"{relationship_id}.old_global_source_class_topology",
        )
        new_topology = _topology(
            row.get("new_global_source_class_topology"),
            label=f"{relationship_id}.new_global_source_class_topology",
        )
        raw_sources = sorted(
            {
                source_class
                for source_class, _operation in (
                    set(old_topology) | set(new_topology)
                )
                if source_class.startswith("RAW:")
            }
        )
        if not raw_sources:
            raise RawSourceExactDeclarationEvidenceError(
                f"{relationship_id}: RAW rejection contains no RAW source"
            )

        def reject(reason: str, **evidence: Any) -> None:
            reason_counts[reason] += 1
            rejected.append(
                {
                    "relationship_id": relationship_id,
                    "logical_class_id": logical_class_id,
                    "old_owner": old_owner,
                    "new_owner": new_owner,
                    "reason": reason,
                    **evidence,
                }
            )

        if old_topology != new_topology:
            reject(
                "raw_source_topology_mismatch",
                old_global_source_class_topology=_topology_rows(
                    old_topology
                ),
                new_global_source_class_topology=_topology_rows(
                    new_topology
                ),
                raw_sources=raw_sources,
            )
            continue

        raw_profiles: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []
        mismatched: list[dict[str, Any]] = []
        for raw_source in raw_sources:
            old_profile = _raw_class_profile(old_jar, raw_source)
            new_profile = _raw_class_profile(new_jar, raw_source)
            if old_profile is None or new_profile is None:
                missing.append(
                    {
                        "source_class": raw_source,
                        "old_present": old_profile is not None,
                        "new_present": new_profile is not None,
                    }
                )
                continue
            if (
                old_profile["sha256"] != new_profile["sha256"]
                or old_profile["byte_length"] != new_profile["byte_length"]
            ):
                mismatched.append(
                    {
                        "source_class": raw_source,
                        "old_sha256": old_profile["sha256"],
                        "new_sha256": new_profile["sha256"],
                        "old_byte_length": old_profile["byte_length"],
                        "new_byte_length": new_profile["byte_length"],
                    }
                )
                continue
            raw_profiles.append(old_profile)

        if missing:
            reject(
                "raw_source_class_missing",
                missing=missing,
                raw_sources=raw_sources,
            )
            continue
        if mismatched:
            reject(
                "raw_source_class_bytes_mismatch",
                mismatched=mismatched,
                exact_raw_sources=raw_profiles,
            )
            continue
        if len(raw_profiles) != len(raw_sources):
            raise RawSourceExactDeclarationEvidenceError(
                f"{relationship_id}: RAW class proof accounting mismatch"
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
        if (
            old_left is None
            or old_right is None
            or new_left is None
            or new_right is None
        ):
            reject(
                "missing_two_sided_canonical_anchor",
                old_left=old_left,
                old_right=old_right,
                new_left=new_left,
                new_right=new_right,
                exact_raw_sources=raw_profiles,
            )
            continue

        if old_left[0] != new_left[0] or old_right[0] != new_right[0]:
            reject(
                "canonical_anchor_identity_mismatch",
                old_left_member_id=old_left[0],
                new_left_member_id=new_left[0],
                old_right_member_id=old_right[0],
                new_right_member_id=new_right[0],
                exact_raw_sources=raw_profiles,
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
                exact_raw_sources=raw_profiles,
            )
            continue
        if old_segment != new_segment:
            reject(
                "declaration_interval_shape_mismatch",
                old_interval_digest=_stable_digest(old_segment),
                new_interval_digest=_stable_digest(new_segment),
                exact_raw_sources=raw_profiles,
            )
            continue

        old_offset = old_index_pos - old_left[1] - 1
        new_offset = new_index_pos - new_left[1] - 1
        if old_offset != new_offset:
            reject(
                "target_interval_offset_mismatch",
                old_offset=old_offset,
                new_offset=new_offset,
                exact_raw_sources=raw_profiles,
            )
            continue

        target_signature = old_segment[old_offset]
        old_occurrences = sum(
            1 for value in old_segment
            if value == target_signature
        )
        new_occurrences = sum(
            1 for value in new_segment
            if value == target_signature
        )
        if (
            new_segment[new_offset] != target_signature
            or old_occurrences != 1
            or new_occurrences != 1
        ):
            reject(
                "target_declaration_signature_not_unique",
                interval_length=len(old_segment),
                interval_offset=old_offset,
                old_occurrences=old_occurrences,
                new_occurrences=new_occurrences,
                exact_raw_sources=raw_profiles,
            )
            continue

        candidates.append(
            {
                "relationship_id": relationship_id,
                "logical_class_id": logical_class_id,
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
                "strategy": (
                    "exact_raw_source_class_bytes_and_"
                    "canonical_anchor_declaration_interval"
                ),
                "confidence": "INFERRED_HIGH",
                "score": 0.999,
                "supports_existing_review": True,
                "raw_source_classes": raw_profiles,
                "global_source_class_topology": _topology_rows(
                    old_topology
                ),
                "left_anchor_member_id": old_left[0],
                "right_anchor_member_id": old_right[0],
                "old_field_ordinal": old_index_pos,
                "new_field_ordinal": new_index_pos,
                "interval_offset": old_offset,
                "interval_length": len(old_segment),
                "interval_digest": _stable_digest(old_segment),
                "base_declaration_report_id": base.get("report_id"),
            }
        )

    candidates.sort(key=lambda row: row["relationship_id"])
    rejected.sort(key=lambda row: row["relationship_id"])
    if len(candidates) + len(rejected) != len(raw_rows):
        raise RawSourceExactDeclarationEvidenceError(
            "RAW-source declaration outcome accounting mismatch"
        )

    summary = {
        "input_raw_source_guard_reviews": len(raw_rows),
        "candidate_fields": len(candidates),
        "remaining_without_raw_source_exact_proof": len(rejected),
        **reason_counts,
    }
    body = {
        "schema_version": 1,
        "kind": "raw_source_exact_declaration_identity_candidates",
        "canonical": False,
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "member_lineage_digest": member_digest,
        "global_usage_report_id": global_report_id,
        "base_declaration_report_id": base.get("report_id"),
        "base_declaration_report_digest": _stable_digest(base),
        "summary": summary,
        "candidates": candidates,
        "rejected": rejected,
        "note": (
            "Research-only exact-JAR RAW-source declaration evidence. "
            "Only #840 rows rejected solely by the RAW-source guard are "
            "considered. RAW source identity is never inferred from a name: "
            "old/new whole-JAR source topology must first be identical and "
            "every RAW source class must exist at the same class entry with "
            "byte-for-byte identical classfile SHA-256. The target must then "
            "independently pass the same two-sided canonical field-anchor, "
            "ordered declaration-interval, target-offset, and unique-target "
            "signature requirements as #840. canonical=false; no lineage "
            "mutation occurs."
        ),
    }
    return {
        "report_id": (
            "RAWSOURCEDECL_"
            + hashlib.sha256(
                json.dumps(
                    body,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()[:20].upper()
        ),
        **body,
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
        prog="spk-raw-source-exact-declaration-evidence"
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
        report = build_raw_source_exact_declaration_evidence(
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
        RawSourceExactDeclarationEvidenceError,
        EmptyFieldDeclarationEvidenceError,
        LineageValidationError,
        MemberLineageError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_RAW_SOURCE_EXACT_DECLARATION_EVIDENCE_PASS")
    print(f"report_id={report['report_id']}")
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
