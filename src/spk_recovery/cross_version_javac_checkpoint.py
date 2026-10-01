from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


class CrossVersionJavacCheckpointError(ValueError):
    pass


_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_BINDING_ID_RE = re.compile(r"^JAVACBIND_[0-9A-F]{20}$")
_DIAGNOSTIC_ID_RE = re.compile(r"^JAVACDIAG_[0-9A-F]{20}$")
_FRONTIER_ID_RE = re.compile(r"^JAVACFRONTIER_[0-9A-F]{20}$")
_REBUILD_ID_RE = re.compile(r"^CLEANBUILD_[0-9A-F]{20}$")
_COMPARISON_ID_RE = re.compile(r"^XJAVACFRONTIER_[0-9A-F]{20}$")
_BINARY_BACKTEST_ID_RE = re.compile(r"^XVERBIN_[0-9A-F]{20}$")
_PUBLIC_FAMILY_KEYS = {
    "family_id",
    "file_id",
    "category",
    "symbol_kind",
    "symbol_shape",
    "location_kind",
    "old_count",
    "new_count",
    "shared_count",
    "old_only_count",
    "new_only_count",
}
_PUBLIC_SUMMARY_KEYS = {
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
    "old_categories",
    "new_categories",
    "shared_categories",
    "old_only_categories",
    "new_only_categories",
    "exact_frontier_equal",
}


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _require_string(
    value: Any,
    *,
    label: str,
    pattern: re.Pattern[str] | None = None,
) -> str:
    if not isinstance(value, str) or not value:
        raise CrossVersionJavacCheckpointError(
            f"{label} must be a non-empty string"
        )
    if pattern is not None and pattern.fullmatch(value) is None:
        raise CrossVersionJavacCheckpointError(
            f"{label} has invalid format"
        )
    return value


def _validate_binding(
    binding: dict[str, Any],
    *,
    label: str,
) -> dict[str, Any]:
    if (
        binding.get("schema_version") != 1
        or binding.get("kind") != "javac_build_binding"
    ):
        raise CrossVersionJavacCheckpointError(
            f"{label}: unsupported javac build binding"
        )
    if binding.get("identifiers_included") is not False:
        raise CrossVersionJavacCheckpointError(
            f"{label}: binding must be redacted"
        )

    binding_id = _require_string(
        binding.get("binding_id"),
        label=f"{label}: binding_id",
        pattern=_BINDING_ID_RE,
    )
    tooling_commit = _require_string(
        binding.get("tooling_commit"),
        label=f"{label}: tooling_commit",
        pattern=_COMMIT_RE,
    )
    build_id = _require_string(
        binding.get("build_id"),
        label=f"{label}: build_id",
    )
    source_authority_sha256 = _require_string(
        binding.get("source_authority_sha256"),
        label=f"{label}: source_authority_sha256",
        pattern=_HEX64_RE,
    )
    rebuild_id = _require_string(
        binding.get("rebuild_id"),
        label=f"{label}: rebuild_id",
        pattern=_REBUILD_ID_RE,
    )
    workspace_id = _require_string(
        binding.get("workspace_id"),
        label=f"{label}: workspace_id",
    )
    source_tree_sha256 = _require_string(
        binding.get("source_tree_sha256"),
        label=f"{label}: source_tree_sha256",
        pattern=_HEX64_RE,
    )
    diagnostic_report_id = _require_string(
        binding.get("diagnostic_report_id"),
        label=f"{label}: diagnostic_report_id",
        pattern=_DIAGNOSTIC_ID_RE,
    )
    diagnostic_input_sha256 = _require_string(
        binding.get("diagnostic_input_sha256"),
        label=f"{label}: diagnostic_input_sha256",
        pattern=_HEX64_RE,
    )
    frontier_id = _require_string(
        binding.get("frontier_id"),
        label=f"{label}: frontier_id",
        pattern=_FRONTIER_ID_RE,
    )

    fallback_count = binding.get("project_binary_fallback_count")
    if (
        isinstance(fallback_count, bool)
        or not isinstance(fallback_count, int)
        or fallback_count != 0
    ):
        raise CrossVersionJavacCheckpointError(
            f"{label}: project binary fallback must be zero"
        )

    clean_rebuild_status = binding.get("clean_rebuild_status")
    if clean_rebuild_status not in {
        "complete",
        "compile_failed",
        "class_set_mismatch",
    }:
        raise CrossVersionJavacCheckpointError(
            f"{label}: invalid clean rebuild status"
        )
    clean_project_build = binding.get("clean_project_build")
    if not isinstance(clean_project_build, bool):
        raise CrossVersionJavacCheckpointError(
            f"{label}: clean_project_build must be boolean"
        )

    material = {
        "tooling_commit": tooling_commit,
        "build_id": build_id,
        "source_authority_sha256": source_authority_sha256,
        "rebuild_id": rebuild_id,
        "workspace_id": workspace_id,
        "source_tree_sha256": source_tree_sha256,
        "diagnostic_report_id": diagnostic_report_id,
        "diagnostic_input_sha256": diagnostic_input_sha256,
        "frontier_id": frontier_id,
        "project_binary_fallback_count": fallback_count,
        "clean_rebuild_status": clean_rebuild_status,
        "clean_project_build": clean_project_build,
    }
    expected_binding_id = (
        "JAVACBIND_" + _stable_digest(material)[:20].upper()
    )
    if binding_id != expected_binding_id:
        raise CrossVersionJavacCheckpointError(
            f"{label}: binding ID does not match public authority"
        )

    return {
        "binding_id": binding_id,
        **material,
    }


