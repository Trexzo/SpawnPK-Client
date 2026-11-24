#!/usr/bin/env python3
"""R464 SHA-gated pairwise hierarchy-memo audit profiling (read only).

Compares current R463 (independent R455/R456 ancestry graph work) with R464
(one class-graph index shared by R455/R456), using the same owner-isolated
SHA-pinned current-source, class, dependency and original-JAR gates.
Public CI uses fabricated data. No path, filename, source/JAR/class bytes,
per-file hash, player history or private worklist is exported.
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
from tools.r462 import shared_instruction_stream as instruction
from tools.r463 import reuse_validated_metadata as metadata
from tools.r464 import shared_hierarchy as hierarchy

SCHEMA = "SpawnPK-R464-hierarchy-memo-UNAPPROVED-v1"


class Refused(RuntimeError):
    pass


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    return r459.inspect(
        original, companion,
        shared_pool_factory=cp.decode,
        shared_instruction_factory=instruction.Index,
        descriptor_cache_factory=metadata.DescriptorShapes,
        reuse_opcode_summary=True,
        hierarchy_factory=hierarchy.Index)


def compare(original: Path, *, pairs: int = 2,
            synthetic: bool = False) -> dict:
    if type(pairs) is not int or not 1 <= pairs <= 4:
        raise Refused("R464_PAIR_COUNT_OUT_OF_RANGE")
    samples = {"R463_independent_hierarchy": [],
               "R464_shared_hierarchy": []}
    stats = []
    for iteration in range(pairs):
        before, _ = r446.observe()
        instances = []

        def capture(rebuilt, selected):
            index = hierarchy.Index(rebuilt, selected)
            instances.append(index)
            return index

        def old(path):
            return r459.inspect(
                path, shared_pool_factory=cp.decode,
                shared_instruction_factory=instruction.Index,
                descriptor_cache_factory=metadata.DescriptorShapes,
                reuse_opcode_summary=True)

        def new(path):
            return r459.inspect(
                path, shared_pool_factory=cp.decode,
                shared_instruction_factory=instruction.Index,
                descriptor_cache_factory=metadata.DescriptorShapes,
                reuse_opcode_summary=True,
                hierarchy_factory=capture)

        order = (("R463_independent_hierarchy", old),
                 ("R464_shared_hierarchy", new))
        if iteration % 2:
            order = tuple(reversed(order))
        reports = {}
        for label, fn in order:
            reports[label], measurement = r460.measure(fn, original)
            samples[label].append(measurement)
        after, _ = r446.observe()
        if before != after:
            raise Refused("R464_PAIRED_FULL_SHA_INVENTORY_CHANGED")
        r447.read_pinned_original(original)
        if reports["R463_independent_hierarchy"] != reports[
                "R464_shared_hierarchy"]:
            raise Refused("R464_AGGREGATE_REPORT_PARITY_FAILURE")
        if len(instances) != 1 or instances[0].admissions != 2:
            raise Refused("R464_WRONG_HIERARCHY_INDEX_LIFETIME")
        original_reads = samples["R463_independent_hierarchy"][-1]["read_calls_by_kind"]
        optimized_reads = samples["R464_shared_hierarchy"][-1]["read_calls_by_kind"]
        if original_reads != optimized_reads:
            raise Refused("R464_BOUNDED_FILE_READ_COUNT_DRIFT")
        entry = instances[0]
        stats.append({
            "ancestry_hits": entry.ancestry_hits,
            "ancestry_misses": entry.ancestry_misses,
            "resolution_hits": entry.resolution_hits,
            "resolution_misses": entry.resolution_misses,
        })

    old = r460.summarized(samples["R463_independent_hierarchy"])
    new = r460.summarized(samples["R464_shared_hierarchy"])
    if old["median_wall_ms"] <= 0 or new["median_wall_ms"] <= 0:
        raise Refused("R464_INVALID_BENCHMARK_MEASUREMENT")
    return {
        "schema": SCHEMA,
        "status": "R464_SHARED_HIERARCHY_BENCHMARK_UNAPPROVED",
        "fixture": "fabricated_synthetic" if synthetic else "owner_private_unapproved",
        "pairs": pairs,
        "order_alternated": True,
        "R463_independent_hierarchy": old,
        "R464_shared_hierarchy": new,
        "observed_wall_speedup_R463_over_R464":
            round(old["median_wall_ms"] / new["median_wall_ms"], 3),
        "median_hierarchy_cache_counters": {
            name: median(item[name] for item in stats) for name in stats[0]
        },
        "shared_index_admissions_per_audit": 2,
        "rebuilt_only_R454_independent_graph_preserved": True,
        "public_output_parity": True,
        "full_sha_inventory_consistent": True,
        "file_read_count_parity": True,
        "legacy_independent_analyzers_available": True,
        "instrumentation_overhead_present": True,
        "synthetic_speedup_generalizes_to_owner": False,
        "private_names_paths_or_bytes_exported": False,
        "historical_R421_manifest_approved": False,
        "client_executed": False,
        "compilation_authorized": False,
        "merge_authorized": False,
        "release_authorized": False,
    }


def main(argv=None):
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
            "status": "R464_HIERARCHY_BENCHMARK_REFUSED",
            "reason": "R464_PRIVATE_INPUT_OR_PARITY_REFUSED",
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
