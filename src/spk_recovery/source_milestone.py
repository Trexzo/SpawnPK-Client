from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any

from .lineage import LineageValidationError, validate_lineage
from .member_lineage import validate_member_lineage
from .source_digest import (
    canonical_source_bytes,
    source_tree_digest,
)
from .v308_authority import V308_SOURCE_AUTHORITY_SHA256


class SourceMilestoneError(ValueError):
    pass


_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_DEFAULT_AUTHORITY_REPOSITORY = "Trexzo/SpawnPK-Client"
_DEFAULT_PUBLICATION_REPOSITORY = "Trexzo/SpawnPK-Client-Source"


def _exact_json_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise SourceMilestoneError(
                f"duplicate JSON key: {key!r}"
            )
        out[key] = value
    return out


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _require_doc(
    doc: dict[str, Any],
    *,
    kind: str,
    label: str,
) -> None:
    if doc.get("schema_version") != 1 or doc.get("kind") != kind:
        raise SourceMilestoneError(
            f"{label}: expected schema_version=1 kind={kind!r}"
        )


def _semantic_review_ids(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
) -> list[str]:
    review_ids: set[str] = set()

    for record in class_lineage.get("classes", []):
        if record.get("semantic_status") != "ACCEPTED":
            continue
        for row in record.get("semantic_provenance", []):
            review_id = row.get("review_id")
            if isinstance(review_id, str) and review_id:
                review_ids.add(review_id)

    for record in member_lineage.get("members", []):
        if record.get("semantic_status") != "ACCEPTED":
            continue
        for row in record.get("semantic_provenance", []):
            review_id = row.get("review_id")
            if isinstance(review_id, str) and review_id:
                review_ids.add(review_id)

    return sorted(review_ids)


def _block(
    blockers: list[dict[str, str]],
    *,
    gate: str,
    reason: str,
) -> None:
    blockers.append(
        {
            "gate": gate,
            "reason": reason,
        }
    )



def _release_authority_pin_provenance(
    release_manifest: dict[str, Any],
    *,
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    readable_manifest: dict[str, Any],
    recovered_source_manifest: dict[str, Any],
    clean_rebuild_report: dict[str, Any],
    blockers: list[dict[str, str]],
) -> dict[str, str] | None:
    pins = release_manifest.get("authority_pins")
    gate = "release_authority_pins"
    if not isinstance(pins, dict):
        _block(
            blockers,
            gate=gate,
            reason="release_authority_pins_missing",
        )
        return None

    documents = {
        "class_lineage_sha256": class_lineage,
        "member_lineage_sha256": member_lineage,
        "readable_manifest_sha256": readable_manifest,
        "recovered_source_manifest_sha256": recovered_source_manifest,
        "clean_rebuild_report_sha256": clean_rebuild_report,
    }
    linked: dict[str, str] = {}
    missing_or_invalid = False
    mismatch = False
    for key, document in documents.items():
        expected = pins.get(key)
        actual = _stable_digest(document)
        linked[key] = actual
        if (
            not isinstance(expected, str)
            or re.fullmatch(r"[0-9a-fA-F]{64}", expected) is None
        ):
            missing_or_invalid = True
            continue
        if expected.lower() != actual:
            mismatch = True

    if missing_or_invalid:
        _block(
            blockers,
            gate=gate,
            reason="release_authority_pins_incomplete",
        )
    if mismatch:
        _block(
            blockers,
            gate=gate,
            reason="release_authority_pin_mismatch",
        )
    return linked


