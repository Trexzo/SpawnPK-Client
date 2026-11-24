"""R461 fabricated-only CP index and independent-parser parity regressions."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r458_bootstrap_callsite as fixtures
import test_v309_r459_consolidated_inspection as owner_fixture
from tools.r450 import classfile_signature_resource as r450
from tools.r453 import classfile_member_reference as r453
from tools.r458 import bootstrap_callsite_evidence as r458
from tools.r459 import audit_consolidated_inspection as r459
from tools.r461 import shared_constant_pool as pool
from tools.r461 import benchmark_shared_index as r461

CLI = r461.ROOT / "tools/r461/benchmark_shared_index.py"


class R461PureJava11(unittest.TestCase):
    def test_01_original_independent_parsers_equal_shared_index_results(self):
        for variant in ("indy", "condy", "condy_w", "condy2", "unused"):
            kwargs = {"opcode": variant}
            if variant == "condy2":
                kwargs["dynamic_descriptor"] = "J"
            data = fixtures.sample(**kwargs)
            index = pool.decode(data)
            self.assertIs(index.raw, data)
            self.assertIsInstance(index.tags, tuple)
            self.assertIsInstance(index.entries, tuple)
            self.assertGreater(index.end_offset, 10)
            self.assertEqual(r453.parse_class(data),
                             r453.parse_class(data, shared_pool=index))
            self.assertEqual(r458.scan_class(data),
                             r458.scan_class(data, shared_pool=index))
            self.assertEqual(
                r450.classfile_evidence(data, lambda _: None),
                r450.classfile_evidence(data, lambda _: None,
                                        shared_pool=index))

    def test_02_wrong_bytes_identity_cannot_reuse_index(self):
        data = fixtures.sample()
        index = pool.decode(data)
        copied = bytes(bytearray(data))
        self.assertEqual(copied, data)
        self.assertIsNot(copied, data)
        for parser in (
            lambda: r453.parse_class(copied, shared_pool=index),
            lambda: r458.scan_class(copied, shared_pool=index),
            lambda: r450.classfile_evidence(
                copied, lambda _: None, shared_pool=index),
        ):
            with self.assertRaisesRegex(
                    pool.Refused, "R461_SHARED_INDEX_INPUT_MISMATCH"):
                parser()
        other = fixtures.sample(opcode="unused")
        with self.assertRaises(pool.Refused):
            r453.parse_class(other, shared_pool=index)

    def test_03_reject_mutable_and_malformed_tag_bytes(self):
        valid = fixtures.sample()
        with self.assertRaises(pool.Refused):
            pool.decode(bytearray(valid))
        bad = bytearray(valid)
        bad[10] = 0xff
        with self.assertRaisesRegex(pool.Refused, "R461_UNKNOWN_CP_TAG"):
            pool.decode(bytes(bad))
        with self.assertRaises(pool.Refused):
            pool.decode(valid[:11])

    def test_04_invalid_bootstrap_metadata_still_rejected(self):
        scenarios = (
            {"bsm_index": 1},
            {"reserved_bytes": b"\x00\x01"},
            {"handle_kind": 1},
        )
        for kwargs in scenarios:
            data = fixtures.sample(**kwargs)
            index = pool.decode(data)
            with self.assertRaises(r458.Refused) as reference:
                r458.scan_class(data)
            with self.assertRaises(r458.Refused) as reused:
                r458.scan_class(data, shared_pool=index)
            self.assertEqual(str(reference.exception), str(reused.exception))

    def test_05_frozen_index_cannot_be_modified(self):
        data = fixtures.sample()
        result = pool.decode(data)
        with self.assertRaises(FrozenInstanceError):
            result.count = 99

    def test_06_rejects_non_java11_and_invalid_cp_count(self):
        wrong_major = fixtures.sample(old_major=54)
        with self.assertRaises(pool.Refused):
            pool.decode(wrong_major)
        wrong_cp = bytearray(fixtures.sample())
        wrong_cp[8:10] = b"\x00\x00"
        with self.assertRaisesRegex(pool.Refused, "R461_INVALID_CP_COUNT"):
            pool.decode(bytes(wrong_cp))


class R461SyntheticOwner(unittest.TestCase):
    def setUp(self):
        owner_fixture.R459ConsolidatedFakeOwner.setUp(self)

    def test_07_r459_reports_and_private_worklists_identical(self):
        old_public, old_private = r459.inspect(self.original_jar)
        new_public, new_private = r461.inspect(self.original_jar)
        self.assertEqual(old_public, new_public)
        self.assertEqual(old_private, new_private)
        self.assertEqual(old_public["full_R446_inventory_observations"], 2)
        self.assertEqual(old_public["classfile_evidence_pass_reads"], 2)
        self.assertFalse(new_public["client_executed"])
        self.assertFalse(new_public["merge_authorized"])

    def test_08_exactly_one_index_for_each_evidence_class(self):
        actual = pool.decode
        calls = [0]
        def measured(raw):
            calls[0] += 1
            return actual(raw)
        with patch.object(pool, "decode", side_effect=measured):
            output, _ = r461.inspect(self.original_jar)
        self.assertEqual(calls[0], 2)
        self.assertEqual(output["isolated_r421_compiled_classes"], 2)

    def test_09_counterbalanced_paired_benchmark(self):
        report = r461.compare(self.original_jar, pairs=2, synthetic=True)
        self.assertEqual(report["pairs"], 2)
        self.assertEqual(report["fixture"], "fabricated_synthetic")
        self.assertEqual(report["median_shared_pool_decodes"], 2)
        self.assertTrue(report["aggregate_output_parity"])
        self.assertTrue(report["same_bounded_file_reads"])
        self.assertTrue(report["full_SHA_input_consistency"])
        self.assertEqual(
            report["R459_independent"]["median_read_calls_by_kind"]["class"], 6)
        self.assertEqual(
            report["R461_shared_index"]["median_read_calls_by_kind"]["class"], 6)
        self.assertFalse(report["release_authorized"])
        self.assertFalse(report["synthetic_speedup_generalizes_to_owner"])
        exported = json.dumps(report, sort_keys=True)
        for secret in ("LootHistoryStore", "rs/Bridge", "java/lang/Class",
                       "images/logo.png", str(self.temp)):
            self.assertNotIn(secret, exported)
        print("R461_SYNTHETIC_AGGREGATE_ONLY=" + exported)

    def test_10_source_change_across_benchmark_pair_refused(self):
        original = r461.r459.inspect
        def tamper(path, *args, **kwargs):
            result = original(path, *args, **kwargs)
            if kwargs.get("shared_pool_factory") is not None:
                src = self.source / "rs/Bridge.java"
                src.write_bytes(src.read_bytes() + b" tampered")
            return result
        with patch.object(r461.r459, "inspect", side_effect=tamper):
            with self.assertRaisesRegex(r461.Refused,
                                        "R461_FULL_INPUT_SHA_CHANGED_ACROSS_PAIR"):
                r461.compare(self.original_jar, pairs=1, synthetic=True)

    def test_11_missing_owner_original_redacts_path_and_refuses(self):
        nonexistent = self.temp / "private-NOT-ACTUAL-v309-client.jar"
        process = subprocess.run(
            [sys.executable, "-B", str(CLI),
             "--original-v309-jar", str(nonexistent), "--pairs", "1"],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(process.returncode, 2, process.stderr)
        self.assertEqual(json.loads(process.stdout)["status"],
                         "R461_SHARED_CP_BENCHMARK_REFUSED")
        self.assertNotIn(str(nonexistent), process.stdout)
        self.assertNotIn("Traceback", process.stderr)

    def test_12_no_persistent_index_cache_or_unapproved_promotion(self):
        self.assertIn("UNAPPROVED", r461.SCHEMA)
        report, _ = r461.inspect(self.original_jar)
        self.assertFalse(report["historical_R421_full_inventory_independently_approved"])
        self.assertFalse(report["source_or_class_bytes_exported"])
        self.assertFalse(report["release_authorized"])
        self.assertEqual(sorted(self.temp.glob("SpawnPK-R461-*")), [])


if __name__ == "__main__":
    unittest.main()
