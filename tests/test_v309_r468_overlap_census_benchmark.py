"""R468 complete aggregate census, SHA-gated observer and batched timing tests."""
from __future__ import annotations

from dataclasses import asdict, replace
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r459_consolidated_inspection as owner_fixture
from tools.r459 import audit_consolidated_inspection as r459
from tools.r465 import benchmark_hierarchy_overlap as fabricated
from tools.r467 import calibrated_hierarchy as r467
from tools.r468 import overlap_census as census
from tools.r468 import audit_owner_overlap as owner
from tools.r468 import benchmark_batched_thresholds as bench


class R468Census(unittest.TestCase):
    def test_01_all_overlapping_target_counts_are_complete(self):
        w = fabricated.fabricated(24, 8, True)
        c = census.count(w.rebuilt, w.selected, w.sites)
        self.assertEqual(c.rebuilt_class_records, 24)
        self.assertEqual(c.selected_dependency_records, 29)
        self.assertEqual(c.decoded_member_opcode_sites, 192)
        self.assertEqual(c.distinct_opcode_member_targets, 192)
        self.assertEqual(c.eligible_in_graph_opcode_targets, 192)
        self.assertEqual(c.rebuilt_reference_occurrences, 192)
        self.assertEqual(c.distinct_rebuilt_reference_targets, 192)
        self.assertEqual(c.exact_overlapping_distinct_targets, 192)
        self.assertEqual(c.exact_overlapping_opcode_site_occurrences, 192)
        self.assertEqual(c.exact_overlapping_owner_count, 24)
        self.assertTrue(all((c.threshold_2_met, c.threshold_4_met,
                             c.threshold_8_met, c.threshold_16_met)))
        self.assertTrue(c.complete_reference_enumeration)

    def test_02_no_opcode_negative_control_counts_references_still(self):
        w = fabricated.fabricated(24, 8, False)
        c = census.count(w.rebuilt, w.selected, w.sites)
        self.assertEqual(c.decoded_member_opcode_sites, 0)
        self.assertEqual(c.distinct_rebuilt_reference_targets, 192)
        self.assertEqual(c.exact_overlapping_distinct_targets, 0)
        self.assertFalse(c.threshold_2_met)
        self.assertTrue(c.complete_reference_enumeration)

    def test_03_duplicate_opcode_sites_increase_occurrences_not_uniques(self):
        w = fabricated.fabricated(8, 1, True)
        c = census.count(w.rebuilt, w.selected, list(w.sites) * 3)
        self.assertEqual(c.decoded_member_opcode_sites, 24)
        self.assertEqual(c.distinct_opcode_member_targets, 8)
        self.assertEqual(c.exact_overlapping_distinct_targets, 8)
        self.assertEqual(c.exact_overlapping_opcode_site_occurrences, 24)
        self.assertTrue(c.threshold_8_met)
        self.assertFalse(c.threshold_16_met)

    def test_04_forged_opcode_names_cannot_create_false_intersection(self):
        w = fabricated.fabricated(24, 8, True)
        wrong = [
            replace(site, target=replace(
                site.target, name="unknownSyntheticName"))
            for site in w.sites
        ]
        c = census.count(w.rebuilt, w.selected, wrong)
        # Replacing all eight method names per owner with one synthetic
        # name collapses eight opcode targets to one per owner: 24 uniques.
        self.assertEqual(c.eligible_in_graph_opcode_targets, 24)
        self.assertEqual(c.distinct_opcode_member_targets, 24)
        self.assertEqual(c.exact_overlapping_distinct_targets, 0)
        self.assertEqual(c.exact_overlapping_opcode_site_occurrences, 0)

    def test_05_threshold_counts_and_prior_selector_agree(self):
        for owners, signatures, overlap in (
                (1, 1, True), (2, 1, True), (4, 1, True),
                (8, 1, True), (16, 1, True),
                (24, 8, True), (24, 8, False)):
            w = fabricated.fabricated(owners, signatures, overlap)
            for threshold in (2, 4, 8, 16):
                enabled, c = census.compare_with_gate(
                    w.rebuilt, w.selected, w.sites, threshold=threshold)
                self.assertEqual(
                    enabled,
                    c.exact_overlapping_distinct_targets >= threshold)

    def test_06_invalid_input_and_budget_are_fail_closed(self):
        w = fabricated.fabricated(24, 8, True)
        with self.assertRaises(census.Refused):
            census.count({}, {}, [object()])
        with patch.object(census, "MAX_REBUILT_REFERENCE_VISITS", 1):
            with self.assertRaisesRegex(
                    census.Refused, "R468_CENSUS_REFERENCE_VISIT_BUDGET"):
                census.count(w.rebuilt, w.selected, w.sites)
        with patch.object(census, "MAX_UNIQUE_MEMBER_REFERENCES", 1):
            with self.assertRaisesRegex(
                    census.Refused, "R468_CENSUS_UNIQUE_REFERENCE_BUDGET"):
                census.count(w.rebuilt, w.selected, w.sites)
        with patch.object(census, "MAX_MEMBER_OPCODE_SITES", 0):
            with self.assertRaises(census.Refused):
                census.count(w.rebuilt, w.selected, w.sites)
        with self.assertRaises(census.Refused):
            census.count(w.rebuilt, {**w.selected, **w.rebuilt}, w.sites)

    def test_07_aggregate_has_no_member_names_or_paths(self):
        w = fabricated.fabricated(8, 1, True)
        payload = json.dumps(asdict(census.count(
            w.rebuilt, w.selected, w.sites)), sort_keys=True)
        for private in ("fixture/deps", "fixture/rebuilt",
                        "method0", "Owner0001", "foo()V"):
            self.assertNotIn(private, payload)


