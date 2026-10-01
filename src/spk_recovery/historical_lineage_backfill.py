from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from .diffing import diff_indexes
from .indexer import index_jar
from .lineage import validate_lineage, write_lineage
from .matcher import match_classes
from .member_identity import build_member_identity_candidates
from .member_lineage import (
    validate_member_lineage,
    write_member_lineage,
)
from .update_finalize import build_authority_candidate_report
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


def _field_declarations(cls: dict[str, Any]) -> list[tuple[Any, ...]]:
    return sorted(
        (
            str(row.get("name", "")),
            str(row.get("descriptor", "")),
            int(row.get("access", 0)),
            tuple(sorted(row.get("attributes", []))),
        )
        for row in cls.get("fields", [])
    )


def _method_declarations(cls: dict[str, Any]) -> list[tuple[Any, ...]]:
    return sorted(
        (
            str(row.get("name", "")),
            str(row.get("descriptor", "")),
            int(row.get("access", 0)),
            row.get("code_length"),
            tuple(sorted(row.get("attributes", []))),
        )
        for row in cls.get("methods", [])
    )


def _validate_fixture_binding(
    fixture: dict[str, Any],
    *,
    v307_index: dict[str, Any],
    v308_index: dict[str, Any],
    v307_sha: str,
    v308_sha: str,
) -> list[str]:
    if (
        fixture.get("schema_version") != 1
        or fixture.get("kind")
        != "historical_source_regeneration_fixture"
    ):
        raise HistoricalLineageBackfillError(
            "unsupported historical regeneration fixture"
        )

    old = fixture.get("old")
    new = fixture.get("new")
    binary = fixture.get("binary_authority")
    if not all(isinstance(row, dict) for row in (old, new, binary)):
        raise HistoricalLineageBackfillError(
            "historical fixture is missing old/new/binary authority"
        )
    if old.get("build_id") != "v307" or new.get("build_id") != "v308":
        raise HistoricalLineageBackfillError(
            "historical fixture is not the v307 -> v308 authority pair"
        )

    if str(old.get("client_sha256", "")).lower() != v307_sha:
        raise HistoricalLineageBackfillError(
            "fixture v307 SHA does not match exact historical JAR"
        )
    if str(new.get("client_sha256", "")).lower() != v308_sha:
        raise HistoricalLineageBackfillError(
            "fixture v308 SHA does not match exact current JAR"
        )

    old_entries = int(v307_index.get("summary", {}).get("entry_count", -1))
    new_entries = int(v308_index.get("summary", {}).get("entry_count", -1))
    if old_entries != int(binary.get("old_entry_count", -2)):
        raise HistoricalLineageBackfillError(
            "fixture old entry count does not match exact v307 index"
        )
    if new_entries != int(binary.get("new_entry_count", -2)):
        raise HistoricalLineageBackfillError(
            "fixture new entry count does not match exact v308 index"
        )

    delta = diff_indexes(v307_index, v308_index)
    expected_changed = binary.get("changed_entries")
    if not isinstance(expected_changed, list):
        raise HistoricalLineageBackfillError(
            "fixture changed_entries must be an array"
        )
    expected_changed = sorted(str(path) for path in expected_changed)

    if len(delta.get("added", [])) != int(binary.get("new_only_count", -1)):
        raise HistoricalLineageBackfillError(
            "fixture new-only count does not match exact archive delta"
        )
    if len(delta.get("removed", [])) != int(binary.get("old_only_count", -1)):
        raise HistoricalLineageBackfillError(
            "fixture old-only count does not match exact archive delta"
        )
    if (
        len(delta.get("changed_same_path", []))
        != int(binary.get("changed_entry_count", -1))
    ):
        raise HistoricalLineageBackfillError(
            "fixture changed-entry count does not match exact archive delta"
        )
    if sorted(delta.get("changed_same_path", [])) != expected_changed:
        raise HistoricalLineageBackfillError(
            "fixture changed-entry paths do not match exact archive delta"
        )

    if len(expected_changed) == 1:
        path = expected_changed[0]
        old_entry = v307_index.get("entries", {}).get(path, {})
        new_entry = v308_index.get("entries", {}).get(path, {})
        if (
            str(old_entry.get("sha256", "")).lower()
            != str(binary.get("changed_class_old_sha256", "")).lower()
        ):
            raise HistoricalLineageBackfillError(
                "fixture changed-class old SHA does not match exact v307 entry"
            )
        if (
            str(new_entry.get("sha256", "")).lower()
            != str(binary.get("changed_class_new_sha256", "")).lower()
        ):
            raise HistoricalLineageBackfillError(
                "fixture changed-class new SHA does not match exact v308 entry"
            )

    return expected_changed


