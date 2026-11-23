"""R460 synthetic-only paired legacy vs consolidated audit benchmark checks.

All owner-like input trees and JARs are fabricated by the R458/R459
regression fixtures. No client, private history, network or runtime start.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tracemalloc
import unittest
from unittest.mock import patch

import test_v309_r459_consolidated_inspection as fixture
from tools.r460 import benchmark_inspection as r460

ROOT = r460.ROOT
CLI = ROOT / "tools/r460/benchmark_inspection.py"


class R460PairedSynthetic(unittest.TestCase):
    def setUp(self):
        fixture.R459ConsolidatedFakeOwner.setUp(self)

    def test_01_identical_fabricated_inputs_produce_parity_and_read_reduction(self):
        output = r460.compare(self.original_jar, pairs=2, synthetic=True)
        self.assertEqual(output["pairs"], 2)
        old = output["legacy_R458"]
        new = output["consolidated_R459"]
        self.assertTrue(output["pair_sha_inventories_consistent"])
        self.assertTrue(output["shared_output_parity_passed"])
        self.assertEqual(output["fixture"], "fabricated_synthetic")
        self.assertEqual(new["median_read_calls_by_kind"]["class"], 6)
        self.assertGreater(old["median_read_calls_by_kind"]["class"], 6)
        self.assertGreater(old["median_instrumented_read_calls"],
                           new["median_instrumented_read_calls"])
        self.assertGreater(old["median_instrumented_read_bytes"],
                           new["median_instrumented_read_bytes"])
        self.assertGreater(new["median_wall_ms"], 0)
        self.assertGreater(old["median_wall_ms"], 0)
        self.assertGreaterEqual(new["median_python_peak_traced_bytes"], 0)
        self.assertEqual(new["median_stage_calls"]["full_sha_inventory"], 2)
        self.assertEqual(new["median_stage_calls"]["member_constant_pool_parse"], 2)
        self.assertEqual(new["median_stage_calls"]["bootstrap_dynamic_parse"], 2)
        self.assertEqual(new["median_stage_calls"]["code_signature_resource_parse"], 2)
        self.assertTrue(output["instrumentation_overhead_present"])
        self.assertFalse(output["all_filesystem_read_apis_counted"])
        self.assertFalse(output["merge_authorized"])
        self.assertFalse(output["release_authorized"])
        self.assertFalse(output["compilation_authorized"])
        self.assertFalse(output["client_executed"])
        self.assertFalse(output["synthetic_speedup_generalizes_to_owner"])
        self.assertEqual(list(self.temp.glob("SpawnPK-R460-*")), [])
        public = json.dumps(output, sort_keys=True)
        for value in (str(self.temp), "LootHistoryStore",
                      "rs/Bridge", "images/logo.png", "java/lang/Class"):
            self.assertNotIn(value, public)
        print("R460_SYNTHETIC_AGGREGATE_ONLY=" + public)

    def test_02_pair_input_mutation_refuses_without_output(self):
        actual = r460.r459.inspect
        def changed(*args, **kwargs):
            summary = actual(*args, **kwargs)
            path = self.source / "rs/Bridge.java"
            path.write_bytes(path.read_bytes() + b" changed after measured scan")
            return summary
        with patch.object(r460.r459, "inspect", side_effect=changed):
            with self.assertRaisesRegex(
                    (r460.Refused, r460.r446.Refused),
                    "R460_PAIRED_FULL_SHA_INPUT_CHANGED|R446_"):
                r460.compare(self.original_jar, pairs=1, synthetic=True)

    def test_03_refuses_invalid_pair_count_without_scanning(self):
        with patch.object(r460.r446, "observe",
                          side_effect=AssertionError("should not scan")):
            for pairs in (0, 5, True, -1):
                with self.assertRaisesRegex(
                        r460.Refused, "R460_PAIR_COUNT_OUT_OF_RANGE"):
                    r460.compare(self.original_jar, pairs=pairs)

    def test_04_refuses_cross_parser_output_parity_drift(self):
        old = {legacy: 1 for legacy, _ in r460.PARITY}
        new = {new_key: 1 for _, new_key in r460.PARITY}
        r460.verify_parity(old, new)
        first = r460.PARITY[0][1]
        new[first] = 2
        with self.assertRaisesRegex(
                r460.Refused, "R460_SHARED_OUTPUT_PARITY_FAILURE"):
            r460.verify_parity(old, new)

    def test_05_unexpected_parser_failure_restores_instrumentation(self):
        with patch.object(r460.r459.r458, "scan_class",
                          side_effect=RuntimeError("invented failure")):
            with self.assertRaisesRegex(RuntimeError, "invented failure"):
                r460.measure(r460.r459.inspect, self.original_jar)
        self.assertFalse(tracemalloc.is_tracing())

    def test_06_missing_input_cli_redacts_owner_path(self):
        missing = self.temp / "owner-private-input-missing-v309.jar"
        run = subprocess.run(
            [sys.executable, "-B", str(CLI),
             "--original-v309-jar", str(missing), "--pairs", "1"],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertEqual(json.loads(run.stdout)["status"],
                         "R460_PAIRED_BENCHMARK_REFUSED")
        self.assertNotIn(str(missing), run.stdout)
        self.assertNotIn("Traceback", run.stderr)


class R460PureContract(unittest.TestCase):
    def test_07_stage_names_are_unique_aggregate_labels(self):
        labels = [name for name, _, _ in r460.STAGES]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(r460.category(r460.ROOT / "foo.class"), "class")
        self.assertEqual(r460.category(r460.ROOT / "bar.java"), "source")
        self.assertEqual(r460.category(r460.ROOT / "baz.jar"), "jar")

    def test_08_schema_and_limits_do_not_promote_approval(self):
        self.assertIn("UNAPPROVED", r460.SCHEMA)
        self.assertLessEqual(r460.MAX_PAIRS, 4)
        self.assertTrue(callable(r460.r458.inspect))
        self.assertTrue(callable(r460.r459.inspect))


if __name__ == "__main__":
    unittest.main()
