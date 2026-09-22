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
    member_safety_acceptance: dict[str, Any] | None = None,
    allow_package_resource_risk: bool = False,
    rewrite_class_name_strings: bool = False,
    source_prefixes: list[str] | None = None,
    java_command: str = "java",
    javac_command: str = "javac",
) -> dict[str, Any]:
    """Compose the verified R4/R5 path for one already-promoted exact build."""
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