def _release_verification_evidence(
    release_manifest: dict[str, Any],
    release_verification: dict[str, Any],
    clean_rebuild_report: dict[str, Any],
    blockers: list[dict[str, str]],
) -> dict[str, Any] | None:
    gate = "release_authority"
    checks = release_verification.get("checks")
    rows_valid = (
        isinstance(checks, list)
        and bool(checks)
        and all(
            isinstance(row, dict)
            and isinstance(row.get("name"), str)
            and bool(row.get("name"))
            and isinstance(row.get("required"), bool)
            and isinstance(row.get("passed"), bool)
            and "expected" in row
            and "actual" in row
            and row["passed"] == (row["expected"] == row["actual"])
            for row in checks
        )
    )
    if not rows_valid:
        _block(
            blockers,
            gate=gate,
            reason="release_verification_structure_invalid",
        )
        return None

    names = [str(row["name"]) for row in checks]
    if len(set(names)) != len(names):
        _block(
            blockers,
            gate=gate,
            reason="release_verification_structure_invalid",
        )

    required_rows = [
        row for row in checks if row["required"]
    ]
    failed_required = [
        row for row in required_rows if not row["passed"]
    ]
    required_count = release_verification.get(
        "required_check_count"
    )
    failed_count = release_verification.get(
        "failed_required_check_count"
    )
    count_shape_valid = (
        isinstance(required_count, int)
        and not isinstance(required_count, bool)
        and required_count > 0
        and required_count == len(required_rows)
        and isinstance(failed_count, int)
        and not isinstance(failed_count, bool)
        and failed_count == len(failed_required)
    )
    if not count_shape_valid:
        _block(
            blockers,
            gate=gate,
            reason="release_verification_structure_invalid",
        )
    if failed_required or failed_count != 0:
        _block(
            blockers,
            gate=gate,
            reason="release_verification_required_checks_failed",
        )

    release_ready = release_verification.get("release_ready")
    if (
        release_ready is not True
        or release_ready
        != release_manifest.get("ready_for_release")
    ):
        _block(
            blockers,
            gate=gate,
            reason="release_verification_release_ready_mismatch",
        )

    reproduction_rows = [
        row
        for row in checks
        if row["name"] == "release_manifest_exact_reproduction"
    ]
    reproduction_valid = (
        len(reproduction_rows) == 1
        and reproduction_rows[0]["required"] is True
        and reproduction_rows[0]["passed"] is True
        and reproduction_rows[0].get("expected") == release_manifest
        and reproduction_rows[0].get("actual") == release_manifest
    )
    if not reproduction_valid:
        _block(
            blockers,
            gate=gate,
            reason="release_verification_manifest_reproduction_invalid",
        )

    compile_transport = clean_rebuild_report.get(
        "compile_transport"
    )
    mode = (
        compile_transport.get("mode")
        if isinstance(compile_transport, dict)
        else None
    )
    required_names = {
        "release_manifest_exact_reproduction",
    }
    if mode == "collision_derived_remap":
        required_names.update(
            {
                "collision_private_plan_supplied",
                "collision_plan_id_authority",
                "collision_report_id_authority",
                "collision_transform_id_authority",
                "collision_base_readable_authority",
                "collision_private_plan_kind",
                "collision_private_plan_id",
                "collision_private_plan_report_id",
                "collision_private_plan_readable_sha256",
                "collision_private_plan_sha256",
                "collision_private_mapping_sha256",
            }
        )
        platform_bridges = compile_transport.get(
            "compile_only_platform_bridges",
            [],
        )
        if platform_bridges:
            required_names.update(
                {
                    "collision_platform_bridge_count",
                    "collision_platform_bridge_id",
                    "collision_platform_bridge_release",
                    "collision_platform_bridge_runtime_forbidden",
                    "collision_platform_bridge_transport_runtime_forbidden",
                    "collision_platform_bridge_v308_authority",
                    "collision_platform_bridge_source_authority",
                }
            )
    elif mode == "official_first_restored":
        required_names.update(
            {
                "official_overlay_manifest_supplied",
                "official_overlay_source_root_supplied",
                "official_private_replacement_plan_supplied",
                "official_private_reverse_plan_supplied",
                "official_artifacts_supplied",
                "official_overlay_id",
                "official_overlay_replacement_plan_id",
                "official_overlay_canonical_source_tree_sha256",
                "official_overlay_bundled_readable_sha256",
                "official_overlay_artifact_sha256",
                "official_overlay_source_tree_sha256",
                "official_private_replacement_identifiers",
                "official_private_replacement_plan_id",
                "official_private_replacement_bundled_readable_sha256",
                "official_private_replacement_artifact_sha256",
                "official_private_reverse_identifiers",
                "official_private_reverse_plan_id",
                "official_private_reverse_replacement_plan_id",
                "official_private_reverse_bundled_readable_sha256",
                "official_private_reverse_bytecode_restore_ready",
                "official_artifact_file_sha256",
            }
        )

    passed_required_names = {
        str(row["name"])
        for row in required_rows
        if row["passed"] is True
    }
    if not required_names.issubset(passed_required_names):
        _block(
            blockers,
            gate=gate,
            reason="release_verification_mode_evidence_incomplete",
        )

    material = {
        "release_id": release_manifest.get("release_id"),
        "checks": [
            (
                row["name"],
                row["required"],
                row["passed"],
                row.get("expected"),
                row.get("actual"),
            )
            for row in checks
        ],
    }
    expected_verification_id = (
        "REPRO_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )
    if release_verification.get(
        "verification_id"
    ) != expected_verification_id:
        _block(
            blockers,
            gate=gate,
            reason="release_verification_id_mismatch",
        )

    return {
        "verification_id": release_verification.get(
            "verification_id"
        ),
        "release_ready": release_ready,
        "required_check_count": required_count,
        "failed_required_check_count": failed_count,
        "exact_release_manifest_reproduction": reproduction_valid,
        "required_check_names": sorted(passed_required_names),
    }


def _official_first_dependency_provenance(
    compile_transport: dict[str, Any] | None,
    blockers: list[dict[str, str]],
) -> dict[str, Any] | None:
    if not isinstance(compile_transport, dict):
        return None
    if compile_transport.get("mode") != "official_first_restored":
        return None

    gate = "dependency_compile_transport"
    authority_prefixes = {
        "official_compile_id": "DEPOFFICIALCOMPILE_",
        "overlay_id": "DEPSRCOVERLAY_",
        "replacement_plan_id": "DEPREPLACE_",
        "reverse_plan_id": "DEPREVERSE_",
        "reverse_application_id": "DEPREVERSEAPPLY_",
    }
    if any(
        not isinstance(compile_transport.get(key), str)
        or not compile_transport[key].startswith(prefix)
        for key, prefix in authority_prefixes.items()
    ):
        _block(
            blockers,
            gate=gate,
            reason="official_first_transport_authority_incomplete",
        )

    hash_keys = (
        "compile_dependency_capsule_sha256",
        "generated_project_jar_sha256",
        "restored_project_jar_sha256",
    )
    if any(
        not isinstance(compile_transport.get(key), str)
        or re.fullmatch(
            r"[0-9a-fA-F]{64}",
            compile_transport[key],
        )
        is None
        for key in hash_keys
    ):
        _block(
            blockers,
            gate=gate,
            reason="official_first_transport_hash_authority_invalid",
        )

    official_shas = compile_transport.get(
        "official_artifact_sha256"
    )
    valid_official_shas = (
        isinstance(official_shas, list)
        and bool(official_shas)
        and all(
            isinstance(value, str)
            and re.fullmatch(r"[0-9a-fA-F]{64}", value)
            for value in official_shas
        )
    )
    if not valid_official_shas:
        _block(
            blockers,
            gate=gate,
            reason="official_first_artifact_authority_invalid",
        )

    capsule_count = compile_transport.get(
        "compile_dependency_capsule_class_count"
    )
    if not isinstance(capsule_count, int) or capsule_count <= 0:
        _block(
            blockers,
            gate=gate,
            reason="official_first_dependency_capsule_invalid",
        )

    required_values = {
        "opt_in": True,
        "status": "complete",
        "project_binary_fallback_count": 0,
        "runtime_official_dependencies_allowed": False,
        "runtime_dependency_source": (
            "original_verified_readable_non_project_bytes"
        ),
        "canonical_source_modified": False,
        "bundled_runtime_dependency_modified": False,
        "restored_project_bytecode_ready_for_runtime_assembly": True,
    }
    if any(
        compile_transport.get(key) != expected
        for key, expected in required_values.items()
    ):
        _block(
            blockers,
            gate=gate,
            reason="official_first_runtime_boundary_invalid",
        )

    return {
        key: compile_transport.get(key)
        for key in (
            "mode",
            "official_compile_id",
            "overlay_id",
            "replacement_plan_id",
            "reverse_plan_id",
            "reverse_application_id",
            "official_artifact_sha256",
            "compile_dependency_capsule_sha256",
            "compile_dependency_capsule_class_count",
            "generated_project_jar_sha256",
            "restored_project_jar_sha256",
            "project_binary_fallback_count",
            "runtime_official_dependencies_allowed",
            "runtime_dependency_source",
            "canonical_source_modified",
            "bundled_runtime_dependency_modified",
            "restored_project_bytecode_ready_for_runtime_assembly",
        )
    }


def _collision_derived_provenance(
    recovered_source_manifest: dict[str, Any],
    compile_transport: dict[str, Any] | None,
    blockers: list[dict[str, str]],
) -> dict[str, Any] | None:
    collision_keys = (
        "collision_transform_id",
        "collision_plan_id",
        "collision_report_id",
        "collision_mapping_sha256",
        "base_readable_jar_sha256",
    )
    recovered_collision = any(
        recovered_source_manifest.get(key) is not None
        for key in collision_keys
    )
    collision_transport = (
        isinstance(compile_transport, dict)
        and compile_transport.get("mode") == "collision_derived_remap"
    )
    gate = "collision_compile_transport"

    if recovered_collision != collision_transport:
        _block(
            blockers,
            gate=gate,
            reason="collision_source_rebuild_mode_mismatch",
        )
        return None
    if not collision_transport:
        return None

    missing = [
        key
        for key in collision_keys
        if not recovered_source_manifest.get(key)
    ]
    if missing:
        _block(
            blockers,
            gate=gate,
            reason="collision_source_authority_incomplete",
        )

    mapping_sha = str(
        recovered_source_manifest.get("collision_mapping_sha256") or ""
    ).lower()
    if (
        len(mapping_sha) != 64
        or any(ch not in "0123456789abcdef" for ch in mapping_sha)
    ):
        _block(
            blockers,
            gate=gate,
            reason="collision_mapping_commitment_invalid",
        )

    identity_keys = (
        "collision_transform_id",
        "collision_plan_id",
        "collision_report_id",
    )
    if any(
        recovered_source_manifest.get(key)
        != compile_transport.get(key)
        for key in identity_keys
    ):
        _block(
            blockers,
            gate=gate,
            reason="collision_stage_authority_mismatch",
        )

    return {
        key: value
        for key, value in {
            "mode": compile_transport.get("mode"),
            "collision_compile_id": compile_transport.get(
                "collision_compile_id"
            ),
            "collision_transform_id": compile_transport.get(
                "collision_transform_id"
            ),
            "collision_plan_id": compile_transport.get(
                "collision_plan_id"
            ),
            "collision_plan_sha256": compile_transport.get(
                "collision_plan_sha256"
            ),
            "collision_report_id": compile_transport.get(
                "collision_report_id"
            ),
            "collision_mapping_sha256": mapping_sha or None,
            "base_readable_jar_sha256": recovered_source_manifest.get(
                "base_readable_jar_sha256"
            ),
        }.items()
        if value is not None
    }


def build_source_milestone_manifest(
    *,
    authority_commit: str,
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    readable_manifest: dict[str, Any],
    recovered_source_manifest: dict[str, Any],
    clean_rebuild_report: dict[str, Any],
    release_manifest: dict[str, Any],
    release_verification: dict[str, Any],
    source_root: Path,
    authority_repository: str = _DEFAULT_AUTHORITY_REPOSITORY,
    publication_repository: str = _DEFAULT_PUBLICATION_REPOSITORY,
) -> dict[str, Any]:
    authority_commit = authority_commit.strip().lower()
    if not _COMMIT_RE.fullmatch(authority_commit):
        raise SourceMilestoneError(
            "authority commit must be one exact lowercase 40-hex Git commit"
        )

    if not authority_repository:
        raise SourceMilestoneError("authority repository is required")
    if not publication_repository:
        raise SourceMilestoneError("publication repository is required")

    try:
        validate_lineage(class_lineage)
        validate_member_lineage(
            member_lineage,
            class_lineage=class_lineage,
        )
    except LineageValidationError as exc:
        raise SourceMilestoneError(
            f"invalid semantic lineage authority: {exc}"
        ) from exc

    _require_doc(
        readable_manifest,
        kind="readable_client_build_manifest",
        label="readable_manifest",
    )
    _require_doc(
        recovered_source_manifest,
        kind="recovered_source_workspace_manifest",
        label="recovered_source_manifest",
    )
    _require_doc(
        clean_rebuild_report,
        kind="clean_project_rebuild_report",
        label="clean_rebuild_report",
    )
    _require_doc(
        release_manifest,
        kind="recovery_release_manifest",
        label="release_manifest",
    )
    _require_doc(
        release_verification,
        kind="recovery_release_verification",
        label="release_verification",
    )

    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise SourceMilestoneError(
            f"source root does not exist: {source_root}"
        )

    source_tree_sha, source_files, source_bytes = source_tree_digest(
        source_root
    )

    blockers: list[dict[str, str]] = []

    if not source_files:
        _block(
            blockers,
            gate="source_tree",
            reason="source_tree_empty",
        )

    build_id = str(
        release_manifest.get("build_id") or ""
    )
    if build_id != "v308":
        _block(
            blockers,
            gate="exact_authority",
            reason="source_milestone_requires_exact_v308",
        )

    authority_sha = str(
        release_manifest.get("authority_sha256") or ""
    ).lower()
    authority_values = {
        str(readable_manifest.get("source_sha256") or "").lower(),
        str(
            recovered_source_manifest.get(
                "source_authority_sha256"
            )
            or ""
        ).lower(),
        str(
            clean_rebuild_report.get("source_authority_sha256")
            or ""
        ).lower(),
        authority_sha,
    }
    if len(authority_values) != 1 or not authority_sha:
        _block(
            blockers,
            gate="exact_authority",
            reason="authority_sha_linkage_mismatch",
        )
    if authority_sha != V308_SOURCE_AUTHORITY_SHA256:
        _block(
            blockers,
            gate="exact_authority",
            reason="authority_sha_not_exact_v308",
        )

    class_baseline_build_id = str(
        class_lineage.get("baseline_build_id") or ""
    )
    class_builds = {
        str(row.get("build_id")): row
        for row in class_lineage.get("builds", [])
        if isinstance(row, dict)
    }
    class_v308 = class_builds.get("v308", {})
    class_v308_sha = str(
        class_v308.get("sha256") or ""
    ).lower()
    member_baseline_build_id = str(
        member_lineage.get("baseline_build_id") or ""
    )
    member_source_sha = str(
        member_lineage.get("source_sha256") or ""
    ).lower()
    class_lineage_namespace = str(
        class_lineage.get("namespace") or ""
    )
    member_class_namespace = str(
        member_lineage.get("class_namespace") or ""
    )

    if class_baseline_build_id != "v308":
        _block(
            blockers,
            gate="semantic_authority",
            reason="class_lineage_baseline_not_exact_v308",
        )
    if class_v308_sha != authority_sha:
        _block(
            blockers,
            gate="semantic_authority",
            reason="class_lineage_authority_sha_mismatch",
        )
    if member_baseline_build_id != "v308":
        _block(
            blockers,
            gate="semantic_authority",
            reason="member_lineage_baseline_not_exact_v308",
        )
    if member_source_sha != authority_sha:
        _block(
            blockers,
            gate="semantic_authority",
            reason="member_lineage_authority_sha_mismatch",
        )
    if member_class_namespace != class_lineage_namespace:
        _block(
            blockers,
            gate="semantic_authority",
            reason="member_class_namespace_mismatch",
        )

    semantic_lineage_authority = {
        "class_baseline_build_id": class_baseline_build_id,
        "class_v308_sha256": class_v308_sha,
        "member_baseline_build_id": member_baseline_build_id,
        "member_source_sha256": member_source_sha,
        "class_namespace": class_lineage_namespace,
        "member_class_namespace": member_class_namespace,
    }

    namespace_id = str(
        readable_manifest.get("namespace_id") or ""
    )
    if (
        not namespace_id
        or namespace_id
        != str(
            recovered_source_manifest.get("namespace_id") or ""
        )
        or namespace_id
        != str(clean_rebuild_report.get("namespace_id") or "")
        or namespace_id
        != str(release_manifest.get("namespace_id") or "")
    ):
        _block(
            blockers,
            gate="semantic_authority",
            reason="semantic_namespace_linkage_mismatch",
        )

    class_plan_digest = str(
        readable_manifest.get("class_plan_digest") or ""
    )
    member_plan_digest = str(
        readable_manifest.get("member_plan_digest") or ""
    )
    if (
        not class_plan_digest
        or class_plan_digest
        != str(
            recovered_source_manifest.get("class_plan_digest") or ""
        )
    ):
        _block(
            blockers,
            gate="semantic_authority",
            reason="class_plan_digest_mismatch",
        )
    if (
        not member_plan_digest
        or member_plan_digest
        != str(
            recovered_source_manifest.get("member_plan_digest") or ""
        )
    ):
        _block(
            blockers,
            gate="semantic_authority",
            reason="member_plan_digest_mismatch",
        )

    source_safe_fallback = (
        readable_manifest.get("source_safe_fallback") is True
    )
    fallback_prefix = readable_manifest.get(
        "fallback_name_prefix"
    )
    if not source_safe_fallback or not isinstance(
        fallback_prefix,
        str,
    ) or not fallback_prefix:
        _block(
            blockers,
            gate="fallback_policy",
            reason="deterministic_source_safe_fallback_not_enabled",
        )

    if release_manifest.get("ready_for_release") is not True:
        _block(
            blockers,
            gate="release_authority",
            reason="recovery_release_not_ready",
        )
    if release_verification.get("verified") is not True:
        _block(
            blockers,
            gate="release_authority",
            reason="recovery_release_verification_failed",
        )
    if release_verification.get("release_id") != release_manifest.get(
        "release_id"
    ):
        _block(
            blockers,
            gate="release_authority",
            reason="release_verification_id_linkage_mismatch",
        )

    release_verification_evidence = _release_verification_evidence(
        release_manifest,
        release_verification,
        clean_rebuild_report,
        blockers,
    )

    if source_tree_sha != str(
        release_manifest.get("final_source_tree_sha256") or ""
    ).lower():
        _block(
            blockers,
            gate="source_tree",
            reason="source_tree_sha256_mismatch",
        )

    if clean_rebuild_report.get("status") != "complete":
        _block(
            blockers,
            gate="clean_compile",
            reason="clean_rebuild_not_complete",
        )
    if clean_rebuild_report.get("clean_project_build") is not True:
        _block(
            blockers,
            gate="clean_compile",
            reason="project_build_not_clean",
        )

    project_classes = clean_rebuild_report.get(
        "project_classes"
    )
    if not isinstance(project_classes, dict):
        raise SourceMilestoneError(
            "clean rebuild lacks project_classes"
        )

    expected_count = int(
        project_classes.get("expected_count", -1)
    )
    generated_count = int(
        project_classes.get("generated_count", -1)
    )
    missing = list(project_classes.get("missing") or [])
    unexpected = list(project_classes.get("unexpected") or [])
    binary_fallback = int(
        project_classes.get("binary_fallback_count", -1)
    )

    class_set_equal = (
        expected_count >= 0
        and generated_count == expected_count
        and not missing
        and not unexpected
    )
    if not class_set_equal:
        _block(
            blockers,
            gate="project_class_set",
            reason="project_class_set_not_exact",
        )
    if binary_fallback != 0:
        _block(
            blockers,
            gate="project_binary_fallback",
            reason="project_binary_fallback_present",
        )

    release_authority_pins = _release_authority_pin_provenance(
        release_manifest,
        class_lineage=class_lineage,
        member_lineage=member_lineage,
        readable_manifest=readable_manifest,
        recovered_source_manifest=recovered_source_manifest,
        clean_rebuild_report=clean_rebuild_report,
        blockers=blockers,
    )

    review_ids = _semantic_review_ids(
        class_lineage,
        member_lineage,
    )

    compile_transport = clean_rebuild_report.get(
        "compile_transport"
    )
    collision_provenance = _collision_derived_provenance(
        recovered_source_manifest,
        compile_transport
        if isinstance(compile_transport, dict)
        else None,
        blockers,
    )

    dependency_transport_provenance = (
        _official_first_dependency_provenance(
            compile_transport
            if isinstance(compile_transport, dict)
            else None,
            blockers,
        )
    )

    provenance = {
        "authority_repository": authority_repository,
        "authority_commit": authority_commit,
        "authority_client_sha256": authority_sha,
        "build_id": build_id,
        "semantic_namespace_id": namespace_id,
        "class_plan_digest": class_plan_digest,
        "member_plan_digest": member_plan_digest,
        "semantic_review_ids": review_ids,
        "semantic_lineage_authority": semantic_lineage_authority,
        "fallback_policy": {
            "source_safe_fallback": source_safe_fallback,
            "fallback_name_prefix": fallback_prefix,
        },
        "readable_manifest_id": readable_manifest.get(
            "manifest_id"
        ),
        "recovered_workspace_id": recovered_source_manifest.get(
            "workspace_id"
        ),
        "build_authority_id": clean_rebuild_report.get(
            "build_authority_id"
        ),
        "clean_rebuild_id": clean_rebuild_report.get(
            "rebuild_id"
        ),
        "release_id": release_manifest.get("release_id"),
        "release_verification_id": release_verification.get(
            "verification_id"
        ),
        "release_verification_evidence": release_verification_evidence,
        "release_authority_pins": release_authority_pins,
        "collision_provenance": collision_provenance,
        "dependency_transport_provenance": (
            dependency_transport_provenance
        ),
    }

    source_tree = {
        "sha256": source_tree_sha,
        "java_file_count": len(source_files),
        "source_bytes": source_bytes,
        "layout": "src/",
    }

    class_set = {
        "expected_count": expected_count,
        "generated_count": generated_count,
        "missing_count": len(missing),
        "unexpected_count": len(unexpected),
        "binary_fallback_count": binary_fallback,
        "exact_match": class_set_equal,
    }

    publication = {
        "target_repository": publication_repository,
        "allowed": len(blockers) == 0,
        "layout": {
            "source": "src/",
            "provenance": "provenance/",
            "manifest": "SOURCE-MILESTONE.json",
        },
    }

    material = {
        "provenance": provenance,
        "source_tree": source_tree,
        "class_set": class_set,
        "publication": publication,
        "blockers": blockers,
    }
    milestone_id = (
        "SRCMILESTONE_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "source_milestone_manifest",
        "milestone_id": milestone_id,
        "milestone": "source-milestone-1",
        "publishable": len(blockers) == 0,
        "blockers": blockers,
        "provenance": provenance,
        "source_tree": source_tree,
        "class_set": class_set,
        "publication": publication,
        "note": (
            "publishable means the exact authority, semantic/fallback, "
            "clean-compile, zero-project-binary-fallback, exact class-set, "
            "source-tree, and release-verification gates all passed. "
            "Semantic names remain evidence-backed accepted recovery names; "
            "the manifest does not claim they are original developer names."
        ),
    }


def verify_source_milestone_manifest(
    manifest: dict[str, Any],
    **build_kwargs: Any,
) -> dict[str, Any]:
    _require_doc(
        manifest,
        kind="source_milestone_manifest",
        label="source_milestone_manifest",
    )
    recomputed = build_source_milestone_manifest(
        **build_kwargs
    )
    exact = manifest == recomputed

    material = {
        "milestone_id": manifest.get("milestone_id"),
        "exact_reproduction": exact,
        "source_tree_sha256": recomputed.get(
            "source_tree",
            {},
        ).get("sha256"),
    }
    verification_id = (
        "SRCMILEVERIFY_"
        + _stable_digest(material)[:20].upper()
    )
    return {
        "schema_version": 1,
        "kind": "source_milestone_verification",
        "verification_id": verification_id,
        "milestone_id": manifest.get("milestone_id"),
        "verified": exact,
        "publishable": bool(
            recomputed.get("publishable")
        ) and exact,
        "exact_reproduction": exact,
        "recomputed_milestone_id": recomputed.get(
            "milestone_id"
        ),
    }


def build_source_provenance_document(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    _require_doc(
        manifest,
        kind="source_milestone_manifest",
        label="source_milestone_manifest",
    )

    provenance = manifest.get("provenance")
    source_tree = manifest.get("source_tree")
    class_set = manifest.get("class_set")
    publication = manifest.get("publication")

    if not isinstance(provenance, dict):
        raise SourceMilestoneError(
            "milestone manifest lacks provenance"
        )
    if not isinstance(source_tree, dict):
        raise SourceMilestoneError(
            "milestone manifest lacks source_tree"
        )
    if not isinstance(class_set, dict):
        raise SourceMilestoneError(
            "milestone manifest lacks class_set"
        )
    if not isinstance(publication, dict):
        raise SourceMilestoneError(
            "milestone manifest lacks publication"
        )

    material = {
        "milestone_id": manifest.get("milestone_id"),
        "publishable": manifest.get("publishable"),
        "provenance": provenance,
        "source_tree": source_tree,
        "class_set": class_set,
        "publication_repository": publication.get(
            "target_repository"
        ),
    }

    return {
        "schema_version": 1,
        "kind": "source_milestone_provenance",
        "provenance_id": (
            "SRCPROV_"
            + _stable_digest(material)[:20].upper()
        ),
        "milestone_id": manifest.get("milestone_id"),
        "publishable": bool(manifest.get("publishable")),
        "authority": {
            "repository": provenance.get(
                "authority_repository"
            ),
            "commit": provenance.get("authority_commit"),
            "client_sha256": provenance.get(
                "authority_client_sha256"
            ),
            "build_id": provenance.get("build_id"),
        },
        "semantic_authority": {
            "namespace_id": provenance.get(
                "semantic_namespace_id"
            ),
            "class_plan_digest": provenance.get(
                "class_plan_digest"
            ),
            "member_plan_digest": provenance.get(
                "member_plan_digest"
            ),
            "review_ids": list(
                provenance.get(
                    "semantic_review_ids",
                    [],
                )
            ),
            "lineage_authority": provenance.get(
                "semantic_lineage_authority"
            ),
            "fallback_policy": provenance.get(
                "fallback_policy"
            ),
        },
        "recovery_authority": {
            "readable_manifest_id": provenance.get(
                "readable_manifest_id"
            ),
            "recovered_workspace_id": provenance.get(
                "recovered_workspace_id"
            ),
            "build_authority_id": provenance.get(
                "build_authority_id"
            ),
            "clean_rebuild_id": provenance.get(
                "clean_rebuild_id"
            ),
            "release_id": provenance.get(
                "release_id"
            ),
            "release_verification_id": provenance.get(
                "release_verification_id"
            ),
            "release_verification_evidence": provenance.get(
                "release_verification_evidence"
            ),
            "collision_provenance": provenance.get(
                "collision_provenance"
            ),
            "dependency_transport_provenance": provenance.get(
                "dependency_transport_provenance"
            ),
        },
        "source_authority": {
            "tree_sha256": source_tree.get("sha256"),
            "java_file_count": source_tree.get(
                "java_file_count"
            ),
            "source_bytes": source_tree.get(
                "source_bytes"
            ),
            "layout": source_tree.get("layout"),
        },
        "class_set": class_set,
        "publication_repository": publication.get(
            "target_repository"
        ),
        "semantic_name_statement": (
            "Accepted semantic names are evidence-backed recovery "
            "names. This document does not claim an inferred semantic "
            "identifier is the original developer name."
        ),
    }


def build_source_publication_bundle(
    manifest: dict[str, Any],
    source_root: Path,
    out_dir: Path,
    *,
    provenance_documents: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    _require_doc(
        manifest,
        kind="source_milestone_manifest",
        label="source_milestone_manifest",
    )
    if manifest.get("publishable") is not True:
        raise SourceMilestoneError(
            "source milestone is not publishable"
        )

    blockers = manifest.get("blockers")
    publication = manifest.get("publication")
    if (
        not isinstance(blockers, list)
        or blockers
        or not isinstance(publication, dict)
        or publication.get("allowed") is not True
    ):
        raise SourceMilestoneError(
            "source milestone publication state is inconsistent"
        )

    milestone_material = {
        "provenance": manifest.get("provenance"),
        "source_tree": manifest.get("source_tree"),
        "class_set": manifest.get("class_set"),
        "publication": publication,
        "blockers": blockers,
    }
    expected_milestone_id = (
        "SRCMILESTONE_"
        + _stable_digest(milestone_material)[:20].upper()
    )
    if manifest.get("milestone_id") != expected_milestone_id:
        raise SourceMilestoneError(
            "source milestone identity mismatch"
        )

    source_root = source_root.resolve()
    out_dir = out_dir.resolve()

    if not source_root.is_dir():
        raise SourceMilestoneError(
            "source root does not exist"
        )
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SourceMilestoneError(
            "publication bundle directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    tree_sha, files, source_bytes = source_tree_digest(
        source_root
    )
    expected_sha = manifest.get("source_tree", {}).get(
        "sha256"
    )
    if tree_sha != expected_sha:
        raise SourceMilestoneError(
            "source tree does not match milestone manifest"
        )

    source_out = out_dir / "src"
    for path in files:
        rel = path.relative_to(source_root)
        target = source_out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(
            canonical_source_bytes(path.read_bytes())
        )

    provenance_out = out_dir / "provenance"
    provenance_out.mkdir(parents=True, exist_ok=True)

    milestone_provenance = build_source_provenance_document(
        manifest
    )
    milestone_provenance_raw = (
        json.dumps(
            milestone_provenance,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (
        provenance_out / "SOURCE-PROVENANCE.json"
    ).write_bytes(
        milestone_provenance_raw.encode("utf-8")
    )

    (out_dir / "SOURCE-MILESTONE.json").write_bytes(
        (
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    )

    provenance_index: dict[str, str] = {
        "SOURCE-PROVENANCE.json": hashlib.sha256(
            milestone_provenance_raw.encode("utf-8")
        ).hexdigest(),
    }
    for name in sorted(provenance_documents):
        if name == "SOURCE-PROVENANCE.json":
            raise SourceMilestoneError(
                "SOURCE-PROVENANCE.json is generated from the "
                "milestone manifest and cannot be overridden"
            )
        if not re.fullmatch(r"[A-Za-z0-9_.-]+\.json", name):
            raise SourceMilestoneError(
                "invalid provenance document name"
            )
        doc = provenance_documents[name]
        target = provenance_out / name
        raw = (
            json.dumps(doc, indent=2, sort_keys=True)
            + "\n"
        )
        target.write_bytes(raw.encode("utf-8"))
        provenance_index[name] = hashlib.sha256(
            target.read_bytes()
        ).hexdigest()

    file_hashes: dict[str, str] = {}
    for path in sorted(
        out_dir.rglob("*"),
        key=lambda p: p.relative_to(out_dir).as_posix(),
    ):
        if not path.is_file():
            continue
        rel = path.relative_to(out_dir).as_posix()
        file_hashes[rel] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

    bundle_material = {
        "milestone_id": manifest.get("milestone_id"),
        "source_tree_sha256": tree_sha,
        "source_file_count": len(files),
        "source_bytes": source_bytes,
        "provenance_index": provenance_index,
        "files": file_hashes,
    }
    bundle_id = (
        "SRCBUNDLE_"
        + _stable_digest(bundle_material)[:20].upper()
    )

    bundle = {
        "schema_version": 1,
        "kind": "source_publication_bundle",
        "bundle_id": bundle_id,
        "milestone_id": manifest.get("milestone_id"),
        "source_tree_sha256": tree_sha,
        "source_file_count": len(files),
        "source_bytes": source_bytes,
        "provenance_documents": provenance_index,
        "file_sha256": file_hashes,
        "contains_binary_artifacts": False,
        "publication_repository": manifest.get(
            "publication",
            {},
        ).get("target_repository"),
    }
    (out_dir / "BUNDLE.json").write_bytes(
        (
            json.dumps(
                bundle,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    )
    return bundle


def verify_source_publication_bundle(
    bundle_dir: Path,
    *,
    expected_manifest: dict[str, Any] | None = None,
    expected_authority_commit: str | None = None,
    expected_authority_repository: str = (
        _DEFAULT_AUTHORITY_REPOSITORY
    ),
    expected_publication_repository: str = (
        _DEFAULT_PUBLICATION_REPOSITORY
    ),
) -> dict[str, Any]:
    bundle_dir = bundle_dir.resolve()
    if not bundle_dir.is_dir():
        raise SourceMilestoneError(
            "publication bundle directory does not exist"
        )

    bundle_path = bundle_dir / "BUNDLE.json"
    milestone_path = bundle_dir / "SOURCE-MILESTONE.json"
    provenance_dir = bundle_dir / "provenance"
    source_root = bundle_dir / "src"

    required = (
        bundle_path,
        milestone_path,
        provenance_dir / "SOURCE-PROVENANCE.json",
        source_root,
    )
    for path in required:
        if not path.exists():
            raise SourceMilestoneError(
                "publication bundle is missing required artifact: "
                + path.relative_to(bundle_dir).as_posix()
            )

    try:
        bundle = json.loads(
            bundle_path.read_text(encoding="utf-8"),
            object_pairs_hook=_exact_json_object,
        )
        milestone = json.loads(
            milestone_path.read_text(encoding="utf-8"),
            object_pairs_hook=_exact_json_object,
        )
        stored_provenance = json.loads(
            (
                provenance_dir / "SOURCE-PROVENANCE.json"
            ).read_text(encoding="utf-8"),
            object_pairs_hook=_exact_json_object,
        )
    except json.JSONDecodeError as exc:
        raise SourceMilestoneError(
            "publication bundle contains invalid JSON"
        ) from exc

    _require_doc(
        bundle,
        kind="source_publication_bundle",
        label="source_publication_bundle",
    )
    _require_doc(
        milestone,
        kind="source_milestone_manifest",
        label="source_milestone_manifest",
    )

    checks: dict[str, bool] = {}

    blockers = milestone.get("blockers")
    publication_raw = milestone.get("publication")
    publication = (
        publication_raw
        if isinstance(publication_raw, dict)
        else {}
    )
    provenance_raw = milestone.get("provenance")
    provenance = (
        provenance_raw
        if isinstance(provenance_raw, dict)
        else {}
    )
    milestone_material = {
        "provenance": milestone.get("provenance"),
        "source_tree": milestone.get("source_tree"),
        "class_set": milestone.get("class_set"),
        "publication": publication_raw,
        "blockers": blockers,
    }
    expected_milestone_id = (
        "SRCMILESTONE_"
        + _stable_digest(milestone_material)[:20].upper()
    )

    checks["external_manifest_match"] = (
        isinstance(expected_manifest, dict)
        and expected_manifest == milestone
    )
    checks["expected_authority_commit"] = (
        isinstance(expected_authority_commit, str)
        and _COMMIT_RE.fullmatch(expected_authority_commit)
        is not None
        and provenance.get("authority_commit")
        == expected_authority_commit
    )
    checks["expected_authority_repository"] = (
        provenance.get("authority_repository")
        == expected_authority_repository
    )
    checks["expected_publication_repository"] = (
        publication.get("target_repository")
        == expected_publication_repository
    )
    checks["milestone_publishable"] = (
        milestone.get("publishable") is True
    )
    checks["milestone_blockers_empty"] = (
        isinstance(blockers, list) and not blockers
    )
    checks["milestone_publication_allowed"] = (
        isinstance(publication_raw, dict)
        and publication_raw.get("allowed") is True
    )
    checks["milestone_identity_match"] = (
        milestone.get("milestone_id")
        == expected_milestone_id
    )
    checks["bundle_milestone_match"] = (
        bundle.get("milestone_id")
        == milestone.get("milestone_id")
    )
    checks["publication_repository_match"] = (
        bundle.get("publication_repository")
        == publication.get("target_repository")
    )
    checks["contains_binary_artifacts_false"] = (
        bundle.get("contains_binary_artifacts") is False
    )

    tree_sha, source_files, source_bytes = source_tree_digest(
        source_root
    )
    source_count = len(source_files)
    checks["source_tree_nonempty"] = source_count > 0
    checks["source_tree_sha256_match"] = (
        tree_sha
        == bundle.get("source_tree_sha256")
        == milestone.get("source_tree", {}).get("sha256")
    )
    checks["source_file_count_match"] = (
        source_count
        == bundle.get("source_file_count")
        == milestone.get("source_tree", {}).get(
            "java_file_count"
        )
    )
    checks["source_bytes_match"] = (
        source_bytes
        == bundle.get("source_bytes")
        == milestone.get("source_tree", {}).get(
            "source_bytes"
        )
    )

    source_only_layout = True
    actual_indexed_files: dict[str, str] = {}
    for path in sorted(
        bundle_dir.rglob("*"),
        key=lambda item: item.relative_to(bundle_dir).as_posix(),
    ):
        if not path.is_file():
            continue
        rel = path.relative_to(bundle_dir).as_posix()
        if rel == "BUNDLE.json":
            continue

        allowed = (
            rel == "SOURCE-MILESTONE.json"
            or (
                rel.startswith("src/")
                and rel.endswith(".java")
            )
            or (
                rel.startswith("provenance/")
                and rel.endswith(".json")
                and "/" not in rel[len("provenance/"):]
            )
        )
        if not allowed:
            source_only_layout = False

        actual_indexed_files[rel] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

    expected_file_hashes = bundle.get("file_sha256")
    if not isinstance(expected_file_hashes, dict):
        expected_file_hashes = {}

    checks["source_only_layout"] = source_only_layout
    checks["indexed_file_set_match"] = (
        set(actual_indexed_files)
        == set(expected_file_hashes)
    )
    checks["indexed_file_hashes_match"] = (
        actual_indexed_files == expected_file_hashes
    )

    expected_provenance_index = bundle.get(
        "provenance_documents"
    )
    if not isinstance(expected_provenance_index, dict):
        expected_provenance_index = {}

    actual_provenance_index: dict[str, str] = {}
    if provenance_dir.is_dir():
        for path in sorted(provenance_dir.iterdir()):
            if not path.is_file():
                source_only_layout = False
                continue
            if path.suffix != ".json":
                source_only_layout = False
                continue
            actual_provenance_index[path.name] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()

    checks["source_only_layout"] = source_only_layout
    checks["provenance_index_match"] = (
        actual_provenance_index
        == expected_provenance_index
    )

    recomputed_provenance = build_source_provenance_document(
        milestone
    )
    checks["generated_provenance_match"] = (
        stored_provenance == recomputed_provenance
    )

    bundle_material = {
        "milestone_id": milestone.get("milestone_id"),
        "source_tree_sha256": tree_sha,
        "source_file_count": source_count,
        "source_bytes": source_bytes,
        "provenance_index": actual_provenance_index,
        "files": actual_indexed_files,
    }
    expected_bundle_id = (
        "SRCBUNDLE_"
        + _stable_digest(bundle_material)[:20].upper()
    )
    checks["bundle_id_match"] = (
        bundle.get("bundle_id") == expected_bundle_id
    )

    verified = all(checks.values())

    material = {
        "bundle_id": bundle.get("bundle_id"),
        "milestone_id": milestone.get("milestone_id"),
        "checks": checks,
        "source_tree_sha256": tree_sha,
        "indexed_file_sha256": actual_indexed_files,
        "provenance_index": actual_provenance_index,
    }
    verification_id = (
        "SRCBUNDLEVERIFY_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "source_publication_bundle_verification",
        "verification_id": verification_id,
        "bundle_id": bundle.get("bundle_id"),
        "milestone_id": milestone.get("milestone_id"),
        "verified": verified,
        "checks": checks,
        "source_tree_sha256": tree_sha,
        "source_file_count": source_count,
        "source_bytes": source_bytes,
        "indexed_file_count": len(actual_indexed_files),
        "provenance_document_count": len(
            actual_provenance_index
        ),
    }


def write_json(doc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(
        (
            json.dumps(
                doc,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    )
