from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .indexer import index_jar
from .lineage import validate_lineage
from .matcher import match_classes
from .member_identity import build_member_identity_candidates
from .member_lineage import validate_member_lineage
from .update_orchestrator import migrate_update


class GenericHistoricalLineageBackfillError(ValueError):
    pass


_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


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


def _build(
    class_lineage: dict[str, Any],
    build_id: str,
) -> dict[str, Any] | None:
    rows = [
        row
        for row in class_lineage.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(rows) > 1:
        raise GenericHistoricalLineageBackfillError(
            f"canonical class lineage contains duplicate build {build_id!r}"
        )
    return rows[0] if rows else None


def _require_sha(value: str, label: str) -> str:
    value = str(value).lower()
    if _HEX64_RE.fullmatch(value) is None:
        raise GenericHistoricalLineageBackfillError(
            f"{label} must be lowercase 64-hex"
        )
    return value


def _verify_expected_match_summary(
    actual: dict[str, Any],
    expected: dict[str, Any] | None,
) -> None:
    if expected is None:
        return
    if not isinstance(expected, dict):
        raise GenericHistoricalLineageBackfillError(
            "expected matcher summary must be an object"
        )
    allowed = {
        "old_class_count",
        "new_class_count",
        "matched",
        "exact_sha256",
        "structural_unique",
        "package_anchor",
        "weighted_mutual_best",
        "ambiguous",
        "unmatched_old",
        "unmatched_new",
    }
    unknown = sorted(set(expected) - allowed)
    if unknown:
        raise GenericHistoricalLineageBackfillError(
            "unsupported matcher expectation fields: "
            + ", ".join(unknown)
        )
    for key, value in sorted(expected.items()):
        if actual.get(key) != value:
            raise GenericHistoricalLineageBackfillError(
                "historical matcher expectation mismatch: "
                f"{key}={actual.get(key)!r} != {value!r}"
            )


def backfill_historical_lineage(
    current_client_jar: Path,
    historical_client_jar: Path,
    current_index: dict[str, Any],
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    *,
    current_build_id: str,
    historical_build_id: str,
    historical_build_number: int | None,
    expected_current_sha256: str,
    expected_historical_sha256: str,
    out_dir: Path,
    scope_prefix: str = "rs/",
    expected_match_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Safely derive historical lineage through the ordinary R3 pipeline.

    Unlike the v307 fixture-specific backfill, this generic path never applies
    special historical field carry. Partial or ambiguous identity transfer is
    preserved as a deterministic blocked authority candidate.
    """
    if not current_build_id or not historical_build_id:
        raise GenericHistoricalLineageBackfillError(
            "build IDs must be non-empty"
        )
    if current_build_id == historical_build_id:
        raise GenericHistoricalLineageBackfillError(
            "current and historical build IDs must differ"
        )
    if not isinstance(scope_prefix, str):
        raise GenericHistoricalLineageBackfillError(
            "scope prefix must be a string"
        )

    expected_current_sha256 = _require_sha(
        expected_current_sha256,
        "expected current SHA-256",
    )
    expected_historical_sha256 = _require_sha(
        expected_historical_sha256,
        "expected historical SHA-256",
    )

    validate_lineage(class_lineage)
    validate_member_lineage(
        member_lineage,
        class_lineage=class_lineage,
    )

    current_build = _build(class_lineage, current_build_id)
    if current_build is None:
        raise GenericHistoricalLineageBackfillError(
            f"canonical lineage has no current build {current_build_id!r}"
        )
    if _build(class_lineage, historical_build_id) is not None:
        raise GenericHistoricalLineageBackfillError(
            f"canonical lineage already contains {historical_build_id!r}"
        )

    current_client_jar = current_client_jar.resolve()
    historical_client_jar = historical_client_jar.resolve()
    for label, path in (
        ("current client JAR", current_client_jar),
        ("historical client JAR", historical_client_jar),
    ):
        if not path.is_file():
            raise GenericHistoricalLineageBackfillError(
                f"{label} does not exist: {path}"
            )

    current_sha = _sha256_file(current_client_jar)
    historical_sha = _sha256_file(historical_client_jar)
    current_index_sha = str(current_index.get("sha256", "")).lower()
    canonical_current_sha = str(current_build.get("sha256", "")).lower()

    if current_sha != expected_current_sha256:
        raise GenericHistoricalLineageBackfillError(
            "current JAR SHA-256 does not match pinned authority"
        )
    if current_sha != current_index_sha:
        raise GenericHistoricalLineageBackfillError(
            "current JAR SHA-256 does not match supplied current index"
        )
    if current_sha != canonical_current_sha:
        raise GenericHistoricalLineageBackfillError(
            "current JAR SHA-256 does not match canonical current build"
        )
    if historical_sha != expected_historical_sha256:
        raise GenericHistoricalLineageBackfillError(
            "historical JAR SHA-256 does not match pinned authority"
        )
    if int(
        current_index.get("summary", {}).get(
            "class_parse_error_count",
            0,
        )
    ) != 0:
        raise GenericHistoricalLineageBackfillError(
            "supplied current index contains class parse errors"
        )

    historical_index = index_jar(historical_client_jar)
    if int(
        historical_index.get("summary", {}).get(
            "class_parse_error_count",
            0,
        )
    ) != 0:
        raise GenericHistoricalLineageBackfillError(
            "historical index contains class parse errors"
        )

    class_match = match_classes(
        current_index,
        historical_index,
        prefix=scope_prefix,
    )
    match_summary = copy.deepcopy(class_match["summary"])
    _verify_expected_match_summary(
        match_summary,
        expected_match_summary,
    )

    member_candidates = build_member_identity_candidates(
        current_index,
        historical_index,
        class_match,
    )

    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    match_path = out_dir / "class-match.json"
    member_candidates_path = out_dir / "member-identity-candidates.json"
    _dump(match_path, class_match)
    _dump(member_candidates_path, member_candidates)

    migration_dir = out_dir / "migration"
    migration = migrate_update(
        current_index,
        historical_client_jar,
        class_lineage,
        member_lineage,
        old_build_id=current_build_id,
        new_build_id=historical_build_id,
        new_build_number=historical_build_number,
        out_dir=migration_dir,
        scope_prefix=scope_prefix,
        member_candidates=member_candidates,
        old_jar=current_client_jar,
        new_authority="EXACT_HISTORICAL_CLIENT",
    )

    authority = json.loads(
        Path(migration["paths"]["authority_candidate"]).read_text(
            encoding="utf-8"
        )
    )
    if authority.get("build_id") != historical_build_id:
        raise GenericHistoricalLineageBackfillError(
            "authority candidate historical build ID drifted"
        )

    material = {
        "current_build_id": current_build_id,
        "historical_build_id": historical_build_id,
        "current_sha256": current_sha,
        "historical_sha256": historical_sha,
        "scope_prefix": scope_prefix,
        "migration_workspace_id": migration["workspace_id"],
        "authority_report_id": authority.get("report_id"),
        "ready_for_authority": bool(authority["ready_for_authority"]),
        "class_match_summary": match_summary,
        "class_transfer_summary": migration["class_transfer_summary"],
        "member_transfer_summary": migration["member_transfer_summary"],
        "field_proof_summary": migration["field_proof_summary"],
        "focused_analysis_items": migration["focused_analysis_items"],
    }
    backfill_id = (
        "HISTGEN_"
        + hashlib.sha256(_stable_json(material))
        .hexdigest()[:20]
        .upper()
    )

    report = {
        "schema_version": 1,
        "kind": "generic_historical_lineage_backfill",
        "backfill_id": backfill_id,
        **material,
        "blockers": copy.deepcopy(authority.get("blockers", [])),
        "authority_summary": copy.deepcopy(authority.get("summary", {})),
        "missing_classes": copy.deepcopy(
            authority.get("missing_classes", [])
        ),
        "missing_members": copy.deepcopy(
            authority.get("missing_members", [])
        ),
        "blocking_class_unresolved": copy.deepcopy(
            authority.get("blocking_class_unresolved", [])
        ),
        "blocking_member_unresolved": copy.deepcopy(
            authority.get("blocking_member_unresolved", [])
        ),
        "paths": {
            "class_match": str(match_path),
            "member_identity_candidates": str(member_candidates_path),
            "migration_workspace": migration["paths"]["workspace"],
            "class_lineage": migration["paths"]["class_lineage"],
            "member_lineage": migration["paths"]["member_lineage"],
            "authority_candidate": migration["paths"][
                "authority_candidate"
            ],
            "focused_analysis_queue": migration["paths"][
                "focused_analysis_queue"
            ],
        },
        "note": (
            "Generic historical derivation through ordinary R3 trust "
            "thresholds only. Partial or ambiguous historical identity remains "
            "blocked for review. The v307 fixture-specific same-symbol field "
            "carry is intentionally not used here."
        ),
    }

    report_path = out_dir / "generic-historical-lineage-backfill.json"
    _dump(report_path, report)
    report["paths"]["report"] = str(report_path)
    return report
