from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .lineage import validate_lineage
from .source_digest import (
    canonical_source_bytes,
    source_tree_digest,
)


class CrossVersionSourceDeltaError(ValueError):
    pass


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _json_digest(value: Any) -> str:
    return hashlib.sha256(_stable_json(value)).hexdigest()


def _require_doc(
    doc: dict[str, Any],
    *,
    kind: str,
    label: str,
) -> None:
    if doc.get("schema_version") != 1 or doc.get("kind") != kind:
        raise CrossVersionSourceDeltaError(
            f"{label}: expected schema_version=1 kind={kind!r}"
        )


def _build_row(
    lineage: dict[str, Any],
    build_id: str,
) -> dict[str, Any]:
    rows = [
        row
        for row in lineage.get("builds", [])
        if row.get("build_id") == build_id
    ]
    if len(rows) != 1:
        raise CrossVersionSourceDeltaError(
            f"class_lineage: expected exactly one build {build_id!r}"
        )
    return rows[0]


def _lineage_entry(
    record: dict[str, Any],
    build_id: str,
) -> dict[str, Any] | None:
    rows = [
        row
        for row in record.get("lineage", [])
        if row.get("build_id") == build_id
    ]
    if len(rows) > 1:
        raise CrossVersionSourceDeltaError(
            f"{record.get('logical_id')}: duplicate lineage for {build_id!r}"
        )
    return rows[0] if rows else None


def _plan_targets(
    plan: dict[str, Any],
    class_lineage: dict[str, Any],
    *,
    build_id: str,
    authority_sha256: str,
    label: str,
) -> dict[str, str]:
    _require_doc(plan, kind="remap_plan", label=label)
    if plan.get("build_id") != build_id:
        raise CrossVersionSourceDeltaError(
            f"{label}: build_id does not match release"
        )
    if (
        str(plan.get("source_sha256") or "").lower()
        != authority_sha256.lower()
    ):
        raise CrossVersionSourceDeltaError(
            f"{label}: source_sha256 does not match release authority"
        )

    records = {
        str(record.get("logical_id")): record
        for record in class_lineage.get("classes", [])
        if isinstance(record, dict)
        and isinstance(record.get("logical_id"), str)
    }
    out: dict[str, str] = {}
    targets: set[str] = set()
    for row in plan.get("classes", []):
        if not isinstance(row, dict):
            raise CrossVersionSourceDeltaError(
                f"{label}: class rows must be objects"
            )
        logical_id = row.get("logical_id")
        target = row.get("target_internal_name")
        if not isinstance(logical_id, str) or not logical_id:
            raise CrossVersionSourceDeltaError(
                f"{label}: class row lacks logical_id"
            )
        if not isinstance(target, str) or not target:
            raise CrossVersionSourceDeltaError(
                f"{label}: class row lacks target_internal_name"
            )
        if logical_id in out:
            raise CrossVersionSourceDeltaError(
                f"{label}: duplicate logical_id {logical_id}"
            )
        record = records.get(logical_id)
        if record is None:
            raise CrossVersionSourceDeltaError(
                f"{label}: unknown logical_id {logical_id}"
            )
        entry = _lineage_entry(record, build_id)
        if entry is None:
            raise CrossVersionSourceDeltaError(
                f"{label}: {logical_id} has no lineage entry for {build_id}"
            )
        expected_source = str(entry.get("internal_name") or "")
        expected_path = str(entry.get("entry_path") or "")
        expected_sha = str(entry.get("entry_sha256") or "").lower()
        if row.get("source_internal_name") != expected_source:
            raise CrossVersionSourceDeltaError(
                f"{label}: {logical_id} source_internal_name drift"
            )
        if row.get("source_entry_path") != expected_path:
            raise CrossVersionSourceDeltaError(
                f"{label}: {logical_id} source_entry_path drift"
            )
        if str(row.get("source_entry_sha256") or "").lower() != expected_sha:
            raise CrossVersionSourceDeltaError(
                f"{label}: {logical_id} source_entry_sha256 drift"
            )
        if target in targets:
            raise CrossVersionSourceDeltaError(
                f"{label}: duplicate target_internal_name {target!r}"
            )
        targets.add(target)
        out[logical_id] = target
    return out


def _tree_sha(root: Path) -> str:
    digest, _files, _bytes = source_tree_digest(root)
    return digest


