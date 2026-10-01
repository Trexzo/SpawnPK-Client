from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .cross_version_javac_checkpoint import (
    CrossVersionJavacCheckpointError,
    _PUBLIC_SUMMARY_KEYS,
    _stable_digest,
    _validate_public_summary,
)


class CrossVersionJavacCheckpointDeltaError(ValueError):
    pass


_CHECKPOINT_ID_RE = re.compile(r"^XJAVACCHECKPOINT_[0-9A-F]{20}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_BINARY_ID_RE = re.compile(r"^XVERBIN_[0-9A-F]{20}$")
_PUBLIC_BUILD_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_TOP_KEYS = {
    "schema_version",
    "kind",
    "checkpoint_id",
    "tooling_commit",
    "binary_backtest_id",
    "old",
    "new",
    "comparison",
    "identifiers_included",
    "note",
}
_BUILD_KEYS = {
    "build_id",
    "source_authority_sha256",
    "binding_id",
    "diagnostic_report_id",
    "diagnostic_input_sha256",
    "frontier_id",
    "rebuild_id",
    "workspace_id",
    "source_tree_sha256",
    "clean_rebuild_status",
    "clean_project_build",
    "project_binary_fallback_count",
}
_COMPARISON_KEYS = {"report_id", "summary"}


def _require_string(value: Any, label: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label} has invalid format"
        )
    return value


def _validate_build(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _BUILD_KEYS:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label} build does not match checkpoint field contract"
        )
    build_id = _require_string(
        value.get("build_id"),
        f"{label} build_id",
        _PUBLIC_BUILD_ID_RE,
    )
    authority = _require_string(
        value.get("source_authority_sha256"),
        f"{label} source authority",
        _HEX64_RE,
    )
    source_tree = _require_string(
        value.get("source_tree_sha256"),
        f"{label} source tree",
        _HEX64_RE,
    )
    frontier = value.get("frontier_id")
    if not isinstance(frontier, str) or not re.fullmatch(
        r"^JAVACFRONTIER_[0-9A-F]{20}$", frontier
    ):
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label} frontier_id has invalid format"
        )
    if value.get("project_binary_fallback_count") != 0:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label} project binary fallback must be zero"
        )
    if not isinstance(value.get("clean_project_build"), bool):
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label} clean_project_build must be boolean"
        )
    return {
        **value,
        "build_id": build_id,
        "source_authority_sha256": authority,
        "source_tree_sha256": source_tree,
        "frontier_id": frontier,
    }


def validate_cross_version_javac_checkpoint(
    report: dict[str, Any],
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(report, dict) or set(report) != _TOP_KEYS:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label}: checkpoint does not match public field contract"
        )
    if (
        report.get("schema_version") != 1
        or report.get("kind") != "cross_version_javac_checkpoint"
        or report.get("identifiers_included") is not False
    ):
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label}: unsupported or non-redacted checkpoint"
        )
    checkpoint_id = _require_string(
        report.get("checkpoint_id"),
        f"{label} checkpoint_id",
        _CHECKPOINT_ID_RE,
    )
    tooling_commit = _require_string(
        report.get("tooling_commit"),
        f"{label} tooling_commit",
        _COMMIT_RE,
    )
    binary_id = report.get("binary_backtest_id")
    if binary_id is not None:
        binary_id = _require_string(
            binary_id,
            f"{label} binary_backtest_id",
            _BINARY_ID_RE,
        )
    old = _validate_build(report.get("old"), label=f"{label} old")
    new = _validate_build(report.get("new"), label=f"{label} new")

    comparison = report.get("comparison")
    if not isinstance(comparison, dict) or set(comparison) != _COMPARISON_KEYS:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label}: comparison does not match checkpoint field contract"
        )
    report_id = comparison.get("report_id")
    if not isinstance(report_id, str) or not re.fullmatch(
        r"^XJAVACFRONTIER_[0-9A-F]{20}$", report_id
    ):
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label}: comparison report_id has invalid format"
        )
    summary = comparison.get("summary")
    if not isinstance(summary, dict) or set(summary) != _PUBLIC_SUMMARY_KEYS:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label}: comparison summary does not match public field contract"
        )
    try:
        summary = _validate_public_summary(summary)
    except CrossVersionJavacCheckpointError as exc:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label}: {exc}"
        ) from exc

    material = {
        "tooling_commit": tooling_commit,
        "binary_backtest_id": binary_id,
        "old": old,
        "new": new,
        "comparison": {
            "report_id": report_id,
            "summary": summary,
        },
    }
    expected_id = (
        "XJAVACCHECKPOINT_" + _stable_digest(material)[:20].upper()
    )
    if checkpoint_id != expected_id:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label}: checkpoint ID does not match public authority"
        )
    return {
        "checkpoint_id": checkpoint_id,
        **material,
    }


def _delta(current: int | float, baseline: int | float) -> int | float:
    value = current - baseline
    if isinstance(value, float):
        return round(value, 4)
    return value


def _category_delta(
    baseline: dict[str, int],
    current: dict[str, int],
) -> dict[str, int]:
    keys = sorted(set(baseline) | set(current))
    return {
        key: current.get(key, 0) - baseline.get(key, 0)
        for key in keys
        if current.get(key, 0) != baseline.get(key, 0)
    }


def build_cross_version_javac_checkpoint_delta(
    baseline_report: dict[str, Any],
    current_report: dict[str, Any],
) -> dict[str, Any]:
    baseline = validate_cross_version_javac_checkpoint(
        baseline_report,
        label="baseline",
    )
    current = validate_cross_version_javac_checkpoint(
        current_report,
        label="current",
    )

    for side in ("old", "new"):
        for key in ("build_id", "source_authority_sha256"):
            if baseline[side][key] != current[side][key]:
                raise CrossVersionJavacCheckpointDeltaError(
                    f"{side} {key} changed across checkpoints"
                )
    if baseline["binary_backtest_id"] != current["binary_backtest_id"]:
        raise CrossVersionJavacCheckpointDeltaError(
            "binary_backtest_id changed across checkpoints"
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
    scalar_delta = {
        key: _delta(cur_summary[key], base_summary[key])
        for key in scalar_fields
    }
    category_delta = {
        key: _category_delta(base_summary[key], cur_summary[key])
        for key in (
            "old_categories",
            "new_categories",
            "shared_categories",
            "old_only_categories",
            "new_only_categories",
        )
    }

    equality_before = base_summary["exact_frontier_equal"]
    equality_after = cur_summary["exact_frontier_equal"]
    if equality_before == equality_after:
        equality_transition = "preserved_true" if equality_after else "preserved_false"
    elif equality_after:
        equality_transition = "gained"
    else:
        equality_transition = "lost"

    material = {
        "baseline_checkpoint_id": baseline["checkpoint_id"],
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
    delta_id = (
        "XJAVACCHECKDELTA_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )
    return {
        "schema_version": 1,
        "kind": "cross_version_javac_checkpoint_delta",
        "delta_id": delta_id,
        **material,
        "identifiers_included": False,
        "note": (
            "Public-safe aggregate delta between two verified redacted javac "
            "checkpoints. It does not identify individual diagnostic-family "
            "transitions."
        ),
    }


def write_cross_version_javac_checkpoint_delta(
    report: dict[str, Any],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
