from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchThresholds:
    """Conservative defaults for inferred cross-build identity matches."""

    minimum_score: float = 0.88
    minimum_margin: float = 0.10
    minimum_evidence_weight: float = 0.50
    package_anchor_min_support: int = 5
    package_anchor_min_dominance: float = 0.90
    package_anchor_min_score: float = 0.82
    package_anchor_min_evidence_weight: float = 0.38
    structural_score: float = 0.995
    exact_score: float = 1.0


def confidence_label(score: float, strategy: str) -> str:
    if strategy == "exact_sha256":
        return "EXACT"
    if strategy == "structural_unique":
        return "CROSS_BUILD"
    if strategy == "package_anchor":
        return "INFERRED_HIGH"
    if score >= 0.97:
        return "INFERRED_HIGH"
    if score >= 0.88:
        return "INFERRED_MEDIUM"
    return "INFERRED_LOW"
