from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any


class JavacDiagnosticError(ValueError):
    pass


_HEADER_RE = re.compile(
    r"^(?P<path>.+\.java):(?P<line>\d+):\s+error:\s+(?P<message>.+)$"
)
_SYMBOL_RE = re.compile(r"^\s*symbol:\s+(?P<kind>\w+)\s+(?P<value>.+?)\s*$")
_LOCATION_RE = re.compile(
    r"^\s*location:\s+(?P<kind>\w+)\s+(?P<value>.+?)\s*$"
)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _category(message: str) -> str:
    value = message.strip()
    if value == "cannot find symbol":
        return "cannot_find_symbol"
    if value.startswith("package ") and value.endswith(" does not exist"):
        return "package_does_not_exist"
    if value.startswith("incompatible types:"):
        return "incompatible_types"
    if " cannot be converted to " in value:
        return "cannot_be_converted"
    if value.startswith("reference to ") and value.endswith(" is ambiguous"):
        return "ambiguous_reference"
    if " has private access in " in value:
        return "private_access"
    if " has protected access in " in value:
        return "protected_access"
    if " cannot be applied to given types" in value:
        return "cannot_apply_arguments"
    if value.endswith(" cannot be dereferenced"):
        return "cannot_be_dereferenced"
    if value.startswith("method does not override or implement"):
        return "override_mismatch"
    if value.startswith("name clash:"):
        return "name_clash"
    if value.startswith("bad operand type"):
        return "bad_operand_type"
    if value.startswith("non-static ") and " cannot be referenced from a static context" in value:
        return "non_static_from_static_context"
    if value.startswith("variable ") and value.endswith(" might already have been assigned"):
        return "already_assigned"
    return "other"


def _split_args(text: str) -> list[str]:
    value = text.strip()
    if not value:
        return []
    out: list[str] = []
    depth = 0
    start = 0
    pairs = {"(": ")", "<": ">", "[": "]"}
    openers = set(pairs)
    closers = set(pairs.values())
    for index, ch in enumerate(value):
        if ch in openers:
            depth += 1
        elif ch in closers:
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            out.append(value[start:index].strip())
            start = index + 1
    out.append(value[start:].strip())
    return out


def _symbol_shape(kind: str | None, value: str | None) -> str:
    if not kind:
        return "none"
    kind = kind.lower()
    if kind == "method" and value:
        left = value.find("(")
        right = value.rfind(")")
        if left >= 0 and right > left:
            arity = len(_split_args(value[left + 1:right]))
            return f"method/arity_{arity}"
        return "method/unknown_arity"
    if kind == "constructor" and value:
        left = value.find("(")
        right = value.rfind(")")
        if left >= 0 and right > left:
            arity = len(_split_args(value[left + 1:right]))
            return f"constructor/arity_{arity}"
        return "constructor/unknown_arity"
    return kind


def classify_javac_diagnostics(
    raw_text: str,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    clean = _ANSI_RE.sub("", raw_text.replace("\r\n", "\n"))
    raw_sha = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    lines = clean.splitlines()

    rows: list[dict[str, Any]] = []
    i = 0
    while i < len(lines):
        match = _HEADER_RE.match(lines[i])
        if match is None:
            i += 1
            continue

        path = match.group("path")
        line = int(match.group("line"))
        message = match.group("message").strip()
        category = _category(message)
        symbol_kind: str | None = None
        symbol_value: str | None = None
        location_kind: str | None = None
        location_value: str | None = None

        j = i + 1
        while j < len(lines):
            if _HEADER_RE.match(lines[j]):
                break
            symbol = _SYMBOL_RE.match(lines[j])
            if symbol is not None:
                symbol_kind = symbol.group("kind")
                symbol_value = symbol.group("value")
            location = _LOCATION_RE.match(lines[j])
            if location is not None:
                location_kind = location.group("kind")
                location_value = location.group("value")
            j += 1

        shape = _symbol_shape(symbol_kind, symbol_value)
        cluster_material = {
            "category": category,
            "symbol_kind": symbol_kind or "none",
            "symbol_shape": shape,
            "location_kind": location_kind or "none",
        }
        row: dict[str, Any] = {
            "category": category,
            "symbol_kind": symbol_kind,
            "symbol_shape": shape,
            "location_kind": location_kind,
            "cluster_id": "JDC_" + _stable_digest(cluster_material)[:16].upper(),
            "file_id": "JFILE_" + hashlib.sha256(path.encode("utf-8")).hexdigest()[:16].upper(),
            "line": line,
        }
        if include_identifiers:
            row.update(
                {
                    "source_path": path,
                    "message": message,
                    "symbol": symbol_value,
                    "location": location_value,
                }
            )
        rows.append(row)
        i = j

    category_counts = Counter(row["category"] for row in rows)
    files = {row["file_id"] for row in rows}
    cannot = [row for row in rows if row["category"] == "cannot_find_symbol"]
    symbol_kinds = Counter((row["symbol_kind"] or "none") for row in cannot)
    location_kinds = Counter((row["location_kind"] or "none") for row in cannot)
    symbol_shapes = Counter(row["symbol_shape"] for row in cannot)
    cluster_counts = Counter(row["cluster_id"] for row in rows)

    public_rows = [
        {
            "category": row["category"],
            "symbol_kind": row["symbol_kind"],
            "symbol_shape": row["symbol_shape"],
            "location_kind": row["location_kind"],
            "cluster_id": row["cluster_id"],
            "file_id": row["file_id"],
            "line": row["line"],
        }
        for row in rows
    ]
    material = {
        "input_sha256": raw_sha,
        "rows": public_rows,
    }
    report = {
        "schema_version": 1,
        "kind": "javac_diagnostic_classification_report",
        "report_id": "JAVACDIAG_" + _stable_digest(material)[:20].upper(),
        "input_sha256": raw_sha,
        "summary": {
            "total_errors": len(rows),
            "affected_files": len(files),
            "categories": dict(sorted(category_counts.items())),
            "cannot_find_symbol": {
                "count": len(cannot),
                "symbol_kinds": dict(sorted(symbol_kinds.items())),
                "location_kinds": dict(sorted(location_kinds.items())),
                "symbol_shapes": dict(sorted(symbol_shapes.items())),
            },
            "clusters": [
                {"cluster_id": key, "count": value}
                for key, value in sorted(
                    cluster_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
        },
        "diagnostics": rows,
        "identifiers_included": include_identifiers,
    }
    return report


def write_javac_diagnostic_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
