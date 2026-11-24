"""R466 source-free adaptive hierarchy policy and performance regressions."""
from __future__ import annotations

from dataclasses import replace
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r459_consolidated_inspection as fake_owner
from tools.r459 import audit_consolidated_inspection as r459
from tools.r464 import shared_hierarchy as shared
from tools.r465 import benchmark_hierarchy_overlap as r465
from tools.r466 import adaptive_hierarchy as policy
from tools.r466 import benchmark_adaptive_hierarchy as r466

CLI = r466.ROOT / "tools/r466/benchmark_adaptive_hierarchy.py"


class R466Policy(unittest.TestCase):
    def test_01_heavy_exact_overlap_activates_cache(self):
        case = r465.fabricated(24, 8, True)
        decision = policy.choose(case.rebuilt, case.selected, case.sites)
        self.assertTrue(decision.use_cache)
        self.assertEqual(decision.overlapping_unique_targets, 16)
        self.assertEqual(decision.candidate_unique_opcode_targets, 192)
        self.assertEqual(decision.reason, "sufficient_exact_overlap")
        self.assertTrue(policy.should_reuse(
            case.rebuilt, case.selected, case.sites))

    def test_02_no_opcode_sites_skips_cache_without_reference_probe(self):
        case = r465.fabricated(96, 8, False)
        decision = policy.choose(case.rebuilt, case.selected, case.sites)
        self.assertFalse(decision.use_cache)
        self.assertEqual(decision.reason, "no_opcode_sites")
        self.assertEqual(decision.reference_visits, 0)

    def test_03_low_unique_overlap_skips_even_if_opcodes_exist(self):
        small = r465.fabricated(8, 1, True)
        decision = policy.choose(small.rebuilt, small.selected, small.sites)
        self.assertFalse(decision.use_cache)
        self.assertEqual(decision.reason, "too_few_opcode_targets")
        self.assertEqual(decision.candidate_unique_opcode_targets, 8)
        self.assertEqual(decision.reference_visits, 0)

    def test_04_threshold_boundary_is_exact_and_tunable(self):
        below = r465.fabricated(15, 1, True)
        equal = r465.fabricated(16, 1, True)
        self.assertFalse(policy.choose(
            below.rebuilt, below.selected, below.sites).use_cache)
        self.assertTrue(policy.choose(
            equal.rebuilt, equal.selected, equal.sites).use_cache)
        self.assertTrue(policy.choose(
            below.rebuilt, below.selected, below.sites,
            threshold=15).use_cache)
        for invalid in (0, 257, True, -1):
            with self.assertRaises(policy.Refused):
                policy.choose(
                    equal.rebuilt, equal.selected, equal.sites,
                    threshold=invalid)

    def test_05_opcode_targets_must_match_actual_R455_member_refs(self):
        case = r465.fabricated(24, 8, True)
        forged = tuple(replace(s, target=replace(
            s.target, name="noSuchReference"))
                       for s in case.sites)
        decision = policy.choose(case.rebuilt, case.selected, forged)
        self.assertFalse(decision.use_cache)
        self.assertEqual(decision.reason, "insufficient_exact_overlap")
        self.assertEqual(decision.overlapping_unique_targets, 0)
        self.assertEqual(decision.reference_visits, 192)

    def test_06_untrusted_hint_or_probe_budget_refuses_optimization(self):
        case = r465.fabricated(24, 8, True)
        with patch.object(policy, "MAX_REFERENCE_VISITS", 0):
            decision = policy.choose(
                case.rebuilt, case.selected, case.sites)
        self.assertFalse(decision.use_cache)
        self.assertTrue(decision.bounded_probe)
        self.assertEqual(decision.reason, "reference_probe_budget_skip")
        with patch.object(policy, "MAX_SITE_HINTS", 0):
            bounded = policy.choose(case.rebuilt, case.selected, case.sites)
        self.assertFalse(bounded.use_cache)
        self.assertEqual(bounded.reason, "unbounded_hint_skip")
        malformed = policy.choose(
            case.rebuilt, case.selected, [object()])
        self.assertFalse(malformed.use_cache)
        self.assertEqual(malformed.reason, "invalid_hint_skip")

    def test_07_original_and_adaptive_R455_R456_full_output_parity(self):
        for owners, signatures, overlap in (
                (8, 1, True), (24, 8, True), (96, 8, False)):
            case = r465.fabricated(owners, signatures, overlap)
            legacy, _, _ = r466.analysis(case, "independent")
            adaptive, index, selected = r466.analysis(case, "adaptive")
            self.assertEqual(legacy, adaptive)
            self.assertEqual(index is not None, selected.use_cache)
            self.assertEqual(index is not None,
                             owners * signatures >= 16 and overlap)

    def test_08_adaptive_performance_includes_selection_cost_and_controls(self):
        report = r466.compare(pairs=2)
        self.assertEqual(len(report["workloads"]), 5)
        self.assertTrue(report["complete_public_private_parity"])
        self.assertEqual(report["fixture"], "fabricated_in_memory_only")
        for row in report["workloads"]:
            self.assertTrue(row["full_public_private_evidence_parity"])
            for timing in ("independent", "forced_cache", "adaptive"):
                self.assertGreater(row[timing]["wall_ms"], 0)
            self.assertEqual(
                row["adaptive_underlying_R454_calls"],
                row["forced_underlying_R454_calls"] if
                row["adaptive_cache_enabled"] else
                row["legacy_underlying_R454_calls"])
        self.assertFalse(report["workloads"][0]["adaptive_cache_enabled"])
        self.assertTrue(report["workloads"][1]["adaptive_cache_enabled"])
        self.assertTrue(report["workloads"][2]["adaptive_cache_enabled"])
        self.assertTrue(report["workloads"][3]["adaptive_cache_enabled"])
        negative = report["workloads"][4]
        self.assertFalse(negative["adaptive_cache_enabled"])
        self.assertEqual(negative["adaptive_cache_ancestry_hits"], 0)
        self.assertEqual(negative["adaptive_cache_resolution_hits"], 0)
        self.assertEqual(negative["selection_reason"], "no_opcode_sites")
        self.assertFalse(report["production_speedup_proven"])
        self.assertFalse(report["original_v309_jar_read"])
        printable = json.dumps(report, sort_keys=True)
        for forbidden in ("fixture/deps", "fixture/rebuilt", "Root.class",
                          "Owner0001", "LootHistoryStore", "images/logo.png"):
            self.assertNotIn(forbidden, printable)
        print("R466_SYNTHETIC_ADAPTIVE_BENCHMARK=" + printable)

    def test_09_invalid_input_sizes_fail_closed(self):
        with self.assertRaises(r466.Refused):
            r466.compare(pairs=0)
        with self.assertRaises(r466.Refused):
            r466.compare(pairs=5)
        with self.assertRaises(r466.Refused):
            r466.compare(pairs=True)
        with self.assertRaises(r466.Refused):
            r466.compare(cases=())
        with self.assertRaises(policy.Refused):
            policy.choose((), {}, [])


