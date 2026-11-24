"""R463 source-free paired metadata reuse and R457 correctness regressions."""
from __future__ import annotations

from types import SimpleNamespace
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r459_consolidated_inspection as owner_fixture
from tools.r451 import straightline_resource_operands as r451
from tools.r457 import jvm_callsite_constraints as r457
from tools.r459 import audit_consolidated_inspection as r459
from tools.r461 import shared_constant_pool as cp
from tools.r462 import shared_instruction_stream as stream
from tools.r463 import reuse_validated_metadata as meta
from tools.r463 import benchmark_metadata_reuse as r463

CLI = r463.ROOT / "tools/r463/benchmark_metadata_reuse.py"


class R463PureMetadata(unittest.TestCase):
    def test_01_descriptor_cache_independent_parsers_and_hits(self):
        value = "(Ljava/lang/String;)Ljava/io/InputStream;"
        counters = {"resource": 0, "callsite": 0}
        resource = r451.method_shape
        callsite = r457.method_shape

        def r(x):
            counters["resource"] += 1
            return resource(x)

        def c(x):
            counters["callsite"] += 1
            return callsite(x)

        with patch.object(r451, "method_shape", side_effect=r), patch.object(
                r457, "method_shape", side_effect=c):
            index = meta.DescriptorShapes()
            for _ in range(8):
                self.assertEqual(index.resource_shape(value), resource(value))
                self.assertEqual(index.callsite_shape(value), callsite(value))
        self.assertEqual(counters["resource"], 1)
        self.assertEqual(counters["callsite"], 1)
        self.assertEqual(index.resource_misses, 1)
        self.assertEqual(index.callsite_misses, 1)
        self.assertEqual(index.resource_hits, 7)
        self.assertEqual(index.callsite_hits, 7)

    def test_02_invalid_descriptor_never_cached_or_promoted(self):
        index = meta.DescriptorShapes()
        invalid = "(V)V"
        with self.assertRaises(r451.Refused):
            index.resource_shape(invalid)
        with self.assertRaises(r457.Refused):
            index.callsite_shape(invalid)
        self.assertEqual(index.resource_misses, 0)
        self.assertEqual(index.callsite_misses, 0)
        self.assertEqual(index.resource_hits, 0)

    def test_03_budget_and_input_refusal(self):
        index = meta.DescriptorShapes()
        with self.assertRaisesRegex(meta.Refused,
                                     "R463_DESCRIPTOR_INPUT_INVALID"):
            index.resource_shape(b"()V")
        with patch.object(meta, "MAX_TOTAL_DESCRIPTOR_CHARS", 1):
            with self.assertRaisesRegex(meta.Refused, "R463_DESCRIPTOR_CACHE_BUDGET"):
                index.callsite_shape("(I)V")

    def test_04_opcode_witness_exact_identity_and_count_checks(self):
        original = [SimpleNamespace(target=SimpleNamespace(kind="method")),
                    SimpleNamespace(target=SimpleNamespace(kind="field"))]
        rebuilt, selected = {}, {}
        summary = {
            "field_and_method_bytecode_sites_inspected": 2,
            "invoke_method_site_count": 1,
            "get_put_field_site_count": 1,
            "static_instance_opcode_declaration_conflicts": 0,
            "method_or_field_owner_unavailable": 1,
        }
        witness = meta.witness(rebuilt, selected, original, 0, summary)
        self.assertEqual(meta.admit(witness, rebuilt, selected, original, 0),
                         summary)
        with self.assertRaisesRegex(meta.Refused, "R463_PRIOR_OPCODE_INPUT_IDENTITY_MISMATCH"):
            meta.admit(witness, rebuilt, selected, list(original), 0)
        with self.assertRaises(meta.Refused):
            meta.admit(witness, rebuilt, selected, original, 1)
        with self.assertRaises(meta.Refused):
            meta.admit(witness, {}, selected, original, 0)
        tampered = dict(summary)
        tampered["invoke_method_site_count"] = 2
        with self.assertRaisesRegex(meta.Refused, "R463_PRIOR_OPCODE_SITE_TOTAL_DISAGREEMENT"):
            meta.witness(rebuilt, selected, original, 0, tampered)
        self.assertEqual(meta.admit(witness, rebuilt, selected, original, 0),
                         summary)

    def test_05_wrong_static_method_counts_cannot_be_used(self):
        sites = [SimpleNamespace(target=SimpleNamespace(kind="field"))]
        summary = {
            "field_and_method_bytecode_sites_inspected": 1,
            "invoke_method_site_count": 1,
            "get_put_field_site_count": 0,
            "static_instance_opcode_declaration_conflicts": 0,
            "method_or_field_owner_unavailable": 0,
        }
        w = meta.witness({}, {}, sites, 0, summary)
        with self.assertRaisesRegex(meta.Refused, "R463_PRIOR_OPCODE_COUNTS_DISAGREE"):
            meta.admit(w, w.rebuilt, w.selected, sites, 0)

    def test_06_legacy_R457_api_keeps_unmodified_defaults(self):
        self.assertTrue(callable(r457.method_shape))
        self.assertTrue(callable(r457.analyze))
        self.assertTrue(callable(r457.site_issues))
        self.assertEqual(r451.method_shape("(J)V"), (1, False, True))
        self.assertEqual(r457.method_shape("(J)V").parameter_slots, 2)


