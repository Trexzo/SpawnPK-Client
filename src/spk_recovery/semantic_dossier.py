from __future__ import annotations

from collections import Counter
import math
import re
from typing import Any


_KIND_WEIGHT = {
    "resource_path": 1.30,
    "command": 1.25,
    "control_token": 1.15,
    "ui_text": 1.00,
    "plain_token": 0.55,
}

_NOISE_EXACT = {
    "N/A",
    "SCRIPT_HOLDER",
}

_NOISE_PATTERNS = (
    re.compile(r"^line\s+\d+$", re.IGNORECASE),
    re.compile(r"^rank:?\s*\d+$", re.IGNORECASE),
    re.compile(r"^[\W_]+$"),
)


def classify_semantic_literal(value: str) -> str | None:
    """Classify one exact class literal as a possible semantic anchor.

    The classification is intentionally descriptive. It does not infer a class,
    field or method name.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if (
        text in _NOISE_EXACT
        or len(text) < 4
        or len(text) > 180
        or sum(ch.isalpha() for ch in text) < 3
    ):
        return None
    if any(pattern.fullmatch(text) for pattern in _NOISE_PATTERNS):
        return None

    if re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", text):
        return "control_token"
    if text.startswith("::"):
        return "command"

    if (
        "/" in text
        and "\n" not in text
        and "@" not in text
        and "<" not in text
        and re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_./ -]+",
            text,
        )
    ):
        return "resource_path"

    if " " in text or "\n" in text:
        return "ui_text"

    if re.fullmatch(r"[a-z][a-z0-9_]{5,}", text):
        return "plain_token"

    return None


def _scope(
    index: dict[str, Any],
    prefix: str | None,
) -> dict[str, dict[str, Any]]:
    classes = index.get("classes", {})
    if prefix is None:
        return {
            path: value
            for path, value in classes.items()
            if isinstance(value, dict)
        }
    return {
        path: value
        for path, value in classes.items()
        if path.startswith(prefix) and isinstance(value, dict)
    }


def _document_frequency(
    classes: dict[str, dict[str, Any]],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for cls in classes.values():
        values = {
            value
            for value in cls.get("literal_strings", [])
            if isinstance(value, str)
        }
        counts.update(values)
    return counts


def _literal_score(
    *,
    text: str,
    kind: str,
    document_frequency: int,
    class_count: int,
) -> float:
    idf = math.log(
        (class_count + 1) / (document_frequency + 1)
    ) + 1.0
    length_factor = min(
        1.0,
        max(0.30, len(text.strip()) / 24.0),
    )
    score = _KIND_WEIGHT[kind] * idf * length_factor
    if document_frequency == 1:
        score *= 1.12
    return score


def _likely_widget_constants(
    cls: dict[str, Any],
    *,
    limit: int,
) -> list[int]:
    values = {
        value
        for value in cls.get("numeric_constants", [])
        if (
            isinstance(value, int)
            and not isinstance(value, bool)
            and 1000 <= value <= 65535
        )
    }
    return sorted(values)[:limit]


def build_semantic_dossiers(
    index: dict[str, Any],
    *,
    prefix: str | None = "rs/",
    max_classes: int | None = None,
    max_evidence_per_class: int = 12,
    max_document_frequency: int = 8,
    widget_constant_limit: int = 40,
) -> dict[str, Any]:
    """Build deterministic, non-canonical semantic evidence dossiers.

    High-information strings are ranked by rarity inside the exact index.
    Numeric constants are surfaced separately as possible widget/interface IDs,
    but do not contribute to the semantic score because their role is not proven.
    """
    if max_classes is not None and max_classes < 1:
        raise ValueError("max_classes must be >= 1 or None")
    if max_evidence_per_class < 1:
        raise ValueError("max_evidence_per_class must be >= 1")
    if max_document_frequency < 1:
        raise ValueError("max_document_frequency must be >= 1")
    if widget_constant_limit < 0:
        raise ValueError("widget_constant_limit must be >= 0")

    classes = _scope(index, prefix)
    class_count = len(classes)
    document_frequency = _document_frequency(classes)
    dossiers: list[dict[str, Any]] = []

    for path, cls in sorted(classes.items()):
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()

        for value in cls.get("literal_strings", []):
            if not isinstance(value, str):
                continue
            text = value.strip()
            if text in seen:
                continue
            seen.add(text)

            kind = classify_semantic_literal(value)
            if kind is None:
                continue

            frequency = int(document_frequency[value])
            if frequency > max_document_frequency:
                continue

            score = _literal_score(
                text=text,
                kind=kind,
                document_frequency=frequency,
                class_count=class_count,
            )
            rows.append(
                {
                    "text": text,
                    "kind": kind,
                    "document_frequency": frequency,
                    "score": round(score, 6),
                }
            )

        rows.sort(
            key=lambda row: (
                -row["score"],
                row["document_frequency"],
                row["kind"],
                row["text"],
            )
        )
        if not rows:
            continue

        selected = rows[:max_evidence_per_class]
        category_count = len(
            {row["kind"] for row in selected}
        )
        raw_score = sum(
            float(row["score"])
            for row in selected
        )
        diversity_factor = (
            1.0 + 0.06 * max(0, category_count - 1)
        )
        semantic_score = raw_score * diversity_factor

        dossiers.append(
            {
                "entry_path": path,
                "internal_name": cls.get("internal_name"),
                "semantic_score": round(
                    semantic_score,
                    6,
                ),
                "anchor_count": len(rows),
                "unique_anchor_count": sum(
                    1
                    for row in rows
                    if row["document_frequency"] == 1
                ),
                "categories": sorted(
                    {row["kind"] for row in rows}
                ),
                "anchors": selected,
                "likely_widget_constants": (
                    _likely_widget_constants(
                        cls,
                        limit=widget_constant_limit,
                    )
                ),
            }
        )

    dossiers.sort(
        key=lambda row: (
            -row["semantic_score"],
            -row["unique_anchor_count"],
            row["entry_path"],
        )
    )
    if max_classes is not None:
        dossiers = dossiers[:max_classes]

    return {
        "schema_version": 1,
        "kind": "semantic_dossiers",
        "canonical": False,
        "source_sha256": index.get("sha256"),
        "scope_prefix": prefix,
        "summary": {
            "scoped_class_count": class_count,
            "dossier_count": len(dossiers),
            "max_document_frequency": (
                max_document_frequency
            ),
            "max_evidence_per_class": (
                max_evidence_per_class
            ),
        },
        "dossiers": dossiers,
    }