def _validate_comparison(
    comparison: dict[str, Any],
) -> dict[str, Any]:
    if (
        comparison.get("schema_version") != 1
        or comparison.get("kind") != "cross_version_javac_frontier"
    ):
        raise CrossVersionJavacCheckpointError(
            "unsupported cross-version javac report"
        )
    if comparison.get("identifiers_included") is not False:
        raise CrossVersionJavacCheckpointError(
            "cross-version javac report must be redacted"
        )

    report_id = _require_string(
        comparison.get("report_id"),
        label="comparison report_id",
        pattern=_COMPARISON_ID_RE,
    )
    old_diagnostic_report_id = _require_string(
        comparison.get("old_diagnostic_report_id"),
        label="old diagnostic report ID",
        pattern=_DIAGNOSTIC_ID_RE,
    )
    new_diagnostic_report_id = _require_string(
        comparison.get("new_diagnostic_report_id"),
        label="new diagnostic report ID",
        pattern=_DIAGNOSTIC_ID_RE,
    )
    old_diagnostic_input_sha256 = _require_string(
        comparison.get("old_diagnostic_input_sha256"),
        label="old diagnostic input SHA-256",
        pattern=_HEX64_RE,
    )
    new_diagnostic_input_sha256 = _require_string(
        comparison.get("new_diagnostic_input_sha256"),
        label="new diagnostic input SHA-256",
        pattern=_HEX64_RE,
    )
    old_frontier_id = _require_string(
        comparison.get("old_frontier_id"),
        label="old frontier ID",
        pattern=_FRONTIER_ID_RE,
    )
    new_frontier_id = _require_string(
        comparison.get("new_frontier_id"),
        label="new frontier ID",
        pattern=_FRONTIER_ID_RE,
    )

    summary = comparison.get("summary")
    if not isinstance(summary, dict):
        raise CrossVersionJavacCheckpointError(
            "comparison summary must be an object"
        )
    summary_keys = set(summary)
    if summary_keys != _PUBLIC_SUMMARY_KEYS:
        unexpected = sorted(summary_keys - _PUBLIC_SUMMARY_KEYS)
        missing = sorted(_PUBLIC_SUMMARY_KEYS - summary_keys)
        detail = []
        if unexpected:
            detail.append("unexpected=" + ",".join(unexpected))
        if missing:
            detail.append("missing=" + ",".join(missing))
        raise CrossVersionJavacCheckpointError(
            "comparison summary does not match the public field contract"
            + (": " + " ".join(detail) if detail else "")
        )

    families = comparison.get("families")
    if not isinstance(families, list):
        raise CrossVersionJavacCheckpointError(
            "comparison families must be an array"
        )
    for index, family in enumerate(families):
        if not isinstance(family, dict):
            raise CrossVersionJavacCheckpointError(
                f"comparison family {index} must be an object"
            )
        family_keys = set(family)
        if family_keys != _PUBLIC_FAMILY_KEYS:
            unexpected = sorted(family_keys - _PUBLIC_FAMILY_KEYS)
            missing = sorted(_PUBLIC_FAMILY_KEYS - family_keys)
            detail = []
            if unexpected:
                detail.append("unexpected=" + ",".join(unexpected))
            if missing:
                detail.append("missing=" + ",".join(missing))
            raise CrossVersionJavacCheckpointError(
                f"comparison family {index} does not match the public "
                "field contract"
                + (": " + " ".join(detail) if detail else "")
            )

    material = {
        "old_diagnostic_report_id": old_diagnostic_report_id,
        "new_diagnostic_report_id": new_diagnostic_report_id,
        "old_diagnostic_input_sha256": old_diagnostic_input_sha256,
        "new_diagnostic_input_sha256": new_diagnostic_input_sha256,
        "old_frontier_id": old_frontier_id,
        "new_frontier_id": new_frontier_id,
        "summary": summary,
        "families": families,
    }
    expected_report_id = (
        "XJAVACFRONTIER_" + _stable_digest(material)[:20].upper()
    )
    if report_id != expected_report_id:
        raise CrossVersionJavacCheckpointError(
            "comparison report ID does not match redacted authority"
        )

    return {
        "report_id": report_id,
        "old_diagnostic_report_id": old_diagnostic_report_id,
        "new_diagnostic_report_id": new_diagnostic_report_id,
        "old_diagnostic_input_sha256": old_diagnostic_input_sha256,
        "new_diagnostic_input_sha256": new_diagnostic_input_sha256,
        "old_frontier_id": old_frontier_id,
        "new_frontier_id": new_frontier_id,
        "summary": summary,
    }