class R468BatchedCalibration(unittest.TestCase):
    def test_08_all_modes_complete_parity_and_batched_spread(self):
        result = bench.compare(pairs=5, iterations=8)
        self.assertEqual(len(result["modeled_cases"]), 7)
        self.assertTrue(result["all_complete_public_and_private_evidence_parity"])
        self.assertEqual(result["paired_trials_per_case"], 5)
        self.assertEqual(result["complete_analyses_per_timed_sample"], 8)
        self.assertTrue(result["tracemalloc_disabled_for_timing"])
        for item in result["modeled_cases"]:
            self.assertTrue(item["entire_public_private_evidence_equal"])
            for mode in bench.MODES:
                self.assertGreater(
                    item["wall_time_by_mode"][mode]
                        ["median_ms_per_complete_analysis"], 0)
                self.assertGreaterEqual(
                    item["wall_time_by_mode"][mode]
                        ["median_abs_deviation_ms"], 0)
            self.assertEqual(
                item["cache_enabled_by_mode"]["threshold_8"],
                item["eligible_unique_overlapping_targets"] >= 8)
        zero = result["modeled_cases"][-1]
        self.assertEqual(zero["eligible_unique_overlapping_targets"], 0)
        self.assertFalse(zero["cache_enabled_by_mode"]["threshold_2"])
        self.assertFalse(zero["cache_enabled_by_mode"]["threshold_16"])
        payload = json.dumps(result, sort_keys=True)
        for private in ("fixture/deps", "Root.class",
                        "Owner0001", "LootHistoryStore",
                        "images/logo.png", "rs/Bridge"):
            self.assertNotIn(private, payload)
        self.assertFalse(result["original_owner_client_used"])
        print("R468_SYNTHETIC_BATCHED_BENCHMARK=" + payload)

    def test_09_bad_batched_arguments_and_wrong_mode_refuse(self):
        for pairs, iterations in ((2, 8), (10, 8), (3, 0),
                                  (3, 17), (True, 8), (3, True)):
            with self.assertRaises(bench.Refused):
                bench.compare(pairs=pairs, iterations=iterations,
                              cases=((1, 1, True),))
        w = fabricated.fabricated(1, 1, True)
        with self.assertRaises(bench.Refused):
            bench.run_mode(w, "invented_mode")

    def test_10_synthetic_benchmark_never_calls_owner_sha_inspect(self):
        with patch.object(r459, "inspect",
                          side_effect=AssertionError("private owner audit")):
            r = bench.compare(pairs=3, iterations=2,
                              cases=((2, 1, True), (8, 1, True)))
        self.assertFalse(r["original_owner_client_used"])


    def test_16_windows_coarse_cpu_timer_zero_is_not_refused(self):
        actual = bench.run_mode

        def zero_cpu(workload, mode, *, iterations):
            return actual(workload, mode), (0.1, 0.0)

        with patch.object(bench, "one_batch", side_effect=zero_cpu):
            result = bench.compare(
                pairs=3, iterations=1, cases=((2, 1, True),))
        self.assertTrue(result["all_complete_public_and_private_evidence_parity"])
        self.assertEqual(
            result["modeled_cases"][0]["cpu_time_by_mode"]
                  ["independent"]["median_ms_per_complete_analysis"], 0.0)
        self.assertTrue(result["coarse_cpu_clock_may_report_zero_on_windows"])

        def invalid_wall(workload, mode, *, iterations):
            return actual(workload, mode), (0.0, 0.0)

        with patch.object(bench, "one_batch", side_effect=invalid_wall):
            with self.assertRaisesRegex(
                    bench.Refused, "R468_PAIRED_MEASUREMENT_OR_OUTPUT_DRIFT"):
                bench.compare(pairs=3, iterations=1,
                              cases=((2, 1, True),))


