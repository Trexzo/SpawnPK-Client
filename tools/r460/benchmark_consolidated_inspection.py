#!/usr/bin/env python3
"""R460 reproducible read-only performance comparison: legacy R458 vs R459.

Measures exactly the same original-v309 SHA-gated R421 current-state inputs.
Legacy = R458's nested R447..R458 inspection; fused = R459's
single-class-evidence-read coordinator. No JAR/class execution or runtime
modification. Timings are explicitly *synthetic* when --synthetic is used.

Default output is aggregate-only JSON: timing, file-read counts, bytes and
tracemalloc Python peak allocations. No source/class/JAR bytes or private
class/path names, credential, history, or source hash is printed.

Owner mode never writes files. Synthetic mode creates a temporary invented
fixture using the existing test setup and cleans it through unittest cleanup.
R415/R417 journal/persistence state and runtime client are never accessed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter_ns
import tracemalloc
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r444 import scan_owner_r421_artifacts as scanner
from tools.r446 import observe_owner_private_inventory as r446
from tools.r447 import audit_original_class_asset_coverage as r447
from tools.r458 import audit_bootstrap_evidence as legacy_audit
from tools.r459 import audit_consolidated_inspection as consolidated_audit

SCHEMA = "SpawnPK-R460-audit-benchmark-UNAPPROVED-v1"
MAX_TIMED_ITERATIONS = 12
MAX_WARMUPS = 3
MODES = ("legacy_R458_nested", "consolidated_R459")
FIELDS = (
    ("original_v309_class_count", "original_v309_class_count"),
    ("original_v309_resource_count", "original_v309_resource_count"),
    ("isolated_r421_compiled_classfiles", "isolated_r421_compiled_classes"),
    ("isolated_r421_java_sources", "isolated_r421_java_sources"),
    ("invokedynamic_bytecode_sites", "R458_invokedynamic_bytecode_sites"),
    ("constant_dynamic_ldc_bytecode_sites",
     "R458_constant_dynamic_ldc_sites"),
)
CATEGORIES = (
    "rebuilt_class", "java_source", "preferred_dependency",
    "alternate_dependency", "original_v309", "other",
)


class Refused(RuntimeError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise Refused(code)


def check_parity(legacy: dict, consolidated: dict) -> None:
    """Every shared safety-critical synthetic/real evidence count must agree."""
    need(type(legacy) is dict and type(consolidated) is dict,
         "R460_INVALID_LEGACY_OR_FUSED_REPORT")
    for old_field, new_field in FIELDS:
        need(old_field in legacy and new_field in consolidated
             and legacy[old_field] == consolidated[new_field],
             "R460_COMPARISON_COMMON_COUNT_DRIFT")
    for report in (legacy, consolidated):
        need(report.get("historical_R421_full_inventory_independently_approved")
             is False and report.get("merge_authorized") is False
             and report.get("release_authorized") is False,
             "R460_UNAPPROVED_CUSTODY_OR_RELEASE_FLAG_CHANGED")
    need(legacy.get("original_v309_exact_sha_verified") is True
         and consolidated.get("original_v309_pinned_sha_matched") is True,
         "R460_ORIGINAL_PIN_NOT_VERIFIED")


def _category(path: Path, roots: tuple[Path, Path, Path, Path, Path],
              original: Path) -> str:
    _temp, src, compiled, preferred, alternate = roots
    p = Path(path)
    try:
        p.relative_to(compiled)
        return "rebuilt_class"
    except ValueError:
        pass
    try:
        p.relative_to(src)
        return "java_source"
    except ValueError:
        pass
    if p == preferred:
        return "preferred_dependency"
    if p == alternate:
        return "alternate_dependency"
    if p == original:
        return "original_v309"
    return "other"


def read_profile(fn, original: Path, roots) -> tuple[dict, dict]:
    """Instrument one complete audit, restoring the scanner even on error.

    All current code paths use the same imported nofollow bounded scanner.
    Unknown paths remain aggregate "other" instead of leaking filenames.
    """
    original_reader = scanner.read_bounded_regular
    reads = Counter()
    bytes_read = Counter()

    def record(path, *args, **kwargs):
        kind = _category(Path(path), roots, original)
        result = original_reader(path, *args, **kwargs)
        reads[kind] += 1
        if result is not None:
            bytes_read[kind] += len(result)
        return result

    with patch.object(scanner, "read_bounded_regular", side_effect=record):
        report, _details = fn(original)
    return report, {
        "bounded_file_read_calls": sum(reads.values()),
        "bounded_file_bytes_returned": sum(bytes_read.values()),
        "read_calls_by_kind": {k: reads[k] for k in CATEGORIES},
        "returned_bytes_by_kind": {k: bytes_read[k] for k in CATEGORIES},
    }


def peak_python_allocated_bytes(fn, original: Path) -> tuple[dict, int]:
    """tracemalloc is a separate pass: never distort wall-clock samples."""
    need(not tracemalloc.is_tracing(), "R460_EXTERNAL_TRACEMALLOC_ACTIVE")
    tracemalloc.start()
    try:
        report, _details = fn(original)
        _, peak = tracemalloc.get_traced_memory()
        return report, peak
    finally:
        tracemalloc.stop()


def _timing(fn, original: Path) -> tuple[dict, int]:
    start = perf_counter_ns()
    result, _details = fn(original)
    elapsed = perf_counter_ns() - start
    need(elapsed > 0, "R460_NONPOSITIVE_DURATION")
    return result, elapsed


def _summary_ns(values: list[int]) -> dict:
    need(values and all(type(x) is int and x > 0 for x in values),
         "R460_BAD_CLOCK_SAMPLES")
    return {
        "samples": len(values),
        "median_ms": round(statistics.median(values) / 1_000_000, 3),
        "min_ms": round(min(values) / 1_000_000, 3),
        "max_ms": round(max(values) / 1_000_000, 3),
    }


def benchmark(
    original: Path,
    *,
    synthetic: bool,
    iterations: int = 3,
    warmups: int = 1,
) -> dict:
    need(type(iterations) is int and 1 <= iterations <= MAX_TIMED_ITERATIONS
         and type(warmups) is int and 0 <= warmups <= MAX_WARMUPS,
         "R460_ITERATION_OR_WARMUP_LIMIT")
    need(isinstance(original, Path), "R460_INVALID_ORIGINAL_PATH")
    # These full R446 observations are outside timing instrumentation;
    # both *individual* audit functions still independently re-observe.
    before, _ = r446.observe()
    pinned = r447.read_pinned_original(original)
    need(sha256(pinned).hexdigest() == r447.ORIGINAL_SHA,
         "R460_ORIGINAL_SHA_NOT_PINNED")

    audits = {
        MODES[0]: legacy_audit.inspect,
        MODES[1]: consolidated_audit.inspect,
    }
    roots = r446.roots()
    warmup_reports = {}
    for _ in range(warmups):
        for mode, fn in audits.items():
            report, _detail = fn(original)
            warmup_reports[mode] = report
        check_parity(warmup_reports[MODES[0]], warmup_reports[MODES[1]])

    # Profile read patterns separately from benchmark timings; counting
    # overhead is not included in the recorded latency measurement.
    profiles = {}
    profiled = {}
    for mode, fn in audits.items():
        profiled[mode], profiles[mode] = read_profile(fn, original, roots)
    check_parity(profiled[MODES[0]], profiled[MODES[1]])

    timed: dict[str, list[int]] = {mode: [] for mode in MODES}
    for round_number in range(iterations):
        order = MODES if round_number % 2 == 0 else MODES[::-1]
        round_reports = {}
        for mode in order:
            report, elapsed = _timing(audits[mode], original)
            round_reports[mode] = report
            timed[mode].append(elapsed)
        check_parity(round_reports[MODES[0]], round_reports[MODES[1]])

    peaks = {}
    peak_reports = {}
    for mode, fn in audits.items():
        peak_reports[mode], peaks[mode] = peak_python_allocated_bytes(
            fn, original)
    check_parity(peak_reports[MODES[0]], peak_reports[MODES[1]])

    after, _ = r446.observe()
    need(after == before, "R460_COMPLETE_SOURCE_CLASS_DEPENDENCY_CHANGED")
    need(sha256(r447.read_pinned_original(original)).hexdigest() ==
         r447.ORIGINAL_SHA, "R460_ORIGINAL_JAR_CHANGED_DURING_BENCHMARK")
    old_ns = statistics.median(timed[MODES[0]])
    new_ns = statistics.median(timed[MODES[1]])
    old_calls = profiles[MODES[0]]["bounded_file_read_calls"]
    new_calls = profiles[MODES[1]]["bounded_file_read_calls"]
    old_bytes = profiles[MODES[0]]["bounded_file_bytes_returned"]
    new_bytes = profiles[MODES[1]]["bounded_file_bytes_returned"]
    need(new_ns > 0 and old_calls > 0 and old_bytes > 0,
         "R460_INVALID_BASELINE_MEASUREMENT")
    return {
        "schema": SCHEMA,
        "status": "R460_BENCHMARK_UNAPPROVED_SYNTHETIC" if synthetic else
                  "R460_OWNER_PRIVATE_STATIC_BENCHMARK_UNAPPROVED",
        "data_origin": "invented_public_fixture" if synthetic else
                       "SHA_pinned_owner_private_current_state",
        "benchmark_iterations_per_mode": iterations,
        "untimed_warmups_per_mode": warmups,
        "timing_is_exclusive_of_tracemalloc_and_io_instrumentation": True,
        "interleaved_order": "AB_BA_alternating",
        "legacy_R458_nested": {
            "wall_clock": _summary_ns(timed[MODES[0]]),
            "bounded_io": profiles[MODES[0]],
            "tracemalloc_peak_python_allocated_bytes": peaks[MODES[0]],
        },
        "consolidated_R459": {
            "wall_clock": _summary_ns(timed[MODES[1]]),
            "bounded_io": profiles[MODES[1]],
            "tracemalloc_peak_python_allocated_bytes": peaks[MODES[1]],
        },
        "observed_median_wall_clock_ratio_legacy_over_consolidated":
            round(old_ns / new_ns, 3),
        "observed_bounded_read_call_reduction_percent":
            round(100 * (old_calls - new_calls) / old_calls, 2),
        "observed_bounded_bytes_returned_reduction_percent":
            round(100 * (old_bytes - new_bytes) / old_bytes, 2),
        "common_original_rebuilt_and_dynamic_counts_matched": True,
        "complete_current_owner_source_class_dependency_SHA_unchanged": True,
        "tracemalloc_is_python_allocation_peak_not_process_RSS": True,
        "real_owner_performance_measured": not synthetic,
        "real_runtime_latency_or_FPS_measured": False,
        "jvm_or_client_executed": False,
        "historical_R421_full_inventory_independently_approved": False,
        "source_class_jar_bytes_or_private_names_exported": False,
        "persistence_history_or_deletion_journal_accessed": False,
        "merge_authorized": False,
        "release_authorized": False,
    }


def synthetic_benchmark(*, iterations=3, warmups=1) -> dict:
    """Use existing invented owner fixture; cleanup all temporary patches."""
    tests = ROOT / "tests"
    if str(tests) not in sys.path:
        sys.path.insert(0, str(tests))
    from test_v309_r458_bootstrap_callsite import R458OwnerInventedOffline

    fixture = R458OwnerInventedOffline(
        "test_31_all_inherited_pinned_owner_inputs_required")
    try:
        fixture.setUp()
        return benchmark(
            fixture.original_jar, synthetic=True, iterations=iterations,
            warmups=warmups)
    finally:
        fixture.doCleanups()


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    group = cli.add_mutually_exclusive_group(required=True)
    group.add_argument("--synthetic", action="store_true")
    group.add_argument("--owner-original-v309-jar", type=Path)
    cli.add_argument("--iterations", type=int, default=3)
    cli.add_argument("--warmups", type=int, default=1)
    args = cli.parse_args(argv)
    try:
        result = (synthetic_benchmark(
            iterations=args.iterations, warmups=args.warmups)
            if args.synthetic else
            benchmark(args.owner_original_v309_jar, synthetic=False,
                      iterations=args.iterations, warmups=args.warmups))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, r446.Refused, r447.Refused, legacy_audit.Refused,
            consolidated_audit.Refused, scanner.Refused,
            OSError, ValueError, TypeError, UnicodeError) as e:
        if isinstance(e, (Refused, r446.Refused, r447.Refused,
                          legacy_audit.Refused, consolidated_audit.Refused,
                          scanner.Refused)):
            reason = str(e)[:120]
        else:
            reason = "R460_BENCHMARK_INPUT_REFUSED"
        print(json.dumps({
            "status": "R460_BENCHMARK_REFUSED",
            "reason": reason,
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
