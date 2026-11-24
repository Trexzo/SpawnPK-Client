"""R465 fabricated in-memory hierarchy stress benchmark and privacy gates."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.r454 import member_ancestry_evidence as r454
from tools.r464 import shared_hierarchy as shared
from tools.r465 import benchmark_hierarchy_overlap as r465

CLI = r465.ROOT / "tools/r465/benchmark_hierarchy_overlap.py"


class R465GeneratedFixture(unittest.TestCase):
    def test_01_expected_generated_dependency_and_opcode_inventory(self):
        job = r465.fabricated(24, 8, True)
        self.assertEqual(len(job.rebuilt), 24)
        self.assertEqual(len(job.selected), 29)  # root, four layers, 24 owners
        self.assertEqual(len(job.sites), 24 * 8)
        self.assertEqual(
            sum(len(rec.references) for rec in job.rebuilt.values()), 24 * 8)
        self.assertEqual(
            set(job.rebuilt).intersection(job.selected), set())

    def test_02_overlapping_hierarchy_parity_including_private_worklists(self):
        job = r465.fabricated(12, 8, True)
        old, _ = r465.analysis(job, reuse=False)
        new, index = r465.analysis(job, reuse=True)
        self.assertEqual(old, new)
        self.assertEqual(index.admissions, 2)
        self.assertEqual(index.ancestry_misses, 12)
        self.assertEqual(index.ancestry_hits, 12)
        self.assertEqual(index.resolution_misses, 12 * 8)
        self.assertEqual(index.resolution_hits, 12 * 8)
        self.assertGreater(
            len(old[0][1]["member_reference_access_and_dependency_leads"]), 0)

    def test_03_true_underlying_ancestry_and_resolution_calls_halved(self):
        job = r465.fabricated(24, 8, True)
        original, _, old = r465.counted(job, False)
        optimized, _, new = r465.counted(job, True)
        self.assertEqual(original, optimized)
        self.assertEqual(old, {
            "underlying_ancestry_traversals": 48,
            "underlying_member_resolutions": 384,
        })
        self.assertEqual(new, {
            "underlying_ancestry_traversals": 24,
            "underlying_member_resolutions": 192,
        })

    def test_04_no_overlap_control_stays_correct_but_no_cache_hits(self):
        job = r465.fabricated(24, 8, False)
        legacy, _, old = r465.counted(job, False)
        reused, graph, new = r465.counted(job, True)
        self.assertEqual(legacy, reused)
        self.assertEqual(old, new)
        self.assertEqual(graph.ancestry_hits, 0)
        self.assertEqual(graph.resolution_hits, 0)
        self.assertEqual(graph.ancestry_misses, 24)
        self.assertEqual(graph.resolution_misses, 192)

    def test_05_public_benchmark_varied_shapes_and_complete_parity(self):
        output = r465.compare(pairs=2, cases=(
            (24, 8, True), (96, 8, True), (192, 8, True),
            (96, 8, False)))
        self.assertEqual(output["pairs_per_workload"], 2)
        self.assertEqual(len(output["workloads"]), 4)
        for row in output["workloads"]:
            self.assertTrue(row["entire_public_and_private_output_equal"])
            self.assertGreater(row["median_independent_wall_ms"], 0)
            self.assertGreater(row["median_shared_wall_ms"], 0)
            self.assertGreater(row["observed_wall_speedup"], 0)
            self.assertEqual(
                row["independent_R454_call_counts"]["underlying_ancestry_traversals"],
                row["reconstructed_caller_records"] *
                (2 if row["overlap_between_R455_and_R456"] else 1))
            self.assertEqual(
                row["shared_R454_call_counts"]["underlying_ancestry_traversals"],
                row["reconstructed_caller_records"])
        self.assertEqual(output["workloads"][-1]["shared_ancestry_cache_hits"], 0)
        self.assertFalse(output["real_client_speedup_established"])
        self.assertFalse(output["original_v309_jar_read"])
        self.assertFalse(output["SHA_file_inventory_measured"])
        self.assertFalse(output["release_authorized"])
        printable = json.dumps(output, sort_keys=True)
        for forbidden in (
            "fixture/deps/", "fixture/rebuilt/", "Root.class",
            "Owner0001.class", "java/lang/Object.class",
            "LootHistoryStore", "images/logo.png"):
            self.assertNotIn(forbidden, printable)
        print("R465_SYNTHETIC_HIERARCHY_BENCHMARK=" + printable)

    def test_06_bad_shape_and_excessive_dataset_refused(self):
        for owners, methods, overlap in (
            (0, 8, True), (257, 8, True), (2, 17, True),
            (5, 0, True), (5, 8, "true")):
            with self.assertRaises(r465.Refused):
                r465.fabricated(owners, methods, overlap)
        for invalid in (0, 5, True, -1):
            with self.assertRaises(r465.Refused):
                r465.compare(pairs=invalid, cases=((2, 2, True),))
        with self.assertRaises(r465.Refused):
            r465.compare(pairs=1, cases=())

    def test_07_output_parity_disagreement_fails_closed(self):
        job = r465.fabricated(4, 3)
        actual = r465.analysis
        count = [0]
        def forged(workload, *, reuse, index_factory=shared.Index):
            result, index = actual(workload, reuse=reuse, index_factory=index_factory)
            count[0] += 1
            if reuse:
                return ({"forged": "unsafe"}, result[1]), index
            return result, index
        with patch.object(r465, "analysis", side_effect=forged):
            with self.assertRaisesRegex(
                    r465.Refused, "R465_COMPLETE_PUBLIC_PRIVATE_OUTPUT_DISAGREEMENT"):
                r465.compare(pairs=1, cases=((4, 3, True),))

    def test_08_new_code_never_inspects_JAR_or_source(self):
        with patch.object(r454, "analyze",
                          side_effect=AssertionError("rebuilt-only R454 not relevant")):
            report = r465.compare(pairs=1, cases=((3, 3, True),))
        self.assertFalse(report["owner_client_benchmarked"])
        self.assertFalse(report["actual_gameplay_latency_measured"])
        self.assertEqual(report["scope"],
                         "R455_and_R456_synthetic_in_memory_hierarchy_only")

    def test_09_CLI_default_missing_dependency_is_not_needed(self):
        result = subprocess.run(
            [sys.executable, "-B", str(CLI),
             "--pairs", "1", "--sizes", "4", "12"],
            capture_output=True, text=True, timeout=45, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual([r["reconstructed_caller_records"] for r in data["workloads"]],
                         [4, 12])
        self.assertTrue(data["strict_complete_output_parity_passed"])
        self.assertNotIn("fixture/", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_10_CLI_invalid_size_redacted_and_denied(self):
        result = subprocess.run(
            [sys.executable, "-B", str(CLI),
             "--pairs", "1", "--sizes", "999"],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["status"],
            "R465_HIERARCHY_SYNTHETIC_BENCHMARK_REFUSED")
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
