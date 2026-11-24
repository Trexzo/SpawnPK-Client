#!/usr/bin/env python3
"""R468 replicated-batch, paired, no-tracemalloc hierarchy threshold benchmark.

The earlier R467 two-pair, single-iteration timings were noisy for 1-4
synthetic references. R468 uses fixed-size repeated batches, prewarming,
alternating mode order, >=3 independent paired trials and median absolute
deviation. NO runtime speedup acceptance threshold or owner-source claim.

All inputs are fabricated immutable R453 metadata and modeled R456 sites;
the full public/private outputs of R455+R456 must agree for EVERY mode.
"""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from statistics import median
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r465 import benchmark_hierarchy_overlap as fixtures
from tools.r466 import adaptive_hierarchy as policy

SCHEMA = "SpawnPK-R468-small-hierarchy-batched-calibration-UNAPPROVED-v1"
CASES = ((1, 1, True), (2, 1, True), (4, 1, True),
         (8, 1, True), (12, 1, True), (16, 1, True),
         (24, 1, False))
MODES = ("independent", "forced", "threshold_2", "threshold_4",
         "threshold_8", "threshold_16")
THRESHOLDS = {
    "threshold_2": 2,
    "threshold_4": 4,
    "threshold_8": 8,
    "threshold_16": 16,
}


class Refused(RuntimeError):
    pass


def select(workload, mode: str):
    if mode == "independent":
        return False
    if mode == "forced":
        return True
    if mode not in THRESHOLDS:
        raise Refused("R468_INVALID_TIMING_MODE")
    return policy.choose(
        workload.rebuilt, workload.selected, workload.sites,
        threshold=THRESHOLDS[mode]).use_cache


def run_mode(workload, mode):
    enable = select(workload, mode)
    outcome, _index = fixtures.analysis(workload, reuse=enable)
    return outcome


def one_batch(workload, mode, *, iterations: int):
    """Wall/CPU timing around MULTIPLE complete analyzer invocations."""
    wall_start = time.perf_counter_ns()
    cpu_start = time.process_time_ns()
    final = None
    for _ in range(iterations):
        final = run_mode(workload, mode)
    elapsed = time.perf_counter_ns() - wall_start
    cpu = time.process_time_ns() - cpu_start
    return final, (
        elapsed / (iterations * 1_000_000),
        cpu / (iterations * 1_000_000))


def robust_median(values):
    value = median(values)
    return {
        "median_ms_per_complete_analysis": round(value, 5),
        "median_abs_deviation_ms": round(
            median(abs(x - value) for x in values), 5),
        "min_ms": round(min(values), 5),
        "max_ms": round(max(values), 5),
    }


def compare(*, pairs: int = 5, iterations: int = 8, cases=CASES):
    if (type(pairs) is not int or not 3 <= pairs <= 9
            or type(iterations) is not int or not 1 <= iterations <= 16
            or type(cases) not in (list, tuple) or
            not 1 <= len(cases) <= len(CASES)):
        raise Refused("R468_BATCH_MEASUREMENT_BUDGET_INVALID")

    output = []
    for owners, signatures, overlap in cases:
        workload = fixtures.fabricated(owners, signatures, overlap)
        baseline = run_mode(workload, "independent")
        for mode in MODES:
            if run_mode(workload, mode) != baseline:
                raise Refused("R468_COMPLETE_PUBLIC_PRIVATE_EVIDENCE_DRIFT")
        selection = {m: select(workload, m) for m in MODES}

        # Warm each mode before the timed runs; no microsecond-scale single
        # iteration data are reported as a demonstrated performance speedup.
        for mode in MODES:
            run_mode(workload, mode)

        wall = {mode: [] for mode in MODES}
        cpu = {mode: [] for mode in MODES}
        paired_ratios = {mode: [] for mode in MODES if mode != "independent"}
        for trial in range(pairs):
            gc.collect()  # OUTSIDE timed regions, consistent per trial.
            order = MODES if trial % 2 == 0 else tuple(reversed(MODES))
            current = {}
            for mode in order:
                result, (w, c) = one_batch(
                    workload, mode, iterations=iterations)
                # Windows process_time_ns can be coarse enough to report
                # ZERO CPU elapsed for short correct batches. Zero is a
                # measured resolution floor, not invalid evidence. Wall
                # time must be positive and both values nonnegative.
                if result != baseline or w <= 0 or c < 0:
                    raise Refused("R468_PAIRED_MEASUREMENT_OR_OUTPUT_DRIFT")
                wall[mode].append(w)
                cpu[mode].append(c)
                current[mode] = w
            for mode in paired_ratios:
                paired_ratios[mode].append(
                    current["independent"] / current[mode])

        output.append({
            "fabricated_class_owners": owners,
            "method_signatures_per_owner": signatures,
            "eligible_unique_overlapping_targets":
                owners * signatures if overlap else 0,
            "modeled_member_opcode_sites": len(workload.sites),
            "cache_enabled_by_mode": selection,
            "wall_time_by_mode": {
                mode: robust_median(values) for mode, values in wall.items()
            },
            "cpu_time_by_mode": {
                mode: robust_median(values) for mode, values in cpu.items()
            },
            "median_paired_wall_ratio_over_independent": {
                mode: round(median(values), 3)
                for mode, values in paired_ratios.items()
            },
            "paired_wall_ratio_range": {
                mode: [round(min(values), 3), round(max(values), 3)]
                for mode, values in paired_ratios.items()
            },
            "entire_public_private_evidence_equal": True,
        })

    return {
        "schema": SCHEMA,
        "status": "R468_SYNTHETIC_BATCHED_THRESHOLD_BENCHMARK_UNAPPROVED",
        "modeled_cases": output,
        "paired_trials_per_case": pairs,
        "complete_analyses_per_timed_sample": iterations,
        "prewarmed": True,
        "alternating_order": True,
        "timer_includes_selector_and_R455_R456_analysis": True,
        "tracemalloc_disabled_for_timing": True,
        "coarse_cpu_clock_may_report_zero_on_windows": True,
        "no_performance_ratio_pass_fail_gate": True,
        "all_complete_public_and_private_evidence_parity": True,
        "original_owner_client_used": False,
        "historical_R421_custody_approved": False,
        "private_names_or_paths_exported": False,
        "runtime_or_network_latency_measured": False,
        "merge_authorized": False,
        "release_authorized": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, choices=range(3, 10), default=5)
    parser.add_argument("--iterations", type=int, choices=range(1, 17),
                        default=8)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(compare(
            pairs=args.pairs, iterations=args.iterations),
            sort_keys=True, separators=(",", ":")))
        return 0
    except Exception:
        print(json.dumps({
            "status": "R468_BATCHED_THRESHOLD_BENCHMARK_REFUSED",
            "reason": "R468_SYNTHETIC_INPUT_OR_PARITY_NOT_ADMITTED",
            "merge_authorized": False,
            "release_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
