#!/usr/bin/env python3
"""R461 opt-in owner-private shared CP index + paired R459 oracle profiling.

Same SHA inventory and TOCTOU gates as R459. Only constant-pool tokenization
is reused; each original R450/R453/R458 parser still independently validates
the semantic information it consumes. Default R459 path remains unchanged.
No class/source/JAR bytes or private names are written or serialized.
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

SCHEMA = "SpawnPK-R461-shared-cp-index-UNAPPROVED-v1"


class Refused(RuntimeError):
    pass


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    """R459 exact audits, with one short-lived immutable CP index per class."""
    return r459.inspect(original, companion, shared_pool_factory=cp.decode)


def compare(original: Path, *, pairs: int = 2, synthetic: bool = False) -> dict:
    if type(pairs) is not int or not 1 <= pairs <= 4:
        raise Refused("R461_PAIR_COUNT_OUT_OF_RANGE")
    captures = {"R459_independent": [], "R461_shared_index": []}
    cp_counts = []
    for iteration in range(pairs):
        before, _ = r446.observe()
        calls = [0]

        def build(data: bytes):
            calls[0] += 1
            return cp.decode(data)

        def optimized(path: Path):
            return r459.inspect(path, shared_pool_factory=build)

        order = (("R459_independent", r459.inspect),
                 ("R461_shared_index", optimized))
        if iteration % 2:
            order = tuple(reversed(order))
        results = {}
        for label, runner in order:
            results[label], metric = r460.measure(runner, original)
            captures[label].append(metric)
        after, _ = r446.observe()
        if before != after:
            raise Refused("R461_FULL_INPUT_SHA_CHANGED_ACROSS_PAIR")
        r447.read_pinned_original(original)
        if results["R459_independent"] != results["R461_shared_index"]:
            raise Refused("R461_INDEPENDENT_AGGREGATE_OUTPUT_DISAGREEMENT")
        compiled = results["R459_independent"]["isolated_r421_compiled_classes"]
        if calls[0] != compiled:
            raise Refused("R461_SHARED_CP_DECODE_COUNT_DRIFT")
        if captures["R459_independent"][-1]["read_calls_by_kind"] != (
                captures["R461_shared_index"][-1]["read_calls_by_kind"]):
            raise Refused("R461_READ_COUNT_SAFETY_GATE_DRIFT")
        cp_counts.append(calls[0])

    old = r460.summarized(captures["R459_independent"])
    new = r460.summarized(captures["R461_shared_index"])
    if old["median_wall_ms"] <= 0 or new["median_wall_ms"] <= 0:
        raise Refused("R461_INVALID_BENCHMARK_TIME")

    return {
        "schema": SCHEMA,
        "status": "R461_SHARED_CP_SYNTHETIC_OR_OWNER_BENCHMARK_UNAPPROVED",
        "fixture": "fabricated_synthetic" if synthetic else "owner_private_unapproved",
        "pairs": pairs,
        "order_alternated": True,
        "R459_independent": old,
        "R461_shared_index": new,
        "observed_wall_speedup_R459_over_R461":
            round(old["median_wall_ms"] / new["median_wall_ms"], 3),
        "median_shared_pool_decodes": median(cp_counts),
        "full_SHA_input_consistency": True,
        "aggregate_output_parity": True,
        "same_bounded_file_reads": True,
        "legacy_default_parsers_untouched": True,
        "instrumentation_overhead_present": True,
        "synthetic_speedup_generalizes_to_owner": False,
        "private_names_paths_or_bytes_exported": False,
        "historical_R421_approval": False,
        "client_executed": False,
        "compilation_authorized": False,
        "release_authorized": False,
        "merge_authorized": False,
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
            "status": "R461_SHARED_CP_BENCHMARK_REFUSED",
            "reason": "R461_PRIVATE_INPUT_OR_PARITY_REFUSED",
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
