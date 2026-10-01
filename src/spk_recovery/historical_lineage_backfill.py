from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .indexer import index_jar
from .lineage import validate_lineage
from .matcher import match_classes
from .member_identity import build_member_identity_candidates
from .member_lineage import validate_member_lineage
from .update_orchestrator import migrate_update


class HistoricalLineageBackfillError(ValueError):
    pass


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _build(doc: dict[str, Any], build_id: str) -> dict[str, Any] | None:
    rows = [
        row
        for row in doc.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(rows) > 1:
        raise HistoricalLineageBackfillError(
            f"canonical class lineage contains duplicate build {build_id!r}"
        )
    return rows[0] if rows else None


def backfill_historical_v307_lineage(
    v308_client_jar: Path,
    v307_client_jar: Path,
    v308_index: dict[str, Any],
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    *,
    out_dir: Path,
) -> dict[str, Any]:
    """Derive canonical v307 relations from exact canonical v308 authority.

    The historical build is treated as the target of the existing R3 migration
    pipeline. No archived lineage input is mutated. The result is usable only
    when the ordinary authority-candidate gate reaches ready_for_authority=true.
    """
    v308_client_jar = v308_client_jar.resolve()
    v307_client_jar = v307_client_jar.resolve()
    out_dir = out_dir.resolve()

    for label, path in (
        ("v308_client_jar", v308_client_jar),
        ("v307_client_jar", v307_client_jar),
    ):
        if not path.is_file():
            raise HistoricalLineageBackfillError(
                f"{label} does not exist: {path}"
            )

    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    canonical_v308 = _build(class_lineage, "v308")
    if canonical_v308 is None:
        raise HistoricalLineageBackfillError(
            "canonical class lineage has no v308 authority"
        )
    if _build(class_lineage, "v307") is not None:
        raise HistoricalLineageBackfillError(
            "canonical class lineage already contains v307; "
            "historical backfill refuses to duplicate it"
        )

    v308_sha = _sha256_file(v308_client_jar)
    index_v308_sha = str(v308_index.get("sha256", "")).lower()
    canonical_v308_sha = str(canonical_v308.get("sha256", "")).lower()
    if v308_sha != index_v308_sha:
        raise HistoricalLineageBackfillError(
            "exact v308 JAR SHA does not match supplied v308 index"
        )
    if v308_sha != canonical_v308_sha:
        raise HistoricalLineageBackfillError(
            "exact v308 JAR SHA does not match canonical v308 build"
        )
    if int(
        v308_index.get("summary", {}).get(
            "class_parse_error_count",
            0,
        )
    ) != 0:
        raise HistoricalLineageBackfillError(
            "supplied v308 index contains class parse errors"
        )

    v307_index = index_jar(v307_client_jar)
    if int(
        v307_index.get("summary", {}).get(
            "class_parse_error_count",
            0,
        )
    ) != 0:
        raise HistoricalLineageBackfillError(
            "exact v307 index contains class parse errors"
        )

    class_match = match_classes(
        v308_index,
        v307_index,
        prefix="rs/",
    )
    member_candidates = build_member_identity_candidates(
        v308_index,
        v307_index,
        class_match,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = out_dir / "member-identity-candidates.json"
    candidate_path.write_text(
        json.dumps(
            member_candidates,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    migration_dir = out_dir / "migration"
    result = migrate_update(
        v308_index,
        v307_client_jar,
        class_lineage,
        member_lineage,
        old_build_id="v308",
        new_build_id="v307",
        new_build_number=307,
        out_dir=migration_dir,
        scope_prefix="rs/",
        member_candidates=member_candidates,
        old_jar=v308_client_jar,
        new_authority="EXACT_HISTORICAL_CLIENT",
    )

    authority_path = Path(
        result["paths"]["authority_candidate"]
    )
    authority = json.loads(
        authority_path.read_text(encoding="utf-8")
    )

    if str(authority.get("build_id")) != "v307":
        raise HistoricalLineageBackfillError(
            "migration authority candidate is not bound to v307"
        )
    if (
        str(authority.get("target_sha256", "")).lower()
        != str(v307_index.get("sha256", "")).lower()
    ):
        raise HistoricalLineageBackfillError(
            "migration authority candidate SHA is not exact v307"
        )

    material = {
        "v308_sha256": v308_sha,
        "v307_sha256": str(v307_index.get("sha256", "")).lower(),
        "workspace_id": result["workspace_id"],
        "authority_report_id": authority.get("report_id"),
        "ready_for_authority": bool(result["ready_for_authority"]),
        "class_transfer_summary": result["class_transfer_summary"],
        "member_transfer_summary": result["member_transfer_summary"],
        "field_proof_summary": result["field_proof_summary"],
        "focused_analysis_items": result["focused_analysis_items"],
    }
    backfill_id = (
        "HISTLINEAGE_"
        + hashlib.sha256(_stable_json(material))
        .hexdigest()[:20]
        .upper()
    )

    report = {
        "schema_version": 1,
        "kind": "historical_v307_lineage_backfill",
        "backfill_id": backfill_id,
        **material,
        "paths": {
            "member_identity_candidates": str(candidate_path),
            **result["paths"],
        },
        "blockers": authority.get("blockers", []),
        "missing_classes": authority.get("missing_classes", []),
        "missing_members": authority.get("missing_members", []),
        "blocking_class_unresolved": authority.get(
            "blocking_class_unresolved",
            [],
        ),
        "blocking_member_unresolved": authority.get(
            "blocking_member_unresolved",
            [],
        ),
        "note": (
            "Derived historical authority only. Archived class/member lineage "
            "inputs were not mutated. Result is consumable only when "
            "ready_for_authority=true."
        ),
    }

    report_path = out_dir / "historical-lineage-backfill.json"
    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    report["paths"]["report"] = str(report_path)
    return report