def _bind_side(
    *,
    label: str,
    binding: dict[str, Any],
    comparison: dict[str, Any],
    prefix: str,
) -> None:
    expected = {
        "diagnostic_report_id": comparison[
            f"{prefix}_diagnostic_report_id"
        ],
        "diagnostic_input_sha256": comparison[
            f"{prefix}_diagnostic_input_sha256"
        ],
        "frontier_id": comparison[f"{prefix}_frontier_id"],
    }
    for key, value in expected.items():
        if binding[key] != value:
            raise CrossVersionJavacCheckpointError(
                f"{label}: binding does not match comparator {key}"
            )


def build_cross_version_javac_checkpoint(
    comparison_report: dict[str, Any],
    old_binding_report: dict[str, Any],
    new_binding_report: dict[str, Any],
    *,
    binary_backtest_id: str | None = None,
) -> dict[str, Any]:
    comparison = _validate_comparison(comparison_report)
    old_binding = _validate_binding(
        old_binding_report,
        label="old",
    )
    new_binding = _validate_binding(
        new_binding_report,
        label="new",
    )

    if old_binding["tooling_commit"] != new_binding["tooling_commit"]:
        raise CrossVersionJavacCheckpointError(
            "old/new recovery tooling commits differ"
        )
    _bind_side(
        label="old",
        binding=old_binding,
        comparison=comparison,
        prefix="old",
    )
    _bind_side(
        label="new",
        binding=new_binding,
        comparison=comparison,
        prefix="new",
    )

    if binary_backtest_id is not None:
        _require_string(
            binary_backtest_id,
            label="binary_backtest_id",
            pattern=_BINARY_BACKTEST_ID_RE,
        )

    def public_build(binding: dict[str, Any]) -> dict[str, Any]:
        return {
            "build_id": binding["build_id"],
            "source_authority_sha256": (
                binding["source_authority_sha256"]
            ),
            "binding_id": binding["binding_id"],
            "diagnostic_report_id": binding["diagnostic_report_id"],
            "diagnostic_input_sha256": (
                binding["diagnostic_input_sha256"]
            ),
            "frontier_id": binding["frontier_id"],
            "rebuild_id": binding["rebuild_id"],
            "workspace_id": binding["workspace_id"],
            "source_tree_sha256": binding["source_tree_sha256"],
            "clean_rebuild_status": binding["clean_rebuild_status"],
            "clean_project_build": binding["clean_project_build"],
            "project_binary_fallback_count": 0,
        }

    material = {
        "tooling_commit": old_binding["tooling_commit"],
        "binary_backtest_id": binary_backtest_id,
        "old": public_build(old_binding),
        "new": public_build(new_binding),
        "comparison": {
            "report_id": comparison["report_id"],
            "summary": comparison["summary"],
        },
    }
    checkpoint_id = (
        "XJAVACCHECKPOINT_" + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "cross_version_javac_checkpoint",
        "checkpoint_id": checkpoint_id,
        **material,
        "identifiers_included": False,
        "note": (
            "Public-safe checkpoint derived only from a redacted "
            "cross-version javac report and two redacted verified build "
            "bindings. It records compiler-frontier evidence only and "
            "does not declare either recovery release ready."
        ),
    }


def write_cross_version_javac_checkpoint(
    report: dict[str, Any],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
