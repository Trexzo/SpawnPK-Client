from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


class SourceMilestoneError(ValueError):
    pass


_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _require_equal(name: str, *values: Any) -> Any:
    if not values:
        raise SourceMilestoneError(f"{name} has no values")
    first = values[0]
    if any(value != first for value in values[1:]):
        raise SourceMilestoneError(
            f"{name} authority mismatch: {values!r}"
        )
    return first


def build_source_milestone_manifest(
    authority_index: dict[str, Any],
    readable_manifest: dict[str, Any],
    recovered_manifest: dict[str, Any],
    clean_rebuild_report: dict[str, Any],
    *,
    authority_commit: str,
    expected_build_id: str = "v308",
) -> dict[str, Any]:
    commit = authority_commit.strip().lower()
    if not _COMMIT_RE.fullmatch(commit):
        raise SourceMilestoneError(
            "authority commit must be an exact 40-hex Git commit"
        )

    authority_sha = str(authority_index.get("sha256") or "").lower()
    readable_source_sha = str(
        readable_manifest.get("source_sha256") or ""
    ).lower()
    recovered_source_sha = str(
        recovered_manifest.get("source_authority_sha256") or ""
    ).lower()
    clean_source_sha = str(
        clean_rebuild_report.get("source_authority_sha256") or ""
    ).lower()

    if len(authority_sha) != 64:
        raise SourceMilestoneError(
            "authority index lacks exact source SHA-256"
        )

    _require_equal(
        "exact source authority SHA-256",
        authority_sha,
        readable_source_sha,
        recovered_source_sha,
        clean_source_sha,
    )

    build_id = _require_equal(
        "build ID",
        str(readable_manifest.get("build_id") or ""),
        str(recovered_manifest.get("build_id") or ""),
        str(clean_rebuild_report.get("build_id") or ""),
    )
    if build_id != expected_build_id:
        raise SourceMilestoneError(
            f"source milestone requires {expected_build_id!r}, "
            f"got {build_id!r}"
        )

    namespace_id = _require_equal(
        "semantic namespace ID",
        readable_manifest.get("namespace_id"),
        recovered_manifest.get("namespace_id"),
        clean_rebuild_report.get("namespace_id"),
    )
    class_plan_digest = _require_equal(
        "class plan digest",
        readable_manifest.get("class_plan_digest"),
        recovered_manifest.get("class_plan_digest"),
    )
    member_plan_digest = _require_equal(
        "member plan digest",
        readable_manifest.get("member_plan_digest"),
        recovered_manifest.get("member_plan_digest"),
    )

    readable_sha = _require_equal(
        "readable JAR SHA-256",
        readable_manifest.get("output_sha256"),
        recovered_manifest.get("readable_jar_sha256"),
        clean_rebuild_report.get("readable_jar_sha256"),
    )

    source_tree_sha = _require_equal(
        "source tree SHA-256",
        recovered_manifest.get("source_tree_sha256"),
        clean_rebuild_report.get("source_tree_sha256"),
    )
    if (
        not isinstance(source_tree_sha, str)
        or len(source_tree_sha) != 64
    ):
        raise SourceMilestoneError(
            "source tree SHA-256 is incomplete"
        )

    project = clean_rebuild_report.get("project_classes")
    if not isinstance(project, dict):
        raise SourceMilestoneError(
            "clean rebuild lacks explicit project_classes evidence"
        )

    expected_count = project.get("expected_count")
    generated_count = project.get("generated_count")
    binary_fallback_count = project.get("binary_fallback_count")
    missing = project.get("missing")
    unexpected = project.get("unexpected")

    if not isinstance(expected_count, int) or expected_count <= 0:
        raise SourceMilestoneError(
            "project expected_count must be a positive integer"
        )
    if not isinstance(generated_count, int):
        raise SourceMilestoneError(
            "project generated_count must be an integer"
        )
    if not isinstance(binary_fallback_count, int):
        raise SourceMilestoneError(
            "project binary_fallback_count must be an integer"
        )
    if not isinstance(missing, list) or not isinstance(unexpected, list):
        raise SourceMilestoneError(
            "project class-set evidence must include missing/unexpected arrays"
        )

    blockers: list[dict[str, str]] = []

    if readable_manifest.get("status") != "complete":
        blockers.append(
            {"gate": "readable", "reason": "readable_not_complete"}
        )
    if readable_manifest.get("verification_pass") is not True:
        blockers.append(
            {
                "gate": "readable",
                "reason": "readable_verification_failed",
            }
        )

    if readable_manifest.get("source_safe_fallback") is not True:
        blockers.append(
            {
                "gate": "naming",
                "reason": "source_safe_fallback_not_enabled",
            }
        )

    fallback_prefix = readable_manifest.get("fallback_name_prefix")
    if not isinstance(fallback_prefix, str) or not fallback_prefix:
        blockers.append(
            {
                "gate": "naming",
                "reason": "fallback_name_prefix_missing",
            }
        )

    if recovered_manifest.get("source_scope") != "project_classes":
        blockers.append(
            {
                "gate": "source_scope",
                "reason": "workspace_not_project_only",
            }
        )

    if clean_rebuild_report.get("status") != "complete":
        blockers.append(
            {
                "gate": "compile",
                "reason": "clean_rebuild_not_complete",
            }
        )
    if clean_rebuild_report.get("clean_project_build") is not True:
        blockers.append(
            {
                "gate": "compile",
                "reason": "clean_project_build_false",
            }
        )
    if binary_fallback_count != 0:
        blockers.append(
            {
                "gate": "compile",
                "reason": "project_binary_fallback_present",
            }
        )

    if generated_count != expected_count:
        blockers.append(
            {
                "gate": "class_set",
                "reason": "generated_expected_count_mismatch",
            }
        )
    if missing:
        blockers.append(
            {
                "gate": "class_set",
                "reason": "missing_project_classes",
            }
        )
    if unexpected:
        blockers.append(
            {
                "gate": "class_set",
                "reason": "unexpected_project_classes",
            }
        )

    rebuilt = clean_rebuild_report.get("rebuilt_client")
    rebuilt_sha = (
        rebuilt.get("sha256")
        if isinstance(rebuilt, dict)
        else None
    )
    if not isinstance(rebuilt_sha, str) or len(rebuilt_sha) != 64:
        blockers.append(
            {
                "gate": "compile",
                "reason": "rebuilt_client_sha_missing",
            }
        )

    semantic_summary = readable_manifest.get("semantic_summary")
    if not isinstance(semantic_summary, dict):
        raise SourceMilestoneError(
            "readable manifest lacks semantic summary"
        )

    collision_derivation = {
        key: recovered_manifest.get(key)
        for key in (
            "collision_transform_id",
            "collision_plan_id",
            "collision_report_id",
            "base_readable_jar_sha256",
        )
        if recovered_manifest.get(key) is not None
    }

    provenance = {
        "spawnpk_client_authority_commit": commit,
        "exact_client_sha256": authority_sha,
        "readable_manifest_id": readable_manifest.get("manifest_id"),
        "readable_jar_sha256": readable_sha,
        "namespace_id": namespace_id,
        "class_plan_digest": class_plan_digest,
        "member_plan_digest": member_plan_digest,
        "workspace_id": recovered_manifest.get("workspace_id"),
        "source_tree_sha256": source_tree_sha,
        "build_authority_id": clean_rebuild_report.get(
            "build_authority_id"
        ),
        "clean_rebuild_id": clean_rebuild_report.get("rebuild_id"),
        "rebuilt_client_sha256": rebuilt_sha,
        "collision_derivation": collision_derivation or None,
    }

    gates = {
        "exact_authority": True,
        "semantic_intelligence_pinned": True,
        "deterministic_source_safe_fallback": (
            readable_manifest.get("source_safe_fallback") is True
            and isinstance(fallback_prefix, str)
            and bool(fallback_prefix)
        ),
        "clean_project_compile": (
            clean_rebuild_report.get("status") == "complete"
            and clean_rebuild_report.get("clean_project_build") is True
        ),
        "zero_project_binary_fallback": binary_fallback_count == 0,
        "exact_project_class_set": (
            generated_count == expected_count
            and not missing
            and not unexpected
        ),
        "source_tree_provenance": True,
        "authority_commit_pinned": True,
    }

    material = {
        "build_id": build_id,
        "authority_commit": commit,
        "authority_sha256": authority_sha,
        "namespace_id": namespace_id,
        "class_plan_digest": class_plan_digest,
        "member_plan_digest": member_plan_digest,
        "source_tree_sha256": source_tree_sha,
        "expected_project_class_count": expected_count,
        "generated_project_class_count": generated_count,
        "binary_fallback_count": binary_fallback_count,
        "provenance": provenance,
        "gates": gates,
        "blockers": blockers,
        "authority_pins": {
            "authority_index_sha256": _digest(authority_index),
            "readable_manifest_sha256": _digest(readable_manifest),
            "recovered_manifest_sha256": _digest(recovered_manifest),
            "clean_rebuild_report_sha256": _digest(
                clean_rebuild_report
            ),
        },
    }
    milestone_id = (
        "SOURCE_M1_" + _digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "spawnpk_source_milestone_manifest",
        "milestone": "Source Milestone 1",
        "milestone_id": milestone_id,
        "build_id": build_id,
        "publish_target": "Trexzo/SpawnPK-Client-Source",
        "publishable": len(blockers) == 0 and all(gates.values()),
        "blockers": blockers,
        "gates": gates,
        "naming_policy": {
            "semantic_names": "accepted_authority_only",
            "unresolved_names": "deterministic_source_safe_fallback_only",
            "invented_semantics_allowed": False,
            "source_safe_fallback": readable_manifest.get(
                "source_safe_fallback"
            ),
            "fallback_name_prefix": fallback_prefix,
        },
        "semantic_authority": {
            "namespace_id": namespace_id,
            "class_plan_digest": class_plan_digest,
            "member_plan_digest": member_plan_digest,
            "summary": semantic_summary,
        },
        "project_class_set": {
            "expected_count": expected_count,
            "generated_count": generated_count,
            "binary_fallback_count": binary_fallback_count,
            "missing_count": len(missing),
            "unexpected_count": len(unexpected),
        },
        "source": {
            "workspace_id": recovered_manifest.get("workspace_id"),
            "java_file_count": recovered_manifest.get(
                "java_file_count"
            ),
            "source_bytes": recovered_manifest.get("source_bytes"),
            "source_tree_sha256": source_tree_sha,
            "source_scope": recovered_manifest.get("source_scope"),
        },
        "provenance": provenance,
        "authority_pins": material["authority_pins"],
        "note": (
            "publishable is true only when exact v308 authority, accepted "
            "semantic naming, deterministic source-safe fallback naming, "
            "clean project compilation, zero project-binary fallback, exact "
            "project class-set equality, and source-tree provenance are all "
            "proven. No unresolved semantic names are invented."
        ),
    }


def write_source_milestone_manifest(
    manifest: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
