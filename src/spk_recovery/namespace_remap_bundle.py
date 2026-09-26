from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile


class NamespaceRemapBundleError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _entry_sha256s(jar: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    with zipfile.ZipFile(jar) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            out[info.filename] = hashlib.sha256(
                archive.read(info)
            ).hexdigest()
    return out


def _rename_map(
    private_collision_proof: dict[str, Any],
) -> dict[str, str]:
    if (
        private_collision_proof.get("schema_version") != 1
        or private_collision_proof.get("kind")
        != "dependency_namespace_collision_proof"
        or private_collision_proof.get("identifiers_included") is not True
    ):
        raise NamespaceRemapBundleError(
            "requires private identifier-bearing collision proof"
        )

    summary = private_collision_proof.get("summary", {})
    if summary.get("remap_plan_topology_safe") is not True:
        raise NamespaceRemapBundleError(
            "collision proof remap topology is not safe"
        )

    out: dict[str, str] = {}
    targets: set[str] = set()
    for row in private_collision_proof.get("collision_plan", []):
        family = row.get("rename_family")
        if not isinstance(family, list) or not family:
            raise NamespaceRemapBundleError(
                "collision row lacks rename family"
            )
        for item in family:
            old = item.get("from")
            new = item.get("to")
            if (
                not isinstance(old, str)
                or not old
                or not isinstance(new, str)
                or not new
            ):
                raise NamespaceRemapBundleError(
                    "invalid rename family item"
                )
            if old in out and out[old] != new:
                raise NamespaceRemapBundleError(
                    "source maps to multiple targets"
                )
            if new in targets and out.get(old) != new:
                raise NamespaceRemapBundleError(
                    "duplicate remap target"
                )
            out[old] = new
            targets.add(new)
    if not out:
        raise NamespaceRemapBundleError(
            "collision proof contains no class remaps"
        )
    return out


def build_namespace_remap_bundle_plan(
    private_collision_proof: dict[str, Any],
    impact_plan: dict[str, Any],
    readable_jar: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    readable_jar = readable_jar.resolve()
    if not readable_jar.is_file():
        raise NamespaceRemapBundleError(
            "readable JAR does not exist"
        )

    rename_map = _rename_map(private_collision_proof)
    source_sha = _sha256_file(readable_jar)

    if (
        impact_plan.get("schema_version") != 1
        or impact_plan.get("kind")
        != "dependency_namespace_remap_impact_plan"
    ):
        raise NamespaceRemapBundleError(
            "unsupported namespace remap impact plan"
        )
    if (
        impact_plan.get("collision_proof_id")
        != private_collision_proof.get("proof_id")
    ):
        raise NamespaceRemapBundleError(
            "impact plan collision proof binding mismatch"
        )
    if impact_plan.get("readable_jar_sha256") != source_sha:
        raise NamespaceRemapBundleError(
            "impact plan readable JAR binding mismatch"
        )

    impact_summary = impact_plan.get("summary", {})
    if (
        impact_summary.get("planned_binary_class_rename_count")
        != len(rename_map)
    ):
        raise NamespaceRemapBundleError(
            "impact-plan rename count mismatch"
        )
    if (
        impact_summary.get("unclassified_utf8_risk_count") != 0
        or impact_summary.get("reflective_literal_risk_count") != 0
    ):
        raise NamespaceRemapBundleError(
            "remap has unresolved UTF8 or reflective literal risk"
        )
    if impact_summary.get("automatic_bytecode_rewrite_safe") is not True:
        raise NamespaceRemapBundleError(
            "impact plan does not authorize automatic bytecode rewrite"
        )

    entry_shas = _entry_sha256s(readable_jar)
    existing_entries = set(entry_shas)
    target_entries = {
        new + ".class"
        for new in rename_map.values()
    }
    source_entries = {
        old + ".class"
        for old in rename_map
    }

    missing_sources = sorted(
        source_entries - existing_entries
    )
    if missing_sources:
        raise NamespaceRemapBundleError(
            "remap source class missing from readable JAR"
        )

    occupied_targets = sorted(
        target_entries
        & (existing_entries - source_entries)
    )
    if occupied_targets:
        raise NamespaceRemapBundleError(
            "remap target entry already exists"
        )

    ordered = sorted(rename_map.items())
    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    for index, (old, new) in enumerate(ordered, start=1):
        source_entry = old + ".class"
        public = {
            "mapping_id": f"JDEPREMAP_{index:03d}",
            "source_entry_sha256": entry_shas[source_entry],
            "nested_binary": "$" in old,
        }
        public_rows.append(public)
        private_rows.append(
            {
                **public,
                "source_internal_name": old,
                "source_entry_path": source_entry,
                "target_internal_name": new,
                "target_entry_path": new + ".class",
            }
        )

    material = {
        "collision_proof_id": private_collision_proof.get("proof_id"),
        "impact_plan_id": impact_plan.get("impact_plan_id"),
        "source_sha256": source_sha,
        "mappings": public_rows,
    }
    plan: dict[str, Any] = {
        "schema_version": 1,
        "kind": "dependency_namespace_remap_bundle_plan",
        "bundle_plan_id": (
            "NSREMAPBUNDLE_"
            + _stable_digest(material)[:20].upper()
        ),
        "collision_proof_id": material["collision_proof_id"],
        "impact_plan_id": material["impact_plan_id"],
        "source_sha256": source_sha,
        "class_mapping_count": len(public_rows),
        "rewrite_class_name_strings": False,
        "expected_entry_count_delta": 0,
        "verification_requirements": {
            "source_entries_absent": True,
            "target_entries_present": True,
            "target_internal_names_match": True,
            "class_parse_error_count": 0,
            "entry_count_preserved": True,
            "namespace_collision_recheck_required": True,
        },
        "mappings": public_rows,
        "identifiers_included": include_identifiers,
    }
    if include_identifiers:
        plan["mappings"] = private_rows
    return plan


def mapping_tsv(
    private_bundle_plan: dict[str, Any],
) -> str:
    if (
        private_bundle_plan.get("schema_version") != 1
        or private_bundle_plan.get("kind")
        != "dependency_namespace_remap_bundle_plan"
        or private_bundle_plan.get("identifiers_included") is not True
    ):
        raise NamespaceRemapBundleError(
            "mapping TSV requires private bundle plan"
        )

    lines: list[str] = []
    for row in private_bundle_plan.get("mappings", []):
        old = row.get("source_internal_name")
        new = row.get("target_internal_name")
        if not isinstance(old, str) or not isinstance(new, str):
            raise NamespaceRemapBundleError(
                "private mapping row lacks exact names"
            )
        lines.append("C\t" + old + "\t" + new)
    if not lines:
        raise NamespaceRemapBundleError(
            "private bundle plan has no mappings"
        )
    return "\n".join(lines) + "\n"


def write_bundle_plan(
    plan: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