class R463SyntheticOwner(unittest.TestCase):
    def setUp(self):
        owner_fixture.R459ConsolidatedFakeOwner.setUp(self)

    def test_07_full_public_and_owner_private_parity_with_R462(self):
        old_public, old_private = r459.inspect(
            self.original_jar, shared_pool_factory=cp.decode,
            shared_instruction_factory=stream.Index)
        new_public, new_private = r463.inspect(self.original_jar)
        self.assertEqual(new_public, old_public)
        self.assertEqual(new_private, old_private)
        self.assertEqual(new_public["full_R446_inventory_observations"], 2)
        self.assertEqual(new_public["classfile_evidence_pass_reads"], 2)
        self.assertFalse(new_public["client_executed"])
        self.assertFalse(new_public["historical_R421_full_inventory_independently_approved"])

    def test_08_two_pairs_benchmark_and_one_R456_classification(self):
        data = r463.compare(self.original_jar, pairs=2, synthetic=True)
        self.assertTrue(data["aggregate_output_parity"])
        self.assertTrue(data["bounded_file_reads_identical"])
        self.assertEqual(data["R456_legacy_calls_per_audit"], 2)
        self.assertEqual(data["R456_optimized_calls_per_audit"], 1)
        self.assertEqual(
            data["R462_repeated_metadata"]["median_stage_calls"]["opcode_analysis"], 2)
        self.assertEqual(
            data["R463_reused_metadata"]["median_stage_calls"]["opcode_analysis"], 1)
        self.assertEqual(data["pairs"], 2)
        self.assertEqual(data["fixture"], "fabricated_synthetic")
        self.assertFalse(data["release_authorized"])
        exported = json.dumps(data, sort_keys=True)
        for private in (str(self.temp), "LootHistoryStore", "rs/Bridge",
                        "images/logo.png", "java/lang/Class"):
            self.assertNotIn(private, exported)
        print("R463_SYNTHETIC_AGGREGATE_ONLY=" + exported)

    def test_09_refuses_source_mutation_after_optimized_scan(self):
        actual = r463.r459.inspect
        def altered(*args, **kwargs):
            output = actual(*args, **kwargs)
            if kwargs.get("reuse_opcode_summary"):
                file = self.source / "rs/Bridge.java"
                file.write_bytes(file.read_bytes() + b" changed")
            return output
        with patch.object(r463.r459, "inspect", side_effect=altered):
            with self.assertRaisesRegex(r463.Refused,
                                        "R463_PAIRED_FULL_SHA_INPUT_CHANGED"):
                r463.compare(self.original_jar, pairs=1, synthetic=True)

    def test_10_untrusted_public_CLI_missing_client_does_not_leak_paths(self):
        missing = self.temp / "private-owner-client-unavailable.jar"
        result = subprocess.run(
            [sys.executable, "-B", str(CLI),
             "--original-v309-jar", str(missing), "--pairs", "1"],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"],
                         "R463_SHARED_METADATA_BENCHMARK_REFUSED")
        self.assertNotIn(str(missing), result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_11_no_private_cache_or_production_change(self):
        report, _ = r463.inspect(self.original_jar)
        self.assertFalse(report["production_history_or_deletion_journal_accessed"])
        self.assertFalse(report["client_compilation_performed"])
        self.assertFalse(report["release_authorized"])
        self.assertFalse(report["merge_authorized"])
        self.assertEqual(sorted(self.temp.glob("SpawnPK-R463-*")), [])

    def test_12_cross_path_default_and_opt_in_are_not_confused(self):
        with patch.object(meta, "witness",
                          side_effect=AssertionError("optimized only")):
            report, _ = r459.inspect(self.original_jar)
            self.assertEqual(report["isolated_r421_compiled_classes"], 2)
        self.assertFalse(report["merge_authorized"])


if __name__ == "__main__":
    unittest.main()
