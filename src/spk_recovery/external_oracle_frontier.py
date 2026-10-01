from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


class ExternalOracleFrontierError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _source_unit_from_path(value: str) -> str | None:
    path = value.replace("\\", "/")
    if not path.endswith(".java"):
        return None

    marker = "/src/"
    if marker in path:
        relative = path.rsplit(marker, 1)[1]
    elif path.startswith("src/"):
        relative = path[4:]
    elif "/rs/" in path:
        relative = "rs/" + path.rsplit("/rs/", 1)[1]
    elif path.startswith("rs/"):
        relative = path
    else:
        return None

    if not relative.endswith(".java"):
        return None
    return relative[:-5]


def _class_remaps(plan: dict[str, Any]) -> dict[str, str]:
    if (
        plan.get("schema_version") != 1
        or plan.get("kind") != "remap_plan"
        or plan.get("build_id") != "v308"
    ):
        raise ExternalOracleFrontierError(
            "requires exact-v308 class remap plan"
        )
    rows = plan.get("classes")
    if not isinstance(rows, list):
        raise ExternalOracleFrontierError(
            "class remap plan classes must be an array"
        )

    out: dict[str, str] = {}
    targets: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ExternalOracleFrontierError(
                f"class remap row {index} must be an object"
            )
        source = row.get("source_internal_name")
        target = row.get("target_internal_name")
        if (
            not isinstance(source, str)
            or not source
            or not isinstance(target, str)
            or not target
        ):
            raise ExternalOracleFrontierError(
                f"class remap row {index} lacks source/target identity"
            )
        if source in out:
            raise ExternalOracleFrontierError(
                f"duplicate class remap source: {source}"
            )
        if target in targets:
            raise ExternalOracleFrontierError(
                f"duplicate class remap target: {target}"
            )
        out[source] = target
        targets.add(target)
    return out


def _collision_remaps(
    plan: dict[str, Any] | None,
) -> tuple[dict[str, str], str | None]:
    if plan is None:
        return {}, None
    if (
        plan.get("schema_version") != 1
        or plan.get("kind")
        != "class_package_namespace_collision_plan"
    ):
        raise ExternalOracleFrontierError(
            "unsupported namespace collision plan"
        )
    if plan.get("identifiers_included") is not True:
        raise ExternalOracleFrontierError(
            "collision plan must include identifiers"
        )
    summary = plan.get("summary")
    if (
        not isinstance(summary, dict)
        or summary.get("plan_eliminates_all_collisions") is not True
        or int(summary.get("post_collision_edge_count", -1)) != 0
    ):
        raise ExternalOracleFrontierError(
            "collision plan is not a complete zero-collision plan"
        )

    out: dict[str, str] = {}
    for index, row in enumerate(plan.get("remaps", [])):
        if not isinstance(row, dict):
            raise ExternalOracleFrontierError(
                f"collision remap row {index} must be an object"
            )
        old = row.get("old_internal_name")
        new = row.get("new_internal_name")
        if (
            not isinstance(old, str)
            or not old
            or not isinstance(new, str)
            or not new
        ):
            raise ExternalOracleFrontierError(
                f"collision remap row {index} lacks identifiers"
            )
        if old in out:
            raise ExternalOracleFrontierError(
                f"duplicate collision remap source: {old}"
            )
        out[old] = new

    plan_id = plan.get("plan_id")
    return out, str(plan_id) if plan_id else None


