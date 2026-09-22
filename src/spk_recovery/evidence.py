from __future__ import annotations

from collections import Counter
from typing import Any

from .classfile import _descriptor_shape


_SIGNAL_WEIGHTS: dict[str, float] = {
    "literal_strings": 0.26,
    "numeric_constants": 0.12,
    "field_shapes": 0.15,
    "method_shapes": 0.24,
    "hierarchy_shape": 0.07,
    "entry_size": 0.06,
    "class_header": 0.05,
    "same_path": 0.05,
}


def _freeze(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    return value


def _counter_similarity(left: list[Any], right: list[Any]) -> float | None:
    """Multiset Jaccard. None means the signal carries no evidence."""
    a, b = Counter(map(_freeze, left)), Counter(map(_freeze, right))
    if not a and not b:
        return None
    keys = set(a) | set(b)
    intersection = sum(min(a[k], b[k]) for k in keys)
    union = sum(max(a[k], b[k]) for k in keys)
    return intersection / union if union else None


def _field_shapes(c: dict) -> list[tuple[int, str]]:
    return [
        (int(f.get("access", 0)), _descriptor_shape(str(f.get("descriptor", ""))))
        for f in c.get("fields", [])
    ]


def _method_shapes(c: dict) -> list[tuple[int, str, int | None]]:
    out: list[tuple[int, str, int | None]] = []
    for m in c.get("methods", []):
        if m.get("name") in ("<init>", "<clinit>"):
            continue
        out.append(
            (
                int(m.get("access", 0)),
                _descriptor_shape(str(m.get("descriptor", ""))),
                m.get("code_length"),
            )
        )
    return out


def _hierarchy_shape(c: dict) -> tuple[bool, int]:
    return (c.get("super_name") is not None, len(c.get("interfaces", [])))


def _entry(index: dict, path: str) -> dict:
    return index.get("entries", {}).get(path, {})


def _entry_size_similarity(
    old_index: dict,
    old_path: str,
    new_index: dict,
    new_path: str,
) -> float | None:
    a = _entry(old_index, old_path).get("size")
    b = _entry(new_index, new_path).get("size")
    if not isinstance(a, int) or not isinstance(b, int):
        return None
    if a == b == 0:
        return 1.0
    maximum = max(a, b)
    return 1.0 - abs(a - b) / maximum if maximum else None


def class_evidence(
    old_index: dict,
    old_path: str,
    old_class: dict,
    new_index: dict,
    new_path: str,
    new_class: dict,
) -> dict:
    """Return deterministic, name-light evidence for one candidate pair."""
    old_entry = _entry(old_index, old_path)
    new_entry = _entry(new_index, new_path)
    exact_sha = bool(old_entry.get("sha256")) and (
        old_entry.get("sha256") == new_entry.get("sha256")
    )
    structural = bool(old_class.get("structural_sha256")) and (
        old_class.get("structural_sha256") == new_class.get("structural_sha256")
    )

    signals: dict[str, float | None] = {
        "literal_strings": _counter_similarity(
            list(old_class.get("literal_strings", [])),
            list(new_class.get("literal_strings", [])),
        ),
        "numeric_constants": _counter_similarity(
            list(old_class.get("numeric_constants", [])),
            list(new_class.get("numeric_constants", [])),
        ),
        "field_shapes": _counter_similarity(
            _field_shapes(old_class),
            _field_shapes(new_class),
        ),
        "method_shapes": _counter_similarity(
            _method_shapes(old_class),
            _method_shapes(new_class),
        ),
        "hierarchy_shape": (
            1.0 if _hierarchy_shape(old_class) == _hierarchy_shape(new_class) else 0.0
        ),
        "entry_size": _entry_size_similarity(
            old_index,
            old_path,
            new_index,
            new_path,
        ),
        "class_header": (
            1.0
            if (
                old_class.get("major"),
                old_class.get("minor"),
                old_class.get("access"),
            )
            == (
                new_class.get("major"),
                new_class.get("minor"),
                new_class.get("access"),
            )
            else 0.0
        ),
        "same_path": 1.0 if old_path == new_path else 0.0,
    }

    weighted = 0.0
    available_weight = 0.0
    contributions: dict[str, dict[str, float]] = {}
    for name, value in signals.items():
        if value is None:
            continue
        weight = _SIGNAL_WEIGHTS[name]
        available_weight += weight
        weighted += weight * value
        contributions[name] = {
            "similarity": round(float(value), 6),
            "weight": weight,
            "weighted": round(weight * float(value), 6),
        }

    score = weighted / available_weight if available_weight else 0.0
    return {
        "exact_entry_sha256": exact_sha,
        "structural_sha256_equal": structural,
        "score": round(score, 6),
        "evidence_weight": round(available_weight, 6),
        "signals": contributions,
    }


def candidate_shape_compatible(old_class: dict, new_class: dict) -> bool:
    """Cheap pruning only; rejection here should be obviously incompatible."""
    if old_class.get("major") != new_class.get("major"):
        return False
    if old_class.get("access") != new_class.get("access"):
        return False

    old_fields = int(
        old_class.get("field_count", len(old_class.get("fields", [])))
    )
    new_fields = int(
        new_class.get("field_count", len(new_class.get("fields", [])))
    )
    old_methods = int(
        old_class.get("method_count", len(old_class.get("methods", [])))
    )
    new_methods = int(
        new_class.get("method_count", len(new_class.get("methods", [])))
    )

    field_limit = max(2, int(max(old_fields, new_fields) * 0.35))
    method_limit = max(3, int(max(old_methods, new_methods) * 0.30))
    return (
        abs(old_fields - new_fields) <= field_limit
        and abs(old_methods - new_methods) <= method_limit
    )
