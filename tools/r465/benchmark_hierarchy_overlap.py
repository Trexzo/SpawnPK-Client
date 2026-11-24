#!/usr/bin/env python3
"""R465 deterministic, hierarchy-heavy, PUBLIC SYNTHETIC microbenchmark.

Measures R455 dependency accessibility + R456 bytecode member classification
on generated in-memory R453 records with many overlapping inherited-member
targets. R464's shared graph cache is compared against the unchanged R463
independent path using identical immutable inputs and alternating run order.

Never opens owner sources, original game JARs, user data or private worklists.
The standalone benchmark makes NO claims about actual SpawnPK source coverage,
JVM loadability, production latency, or full owner audit performance.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
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

from tools.r453 import classfile_member_reference as records
from tools.r454 import member_ancestry_evidence as inheritance
from tools.r455 import dependency_member_access as dependencies
from tools.r456 import member_opcode_evidence as opcodes
from tools.r464 import shared_hierarchy as shared

SCHEMA = "SpawnPK-R465-synthetic-hierarchy-overlap-benchmark-UNAPPROVED-v1"
MAX_OWNERS = 256
MAX_METHODS = 16
MAX_PAIRS = 4
DEFAULT_CASES = ((24, 8, True), (96, 8, True), (192, 8, True),
                 (96, 8, False))


class Refused(RuntimeError):
    pass


@dataclass(frozen=True)
class Workload:
    rebuilt: dict[str, records.ClassMembers]
    selected: dict[str, records.ClassMembers]
    sites: tuple[opcodes.Site, ...]
    owners: int
    signatures: int
    overlap: bool


def record(name: str, superclass: str | None, *,
           methods=(), references=(), access=()):
    return records.ClassMembers(
        name, superclass, frozenset(), frozenset(methods),
        frozenset(references), frozenset(), (), tuple(access), 0x0001)


def fabricated(owners: int, signatures: int, overlap: bool = True) -> Workload:
    if (type(owners) is not int or type(signatures) is not int
            or type(overlap) is not bool or not 1 <= owners <= MAX_OWNERS
            or not 1 <= signatures <= MAX_METHODS):
        raise Refused("R465_SYNTHETIC_WORKLOAD_SIZE_REFUSED")
    root = "fixture/deps/Root.class"
    members = [(f"method{i}", "()V") for i in range(signatures)]
    # Static, private and public declarations produce distinct static
    # classification outcomes rather than an easy all-public happy path.
    access = [
        (name, desc, 0x0002 if i == signatures - 1 else
         (0x0009 if i == signatures - 2 else 0x0001))
        for i, (name, desc) in enumerate(members)
    ]
    selected = {
        root: record(root, "java/lang/Object.class",
                     methods=members, access=access)
    }
    layers = [f"fixture/deps/Layer{i}.class" for i in range(4)]
    for layer in layers:
        selected[layer] = record(layer, root)
    rebuilt = {}
    sites = []
    for i in range(owners):
        owner = f"fixture/deps/Owner{i:04d}.class"
        caller = f"fixture/rebuilt/Caller{i:04d}.class"
        targets = tuple(records.Member(owner, name, desc, "method")
                        for name, desc in members)
        selected[owner] = record(owner, layers[i % len(layers)])
        rebuilt[caller] = record(
            caller, "java/lang/Object.class", references=targets)
        if overlap:
            sites.extend(
                opcodes.Site(caller, "simulate()V", j * 3,
                             "invokevirtual", False, target)
                for j, target in enumerate(targets)
            )
    return Workload(rebuilt, selected, tuple(sites), owners,
                    signatures, overlap)


def analysis(workload: Workload, *, reuse: bool, index_factory=shared.Index):
    if reuse:
        index = index_factory(workload.rebuilt, workload.selected)
        options = {"shared_hierarchy": index}
    else:
        index = None
        options = {}
    dependency = dependencies.analyze(
        workload.rebuilt, workload.selected, set(), set(), **options)
    opcode = opcodes.analyze(
        workload.rebuilt, workload.selected, list(workload.sites), 0,
        **options)
    return (dependency, opcode), index


def counted(workload: Workload, reuse: bool):
    """Count real underlying R454 ancestry and lookup calls; not timed."""
    ancestors = [0]
    resolutions = [0]
    original_ancestry = inheritance.ancestry
    original_lookup = inheritance.lookup

    def traced_ancestry(*args, **kwargs):
        ancestors[0] += 1
        return original_ancestry(*args, **kwargs)

    def traced_lookup(*args, **kwargs):
        resolutions[0] += 1
        return original_lookup(*args, **kwargs)

    with patch.object(inheritance, "ancestry",
                      side_effect=traced_ancestry), patch.object(
                      inheritance, "lookup", side_effect=traced_lookup):
        result, index = analysis(workload, reuse=reuse)
    return result, index, {
        "underlying_ancestry_traversals": ancestors[0],
        "underlying_member_resolutions": resolutions[0],
    }


def measured(workload: Workload, reuse: bool):
    """Instrumented in-memory-only paired measurement, no disk reads."""
    gc.collect()
    tracemalloc.start()
    wall_start = time.perf_counter_ns()
    cpu_start = time.process_time_ns()
    try:
        result, _index = analysis(workload, reuse=reuse)
    finally:
        cpu = time.process_time_ns() - cpu_start
        wall = time.perf_counter_ns() - wall_start
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return result, {
        "wall_ms": round(wall / 1_000_000, 4),
        "cpu_ms": round(cpu / 1_000_000, 4),
        "peak_traced_python_bytes": peak,
    }


def compare(*, pairs: int = 2, cases=DEFAULT_CASES) -> dict:
    if type(pairs) is not int or not 1 <= pairs <= MAX_PAIRS:
        raise Refused("R465_PAIR_COUNT_REFUSED")
    if (type(cases) not in (list, tuple) or not cases
            or len(cases) > 8):
        raise Refused("R465_WORKLOAD_SET_REFUSED")
    findings = []
    for owners, signatures, overlap in cases:
        workload = fabricated(owners, signatures, overlap)
        prior, _, prior_counts = counted(workload, reuse=False)
        shared_result, witness, shared_counts = counted(workload, reuse=True)
        if prior != shared_result:
            raise Refused("R465_COMPLETE_PUBLIC_PRIVATE_OUTPUT_DISAGREEMENT")
        expected_old_ancestry = owners * (2 if overlap else 1)
        expected_old_resolution = owners * signatures * (
            2 if overlap else 1)
        if (prior_counts["underlying_ancestry_traversals"] !=
                expected_old_ancestry
                or prior_counts["underlying_member_resolutions"] !=
                expected_old_resolution
                or shared_counts["underlying_ancestry_traversals"] != owners
                or shared_counts["underlying_member_resolutions"] !=
                owners * signatures):
            raise Refused("R465_HIERARCHY_WORKLOAD_COUNTER_DRIFT")
        if (witness.admissions != 2
                or witness.ancestry_hits != (owners if overlap else 0)
                or witness.resolution_hits != (
                    owners * signatures if overlap else 0)):
            raise Refused("R465_HIERARCHY_CACHE_HIT_DRIFT")

        samples = {"independent": [], "shared": []}
        for iteration in range(pairs):
            order = (("independent", False), ("shared", True))
            if iteration % 2:
                order = tuple(reversed(order))
            matched = {}
            for label, reused in order:
                matched[label], sample = measured(workload, reused)
                samples[label].append(sample)
            if matched["independent"] != matched["shared"]:
                raise Refused("R465_PAIRED_PUBLIC_PRIVATE_OUTPUT_DISAGREEMENT")
        old_wall = median(row["wall_ms"] for row in samples["independent"])
        new_wall = median(row["wall_ms"] for row in samples["shared"])
        if old_wall <= 0 or new_wall <= 0:
            raise Refused("R465_INVALID_TIMINGS")

        findings.append({
            "reconstructed_caller_records": owners,
            "dependency_class_records": len(workload.selected),
            "unique_member_signatures_per_owner": signatures,
            "member_reference_count": owners * signatures,
            "opcode_site_count": len(workload.sites),
            "overlap_between_R455_and_R456": overlap,
            "independent_R454_call_counts": prior_counts,
            "shared_R454_call_counts": shared_counts,
            "shared_ancestry_cache_hits": witness.ancestry_hits,
            "shared_resolution_cache_hits": witness.resolution_hits,
            "median_independent_wall_ms": old_wall,
            "median_shared_wall_ms": new_wall,
            "median_independent_cpu_ms": median(
                row["cpu_ms"] for row in samples["independent"]),
            "median_shared_cpu_ms": median(
                row["cpu_ms"] for row in samples["shared"]),
            "median_independent_peak_python_bytes": median(
                row["peak_traced_python_bytes"]
                for row in samples["independent"]),
            "median_shared_peak_python_bytes": median(
                row["peak_traced_python_bytes"]
                for row in samples["shared"]),
            "observed_wall_speedup": round(old_wall / new_wall, 3),
            "entire_public_and_private_output_equal": True,
            "synthetic_data_only": True,
        })

    return {
        "schema": SCHEMA,
        "status": "R465_SYNTHETIC_IN_MEMORY_HIERARCHY_ONLY",
        "pairs_per_workload": pairs,
        "order_alternated": True,
        "workloads": findings,
        "strict_complete_output_parity_passed": True,
        "scope": "R455_and_R456_synthetic_in_memory_hierarchy_only",
        "SHA_file_inventory_measured": False,
        "filesystem_bounded_reads_measured": False,
        "owner_client_benchmarked": False,
        "original_v309_jar_read": False,
        "actual_gameplay_latency_measured": False,
        "real_client_speedup_established": False,
        "instrumentation_overhead_present": True,
        "private_names_paths_hashes_or_bytes_exported": False,
        "historical_R421_manifest_approved": False,
        "compilation_authorized": False,
        "merge_authorized": False,
        "release_authorized": False,
    }


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--pairs", type=int, choices=range(1, MAX_PAIRS + 1),
                     default=2)
    cli.add_argument("--sizes", nargs="*", type=int, default=None,
                     help="optional positive owner counts; 8 signatures each")
    args = cli.parse_args(argv)
    try:
        cases = (tuple((n, 8, True) for n in args.sizes)
                 if args.sizes is not None else DEFAULT_CASES)
        print(json.dumps(compare(pairs=args.pairs, cases=cases),
                         sort_keys=True, separators=(",", ":")))
        return 0
    except Exception:
        print(json.dumps({
            "status": "R465_HIERARCHY_SYNTHETIC_BENCHMARK_REFUSED",
            "reason": "R465_SIZE_PARITY_OR_BUDGET_REFUSED",
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
