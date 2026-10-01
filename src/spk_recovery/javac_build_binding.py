from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .cross_version_javac_frontier import (
    CrossVersionJavacFrontierError,
    _validate_report,
)


class JavacBuildBindingError(ValueError):
    pass


_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_REBUILD_ID_RE = re.compile(r"^CLEANBUILD_[0-9A-F]{20}$")


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_javac_build_binding(
    diagnostic_report: dict[str, Any],
    clean_rebuild_report: dict[str, Any],
    *,
    expected_build_id: str,
    expected_authority_sha256: str,
) -> dict[str, Any]:
    try:
        _validate_report(diagnostic_report, "diagnostic")
    except CrossVersionJavacFrontierError as exc:
        raise JavacBuildBindingError(str(exc)) from exc

    if (
        clean_rebuild_report.get("schema_version") != 1
        or clean_rebuild_report.get("kind")
        != "clean_project_rebuild_report"
    ):
        raise JavacBuildBindingError(
            "clean rebuild report has unsupported schema/kind"
        )

    if not expected_build_id:
        raise JavacBuildBindingError(
            "expected build ID must be non-empty"
        )
    if (
        not isinstance(expected_authority_sha256, str)
        or _HEX64_RE.fullmatch(expected_authority_sha256) is None
    ):
        raise JavacBuildBindingError(
            "expected authority SHA-256 must be lowercase 64-hex"
        )
    expected_sha = expected_authority_sha256

    build_id = clean_rebuild_report.get("build_id")
    if build_id != expected_build_id:
        raise JavacBuildBindingError(
            "clean rebuild build ID mismatch: "
            f"{build_id!r} != {expected_build_id!r}"
        )

    authority_sha = str(
        clean_rebuild_report.get("source_authority_sha256") or ""
    ).lower()
    if authority_sha != expected_sha:
        raise JavacBuildBindingError(
            "clean rebuild source authority SHA-256 mismatch"
        )

    rebuild_id = clean_rebuild_report.get("rebuild_id")
    if (
        not isinstance(rebuild_id, str)
        or _REBUILD_ID_RE.fullmatch(rebuild_id) is None
    ):
        raise JavacBuildBindingError(
            "clean rebuild report lacks exact rebuild identity"
        )

    workspace_id = clean_rebuild_report.get("workspace_id")
    if not isinstance(workspace_id, str) or not workspace_id:
        raise JavacBuildBindingError(
            "clean rebuild report lacks workspace identity"
        )

    source_tree_sha = str(
        clean_rebuild_report.get("source_tree_sha256") or ""
    ).lower()
    if _HEX64_RE.fullmatch(source_tree_sha) is None:
        raise JavacBuildBindingError(
            "clean rebuild report lacks source-tree SHA-256"
        )

    project_classes = clean_rebuild_report.get("project_classes")
    if not isinstance(project_classes, dict):
        raise JavacBuildBindingError(
            "clean rebuild report lacks project class summary"
        )
    fallback_count = project_classes.get("binary_fallback_count")
    if (
        isinstance(fallback_count, bool)
        or not isinstance(fallback_count, int)
        or fallback_count != 0
    ):
        raise JavacBuildBindingError(
            "clean rebuild contains project binary fallback"
        )

    compiler = clean_rebuild_report.get("compiler")
    if not isinstance(compiler, dict):
        raise JavacBuildBindingError(
            "clean rebuild report lacks compiler authority"
        )
    classification = compiler.get("diagnostic_classification")
    if not isinstance(classification, dict):
        raise JavacBuildBindingError(
            "clean rebuild report lacks diagnostic classification"
        )
    if classification.get("identifiers_included") is not False:
        raise JavacBuildBindingError(
            "clean rebuild diagnostic authority must be public/redacted"
        )

    diagnostic_summary = diagnostic_report.get("summary")
    if not isinstance(diagnostic_summary, dict):
        raise JavacBuildBindingError(
            "private diagnostic report lacks aggregate summary"
        )

    expected_pairs = {
        "report_id": diagnostic_report["report_id"],
        "frontier_id": diagnostic_report["frontier_id"],
        "input_sha256": diagnostic_report["input_sha256"],
        "summary": diagnostic_summary,
    }
    for key, expected in expected_pairs.items():
        if classification.get(key) != expected:
            raise JavacBuildBindingError(
                "clean rebuild diagnostic authority mismatch: "
                + key
            )

    status = clean_rebuild_report.get("status")
    if status not in {
        "complete",
        "compile_failed",
        "class_set_mismatch",
    }:
        raise JavacBuildBindingError(
            "clean rebuild report has invalid status"
        )
    clean_project_build = clean_rebuild_report.get(
        "clean_project_build"
    )
    if not isinstance(clean_project_build, bool):
        raise JavacBuildBindingError(
            "clean rebuild clean_project_build must be boolean"
        )

    material = {
        "build_id": build_id,
        "source_authority_sha256": authority_sha,
        "rebuild_id": rebuild_id,
        "workspace_id": workspace_id,
        "source_tree_sha256": source_tree_sha,
        "diagnostic_report_id": diagnostic_report["report_id"],
        "diagnostic_input_sha256": diagnostic_report["input_sha256"],
        "frontier_id": diagnostic_report["frontier_id"],
        "project_binary_fallback_count": fallback_count,
        "clean_rebuild_status": status,
        "clean_project_build": clean_project_build,
    }
    return {
        "schema_version": 1,
        "kind": "javac_build_binding",
        "binding_id": (
            "JAVACBIND_" + _stable_digest(material)[:20].upper()
        ),
        **material,
        "identifiers_included": False,
        "note": (
            "Binds one private javac diagnostic authority to the exact "
            "clean-rebuild build/source authority that produced it. "
            "No raw source paths, symbols, locations or messages are emitted."
        ),
    }


def write_javac_build_binding(
    report: dict[str, Any],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
