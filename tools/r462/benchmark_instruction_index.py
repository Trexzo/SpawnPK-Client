#!/usr/bin/env python3
"""R462 compare independent R461 vs shared JVM instruction index.

Alternative read-only static evidence path; preserves R459's full source,
class, dependency and pinned-original SHA safeguards and owner isolation.
Public synthetic fixtures do not establish real owner-PC performance.
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
from tools.r462 import shared_instruction_stream as bytecode

SCHEMA = "SpawnPK-R462-shared-instruction-index-UNAPPROVED-v1"


class Refused(RuntimeError):
    pass


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    """Use R461's shared CP plus R462 class-local bytecode index."""
    return r459.inspect(
        original, companion, shared_pool_factory=cp.decode,
        shared_instruction_factory=bytecode.Index)


def compare(original: Path, *, pairs: int = 2,
            synthetic: bool = False) -> dict:
    if type(pairs) is not int or not 1 <= pairs <= 4:
        raise Refused("R462_PAIR_COUNT_OUT_OF_RANGE")
    captures = {"R461_independent_instructions": [],
                "R462_shared_instructions": []}
    index_counts = []
    hits = []
    misses = []

    for iteration in range(pairs):
        before, _ = r446.observe()
        indices = []

        def create_index():
            index = bytecode.Index()
            indices.append(index)
            return index

        def independent(path: Path):
            return r459.inspect(path, shared_pool_factory=cp.decode)

        def reused(path: Path):
            return r459.inspect(
                path, shared_pool_factory=cp.decode,
                shared_instruction_factory=create_index)

        order = (("R461_independent_instructions", independent),
                 ("R462_shared_instructions", reused))
        if iteration % 2:
            order = tuple(reversed(order))
        reports = {}
        for label, runner in order:
            reports[label], metrics = r460.measure(runner, original)
            captures[label].append(metrics)
        after, _ = r446.observe()
        if before != after:
            raise Refused("R462_FULL_INPUT_SHA_CHANGED_ACROSS_PAIR")
        r447.read_pinned_original(original)
        if reports["R461_independent_instructions"] != reports[
                "R462_shared_instructions"]:
            raise Refused("R462_INDEPENDENT_OUTPUT_OR_WORKLIST_DISAGREEMENT")
        class_count = reports["R461_independent_instructions"][
            "isolated_r421_compiled_classes"]
        if len(indices) != class_count:
            raise Refused("R462_ONE_INDEX_PER_CLASS_REQUIRED")
        if captures["R461_independent_instructions"][-1][
                "read_calls_by_kind"] != captures[
                "R462_shared_instructions"][-1]["read_calls_by_kind"]:
            raise Refused("R462_FILE_READ_COUNT_DRIFT")
        index_counts.append(len(indices))
        hits.append(sum(item.hits for item in indices))
        misses.append(sum(item.misses for item in indices))

    old = r460.summarized(captures["R461_independent_instructions"])
    new = r460.summarized(captures["R462_shared_instructions"])
    if old["median_wall_ms"] <= 0 or new["median_wall_ms"] <= 0:
        raise Refused("R462_ZERO_ELAPSED_MEASUREMENT")

    return {
        "schema": SCHEMA,
        "status": "R462_SHARED_INSTRUCTION_BENCHMARK_UNAPPROVED",
        "fixture": "fabricated_synthetic" if synthetic else "owner_private_unapproved",
        "pairs": pairs,
        "order_alternated": True,
        "R461_independent_instructions": old,
        "R462_shared_instructions": new,
        "observed_wall_speedup_R461_over_R462":
            round(old["median_wall_ms"] / new["median_wall_ms"], 3),
        "median_ephemeral_class_indices": median(index_counts),
        "median_instruction_decode_misses": median(misses),
        "median_instruction_cache_hits": median(hits),
        "full_SHA_input_consistency": True,
        "aggregate_output_parity": True,
        "file_read_count_parity": True,
        "default_legacy_instruction_decoders_available": True,
        "instrumentation_overhead_present": True,
        "synthetic_speedup_generalizes_to_owner": False,
        "private_paths_names_or_bytes_exported": False,
        "source_or_jar_bytes_exported": False,
        "historical_R421_full_inventory_approved": False,
        "compilation_authorized": False,
        "client_executed": False,
        "merge_authorized": False,
        "release_authorized": False,
    }


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--original-v309-jar", type=Path, required=True)
    cli.add_argument("--pairs", type=int, choices=range(1, 5), default=2)
    args = cli.parse_args(argv)
    try:
        print(json.dumps(
            compare(args.original_v309_jar, pairs=args.pairs),
            sort_keys=True, separators=(",", ":")))
        return 0
    except Exception:
        print(json.dumps({
            "status": "R462_SHARED_INSTRUCTION_BENCHMARK_REFUSED",
            "reason": "R462_PRIVATE_INPUT_OR_PARITY_REFUSED",
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
