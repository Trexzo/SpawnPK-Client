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
_BINDING_ID_RE = re.compile(r"^JAVACBIND_[0-9A-F]{20}$")
_DIAGNOSTIC_ID_RE = re.compile(r"^JAVACDIAG_[0-9A-F]{20}$")
_FRONTIER_ID_RE = re.compile(r"^JAVACFRONTIER_[0-9A-F]{20}$")
_REBUILD_ID_RE = re.compile(r"^CLEANBUILD_[0-9A-F]{20}$")
_WORKSPACE_ID_RE = re.compile(r"^SRCWS_[0-9A-F]{20}$")
_COMPARISON_ID_RE = re.compile(r"^XJAVACFRONTIER_[0-9A-F]{20}$")
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


def _validate_build(
    value: Any,
    *,
    label: str,
    tooling_commit: str,
) -> dict[str, Any]:
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
    binding_id = _require_string(
        value.get("binding_id"),
        f"{label} binding_id",
        _BINDING_ID_RE,
    )
    diagnostic_report_id = _require_string(
        value.get("diagnostic_report_id"),
        f"{label} diagnostic_report_id",
        _DIAGNOSTIC_ID_RE,
    )
    diagnostic_input_sha256 = _require_string(
        value.get("diagnostic_input_sha256"),
        f"{label} diagnostic input",
        _HEX64_RE,
    )
    frontier = _require_string(
        value.get("frontier_id"),
        f"{label} frontier_id",
        _FRONTIER_ID_RE,
    )
    rebuild_id = _require_string(
        value.get("rebuild_id"),
        f"{label} rebuild_id",
        _REBUILD_ID_RE,
    )
    workspace_id = _require_string(
        value.get("workspace_id"),
        f"{label} workspace_id",
        _WORKSPACE_ID_RE,
    )
    source_tree = _require_string(
        value.get("source_tree_sha256"),
        f"{label} source tree",
        _HEX64_RE,
    )
    clean_rebuild_status = value.get("clean_rebuild_status")
    if clean_rebuild_status not in {
        "complete",
        "compile_failed",
        "class_set_mismatch",
    }:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label} clean_rebuild_status is invalid"
        )
    fallback_count = value.get("project_binary_fallback_count")
    if fallback_count != 0:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label} project binary fallback must be zero"
        )
    clean_project_build = value.get("clean_project_build")
    if not isinstance(clean_project_build, bool):
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label} clean_project_build must be boolean"
        )

    binding_material = {
        "tooling_commit": tooling_commit,
        "build_id": build_id,
        "source_authority_sha256": authority,
        "rebuild_id": rebuild_id,
        "workspace_id": workspace_id,
        "source_tree_sha256": source_tree,
        "diagnostic_report_id": diagnostic_report_id,
        "diagnostic_input_sha256": diagnostic_input_sha256,
        "frontier_id": frontier,
        "project_binary_fallback_count": fallback_count,
        "clean_rebuild_status": clean_rebuild_status,
        "clean_project_build": clean_project_build,
    }
    expected_binding_id = (
        "JAVACBIND_" + _stable_digest(binding_material)[:20].upper()
    )
    if binding_id != expected_binding_id:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label} binding ID does not match public authority"
        )

    return {
        **value,
        "build_id": build_id,
        "source_authority_sha256": authority,
        "binding_id": binding_id,
        "diagnostic_report_id": diagnostic_report_id,
        "diagnostic_input_sha256": diagnostic_input_sha256,
        "frontier_id": frontier,
        "rebuild_id": rebuild_id,
        "workspace_id": workspace_id,
        "source_tree_sha256": source_tree,
        "clean_rebuild_status": clean_rebuild_status,
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
    old = _validate_build(
        report.get("old"),
        label=f"{label} old",
        tooling_commit=tooling_commit,
    )
    new = _validate_build(
        report.get("new"),
        label=f"{label} new",
        tooling_commit=tooling_commit,
    )

    comparison = report.get("comparison")
    if not isinstance(comparison, dict) or set(comparison) != _COMPARISON_KEYS:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label}: comparison does not match checkpoint field contract"
        )
    report_id = _require_string(
        comparison.get("report_id"),
        f"{label}: comparison report_id",
        _COMPARISON_ID_RE,
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

    expected_old_percent = (
        100.0
        if summary["old_total_errors"] == 0
        else round(
            summary["shared_errors"]
            * 100.0
            / summary["old_total_errors"],
            4,
        )
    )
    expected_new_percent = (
        100.0
        if summary["new_total_errors"] == 0
        else round(
            summary["shared_errors"]
            * 100.0
            / summary["new_total_errors"],
            4,
        )
    )
    if summary["shared_percent_of_old"] != expected_old_percent:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label}: shared_percent_of_old is inconsistent"
        )
    if summary["shared_percent_of_new"] != expected_new_percent:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label}: shared_percent_of_new is inconsistent"
        )

    categories = sorted(
        set(summary["old_categories"])
        | set(summary["new_categories"])
        | set(summary["shared_categories"])
        | set(summary["old_only_categories"])
        | set(summary["new_only_categories"])
    )
    for category in categories:
        shared_count = summary["shared_categories"].get(category, 0)
        if (
            shared_count
            + summary["old_only_categories"].get(category, 0)
            != summary["old_categories"].get(category, 0)
        ):
            raise CrossVersionJavacCheckpointDeltaError(
                f"{label}: old category decomposition is inconsistent"
            )
        if (
            shared_count
            + summary["new_only_categories"].get(category, 0)
            != summary["new_categories"].get(category, 0)
        ):
            raise CrossVersionJavacCheckpointDeltaError(
                f"{label}: new category decomposition is inconsistent"
            )

    expected_exact = (
        summary["old_only_errors"] == 0
        and summary["new_only_errors"] == 0
    )
    if summary["exact_frontier_equal"] != expected_exact:
        raise CrossVersionJavacCheckpointDeltaError(
            f"{label}: exact_frontier_equal is inconsistent"
        )

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