def _historical_same_symbol_field_carry(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    v308_index: dict[str, Any],
    v307_index: dict[str, Any],
    changed_paths: list[str],
    *,
    fixture_id: str,
    binary_backtest_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Carry fields only across exact fixture-bound changed classes.

    This is deliberately historical-only. It does not alter the generic R3
    transfer threshold for structurally matched classes.
    """
    out = copy.deepcopy(member_lineage)
    proofs: list[dict[str, Any]] = []
    resolved_keys: set[tuple[str, str, str, str, str]] = set()

    for path in changed_paths:
        old_cls = v308_index.get("classes", {}).get(path)
        new_cls = v307_index.get("classes", {}).get(path)
        if not isinstance(old_cls, dict) or not isinstance(new_cls, dict):
            raise HistoricalLineageBackfillError(
                f"changed class missing from exact indexes: {path}"
            )

        if old_cls.get("internal_name") != new_cls.get("internal_name"):
            raise HistoricalLineageBackfillError(
                f"changed class internal name drifted: {path}"
            )
        if (
            old_cls.get("structural_sha256")
            != new_cls.get("structural_sha256")
        ):
            raise HistoricalLineageBackfillError(
                f"changed class is not structurally equivalent: {path}"
            )
        if _field_declarations(old_cls) != _field_declarations(new_cls):
            raise HistoricalLineageBackfillError(
                f"changed class field declarations drifted: {path}"
            )
        if _method_declarations(old_cls) != _method_declarations(new_cls):
            raise HistoricalLineageBackfillError(
                f"changed class method declarations drifted: {path}"
            )

        internal = str(old_cls.get("internal_name"))
        old_entry_sha = str(
            v308_index.get("entries", {}).get(path, {}).get("sha256", "")
        ).lower()
        new_entry_sha = str(
            v307_index.get("entries", {}).get(path, {}).get("sha256", "")
        ).lower()

        class_records = [
            row
            for row in class_lineage.get("classes", [])
            if any(
                entry.get("build_id") == "v308"
                and entry.get("entry_path") == path
                for entry in row.get("lineage", [])
            )
        ]
        if len(class_records) != 1:
            raise HistoricalLineageBackfillError(
                f"changed class does not resolve to one canonical identity: {path}"
            )
        class_record = class_records[0]
        if not any(
            entry.get("build_id") == "v307"
            and entry.get("entry_path") == path
            for entry in class_record.get("lineage", [])
        ):
            raise HistoricalLineageBackfillError(
                f"changed class has no canonical v307 relation: {path}"
            )

        target_fields = {
            (
                str(row.get("name")),
                str(row.get("descriptor")),
            ): row
            for row in new_cls.get("fields", [])
        }

        for record in out.get("members", []):
            if record.get("kind") != "field":
                continue
            old_hits = [
                entry
                for entry in record.get("lineage", [])
                if entry.get("build_id") == "v308"
                and entry.get("owner_internal_name") == internal
            ]
            if not old_hits:
                continue
            if len(old_hits) != 1:
                raise HistoricalLineageBackfillError(
                    f"{record.get('member_id')}: duplicate v308 field relation"
                )
            if any(
                entry.get("build_id") == "v307"
                for entry in record.get("lineage", [])
            ):
                continue

            old_entry = old_hits[0]
            coord = (
                str(old_entry.get("name")),
                str(old_entry.get("descriptor")),
            )
            target = target_fields.get(coord)
            if target is None:
                raise HistoricalLineageBackfillError(
                    f"changed class field missing from v307: {internal}.{coord}"
                )
            if int(old_entry.get("access", 0)) != int(target.get("access", 0)):
                raise HistoricalLineageBackfillError(
                    f"changed class field access drifted: {internal}.{coord}"
                )

            material = {
                "fixture_id": fixture_id,
                "binary_backtest_id": binary_backtest_id,
                "logical_class_id": class_record.get("logical_id"),
                "member_id": record.get("member_id"),
                "owner": internal,
                "name": coord[0],
                "descriptor": coord[1],
                "v308_entry_sha256": old_entry_sha,
                "v307_entry_sha256": new_entry_sha,
            }
            proof_id = (
                "HISTFIELD_"
                + hashlib.sha256(_stable_json(material))
                .hexdigest()[:20]
                .upper()
            )
            record["lineage"].append(
                {
                    "build_id": "v307",
                    "owner_internal_name": internal,
                    "name": coord[0],
                    "descriptor": coord[1],
                    "access": int(target.get("access", 0)),
                    "relation": "MANUAL",
                    "confidence": 1.0,
                    "provenance": [
                        {
                            "authority": "EXACT_HISTORICAL_CLIENT",
                            "source": proof_id,
                            "note": (
                                "Historical fixture-bound same-symbol field carry. "
                                "Exact changed class hashes are pinned by the binary "
                                "backtest; class structural fingerprint and complete "
                                "field/method declarations are identical."
                            ),
                        }
                    ],
                }
            )
            resolved_keys.add(
                (
                    internal,
                    coord[0],
                    coord[1],
                    internal,
                    coord[0],
                )
            )
            proofs.append(
                {
                    **material,
                    "proof_id": proof_id,
                }
            )

    def keep_unresolved(item: Any) -> bool:
        if not isinstance(item, dict):
            return True
        if (
            item.get("new_build_id") != "v307"
            or item.get("kind") != "member_identity_review"
            or item.get("member_kind") != "field"
        ):
            return True
        candidate = item.get("candidate")
        if not isinstance(candidate, dict):
            return True
        old = candidate.get("old")
        new = candidate.get("new")
        if not isinstance(old, dict) or not isinstance(new, dict):
            return True
        old_owner = str(candidate.get("old_owner", "")).removesuffix(".class")
        new_owner = str(candidate.get("new_owner", "")).removesuffix(".class")
        key = (
            old_owner,
            str(old.get("name")),
            str(old.get("descriptor")),
            new_owner,
            str(new.get("name")),
        )
        return key not in resolved_keys

    before = len(out.get("unresolved", []))
    out["unresolved"] = [
        item
        for item in out.get("unresolved", [])
        if keep_unresolved(item)
    ]
    removed = before - len(out["unresolved"])

    validate_member_lineage(
        out,
        class_lineage=class_lineage,
    )

    material = {
        "fixture_id": fixture_id,
        "binary_backtest_id": binary_backtest_id,
        "changed_paths": changed_paths,
        "proofs": proofs,
    }
    report_id = (
        "HISTFIELDS_"
        + hashlib.sha256(_stable_json(material))
        .hexdigest()[:20]
        .upper()
    )
    return out, {
        "schema_version": 1,
        "kind": "historical_same_symbol_field_carry",
        "report_id": report_id,
        **material,
        "applied_fields": len(proofs),
        "unresolved_removed": removed,
    }


def backfill_historical_v307_lineage(
    v308_client_jar: Path,
    v307_client_jar: Path,
    v308_index: dict[str, Any],
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    fixture: dict[str, Any],
    *,
    out_dir: Path,
) -> dict[str, Any]:
    """Derive canonical v307 relations from exact canonical v308 authority."""
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
    v307_sha = _sha256_file(v307_client_jar)
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

    changed_paths = _validate_fixture_binding(
        fixture,
        v307_index=v307_index,
        v308_index=v308_index,
        v307_sha=v307_sha,
        v308_sha=v308_sha,
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
    _dump(candidate_path, member_candidates)

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

    migrated_classes = json.loads(
        Path(result["paths"]["class_lineage"]).read_text(
            encoding="utf-8"
        )
    )
    migrated_members = json.loads(
        Path(result["paths"]["member_lineage"]).read_text(
            encoding="utf-8"
        )
    )

    binary = fixture["binary_authority"]
    fixture_id = str(fixture.get("fixture_id"))
    binary_backtest_id = str(binary.get("backtest_id"))

    historical_field_report = {
        "schema_version": 1,
        "kind": "historical_same_symbol_field_carry",
        "report_id": "HISTFIELDS_NONE",
        "fixture_id": fixture_id,
        "binary_backtest_id": binary_backtest_id,
        "changed_paths": changed_paths,
        "proofs": [],
        "applied_fields": 0,
        "unresolved_removed": 0,
    }

    changed_class_paths = [
        path
        for path in changed_paths
        if path.startswith("rs/") and path.endswith(".class")
    ]

    if changed_class_paths:
        (
            migrated_members,
            historical_field_report,
        ) = _historical_same_symbol_field_carry(
            migrated_classes,
            migrated_members,
            v308_index,
            v307_index,
            changed_class_paths,
            fixture_id=fixture_id,
            binary_backtest_id=binary_backtest_id,
        )

    intake = json.loads(
        Path(result["paths"]["intake_report"]).read_text(
            encoding="utf-8"
        )
    )
    authority = build_authority_candidate_report(
        migrated_classes,
        migrated_members,
        v307_index,
        intake,
        build_id="v307",
        scope_prefix="rs/",
    )

    final_class_path = out_dir / "class-lineage.json"
    final_member_path = out_dir / "member-lineage.json"
    authority_path = out_dir / "authority-candidate.json"
    field_report_path = out_dir / "historical-field-carry.json"

    write_lineage(migrated_classes, final_class_path)
    write_member_lineage(migrated_members, final_member_path)
    _dump(authority_path, authority)
    _dump(field_report_path, historical_field_report)

    material = {
        "v308_sha256": v308_sha,
        "v307_sha256": v307_sha,
        "workspace_id": result["workspace_id"],
        "authority_report_id": authority.get("report_id"),
        "ready_for_authority": bool(authority["ready_for_authority"]),
        "class_transfer_summary": result["class_transfer_summary"],
        "member_transfer_summary": result["member_transfer_summary"],
        "field_proof_summary": result["field_proof_summary"],
        "historical_field_carry_summary": {
            "report_id": historical_field_report["report_id"],
            "applied_fields": historical_field_report["applied_fields"],
            "unresolved_removed": historical_field_report[
                "unresolved_removed"
            ],
        },
        "focused_analysis_items": (
            0
            if authority["ready_for_authority"]
            else result["focused_analysis_items"]
        ),
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
            "generic_migration_workspace": result["paths"]["workspace"],
            "class_lineage": str(final_class_path),
            "member_lineage": str(final_member_path),
            "authority_candidate": str(authority_path),
            "historical_field_carry": str(field_report_path),
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
            "inputs were not mutated. Generic R3 trust thresholds remain "
            "unchanged; exact fixture-bound same-symbol field carry is isolated "
            "to the pinned historical v307/v308 binary pair."
        ),
    }

    report_path = out_dir / "historical-lineage-backfill.json"
    _dump(report_path, report)
    report["paths"]["report"] = str(report_path)
    return report
