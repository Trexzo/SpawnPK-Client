from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .build_authority import (
    BuildAuthorityError,
    build_build_authority,
    write_build_authority,
)
from .clean_rebuild import CleanRebuildError, clean_project_rebuild
from .readable_build import ReadableBuildError, build_readable_client
from .release_manifest import (
    RecoveryReleaseError,
    build_recovery_release_manifest,
    write_recovery_release_manifest,
)
from .roundtrip_verify import (
    RoundTripVerificationError,
    verify_clean_round_trip,
    write_roundtrip_report,
)
from .source_readiness import (
    SourceReadinessError,
    audit_source_workspace,
    write_source_readiness_report,
)
from .source_workspace import (
    SourceWorkspaceError,
    build_source_workspace,
)


class ExistingAuthorityReleaseError(ValueError):
    pass


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _write_json(doc: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _report(
    *,
    build_id: str,
    status: str,
    ready_for_release: bool,
    stage: str,
    blocker: dict[str, Any] | None,
    stage_ids: dict[str, Any],
    artifacts: dict[str, Any],
    release_id: str | None,
) -> dict[str, Any]:
    material = {
        "build_id": build_id,
        "status": status,
        "ready_for_release": ready_for_release,
        "stage": stage,
        "blocker": blocker,
        "stage_ids": stage_ids,
        "release_id": release_id,
    }
    return {
        "schema_version": 1,
        "kind": "existing_authority_release_report",
        "run_id": "RELEASE_RUN_" + _digest(material)[:20].upper(),
        "build_id": build_id,
        "status": status,
        "ready_for_release": ready_for_release,
        "terminal_stage": stage,
        "blocker": blocker,
        "release_id": release_id,
        "stage_ids": stage_ids,
        "artifacts": artifacts,
        "note": (
            "Blocked is a valid fail-closed outcome. The orchestrator never "
            "accepts semantic names, bypasses safety review, or weakens R5 "
            "round-trip acceptance."
        ),
    }


def build_existing_authority_release(
    source_jar: Path,
    source_index: dict[str, Any],
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    decompiler_jar: Path,
    *,
    expected_decompiler_sha256: str,
    engine: str,
    build_id: str,
    out_dir: Path,
    target_package: str = "recovered/spawnpk/client",
    source_safe_fallback: bool = False,
    fallback_name_prefix: str = "Recovered_",
    member_safety_acceptance: dict[str, Any] | None = None,
    allow_package_resource_risk: bool = False,
    rewrite_class_name_strings: bool = False,
    source_prefixes: list[str] | None = None,
    project_source_only: bool = False,
    official_first_restored: bool = False,
    official_overlay_manifest_path: Path | None = None,
    official_overlay_source_root: Path | None = None,
    private_dependency_replacement_plan_path: Path | None = None,
    private_dependency_reverse_plan_path: Path | None = None,
    official_artifacts: list[Path] | None = None,
    java_command: str = "java",
    javac_command: str = "javac",
) -> dict[str, Any]:
    """Compose the verified R4/R5 path for one already-promoted exact build."""
    if official_first_restored and not project_source_only:
        raise ExistingAuthorityReleaseError(
            "official-first restored release requires project_source_only"
        )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ExistingAuthorityReleaseError(
            "release output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    readable_dir = out_dir / "readable"
    source_dir = out_dir / "source"
    rebuild_dir = out_dir / "rebuild"

    stage_ids: dict[str, Any] = {}
    artifacts = {
        "readable": "readable/",
        "source": "source/",
        "rebuild": "rebuild/",
        "release_manifest": "recovery-release.json",
        "run_report": "release-run.json",
    }

    try:
        readable = build_readable_client(
            source_jar,
            class_lineage,
            member_lineage,
            source_index,
            build_id=build_id,
            out_dir=readable_dir,
            target_package=target_package,
            source_safe_fallback=source_safe_fallback,
            fallback_name_prefix=fallback_name_prefix,
            member_safety_acceptance=member_safety_acceptance,
            allow_package_resource_risk=allow_package_resource_risk,
            rewrite_class_name_strings=rewrite_class_name_strings,
        )
    except ReadableBuildError as exc:
        raise ExistingAuthorityReleaseError(str(exc)) from exc

    stage_ids["readable_manifest_id"] = readable.get("manifest_id")
    if readable.get("status") != "complete":
        report = _report(
            build_id=build_id,
            status="blocked",
            ready_for_release=False,
            stage="readable_build",
            blocker=readable.get("blocker")
            or {"reason": "readable_build_not_complete"},
            stage_ids=stage_ids,
            artifacts=artifacts,
            release_id=None,
        )
        _write_json(report, out_dir / "release-run.json")
        return report

    readable_jar = readable_dir / "readable-client.jar"

    try:
        recovered = build_source_workspace(
            readable,
            readable_jar,
            decompiler_jar,
            expected_decompiler_sha256=expected_decompiler_sha256,
            engine=engine,
            out_dir=source_dir,
            project_only=project_source_only,
        )
    except SourceWorkspaceError as exc:
        raise ExistingAuthorityReleaseError(str(exc)) from exc

    stage_ids["recovered_workspace_id"] = recovered.get("workspace_id")
    recovered_source_root = source_dir / "src"

    try:
        readiness = audit_source_workspace(
            recovered,
            recovered_source_root,
        )
    except SourceReadinessError as exc:
        raise ExistingAuthorityReleaseError(str(exc)) from exc
    write_source_readiness_report(
        readiness,
        source_dir / "source-readiness.json",
    )
    stage_ids["source_readiness_id"] = readiness.get("audit_id")

    try:
        build_authority = build_build_authority(
            source_jar,
            source_index,
            source_readiness=readiness,
            java_command=java_command,
            javac_command=javac_command,
        )
    except BuildAuthorityError as exc:
        raise ExistingAuthorityReleaseError(str(exc)) from exc
    write_build_authority(
        build_authority,
        source_dir / "build-authority.json",
    )
    stage_ids["build_authority_id"] = build_authority.get(
        "authority_id"
    )

    try:
        clean = clean_project_rebuild(
            recovered,
            readiness,
            readable,
            readable_jar,
            build_authority,
            recovered_source_root,
            out_dir=rebuild_dir,
            javac_command=javac_command,
            source_prefixes=source_prefixes,
            official_first_restored=official_first_restored,
            official_overlay_manifest_path=(
                official_overlay_manifest_path
            ),
            official_overlay_source_root=(
                official_overlay_source_root
            ),
            private_dependency_replacement_plan_path=(
                private_dependency_replacement_plan_path
            ),
            private_dependency_reverse_plan_path=(
                private_dependency_reverse_plan_path
            ),
            official_artifacts=official_artifacts,
            java_command=java_command,
        )
    except CleanRebuildError as exc:
        raise ExistingAuthorityReleaseError(str(exc)) from exc

    stage_ids["clean_rebuild_id"] = clean.get("rebuild_id")
    compile_transport = clean.get("compile_transport")
    if (
        isinstance(compile_transport, dict)
        and compile_transport.get("mode") == "official_first_restored"
    ):
        stage_ids.update(
            {
                "official_compile_id": compile_transport.get(
                    "official_compile_id"
                ),
                "dependency_overlay_id": compile_transport.get(
                    "overlay_id"
                ),
                "dependency_replacement_plan_id": compile_transport.get(
                    "replacement_plan_id"
                ),
                "dependency_reverse_plan_id": compile_transport.get(
                    "reverse_plan_id"
                ),
                "dependency_reverse_application_id": (
                    compile_transport.get("reverse_application_id")
                ),
            }
        )
    if clean.get("status") != "complete":
        report = _report(
            build_id=build_id,
            status="blocked",
            ready_for_release=False,
            stage="clean_rebuild",
            blocker={
                "reason": "clean_rebuild_not_complete",
                "status": clean.get("status"),
                "diagnostic": clean.get("diagnostic"),
            },
            stage_ids=stage_ids,
            artifacts=artifacts,
            release_id=None,
        )
        _write_json(report, out_dir / "release-run.json")
        return report

    rebuilt_jar = rebuild_dir / "rebuilt-client.jar"
    try:
        roundtrip = verify_clean_round_trip(
            clean,
            readable_jar,
            rebuilt_jar,
        )
    except RoundTripVerificationError as exc:
        raise ExistingAuthorityReleaseError(str(exc)) from exc
    write_roundtrip_report(
        roundtrip,
        rebuild_dir / "roundtrip.json",
    )
    stage_ids["roundtrip_verification_id"] = roundtrip.get(
        "verification_id"
    )

    try:
        release = build_recovery_release_manifest(
            source_index,
            class_lineage,
            member_lineage,
            readable,
            recovered,
            clean,
            roundtrip,
        )
    except RecoveryReleaseError as exc:
        raise ExistingAuthorityReleaseError(str(exc)) from exc

    write_recovery_release_manifest(
        release,
        out_dir / "recovery-release.json",
    )
    stage_ids["release_id"] = release.get("release_id")

    report = _report(
        build_id=build_id,
        status=(
            "complete"
            if release.get("ready_for_release")
            else "blocked"
        ),
        ready_for_release=bool(
            release.get("ready_for_release")
        ),
        stage="release_manifest",
        blocker=(
            None
            if release.get("ready_for_release")
            else {
                "reason": "release_manifest_blocked",
                "blockers": release.get("blockers", []),
            }
        ),
        stage_ids=stage_ids,
        artifacts=artifacts,
        release_id=release.get("release_id"),
    )
    _write_json(report, out_dir / "release-run.json")
    return report


def build_existing_authority_release_from_workspace(
    source_jar: Path,
    source_index: dict[str, Any],
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    recovered_manifest: dict[str, Any],
    recovered_source_root: Path,
    private_collision_plan_path: Path,
    *,
    build_id: str,
    out_dir: Path,
    target_package: str = "recovered/spawnpk/client",
    source_safe_fallback: bool = False,
    fallback_name_prefix: str = "Recovered_",
    member_safety_acceptance: dict[str, Any] | None = None,
    allow_package_resource_risk: bool = False,
    rewrite_class_name_strings: bool = False,
    source_prefixes: list[str] | None = None,
    java_command: str = "java",
    javac_command: str = "javac",
) -> dict[str, Any]:
    """Release from an existing collision-derived recovered source authority."""

    required_derivation = (
        "collision_transform_id",
        "collision_plan_id",
        "collision_report_id",
        "base_readable_jar_sha256",
    )
    missing = [
        key
        for key in required_derivation
        if not recovered_manifest.get(key)
    ]
    if missing:
        raise ExistingAuthorityReleaseError(
            "external recovered workspace is not complete collision-derived "
            "authority: missing " + ", ".join(sorted(missing))
        )

    recovered_source_root = recovered_source_root.resolve()
    if not recovered_source_root.is_dir():
        raise ExistingAuthorityReleaseError(
            "external recovered source root does not exist"
        )

    private_collision_plan_path = private_collision_plan_path.resolve()
    if not private_collision_plan_path.is_file():
        raise ExistingAuthorityReleaseError(
            "private collision plan path does not exist"
        )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ExistingAuthorityReleaseError(
            "release output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    readable_dir = out_dir / "readable"
    source_authority_dir = out_dir / "source-authority"
    rebuild_dir = out_dir / "rebuild"

    stage_ids: dict[str, Any] = {}
    artifacts = {
        "readable": "readable/",
        "source_authority": "source-authority/",
        "rebuild": "rebuild/",
        "release_manifest": "recovery-release.json",
        "run_report": "release-run.json",
    }

    try:
        readable = build_readable_client(
            source_jar,
            class_lineage,
            member_lineage,
            source_index,
            build_id=build_id,
            out_dir=readable_dir,
            target_package=target_package,
            source_safe_fallback=source_safe_fallback,
            fallback_name_prefix=fallback_name_prefix,
            member_safety_acceptance=member_safety_acceptance,
            allow_package_resource_risk=allow_package_resource_risk,
            rewrite_class_name_strings=rewrite_class_name_strings,
        )
    except ReadableBuildError as exc:
        raise ExistingAuthorityReleaseError(str(exc)) from exc

    stage_ids["readable_manifest_id"] = readable.get("manifest_id")
    if readable.get("status") != "complete":
        report = _report(
            build_id=build_id,
            status="blocked",
            ready_for_release=False,
            stage="readable_build",
            blocker=readable.get("blocker")
            or {"reason": "readable_build_not_complete"},
            stage_ids=stage_ids,
            artifacts=artifacts,
            release_id=None,
        )
        _write_json(report, out_dir / "release-run.json")
        return report

    readable_jar = readable_dir / "readable-client.jar"

    base_sha = recovered_manifest.get("base_readable_jar_sha256")
    readable_sha = readable.get("output_sha256")
    if base_sha != readable_sha:
        raise ExistingAuthorityReleaseError(
            "collision-derived workspace base readable SHA-256 disagrees "
            "with rebuilt readable authority"
        )

    source_authority_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        recovered_manifest,
        source_authority_dir / "recovered-manifest.json",
    )
    stage_ids["recovered_workspace_id"] = recovered_manifest.get(
        "workspace_id"
    )
    stage_ids["collision_transform_id"] = recovered_manifest.get(
        "collision_transform_id"
    )
    stage_ids["collision_plan_id"] = recovered_manifest.get(
        "collision_plan_id"
    )
    stage_ids["collision_report_id"] = recovered_manifest.get(
        "collision_report_id"
    )

    try:
        readiness = audit_source_workspace(
            recovered_manifest,
            recovered_source_root,
        )
    except SourceReadinessError as exc:
        raise ExistingAuthorityReleaseError(str(exc)) from exc
    write_source_readiness_report(
        readiness,
        source_authority_dir / "source-readiness.json",
    )
    stage_ids["source_readiness_id"] = readiness.get("audit_id")

    try:
        build_authority = build_build_authority(
            source_jar,
            source_index,
            source_readiness=readiness,
            java_command=java_command,
            javac_command=javac_command,
        )
    except BuildAuthorityError as exc:
        raise ExistingAuthorityReleaseError(str(exc)) from exc
    write_build_authority(
        build_authority,
        source_authority_dir / "build-authority.json",
    )
    stage_ids["build_authority_id"] = build_authority.get(
        "authority_id"
    )

    try:
        clean = clean_project_rebuild(
            recovered_manifest,
            readiness,
            readable,
            readable_jar,
            build_authority,
            recovered_source_root,
            out_dir=rebuild_dir,
            javac_command=javac_command,
            source_prefixes=source_prefixes,
            private_collision_plan_path=private_collision_plan_path,
        )
    except CleanRebuildError as exc:
        raise ExistingAuthorityReleaseError(str(exc)) from exc

    stage_ids["clean_rebuild_id"] = clean.get("rebuild_id")
    if clean.get("status") != "complete":
        report = _report(
            build_id=build_id,
            status="blocked",
            ready_for_release=False,
            stage="clean_rebuild",
            blocker={
                "reason": "clean_rebuild_not_complete",
                "status": clean.get("status"),
                "diagnostic": clean.get("diagnostic"),
            },
            stage_ids=stage_ids,
            artifacts=artifacts,
            release_id=None,
        )
        _write_json(report, out_dir / "release-run.json")
        return report

    rebuilt_jar = rebuild_dir / "rebuilt-client.jar"
    try:
        roundtrip = verify_clean_round_trip(
            clean,
            readable_jar,
            rebuilt_jar,
        )
    except RoundTripVerificationError as exc:
        raise ExistingAuthorityReleaseError(str(exc)) from exc
    write_roundtrip_report(
        roundtrip,
        rebuild_dir / "roundtrip.json",
    )
    stage_ids["roundtrip_verification_id"] = roundtrip.get(
        "verification_id"
    )

    try:
        release = build_recovery_release_manifest(
            source_index,
            class_lineage,
            member_lineage,
            readable,
            recovered_manifest,
            clean,
            roundtrip,
        )
    except RecoveryReleaseError as exc:
        raise ExistingAuthorityReleaseError(str(exc)) from exc

    write_recovery_release_manifest(
        release,
        out_dir / "recovery-release.json",
    )
    stage_ids["release_id"] = release.get("release_id")

    report = _report(
        build_id=build_id,
        status=(
            "complete"
            if release.get("ready_for_release")
            else "blocked"
        ),
        ready_for_release=bool(
            release.get("ready_for_release")
        ),
        stage="release_manifest",
        blocker=(
            None
            if release.get("ready_for_release")
            else {
                "reason": "release_manifest_blocked",
                "blockers": release.get("blockers", []),
            }
        ),
        stage_ids=stage_ids,
        artifacts=artifacts,
        release_id=release.get("release_id"),
    )
    _write_json(report, out_dir / "release-run.json")
    return report