def build_external_oracle_frontier(
    *,
    private_diagnostic: dict[str, Any],
    external_oracle: dict[str, Any],
    class_remap_plan: dict[str, Any],
    collision_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if (
        private_diagnostic.get("schema_version") != 1
        or private_diagnostic.get("kind")
        != "javac_diagnostic_classification_report"
        or private_diagnostic.get("identifiers_included") is not True
    ):
        raise ExternalOracleFrontierError(
            "requires private identifier-bearing javac diagnostic report"
        )

    if (
        external_oracle.get("schema_version") != 1
        or external_oracle.get("kind")
        != "external_readable_v308_structural_oracle"
        or external_oracle.get("research_only") is not True
        or external_oracle.get("source_authority") is not False
        or external_oracle.get("semantic_authority") is not False
        or external_oracle.get("source_mutation_allowed") is not False
    ):
        raise ExternalOracleFrontierError(
            "external oracle truth boundary is invalid"
        )

    exact = external_oracle.get("exact_v308")
    if not isinstance(exact, dict):
        raise ExternalOracleFrontierError(
            "external oracle lacks exact-v308 authority"
        )
    exact_sha = str(exact.get("sha256", "")).lower()
    plan_sha = str(
        class_remap_plan.get("source_sha256", "")
    ).lower()
    if not exact_sha or exact_sha != plan_sha:
        raise ExternalOracleFrontierError(
            "class remap plan authority does not match oracle exact v308"
        )

    remaps = _class_remaps(class_remap_plan)
    collision_remaps, collision_plan_id = _collision_remaps(
        collision_plan
    )

    diagnostics = private_diagnostic.get("diagnostics")
    if not isinstance(diagnostics, list):
        raise ExternalOracleFrontierError(
            "private diagnostic diagnostics must be an array"
        )

    by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unmapped_paths: Counter[str] = Counter()
    for row in diagnostics:
        if not isinstance(row, dict):
            raise ExternalOracleFrontierError(
                "private diagnostic row must be an object"
            )
        source_path = row.get("source_path")
        if not isinstance(source_path, str) or not source_path:
            raise ExternalOracleFrontierError(
                "private diagnostic row lacks source_path"
            )
        source_unit = _source_unit_from_path(source_path)
        if source_unit is None:
            unmapped_paths[source_path.replace("\\", "/")] += 1
            continue
        by_unit[source_unit].append(row)

    candidate_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    nested_skipped = 0
    for candidate in external_oracle.get("candidates", []):
        if not isinstance(candidate, dict):
            raise ExternalOracleFrontierError(
                "external oracle candidate must be an object"
            )
        exact_entry = candidate.get("exact_v308_entry")
        if (
            not isinstance(exact_entry, str)
            or not exact_entry.endswith(".class")
        ):
            raise ExternalOracleFrontierError(
                "external oracle candidate lacks exact class entry"
            )
        exact_internal = exact_entry[:-6]
        if "$" in exact_internal:
            nested_skipped += 1
            continue

        readable_internal = remaps.get(
            exact_internal,
            exact_internal,
        )
        recovered_internal = collision_remaps.get(
            readable_internal,
            readable_internal,
        )
        if "$" in recovered_internal:
            nested_skipped += 1
            continue

        candidate_by_unit[recovered_internal].append(
            {
                **candidate,
                "exact_v308_internal_name": exact_internal,
                "readable_internal_name": readable_internal,
                "recovered_internal_name": recovered_internal,
            }
        )

    rows: list[dict[str, Any]] = []
    duplicate_candidate_units: list[str] = []
    unmatched_units: list[dict[str, Any]] = []

    for source_unit in sorted(by_unit):
        file_rows = by_unit[source_unit]
        category_counts = Counter(
            str(row.get("category") or "unknown")
            for row in file_rows
        )
        paths = sorted(
            {
                str(row["source_path"]).replace("\\", "/")
                for row in file_rows
            }
        )
        candidates = candidate_by_unit.get(source_unit, [])

        base = {
            "source_unit": source_unit,
            "source_paths": paths,
            "error_count": len(file_rows),
            "categories": dict(sorted(category_counts.items())),
        }
        if not candidates:
            unmatched_units.append(base)
            continue
        if len(candidates) != 1:
            duplicate_candidate_units.append(source_unit)
            continue

        candidate = candidates[0]
        rows.append(
            {
                **base,
                "exact_v308_entry": candidate[
                    "exact_v308_entry"
                ],
                "external_entry": candidate[
                    "external_entry"
                ],
                "external_internal_name": candidate[
                    "external_internal_name"
                ],
                "external_simple_name": candidate[
                    "external_simple_name"
                ],
                "strategy": candidate["strategy"],
                "evidence_tier": candidate[
                    "evidence_tier"
                ],
                "score": candidate["score"],
                "confidence": candidate["confidence"],
                "research_name_candidate": True,
                "semantic_name_accepted": False,
            }
        )

    if duplicate_candidate_units:
        raise ExternalOracleFrontierError(
            "multiple external oracle candidates map to one recovered "
            "source unit: "
            + duplicate_candidate_units[0]
        )

    rows.sort(
        key=lambda row: (
            0 if row["evidence_tier"] == "strong" else 1,
            -int(row["error_count"]),
            row["source_unit"],
        )
    )
    unmatched_units.sort(
        key=lambda row: (
            -int(row["error_count"]),
            row["source_unit"],
        )
    )

    strong = [
        row for row in rows
        if row["evidence_tier"] == "strong"
    ]
    inferred = [
        row for row in rows
        if row["evidence_tier"] == "inferred"
    ]
    material = {
        "javac_frontier_id": private_diagnostic.get(
            "frontier_id"
        ),
        "oracle_id": external_oracle.get("oracle_id"),
        "class_plan_source_sha256": plan_sha,
        "collision_plan_id": collision_plan_id,
        "matched": [
            {
                "source_unit": row["source_unit"],
                "exact_v308_entry": row["exact_v308_entry"],
                "external_entry": row["external_entry"],
                "evidence_tier": row["evidence_tier"],
                "error_count": row["error_count"],
            }
            for row in rows
        ],
        "unmatched_source_units": [
            {
                "source_unit": row["source_unit"],
                "error_count": row["error_count"],
            }
            for row in unmatched_units
        ],
    }
    report_id = (
        "EXTFRONTIER_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "external_oracle_javac_frontier",
        "report_id": report_id,
        "research_only": True,
        "identifiers_included": True,
        "source_mutation_allowed": False,
        "semantic_acceptance_allowed": False,
        "javac_frontier_id": private_diagnostic.get(
            "frontier_id"
        ),
        "javac_diagnostic_report_id": private_diagnostic.get(
            "report_id"
        ),
        "oracle_id": external_oracle.get("oracle_id"),
        "corpus_id": external_oracle.get("corpus_id"),
        "exact_v308_sha256": exact_sha,
        "collision_plan_id": collision_plan_id,
        "summary": {
            "failing_source_units": len(by_unit),
            "matched_source_units": len(rows),
            "strong_source_units": len(strong),
            "inferred_source_units": len(inferred),
            "unmatched_source_units": len(unmatched_units),
            "unmapped_diagnostic_path_count": len(
                unmapped_paths
            ),
            "nested_oracle_candidates_skipped": nested_skipped,
            "matched_errors": sum(
                int(row["error_count"]) for row in rows
            ),
            "strong_errors": sum(
                int(row["error_count"]) for row in strong
            ),
            "inferred_errors": sum(
                int(row["error_count"]) for row in inferred
            ),
            "unmatched_errors": sum(
                int(row["error_count"])
                for row in unmatched_units
            ),
        },
        "matches": rows,
        "unmatched_source_units": unmatched_units,
        "unmapped_diagnostic_paths": [
            {
                "source_path": path,
                "error_count": count,
            }
            for path, count in sorted(
                unmapped_paths.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        "truth_boundary": {
            "external_names_are_research_candidates_only": True,
            "automatic_semantic_promotion": False,
            "automatic_source_rewrite": False,
        },
    }
