#!/usr/bin/env python3
"""R463 read-only paired R462 vs witness/descriptor metadata reuse benchmark.

The SHA-gated R459 coordinator remains the source of class/source/dependency
integrity. R463 opt-in eliminates the redundant second R456 classification
from R457 and caches independently validated method shapes. Only aggregate
metrics go to stdout. Never executes the client or writes private artifacts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r446 import observe_owner_private_inventory as r446
from tools.r447 import audit_original_class_asset_coverage as r447
from tools.r459 import audit_consolidated_inspection as r459
from tools.r460 import benchmark_inspection as r460
from tools.r461 import shared_constant_pool as cp
from tools.r462 import shared_instruction_stream as code
from tools.r463 import reuse_validated_metadata as meta

SCHEMA = "SpawnPK-R463-shared-metadata-UNAPPROVED-v1"


class Refused(RuntimeError):
    pass


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    return r459.inspect(
        original, companion, shared_pool_factory=cp.decode,
        shared_instruction_factory=code.Index,
        descriptor_cache_factory=meta.DescriptorShapes,
        reuse_opcode_summary=True)


def compare(original: Path, *, pairs: int = 2,
            synthetic: bool = False) -> dict:
    if type(pairs) is not int or pairs < 1 or pairs > 4:
        raise Refused("R463_PAIR_COUNT_OUT_OF_RANGE")
    captures = {"R462_repeated_metadata": [], "R463_reused_metadata": []}
    descriptor_totals = []

    for iteration in range(pairs):
        before, _ = r446.observe()
        caches = []

        def create_shape_cache():
            cache = meta.DescriptorShapes()
            caches.append(cache)
            return cache

        def old(path):
            return r459.inspect(
                path, shared_pool_factory=cp.decode,
                shared_instruction_factory=code.Index)

        def new(path):
            return r459.inspect(
                path, shared_pool_factory=cp.decode,
                shared_instruction_factory=code.Index,
                descriptor_cache_factory=create_shape_cache,
                reuse_opcode_summary=True)

        order = (("R462_repeated_metadata", old),
                 ("R463_reused_metadata", new))
        if iteration % 2:
            order = tuple(reversed(order))
        summaries = {}
        for label, runner in order:
            summaries[label], sampled = r460.measure(runner, original)
            captures[label].append(sampled)

        after, _ = r446.observe()
        if before != after:
            raise Refused("R463_PAIRED_FULL_SHA_INPUT_CHANGED")
        r447.read_pinned_original(original)
        if summaries["R462_repeated_metadata"] != summaries["R463_reused_metadata"]:
            raise Refused("R463_AGGREGATE_OUTPUT_PARITY_FAILURE")
        if len(caches) != 1:
            raise Refused("R463_DESCRIPTOR_INDEX_NOT_SCAN_LOCAL")
        old_metrics = captures["R462_repeated_metadata"][-1]
        new_metrics = captures["R463_reused_metadata"][-1]
        if old_metrics["read_calls_by_kind"] != new_metrics["read_calls_by_kind"]:
            raise Refused("R463_FILE_READ_COUNT_DRIFT")
        if (old_metrics["stage_calls"]["opcode_analysis"] != 2
                or new_metrics["stage_calls"]["opcode_analysis"] != 1):
            raise Refused("R463_DUPLICATED_R456_AGGREGATE_NOT_ELIMINATED")
        cache = caches[0]
        descriptor_totals.append({
            "resource_shape_hits": cache.resource_hits,
            "resource_shape_misses": cache.resource_misses,
            "callsite_shape_hits": cache.callsite_hits,
            "callsite_shape_misses": cache.callsite_misses,
        })

    previous = r460.summarized(captures["R462_repeated_metadata"])
    optimized = r460.summarized(captures["R463_reused_metadata"])
    if previous["median_wall_ms"] <= 0 or optimized["median_wall_ms"] <= 0:
        raise Refused("R463_INVALID_TIMING")
    return {
        "schema": SCHEMA,
        "status": "R463_SHARED_STATIC_METADATA_BENCHMARK_UNAPPROVED",
        "fixture": "fabricated_synthetic" if synthetic else "owner_private_unapproved",
        "pairs": pairs,
        "order_alternated": True,
        "R462_repeated_metadata": previous,
        "R463_reused_metadata": optimized,
        "observed_wall_speedup_R462_over_R463":
            round(previous["median_wall_ms"] / optimized["median_wall_ms"], 3),
        "median_descriptor_cache": {
            key: median(row[key] for row in descriptor_totals)
            for key in descriptor_totals[0]
        },
        "R456_legacy_calls_per_audit": 2,
        "R456_optimized_calls_per_audit": 1,
        "full_SHA_inventories_consistent": True,
        "aggregate_output_parity": True,
        "bounded_file_reads_identical": True,
        "legacy_default_R457_independent_analysis_preserved": True,
        "instrumentation_overhead_present": True,
        "synthetic_speedup_generalizes_to_owner": False,
        "private_names_or_source_bytes_exported": False,
        "historical_R421_independent_approval": False,
        "client_executed": False,
        "compilation_authorized": False,
        "merge_authorized": False,
        "release_authorized": False,
    }


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--original-v309-jar", type=Path, required=True)
    cli.add_argument("--pairs", type=int, choices=range(1, 5), default=2)
    args = cli.parse_args(argv)
    try:
        print(json.dumps(compare(args.original_v309_jar, pairs=args.pairs),
                         sort_keys=True, separators=(",", ":")))
        return 0
    except Exception:
        print(json.dumps({
            "status": "R463_SHARED_METADATA_BENCHMARK_REFUSED",
            "reason": "R463_PRIVATE_INPUT_OR_PARITY_REFUSED",
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
