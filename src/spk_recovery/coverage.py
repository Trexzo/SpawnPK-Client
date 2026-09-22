from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .lineage import validate_lineage
from .member_lineage import validate_member_lineage


class CoverageError(ValueError):
    pass


def _has_build(record: dict[str, Any], build_id: str) -> bool:
    return any(
        row.get("build_id") == build_id
        for row in record.get("lineage", [])
    )


def _status_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row.get("semantic_status", "UNKNOWN")) for row in records)
    return {
        "accepted": counts.get("ACCEPTED", 0),
        "candidate": counts.get("CANDIDATE", 0),
        "unknown": counts.get("UNKNOWN", 0),
        "total": len(records),
    }


def _percent(part: int, whole: int) -> float:
    return round((100.0 * part / whole), 4) if whole else 0.0


def _provenance_families(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in records:
        if row.get("semantic_status") != "ACCEPTED":
            continue
        for prov in row.get("semantic_provenance", []):
            if not isinstance(prov, dict):
                continue
            family = prov.get("family") or prov.get("authority") or prov.get("source")
            if isinstance(family, str) and family:
                counts[family] += 1
            evidence = prov.get("evidence")
            if isinstance(evidence, list):
                for item in evidence:
                    if isinstance(item, dict):
                        ef = item.get("family")
                        if isinstance(ef, str) and ef:
                            counts[ef] += 1
    return dict(sorted(counts.items()))


def build_coverage_report(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    *,
    build_id: str,
) -> dict[str, Any]:
    validate_lineage(class_lineage)
    validate_member_lineage(member_lineage, class_lineage=class_lineage)

    builds = [
        b for b in class_lineage.get("builds", [])
        if b.get("build_id") == build_id
    ]
    if len(builds) != 1:
        raise CoverageError(
            f"expected exactly one canonical build {build_id!r}, found {len(builds)}"
        )
    build = builds[0]

    classes = [
        row for row in class_lineage.get("classes", [])
        if _has_build(row, build_id)
    ]
    members = [
        row for row in member_lineage.get("members", [])
        if _has_build(row, build_id)
    ]
    fields = [row for row in members if row.get("kind") == "field"]
    methods = [row for row in members if row.get("kind") == "method"]

    class_counts = _status_counts(classes)
    field_counts = _status_counts(fields)
    method_counts = _status_counts(methods)

    summary = {
        "classes": {
            **class_counts,
            "accepted_percent": _percent(
                class_counts["accepted"], class_counts["total"]
            ),
            "known_percent": _percent(
                class_counts["accepted"] + class_counts["candidate"],
                class_counts["total"],
            ),
        },
        "fields": {
            **field_counts,
            "accepted_percent": _percent(
                field_counts["accepted"], field_counts["total"]
            ),
            "known_percent": _percent(
                field_counts["accepted"] + field_counts["candidate"],
                field_counts["total"],
            ),
        },
        "methods": {
            **method_counts,
            "accepted_percent": _percent(
                method_counts["accepted"], method_counts["total"]
            ),
            "known_percent": _percent(
                method_counts["accepted"] + method_counts["candidate"],
                method_counts["total"],
            ),
        },
    }

    accepted_total = (
        class_counts["accepted"]
        + field_counts["accepted"]
        + method_counts["accepted"]
    )
    entity_total = (
        class_counts["total"]
        + field_counts["total"]
        + method_counts["total"]
    )
    candidate_total = (
        class_counts["candidate"]
        + field_counts["candidate"]
        + method_counts["candidate"]
    )

    material = {
        "build_id": build_id,
        "source_sha256": str(build.get("sha256", "")).lower(),
        "summary": summary,
    }
    digest = hashlib.sha256(
        json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    return {
        "schema_version": 1,
        "kind": "semantic_coverage_report",
        "coverage_id": "COVERAGE_" + digest[:20].upper(),
        "build_id": build_id,
        "source_sha256": str(build.get("sha256", "")).lower(),
        "summary": summary,
        "overall": {
            "entities_total": entity_total,
            "accepted": accepted_total,
            "candidate": candidate_total,
            "unknown": entity_total - accepted_total - candidate_total,
            "accepted_percent": _percent(accepted_total, entity_total),
            "known_percent": _percent(
                accepted_total + candidate_total,
                entity_total,
            ),
        },
        "accepted_provenance_families": {
            "classes": _provenance_families(classes),
            "fields": _provenance_families(fields),
            "methods": _provenance_families(methods),
        },
    }


def write_coverage_report(report: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
