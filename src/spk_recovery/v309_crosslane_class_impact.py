from __future__ import annotations

"""Read-only v309 cross-lane triage, NOT evidence of transferred class identity.

The raw class spelling in a field descriptor only names a hypothesis. Replacing
a missing canonical alias in topology for analysis does not prove that alias.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from .descriptor_class_dependencies import build_descriptor_class_dependency_report
from .descriptor_class_private_jar_replay import (
    _read_json_exact,
    write_research_report_no_clobber,
)


class V309CrossLaneImpactError(ValueError):
    pass


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _topology(rows: Any, *, label: str) -> Counter[tuple[str, str]]:
    if not isinstance(rows, list):
        raise V309CrossLaneImpactError(f"{label}: topology must be a list")
    result: Counter[tuple[str, str]] = Counter()
    for item in rows:
        if not isinstance(item, dict) or set(item) != {
            "source_class", "operation", "count",
        }:
            raise V309CrossLaneImpactError(f"{label}: invalid source-class topology")
        source, operation, count = (
            item["source_class"], item["operation"], item["count"],
        )
        if (
            not isinstance(source, str) or not source
            or operation not in ("getfield", "putfield", "getstatic", "putstatic")
            or type(count) is not int or count < 1
            or (source, operation) in result
        ):
            raise V309CrossLaneImpactError(f"{label}: invalid or duplicate topology row")
        result[source, operation] = count
    return result


def _rename(
    source: Counter[tuple[str, str]], aliases: dict[str, str],
) -> Counter[tuple[str, str]]:
    renamed: Counter[tuple[str, str]] = Counter()
    for (name, operation), count in source.items():
        renamed[aliases.get(name, name), operation] += count
    return renamed


def build_v309_crosslane_class_impact(
    global_report: dict[str, Any],
) -> dict[str, Any]:
    """Compute possible *research priority* from a pinned, unaccepted report."""
    if (
        not isinstance(global_report, dict)
        or global_report.get("kind") != "global_field_usage_identity_candidates"
        or global_report.get("canonical") is not False
        or global_report.get("old_build_id") != "v308"
        or global_report.get("new_build_id") != "v309"
    ):
        raise V309CrossLaneImpactError("requires noncanonical v308->v309 global field report")
    dependencies = build_descriptor_class_dependency_report(global_report)
    summary = global_report.get("summary", {})
    outcomes = global_report.get("review_outcomes", [])
    if (
        not isinstance(summary, dict) or not isinstance(outcomes, list)
        or summary.get("descriptor_identity_guard_rejected") != 26
        or summary.get("global_class_topology_guard_rejected") != 48
        or len(outcomes) != 143
        or dependencies["summary"]["blocked_fields"] != 26
        or dependencies["summary"]["blocking_old_class_identities"] != 8
    ):
        raise V309CrossLaneImpactError("v309 143/26/48 accepted review frontier drift")
    by_outcome = Counter()
    known_ids: set[str] = set()
    topology_rows = []
    for row in outcomes:
        if not isinstance(row, dict):
            raise V309CrossLaneImpactError("non-object global review outcome")
        rel = row.get("relationship_id")
        kind = row.get("outcome")
        if not isinstance(rel, str) or not rel or rel in known_ids or not isinstance(kind, str):
            raise V309CrossLaneImpactError("missing, duplicate or invalid review relationship")
        known_ids.add(rel)
        by_outcome[kind] += 1
        if kind == "global_class_topology_guard_rejected":
            original = _topology(
                row.get("old_global_source_class_topology"),
                label=f"{rel}: old",
            )
            current = _topology(
                row.get("new_global_source_class_topology"),
                label=f"{rel}: new",
            )
            if original == current:
                raise V309CrossLaneImpactError(f"{rel}: topology veto has identical sources")
            topology_rows.append((rel, original, current))
    if (
        by_outcome["descriptor_identity_guard_rejected"] != 26
        or by_outcome["global_class_topology_guard_rejected"] != 48
        or by_outcome["empty_both"] != 68
        or by_outcome["raw_source_guard_rejected"] != 1
        or set(by_outcome) != {
            "descriptor_identity_guard_rejected",
            "global_class_topology_guard_rejected",
            "empty_both", "raw_source_guard_rejected",
        }
    ):
        raise V309CrossLaneImpactError("global rejected field outcome partition drift")
    aliases: dict[str, str] = {}
    groups = []
    for group in dependencies["class_dependencies"]:
        cid = group["old_canonical_class_id"]
        new_desc = group["new_raw_descriptors"]
        if len(new_desc) != 1:
            raise V309CrossLaneImpactError(
                f"{cid}: non-unique new raw descriptor hypothesis"
            )
        raw = new_desc[0]
        if not isinstance(raw, str) or not raw.startswith("Lrs/") or not raw.endswith(";"):
            raise V309CrossLaneImpactError(f"{cid}: unsupported raw reference descriptor")
        new_alias = "RAW:" + raw[1:-1]
        if cid in aliases or new_alias in aliases.values():
            raise V309CrossLaneImpactError("duplicate or conflicting descriptor alias hypothesis")
        aliases[cid] = new_alias
        exactly_normalized = sorted(
            rel for rel, old, new in topology_rows
            if _rename(old, {cid: new_alias}) == new
        )
        touched = sorted(
            rel for rel, old, new in topology_rows
            if any(n == cid for n, _operation in old)
            and any(n == new_alias for n, _operation in new)
        )
        groups.append({
            "old_canonical_class_id": cid,
            "hypothetical_new_source_class": new_alias,
            "descriptor_blocked_fields": group["blocked_fields"],
            "topology_rows_with_both_labels": len(touched),
            "topology_rows_equal_after_this_alias_only": len(exactly_normalized),
            "combined_research_priority_rows": (
                group["blocked_fields"] + len(exactly_normalized)
            ),
            "affected_topology_relationship_ids": exactly_normalized,
            "state": "UNPROVEN_DESCRIPTOR_DERIVED_ALIAS_FOR_RESEARCH_ONLY",
        })
    groups.sort(key=lambda r: (
        -r["combined_research_priority_rows"],
        -r["descriptor_blocked_fields"],
        r["old_canonical_class_id"],
    ))
    combined_equal = sorted(
        rel for rel, old, new in topology_rows if _rename(old, aliases) == new
    )
    result = {
        "schema_version": 1,
        "kind": "v309_crosslane_class_alias_research_priorities",
        "canonical": False,
        "state": "HYPOTHETICAL_NORMALIZATION_NOT_CLASS_IDENTITY_PROOF",
        "global_report_id": global_report.get("report_id"),
        "global_report_digest": _digest(global_report),
        "dependency_digest": _digest(dependencies),
        "summary": {
            "accepted_unresolved_fields": 143,
            "descriptor_blocked_fields": 26,
            "descriptor_dependent_class_hypotheses": len(groups),
            "topology_guard_blocked_fields": 48,
            "topology_rows_equal_only_after_all_eight_hypotheses": len(combined_equal),
            "topology_rows_still_not_equal_under_all_hypotheses": (
                48 - len(combined_equal)
            ),
            "no_class_or_member_identities_accepted": True,
        },
        "class_hypotheses": groups,
        "multi_hypothesis_normalized_relationship_ids": combined_equal,
        "warning": (
            "A raw JVM descriptor is not canonical class identity evidence. "
            "These alias substitutions are counterfactual research triage only; "
            "exact private-JAR witnesses and reviewed lineage acceptance are required."
        ),
    }
    return {
        "report_id": "V309CROSSLANE_" + _digest(result)[:20].upper(),
        **result,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-crosslane-class-impact")
    p.add_argument(
        "--global-field-report", type=Path,
        default=Path("research/v309-field-recovery/global-field-usage.json"),
    )
    p.add_argument(
        "--frontier", type=Path,
        default=Path("research/v309-field-recovery/frontier.json"),
    )
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        import hashlib
        frontier = _read_json_exact(args.frontier)
        sha = frontier.get("files", {}).get("global_field_usage", {}).get("sha256")
        if (
            frontier.get("kind") != "v309_recovery_frontier"
            or frontier.get("state") != "ACCEPTED_INCOMPLETE"
            or frontier.get("frontier", {}).get("unresolved") != 143
            or not isinstance(sha, str) or len(sha) != 64
            or hashlib.sha256(args.global_field_report.read_bytes()).hexdigest() != sha.lower()
        ):
            raise V309CrossLaneImpactError("global report differs from accepted GitHub frontier")
        report = build_v309_crosslane_class_impact(
            _read_json_exact(args.global_field_report)
        )
        write_research_report_no_clobber(
            report, args.out, (args.global_field_report, args.frontier),
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"SPK_V309_CROSSLANE_CLASS_IMPACT_FAIL: {exc}")
        return 1
    print("SPK_V309_CROSSLANE_IMPACT_PASS_RESEARCH_ONLY")
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    for row in report["class_hypotheses"]:
        print(
            f'{row["old_canonical_class_id"]} -> '
            f'{row["hypothetical_new_source_class"]} '
            f'priority={row["combined_research_priority_rows"]}'
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
