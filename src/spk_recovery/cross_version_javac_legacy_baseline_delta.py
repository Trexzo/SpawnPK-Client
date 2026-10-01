from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .cross_version_javac_checkpoint_delta import (
    CrossVersionJavacCheckpointDeltaError,
    validate_cross_version_javac_checkpoint,
)


class CrossVersionJavacLegacyBaselineDeltaError(ValueError):
    pass


_CANONICAL = {
    "fixture_id": "SPK_V307_V308_EXACT_JAVAC_PARITY_07ED6F9_20261001",
    "old_build_id": "v307",
    "new_build_id": "v308",
    "old_authority_sha256": "6232bae206846a4ba8d09766a2dee886b69016066a3f50f83b201bf705f93662",
    "new_authority_sha256": "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6",
    "binary_backtest_id": "XVERBIN_E56BD2FB8CCC172D6184",
    "tooling_commit": "07ed6f961fd9ab67439b1d9428446f914bafeabf",
    "historical_public_anchor_fixture": (
        "fixtures/v307-v308-source-m1-public-frontier-parity.json"
    ),
    "old_binding_id": "JAVACBIND_21E319970E16BE91799B",
    "new_binding_id": "JAVACBIND_C534A43BDA991CC6703C",
    "old_diagnostic_report_id": "JAVACDIAG_788CFA0C3838C4FF6B2D",
    "new_diagnostic_report_id": "JAVACDIAG_F5C704C36B8D3DB9F5ED",
    "old_diagnostic_input_sha256": "48a074e9bf059ad67c75c01b09d8d93fd418d0974dc6b35f4ad8fbebbf55b125",
    "new_diagnostic_input_sha256": "46a2daffeed7c4c0c00f822bf3d2782835f418bbc14d783a0d9b62bfce499452",
    "old_rebuild_id": "CLEANBUILD_AB477016B530F36B14A8",
    "new_rebuild_id": "CLEANBUILD_583BE791331D63209715",
    "old_workspace_id": "SRCWS_F9828CC43A774046A278",
    "new_workspace_id": "SRCWS_05136430C4BD0DB02ED2",
    "old_source_tree_sha256": "acef2dacdc21e2569ec114175998b3cb9b8fd8b321ca764d92d1a32c5bb41b3f",
    "new_source_tree_sha256": "8bbee4b6b8f8d1d12a943c2210690122331fc803f7a1b0f65ac050b464181fbf",
    "report_id": "XJAVACFRONTIER_3029D957ED98E41FC96D",
    "frontier_id": "JAVACFRONTIER_D028FE33F2F3EC395B94",
}

_TOP_KEYS = {
    "schema_version",
    "kind",
    "fixture_id",
    "measurement_status",
    "old_build_id",
    "new_build_id",
    "old_authority_sha256",
    "new_authority_sha256",
    "binary_backtest_id",
    "tooling_commit",
    "historical_public_anchor_fixture",
    "bindings",
    "comparison",
    "run_state",
    "truth_boundary",
    "notes",
}
_BINDING_KEYS = {
    "old_binding_id",
    "new_binding_id",
    "old_diagnostic_report_id",
    "new_diagnostic_report_id",
    "old_diagnostic_input_sha256",
    "new_diagnostic_input_sha256",
    "old_rebuild_id",
    "new_rebuild_id",
    "old_workspace_id",
    "new_workspace_id",
    "old_source_tree_sha256",
    "new_source_tree_sha256",
}
_COMPARISON_KEYS = {
    "report_id",
    "old_frontier_id",
    "new_frontier_id",
    "exact_frontier_equal",
    "old_total_errors",
    "new_total_errors",
    "shared_errors",
    "old_only_errors",
    "new_only_errors",
    "shared_percent_of_old",
    "shared_percent_of_new",
    "old_affected_files",
    "new_affected_files",
    "shared_affected_files",
    "categories",
}
_RUN_STATE_KEYS = {
    "old_release_ready",
    "new_release_ready",
    "equivalent_tooling_recovery_releases_ready",
    "wrapper_exit",
    "frozen_tooling_cleanup_pass",
    "live_main_advanced",
}


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise CrossVersionJavacLegacyBaselineDeltaError(
            f"legacy baseline {label} does not match canonical authority"
        )


