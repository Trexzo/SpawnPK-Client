#!/usr/bin/env python3
"""R460 read-only paired profiling of legacy R458 and consolidated R459.

Only aggregate counters leave the process: no private filenames, class
names, SHA maps, bytecode, source, player history, or persistence journals.
Both workflows retain their original authorization and integrity checks.
Timing includes instrumentation/tracemalloc overhead and is not a production
speedup claim; the public CI fixture is fabricated.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import gc
import json
from pathlib import Path
from statistics import median
import sys
import time
import tracemalloc
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r444 import scan_owner_r421_artifacts as scanner
from tools.r446 import observe_owner_private_inventory as r446
from tools.r447 import audit_original_class_asset_coverage as r447
from tools.r458 import audit_bootstrap_evidence as r458
from tools.r459 import audit_consolidated_inspection as r459

SCHEMA = "SpawnPK-R460-paired-benchmark-UNAPPROVED-v1"
MAX_PAIRS = 4
# Timers are inclusive and may overlap (e.g., a nested parser). Never add
# them to calculate exclusive CPU percentages.
STAGES = (
    ("full_sha_inventory", r446, "observe"),
    ("zip_directory_admission", r447, "archive"),
    ("member_constant_pool_parse", r459.r453, "parse_class"),
    ("bootstrap_dynamic_parse", r459.r458, "scan_class"),
    ("code_signature_resource_parse", r459.r450, "classfile_evidence"),
    ("dependency_selection", r459.r455, "selected_dependencies"),
    ("member_reference_classification", r459.r453_audit, "classify"),
    ("inheritance_analysis", r459.r454, "analyze"),
    ("dependency_access_analysis", r459.r455, "analyze"),
    ("opcode_analysis", r459.r456, "analyze"),
    ("callsite_analysis", r459.r457, "analyze"),
    ("bootstrap_aggregation", r459.r458_audit, "aggregate"),
)

class Refused(RuntimeError):
    pass


def need(condition: bool, code: str) -> None:
    if not condition:
        raise Refused(code)


def category(path: Path) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".class": "class", ".java": "source", ".jar": "jar",
    }.get(suffix, "other")


def measure(inspect_function, original: Path) -> tuple[dict, dict]:
    reads = Counter()
    read_bytes = Counter()
    stage_ns = Counter()
    stage_calls = Counter()
    original_reader = scanner.read_bounded_regular

    def counted_reader(path, *args, **kwargs):
        data = original_reader(path, *args, **kwargs)
        if data is not None:
            label = category(path)
            reads[label] += 1
            read_bytes[label] += len(data)
        return data

    gc.collect()
    with ExitStack() as scope:
        scope.enter_context(patch.object(
            scanner, "read_bounded_regular", side_effect=counted_reader))
        for label, module, method in STAGES:
            actual = getattr(module, method)

            def timed(*args, _actual=actual, _label=label, **kwargs):
                start = time.perf_counter_ns()
                try:
                    return _actual(*args, **kwargs)
                finally:
                    stage_ns[_label] += time.perf_counter_ns() - start
                    stage_calls[_label] += 1

            scope.enter_context(patch.object(module, method, side_effect=timed))

        tracemalloc.start()
        wall_start = time.perf_counter_ns()
        cpu_start = time.process_time_ns()
        try:
            summary, _private = inspect_function(original)
        finally:
            elapsed = time.perf_counter_ns() - wall_start
            cpu = time.process_time_ns() - cpu_start
            _current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

    return summary, {
        "wall_ms": round(elapsed / 1_000_000, 3),
        "cpu_ms": round(cpu / 1_000_000, 3),
        "python_peak_traced_bytes": peak,
        "instrumented_read_calls": sum(reads.values()),
        "instrumented_read_bytes": sum(read_bytes.values()),
        "read_calls_by_kind": {kind: reads[kind]
                              for kind in ("source", "class", "jar", "other")},
        "read_bytes_by_kind": {kind: read_bytes[kind]
                              for kind in ("source", "class", "jar", "other")},
        "inclusive_stage_ms": {label: round(stage_ns[label] / 1_000_000, 3)
                               for label, _, _ in STAGES},
        "stage_calls": {label: stage_calls[label] for label, _, _ in STAGES},
    }


PARITY = (
    ("original_v309_class_count", "original_v309_class_count"),
    ("original_v309_resource_count", "original_v309_resource_count"),
    ("isolated_r421_java_sources", "isolated_r421_java_sources"),
    ("isolated_r421_compiled_classfiles", "isolated_r421_compiled_classes"),
    ("invokedynamic_bytecode_sites", "R458_invokedynamic_bytecode_sites"),
    ("constant_dynamic_ldc_bytecode_sites", "R458_constant_dynamic_ldc_sites"),
    ("bootstrap_method_handle_arguments_at_instruction_sites",
     "R458_bootstrap_method_handle_argument_sites"),
)


def verify_parity(legacy: dict, consolidated: dict) -> None:
    for old, new in PARITY:
        need(old in legacy and new in consolidated and legacy[old] == consolidated[new],
             "R460_SHARED_OUTPUT_PARITY_FAILURE")


def summarized(samples: list[dict]) -> dict:
    def med(key):
        return median(row[key] for row in samples)

    kinds = ("source", "class", "jar", "other")
    stages = tuple(item[0] for item in STAGES)
    return {
        "median_wall_ms": med("wall_ms"),
        "median_cpu_ms": med("cpu_ms"),
        "median_python_peak_traced_bytes": med("python_peak_traced_bytes"),
        "median_instrumented_read_calls": med("instrumented_read_calls"),
        "median_instrumented_read_bytes": med("instrumented_read_bytes"),
        "median_read_calls_by_kind": {
            name: median(row["read_calls_by_kind"][name] for row in samples)
            for name in kinds},
        "median_read_bytes_by_kind": {
            name: median(row["read_bytes_by_kind"][name] for row in samples)
            for name in kinds},
        "median_inclusive_stage_ms": {
            name: median(row["inclusive_stage_ms"][name] for row in samples)
            for name in stages},
        "median_stage_calls": {
            name: median(row["stage_calls"][name] for row in samples)
            for name in stages},
    }


def compare(original: Path, *, pairs: int = 2, synthetic: bool = False) -> dict:
    need(type(pairs) is int and 1 <= pairs <= MAX_PAIRS,
         "R460_PAIR_COUNT_OUT_OF_RANGE")
    measurements: dict[str, list[dict]] = {
        "legacy_R458": [], "consolidated_R459": []}
    for index in range(pairs):
        # Extra observations are outside timed regions, proving the paired
        # measurements used one stable owner current-state inventory.
        before, _ = r446.observe()
        sequence = (
            (("legacy_R458", r458.inspect),
             ("consolidated_R459", r459.inspect))
            if index % 2 == 0 else
            (("consolidated_R459", r459.inspect),
             ("legacy_R458", r458.inspect))
        )
        summaries = {}
        for label, function in sequence:
            summaries[label], observation = measure(function, original)
            measurements[label].append(observation)
        after, _ = r446.observe()
        need(before == after, "R460_PAIRED_FULL_SHA_INPUT_CHANGED")
        # Both audits independently SHA-check this original; an additional
        # end-of-pair verification protects the comparison boundary.
        r447.read_pinned_original(original)
        verify_parity(summaries["legacy_R458"], summaries["consolidated_R459"])

    a = summarized(measurements["legacy_R458"])
    b = summarized(measurements["consolidated_R459"])
    need(a["median_wall_ms"] > 0 and b["median_wall_ms"] > 0,
         "R460_ZERO_MEASUREMENT")
    need(b["median_read_calls_by_kind"]["class"] == 
         3 * summaries["consolidated_R459"]["isolated_r421_compiled_classes"],
         "R460_CONSOLIDATED_CLASS_READ_COUNT_DRIFT")
    return {
        "schema": SCHEMA,
        "status": "R460_PAIRED_STATIC_AUDIT_BENCHMARK_UNAPPROVED",
        "fixture": "fabricated_synthetic" if synthetic else "owner_private_unapproved",
        "pairs": pairs,
        "order": "R458-R459, then alternate for successive pairs",
        "legacy_R458": a,
        "consolidated_R459": b,
        "observed_wall_speedup_R458_over_R459":
            round(a["median_wall_ms"] / b["median_wall_ms"], 3),
        "observed_instrumented_read_reduction_fraction":
            round(1 - b["median_instrumented_read_bytes"] /
                  max(1, a["median_instrumented_read_bytes"]), 5),
        "pair_sha_inventories_consistent": True,
        "shared_output_parity_passed": True,
        "instrumentation": "scanner.read_bounded_regular + inclusive stage timers + tracemalloc",
        "instrumentation_overhead_present": True,
        "all_filesystem_read_apis_counted": False,
        "allocation_peak_includes_instrumentation": True,
        "synthetic_speedup_generalizes_to_owner": False,
        "private_paths_or_names_exported": False,
        "source_or_jar_bytes_exported": False,
        "historical_R421_manifest_approved": False,
        "compilation_authorized": False,
        "merge_authorized": False,
        "release_authorized": False,
        "client_executed": False,
    }


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--original-v309-jar", type=Path, required=True)
    cli.add_argument("--pairs", type=int, choices=range(1, MAX_PAIRS + 1),
                     default=2)
    args = cli.parse_args(argv)
    try:
        print(json.dumps(compare(args.original_v309_jar, pairs=args.pairs),
                         sort_keys=True, separators=(",", ":")))
        return 0
    except Exception:
        # No paths, filenames, user-defined exception text or stack traces
        # appear in normal CLI failure output.
        print(json.dumps({
            "status": "R460_PAIRED_BENCHMARK_REFUSED",
            "reason": "R460_PRIVATE_INPUT_OR_PARITY_REFUSED",
            "merge_authorized": False, "release_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
