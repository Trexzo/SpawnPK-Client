from __future__ import annotations

"""Summarize unproven v309 descriptor-class dependencies without accepting identities."""

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any


_CLASS_ID = re.compile(r"L@(CLIENT_CLASS_[0-9]{6});")


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def build_descriptor_class_dependency_report(report: dict[str, Any]) -> dict[str, Any]:
    """Derive a fail-closed research queue from a validated global-field report.

    A blocked field is *not* an accepted member mapping. In particular, matching
    raw JVM class names or descriptors is never used as class identity proof.
    """
    if (
        not isinstance(report, dict)
        or report.get("kind") != "global_field_usage_identity_candidates"
        or report.get("canonical") is not False
    ):
        raise ValueError("expected noncanonical global-field-usage research report")
    summary = report.get("summary")
    blockers = report.get("descriptor_identity_rejections")
    outcomes = report.get("review_outcomes")
    if not isinstance(summary, dict) or not isinstance(blockers, list):
        raise ValueError("missing descriptor rejection accounting")
    if not isinstance(outcomes, list):
        raise ValueError("missing global review outcomes")
    expected = summary.get("descriptor_identity_guard_rejected")
    if type(expected) is not int or expected != len(blockers):
        raise ValueError("descriptor rejection summary differs from report rows")

    from_outcomes = {
        row.get("relationship_id"): {k: v for k, v in row.items() if k != "outcome"}
        for row in outcomes
        if isinstance(row, dict)
        and row.get("outcome") == "descriptor_identity_guard_rejected"
    }
    if len(from_outcomes) != len(blockers):
        raise ValueError("descriptor review outcomes are missing or duplicated")

    grouped: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    renamed_descriptors = 0
    renamed_owners = 0

    for row in blockers:
        if not isinstance(row, dict):
            raise ValueError("descriptor rejection row must be an object")
        rel = row.get("relationship_id")
        match = _CLASS_ID.fullmatch(str(row.get("old_descriptor_identity", "")))
        if (
            not isinstance(rel, str) or not rel or rel in seen
            or row.get("reason") != "canonical_descriptor_identity_changed"
            or match is None
            or row.get("new_descriptor_identity") != "Lrs/?;"
            or not isinstance(row.get("old_descriptor"), str)
            or not isinstance(row.get("new_descriptor"), str)
            or not isinstance(row.get("old_owner"), str)
            or not isinstance(row.get("new_owner"), str)
        ):
            raise ValueError(f"unsupported, duplicate, or ambiguous descriptor veto: {rel}")
        seen.add(rel)
        if from_outcomes.get(rel) != row:
            raise ValueError(f"descriptor rejection/outcome mismatch: {rel}")

        old_descriptor = row["old_descriptor"]
        new_descriptor = row["new_descriptor"]
        if not (
            old_descriptor.startswith("L") and old_descriptor.endswith(";")
            and new_descriptor.startswith("L") and new_descriptor.endswith(";")
        ):
            raise ValueError(f"expected reference descriptors: {rel}")

        cid = match.group(1)
        group = grouped.setdefault(cid, {
            "old_canonical_class_id": cid,
            "state": "UNPROVEN_NEW_CLASS_IDENTITY",
            "relationship_ids": [],
            "old_raw_descriptors": set(),
            "new_raw_descriptors": set(),
            "descriptor_renamed_count": 0,
            "owner_renamed_count": 0,
        })
        group["relationship_ids"].append(rel)
        group["old_raw_descriptors"].add(old_descriptor)
        group["new_raw_descriptors"].add(new_descriptor)
        if old_descriptor != new_descriptor:
            group["descriptor_renamed_count"] += 1
            renamed_descriptors += 1
        if row["old_owner"] != row["new_owner"]:
            group["owner_renamed_count"] += 1
            renamed_owners += 1

    groups = []
    for group in grouped.values():
        group["relationship_ids"].sort()
        group["blocked_fields"] = len(group["relationship_ids"])
        group["old_raw_descriptors"] = sorted(group["old_raw_descriptors"])
        group["new_raw_descriptors"] = sorted(group["new_raw_descriptors"])
        groups.append(group)
    groups.sort(key=lambda g: (-g["blocked_fields"], g["old_canonical_class_id"]))

    return {
        "schema_version": 1,
        "kind": "v309_descriptor_class_dependency_research_queue",
        "state": "RESEARCH_ONLY_NO_IDENTITIES_ACCEPTED",
        "source_report_id": report.get("report_id"),
        "source_report_digest": _canonical_digest(report),
        "member_lineage_digest": report.get("member_lineage_digest"),
        "old_build_id": report.get("old_build_id"),
        "new_build_id": report.get("new_build_id"),
        "summary": {
            "blocked_fields": len(blockers),
            "blocking_old_class_identities": len(groups),
            "raw_descriptors_renamed": renamed_descriptors,
            "field_owners_renamed": renamed_owners,
        },
        "class_dependencies": groups,
        "note": (
            "This report is a deterministic triage queue only. An old canonical "
            "class ID plus an unresolved new descriptor is NOT proof of a new "
            "class identity. Prove the new class independently, recompute the "
            "field report, and use reviewed lineage acceptance before promotion."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spk-v309-descriptor-class-dependencies")
    parser.add_argument("global_field_usage", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        source = json.loads(args.global_field_usage.read_text(encoding="utf-8"))
        result = build_descriptor_class_dependency_report(source)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"SPK_DESCRIPTOR_CLASS_DEPENDENCIES_FAIL: {exc}")
        return 1
    print("SPK_DESCRIPTOR_CLASS_DEPENDENCIES_PASS")
    for key, value in result["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
