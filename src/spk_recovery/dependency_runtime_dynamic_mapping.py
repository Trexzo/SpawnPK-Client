from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from .dependency_artifact_proof import (
    DependencyArtifactProofError,
    _artifact_index,
)
from .dependency_remap_proof import (
    DependencyRemapProofError,
    _bundled_index,
    _field_sequence,
    _ordinary_method_sequence,
    _structural_groups,
)
from .dependency_runtime_frontier import (
    DependencyRuntimeFrontierError,
    _artifact_rows_key,
    _load_private_plan,
    _normalize_prefixes,
)


class DependencyRuntimeDynamicMappingError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _load_augmented(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRuntimeDynamicMappingError(
            "invalid augmented runtime closure authority"
        ) from exc
    if value.get("kind") != "dependency_runtime_augmented_closure":
        raise DependencyRuntimeDynamicMappingError(
            "unexpected augmented runtime closure kind"
        )
    if value.get("identifiers_included") is not True:
        raise DependencyRuntimeDynamicMappingError(
            "dynamic mapping proof requires private augmented closure"
        )
    return value


def build_dependency_runtime_dynamic_mapping_proof(
    private_augmented_closure_path: Path,
    private_replacement_plan_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    augmented = _load_augmented(
        private_augmented_closure_path.resolve()
    )
    try:
        plan = _load_private_plan(
            private_replacement_plan_path.resolve()
        )
    except DependencyRuntimeFrontierError as exc:
        raise DependencyRuntimeDynamicMappingError(str(exc)) from exc

    bundled_jar = bundled_jar.resolve()
    prefixes = _normalize_prefixes(plan.get("project_prefixes"))

    if augmented.get("replacement_plan_id") != plan.get(
        "replacement_plan_id"
    ):
        raise DependencyRuntimeDynamicMappingError(
            "augmented closure is bound to a different DEPREPLACE"
        )

    try:
        bundled = _bundled_index(
            bundled_jar,
            project_prefixes=prefixes,
        )
    except DependencyRemapProofError as exc:
        raise DependencyRuntimeDynamicMappingError(str(exc)) from exc

    if augmented.get("bundled_jar_sha256") != plan.get(
        "bundled_jar_sha256"
    ):
        raise DependencyRuntimeDynamicMappingError(
            "augmented closure bundled authority differs from DEPREPLACE"
        )

    release = plan.get("java_release")
    if (
        not isinstance(release, int)
        or isinstance(release, bool)
        or release < 1
    ):
        raise DependencyRuntimeDynamicMappingError(
            "private DEPREPLACE has invalid java_release"
        )

    try:
        official, artifact_by_class, artifact_rows = _artifact_index(
            [path.resolve() for path in official_artifacts],
            java_release=release,
        )
    except DependencyArtifactProofError as exc:
        raise DependencyRuntimeDynamicMappingError(str(exc)) from exc

    expected_rows = plan.get("official_artifacts")
    if (
        not isinstance(expected_rows, list)
        or _artifact_rows_key(expected_rows)
        != _artifact_rows_key(artifact_rows)
    ):
        raise DependencyRuntimeDynamicMappingError(
            "official artifact authority differs from DEPREPLACE"
        )

    gap_sources: dict[str, set[str]] = {}
    for row in augmented.get("dynamic_roots", []):
        if (
            isinstance(row, dict)
            and row.get("status") == "dynamic_mapping_authority_gap"
            and isinstance(row.get("owner"), str)
        ):
            gap_sources.setdefault(
                str(row["owner"]), set()
            ).add("dynamic_root")

    for row in augmented.get("new_owners", []):
        if (
            isinstance(row, dict)
            and row.get("status") == "dynamic_mapping_authority_gap"
            and isinstance(row.get("owner"), str)
        ):
            gap_sources.setdefault(
                str(row["owner"]), set()
            ).add("closure_edge")

    bundled_groups = _structural_groups(bundled)
    official_groups = _structural_groups(official)

    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    accepted_strategy_counts: Counter[str] = Counter()
    member_authority_required_count = 0

    for index, owner in enumerate(sorted(gap_sources), start=1):
        if any(owner.startswith(prefix) for prefix in prefixes):
            raise DependencyRuntimeDynamicMappingError(
                "dynamic mapping gap overlaps project prefix"
            )
        parsed = bundled.get(owner)
        if parsed is None:
            raise DependencyRuntimeDynamicMappingError(
                f"dynamic mapping gap class missing from bundled authority: {owner}"
            )

        structural = parsed.structural_sha256()
        same = official.get(owner)
        old_candidates = bundled_groups.get(structural, [])
        new_candidates = official_groups.get(structural, [])

        new_owner: str | None = None
        artifact: str | None = None
        strategy: str | None = None

        if (
            same is not None
            and same.structural_sha256() == structural
        ):
            status = "accepted_class_mapping"
            strategy = "identity_structural"
            new_owner = owner
            artifact = artifact_by_class.get(owner)
        elif (
            len(old_candidates) == 1
            and len(new_candidates) == 1
        ):
            status = "accepted_class_mapping"
            strategy = "unique_structural"
            new_owner = new_candidates[0]
            artifact = artifact_by_class.get(new_owner)
        elif new_candidates:
            status = "ambiguous_structural_match"
        else:
            status = "no_official_structural_match"

        field_equal: bool | None = None
        methods_equal: bool | None = None
        if new_owner is not None:
            target = official.get(new_owner)
            if target is None or artifact is None:
                raise DependencyRuntimeDynamicMappingError(
                    "accepted dynamic class mapping lacks exact official artifact target"
                )
            field_equal = (
                _field_sequence(parsed)
                == _field_sequence(target)
            )
            methods_equal = (
                _ordinary_method_sequence(parsed)
                == _ordinary_method_sequence(target)
            )
            if not field_equal or not methods_equal:
                raise DependencyRuntimeDynamicMappingError(
                    "accepted structural mapping failed ordered member-sequence verification"
                )
            accepted_strategy_counts[strategy] += 1
            member_authority_required_count += 1

        status_counts[status] += 1
        public = {
            "dynamic_mapping_id": f"DEPDYNMAPROW_{index:05d}",
            "status": status,
            "strategy": strategy,
            "source_kinds": sorted(gap_sources[owner]),
            "field_sequence_equal": field_equal,
            "ordinary_method_sequence_equal": methods_equal,
            "member_authority_required": (
                status == "accepted_class_mapping"
            ),
            "official_artifact_bound": artifact is not None,
        }
        public_rows.append(public)
        if include_identifiers:
            private_rows.append(
                {
                    **public,
                    "old_owner": owner,
                    "new_owner": new_owner,
                    "artifact": artifact,
                    "structural_sha256": structural,
                    "official_structural_candidate_count": len(
                        new_candidates
                    ),
                    "bundled_structural_candidate_count": len(
                        old_candidates
                    ),
                }
            )

    accepted_count = status_counts.get(
        "accepted_class_mapping",
        0,
    )
    ambiguous_count = status_counts.get(
        "ambiguous_structural_match",
        0,
    )
    no_match_count = status_counts.get(
        "no_official_structural_match",
        0,
    )

    material = {
        "runtime_augmented_closure_id": augmented.get(
            "runtime_augmented_closure_id"
        ),
        "replacement_plan_id": plan.get(
            "replacement_plan_id"
        ),
        "bundled_jar_sha256": plan.get(
            "bundled_jar_sha256"
        ),
        "official_artifact_sha256": sorted(
            str(row["sha256"]).lower()
            for row in artifact_rows
        ),
        "rows": public_rows,
        "ready_for_dynamic_root_promotion": False,
    }
    proof_id = (
        "DEPRUNTIMEDYNMAP_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "dependency_runtime_dynamic_mapping_proof",
        "runtime_dynamic_mapping_id": proof_id,
        "runtime_augmented_closure_id": augmented.get(
            "runtime_augmented_closure_id"
        ),
        "replacement_plan_id": plan.get(
            "replacement_plan_id"
        ),
        "bundled_jar_sha256": plan.get(
            "bundled_jar_sha256"
        ),
        "official_artifact_sha256": material[
            "official_artifact_sha256"
        ],
        "summary": {
            "dynamic_mapping_gap_target_count": len(
                gap_sources
            ),
            "accepted_class_mapping_count": accepted_count,
            "identity_structural_count": (
                accepted_strategy_counts.get(
                    "identity_structural",
                    0,
                )
            ),
            "unique_structural_count": (
                accepted_strategy_counts.get(
                    "unique_structural",
                    0,
                )
            ),
            "renamed_class_mapping_count": sum(
                1
                for row in private_rows
                if row.get("status")
                == "accepted_class_mapping"
                and row.get("old_owner")
                != row.get("new_owner")
            )
            if include_identifiers
            else accepted_strategy_counts.get(
                "unique_structural",
                0,
            ),
            "ambiguous_structural_match_count": ambiguous_count,
            "no_official_structural_match_count": no_match_count,
            "member_authority_required_count": (
                member_authority_required_count
            ),
            "ready_for_dynamic_root_promotion": False,
        },
        "rows": (
            private_rows
            if include_identifiers
            else public_rows
        ),
        "identifiers_included": include_identifiers,
        "note": (
            "Accepted class mapping is structural class authority only. "
            "Full member/API replacement authority remains required before "
            "a dynamic-only bundled target may be promoted to runtime "
            "replacement authority."
        ),
    }


def write_dependency_runtime_dynamic_mapping_proof(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
