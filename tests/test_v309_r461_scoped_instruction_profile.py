"""R461 synthetic per-audit JVM instruction decoding cache and cProfile tests.

All original/source/class/dependency data are invented owner TEMP fixtures.
All live client and R415/R417 persistent history interactions are prohibited.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r458_bootstrap_callsite as fixture_module
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r450 import classfile_signature_resource as r450
from tools.r459 import audit_consolidated_inspection as r459
from tools.r461 import profile_scoped_decoder as r461

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r461/profile_scoped_decoder.py"


def run_small_cache(*codes):
    @r450.scoped_instruction_cache
    def audit():
        decoded = [r450.instructions(code) for code in codes]
        return {"decoded": decoded}, {"safe": True}
    return audit()


class R461ScopedDecodePure(unittest.TestCase):
    def test_01_instructions_legacy_path_matches_explicit_uncached(self):
        for code in (b"\xb1", b"\x00\xb1", b"\xb6\x00\x01\xb1",
                     b"\xb9\x00\x02\x01\x00\xb1"):
            with self.subTest(code=code):
                self.assertEqual(r450.instructions(code),
                                 r450._instructions_uncached(code))

    def test_02_same_code_second_use_is_cache_hit(self):
        summary,_ = run_small_cache(b"\x00\xb1",b"\x00\xb1")
        self.assertEqual(summary["R461_scoped_instruction_decode_misses"],1)
        self.assertEqual(summary["R461_scoped_instruction_decode_hits"],1)
        self.assertEqual(summary["decoded"][0],summary["decoded"][1])

    def test_03_cache_never_returns_shared_mutable_list(self):
        @r450.scoped_instruction_cache
        def audit():
            first=r450.instructions(b"\x00\xb1")
            first.append((999,999,b"unsafe"))
            second=r450.instructions(b"\x00\xb1")
            return {"same":second == [(0,0,b""),(1,0xb1,b"")]},{}
        report,_=audit()
        self.assertTrue(report["same"])

    def test_04_two_separate_audits_never_share_cached_code(self):
        a,_=run_small_cache(b"\xb1",b"\xb1")
        b,_=run_small_cache(b"\xb1")
        self.assertEqual(a["R461_scoped_instruction_decode_hits"],1)
        self.assertEqual(b["R461_scoped_instruction_decode_hits"],0)
        self.assertEqual(b["R461_scoped_instruction_decode_misses"],1)
        self.assertIsNone(r450._R461_ACTIVE_CACHE.get())

    def test_05_scope_restores_after_exception(self):
        @r450.scoped_instruction_cache
        def broken():
            r450.instructions(b"\xb1")
            raise ValueError("invented failure")
        with self.assertRaisesRegex(ValueError,"invented failure"):
            broken()
        self.assertIsNone(r450._R461_ACTIVE_CACHE.get())

    def test_06_nested_scopes_refuse_without_erasing_outer_context(self):
        @r450.scoped_instruction_cache
        def nested():
            with self.assertRaisesRegex(
                    r450.Refused,"R461_NESTED_INSTRUCTION_CACHE_NOT_ALLOWED"):
                run_small_cache(b"\xb1")
            return {"outer":True},{}
        report,_=nested()
        self.assertTrue(report["outer"])
        self.assertIsNone(r450._R461_ACTIVE_CACHE.get())

    def test_07_tiny_lru_entry_budget_evicts_old_code(self):
        with patch.object(r450,"R461_MAX_CACHED_METHODS",1):
            report,_=run_small_cache(b"\xb1",b"\x00\xb1",b"\xb1")
        self.assertEqual(report["R461_scoped_instruction_decode_misses"],3)
        self.assertEqual(report["R461_instruction_decode_evictions"],2)
        self.assertEqual(report["R461_cached_method_bodies_at_exit"],1)

    def test_08_tiny_byte_budget_evicts(self):
        with patch.object(r450,"R461_MAX_CACHED_CODE_BYTES",3):
            report,_=run_small_cache(b"\x00\xb1",b"\x00\x00\xb1",b"\x00\xb1")
        self.assertEqual(report["R461_scoped_instruction_decode_misses"],3)
        self.assertEqual(report["R461_instruction_decode_evictions"],2)

    def test_09_uncacheable_long_method_is_counted_and_still_decoded(self):
        with patch.object(r450,"R461_MAX_METHOD_CODE_BYTES",1):
            report,_=run_small_cache(b"\x00\xb1",b"\x00\xb1")
        self.assertEqual(report["R461_oversize_method_cache_skips"],2)
        self.assertEqual(report["R461_scoped_instruction_decode_hits"],0)
        self.assertEqual(report["R461_cached_method_bodies_at_exit"],0)

    def test_10_strict_reserved_opcode_rejection_preserved_in_cache(self):
        with self.assertRaises(r450.Refused):
            run_small_cache(b"\xca")
        self.assertIsNone(r450._R461_ACTIVE_CACHE.get())

    def test_11_truncated_branch_rejection_preserved_in_cache(self):
        with self.assertRaises(r450.Refused):
            run_small_cache(b"\xa7\x00")
        self.assertIsNone(r450._R461_ACTIVE_CACHE.get())

    def test_12_invalid_method_code_type_refused(self):
        with self.assertRaises(r450.Refused):
            run_small_cache("not bytes")

    def test_13_cached_methods_do_not_exceed_byte_and_instruction_budgets(self):
        report,_=run_small_cache(
            *[bytes([0])*i+b"\xb1" for i in range(1,80)])
        self.assertLessEqual(report["R461_cached_method_bodies_at_exit"],
                             r450.R461_MAX_CACHED_METHODS)
        self.assertGreater(report["R461_instruction_decode_evictions"],0)

    def test_14_contextvars_isolate_parallel_tasks(self):
        def worker(i):
            report,_=run_small_cache(b"\x00"*i+b"\xb1",
                                     b"\x00"*i+b"\xb1")
            return report["R461_scoped_instruction_decode_hits"]
        with ThreadPoolExecutor(max_workers=3) as pool:
            self.assertEqual(list(pool.map(worker,range(1,7))),[1]*6)
        self.assertIsNone(r450._R461_ACTIVE_CACHE.get())

    def test_15_unknown_code_body_cache_miss_never_creates_empty_success(self):
        with patch.object(r450,"_instructions_uncached",
                          wraps=r450._instructions_uncached) as spy:
            report,_=run_small_cache(b"\xb1",b"\xb1",b"\xb1")
        self.assertEqual(spy.call_count,1)
        self.assertEqual(report["R461_scoped_instruction_decode_hits"],2)

    def test_16_profile_safename_filter_denies_filepaths(self):
        for name in ("/home/private/file.py","C:\\owner\\private",
                     "<method 'read' of bytes>", "a b", "a.b"):
            self.assertFalse(r461.safe_stat_names(name))
        self.assertTrue(r461.safe_stat_names("instructions"))

    def test_17_profiling_symbol_allowlist_is_public_code(self):
        self.assertIn("classfile_signature_resource.py",r461.ALLOWLIST)
        self.assertNotIn("client.jar",r461.ALLOWLIST)
        self.assertEqual(len(r461.EVIDENCE_KEYS),15)


class R461FakeOwnerComparison(unittest.TestCase):
    def setUp(self):
        fixture_module.R458OwnerInventedOffline.setUp(self)

    def test_18_cached_R459_has_same_public_evidence_and_private_worklist(self):
        raw, raw_private=r459.inspect.__wrapped__(self.original_jar)
        scoped, scoped_private=r459.inspect(self.original_jar)
        r461.require_parity(raw,scoped,raw_private,scoped_private)
        self.assertEqual(scoped_private,raw_private)
        self.assertGreater(scoped["R461_scoped_instruction_decode_hits"],0)

    def test_19_actual_R450_instruction_reparses_reduced(self):
        original=r450._instructions_uncached
        with patch.object(r450,"_instructions_uncached",wraps=original) as spy:
            bare,_=r459.inspect.__wrapped__(self.original_jar)
            bare_count=spy.call_count
            spy.reset_mock()
            cached,_=r459.inspect(self.original_jar)
            cached_count=spy.call_count
        self.assertGreater(bare_count,cached_count)
        self.assertGreater(cached["R461_scoped_instruction_decode_hits"],0)
        self.assertEqual(bare["R456_actual_member_instruction_sites"],
                         cached["R456_actual_member_instruction_sites"])

    def test_20_scoped_cache_keeps_R459_compiled_file_read_counts_unchanged(self):
        baseline,_=r459.inspect.__wrapped__(self.original_jar)
        scoped,_=r459.inspect(self.original_jar)
        self.assertEqual(baseline["classfile_evidence_pass_reads"],2)
        self.assertEqual(scoped["classfile_evidence_pass_reads"],2)
        self.assertEqual(scoped["full_R446_inventory_observations"],2)

    def test_21_default_R459_report_does_not_contain_private_names(self):
        result,_=r459.inspect(self.original_jar)
        text=json.dumps(result,sort_keys=True)
        for secret in ("rs/plugins/loottracker/LootHistoryStore",
                       "textures/missing.png",str(self.temp),
                       r425.PINNED_R421_STORE_SHA):
            self.assertNotIn(secret,text)

    def test_22_cprofile_uses_public_module_symbol_names_only(self):
        result=r461.run(self.original_jar,synthetic=True)
        self.assertEqual(result["status"],
                         "R461_SYNTHETIC_PARSER_PROFILE_UNAPPROVED")
        self.assertTrue(
            result["shared_static_evidence_and_private_worklists_exactly_match"])
        self.assertGreater(result["scoped_R459"]["instruction_decode_hits"],0)
        for mode in ("uncached_R459","scoped_R459"):
            self.assertGreater(result[mode]["profile"][
                "allowlisted_function_symbols_examined"],0)
            for entry in result[mode][
                    "hottest_public_symbols_by_Python_self_time"]:
                self.assertIn(entry["module"],r461.ALLOWLIST)
                self.assertTrue(r461.safe_stat_names(entry["symbol"]))

    def test_23_modified_pinned_original_refused_before_profiler(self):
        self.original_jar.write_bytes(b"not exact v309")
        with self.assertRaises(r461.r447.Refused):
            r461.run(self.original_jar,synthetic=True)

    def test_24_source_mutation_between_cprofile_comparisons_refused(self):
        original=r461.profile_one
        count=[0]
        def change(*args,**kwargs):
            result=original(*args,**kwargs)
            count[0]+=1
            if count[0]==1:
                file=self.source/"rs/Bridge.java"
                file.write_bytes(file.read_bytes()+b" changed")
            return result
        with patch.object(r461,"profile_one",side_effect=change):
            with self.assertRaises((
                    r461.r446.Refused,r459.Refused,r461.Refused)):
                r461.run(self.original_jar,synthetic=True)

    def test_25_cprofile_does_not_claim_runtime_or_R421_history(self):
        result=r461.run(self.original_jar,synthetic=True)
        for key in ("real_owner_speedup_measured",
                    "runtime_client_network_latency_or_FPS_measured",
                    "class_or_source_names_from_owner_in_report",
                    "source_or_class_bytes_uploaded",
                    "historical_R421_full_inventory_independently_approved",
                    "player_history_or_R415_R417_journals_accessed",
                    "merge_authorized","release_authorized"):
            self.assertFalse(result[key])


class R461SyntheticCLI(unittest.TestCase):
    def test_26_cli_synthetic_runs_without_uploaded_source(self):
        p=subprocess.run([sys.executable,"-B",str(CLI),"--synthetic"],
                         capture_output=True,text=True,check=False,timeout=25)
        self.assertEqual(p.returncode,0,p.stderr)
        obj=json.loads(p.stdout)
        self.assertEqual(obj["status"],
                         "R461_SYNTHETIC_PARSER_PROFILE_UNAPPROVED")
        self.assertTrue(obj["source_classes_and_dependencies_unchanged"])

    def test_27_owner_mode_missing_original_refused_no_path(self):
        path=ROOT/"missing-owner-private-original-v309.jar"
        p=subprocess.run([sys.executable,"-B",str(CLI),
                          "--owner-original-v309-jar",str(path)],
                         capture_output=True,text=True,check=False,timeout=15)
        self.assertEqual(p.returncode,2,p.stderr)
        obj=json.loads(p.stdout)
        self.assertEqual(obj["status"],"R461_STATIC_PARSER_PROFILE_REFUSED")
        self.assertNotIn(str(path),p.stdout)
        self.assertFalse(obj["release_authorized"])


if __name__=="__main__":
    unittest.main()
