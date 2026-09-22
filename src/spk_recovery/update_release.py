from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .authority_snapshot import (
    AuthoritySnapshotError,
    promote_authority_snapshot,
    write_authority_snapshot,
)
from .release_orchestrator import (
    ExistingAuthorityReleaseError,
    build_existing_authority_release,
)
from .semantic_carryforward import (
    SemanticCarryForwardError,
    build_semantic_carryforward,
    write_json as write_semantic_json,
)
from .update_orchestrator import (
    UpdateOrchestratorError,
    migrate_update,
)


class UpdateReleaseError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise UpdateReleaseError(f"expected JSON object at {path}")
    return value


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _write(doc: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _report(
    *,
    old_build_id: str,
    new_build_id: str,
    status: str,
    terminal_stage: str,
    ready_for_release: bool,
    migration_workspace_id: str | None,
    new_authority_id: str | None,
    semantic_carryforward_id: str | None,
    release_run_id: str | None,
    release_id: str | None,
    blocker: dict[str, Any] | None,
) -> dict[str, Any]:
    material = {
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "status": status,
        "terminal_stage": terminal_stage,
        "ready_for_release": ready_for_release,
        "migration_workspace_id": migration_workspace_id,
        "new_authority_id": new_authority_id,
        "semantic_carryforward_id": semantic_carryforward_id,
        "release_run_id": release_run_id,
        "release_id": release_id,
        "blocker": blocker,
    }
    return {
        "schema_version": 1,
        "kind": "update_to_release_report",
        "run_id": "UPDATE_RELEASE_" + _digest(material)[:20].upper(),
        **material,
        "note": (
            "This workflow never promotes unresolved migration state or accepts "
            "new semantic candidates. Blocked update/release states are valid "
            "fail-closed outputs."
        ),
    }


def migrate_update_to_release(
    old_index: dict[str, Any],
    old_authority: dict[str, Any],
    new_jar: Path,
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    decompiler_jar: Path,
    *,
    expected_decompiler_sha256: str,
    engine: str,
    old_build_id: str,
    new_build_id: str,
    new_build_number: int | None,
    out_dir: Path,
    member_candidates: dict[str, Any] | None = None,
    old_jar: Path | None = None,
    scope_prefix: str = "rs/",
    target_package: str = "recovered/spawnpk/client",
    source_safe_fallback: bool = False,
    fallback_name_prefix: str = "Recovered_",
    member_safety_acceptance: dict[str, Any] | None = None,
    allow_package_resource_risk: bool = False,
    rewrite_class_name_strings: bool = False,
    source_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise UpdateReleaseError(
            "update-to-release output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    migration_dir = out_dir / "migration"
    semantic_dir = out_dir / "semantic-carryforward"
    release_dir = out_dir / "release"

    try:
        migration = migrate_update(
            old_index,
            new_jar,
            class_lineage,
            member_lineage,
            old_build_id=old_build_id,
            new_build_id=new_build_id,
            new_build_number=new_build_number,
            out_dir=migration_dir,
            scope_prefix=scope_prefix,
            member_candidates=member_candidates,
            old_jar=old_jar,
        )
    except (UpdateOrchestratorError, ValueError) as exc:
        raise UpdateReleaseError(str(exc)) from exc

    migration_workspace_id = migration.get("workspace_id")
    if migration.get("ready_for_authority") is not True:
        report = _report(
            old_build_id=old_build_id,
            new_build_id=new_build_id,
            status="blocked",
            terminal_stage="migration",
            ready_for_release=False,
            migration_workspace_id=migration_workspace_id,
            new_authority_id=None,
            semantic_carryforward_id=None,
            release_run_id=None,
            release_id=None,
            blocker={
                "reason": "migration_not_authority_ready",
                "focused_analysis_items": migration.get(
                    "focused_analysis_items"
                ),
                "authority_report_id": migration.get(
                    "authority_report_id"
                ),
            },
        )
        _write(report, out_dir / "update-release.json")
        return report

    new_index = _load(migration_dir / "new-index.json")
    intake = _load(migration_dir / "migration-report.json")
    migrated_classes = _load(migration_dir / "class-lineage.json")
    migrated_members = _load(migration_dir / "member-lineage.json")
    authority_candidate = _load(
        migration_dir / "authority-candidate.json"
    )

    try:
        new_authority = promote_authority_snapshot(
            migrated_classes,
            migrated_members,
            new_index,
            intake,
            authority_candidate,
            build_id=new_build_id,
            scope_prefix=scope_prefix,
        )
    except AuthoritySnapshotError as exc:
        raise UpdateReleaseError(str(exc)) from exc

    write_authority_snapshot(
        new_authority,
        out_dir / "new-authority.json",
    )

    try:
        carry, namespace, class_plan, member_plan = (
            build_semantic_carryforward(
                old_authority,
                new_authority,
                migrated_classes,
                migrated_members,
                new_index,
                target_package=target_package,
            )
        )
    except SemanticCarryForwardError as exc:
        raise UpdateReleaseError(str(exc)) from exc

    write_semantic_json(
        carry,
        semantic_dir / "semantic-carryforward.json",
    )
    write_semantic_json(
        namespace,
        semantic_dir / "semantic-namespace.json",
    )
    write_semantic_json(
        class_plan,
        semantic_dir / "class-remap-plan.json",
    )
    write_semantic_json(
        member_plan,
        semantic_dir / "member-remap-plan.json",
    )

    if carry.get("ready_for_readable_build") is not True:
        report = _report(
            old_build_id=old_build_id,
            new_build_id=new_build_id,
            status="blocked",
            terminal_stage="semantic_carryforward",
            ready_for_release=False,
            migration_workspace_id=migration_workspace_id,
            new_authority_id=new_authority.get("authority_id"),
            semantic_carryforward_id=carry.get("report_id"),
            release_run_id=None,
            release_id=None,
            blocker={
                "reason": "accepted_semantic_identity_missing_in_new_build",
                "summary": carry.get("summary", {}),
            },
        )
        _write(report, out_dir / "update-release.json")
        return report

    try:
        release = build_existing_authority_release(
            new_jar,
            new_index,
            migrated_classes,
            migrated_members,
            decompiler_jar,
            expected_decompiler_sha256=expected_decompiler_sha256,
            engine=engine,
            build_id=new_build_id,
            out_dir=release_dir,
            target_package=target_package,
            source_safe_fallback=source_safe_fallback,
            fallback_name_prefix=fallback_name_prefix,
            member_safety_acceptance=member_safety_acceptance,
            allow_package_resource_risk=allow_package_resource_risk,
            rewrite_class_name_strings=rewrite_class_name_strings,
            source_prefixes=source_prefixes,
        )
    except ExistingAuthorityReleaseError as exc:
        raise UpdateReleaseError(str(exc)) from exc

    report = _report(
        old_build_id=old_build_id,
        new_build_id=new_build_id,
        status=(
            "complete"
            if release.get("ready_for_release")
            else "blocked"
        ),
        terminal_stage="release",
        ready_for_release=bool(
            release.get("ready_for_release")
        ),
        migration_workspace_id=migration_workspace_id,
        new_authority_id=new_authority.get("authority_id"),
        semantic_carryforward_id=carry.get("report_id"),
        release_run_id=release.get("run_id"),
        release_id=release.get("release_id"),
        blocker=release.get("blocker"),
    )
    _write(report, out_dir / "update-release.json")
    return report
