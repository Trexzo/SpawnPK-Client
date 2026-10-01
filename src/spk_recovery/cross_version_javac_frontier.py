from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any


class CrossVersionJavacFrontierError(ValueError):
    pass


_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_DIAGNOSTIC_ID_RE = re.compile(r"^JAVACDIAG_[0-9A-F]{20}$")
_FRONTIER_ID_RE = re.compile(r"^JAVACFRONTIER_[0-9A-F]{20}$")


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _public_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics = report.get("diagnostics")
    if not isinstance(diagnostics, list):
        raise CrossVersionJavacFrontierError(
            "javac diagnostic report lacks diagnostic rows"
        )

    rows: list[dict[str, Any]] = []
    public_keys = (
        "category",
        "symbol_kind",
        "symbol_shape",
        "location_kind",
        "shape_cluster_id",
        "cluster_id",
        "symbol_id",
        "location_id",
        "file_id",
        "line",
    )
    for row in diagnostics:
        if not isinstance(row, dict):
            raise CrossVersionJavacFrontierError(
                "javac diagnostic row is not an object"
            )
        try:
            rows.append({key: row[key] for key in public_keys})
        except KeyError as exc:
            raise CrossVersionJavacFrontierError(
                "javac diagnostic row lacks public authority fields"
            ) from exc
    return rows


def _validate_diagnostic_authority(
    report: dict[str, Any],
    label: str,
) -> None:
    rows = _public_rows(report)
    expected_frontier = (
        "JAVACFRONTIER_"
        + _stable_digest({"rows": rows})[:20].upper()
    )
    if report.get("frontier_id") != expected_frontier:
        raise CrossVersionJavacFrontierError(
            f"{label}: javac frontier ID does not match diagnostic rows"
        )

    input_sha256 = report["input_sha256"]
    expected_report = (
        "JAVACDIAG_"
        + _stable_digest(
            {
                "input_sha256": input_sha256,
                "rows": rows,
            }
        )[:20].upper()
    )
    if report.get("report_id") != expected_report:
        raise CrossVersionJavacFrontierError(
            f"{label}: javac diagnostic report ID does not match authority"
        )


def _validate_report(report: dict[str, Any], label: str) -> None:
    if (
        report.get("schema_version") != 1
        or report.get("kind") != "javac_diagnostic_classification_report"
    ):
        raise CrossVersionJavacFrontierError(
            f"{label}: unsupported javac diagnostic report"
        )
    frontier_id = report.get("frontier_id")
    if (
        not isinstance(frontier_id, str)
        or _FRONTIER_ID_RE.fullmatch(frontier_id) is None
    ):
        raise CrossVersionJavacFrontierError(
            f"{label}: missing javac frontier authority"
        )
    diagnostic_report_id = report.get("report_id")
    if (
        not isinstance(diagnostic_report_id, str)
        or _DIAGNOSTIC_ID_RE.fullmatch(diagnostic_report_id) is None
    ):
        raise CrossVersionJavacFrontierError(
            f"{label}: missing javac diagnostic report identity"
        )
    input_sha256 = report.get("input_sha256")
    if (
        not isinstance(input_sha256, str)
        or _HEX64_RE.fullmatch(input_sha256) is None
    ):
        raise CrossVersionJavacFrontierError(
            f"{label}: missing javac diagnostic input SHA-256"
        )
    if report.get("identifiers_included") is not True:
        raise CrossVersionJavacFrontierError(
            f"{label}: cross-version comparison requires a private "
            "diagnostic report generated with --include-identifiers"
        )
    if not isinstance(report.get("diagnostics"), list):
        raise CrossVersionJavacFrontierError(
            f"{label}: diagnostics must be an array"
        )
    _validate_diagnostic_authority(report, label)


def _relative_source_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    lowered = normalized.lower()
    marker = "/src/"
    index = lowered.rfind(marker)
    if index >= 0:
        rel = normalized[index + len(marker):]
    elif lowered.startswith("src/"):
        rel = normalized[4:]
    else:
        raise CrossVersionJavacFrontierError(
            f"source path does not contain a src boundary: {value!r}"
        )
    rel = rel.lstrip("/")
    if not rel or not rel.endswith(".java"):
        raise CrossVersionJavacFrontierError(
            f"invalid Java source path: {value!r}"
        )
    return rel


