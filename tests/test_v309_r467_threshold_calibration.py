"""R467 in-memory threshold calibration, owner-audit parity and refusal gates."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r459_consolidated_inspection as fake_owner
from tools.r459 import audit_consolidated_inspection as r459
from tools.r465 import benchmark_hierarchy_overlap as fixture
from tools.r466 import adaptive_hierarchy as r466_policy
from tools.r466 import benchmark_adaptive_hierarchy as r466
from tools.r467 import calibrated_hierarchy as r467
from tools.r467 import benchmark_threshold_sweep as benchmark


class R467PureCalibration(unittest.TestCase):
    def test_01_exact_eight_target_gate_vs_legacy_sixteen(self):
        seven = fixture.fabricated(7, 1, True)
        eight = fixture.fabricated(8, 1, True)
        self.assertFalse(r467.choose(
            seven.rebuilt, seven.selected, seven.sites).use_cache)
        self.assertTrue(r467.choose(
            eight.rebuilt, eight.selected, eight.sites).use_cache)
        self.assertFalse(r466_policy.should_reuse(
            eight.rebuilt, eight.selected, eight.sites))
        self.assertEqual(r467.CALIBRATION_THRESHOLD, 8)
        self.assertEqual(r466_policy.MIN_SHARED_UNIQUE_TARGETS, 16)

    def test_02_no_overlap_neg_control_and_distinct_identity(self):
        zero = fixture.fabricated(24, 8, False)
        decision = r467.choose(zero.rebuilt, zero.selected, zero.sites)
        self.assertFalse(decision.use_cache)
        self.assertEqual(decision.reason, "no_opcode_sites")
        self.assertEqual(decision.reference_visits, 0)
        small = fixture.fabricated(2, 2, True)
        self.assertFalse(r467.choose(
            small.rebuilt, small.selected, small.sites).use_cache)

    def test_03_singleton_four_and_eight_target_semantic_parity(self):
        for size in (1, 2, 4, 8, 12, 16):
            workload = fixture.fabricated(size, 1, True)
            expected, _ = fixture.analysis(workload, reuse=False)
            index_enabled = r467.should_reuse(
                workload.rebuilt, workload.selected, workload.sites)
            actual, cache = fixture.analysis(
                workload, reuse=index_enabled)
            self.assertEqual(actual, expected)
            self.assertEqual(index_enabled, cache is not None)

    def test_04_all_threshold_sweep_cases_preserve_full_private_output(self):
        results = benchmark.compare(pairs=2)
        self.assertEqual(results["pairs_per_case"], 2)
        self.assertEqual(len(results["cases"]), 11)
        self.assertTrue(results["all_complete_public_private_evidence_equal"])
        self.assertTrue(results["selector_time_included_in_adaptive_total"])
        cases = results["cases"]
        self.assertFalse(cases[3]["R466_threshold_16_enabled"])
        self.assertTrue(cases[3]["R467_threshold_8_enabled"])
        self.assertFalse(cases[-1]["R467_threshold_8_enabled"])
        for row in cases:
            self.assertTrue(row["complete_public_private_parity"])
            self.assertGreater(row["R467_threshold_8_median_selector_us"], 0)
            self.assertGreater(row["R466_threshold_16_median_selector_us"], 0)
            for mode in benchmark.MODES:
                self.assertGreater(
                    row["timing_and_memory"][mode]["median_wall_ms"], 0)
            self.assertGreater(row["forced_wall_ratio"], 0)
            self.assertGreater(row["threshold_8_wall_ratio"], 0)
        payload = json.dumps(results, sort_keys=True)
        for forbidden in ("fixture/deps/", "fixture/rebuilt/",
                          "Root.class", "Owner0001", "LootHistoryStore",
                          "images/logo.png", "rs/Bridge"):
            self.assertNotIn(forbidden, payload)
        self.assertFalse(results["real_client_speedup_established"])
        self.assertFalse(results["owner_client_or_original_v309_jar_read"])
        print("R467_SYNTHETIC_THRESHOLD_SWEEP=" + payload)

    def test_05_bad_benchmark_count_refuses_before_any_inspection(self):
        for bad in (-1, 0, 5, True, 1.0):
            with self.assertRaises(benchmark.Refused):
                benchmark.compare(pairs=bad, cases=((1, 1, True),))
        for cases in ((), [], [(1, 1, True)] * 15):
            with self.assertRaises(benchmark.Refused):
                benchmark.compare(pairs=1, cases=cases)

    def test_06_completely_different_results_refuse_not_averaged(self):
        real = benchmark.execute
        def forged(workload, mode):
            outcome, index, decision = real(workload, mode)
            if mode == "threshold_8":
                return ({"forged": True}, outcome[1]), index, decision
            return outcome, index, decision
        with patch.object(benchmark, "execute", side_effect=forged):
            with self.assertRaisesRegex(
                    benchmark.Refused,
                    "R467_FULL_PUBLIC_PRIVATE_EVIDENCE_MISMATCH"):
                benchmark.compare(pairs=1, cases=((8, 1, True),))

    def test_07_selector_probe_repetition_budget_and_result(self):
        w = fixture.fabricated(8, 1, True)
        self.assertGreater(benchmark.selector_probe(w, 8), 0)
        for count in (0, 101, True):
            with self.assertRaises(benchmark.Refused):
                benchmark.selector_probe(w, 8, repetitions=count)

    def test_08_no_production_history_and_no_input_file_requirement(self):
        with patch.object(r459, "inspect",
                          side_effect=AssertionError("owner path forbidden")):
            result = benchmark.compare(
                pairs=1, cases=((8, 1, True), (8, 1, False)))
        self.assertFalse(result["owner_client_or_original_v309_jar_read"])
        self.assertFalse(result["client_compiled_or_executed"])
        self.assertFalse(result["historical_R421_approved"])
        self.assertFalse(result["release_authorized"])


class R467SyntheticOwner(unittest.TestCase):
    def setUp(self):
        fake_owner.R459ConsolidatedFakeOwner.setUp(self)

    def test_09_legacy_R466_R467_exact_owner_audit_parity(self):
        independent, private_independent = r459.inspect(self.original_jar)
        previous, private_previous = r466.inspect(self.original_jar)
        latest, private_latest = r467.inspect(self.original_jar)
        self.assertEqual(independent, previous)
        self.assertEqual(independent, latest)
        self.assertEqual(private_independent, private_previous)
        self.assertEqual(private_independent, private_latest)
        self.assertEqual(latest["full_R446_inventory_observations"], 2)
        self.assertEqual(latest["classfile_evidence_pass_reads"], 2)
        self.assertFalse(
            latest["historical_R421_full_inventory_independently_approved"])

    def test_10_no_new_history_write_or_client_execution(self):
        output, _ = r467.inspect(self.original_jar)
        self.assertFalse(output["production_history_or_deletion_journal_accessed"])
        self.assertFalse(output["source_or_class_bytes_exported"])
        self.assertFalse(output["client_executed"])
        self.assertFalse(output["client_compilation_performed"])
        self.assertFalse(output["release_authorized"])
        self.assertEqual(sorted(self.temp.glob("SpawnPK-R467-*")), [])

    def test_11_entrypoint_preserves_default_independent_path(self):
        from tools.r464 import shared_hierarchy as hierarchy
        with patch.object(hierarchy, "Index",
                          side_effect=AssertionError("optimized-only")):
            result, _ = r459.inspect(self.original_jar)
        self.assertEqual(result["isolated_r421_compiled_classes"], 2)

    def test_12_missing_real_client_is_not_used_by_synthetic_CLI(self):
        # The synthetic benchmark has no --original-jar path argument.
        result = subprocess.run(
            [sys.executable, "-B",
             str(benchmark.ROOT / "tools/r467/benchmark_threshold_sweep.py"),
             "--pairs", "1"], capture_output=True, text=True,
            timeout=100, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["fixture"],
                         "fabricated_R455_R456_in_memory_only")
        self.assertNotIn(str(self.temp), result.stdout)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