class R468SyntheticOwner(unittest.TestCase):
    def setUp(self):
        owner_fixture.R459ConsolidatedFakeOwner.setUp(self)

    def test_11_exact_SHA_gate_and_all_private_evidence_parity(self):
        baseline, private = r459.inspect(self.original_jar)
        previous, previous_detail = r467.inspect(self.original_jar)
        latest, latest_detail, c = owner.inspect(self.original_jar)
        self.assertEqual(latest, baseline)
        self.assertEqual(latest, previous)
        self.assertEqual(private, previous_detail)
        self.assertEqual(private, latest_detail)
        self.assertEqual(c.rebuilt_class_records, 2)
        self.assertEqual(c.decoded_member_opcode_sites, 2)
        self.assertEqual(latest["full_R446_inventory_observations"], 2)
        self.assertTrue(latest["pinned_original_archive_re_read_after_evidence_pass"])
        result = owner.public_result(latest, c)
        self.assertEqual(result["census"]["decoded_member_opcode_sites"], 2)
        self.assertTrue(result["original_v309_exact_pin_verified"])
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["candidate_worklist_exported"])

    def test_12_source_mutation_during_census_is_caught_by_final_sha(self):
        original = census.compare_with_gate
        def mutating(*args, **kwargs):
            result = original(*args, **kwargs)
            source = self.source / "rs/Bridge.java"
            source.write_bytes(source.read_bytes() + b" altered")
            return result
        with patch.object(census, "compare_with_gate", side_effect=mutating):
            with self.assertRaisesRegex(
                    (r459.Refused, r459.r446.Refused),
                    "R459_.*|R446_.*"):
                owner.inspect(self.original_jar)

    def test_13_invalid_public_summary_refused_without_export(self):
        summary, _details, c = owner.inspect(self.original_jar)
        summary = dict(summary)
        summary["pinned_original_archive_re_read_after_evidence_pass"] = False
        with self.assertRaises(owner.Refused):
            owner.public_result(summary, c)

    def test_14_missing_owner_archive_redacted_CLI(self):
        missing = self.temp / "private-location-and-client-not-found.jar"
        completed = subprocess.run(
            [sys.executable, "-B",
             str(owner.ROOT / "tools/r468/audit_owner_overlap.py"),
             "--original-v309-jar", str(missing)],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"],
                         "R468_OWNER_OVERLAP_CENSUS_REFUSED")
        self.assertNotIn(str(missing), completed.stdout)
        self.assertNotIn("Traceback", completed.stderr)

    def test_15_fake_owner_CLI_reports_aggregate_only(self):
        completed = subprocess.run(
            [sys.executable, "-B",
             str(owner.ROOT / "tools/r468/audit_owner_overlap.py"),
             "--original-v309-jar", str(self.original_jar)],
            capture_output=True, text=True, timeout=30, check=False)
        # Isolated subprocess does not inherit in-process fake-owner patches.
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(json.loads(completed.stdout)["status"],
                         "R468_OWNER_OVERLAP_CENSUS_REFUSED")
        self.assertNotIn(str(self.temp), completed.stdout)
        self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
