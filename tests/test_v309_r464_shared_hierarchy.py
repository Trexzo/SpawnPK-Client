"""R464 fabricated-only ancestry cache correctness and owner-audit regressions."""
from __future__ import annotations

from dataclasses import replace
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r459_consolidated_inspection as fake_owner
from tools.r453 import classfile_member_reference as r453
from tools.r454 import member_ancestry_evidence as r454
from tools.r455 import dependency_member_access as r455
from tools.r456 import member_opcode_evidence as r456
from tools.r459 import audit_consolidated_inspection as r459
from tools.r463 import benchmark_metadata_reuse as r463
from tools.r464 import shared_hierarchy as shared
from tools.r464 import benchmark_hierarchy as r464

CLI = r464.ROOT / "tools/r464/benchmark_hierarchy.py"


def fabricated():
    """Diamond-friendly supergraph with a referenced inherited member."""
    reference = r453.Member("demo/B.class", "foo", "()V", "method")
    def record(name, super_name, methods=(), references=(), flags=()):
        return r453.ClassMembers(
            name, super_name, frozenset(), frozenset(methods),
            frozenset(references), frozenset(), (), tuple(flags), 0x0001)
    rebuilt = {
        "demo/Caller.class": record(
            "demo/Caller.class", "java/lang/Object.class",
            references=(reference,)),
    }
    selected = {
        "demo/B.class": record("demo/B.class", "demo/A.class"),
        "demo/A.class": record(
            "demo/A.class", "java/lang/Object.class",
            methods=(("foo", "()V"),),
            flags=(("foo", "()V", 0x0001),)),
    }
    sites = [
        r456.Site("demo/Caller.class", "go()V", 0, "invokevirtual",
                  False, reference),
    ]
    return rebuilt, selected, sites, reference


class R464PureGraphReuse(unittest.TestCase):
    def test_01_R455_R456_parity_and_cross_stage_cache_hits(self):
        rebuilt, selected, sites, ref = fabricated()
        baseline_dependency = r455.analyze(rebuilt, selected, set(), set())
        baseline_opcode = r456.analyze(rebuilt, selected, sites, 0)
        index = shared.Index(rebuilt, selected)
        cached_dependency = r455.analyze(
            rebuilt, selected, set(), set(), shared_hierarchy=index)
        cached_opcode = r456.analyze(
            rebuilt, selected, sites, 0, shared_hierarchy=index)
        self.assertEqual(baseline_dependency, cached_dependency)
        self.assertEqual(baseline_opcode, cached_opcode)
        self.assertEqual(index.admissions, 2)
        self.assertEqual(index.ancestry_misses, 1)
        self.assertEqual(index.resolution_misses, 1)
        self.assertGreaterEqual(index.ancestry_hits, 1)
        self.assertGreaterEqual(index.resolution_hits, 1)

    def test_02_avoid_repeated_ancestry_and_lookup_decoder_calls(self):
        rebuilt, selected, sites, _ = fabricated()
        true_ancestry, true_lookup = r454.ancestry, r454.lookup
        before = {"ancestor": 0, "lookup": 0}
        after = {"ancestor": 0, "lookup": 0}

        def scan(target):
            def trace_ancestor(*args, **kwargs):
                target["ancestor"] += 1
                return true_ancestry(*args, **kwargs)
            def trace_lookup(*args, **kwargs):
                target["lookup"] += 1
                return true_lookup(*args, **kwargs)
            with patch.object(r454, "ancestry", side_effect=trace_ancestor), patch.object(
                    r454, "lookup", side_effect=trace_lookup):
                index = shared.Index(rebuilt, selected) if target is after else None
                kwargs = {} if index is None else {"shared_hierarchy": index}
                r455.analyze(rebuilt, selected, set(), set(), **kwargs)
                r456.analyze(rebuilt, selected, sites, 0, **kwargs)

        scan(before)
        scan(after)
        self.assertEqual(before, {"ancestor": 2, "lookup": 2})
        self.assertEqual(after, {"ancestor": 1, "lookup": 1})

    def test_03_different_graph_or_replaced_record_refused(self):
        rebuilt, selected, sites, ref = fabricated()
        index = shared.Index(rebuilt, selected)
        merged = {**selected, **rebuilt}
        index.admit(merged)
        altered = dict(merged)
        altered["demo/B.class"] = replace(
            altered["demo/B.class"], superclass_name="demo/Missing.class")
        with self.assertRaisesRegex(shared.Refused,
                                     "R464_CLASS_GRAPH_IDENTITY_DRIFT"):
            index.admit(altered)
        with self.assertRaises(shared.Refused):
            index.admit({**rebuilt})
        with self.assertRaises(shared.Refused):
            shared.Index(rebuilt, {**selected, **rebuilt})

    def test_04_chain_must_belong_to_exact_owner(self):
        rebuilt, selected, sites, reference = fabricated()
        index = shared.Index(rebuilt, selected)
        index.admit({**selected, **rebuilt})
        chain = index.chain("demo/B.class")
        self.assertEqual(index.resolve(reference, chain).category,
                         "superclass_signature_candidate")
        with self.assertRaisesRegex(
                shared.Refused, "R464_RESOLUTION_CHAIN_OWNER_MISMATCH"):
            index.resolve(reference, r454.Ancestry((), (), (), False, False))
        with self.assertRaises(shared.Refused):
            index.chain("demo/Nonexistent.class")

    def test_05_budgets_are_enforced_before_cache_growth(self):
        rebuilt, selected, sites, reference = fabricated()
        with patch.object(shared, "MAX_CLASSES", 1):
            with self.assertRaisesRegex(shared.Refused,
                                         "R464_CLASS_GRAPH_RECORD_INVALID"):
                shared.Index(rebuilt, selected)
        index = shared.Index(rebuilt, selected)
        with patch.object(shared, "MAX_OWNERS", 0):
            with self.assertRaisesRegex(shared.Refused, "R464_ANCESTRY_CACHE_BUDGET"):
                index.chain("demo/B.class")
        chain = index.chain("demo/B.class")
        with patch.object(shared, "MAX_RESOLUTIONS", 0):
            with self.assertRaisesRegex(shared.Refused, "R464_RESOLUTION_CACHE_BUDGET"):
                index.resolve(reference, chain)

    def test_06_rebuilt_only_R454_must_stay_separate(self):
        rebuilt, selected, sites, ref = fabricated()
        first, private = r454.analyze(
            rebuilt, set(selected), set(), set())
        shared_graph = shared.Index(rebuilt, selected)
        r455.analyze(rebuilt, selected, set(), set(),
                     shared_hierarchy=shared_graph)
        after, private_after = r454.analyze(
            rebuilt, set(selected), set(), set())
        self.assertEqual(first, after)
        self.assertEqual(private, private_after)
        self.assertNotEqual(
            r454.ancestry(rebuilt, "demo/Caller.class"),
            shared_graph.chain("demo/B.class"))