def _string_or_empty(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _signature(row: dict[str, Any]) -> tuple[str, ...]:
    path = row.get("source_path")
    category = row.get("category")
    if not isinstance(path, str) or not path:
        raise CrossVersionJavacFrontierError(
            "private diagnostic row is missing source_path"
        )
    if not isinstance(category, str) or not category:
        raise CrossVersionJavacFrontierError(
            "diagnostic row is missing category"
        )
    return (
        _relative_source_path(path),
        category,
        _string_or_empty(row.get("message")),
        _string_or_empty(row.get("symbol_kind")),
        _string_or_empty(row.get("symbol")),
        _string_or_empty(row.get("location_kind")),
        _string_or_empty(row.get("location")),
        _string_or_empty(row.get("symbol_shape")),
    )


def _counter(report: dict[str, Any]) -> Counter[tuple[str, ...]]:
    out: Counter[tuple[str, ...]] = Counter()
    for raw in report["diagnostics"]:
        if not isinstance(raw, dict):
            raise CrossVersionJavacFrontierError(
                "diagnostic rows must be objects"
            )
        out[_signature(raw)] += 1
    return out


def _category_counts(
    counts: Counter[tuple[str, ...]],
) -> dict[str, int]:
    out: Counter[str] = Counter()
    for signature, count in counts.items():
        out[signature[1]] += count
    return dict(sorted(out.items()))


def _percentage(part: int, whole: int) -> float:
    if whole == 0:
        return 100.0 if part == 0 else 0.0
    return round((part * 100.0) / whole, 4)


def compare_javac_frontiers(
    old_report: dict[str, Any],
    new_report: dict[str, Any],
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    _validate_report(old_report, "old")
    _validate_report(new_report, "new")

    old = _counter(old_report)
    new = _counter(new_report)
    signatures = sorted(set(old) | set(new))

    shared: Counter[tuple[str, ...]] = Counter()
    old_only: Counter[tuple[str, ...]] = Counter()
    new_only: Counter[tuple[str, ...]] = Counter()
    for signature in signatures:
        old_count = old[signature]
        new_count = new[signature]
        common = min(old_count, new_count)
        if common:
            shared[signature] = common
        if old_count > common:
            old_only[signature] = old_count - common
        if new_count > common:
            new_only[signature] = new_count - common

    source_paths = sorted({signature[0] for signature in signatures})
    file_ids = {
        path: f"XJFILE_{index:06d}"
        for index, path in enumerate(source_paths, start=1)
    }

    families: list[dict[str, Any]] = []
    for index, signature in enumerate(signatures, start=1):
        (
            source_path,
            category,
            message,
            symbol_kind,
            symbol,
            location_kind,
            location,
            symbol_shape,
        ) = signature
        row: dict[str, Any] = {
            "family_id": f"XJERR_{index:06d}",
            "file_id": file_ids[source_path],
            "category": category,
            "symbol_kind": symbol_kind or None,
            "symbol_shape": symbol_shape or "none",
            "location_kind": location_kind or None,
            "old_count": old[signature],
            "new_count": new[signature],
            "shared_count": shared[signature],
            "old_only_count": old_only[signature],
            "new_only_count": new_only[signature],
        }
        if include_identifiers:
            row.update(
                {
                    "source_path": source_path,
                    "message": message,
                    "symbol": symbol or None,
                    "location": location or None,
                }
            )
        families.append(row)

    old_total = sum(old.values())
    new_total = sum(new.values())
    shared_total = sum(shared.values())
    old_only_total = sum(old_only.values())
    new_only_total = sum(new_only.values())

    old_files = {signature[0] for signature in old}
    new_files = {signature[0] for signature in new}
    shared_files = {signature[0] for signature in shared}
    public_families = [
        {
            key: value
            for key, value in row.items()
            if key not in {"source_path", "message", "symbol", "location"}
        }
        for row in families
    ]

    summary = {
        "old_total_errors": old_total,
        "new_total_errors": new_total,
        "shared_errors": shared_total,
        "old_only_errors": old_only_total,
        "new_only_errors": new_only_total,
        "shared_percent_of_old": _percentage(shared_total, old_total),
        "shared_percent_of_new": _percentage(shared_total, new_total),
        "old_affected_files": len(old_files),
        "new_affected_files": len(new_files),
        "shared_affected_files": len(shared_files),
        "old_categories": _category_counts(old),
        "new_categories": _category_counts(new),
        "shared_categories": _category_counts(shared),
        "old_only_categories": _category_counts(old_only),
        "new_only_categories": _category_counts(new_only),
        "exact_frontier_equal": old == new,
    }
    material = {
        "old_diagnostic_report_id": old_report["report_id"],
        "new_diagnostic_report_id": new_report["report_id"],
        "old_diagnostic_input_sha256": old_report["input_sha256"],
        "new_diagnostic_input_sha256": new_report["input_sha256"],
        "old_frontier_id": old_report["frontier_id"],
        "new_frontier_id": new_report["frontier_id"],
        "summary": summary,
        "families": public_families,
    }
    report = {
        "schema_version": 1,
        "kind": "cross_version_javac_frontier",
        "report_id": (
            "XJAVACFRONTIER_"
            + _stable_digest(material)[:20].upper()
        ),
        "old_diagnostic_report_id": old_report["report_id"],
        "new_diagnostic_report_id": new_report["report_id"],
        "old_diagnostic_input_sha256": old_report["input_sha256"],
        "new_diagnostic_input_sha256": new_report["input_sha256"],
        "old_frontier_id": old_report["frontier_id"],
        "new_frontier_id": new_report["frontier_id"],
        "summary": summary,
        "families": families,
        "identifiers_included": include_identifiers,
        "note": (
            "Shared counts are multiset intersections of private javac "
            "diagnostic signatures after source-root normalization. "
            "This report compares compiler failure surfaces only; it does "
            "not declare either source tree release-ready."
        ),
    }
    return report


def write_cross_version_javac_frontier(
    report: dict[str, Any],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
