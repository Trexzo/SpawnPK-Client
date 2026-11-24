#!/usr/bin/env python3
"""R467 synthetic threshold sweep with directly measured selector overhead.

Compares R455+R456 on identical fabricated in-memory R453 graphs:
independent, forced R464 cache, R466 16-target selector, provisional R467
8-target selector. Includes selector time IN the total and separately
measures its absolute probe cost. Never reads owner files or JAR bytes.
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

from tools.r465 import benchmark_hierarchy_overlap as fixture
from tools.r466 import adaptive_hierarchy as policy
from tools.r467 import calibrated_hierarchy as calibrated

SCHEMA = "SpawnPK-R467-synthetic-threshold-calibration-UNAPPROVED-v1"
DEFAULT_CASES = (
    (1, 1, True),
    (2, 1, True),
    (4, 1, True),
    (8, 1, True),
    (12, 1, True),
    (16, 1, True),
    (24, 1, True),
    (32, 1, True),
    (8, 8, True),
    (24, 8, True),
    (24, 8, False),
)
MAX_CASES = 14
MAX_PAIRS = 4
MODES = ("independent", "forced", "threshold_8", "threshold_16")


class Refused(RuntimeError):
    pass


def choose(workload, threshold):
    return policy.choose(
        workload.rebuilt, workload.selected, workload.sites,
        threshold=threshold)


def execute(workload, mode):
    """Return complete (public, private) R455/R456 evidence and selected gate."""
    if mode == "independent":
        result, index = fixture.analysis(workload, reuse=False)
        return result, index, None
    if mode == "forced":
        result, index = fixture.analysis(workload, reuse=True)
        return result, index, None
    if mode not in ("threshold_8", "threshold_16"):
        raise Refused("R467_UNKNOWN_ANALYSIS_MODE")
    threshold = (calibrated.CALIBRATION_THRESHOLD if
                 mode == "threshold_8" else policy.MIN_SHARED_UNIQUE_TARGETS)
    decision = choose(workload, threshold)
    result, index = fixture.analysis(
        workload, reuse=decision.use_cache)
    return result, index, decision


def measured(workload, mode):
    """Measures selector PLUS analysis, with Python tracked allocations."""
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter_ns()
    cpu_start = time.process_time_ns()
    try:
        outcome, _, decision = execute(workload, mode)
    finally:
        cpu_ns = time.process_time_ns() - cpu_start
        wall_ns = time.perf_counter_ns() - start
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return outcome, {
        "wall_ms": round(wall_ns / 1_000_000, 5),
        "cpu_ms": round(cpu_ns / 1_000_000, 5),
        "python_peak_traced_bytes": peak,
    }


def selector_probe(workload, threshold, *, repetitions=32):
    """Standalone median selector time without the R455/R456 stage."""
    if type(repetitions) is not int or not 1 <= repetitions <= 100:
        raise Refused("R467_INVALID_SELECTOR_SAMPLE_COUNT")
    elapsed = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        choose(workload, threshold)
        elapsed.append((time.perf_counter_ns() - start) / 1000)
    return round(median(elapsed), 3)


def compare(*, pairs=2, cases=DEFAULT_CASES):
    if type(pairs) is not int or not 1 <= pairs <= MAX_PAIRS:
        raise Refused("R467_INVALID_PAIR_COUNT")
    if type(cases) not in (list, tuple) or not cases or len(cases) > MAX_CASES:
        raise Refused("R467_INVALID_CASE_LIST")
    results = []
    for owners, signatures, overlap in cases:
        workload = fixture.fabricated(owners, signatures, overlap)
        baseline, baseline_index, _ = execute(workload, "independent")
        forced, forced_index, _ = execute(workload, "forced")
        calibrated_evidence, calibrated_index, calibrated_decision = execute(
            workload, "threshold_8")
        default_evidence, default_index, default_decision = execute(
            workload, "threshold_16")
        if not (baseline == forced == calibrated_evidence == default_evidence):
            raise Refused("R467_FULL_PUBLIC_PRIVATE_EVIDENCE_MISMATCH")
        if baseline_index is not None or forced_index is None:
            raise Refused("R467_FORCED_INDEPENDENT_MODE_DRIFT")
        if ((calibrated_index is None) == calibrated_decision.use_cache
                or (default_index is None) == default_decision.use_cache):
            raise Refused("R467_GATE_INDEX_SELECTION_DRIFT")
        if (calibrated_decision.use_cache !=
                (overlap and owners * signatures >=
                 calibrated.CALIBRATION_THRESHOLD)
                or default_decision.use_cache !=
                (overlap and owners * signatures >=
                 policy.MIN_SHARED_UNIQUE_TARGETS)):
            raise Refused("R467_EXACT_OVERLAP_THRESHOLD_DRIFT")

        timings = {mode: [] for mode in MODES}
        for iteration in range(pairs):
            order = MODES if iteration % 2 == 0 else tuple(reversed(MODES))
            responses = {}
            for mode in order:
                response, measurement = measured(workload, mode)
                responses[mode] = response
                timings[mode].append(measurement)
            if any(responses[m] != baseline for m in MODES):
                raise Refused("R467_TIMED_FULL_EVIDENCE_MISMATCH")

        output = {}
        for mode, data in timings.items():
            output[mode] = {
                "median_wall_ms": median(x["wall_ms"] for x in data),
                "median_cpu_ms": median(x["cpu_ms"] for x in data),
                "median_python_peak_traced_bytes":
                    median(x["python_peak_traced_bytes"] for x in data),
            }
        base = output["independent"]["median_wall_ms"]
        if base <= 0 or any(v["median_wall_ms"] <= 0 for v in output.values()):
            raise Refused("R467_ZERO_MEASURED_WALL_TIME")

        results.append({
            "reconstructed_class_owners": owners,
            "member_signatures_per_owner": signatures,
            "unique_candidate_references": owners * signatures,
            "overlap": overlap,
            "opcode_sites": len(workload.sites),
            "R466_threshold_16_enabled": default_decision.use_cache,
            "R467_threshold_8_enabled": calibrated_decision.use_cache,
            "R466_threshold_16_selection_reason": default_decision.reason,
            "R467_threshold_8_selection_reason": calibrated_decision.reason,
            "R466_threshold_16_median_selector_us":
                selector_probe(workload, policy.MIN_SHARED_UNIQUE_TARGETS),
            "R467_threshold_8_median_selector_us":
                selector_probe(workload, calibrated.CALIBRATION_THRESHOLD),
            "timing_and_memory": output,
            "forced_wall_ratio": round(
                base / output["forced"]["median_wall_ms"], 3),
            "threshold_16_wall_ratio": round(
                base / output["threshold_16"]["median_wall_ms"], 3),
            "threshold_8_wall_ratio": round(
                base / output["threshold_8"]["median_wall_ms"], 3),
            "complete_public_private_parity": True,
        })

    return {
        "schema": SCHEMA,
        "status": "R467_PROVISIONAL_THRESHOLD_8_SYNTHETIC_BENCHMARK_UNAPPROVED",
        "fixture": "fabricated_R455_R456_in_memory_only",
        "pairs_per_case": pairs,
        "counterbalanced_order": True,
        "provisional_threshold": calibrated.CALIBRATION_THRESHOLD,
        "R466_existing_default_threshold": policy.MIN_SHARED_UNIQUE_TARGETS,
        "cases": results,
        "all_complete_public_private_evidence_equal": True,
        "selector_time_included_in_adaptive_total": True,
        "no_runtime_speedup_threshold_assertions": True,
        "owner_client_or_original_v309_jar_read": False,
        "full_owner_SHA_inventory_measured": False,
        "real_client_speedup_established": False,
        "instrumentation_and_CI_noise_present": True,
        "private_names_paths_hashes_or_bytes_exported": False,
        "historical_R421_approved": False,
        "client_compiled_or_executed": False,
        "merge_authorized": False,
        "release_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, choices=range(1, MAX_PAIRS + 1),
                        default=2)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(compare(pairs=args.pairs),
                         sort_keys=True, separators=(",", ":")))
        return 0
    except Exception:
        print(json.dumps({
            "status": "R467_THRESHOLD_CALIBRATION_REFUSED",
            "reason": "R467_BOUNDED_SYNTHETIC_OR_PARITY_FAILURE",
            "merge_authorized": False,
            "release_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
