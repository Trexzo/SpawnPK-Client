from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from .lineage import LineageValidationError, load_lineage, validate_lineage
from .member_lineage import (
    MemberLineageError,
    load_member_lineage,
    validate_member_lineage,
)


class GlobalFieldReviewSpecError(MemberLineageError):
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
        raise GlobalFieldReviewSpecError(
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
        raise GlobalFieldReviewSpecError(
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
                raise GlobalFieldReviewSpecError(
                    f"invalid canonical owner in build {build_id!r}"
                )
            if internal in out:
                raise GlobalFieldReviewSpecError(
                    f"duplicate canonical owner {internal!r}"
                )
            out[internal] = logical_id
    return out


def _exact_field(
    index: dict[str, Any],
    *,
    owner: str,
    name: str,
    descriptor: str,
) -> dict[str, Any]:
    cls = index.get("classes", {}).get(owner + ".class")
    if not isinstance(cls, dict):
        raise GlobalFieldReviewSpecError(
            f"exact index missing owner {owner!r}"
        )
    hits = [
        row
        for row in cls.get("fields", [])
        if row.get("name") == name
        and row.get("descriptor") == descriptor
    ]
    if len(hits) != 1:
        raise GlobalFieldReviewSpecError(
            f"expected one exact field {owner}.{name}:{descriptor}, "
            f"found {len(hits)}"
        )
    return hits[0]


def _coord(value: Any, *, label: str) -> tuple[str, str, int]:
    if not isinstance(value, dict):
        raise GlobalFieldReviewSpecError(f"{label} must be an object")
    name = value.get("name")
    descriptor = value.get("descriptor")
    access = value.get("access")
    if not isinstance(name, str) or not name:
        raise GlobalFieldReviewSpecError(
            f"{label}.name must be non-empty"
        )
    if not isinstance(descriptor, str) or not descriptor:
        raise GlobalFieldReviewSpecError(
            f"{label}.descriptor must be non-empty"
        )
    if not isinstance(access, int) or isinstance(access, bool):
        raise GlobalFieldReviewSpecError(
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
        relationship_id = candidate.get("relationship_id")
        if not isinstance(relationship_id, str) or not relationship_id:
            continue
        if relationship_id in out:
            raise GlobalFieldReviewSpecError(
                f"duplicate unresolved relationship_id {relationship_id!r}"
            )
        out[relationship_id] = candidate
    return out


def _topology_rows(
    value: Any,
    *,
    label: str,
    source_key: str,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise GlobalFieldReviewSpecError(
            f"{label} must be a non-empty array"
        )
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for i, row in enumerate(value):
        if not isinstance(row, dict):
            raise GlobalFieldReviewSpecError(
                f"{label}[{i}] must be an object"
            )
        source = row.get(source_key)
        operation = row.get("operation")
        count = row.get("count")
        if (
            not isinstance(source, str)
            or not source
            or not isinstance(operation, str)
            or operation not in {
                "getfield",
                "putfield",
                "getstatic",
                "putstatic",
            }
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count <= 0
        ):
            raise GlobalFieldReviewSpecError(
                f"{label}[{i}] has invalid topology evidence"
            )
        key = (source, operation)
        if key in seen:
            raise GlobalFieldReviewSpecError(
                f"{label} contains duplicate topology row {key!r}"
            )
        seen.add(key)
        rows.append(row)
    return rows


def build_global_field_review_spec(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    if (
        report.get("schema_version") != 1
        or report.get("kind")
        != "global_field_usage_identity_candidates"
        or report.get("canonical") is not False
    ):
        raise GlobalFieldReviewSpecError(
            "unsupported global field usage evidence report"
        )

    report_id = report.get("report_id")
    old_build_id = report.get("old_build_id")
    new_build_id = report.get("new_build_id")
    if (
        not isinstance(report_id, str)
        or not report_id
        or not isinstance(old_build_id, str)
        or not old_build_id
        or not isinstance(new_build_id, str)
        or not new_build_id
        or old_build_id == new_build_id
    ):
        raise GlobalFieldReviewSpecError(
            "report identity/build binding is invalid"
        )

    old_sha = str(old_index.get("sha256", "")).lower()
    new_sha = str(new_index.get("sha256", "")).lower()
    if old_sha != str(_build(class_lineage, old_build_id).get("sha256", "")).lower():
        raise GlobalFieldReviewSpecError(
            "old index SHA does not match canonical old build"
        )
    if new_sha != str(_build(class_lineage, new_build_id).get("sha256", "")).lower():
        raise GlobalFieldReviewSpecError(
            "new index SHA does not match canonical new build"
        )
    if str(report.get("old_sha256", "")).lower() != old_sha:
        raise GlobalFieldReviewSpecError(
            "report old SHA does not match exact old index"
        )
    if str(report.get("new_sha256", "")).lower() != new_sha:
        raise GlobalFieldReviewSpecError(
            "report new SHA does not match exact new index"
        )

    lineage_digest = _stable_digest(member_lineage)
    if report.get("member_lineage_digest") != lineage_digest:
        raise GlobalFieldReviewSpecError(
            "report member lineage digest does not match exact input lineage"
        )

    summary = report.get("summary")
    candidates = report.get("candidates")
    rejections = report.get("descriptor_identity_rejections")
    if (
        not isinstance(summary, dict)
        or not isinstance(candidates, list)
        or not isinstance(rejections, list)
    ):
        raise GlobalFieldReviewSpecError(
            "report summary/candidates/rejections shape is invalid"
        )

    input_count = summary.get("input_stable_symbol_reviews")
    eligible_count = summary.get("eligible_stable_symbol_reviews")
    veto_count = summary.get("descriptor_identity_guard_rejected")
    candidate_count = summary.get("candidate_fields")
    remaining_count = summary.get("remaining_without_global_topology_proof")
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in (
            input_count,
            eligible_count,
            veto_count,
            candidate_count,
            remaining_count,
        )
    ):
        raise GlobalFieldReviewSpecError(
            "report frontier summary is invalid"
        )
    if eligible_count + veto_count != input_count:
        raise GlobalFieldReviewSpecError(
            "eligible+descriptor-veto frontier accounting mismatch"
        )
    if len(rejections) != veto_count:
        raise GlobalFieldReviewSpecError(
            "descriptor veto detail count mismatch"
        )
    if len(candidates) != candidate_count:
        raise GlobalFieldReviewSpecError(
            "candidate detail count mismatch"
        )
    if candidate_count + remaining_count != input_count:
        raise GlobalFieldReviewSpecError(
            "candidate+remaining frontier accounting mismatch"
        )

    unresolved = _unresolved_reviews(
        member_lineage,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
    )
    if len(unresolved) != input_count:
        raise GlobalFieldReviewSpecError(
            "report frontier count does not match unresolved review frontier"
        )

    old_owners = _owner_map(class_lineage, old_build_id)
    new_owners = _owner_map(class_lineage, new_build_id)
    seen_ids: set[str] = set()
    seen_old: set[tuple[str, str, str]] = set()
    seen_new: set[tuple[str, str, str]] = set()
    relationship_ids: list[str] = []

    for i, row in enumerate(candidates):
        label = f"candidates[{i}]"
        if not isinstance(row, dict):
            raise GlobalFieldReviewSpecError(
                f"{label} must be an object"
            )
        if (
            row.get("strategy")
            != "canonical_method_and_global_class_usage_topology_exact"
            or row.get("supports_existing_review") is not True
            or row.get("confidence") != "INFERRED_HIGH"
        ):
            raise GlobalFieldReviewSpecError(
                f"{label} is not trusted global-usage review evidence"
            )

        relationship_id = row.get("relationship_id")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in seen_ids
        ):
            raise GlobalFieldReviewSpecError(
                f"{label} has invalid/duplicate relationship_id"
            )
        seen_ids.add(relationship_id)

        original = unresolved.get(relationship_id)
        if original is None:
            raise GlobalFieldReviewSpecError(
                f"{relationship_id}: not present in exact unresolved frontier"
            )

        old_owner = str(row.get("old_owner", "")).removesuffix(".class")
        new_owner = str(row.get("new_owner", "")).removesuffix(".class")
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
            raise GlobalFieldReviewSpecError(
                f"{relationship_id}: evidence owner differs from unresolved review"
            )

        old_logical = old_owners.get(old_owner)
        new_logical = new_owners.get(new_owner)
        if old_logical is None or new_logical is None or old_logical != new_logical:
            raise GlobalFieldReviewSpecError(
                f"{relationship_id}: owner is not one canonical class"
            )
        if row.get("logical_class_id") != old_logical:
            raise GlobalFieldReviewSpecError(
                f"{relationship_id}: logical class binding drift"
            )

        old_name, old_desc, old_access = _coord(
            row.get("old"),
            label=f"{label}.old",
        )
        new_name, new_desc, new_access = _coord(
            row.get("new"),
            label=f"{label}.new",
        )
        orig_old_name, orig_old_desc, orig_old_access = _coord(
            original.get("old"),
            label=f"{relationship_id}.unresolved.old",
        )
        orig_new_name, orig_new_desc, orig_new_access = _coord(
            original.get("new"),
            label=f"{relationship_id}.unresolved.new",
        )
        if (
            (old_name, old_desc, old_access)
            != (orig_old_name, orig_old_desc, orig_old_access)
            or (new_name, new_desc, new_access)
            != (orig_new_name, orig_new_desc, orig_new_access)
        ):
            raise GlobalFieldReviewSpecError(
                f"{relationship_id}: evidence coordinate differs from unresolved review"
            )

        old_decl = _exact_field(
            old_index,
            owner=old_owner,
            name=old_name,
            descriptor=old_desc,
        )
        new_decl = _exact_field(
            new_index,
            owner=new_owner,
            name=new_name,
            descriptor=new_desc,
        )
        if (
            int(old_decl.get("access", 0)) != old_access
            or int(new_decl.get("access", 0)) != new_access
        ):
            raise GlobalFieldReviewSpecError(
                f"{relationship_id}: exact index access drift"
            )

        old_key = (old_owner, old_name, old_desc)
        new_key = (new_owner, new_name, new_desc)
        if old_key in seen_old:
            raise GlobalFieldReviewSpecError(
                f"{relationship_id}: duplicate old candidate coordinate"
            )
        if new_key in seen_new:
            raise GlobalFieldReviewSpecError(
                f"{relationship_id}: duplicate new candidate coordinate"
            )
        seen_old.add(old_key)
        seen_new.add(new_key)

        observations = row.get("observations")
        canonical_methods = row.get("canonical_methods")
        if (
            not isinstance(observations, int)
            or isinstance(observations, bool)
            or observations <= 0
            or not isinstance(canonical_methods, int)
            or isinstance(canonical_methods, bool)
            or canonical_methods <= 0
        ):
            raise GlobalFieldReviewSpecError(
                f"{relationship_id}: non-positive usage evidence"
            )

        method_rows = _topology_rows(
            row.get("canonical_method_topology"),
            label=f"{relationship_id}.canonical_method_topology",
            source_key="member_id",
        )
        class_rows = _topology_rows(
            row.get("global_source_class_topology"),
            label=f"{relationship_id}.global_source_class_topology",
            source_key="source_class",
        )
        if any(
            str(item.get("source_class", "")).startswith("RAW:")
            for item in class_rows
        ):
            raise GlobalFieldReviewSpecError(
                f"{relationship_id}: RAW source class support is not reviewable"
            )
        if sum(int(item["count"]) for item in method_rows) != observations:
            raise GlobalFieldReviewSpecError(
                f"{relationship_id}: observation count does not match method topology"
            )
        if len({str(item["member_id"]) for item in method_rows}) != canonical_methods:
            raise GlobalFieldReviewSpecError(
                f"{relationship_id}: canonical method count does not match topology"
            )

        relationship_ids.append(relationship_id)

    if not relationship_ids:
        raise GlobalFieldReviewSpecError(
            "global field usage report contains no reviewable candidates"
        )

    report_digest = _stable_digest(report)
    return {
        "schema_version": 1,
        "kind": "reviewed_member_identity_acceptance_spec",
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "note": (
            f"Explicitly reviewed from {report_id}: exact non-empty canonical "
            "method usage topology plus identical whole-JAR canonical source-class "
            "read/write topology; descriptor-identity vetoes and all unproven "
            "reviews remain unresolved."
        ),
        "evidence": [
            f"report_id={report_id}",
            f"report_digest_sha256={report_digest}",
            f"member_lineage_digest_sha256={lineage_digest}",
            (
                "strategy="
                "canonical_method_and_global_class_usage_topology_exact"
            ),
            f"reviewed_candidates={len(relationship_ids)}",
            f"descriptor_identity_vetoes={veto_count}",
            f"remaining_without_global_topology_proof={remaining_count}",
        ],
        "relationship_ids": sorted(relationship_ids),
    }


def write_spec(spec: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            spec,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-global-field-review-spec"
    )
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("old_index", type=Path)
    p.add_argument("new_index", type=Path)
    p.add_argument("report", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        spec = build_global_field_review_spec(
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.old_index),
            _load(args.new_index),
            _load(args.report),
        )
        write_spec(spec, args.out)
    except (
        GlobalFieldReviewSpecError,
        LineageValidationError,
        MemberLineageError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_GLOBAL_FIELD_REVIEW_SPEC_PASS")
    print(f"relationship_ids={len(spec['relationship_ids'])}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
