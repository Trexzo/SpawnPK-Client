"""R462 fabricated-only shared JVM instruction stream and audit parity tests."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r458_bootstrap_callsite as r458_fixture
import test_v309_r459_consolidated_inspection as owner_fixture
from tools.r450 import classfile_signature_resource as r450
from tools.r459 import audit_consolidated_inspection as r459
from tools.r461 import shared_constant_pool as cp
from tools.r462 import shared_instruction_stream as stream
from tools.r462 import benchmark_instruction_index as r462

CLI = r462.ROOT / "tools/r462/benchmark_instruction_index.py"


class R462PureInstructionStream(unittest.TestCase):
    def test_01_shared_instruction_boundaries_exactly_match_legacy(self):
        cases = (
            b"\xb1",                       # return
            b"\x12\x01\x57\xb1",           # ldc, pop, return
            b"\x99\x00\x03\xb1",           # branch + return
            b"\xc4\x15\x00\x01\xb1",       # wide iload + return
            b"\xaa\x00\x00\x00" + b"\x00" * 16 + b"\xb1",
            b"\xab\x00\x00\x00" + b"\x00" * 8 + b"\xb1",
        )
        index = stream.Index()
        for case in cases:
            expected = r450.instructions(case)
            first = r450.instructions(case, shared_instructions=index)
            second = r450.instructions(bytes(bytearray(case)), shared_instructions=index)
            self.assertEqual(tuple(expected), first)
            self.assertIs(first, second)
        self.assertEqual(index.misses, len(cases))
        self.assertEqual(index.hits, len(cases))

    def test_02_truncated_reserved_and_bad_wide_have_original_refusal(self):
        for case in (b"\xff", b"\xc4", b"\xc4\x00\x00\x00", b"\xa7\x00",
                     b"\xaa", b"\xab"):
            with self.assertRaises(r450.Refused) as independent:
                r450.instructions(case)
            with self.assertRaises(r450.Refused) as optimized:
                r450.instructions(case, shared_instructions=stream.Index())
            self.assertEqual(str(independent.exception),
                             str(optimized.exception))

    def test_03_same_stream_cached_once_and_never_persisted(self):
        cache = stream.Index()
        raw = b"\xb1"
        actual = r450._instructions_uncached
        counts = [0]
        def counted(data):
            counts[0] += 1
            return actual(data)
        with patch.object(r450, "_instructions_uncached", side_effect=counted):
            for _ in range(7):
                self.assertEqual(
                    r450.instructions(raw, shared_instructions=cache),
                    ((0, 0xb1, b""),))
        self.assertEqual(counts[0], 1)
        self.assertEqual(cache.hits, 6)
        self.assertEqual(cache.misses, 1)
        self.assertEqual(cache.bytes_decoded, 1)

    def test_04_wrong_cache_type_or_mutable_input_refused(self):
        for cache, data in ((object(), b"\xb1"),
                            (stream.Index(), bytearray(b"\xb1"))):
            with self.assertRaisesRegex(
                    stream.Refused, "R462_INSTRUCTION_INDEX_INPUT_REFUSED"):
                r450.instructions(data, shared_instructions=cache)

    def test_05_class_local_byte_and_opcode_budget_refusal(self):
        with patch.object(stream, "MAX_TOTAL_CODE_BYTES", 1):
            cache = stream.Index()
            r450.instructions(b"\xb1", shared_instructions=cache)
            with self.assertRaisesRegex(
                    stream.Refused, "R462_INSTRUCTION_INDEX_CLASS_BUDGET"):
                r450.instructions(b"\x00\xb1", shared_instructions=cache)
        with patch.object(stream, "MAX_TOTAL_INSTRUCTIONS", 0):
            with self.assertRaisesRegex(
                    stream.Refused, "R462_INSTRUCTION_INDEX_OPCODE_BUDGET"):
                r450.instructions(b"\xb1", shared_instructions=stream.Index())

    def test_06_dynamic_and_condy_parity_with_shared_instruction_cache(self):
        for opcode in ("indy", "condy", "condy_w", "condy2", "unused"):
            options = {"opcode": opcode}
            if opcode == "condy2":
                options["dynamic_descriptor"] = "J"
            data = r458_fixture.sample(**options)
            ix = cp.decode(data)
            cache = stream.Index()
            from tools.r458 import bootstrap_callsite_evidence as r458
            expected = r458.scan_class(data, shared_pool=ix)
            result = r458.scan_class(
                data, shared_pool=ix, shared_instructions=cache)
            self.assertEqual(expected, result)
            self.assertGreaterEqual(cache.misses, 1)
            self.assertEqual(r458.scan_class(
                data, shared_pool=ix, shared_instructions=cache), result)
            self.assertGreaterEqual(cache.hits, 1)


class R462FakeOwner(unittest.TestCase):
    def setUp(self):
        owner_fixture.R459ConsolidatedFakeOwner.setUp(self)

    def test_07_r459_r461_and_r462_match_public_and_private(self):
        old_report, old_private = r459.inspect(self.original_jar)
        r461_report, r461_private = r459.inspect(
            self.original_jar, shared_pool_factory=cp.decode)
        r462_report, r462_private = r462.inspect(self.original_jar)
        self.assertEqual(old_report, r461_report)
        self.assertEqual(r461_report, r462_report)
        self.assertEqual(old_private, r461_private)
        self.assertEqual(r461_private, r462_private)
        self.assertEqual(old_report["full_R446_inventory_observations"], 2)
        self.assertEqual(r462_report["classfile_evidence_pass_reads"], 2)
        self.assertFalse(r462_report["client_executed"])
        self.assertFalse(r462_report["historical_R421_full_inventory_independently_approved"])

    def test_08_one_index_per_class_with_shared_decoder_cache_hits(self):
        caches = []
        def create():
            index = stream.Index()
            caches.append(index)
            return index
        result, _ = r459.inspect(
            self.original_jar, shared_pool_factory=cp.decode,
            shared_instruction_factory=create)
        self.assertEqual(len(caches), 2)
        self.assertEqual(result["isolated_r421_compiled_classes"], 2)
        self.assertGreater(sum(x.hits for x in caches), 0)
        self.assertGreater(sum(x.misses for x in caches), 0)
        self.assertGreater(sum(x.hits for x in caches),
                           sum(x.misses for x in caches))

    def test_09_two_pair_synthetic_R461_R462_benchmark(self):
        result = r462.compare(self.original_jar, pairs=2, synthetic=True)
        self.assertEqual(result["pairs"], 2)
        self.assertTrue(result["aggregate_output_parity"])
        self.assertTrue(result["file_read_count_parity"])
        self.assertTrue(result["full_SHA_input_consistency"])
        self.assertGreater(result["median_instruction_cache_hits"], 0)
        self.assertEqual(result["median_ephemeral_class_indices"], 2)
        self.assertEqual(
            result["R461_independent_instructions"][
                "median_read_calls_by_kind"]["class"], 6)
        self.assertEqual(
            result["R462_shared_instructions"][
                "median_read_calls_by_kind"]["class"], 6)
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["synthetic_speedup_generalizes_to_owner"])
        stdout = json.dumps(result, sort_keys=True)
        for forbidden in (str(self.temp), "LootHistoryStore",
                          "rs/Bridge", "java/lang/Class", "images/logo.png"):
            self.assertNotIn(forbidden, stdout)
        print("R462_SYNTHETIC_AGGREGATE_ONLY=" + stdout)

    def test_10_refuse_current_source_sha_change_between_pair(self):
        original = r462.r459.inspect
        def altered(path, *args, **kwargs):
            output = original(path, *args, **kwargs)
            if kwargs.get("shared_instruction_factory") is not None:
                path = self.source / "rs/Bridge.java"
                path.write_bytes(path.read_bytes() + b" mutated")
            return output
        with patch.object(r462.r459, "inspect", side_effect=altered):
            with self.assertRaisesRegex(
                    r462.Refused, "R462_FULL_INPUT_SHA_CHANGED_ACROSS_PAIR"):
                r462.compare(self.original_jar, pairs=1, synthetic=True)

    def test_11_cli_missing_original_redacted(self):
        nonexistent = self.temp / "private-original-client-no-copy-v309.jar"
        process = subprocess.run([
            sys.executable, "-B", str(CLI),
            "--original-v309-jar", str(nonexistent), "--pairs", "1"],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(process.returncode, 2, process.stderr)
        self.assertEqual(json.loads(process.stdout)["status"],
                         "R462_SHARED_INSTRUCTION_BENCHMARK_REFUSED")
        self.assertNotIn(str(nonexistent), process.stdout)
        self.assertNotIn("Traceback", process.stderr)

    def test_12_no_persistent_history_class_or_jar_exports(self):
        result, _ = r462.inspect(self.original_jar)
        self.assertFalse(result["production_history_or_deletion_journal_accessed"])
        self.assertFalse(result["client_compilation_performed"])
        self.assertFalse(result["merge_authorized"])
        self.assertFalse(result["release_authorized"])
        self.assertEqual(sorted(self.temp.glob("SpawnPK-R462-*")), [])


if __name__ == "__main__":
    unittest.main()