def _collision_targets(
    plan: dict[str, Any] | None,
    *,
    readable_jar_sha256: str,
    label: str,
) -> dict[str, str]:
    if plan is None:
        return {}
    _require_doc(
        plan,
        kind="class_package_namespace_collision_plan",
        label=label,
    )
    if plan.get("identifiers_included") is not True:
        raise CrossVersionSourceDeltaError(
            f"{label}: identifier-bearing private collision plan required"
        )
    if (
        str(plan.get("readable_jar_sha256") or "").lower()
        != readable_jar_sha256.lower()
    ):
        raise CrossVersionSourceDeltaError(
            f"{label}: readable_jar_sha256 does not match release"
        )
    plan_id = plan.get("plan_id")
    if not isinstance(plan_id, str) or not plan_id.startswith("JNSPLAN_"):
        raise CrossVersionSourceDeltaError(
            f"{label}: invalid collision plan_id"
        )

    out: dict[str, str] = {}
    targets: set[str] = set()
    for row in plan.get("remaps", []):
        if not isinstance(row, dict):
            raise CrossVersionSourceDeltaError(
                f"{label}: remap rows must be objects"
            )
        old = row.get("old_internal_name")
        new = row.get("new_internal_name")
        if not isinstance(old, str) or not old:
            raise CrossVersionSourceDeltaError(
                f"{label}: remap lacks old_internal_name"
            )
        if not isinstance(new, str) or not new:
            raise CrossVersionSourceDeltaError(
                f"{label}: remap lacks new_internal_name"
            )
        if old in out and out[old] != new:
            raise CrossVersionSourceDeltaError(
                f"{label}: conflicting collision remap for {old}"
            )
        if new in targets:
            raise CrossVersionSourceDeltaError(
                f"{label}: duplicate collision target {new}"
            )
        out[old] = new
        targets.add(new)
    return out


