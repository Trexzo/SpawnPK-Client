from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


class CrossVersionBacktestError(ValueError):
    pass


_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _require_doc(doc: dict[str, Any], *, kind: str, label: str) -> None:
    if doc.get("schema_version") != 1 or doc.get("kind") != kind:
        raise CrossVersionBacktestError(
            f"{label}: expected schema_version=1 kind={kind!r}"
        )


def _require_sha(doc: dict[str, Any], key: str, *, label: str) -> str:
    value = str(doc.get(key) or "").lower()
    if _SHA256_RE.fullmatch(value) is None:
        raise CrossVersionBacktestError(
            f"{label}: missing or invalid {key}"
        )
    return value


def _require_build(doc: dict[str, Any], key: str, *, label: str) -> str:
    value = str(doc.get(key) or "")
    if not value:
        raise CrossVersionBacktestError(f"{label}: missing {key}")
    return value


def _add_check(
    checks: list[dict[str, Any]],
    *,
    name: str,
    expected: Any,
    actual: Any,
    required: bool = True,
) -> None:
    checks.append(
        {
            "name": name,
            "required": required,
            "passed": expected == actual,
            "expected": expected,
            "actual": actual,
        }
    )


def _expectations(
    checks: list[dict[str, Any]],
    intake: dict[str, Any],
    binary_delta: dict[str, Any] | None,
    expectations: dict[str, Any] | None,
) -> None:
    if expectations is None:
        return
    if not isinstance(expectations, dict):
        raise CrossVersionBacktestError("expectations must be an object")

    summary = intake.get("summary")
    if not isinstance(summary, dict):
        raise CrossVersionBacktestError(
            "update_intake: missing summary object"
        )

    summary_keys = {
        "old_scope_classes",
        "new_scope_classes",
        "matched_classes",
        "class_identity_reuse_percent",
        "changed_same_path_classes",
        "analysis_queue_items",
        "ambiguous_classes",
        "unmatched_old_classes",
        "unmatched_new_classes",
    }
    detail_keys = {
        "changed_same_path_class_paths",
        "classifications",
        "class_delta_summary",
        "binary_summary",
        "binary_report_id",
        "changed_entry_paths",
    }
    unknown = sorted(
        set(expectations) - summary_keys - detail_keys
    )
    if unknown:
        raise CrossVersionBacktestError(
            "unsupported expectation keys: " + ", ".join(unknown)
        )

    for key in sorted(set(expectations) & summary_keys):
        _add_check(
            checks,
            name=f"expectation.{key}",
            expected=expectations[key],
            actual=summary.get(key),
        )

    if "changed_same_path_class_paths" in expectations:
        expected_paths = expectations[
            "changed_same_path_class_paths"
        ]
        if not (
            isinstance(expected_paths, list)
            and all(isinstance(value, str) for value in expected_paths)
        ):
            raise CrossVersionBacktestError(
                "changed_same_path_class_paths must be a list of strings"
            )
        actual_paths = intake.get("changed_same_path_classes")
        if not isinstance(actual_paths, list):
            actual_paths = []
        _add_check(
            checks,
            name="expectation.changed_same_path_class_paths",
            expected=sorted(expected_paths),
            actual=sorted(str(value) for value in actual_paths),
        )

    if "classifications" in expectations:
        expected_classifications = expectations["classifications"]
        if not isinstance(expected_classifications, dict):
            raise CrossVersionBacktestError(
                "classifications expectation must be an object"
            )
        actual_classifications = intake.get("classifications")
        if not isinstance(actual_classifications, dict):
            actual_classifications = {}
        _add_check(
            checks,
            name="expectation.classifications",
            expected=expected_classifications,
            actual=actual_classifications,
        )

    if "class_delta_summary" in expectations:
        expected_delta = expectations["class_delta_summary"]
        if not isinstance(expected_delta, dict):
            raise CrossVersionBacktestError(
                "class_delta_summary expectation must be an object"
            )
        class_delta = intake.get("class_delta_report")
        actual_delta = (
            class_delta.get("summary", {})
            if isinstance(class_delta, dict)
            else {}
        )
        _add_check(
            checks,
            name="expectation.class_delta_summary",
            expected=expected_delta,
            actual=actual_delta,
        )

    if (
        "binary_summary" in expectations
        or "binary_report_id" in expectations
        or "changed_entry_paths" in expectations
    ):
        if binary_delta is None:
            raise CrossVersionBacktestError(
                "binary expectations require binary_delta"
            )

    if "binary_report_id" in expectations:
        expected_binary_id = expectations["binary_report_id"]
        if not isinstance(expected_binary_id, str):
            raise CrossVersionBacktestError(
                "binary_report_id expectation must be a string"
            )
        _add_check(
            checks,
            name="expectation.binary_report_id",
            expected=expected_binary_id,
            actual=binary_delta.get("report_id"),
        )

    if "binary_summary" in expectations:
        expected_binary = expectations["binary_summary"]
        if not isinstance(expected_binary, dict):
            raise CrossVersionBacktestError(
                "binary_summary expectation must be an object"
            )
        actual_binary = binary_delta.get("summary")
        if not isinstance(actual_binary, dict):
            actual_binary = {}
        _add_check(
            checks,
            name="expectation.binary_summary",
            expected=expected_binary,
            actual=actual_binary,
        )

    if "changed_entry_paths" in expectations:
        expected_entries = expectations["changed_entry_paths"]
        if not (
            isinstance(expected_entries, list)
            and all(isinstance(value, str) for value in expected_entries)
        ):
            raise CrossVersionBacktestError(
                "changed_entry_paths must be a list of strings"
            )
        changed = binary_delta.get("changed")
        if not isinstance(changed, list):
            changed = []
        actual_entries = sorted(
            str(row.get("path"))
            for row in changed
            if isinstance(row, dict) and isinstance(row.get("path"), str)
        )
        _add_check(
            checks,
            name="expectation.changed_entry_paths",
            expected=sorted(expected_entries),
            actual=actual_entries,
        )