def _require_exact_keys(
    value: dict[str, Any],
    expected: set[str],
    label: str,
) -> None:
    actual = set(value)
    if actual == expected:
        return

    unexpected = sorted(actual - expected)
    missing = sorted(expected - actual)
    detail: list[str] = []
    if unexpected:
        detail.append("unexpected=" + ",".join(unexpected))
    if missing:
        detail.append("missing=" + ",".join(missing))
    suffix = ": " + " ".join(detail) if detail else ""
    raise CrossVersionJavacLegacyBaselineDeltaError(
        f"legacy baseline {label} does not match canonical field contract"
        + suffix
    )


def validate_legacy_exact_parity_baseline(
    report: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(report, dict):
        raise CrossVersionJavacLegacyBaselineDeltaError(
            "legacy baseline must be an object"
        )
    if report.get("schema_version") != 1:
        raise CrossVersionJavacLegacyBaselineDeltaError(
            "legacy baseline schema_version must be 1"
        )
    if report.get("kind") != "cross_version_exact_javac_frontier_parity_checkpoint":
        raise CrossVersionJavacLegacyBaselineDeltaError(
            "unsupported legacy baseline kind"
        )
    if report.get("measurement_status") != (
        "exact_private_comparator_executed_redacted_checkpoint"
    ):
        raise CrossVersionJavacLegacyBaselineDeltaError(
            "legacy baseline measurement_status is not canonical"
        )

    _require_exact_keys(report, _TOP_KEYS, "top-level")

    if not isinstance(report.get("truth_boundary"), dict):
        raise CrossVersionJavacLegacyBaselineDeltaError(
            "legacy baseline truth_boundary must be an object"
        )
    if not isinstance(report.get("notes"), list):
        raise CrossVersionJavacLegacyBaselineDeltaError(
            "legacy baseline notes must be an array"
        )

    for key in (
        "fixture_id",
        "old_build_id",
        "new_build_id",
        "old_authority_sha256",
        "new_authority_sha256",
        "binary_backtest_id",
        "tooling_commit",
        "historical_public_anchor_fixture",
    ):
        _require_equal(report.get(key), _CANONICAL[key], key)

    bindings = report.get("bindings")
    comparison = report.get("comparison")
    run_state = report.get("run_state")
    if not isinstance(bindings, dict):
        raise CrossVersionJavacLegacyBaselineDeltaError(
            "legacy baseline bindings must be an object"
        )
    if not isinstance(comparison, dict):
        raise CrossVersionJavacLegacyBaselineDeltaError(
            "legacy baseline comparison must be an object"
        )
    if not isinstance(run_state, dict):
        raise CrossVersionJavacLegacyBaselineDeltaError(
            "legacy baseline run_state must be an object"
        )

    _require_exact_keys(bindings, _BINDING_KEYS, "bindings")
    _require_exact_keys(comparison, _COMPARISON_KEYS, "comparison")
    _require_exact_keys(run_state, _RUN_STATE_KEYS, "run_state")

    for key in (
        "old_binding_id",
        "new_binding_id",
        "old_diagnostic_report_id",
        "new_diagnostic_report_id",
        "old_diagnostic_input_sha256",
        "new_diagnostic_input_sha256",
        "old_rebuild_id",
        "new_rebuild_id",
        "old_workspace_id",
        "new_workspace_id",
        "old_source_tree_sha256",
        "new_source_tree_sha256",
    ):
        _require_equal(bindings.get(key), _CANONICAL[key], f"bindings.{key}")

    _require_equal(comparison.get("report_id"), _CANONICAL["report_id"], "comparison.report_id")
    _require_equal(comparison.get("old_frontier_id"), _CANONICAL["frontier_id"], "comparison.old_frontier_id")
    _require_equal(comparison.get("new_frontier_id"), _CANONICAL["frontier_id"], "comparison.new_frontier_id")

    expected_scalars = {
        "exact_frontier_equal": True,
        "old_total_errors": 350,
        "new_total_errors": 350,
        "shared_errors": 350,
        "old_only_errors": 0,
        "new_only_errors": 0,
        "shared_percent_of_old": 100.0,
        "shared_percent_of_new": 100.0,
        "old_affected_files": 75,
        "new_affected_files": 75,
        "shared_affected_files": 75,
    }
    for key, expected in expected_scalars.items():
        _require_equal(comparison.get(key), expected, f"comparison.{key}")

    categories = comparison.get("categories")
    expected_categories = {
        "bad_operand_type": 2,
        "cannot_apply_arguments": 11,
        "cannot_be_dereferenced": 42,
        "cannot_find_symbol": 154,
        "incompatible_types": 45,
        "non_static_from_static_context": 39,
        "other": 38,
        "package_does_not_exist": 9,
        "private_access": 9,
        "protected_access": 1,
    }
    _require_equal(categories, expected_categories, "comparison.categories")
    if sum(categories.values()) != 350:
        raise CrossVersionJavacLegacyBaselineDeltaError(
            "legacy baseline categories do not sum to total errors"
        )

    expected_run_state = {
        "old_release_ready": False,
        "new_release_ready": False,
        "equivalent_tooling_recovery_releases_ready": False,
        "wrapper_exit": 3,
        "frozen_tooling_cleanup_pass": True,
        "live_main_advanced": False,
    }
    for key, expected in expected_run_state.items():
        _require_equal(run_state.get(key), expected, f"run_state.{key}")

    summary = {
        "old_total_errors": 350,
        "new_total_errors": 350,
        "shared_errors": 350,
        "old_only_errors": 0,
        "new_only_errors": 0,
        "shared_percent_of_old": 100.0,
        "shared_percent_of_new": 100.0,
        "old_affected_files": 75,
        "new_affected_files": 75,
        "shared_affected_files": 75,
        "old_categories": dict(sorted(categories.items())),
        "new_categories": dict(sorted(categories.items())),
        "shared_categories": dict(sorted(categories.items())),
        "old_only_categories": {},
        "new_only_categories": {},
        "exact_frontier_equal": True,
    }
    return {
        "fixture_id": report["fixture_id"],
        "tooling_commit": report["tooling_commit"],
        "binary_backtest_id": report["binary_backtest_id"],
        "old": {
            "build_id": report["old_build_id"],
            "source_authority_sha256": report["old_authority_sha256"],
            "binding_id": bindings["old_binding_id"],
            "diagnostic_report_id": bindings["old_diagnostic_report_id"],
            "diagnostic_input_sha256": bindings["old_diagnostic_input_sha256"],
            "frontier_id": comparison["old_frontier_id"],
            "rebuild_id": bindings["old_rebuild_id"],
            "workspace_id": bindings["old_workspace_id"],
            "source_tree_sha256": bindings["old_source_tree_sha256"],
        },
        "new": {
            "build_id": report["new_build_id"],
            "source_authority_sha256": report["new_authority_sha256"],
            "binding_id": bindings["new_binding_id"],
            "diagnostic_report_id": bindings["new_diagnostic_report_id"],
            "diagnostic_input_sha256": bindings["new_diagnostic_input_sha256"],
            "frontier_id": comparison["new_frontier_id"],
            "rebuild_id": bindings["new_rebuild_id"],
            "workspace_id": bindings["new_workspace_id"],
            "source_tree_sha256": bindings["new_source_tree_sha256"],
        },
        "comparison": {
            "report_id": comparison["report_id"],
            "summary": summary,
        },
    }


def _delta(current: int | float, baseline: int | float) -> int | float:
    value = current - baseline
    return round(value, 4) if isinstance(value, float) else value


def _category_delta(
    baseline: dict[str, int],
    current: dict[str, int],
) -> dict[str, int]:
    return {
        key: current.get(key, 0) - baseline.get(key, 0)
        for key in sorted(set(baseline) | set(current))
        if current.get(key, 0) != baseline.get(key, 0)
    }


def build_cross_version_javac_legacy_baseline_delta(
    baseline_report: dict[str, Any],
    current_checkpoint_report: dict[str, Any],
) -> dict[str, Any]:
    baseline = validate_legacy_exact_parity_baseline(baseline_report)
    try:
        current = validate_cross_version_javac_checkpoint(
            current_checkpoint_report,
            label="current",
        )
    except CrossVersionJavacCheckpointDeltaError as exc:
        raise CrossVersionJavacLegacyBaselineDeltaError(str(exc)) from exc

    for side in ("old", "new"):
        for key in ("build_id", "source_authority_sha256"):
            if baseline[side][key] != current[side][key]:
                raise CrossVersionJavacLegacyBaselineDeltaError(
                    f"{side} {key} changed from canonical legacy baseline"
                )
    if baseline["binary_backtest_id"] != current["binary_backtest_id"]:
        raise CrossVersionJavacLegacyBaselineDeltaError(
            "binary_backtest_id changed from canonical legacy baseline"
        )

    base_summary = baseline["comparison"]["summary"]
    cur_summary = current["comparison"]["summary"]
    scalar_fields = (
        "old_total_errors",
        "new_total_errors",
        "shared_errors",
        "old_only_errors",
        "new_only_errors",
        "shared_percent_of_old",
        "shared_percent_of_new",
        "old_affected_files",
        "new_affected_files",
        "shared_affected_files",
    )
    category_fields = (
        "old_categories",
        "new_categories",
        "shared_categories",
        "old_only_categories",
        "new_only_categories",
    )
    scalar_delta = {
        key: _delta(cur_summary[key], base_summary[key])
        for key in scalar_fields
    }
    category_delta = {
        key: _category_delta(base_summary[key], cur_summary[key])
        for key in category_fields
    }

    before = base_summary["exact_frontier_equal"]
    after = cur_summary["exact_frontier_equal"]
    if before == after:
        equality_transition = "preserved_true" if after else "preserved_false"
    elif after:
        equality_transition = "gained"
    else:
        equality_transition = "lost"

    material = {
        "baseline_fixture_id": baseline["fixture_id"],
        "current_checkpoint_id": current["checkpoint_id"],
        "old_build_id": baseline["old"]["build_id"],
        "new_build_id": baseline["new"]["build_id"],
        "old_source_authority_sha256": baseline["old"]["source_authority_sha256"],
        "new_source_authority_sha256": baseline["new"]["source_authority_sha256"],
        "binary_backtest_id": baseline["binary_backtest_id"],
        "baseline_tooling_commit": baseline["tooling_commit"],
        "current_tooling_commit": current["tooling_commit"],
        "scalar_delta": scalar_delta,
        "category_delta": category_delta,
        "exact_frontier_equality_transition": equality_transition,
        "old_frontier_changed": (
            baseline["old"]["frontier_id"] != current["old"]["frontier_id"]
        ),
        "new_frontier_changed": (
            baseline["new"]["frontier_id"] != current["new"]["frontier_id"]
        ),
        "old_source_tree_changed": (
            baseline["old"]["source_tree_sha256"]
            != current["old"]["source_tree_sha256"]
        ),
        "new_source_tree_changed": (
            baseline["new"]["source_tree_sha256"]
            != current["new"]["source_tree_sha256"]
        ),
    }
    return {
        "schema_version": 1,
        "kind": "cross_version_javac_legacy_baseline_delta",
        "delta_id": (
            "XJAVACLEGACYDELTA_" + _stable_digest(material)[:20].upper()
        ),
        **material,
        "identifiers_included": False,
        "note": (
            "Aggregate-only delta from the canonical pre-checkpoint 350/350 "
            "legacy fixture to one verified modern XJAVACCHECKPOINT artifact. "
            "The baseline is intentionally identified by fixture_id, not by "
            "a fabricated historical checkpoint ID, and this report does not "
            "identify individual diagnostic-family transitions."
        ),
    }


def write_cross_version_javac_legacy_baseline_delta(
    report: dict[str, Any],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