def _index_source_units(
    *,
    release: dict[str, Any],
    recovered_manifest: dict[str, Any],
    class_lineage: dict[str, Any],
    class_plan: dict[str, Any],
    collision_plan: dict[str, Any] | None,
    source_root: Path,
    label: str,
) -> dict[str, Any]:
    _require_doc(
        release,
        kind="recovery_release_manifest",
        label=f"{label}_release",
    )
    if release.get("ready_for_release") is not True:
        raise CrossVersionSourceDeltaError(
            f"{label}_release: source comparison requires ready_for_release=true"
        )
    _require_doc(
        recovered_manifest,
        kind="recovered_source_workspace_manifest",
        label=f"{label}_recovered_manifest",
    )

    build_id = str(release.get("build_id") or "")
    authority_sha = str(release.get("authority_sha256") or "").lower()
    expected_tree = str(
        release.get("final_source_tree_sha256") or ""
    ).lower()
    readable_sha = str(
        release.get("readable_jar_sha256") or ""
    ).lower()
    if (
        not build_id
        or len(authority_sha) != 64
        or len(expected_tree) != 64
        or len(readable_sha) != 64
    ):
        raise CrossVersionSourceDeltaError(
            f"{label}_release: incomplete build/source authority"
        )

    pins = release.get("authority_pins")
    if not isinstance(pins, dict):
        raise CrossVersionSourceDeltaError(
            f"{label}_release: missing authority_pins"
        )
    expected_recovered_digest = str(
        pins.get("recovered_source_manifest_sha256") or ""
    ).lower()
    if expected_recovered_digest != _json_digest(recovered_manifest):
        raise CrossVersionSourceDeltaError(
            f"{label}: recovered-source manifest digest does not match release pin"
        )
    if recovered_manifest.get("build_id") != build_id:
        raise CrossVersionSourceDeltaError(
            f"{label}: recovered manifest build_id does not match release"
        )
    if (
        str(recovered_manifest.get("source_authority_sha256") or "").lower()
        != authority_sha
    ):
        raise CrossVersionSourceDeltaError(
            f"{label}: recovered manifest authority SHA does not match release"
        )
    if (
        str(recovered_manifest.get("readable_jar_sha256") or "").lower()
        != readable_sha
    ):
        raise CrossVersionSourceDeltaError(
            f"{label}: recovered manifest readable SHA does not match release"
        )
    if (
        release.get("recovered_workspace_id")
        != recovered_manifest.get("workspace_id")
    ):
        raise CrossVersionSourceDeltaError(
            f"{label}: recovered workspace ID does not match release"
        )

    build = _build_row(class_lineage, build_id)
    if str(build.get("sha256") or "").lower() != authority_sha:
        raise CrossVersionSourceDeltaError(
            f"{label}: lineage build SHA does not match release authority"
        )

    root = source_root.resolve()
    if not root.is_dir():
        raise CrossVersionSourceDeltaError(
            f"{label}: source root does not exist: {root}"
        )
    actual_tree = _tree_sha(root)
    if actual_tree.lower() != expected_tree:
        raise CrossVersionSourceDeltaError(
            f"{label}: source tree SHA mismatch: "
            f"{actual_tree} != {expected_tree}"
        )

    remaps = _plan_targets(
        class_plan,
        class_lineage,
        build_id=build_id,
        authority_sha256=authority_sha,
        label=f"{label}_class_plan",
    )
    if (
        str(recovered_manifest.get("class_plan_digest") or "").lower()
        != _json_digest(class_plan)
    ):
        raise CrossVersionSourceDeltaError(
            f"{label}: class plan digest does not match recovered source authority"
        )
    collision_remaps = _collision_targets(
        collision_plan,
        readable_jar_sha256=readable_sha,
        label=f"{label}_collision_plan",
    )
    expected_collision_plan_id = recovered_manifest.get(
        "collision_plan_id"
    )
    if expected_collision_plan_id is None:
        if collision_plan is not None:
            raise CrossVersionSourceDeltaError(
                f"{label}: collision plan supplied but recovered source is not collision-derived"
            )
    else:
        if collision_plan is None:
            raise CrossVersionSourceDeltaError(
                f"{label}: collision-derived recovered source requires collision plan"
            )
        if collision_plan.get("plan_id") != expected_collision_plan_id:
            raise CrossVersionSourceDeltaError(
                f"{label}: collision plan ID does not match recovered source authority"
            )

    units: dict[str, dict[str, Any]] = {}
    expected_paths: set[str] = set()
    for record in class_lineage.get("classes", []):
        if not isinstance(record, dict):
            continue
        logical_id = record.get("logical_id")
        if not isinstance(logical_id, str) or not logical_id:
            continue
        entry = _lineage_entry(record, build_id)
        if entry is None:
            continue

        source_internal = str(entry.get("internal_name") or "")
        if not source_internal:
            raise CrossVersionSourceDeltaError(
                f"{logical_id}: missing internal_name for {build_id}"
            )

        # Procyon source-workspace selection targets top-level classes only.
        # Nested binary classes are reconstructed inside the outer Java unit.
        if "$" in source_internal.rsplit("/", 1)[-1]:
            continue

        semantic_internal = remaps.get(logical_id, source_internal)
        effective_internal = collision_remaps.get(
            semantic_internal,
            semantic_internal,
        )
        rel = effective_internal + ".java"
        if rel in expected_paths:
            raise CrossVersionSourceDeltaError(
                f"{label}: two logical classes map to source path {rel!r}"
            )
        expected_paths.add(rel)

        path = root / Path(rel)
        if not path.is_file():
            raise CrossVersionSourceDeltaError(
                f"{label}: expected source unit missing for "
                f"{logical_id}: {rel}"
            )
        data = canonical_source_bytes(path.read_bytes())
        units[logical_id] = {
            "logical_id": logical_id,
            "source_internal_name": source_internal,
            "semantic_internal_name": semantic_internal,
            "effective_internal_name": effective_internal,
            "source_path": rel,
            "source_sha256": hashlib.sha256(data).hexdigest(),
            "source_bytes": len(data),
            "semantic_status": record.get("semantic_status"),
            "semantic_name": record.get("semantic_name"),
        }

    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*.java")
    }
    missing_from_index = sorted(actual_paths - expected_paths)
    missing_from_tree = sorted(expected_paths - actual_paths)
    if missing_from_index or missing_from_tree:
        raise CrossVersionSourceDeltaError(
            f"{label}: source-unit coverage mismatch "
            f"unmapped_files={missing_from_index[:10]!r} "
            f"missing_files={missing_from_tree[:10]!r}"
        )

    return {
        "build_id": build_id,
        "authority_sha256": authority_sha,
        "release_id": release.get("release_id"),
        "recovered_workspace_id": recovered_manifest.get("workspace_id"),
        "readable_jar_sha256": readable_sha,
        "collision_plan_id": (
            collision_plan.get("plan_id")
            if collision_plan is not None
            else None
        ),
        "source_tree_sha256": actual_tree,
        "unit_count": len(units),
        "units": units,
    }