def build_cross_version_backtest(
    old_release: dict[str, Any],
    new_release: dict[str, Any],
    update_intake: dict[str, Any],
    semantic_carryforward: dict[str, Any],
    *,
    source_name_carryforward: dict[str, Any] | None = None,
    binary_delta: dict[str, Any] | None = None,
    expectations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify that recovery/readable authority remains coherent across builds.

    The inputs are already-produced authority artifacts. This verifier does not
    recover or mutate source; it proves that two independently releasable source
    states are linked by the same exact update and carry-forward authority pair.
    """
    _require_doc(
        old_release,
        kind="recovery_release_manifest",
        label="old_release",
    )
    _require_doc(
        new_release,
        kind="recovery_release_manifest",
        label="new_release",
    )
    _require_doc(
        update_intake,
        kind="update_intake_report",
        label="update_intake",
    )
    _require_doc(
        semantic_carryforward,
        kind="semantic_carryforward_report",
        label="semantic_carryforward",
    )
    if source_name_carryforward is not None:
        _require_doc(
            source_name_carryforward,
            kind="source_name_carryforward_report",
            label="source_name_carryforward",
        )
    if binary_delta is not None:
        _require_doc(
            binary_delta,
            kind="cross_version_binary_delta",
            label="binary_delta",
        )

    old_build = _require_build(
        old_release, "build_id", label="old_release"
    )
    new_build = _require_build(
        new_release, "build_id", label="new_release"
    )
    if old_build == new_build:
        raise CrossVersionBacktestError(
            "old and new release build IDs must differ"
        )

    old_sha = _require_sha(
        old_release, "authority_sha256", label="old_release"
    )
    new_sha = _require_sha(
        new_release, "authority_sha256", label="new_release"
    )
    old_source_tree_sha = _require_sha(
        old_release,
        "final_source_tree_sha256",
        label="old_release",
    )
    new_source_tree_sha = _require_sha(
        new_release,
        "final_source_tree_sha256",
        label="new_release",
    )
    old_release_id = _require_build(
        old_release, "release_id", label="old_release"
    )
    new_release_id = _require_build(
        new_release, "release_id", label="new_release"
    )
    migration_id = _require_build(
        update_intake, "migration_id", label="update_intake"
    )
    semantic_carryforward_id = _require_build(
        semantic_carryforward,
        "report_id",
        label="semantic_carryforward",
    )
    source_name_carryforward_id = None
    if source_name_carryforward is not None:
        source_name_carryforward_id = _require_build(
            source_name_carryforward,
            "report_id",
            label="source_name_carryforward",
        )
    binary_delta_id = None
    if binary_delta is not None:
        binary_delta_id = _require_build(
            binary_delta,
            "report_id",
            label="binary_delta",
        )
    if old_sha == new_sha:
        raise CrossVersionBacktestError(
            "old and new release authorities must differ"
        )

    checks: list[dict[str, Any]] = []

    _add_check(
        checks,
        name="old_release.ready_for_release",
        expected=True,
        actual=old_release.get("ready_for_release"),
    )
    _add_check(
        checks,
        name="new_release.ready_for_release",
        expected=True,
        actual=new_release.get("ready_for_release"),
    )

    for prefix, doc, build_key, sha_key in (
        ("intake.old", update_intake, "old_build_id", "old_sha256"),
        ("semantic.old", semantic_carryforward, "old_build_id", "old_sha256"),
    ):
        _add_check(
            checks,
            name=f"{prefix}.build_id",
            expected=old_build,
            actual=doc.get(build_key),
        )
        _add_check(
            checks,
            name=f"{prefix}.sha256",
            expected=old_sha,
            actual=str(doc.get(sha_key) or "").lower(),
        )

    for prefix, doc, build_key, sha_key in (
        ("intake.new", update_intake, "new_build_id", "new_sha256"),
        ("semantic.new", semantic_carryforward, "new_build_id", "new_sha256"),
    ):
        _add_check(
            checks,
            name=f"{prefix}.build_id",
            expected=new_build,
            actual=doc.get(build_key),
        )
        _add_check(
            checks,
            name=f"{prefix}.sha256",
            expected=new_sha,
            actual=str(doc.get(sha_key) or "").lower(),
        )

    if binary_delta is not None:
        for prefix, expected, key in (
            ("binary.old_build_id", old_build, "old_build_id"),
            ("binary.new_build_id", new_build, "new_build_id"),
            ("binary.old_sha256", old_sha, "old_sha256"),
            ("binary.new_sha256", new_sha, "new_sha256"),
        ):
            actual = binary_delta.get(key)
            if key.endswith("sha256"):
                actual = str(actual or "").lower()
            _add_check(
                checks,
                name=prefix,
                expected=expected,
                actual=actual,
            )

    _add_check(
        checks,
        name="semantic.ready_for_readable_build",
        expected=True,
        actual=semantic_carryforward.get(
            "ready_for_readable_build"
        ),
    )
    _add_check(
        checks,
        name="semantic.namespace_matches_new_release",
        expected=new_release.get("namespace_id"),
        actual=semantic_carryforward.get("namespace_id"),
    )

    if source_name_carryforward is not None:
        for prefix, expected, key in (
            ("source_names.old_build_id", old_build, "old_build_id"),
            ("source_names.new_build_id", new_build, "new_build_id"),
            (
                "source_names.old_sha256",
                old_sha,
                "old_source_authority_sha256",
            ),
            (
                "source_names.new_sha256",
                new_sha,
                "new_source_authority_sha256",
            ),
        ):
            actual = source_name_carryforward.get(key)
            if key.endswith("sha256"):
                actual = str(actual or "").lower()
            _add_check(
                checks,
                name=prefix,
                expected=expected,
                actual=actual,
            )
        _add_check(
            checks,
            name="source_names.full_carryforward_ready",
            expected=True,
            actual=source_name_carryforward.get(
                "full_carryforward_ready"
            ),
        )

    _expectations(
        checks,
        update_intake,
        binary_delta,
        expectations,
    )

    failed = [
        row for row in checks if row["required"] and not row["passed"]
    ]

    material = {
        "old_release_id": old_release_id,
        "new_release_id": new_release_id,
        "old_source_tree_sha256": old_source_tree_sha,
        "new_source_tree_sha256": new_source_tree_sha,
        "migration_id": migration_id,
        "semantic_carryforward_id": semantic_carryforward_id,
        "source_name_carryforward_id": source_name_carryforward_id,
        "binary_delta_id": binary_delta_id,
        "expectations": expectations or {},
        "checks": [
            (
                row["name"],
                row["required"],
                row["passed"],
                row["expected"],
                row["actual"],
            )
            for row in checks
        ],
    }
    backtest_id = (
        "XVER_"
        + hashlib.sha256(_stable_json(material))
        .hexdigest()[:20]
        .upper()
    )

    summary = update_intake.get("summary", {})
    return {
        "schema_version": 1,
        "kind": "cross_version_recovery_backtest",
        "backtest_id": backtest_id,
        "old_build_id": old_build,
        "new_build_id": new_build,
        "old_authority_sha256": old_sha,
        "new_authority_sha256": new_sha,
        "old_source_tree_sha256": old_source_tree_sha,
        "new_source_tree_sha256": new_source_tree_sha,
        "old_release_id": old_release_id,
        "new_release_id": new_release_id,
        "migration_id": migration_id,
        "semantic_carryforward_id": semantic_carryforward_id,
        "source_name_carryforward_id": source_name_carryforward_id,
        "binary_delta_id": binary_delta_id,
        "binary_delta_required": binary_delta is not None,
        "source_name_carryforward_required": (
            source_name_carryforward is not None
        ),
        "passed": len(failed) == 0,
        "required_check_count": sum(
            1 for row in checks if row["required"]
        ),
        "failed_required_check_count": len(failed),
        "checks": checks,
        "migration_summary": {
            key: summary.get(key)
            for key in (
                "old_scope_classes",
                "new_scope_classes",
                "matched_classes",
                "class_identity_reuse_percent",
                "changed_same_path_classes",
                "analysis_queue_items",
                "ambiguous_classes",
                "unmatched_old_classes",
                "unmatched_new_classes",
            )
        },
        "note": (
            "PASS proves that independently release-ready recovered source "
            "authorities are linked by one exact update pair and one compatible "
            "semantic carry-forward result. It is a cross-version recovery "
            "consistency proof, not evidence that inferred names are original."
        ),
    }


def write_cross_version_backtest(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
