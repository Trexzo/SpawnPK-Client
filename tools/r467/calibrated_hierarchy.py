"""R467 conservative provisional 8-overlap hierarchy selector.

R466's established 16-reference default and independent analyzers stay
unchanged. R467 opts in to a LOWER threshold only in a separately audited
entrypoint so real-owner evidence can decide whether it is worth promoting.
A selection is not a statement of JVM linkage or production speed.
"""
from __future__ import annotations

from pathlib import Path

from tools.r459 import audit_consolidated_inspection as r459
from tools.r461 import shared_constant_pool as cp
from tools.r462 import shared_instruction_stream as instructions
from tools.r463 import reuse_validated_metadata as metadata
from tools.r464 import shared_hierarchy as hierarchy
from tools.r466 import adaptive_hierarchy as policy

CALIBRATION_THRESHOLD = 8


def choose(rebuilt, selected, sites):
    return policy.choose(
        rebuilt, selected, sites, threshold=CALIBRATION_THRESHOLD)


def should_reuse(rebuilt, selected, sites) -> bool:
    return choose(rebuilt, selected, sites).use_cache


def inspect(original: Path, companion: Path | None = None):
    """An opt-in SHA-gated R459 audit; no production promotion or writes."""
    return r459.inspect(
        original, companion,
        shared_pool_factory=cp.decode,
        shared_instruction_factory=instructions.Index,
        descriptor_cache_factory=metadata.DescriptorShapes,
        reuse_opcode_summary=True,
        hierarchy_factory=hierarchy.Index,
        hierarchy_selector=should_reuse)