class R466FakeOwner(unittest.TestCase):
    def setUp(self):
        fake_owner.R459ConsolidatedFakeOwner.setUp(self)

    def test_10_R459_owner_path_selector_skips_low_overlap_and_keeps_parity(self):
        legacy, legacy_private = r459.inspect(self.original_jar)
        optimized, private = r466.inspect(self.original_jar)
        self.assertEqual(legacy, optimized)
        self.assertEqual(legacy_private, private)
        self.assertEqual(optimized["full_R446_inventory_observations"], 2)
        self.assertEqual(optimized["classfile_evidence_pass_reads"], 2)
        self.assertFalse(optimized["historical_R421_full_inventory_independently_approved"])
        self.assertFalse(optimized["client_compilation_performed"])
        with patch.object(shared, "Index", side_effect=AssertionError(
                "low-overlap synthetic fixture must not create an index")):
            again, _ = r466.inspect(self.original_jar)
        self.assertEqual(again, legacy)

    def test_11_selector_requires_factory_and_boolean_result(self):
        with self.assertRaisesRegex(
                r459.Refused, "R466_HIERARCHY_SELECTOR_REQUIRES_FACTORY"):
            r459.inspect(self.original_jar,
                         hierarchy_selector=lambda *_: True)
        with self.assertRaisesRegex(
                r459.Refused, "R466_HIERARCHY_SELECTOR_RESULT_MUST_BE_BOOL"):
            r459.inspect(self.original_jar,
                         hierarchy_factory=shared.Index,
                         hierarchy_selector=lambda *_: object())
        self.assertEqual(r459.inspect(self.original_jar)[0][
            "isolated_r421_compiled_classes"], 2)

    def test_12_no_persistence_export_or_client_execution(self):
        public, _ = r466.inspect(self.original_jar)
        self.assertFalse(public["production_history_or_deletion_journal_accessed"])
        self.assertFalse(public["source_or_class_bytes_exported"])
        self.assertFalse(public["client_executed"])
        self.assertFalse(public["merge_authorized"])
        self.assertFalse(public["release_authorized"])
        self.assertEqual(sorted(self.temp.glob("SpawnPK-R466-*")), [])

    def test_13_public_CLI_does_not_require_or_print_private_jar(self):
        outcome = subprocess.run([
            sys.executable, "-B", str(CLI), "--pairs", "1"],
            capture_output=True, text=True, timeout=60, check=False)
        self.assertEqual(outcome.returncode, 0, outcome.stderr)
        parsed = json.loads(outcome.stdout)
        self.assertEqual(parsed["status"],
                         "R466_SYNTHETIC_ADAPTIVE_CACHE_BENCHMARK_UNAPPROVED")
        self.assertFalse(parsed["real_client_analyzed"])
        self.assertNotIn(str(self.temp), outcome.stdout)
        self.assertNotIn("Traceback", outcome.stderr)


if __name__ == "__main__":
    unittest.main()
