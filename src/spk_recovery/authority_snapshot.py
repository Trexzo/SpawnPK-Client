from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .lineage import validate_lineage
from .member_lineage import validate_member_lineage
from .update_finalize import (
    UpdateFinalizeError,
    build_authority_candidate_report,
)


class AuthoritySnapshotError(UpdateFinalizeError):
    pass


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_stable_json(value)).hexdigest()


def _canonical_build(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, Any]:
    hits = [
        row
        for row in class_lineage.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(hits) != 1:
        raise AuthoritySnapshotError(
            f"expected exactly one canonical build {build_id!r}, "
            f"found {len(hits)}"
        )
    return hits[0]


def promote_authority_snapshot(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    target_index: dict[str, Any],
    intake_report: dict[str, Any],
    candidate_report: dict[str, Any],
    *,
    build_id: str,
    scope_prefix: str | None = None,
) -> dict[str, Any]:
    """Promote a complete R3E candidate into an immutable authority manifest.

    The R3E report is independently recomputed before promotion. This prevents a
    stale or edited ready=true report from becoming authority.
    """
    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    recomputed = build_authority_candidate_report(
        class_lineage,
        member_lineage,
        target_index,
        intake_report,
        build_id=build_id,
        scope_prefix=scope_prefix,
    )
    if recomputed != candidate_report:
        raise AuthoritySnapshotError(
            "supplied authority-candidate report does not exactly match "
            "the recomputed R3E report"
        )
    if not recomputed.get("ready_for_authority"):
        raise AuthoritySnapshotError(
            "authority candidate is blocked; explicit review/promotion "
            "must complete before authority snapshot promotion"
        )

    build = _canonical_build(class_lineage, build_id)
    target_sha = str(target_index.get("sha256", "")).lower()
    if target_sha != str(build.get("sha256", "")).lower():
        raise AuthoritySnapshotError(
            "target index SHA-256 does not match canonical build"
        )

    effective_scope = (
        scope_prefix
        if scope_prefix is not None
        else recomputed.get("scope_prefix", "rs/")
    )
    previous_build_id = intake_report.get("old_build_id")
    previous_sha = intake_report.get("old_sha256")

    material = {
        "build_id": build_id,
        "build_number": build.get("build_number"),
        "source_name": build.get("source_name"),
        "sha256": target_sha,
        "scope_prefix": effective_scope,
        "migration_id": recomputed.get("migration_id"),
        "authority_candidate_report_id": recomputed["report_id"],
        "previous_build_id": previous_build_id,
        "previous_sha256": previous_sha,
        "class_lineage_sha256": _sha256_json(class_lineage),
        "member_lineage_sha256": _sha256_json(member_lineage),
        "summary": recomputed["summary"],
    }
    authority_id = (
        "AUTHORITY_"
        + hashlib.sha256(_stable_json(material))
        .hexdigest()[:20]
        .upper()
    )

    return {
        "schema_version": 1,
        "kind": "authority_snapshot",
        "authority_id": authority_id,
        "state": "EXACT_CURRENT_CLIENT",
        **material,
    }


def write_authority_snapshot(
    snapshot: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            snapshot,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