def build_cross_version_source_delta(
    old_release: dict[str, Any],
    new_release: dict[str, Any],
    old_recovered_manifest: dict[str, Any],
    new_recovered_manifest: dict[str, Any],
    class_lineage: dict[str, Any],
    old_class_plan: dict[str, Any],
    new_class_plan: dict[str, Any],
    old_source_root: Path,
    new_source_root: Path,
    *,
    old_collision_plan: dict[str, Any] | None = None,
    new_collision_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare independently recovered source trees by stable logical class ID."""
    validate_lineage(class_lineage)

    old = _index_source_units(
        release=old_release,
        recovered_manifest=old_recovered_manifest,
        class_lineage=class_lineage,
        class_plan=old_class_plan,
        collision_plan=old_collision_plan,
        source_root=old_source_root,
        label="old",
    )
    new = _index_source_units(
        release=new_release,
        recovered_manifest=new_recovered_manifest,
        class_lineage=class_lineage,
        class_plan=new_class_plan,
        collision_plan=new_collision_plan,
        source_root=new_source_root,
        label="new",
    )
    if old["build_id"] == new["build_id"]:
        raise CrossVersionSourceDeltaError(
            "old and new source builds must differ"
        )
    if old["authority_sha256"] == new["authority_sha256"]:
        raise CrossVersionSourceDeltaError(
            "old and new exact authorities must differ"
        )

    old_units = old["units"]
    new_units = new["units"]
    old_ids = set(old_units)
    new_ids = set(new_units)

    common = sorted(old_ids & new_ids)
    old_only = sorted(old_ids - new_ids)
    new_only = sorted(new_ids - old_ids)

    unchanged: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    moved: list[dict[str, Any]] = []

    for logical_id in common:
        a = old_units[logical_id]
        b = new_units[logical_id]
        row = {
            "logical_id": logical_id,
            "old_source_path": a["source_path"],
            "new_source_path": b["source_path"],
            "old_source_sha256": a["source_sha256"],
            "new_source_sha256": b["source_sha256"],
            "old_source_bytes": a["source_bytes"],
            "new_source_bytes": b["source_bytes"],
        }
        if a["source_path"] != b["source_path"]:
            moved.append(row)
        if a["source_sha256"] == b["source_sha256"]:
            unchanged.append(row)
        else:
            changed.append(row)

    summary = {
        "old_source_units": len(old_ids),
        "new_source_units": len(new_ids),
        "common_logical_units": len(common),
        "unchanged_source_units": len(unchanged),
        "changed_source_units": len(changed),
        "moved_source_paths": len(moved),
        "old_only_source_units": len(old_only),
        "new_only_source_units": len(new_only),
    }
    material = {
        "old_build_id": old["build_id"],
        "new_build_id": new["build_id"],
        "old_authority_sha256": old["authority_sha256"],
        "new_authority_sha256": new["authority_sha256"],
        "old_release_id": old["release_id"],
        "new_release_id": new["release_id"],
        "old_recovered_workspace_id": old["recovered_workspace_id"],
        "new_recovered_workspace_id": new["recovered_workspace_id"],
        "old_source_tree_sha256": old["source_tree_sha256"],
        "new_source_tree_sha256": new["source_tree_sha256"],
        "old_collision_plan_id": old["collision_plan_id"],
        "new_collision_plan_id": new["collision_plan_id"],
        "summary": summary,
        "old_only": old_only,
        "new_only": new_only,
        "changed": changed,
        "moved": moved,
    }
    report_id = (
        "XVERSRC_"
        + hashlib.sha256(_stable_json(material))
        .hexdigest()[:20]
        .upper()
    )

    return {
        "schema_version": 1,
        "kind": "cross_version_source_delta",
        "report_id": report_id,
        **material,
        "unchanged": unchanged,
        "note": (
            "Source equality is canonicalized Java text equality keyed by "
            "stable CLIENT_CLASS logical identity. A changed source unit is "
            "not by itself a semantic change claim; deterministic decompiler "
            "or normalization differences remain possible and must be "
            "explained by their own provenance."
        ),
    }


def write_cross_version_source_delta(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
