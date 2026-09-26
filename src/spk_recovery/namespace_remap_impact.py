from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .classfile import ClassFormatError, ParsedClass, parse_class


class NamespaceRemapImpactError(ValueError):
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


def _load_classes(jar: Path) -> dict[str, ParsedClass]:
    out: dict[str, ParsedClass] = {}
    with zipfile.ZipFile(jar) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.endswith(".class"):
                continue
            if info.filename.startswith("META-INF/versions/"):
                continue
            try:
                parsed = parse_class(archive.read(info))
            except ClassFormatError as exc:
                raise NamespaceRemapImpactError(
                    f"class parse failed for {info.filename}: {exc}"
                ) from exc
            out[parsed.name] = parsed
    return out


def _rename_map_from_private_proof(
    private_collision_proof: dict[str, Any],
) -> dict[str, str]:
    if (
        private_collision_proof.get("schema_version") != 1
        or private_collision_proof.get("kind")
        != "dependency_namespace_collision_proof"
        or private_collision_proof.get("identifiers_included") is not True
    ):
        raise NamespaceRemapImpactError(
            "requires private identifier-bearing collision proof"
        )

    out: dict[str, str] = {}
    for row in private_collision_proof.get("collision_plan", []):
        family = row.get("rename_family")
        if not isinstance(family, list) or not family:
            raise NamespaceRemapImpactError(
                "collision plan row lacks rename family"
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
                raise NamespaceRemapImpactError(
                    "invalid rename family item"
                )
            existing = out.get(old)
            if existing is not None and existing != new:
                raise NamespaceRemapImpactError(
                    "rename map disagrees across collision families"
                )
            out[old] = new
    return out


def _descriptor_signature_hits(
    value: str,
    old_names: set[str],
) -> set[str]:
    hits: set[str] = set()
    for old in old_names:
        if (
            f"L{old};" in value
            or f"L{old}<" in value
            or f"[L{old};" in value
        ):
            hits.add(old)
    return hits


def _literal_ref_hits(
    literal: str,
    old_names: set[str],
) -> set[str]:
    hits: set[str] = set()
    for old in old_names:
        dotted = old.replace("/", ".")
        if literal in {old, dotted}:
            hits.add(old)
            continue
        if literal.startswith(old + "$"):
            hits.add(old)
            continue
        if literal.startswith(dotted + "$"):
            hits.add(old)
    return hits


def plan_namespace_remap_impact(
    private_collision_proof: dict[str, Any],
    readable_jar: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    readable_jar = readable_jar.resolve()
    if not readable_jar.is_file():
        raise NamespaceRemapImpactError(
            "readable JAR does not exist"
        )

    rename_map = _rename_map_from_private_proof(
        private_collision_proof
    )
    if not rename_map:
        raise NamespaceRemapImpactError(
            "collision proof contains no rename map"
        )

    classes = _load_classes(readable_jar)
    old_names = set(rename_map)

    rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []

    total_class_ref_hits = 0
    total_descriptor_signature_hits = 0
    total_unclassified_utf8_risks = 0
    total_literal_risks = 0

    for index, (internal, parsed) in enumerate(
        sorted(classes.items()),
        start=1,
    ):
        class_ref_hits = sorted(
            old_names & set(parsed.class_references)
        )

        descriptor_signature_hits: set[str] = set()
        unclassified_utf8_hits: set[str] = set()

        literal_values = set(parsed.literal_strings)

        for value in parsed.utf8_strings:
            symbolic = _descriptor_signature_hits(
                value,
                old_names,
            )
            descriptor_signature_hits.update(symbolic)

            for old in old_names:
                if old not in value:
                    continue
                if value == old:
                    continue
                if old in symbolic:
                    continue
                if value in literal_values:
                    continue
                unclassified_utf8_hits.add(old)

        literal_hits: set[str] = set()
        for literal in parsed.literal_strings:
            literal_hits.update(
                _literal_ref_hits(
                    literal,
                    old_names,
                )
            )

        if not (
            class_ref_hits
            or descriptor_signature_hits
            or unclassified_utf8_hits
            or literal_hits
        ):
            continue

        total_class_ref_hits += len(class_ref_hits)
        total_descriptor_signature_hits += len(
            descriptor_signature_hits
        )
        total_unclassified_utf8_risks += len(
            unclassified_utf8_hits
        )
        total_literal_risks += len(literal_hits)

        public = {
            "class_id": f"JREMAPIMPACT_{len(rows) + 1:04d}",
            "hard_class_reference_count": len(class_ref_hits),
            "descriptor_signature_reference_count": len(
                descriptor_signature_hits
            ),
            "unclassified_utf8_risk_count": len(
                unclassified_utf8_hits
            ),
            "reflective_literal_risk_count": len(literal_hits),
            "requires_bytecode_rewrite": bool(
                class_ref_hits
                or descriptor_signature_hits
                or unclassified_utf8_hits
            ),
            "requires_manual_literal_review": bool(literal_hits),
        }
        rows.append(public)

        private_rows.append(
            {
                **public,
                "class_internal_name": internal,
                "hard_class_references": class_ref_hits,
                "descriptor_signature_references": sorted(
                    descriptor_signature_hits
                ),
                "unclassified_utf8_risks": sorted(
                    unclassified_utf8_hits
                ),
                "reflective_literal_risks": sorted(
                    literal_hits
                ),
            }
        )

    target_owner_missing = sorted(
        old_names - set(classes)
    )
    if target_owner_missing:
        raise NamespaceRemapImpactError(
            "rename target owner missing from readable JAR"
        )

    public_rename_rows = [
        {
            "rename_id": f"JRENAME_{index:03d}",
            "nested_binary": "$" in old,
        }
        for index, old in enumerate(
            sorted(rename_map),
            start=1,
        )
    ]

    material = {
        "collision_proof_id": private_collision_proof.get(
            "proof_id"
        ),
        "readable_jar_sha256": _sha256_file(readable_jar),
        "rename_rows": public_rename_rows,
        "impact_rows": rows,
    }

    report: dict[str, Any] = {
        "schema_version": 1,
        "kind": "dependency_namespace_remap_impact_plan",
        "impact_plan_id": (
            "NSREMAPIMPACT_"
            + _stable_digest(material)[:20].upper()
        ),
        "collision_proof_id": private_collision_proof.get(
            "proof_id"
        ),
        "readable_jar_sha256": material[
            "readable_jar_sha256"
        ],
        "summary": {
            "readable_class_count": len(classes),
            "planned_binary_class_rename_count": len(rename_map),
            "planned_nested_binary_class_rename_count": sum(
                "$" in old for old in rename_map
            ),
            "impacted_classfile_count": len(rows),
            "hard_class_reference_count": total_class_ref_hits,
            "descriptor_signature_reference_count": (
                total_descriptor_signature_hits
            ),
            "unclassified_utf8_risk_count": (
                total_unclassified_utf8_risks
            ),
            "reflective_literal_risk_count": total_literal_risks,
            "automatic_bytecode_rewrite_safe": (
                total_unclassified_utf8_risks == 0
                and total_literal_risks == 0
            ),
            "source_reference_rewrite_required": True,
        },
        "renames": public_rename_rows,
        "impact": rows,
        "identifiers_included": include_identifiers,
    }

    if include_identifiers:
        report["renames"] = [
            {
                **public_rename_rows[index - 1],
                "from": old,
                "to": rename_map[old],
            }
            for index, old in enumerate(
                sorted(rename_map),
                start=1,
            )
        ]
        report["impact"] = private_rows

    return report


def write_namespace_remap_impact(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
