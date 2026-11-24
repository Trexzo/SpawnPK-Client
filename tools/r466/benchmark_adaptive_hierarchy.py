#!/usr/bin/env python3
"""R466 read-only adaptive hierarchy selection microbenchmark.

Three actual R455/R456 execution paths on identical fabricated in-memory
ClassMembers: independent R463, forced R464 caching, and selectively enabled
R466 caching. R466 selection time is INCLUDED in adaptive measurements.
No owner files, ZIP, Java class loading, client launch or private data.
"""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from statistics import median
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r459 import audit_consolidated_inspection as r459
from tools.r461 import shared_constant_pool as cp
from tools.r462 import shared_instruction_stream as instruction
from tools.r463 import reuse_validated_metadata as metadata
from tools.r464 import shared_hierarchy as shared
from tools.r465 import benchmark_hierarchy_overlap as r465
from tools.r466 import adaptive_hierarchy as policy

SCHEMA = "SpawnPK-R466-adaptive-hierarchy-UNAPPROVED-v1"
MAX_PAIRS = 4
DEFAULT_CASES = (
    (8, 1, True),    # low overlap: cache disabled
    (24, 8, True),   # medium overlap: cache enabled
    (96, 8, True),   # heavy overlap: cache enabled
    (192, 8, True),  # bounded large overlap: cache enabled
    (96, 8, False),  # no actual R456 callsites: cache disabled
)


class Refused(RuntimeError):
    pass


def inspect(original: Path, companion: Path | None = None):
    """Use all R463 optimizations and R464 cache only above overlap gate."""
    return r459.inspect(
        original, companion,
        shared_pool_factory=cp.decode,
        shared_instruction_factory=instruction.Index,
        descriptor_cache_factory=metadata.DescriptorShapes,
        reuse_opcode_summary=True,
        hierarchy_factory=shared.Index,
        hierarchy_selector=policy.should_reuse)


def analysis(workload: r465.Workload, mode: str):
    if mode == "independent":
        result, index = r465.analysis(workload, reuse=False)
        return result, index, None
    if mode == "forced":
        result, index = r465.analysis(workload, reuse=True)
        return result, index, None
    if mode != "adaptive":
        raise Refused("R466_ANALYSIS_MODE_REFUSED")
    decision = policy.choose(workload.rebuilt, workload.selected,
                             workload.sites)
    result, index = r465.analysis(workload, reuse=decision.use_cache)
    return result, index, decision


def timed(workload: r465.Workload, mode: str):
    gc.collect()
    tracemalloc.start()
    wall_start = time.perf_counter_ns()
    cpu_start = time.process_time_ns()
    try:
        result, index, decision = analysis(workload, mode)
    finally:
        elapsed = time.perf_counter_ns() - wall_start
        cpu = time.process_time_ns() - cpu_start
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return result, {
        "wall_ms": round(elapsed / 1_000_000, 4),
        "cpu_ms": round(cpu / 1_000_000, 4),
        "peak_traced_python_bytes": peak,
    }


