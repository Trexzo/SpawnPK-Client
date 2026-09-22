from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from .lineage import validate_lineage, write_lineage
from .member_lineage import validate_member_lineage, write_member_lineage
from .update_finalize import build_authority_candidate_report
from .update_intake import intake_new_jar, write_update_workspace
from .update_member_transfer import (
    transfer_member_identity_candidates,
)
from .update_transfer import transfer_trusted_class_lineage


class UpdateOrchestratorError(ValueError):
    pass


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _queue_key(item: dict[str, Any]) -> str:
    return json.dumps(
        item,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _merge_review_queue(
    intake_report: dict[str, Any],
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    *,
    new_build_id: str,
    member_candidates_supplied: bool,
) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []

    for item in intake_report.get("analysis_queue", []):
        if isinstance(item, dict):
            queue.append(
                {
                    "source": "update_intake",
                    **copy.deepcopy(item),
                }
            )

    for item in class_lineage.get("unresolved", []):
        if not isinstance(item, dict):
            continue
        if item.get("new_build_id") != new_build_id:
            continue
        queue.append(
            {
                "source": "class_lineage",
                "priority": (
                    "medium"
                    if item.get("kind") == "unmatched_old"
                    else "high"
                ),
                "kind": item.get("kind", "class_unresolved"),
                "detail": copy.deepcopy(item),
            }
        )

    for item in member_lineage.get("unresolved", []):
        if not isinstance(item, dict):
            continue
        if item.get("new_build_id") != new_build_id:
            continue
        queue.append(
            {
                "source": "member_lineage",
                "priority": (
                    "medium"
                    if item.get("kind") == "member_unmatched_old"
                    else "high"
                ),
                "kind": item.get("kind", "member_unresolved"),
                "detail": copy.deepcopy(item),
            }
        )

    if not member_candidates_supplied:
        queue.append(
            {
                "source": "orchestrator",
                "priority": "high",
                "kind": "member_identity_candidates_required",
                "reason": (
                    "No member-identity candidate report was supplied. "
                    "Class migration completed, but member lineage cannot "
                    "be transferred automatically without explicit matcher output."
                ),
            }
        )

    order = {"high": 0, "medium": 1, "low": 2}
    dedup: dict[str, dict[str, Any]] = {}
    for item in queue:
        dedup.setdefault(_queue_key(item), item)

    rows = list(dedup.values())
    rows.sort(
        key=lambda row: (
            order.get(str(row.get("priority")), 99),
            str(row.get("kind", "")),
            _queue_key(row),
        )
    )
    return rows


def migrate_update(
    old_index: dict[str, Any],
    new_jar: Path,
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
    new_build_number: int | None,
    out_dir: Path,
    scope_prefix: str = "rs/",
    member_candidates: dict[str, Any] | None = None,
    new_authority: str = "CROSS_BUILD",
) -> dict[str, Any]:
    """Run the safe automatic portion of a client-version migration.

    This never promotes unmatched classes/members and never accepts semantic names.
    The workspace is always deterministic for the same exact inputs.
    """
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    new_index, intake = intake_new_jar(
        old_index,
        new_jar,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
        scope_prefix=scope_prefix,
    )
    intake_paths = write_update_workspace(
        out_dir,
        new_index=new_index,
        report=intake,
    )

    migrated_classes, class_summary = transfer_trusted_class_lineage(
        class_lineage,
        old_index,
        new_index,
        intake,
        old_build_id=old_build_id,
        new_build_id=new_build_id,
        new_build_number=new_build_number,
        new_authority=new_authority,
    )

    if member_candidates is not None:
        migrated_members, member_summary = (
            transfer_member_identity_candidates(
                migrated_classes,
                member_lineage,
                old_index,
                new_index,
                member_candidates,
                old_build_id=old_build_id,
                new_build_id=new_build_id,
            )
        )
    else:
        migrated_members = copy.deepcopy(member_lineage)
        member_summary = {
            "applied_member_relationships": 0,
            "review_only_relationships": 0,
            "unresolved_added": 0,
            "status": "member_candidates_not_supplied",
        }

    class_path = out_dir / "class-lineage.json"
    member_path = out_dir / "member-lineage.json"
    class_summary_path = out_dir / "class-transfer-summary.json"
    member_summary_path = out_dir / "member-transfer-summary.json"
    authority_path = out_dir / "authority-candidate.json"
    queue_path = out_dir / "focused-analysis-queue.json"
    orchestration_path = out_dir / "migration-workspace.json"

    write_lineage(migrated_classes, class_path)
    write_member_lineage(migrated_members, member_path)
    _dump(class_summary_path, class_summary)
    _dump(member_summary_path, member_summary)

    authority = build_authority_candidate_report(
        migrated_classes,
        migrated_members,
        new_index,
        intake,
        build_id=new_build_id,
        scope_prefix=scope_prefix,
    )
    _dump(authority_path, authority)

    queue = _merge_review_queue(
        intake,
        migrated_classes,
        migrated_members,
        new_build_id=new_build_id,
        member_candidates_supplied=member_candidates is not None,
    )
    queue_doc = {
        "schema_version": 1,
        "kind": "focused_update_analysis_queue",
        "migration_id": intake["migration_id"],
        "old_sha256": intake["old_sha256"],
        "new_sha256": intake["new_sha256"],
        "items": queue,
    }
    _dump(queue_path, queue_doc)

    material = {
        "migration_id": intake["migration_id"],
        "old_sha256": intake["old_sha256"],
        "new_sha256": intake["new_sha256"],
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "class_transfer_summary": class_summary,
        "member_transfer_summary": member_summary,
        "authority_report_id": authority["report_id"],
        "ready_for_authority": authority["ready_for_authority"],
        "focused_analysis_items": len(queue),
    }
    workspace_id = (
        "MIGWORK_"
        + hashlib.sha256(_stable_json(material))
        .hexdigest()[:20]
        .upper()
    )

    result = {
        "schema_version": 1,
        "kind": "update_migration_workspace",
        "workspace_id": workspace_id,
        **material,
        "paths": {
            "new_index": intake_paths["index"],
            "intake_report": intake_paths["report"],
            "intake_queue": intake_paths["queue"],
            "class_lineage": str(class_path),
            "member_lineage": str(member_path),
            "class_transfer_summary": str(class_summary_path),
            "member_transfer_summary": str(member_summary_path),
            "authority_candidate": str(authority_path),
            "focused_analysis_queue": str(queue_path),
        },
    }
    _dump(orchestration_path, result)
    result["paths"]["workspace"] = str(orchestration_path)
    return result