class R464FakeOwner(unittest.TestCase):
    def setUp(self):
        fake_owner.R459ConsolidatedFakeOwner.setUp(self)

    def test_07_complete_public_and_private_R463_R464_parity(self):
        old_public, old_private = r463.inspect(self.original_jar)
        new_public, new_private = r464.inspect(self.original_jar)
        self.assertEqual(old_public, new_public)
        self.assertEqual(old_private, new_private)
        self.assertEqual(new_public["full_R446_inventory_observations"], 2)
        self.assertEqual(new_public["classfile_evidence_pass_reads"], 2)
        self.assertFalse(new_public["historical_R421_full_inventory_independently_approved"])
        self.assertFalse(new_public["client_executed"])

    def test_08_exactly_one_index_admitted_twice(self):
        created = []
        actual = shared.Index
        def capture(rebuilt, selected):
            index = actual(rebuilt, selected)
            created.append(index)
            return index
        with patch.object(r464.hierarchy, "Index", side_effect=capture):
            public, _ = r464.inspect(self.original_jar)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].admissions, 2)
        self.assertEqual(public["isolated_r421_compiled_classes"], 2)

    def test_09_paired_benchmark_and_redaction(self):
        report = r464.compare(self.original_jar, pairs=2, synthetic=True)
        self.assertTrue(report["full_sha_inventory_consistent"])
        self.assertTrue(report["public_output_parity"])
        self.assertTrue(report["file_read_count_parity"])
        self.assertEqual(report["shared_index_admissions_per_audit"], 2)
        self.assertEqual(report["pairs"], 2)
        self.assertEqual(report["fixture"], "fabricated_synthetic")
        self.assertFalse(report["release_authorized"])
        self.assertEqual(
            report["R463_independent_hierarchy"][
                "median_read_calls_by_kind"]["class"], 6)
        self.assertEqual(
            report["R464_shared_hierarchy"][
                "median_read_calls_by_kind"]["class"], 6)
        payload = json.dumps(report, sort_keys=True)
        for forbidden in (str(self.temp), "LootHistoryStore",
                          "rs/Bridge", "java/lang/Class", "images/logo.png"):
            self.assertNotIn(forbidden, payload)
        print("R464_SYNTHETIC_AGGREGATE_ONLY=" + payload)

    def test_10_between_pair_full_source_SHA_drift_refused(self):
        original = r464.r459.inspect
        def altered(*args, **kwargs):
            output = original(*args, **kwargs)
            if kwargs.get("hierarchy_factory") is not None:
                src = self.source / "rs/Bridge.java"
                src.write_bytes(src.read_bytes() + b" changed")
            return output
        with patch.object(r464.r459, "inspect", side_effect=altered):
            with self.assertRaisesRegex(
                    r464.Refused, "R464_PAIRED_FULL_SHA_INVENTORY_CHANGED"):
                r464.compare(self.original_jar, pairs=1, synthetic=True)

    def test_11_missing_owner_original_CLI_redacts_paths(self):
        missing = self.temp / "private-owner-original-v309-not-present.jar"
        result = subprocess.run(
            [sys.executable, "-B", str(CLI),
             "--original-v309-jar", str(missing), "--pairs", "1"],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"],
                         "R464_HIERARCHY_BENCHMARK_REFUSED")
        self.assertNotIn(str(missing), result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_12_legacy_coordinator_works_without_R464(self):
        with patch.object(shared, "Index",
                          side_effect=AssertionError("optimized-only")):
            old, _ = r459.inspect(self.original_jar)
            self.assertEqual(old["isolated_r421_compiled_classes"], 2)
        self.assertFalse(old["client_compilation_performed"])
        self.assertFalse(old["merge_authorized"])


if __name__ == "__main__":
    unittest.main()