def compare(*, pairs: int = 2, cases=DEFAULT_CASES):
    if type(pairs) is not int or not 1 <= pairs <= MAX_PAIRS:
        raise Refused("R466_INVALID_PAIR_COUNT")
    if type(cases) not in (list, tuple) or not cases or len(cases) > 8:
        raise Refused("R466_INVALID_WORKLOAD_SET")
    output = []
    for owners, signatures, overlap in cases:
        workload = r465.fabricated(owners, signatures, overlap)
        choice = policy.choose(
            workload.rebuilt, workload.selected, workload.sites)
        expect = (overlap and owners * signatures >=
                  policy.MIN_SHARED_UNIQUE_TARGETS)
        if choice.use_cache != expect:
            raise Refused("R466_OVERLAP_SELECTION_DISAGREEMENT")

        legacy, _, legacy_counts = r465.counted(workload, reuse=False)
        forced, forced_index, forced_counts = r465.counted(
            workload, reuse=True)
        adaptive, adaptive_index, adaptive_counts = r465.counted(
            workload, reuse=choice.use_cache)
        if not (legacy == forced == adaptive):
            raise Refused("R466_FULL_PUBLIC_PRIVATE_OUTPUT_DISAGREEMENT")
        if (adaptive_counts != (forced_counts if expect else legacy_counts)
                or forced_index is None or forced_index.admissions != 2
                or (adaptive_index is None) != (not expect)):
            raise Refused("R466_ADAPTIVE_STAGE_COUNT_DISAGREEMENT")

        sample = {"independent": [], "forced": [], "adaptive": []}
        for pair in range(pairs):
            order = ("independent", "forced", "adaptive")
            if pair % 2:
                order = ("adaptive", "forced", "independent")
            compared = {}
            for name in order:
                result, metrics = timed(workload, name)
                compared[name] = result
                sample[name].append(metrics)
            if not (compared["independent"] ==
                    compared["forced"] == compared["adaptive"]):
                raise Refused("R466_PAIRED_COMPLETE_EVIDENCE_DISAGREEMENT")

        medians = {
            name: {
                "wall_ms": median(m["wall_ms"] for m in rows),
                "cpu_ms": median(m["cpu_ms"] for m in rows),
                "traced_peak_bytes": median(
                    m["peak_traced_python_bytes"] for m in rows),
            }
            for name, rows in sample.items()
        }
        if any(v["wall_ms"] <= 0 for v in medians.values()):
            raise Refused("R466_INVALID_ELAPSED_TIME")
        output.append({
            "reconstructed_caller_records": owners,
            "dependency_class_records": len(workload.selected),
            "unique_signatures_per_owner": signatures,
            "member_reference_count": owners * signatures,
            "modeled_opcode_site_count": len(workload.sites),
            "overlap": overlap,
            "adaptive_cache_enabled": choice.use_cache,
            "selection_reason": choice.reason,
            "selection_threshold": choice.required_unique_targets,
            "exact_shared_unique_targets_at_decision":
                choice.overlapping_unique_targets,
            "legacy_underlying_R454_calls": legacy_counts,
            "forced_underlying_R454_calls": forced_counts,
            "adaptive_underlying_R454_calls": adaptive_counts,
            "forced_cache_ancestry_hits": forced_index.ancestry_hits,
            "forced_cache_resolution_hits": forced_index.resolution_hits,
            "adaptive_cache_ancestry_hits":
                adaptive_index.ancestry_hits if adaptive_index else 0,
            "adaptive_cache_resolution_hits":
                adaptive_index.resolution_hits if adaptive_index else 0,
            "independent": medians["independent"],
            "forced_cache": medians["forced"],
            "adaptive": medians["adaptive"],
            "adaptive_vs_independent_wall_ratio": round(
                medians["independent"]["wall_ms"] /
                medians["adaptive"]["wall_ms"], 3),
            "adaptive_vs_forced_wall_ratio": round(
                medians["forced"]["wall_ms"] /
                medians["adaptive"]["wall_ms"], 3),
            "full_public_private_evidence_parity": True,
        })

    return {
        "schema": SCHEMA,
        "status": "R466_SYNTHETIC_ADAPTIVE_CACHE_BENCHMARK_UNAPPROVED",
        "pairs_per_workload": pairs,
        "counterbalanced_three_mode_comparison": True,
        "fixture": "fabricated_in_memory_only",
        "workloads": output,
        "complete_public_private_parity": True,
        "SHA_owner_inventory_used": False,
        "original_v309_jar_read": False,
        "real_client_analyzed": False,
        "production_speedup_proven": False,
        "instrumentation_overhead_present": True,
        "private_source_or_names_exported": False,
        "owner_history_or_deletion_journals_read": False,
        "historical_R421_custody_approved": False,
        "compilation_authorized": False,
        "merge_authorized": False,
        "release_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, choices=range(1, 5), default=2)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(compare(pairs=args.pairs), sort_keys=True,
                         separators=(",", ":")))
        return 0
    except Exception:
        print(json.dumps({
            "status": "R466_ADAPTIVE_CACHE_BENCHMARK_REFUSED",
            "reason": "R466_SYNTHETIC_INPUT_OR_PARITY_REFUSED",
            "merge_authorized": False,
            "release_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
