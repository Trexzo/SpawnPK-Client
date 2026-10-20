#!/usr/bin/env python3
"""Run the unchanged unittest discovery corpus in four reproducible CI shards.

The full suite previously ran 3,531 tests serially per platform, including
262 costly cases in test_source_normalization. Splitting by *module* preserves
test order and setUpClass/module within a job. Every discovered test is in
exactly one shard, and import failures are still real unittest failures.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOTAL_SHARDS = 4
BASELINE_TEST_COUNT = 3531
HEAVY_MODULE = "test_source_normalization"


def stable_bucket(name: str) -> int:
    """32-bit FNV-1a over module bytes, deliberately independent of hash seed."""
    value = 2166136261
    for byte in name.encode("utf-8"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value


def assign(module: str) -> int:
    if module == HEAVY_MODULE:
        return 0
    return 1 + stable_bucket(module) % (TOTAL_SHARDS - 1)


def flatten(suite):
    for part in suite:
        if isinstance(part, unittest.TestSuite):
            yield from flatten(part)
        elif isinstance(part, unittest.TestCase):
            yield part
        else:
            raise RuntimeError("RECOVERY_SHARD_UNEXPECTED_TEST_TYPE " + type(part).__name__)


def plan_cases(cases):
    all_cases = list(cases)
    ids = [case.id() for case in all_cases]
    duplicates = [identifier for identifier, n in Counter(ids).items() if n != 1]
    if duplicates:
        raise RuntimeError("RECOVERY_SHARD_DUPLICATE_TEST_ID " + duplicates[0])
    if len(all_cases) < BASELINE_TEST_COUNT:
        raise RuntimeError(
            "RECOVERY_SHARD_DISCOVERY_REGRESSION expected_at_least="
            + str(BASELINE_TEST_COUNT) + " observed=" + str(len(all_cases))
        )
    groups = [[] for _ in range(TOTAL_SHARDS)]
    for case in all_cases:
        groups[assign(case.__class__.__module__)].append(case)
    assigned = [case.id() for group in groups for case in group]
    if Counter(assigned) != Counter(ids):
        raise RuntimeError("RECOVERY_SHARD_INCOMPLETE_COVERAGE")
    if not all(groups):
        raise RuntimeError("RECOVERY_SHARD_EMPTY_GROUP")
    if not any(case.__class__.__module__ == HEAVY_MODULE for case in groups[0]):
        raise RuntimeError("RECOVERY_SHARD_HEAVY_MODULE_MISSING")
    if any(case.__class__.__module__ != HEAVY_MODULE for case in groups[0]):
        raise RuntimeError("RECOVERY_SHARD_HEAVY_MODULE_COLLISION")
    return groups


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard", type=int, choices=range(TOTAL_SHARDS), required=True)
    args = parser.parse_args(argv)

    # Identical discovery semantics to: python -m unittest discover -s tests -v
    loader = unittest.TestLoader()
    discovered = loader.discover(start_dir=str(ROOT / "tests"))
    cases = list(flatten(discovered))
    groups = plan_cases(cases)
    print(
        "RECOVERY_SHARD_COVERAGE_PASS total=" + str(len(cases))
        + " shards=" + str(TOTAL_SHARDS)
        + " counts=" + ",".join(str(len(group)) for group in groups)
        + " selection=" + str(args.shard),
        flush=True,
    )
    suite = unittest.TestSuite(groups[args.shard])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    print(
        "RECOVERY_SHARD_PASS shard=" + str(args.shard)
        + " executed=" + str(result.testsRun)
        + " total_discovered=" + str(len(cases)),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print("RECOVERY_SHARD_FAIL_CLOSED " + str(exc), file=sys.stderr)
        raise SystemExit(2)
