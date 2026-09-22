from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .lineage import validate_lineage
from .member_lineage import validate_member_lineage


class RecoveryReleaseError(ValueError):
    pass


def _digest(value: Any) -> str:
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
        raise RecoveryReleaseError(
            f"{label}: expected schema_version=1 kind={kind!r}"
        )


def _eq(label: str, *values: Any) -> Any:
    normalized = [str(v).lower() if isinstance(v, str) else v for v in values]
    first = normalized[0]
    if any(value != first for value in normalized[1:]):
        raise RecoveryReleaseError(
            f"{label}: authority linkage mismatch: {values!r}"
        )
    return values[0]


def build_recovery_release_manifest(
    authority_index: dict[str, Any],
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    readable_manifest: dict[str, Any],
    recovered_source_manifest: dict[str, Any],
    clean_rebuild_report: dict[str, Any],
    roundtrip_report: dict[str, Any],
    *,
    source_rewrite_acceptance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    if not isinstance(authority_index.get("sha256"), str):
        raise RecoveryReleaseError("authority_index: missing sha256")

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
        roundtrip_report,
        kind="round_trip_verification_report",
        label="roundtrip_report",
    )
    if source_rewrite_acceptance is not None:
        _require_doc(
            source_rewrite_acceptance,
            kind="source_rewrite_acceptance_report",
            label="source_rewrite_acceptance",
        )

    authority_sha = str(authority_index["sha256"]).lower()
    build_id = str(readable_manifest.get("build_id") or "")
    namespace_id = str(readable_manifest.get("namespace_id") or "")
    readable_sha = str(readable_manifest.get("output_sha256") or "").lower()
    workspace_id = str(recovered_source_manifest.get("workspace_id") or "")

    if not build_id or not namespace_id or not readable_sha or not workspace_id:
        raise RecoveryReleaseError(
            "readable/recovered manifests lack required authority identifiers"
        )

    _eq(
        "exact client authority SHA",
        authority_sha,
        readable_manifest.get("source_sha256"),
        recovered_source_manifest.get("source_authority_sha256"),
        clean_rebuild_report.get("source_authority_sha256"),
        roundtrip_report.get("source_authority_sha256"),
    )
    _eq(
        "build ID",
        build_id,
        recovered_source_manifest.get("build_id"),
        clean_rebuild_report.get("build_id"),
        roundtrip_report.get("build_id"),
    )
    _eq(
        "semantic namespace ID",
        namespace_id,
        recovered_source_manifest.get("namespace_id"),
        clean_rebuild_report.get("namespace_id"),
        roundtrip_report.get("namespace_id"),
    )
    _eq(
        "readable JAR SHA",
        readable_sha,
        recovered_source_manifest.get("readable_jar_sha256"),
        clean_rebuild_report.get("readable_jar_sha256"),
        roundtrip_report.get("readable_jar_sha256"),
    )
    _eq(
        "recovered source workspace",
        workspace_id,
        clean_rebuild_report.get("workspace_id"),
        roundtrip_report.get("workspace_id"),
    )

    build_hits = [
        row
        for row in class_lineage.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(build_hits) != 1:
        raise RecoveryReleaseError(
            f"class lineage must contain exactly one build {build_id!r}"
        )
    _eq(
        "class lineage build SHA",
        authority_sha,
        build_hits[0].get("sha256"),
    )

    if (
        str(member_lineage.get("baseline_build_id")) == build_id
        and str(member_lineage.get("source_sha256", "")).lower()
        != authority_sha
    ):
        raise RecoveryReleaseError(
            "member lineage baseline SHA does not match exact authority"
        )

    blockers: list[dict[str, str]] = []

    if readable_manifest.get("status") != "complete":
        blockers.append(
            {
                "stage": "readable_build",
                "reason": "readable_build_not_complete",
            }
        )
    if readable_manifest.get("verification_pass") is not True:
        blockers.append(
            {
                "stage": "readable_build",
                "reason": "readable_build_verification_failed",
            }
        )
    if clean_rebuild_report.get("status") != "complete":
        blockers.append(
            {
                "stage": "clean_rebuild",
                "reason": "clean_rebuild_not_complete",
            }
        )
    if clean_rebuild_report.get("clean_project_build") is not True:
        blockers.append(
            {
                "stage": "clean_rebuild",
                "reason": "project_binary_fallback_or_unclean_build",
            }
        )

    candidate = roundtrip_report.get("rebuild_authority_candidate")
    if not isinstance(candidate, dict):
        raise RecoveryReleaseError(
            "roundtrip report lacks rebuild_authority_candidate"
        )
    if candidate.get("ready") is not True:
        blockers.append(
            {
                "stage": "roundtrip",
                "reason": "roundtrip_not_authority_ready",
            }
        )
    if candidate.get("project_binary_fallback_count") not in (0, None):
        blockers.append(
            {
                "stage": "roundtrip",
                "reason": "project_binary_fallback_present",
            }
        )
    if int(candidate.get("semantic_surface_blockers", 0)) != 0:
        blockers.append(
            {
                "stage": "roundtrip",
                "reason": "semantic_surface_blockers_present",
            }
        )

    final_source_tree_sha = str(
        recovered_source_manifest.get("source_tree_sha256") or ""
    ).lower()
    final_workspace_id = workspace_id
    source_state = "recovered"

    if source_rewrite_acceptance is not None:
        _eq(
            "rewritten source build ID",
            build_id,
            source_rewrite_acceptance.get("build_id"),
        )
        _eq(
            "rewritten source authority SHA",
            authority_sha,
            source_rewrite_acceptance.get("source_authority_sha256"),
        )
        if source_rewrite_acceptance.get("parent_workspace_id") not in (
            None,
            workspace_id,
        ):
            raise RecoveryReleaseError(
                "source rewrite acceptance parent_workspace_id does not match recovered workspace"
            )
        if source_rewrite_acceptance.get("accepted") is not True:
            blockers.append(
                {
                    "stage": "source_rewrite",
                    "reason": "rewritten_source_not_accepted",
                }
            )
        final_source_tree_sha = str(
            source_rewrite_acceptance.get(
                "rewritten_source_tree_sha256"
            )
            or ""
        ).lower()
        final_workspace_id = str(
            source_rewrite_acceptance.get("workspace_id") or ""
        )
        source_state = "rewritten"

    if len(final_source_tree_sha) != 64 or len(final_workspace_id) == 0:
        raise RecoveryReleaseError(
            "final source authority identifiers are incomplete"
        )

    pins = {
        "authority_index_sha256": _digest(authority_index),
        "class_lineage_sha256": _digest(class_lineage),
        "member_lineage_sha256": _digest(member_lineage),
        "readable_manifest_sha256": _digest(readable_manifest),
        "recovered_source_manifest_sha256": _digest(
            recovered_source_manifest
        ),
        "clean_rebuild_report_sha256": _digest(clean_rebuild_report),
        "roundtrip_report_sha256": _digest(roundtrip_report),
        "source_rewrite_acceptance_sha256": (
            _digest(source_rewrite_acceptance)
            if source_rewrite_acceptance is not None
            else None
        ),
    }

    material = {
        "build_id": build_id,
        "authority_sha256": authority_sha,
        "namespace_id": namespace_id,
        "readable_jar_sha256": readable_sha,
        "final_workspace_id": final_workspace_id,
        "final_source_tree_sha256": final_source_tree_sha,
        "source_state": source_state,
        "pins": pins,
        "blockers": blockers,
    }
    release_id = "RECOVERY_" + _digest(material)[:20].upper()

    return {
        "schema_version": 1,
        "kind": "recovery_release_manifest",
        "release_id": release_id,
        "build_id": build_id,
        "authority_sha256": authority_sha,
        "namespace_id": namespace_id,
        "readable_jar_sha256": readable_sha,
        "recovered_workspace_id": workspace_id,
        "final_workspace_id": final_workspace_id,
        "final_source_tree_sha256": final_source_tree_sha,
        "source_state": source_state,
        "ready_for_release": len(blockers) == 0,
        "blockers": blockers,
        "authority_pins": pins,
        "stage_ids": {
            "readable_manifest_id": readable_manifest.get("manifest_id"),
            "recovered_workspace_id": recovered_source_manifest.get(
                "workspace_id"
            ),
            "clean_rebuild_id": clean_rebuild_report.get("rebuild_id"),
            "roundtrip_verification_id": roundtrip_report.get(
                "verification_id"
            ),
            "source_rewrite_acceptance_id": (
                source_rewrite_acceptance.get("acceptance_id")
                if source_rewrite_acceptance is not None
                else None
            ),
        },
        "note": (
            "Release readiness means the supplied authority chain is mutually "
            "consistent and all static acceptance gates passed. It does not "
            "claim inferred source names are original developer identifiers."
        ),
    }


def write_recovery_release_manifest(
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
