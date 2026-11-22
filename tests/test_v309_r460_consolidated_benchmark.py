"""R460 deterministic safety assertions + invented-input performance benchmarks.

Never require a faster median to pass CI: real timings depend on runner load.
Test the actual read-count reductions, count parity, mode labels, no private
data in stdout, independent tracemalloc sampling and mutation refusal.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r458_bootstrap_callsite as fixture_module
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r460 import benchmark_consolidated_inspection as bench

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r460/benchmark_consolidated_inspection.py"


class R460BenchmarkPure(unittest.TestCase):
    def test_01_same_origin_and_dynamic_counts_are_required(self):
        old = {
            "original_v309_class_count": 5,
            "original_v309_resource_count": 2,
            "isolated_r421_compiled_classfiles": 2,
            "isolated_r421_java_sources": 2,
            "invokedynamic_bytecode_sites": 0,
            "constant_dynamic_ldc_bytecode_sites": 0,
            "original_v309_exact_sha_verified": True,
            "historical_R421_full_inventory_independently_approved": False,
            "merge_authorized": False, "release_authorized": False,
        }
        new = {
            "original_v309_class_count": 5,
            "original_v309_resource_count": 2,
            "isolated_r421_compiled_classes": 2,
            "isolated_r421_java_sources": 2,
            "R458_invokedynamic_bytecode_sites": 0,
            "R458_constant_dynamic_ldc_sites": 0,
            "original_v309_pinned_sha_matched": True,
            "historical_R421_full_inventory_independently_approved": False,
            "merge_authorized": False, "release_authorized": False,
        }
        bench.check_parity(old, new)

    def test_02_mismatched_dynamic_counts_refused(self):
        old, new = self._reports()
        new["R458_invokedynamic_bytecode_sites"] += 1
        with self.assertRaisesRegex(
                bench.Refused, "R460_COMPARISON_COMMON_COUNT_DRIFT"):
            bench.check_parity(old, new)

    def test_03_mismatched_class_count_refused(self):
        old, new = self._reports()
        new["isolated_r421_compiled_classes"] = 99
        with self.assertRaisesRegex(
                bench.Refused, "R460_COMPARISON_COMMON_COUNT_DRIFT"):
            bench.check_parity(old, new)

    def test_04_cannot_self_approve_custody_or_release(self):
        old, new = self._reports()
        old["historical_R421_full_inventory_independently_approved"] = True
        with self.assertRaisesRegex(
                bench.Refused,
                "R460_UNAPPROVED_CUSTODY_OR_RELEASE_FLAG_CHANGED"):
            bench.check_parity(old, new)
        old["historical_R421_full_inventory_independently_approved"] = False
        new["release_authorized"] = True
        with self.assertRaisesRegex(
                bench.Refused,
                "R460_UNAPPROVED_CUSTODY_OR_RELEASE_FLAG_CHANGED"):
            bench.check_parity(old, new)

    def test_05_unpinned_original_is_refused(self):
        old, new = self._reports()
        new["original_v309_pinned_sha_matched"] = False
        with self.assertRaisesRegex(
                bench.Refused, "R460_ORIGINAL_PIN_NOT_VERIFIED"):
            bench.check_parity(old, new)

    def test_06_nested_classification_does_not_emit_private_paths(self):
        root = Path("/fake-isolated")  # only fabricated path, never read
        roots = (root, root/"source", root/"classes",
                 root/"preferred.jar", root/"alternate.jar")
        original = root/"original.jar"
        for path, kind in (
            (root/"source"/"A.java", "java_source"),
            (root/"classes"/"p"/"A.class", "rebuilt_class"),
            (root/"preferred.jar", "preferred_dependency"),
            (root/"alternate.jar", "alternate_dependency"),
            (original, "original_v309"),
            (root/"not-owned", "other")):
            self.assertEqual(bench._category(path, roots, original), kind)

    def test_07_bad_sample_or_clock_measurement_refused(self):
        with self.assertRaisesRegex(bench.Refused, "R460_BAD_CLOCK_SAMPLES"):
            bench._summary_ns([])
        with self.assertRaisesRegex(bench.Refused, "R460_BAD_CLOCK_SAMPLES"):
            bench._summary_ns([1, 0])

    def test_08_median_units_are_milliseconds_not_nanoseconds(self):
        sample = bench._summary_ns([1_000_000, 2_000_000, 3_000_000])
        self.assertEqual(sample["samples"], 3)
        self.assertEqual(sample["median_ms"], 2.0)
        self.assertEqual(sample["min_ms"], 1.0)
        self.assertEqual(sample["max_ms"], 3.0)

    def test_09_schema_and_mode_order_explicit(self):
        self.assertIn("UNAPPROVED", bench.SCHEMA)
        self.assertEqual(bench.MODES, (
            "legacy_R458_nested", "consolidated_R459"))
        self.assertGreater(bench.MAX_TIMED_ITERATIONS, 1)

    @staticmethod
    def _reports():
        old = {
            "original_v309_class_count": 5,
            "original_v309_resource_count": 2,
            "isolated_r421_compiled_classfiles": 2,
            "isolated_r421_java_sources": 2,
            "invokedynamic_bytecode_sites": 0,
            "constant_dynamic_ldc_bytecode_sites": 0,
            "original_v309_exact_sha_verified": True,
            "historical_R421_full_inventory_independently_approved": False,
            "merge_authorized": False, "release_authorized": False,
        }
        new = {
            "original_v309_class_count": 5,
            "original_v309_resource_count": 2,
            "isolated_r421_compiled_classes": 2,
            "isolated_r421_java_sources": 2,
            "R458_invokedynamic_bytecode_sites": 0,
            "R458_constant_dynamic_ldc_sites": 0,
            "original_v309_pinned_sha_matched": True,
            "historical_R421_full_inventory_independently_approved": False,
            "merge_authorized": False, "release_authorized": False,
        }
        return old, new


class R460InventedOwnerBench(unittest.TestCase):
    def setUp(self):
        fixture_module.R458OwnerInventedOffline.setUp(self)

    def run_benchmark(self, iterations=1, warmups=0):
        return bench.benchmark(
            self.original_jar, synthetic=True,
            iterations=iterations, warmups=warmups)

    def test_10_legacy_and_fused_real_scanners_produce_matching_synthetic_counts(self):
        result = self.run_benchmark()
        self.assertEqual(
            result["status"], "R460_BENCHMARK_UNAPPROVED_SYNTHETIC")
        self.assertTrue(result["common_original_rebuilt_and_dynamic_counts_matched"])
        self.assertEqual(result["benchmark_iterations_per_mode"], 1)
        self.assertTrue(result["complete_current_owner_source_class_dependency_SHA_unchanged"])
        self.assertFalse(result["real_owner_performance_measured"])

    def test_11_consolidated_reads_fewer_fabricated_classes_and_bytes(self):
        result = self.run_benchmark()
        old = result["legacy_R458_nested"]["bounded_io"]
        new = result["consolidated_R459"]["bounded_io"]
        self.assertGreater(
            old["read_calls_by_kind"]["rebuilt_class"],
            new["read_calls_by_kind"]["rebuilt_class"])
        self.assertEqual(new["read_calls_by_kind"]["rebuilt_class"], 6)
        self.assertGreater(
            old["bounded_file_bytes_returned"],
            new["bounded_file_bytes_returned"])
        self.assertGreater(result["observed_bounded_read_call_reduction_percent"], 0)

    def test_12_timing_does_not_assert_synthetic_speedup_and_memory_is_distinct(self):
        report = self.run_benchmark(iterations=2, warmups=1)
        for name in bench.MODES:
            self.assertEqual(report[name]["wall_clock"]["samples"], 2)
            self.assertGreater(report[name]["wall_clock"]["median_ms"], 0)
            self.assertGreater(
                report[name]["tracemalloc_peak_python_allocated_bytes"], 0)
        self.assertGreater(
            report["observed_median_wall_clock_ratio_legacy_over_consolidated"], 0)
        self.assertTrue(
            report["timing_is_exclusive_of_tracemalloc_and_io_instrumentation"])
        self.assertTrue(report["tracemalloc_is_python_allocation_peak_not_process_RSS"])

    def test_13_public_aggregate_no_real_owner_paths_or_private_member_names(self):
        payload = json.dumps(self.run_benchmark(), sort_keys=True)
        for private in ("rs/plugins/loottracker/LootHistoryStore",
                        "images/logo.png", "java/lang/Class",
                        "textures/missing.png", str(self.temp),
                        r425.PINNED_R421_STORE_SHA):
            self.assertNotIn(private, payload)
        self.assertIn("invented_public_fixture", payload)

    def test_14_invalid_loop_budgets_refused_before_timed_work(self):
        for n, w in ((0,0),(13,0),(1,-1),(1,4)):
            with self.subTest(iterations=n, warmups=w):
                with self.assertRaisesRegex(
                        bench.Refused, "R460_ITERATION_OR_WARMUP_LIMIT"):
                    self.run_benchmark(n, w)

    def test_15_original_JAR_tamper_refused(self):
        self.original_jar.write_bytes(b"not pinned v309 bytes")
        with self.assertRaises(bench.r447.Refused):
            self.run_benchmark()

    def test_16_source_mutation_during_benchmark_refused(self):
        real = bench.consolidated_audit.inspect
        touched = [False]
        def mutate(*args, **kwargs):
            value = real(*args, **kwargs)
            if not touched[0]:
                touched[0] = True
                path = self.source / "rs/Bridge.java"
                path.write_bytes(path.read_bytes()+b" changed")
            return value
        with patch.object(bench.consolidated_audit, "inspect",
                          side_effect=mutate):
            with self.assertRaises((
                    bench.r446.Refused, bench.Refused)):
                self.run_benchmark()

    def test_17_tracemalloc_restored_after_successful_memory_measurement(self):
        self.assertFalse(bench.tracemalloc.is_tracing())
        report, peak = bench.peak_python_allocated_bytes(
            bench.consolidated_audit.inspect, self.original_jar)
        self.assertGreater(peak, 0)
        self.assertFalse(bench.tracemalloc.is_tracing())
        self.assertFalse(report["release_authorized"])

    def test_18_private_mode_semantics_never_claims_runtime_or_compilation(self):
        report = self.run_benchmark()
        for key in (
            "jvm_or_client_executed",
            "historical_R421_full_inventory_independently_approved",
            "real_runtime_latency_or_FPS_measured",
            "source_class_jar_bytes_or_private_names_exported",
            "persistence_history_or_deletion_journal_accessed",
            "merge_authorized", "release_authorized",
        ):
            self.assertFalse(report[key])


class R460SyntheticCLI(unittest.TestCase):
    def test_19_explicit_synthetic_CLI_produces_aggregate_only(self):
        result = subprocess.run(
            [sys.executable, "-B", str(CLI), "--synthetic",
             "--iterations", "1", "--warmups", "0"],
            capture_output=True, text=True, check=False, timeout=35)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"],
                         "R460_BENCHMARK_UNAPPROVED_SYNTHETIC")
        self.assertFalse(payload["real_runtime_latency_or_FPS_measured"])

    def test_20_invalid_synthetic_iteration_CLI_refuses_without_paths(self):
        result = subprocess.run(
            [sys.executable, "-B", str(CLI), "--synthetic",
             "--iterations", "200"],
            capture_output=True, text=True, check=False, timeout=15)
        self.assertEqual(result.returncode, 2, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "R460_BENCHMARK_REFUSED")
        self.assertNotIn("C:", result.stdout)
        self.assertFalse(data["release_authorized"])


if __name__ == "__main__":
    unittest.main()
