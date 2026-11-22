"""R462 fabricated JVM generic Signature grammar LRU isolation tests.

Validates exact R450 grammar parity, bounded in-audit cache, immutable
results, private output boundaries and unchanged R459 SHA-gated evidence.
No recovered SpawnPK code, owner classfiles or player histories involved.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import unittest
from unittest.mock import patch

import test_v309_r450_generic_resource_proximity as r450_fixture
import test_v309_r458_bootstrap_callsite as owner_fixture
from tools.r450 import classfile_signature_resource as r450
from tools.r459 import audit_consolidated_inspection as r459
from tools.r461 import profile_scoped_decoder as profiler

FIELD = "Ljava/util/List<Lrs/Thing;>;"
ANOTHER = "Ljava/util/Map<Lrs/Key;Lrs/Value;>;"
CLASS = "Ljava/lang/Object;"
METHOD = "<T:Lrs/Bound;>()Lrs/Result;^Lrs/Error;"


def examine(*pairs):
    @r450.scoped_instruction_cache
    def audit():
        values = [r450.generic_signature_refs(sig, kind)
                  for sig, kind in pairs]
        return {"values": values}, {"safe": True}
    return audit()


class R462SignatureCachePure(unittest.TestCase):
    def test_01_legacy_default_parser_unchanged(self):
        for sig, kind in ((FIELD,"field"),(ANOTHER,"field"),
                          (CLASS,"class"),(METHOD,"method")):
            self.assertEqual(
                r450.generic_signature_refs(sig, kind),
                r450._generic_signature_refs_uncached(sig, kind))
        self.assertIsNone(r450._R461_ACTIVE_CACHE.get())

    def test_02_repeated_valid_signature_reused_in_same_audit(self):
        report,_=examine((FIELD,"field"),(FIELD,"field"))
        self.assertEqual(report["R462_scoped_generic_signature_hits"],1)
        self.assertEqual(report["R462_scoped_generic_signature_misses"],1)
        self.assertEqual(report["values"][0],report["values"][1])

    def test_03_key_includes_full_JVM_signature_kind(self):
        report,_=examine((CLASS,"field"),(CLASS,"class"))
        self.assertEqual(report["R462_scoped_generic_signature_misses"],2)
        self.assertEqual(report["R462_scoped_generic_signature_hits"],0)

    def test_04_mutating_returned_set_cannot_poison_cache(self):
        @r450.scoped_instruction_cache
        def audit():
            first=r450.generic_signature_refs(FIELD,"field")
            first.clear()
            again=r450.generic_signature_refs(FIELD,"field")
            return {"result":again},{}
        report,_=audit()
        self.assertEqual(report["result"],
                         {"java/util/List.class","rs/Thing.class"})
        self.assertEqual(report["R462_scoped_generic_signature_hits"],1)

    def test_05_invalid_signature_refused_and_not_cached(self):
        @r450.scoped_instruction_cache
        def audit():
            for _ in range(2):
                with self.assertRaises(r450.Refused):
                    r450.generic_signature_refs("Lrs/Bad","field")
            return {},{}
        report,_=audit()
        self.assertEqual(report["R462_scoped_generic_signature_misses"],2)
        self.assertEqual(report["R462_cached_signatures_at_exit"],0)

    def test_06_invalid_kind_refused_under_cache(self):
        with self.assertRaisesRegex(r450.Refused,"R450_UNKNOWN_SIGNATURE_KIND"):
            examine((FIELD,"not-a-jvm-signature-kind"))
        self.assertIsNone(r450._R461_ACTIVE_CACHE.get())

    def test_07_unhashable_invalid_argument_refused_without_typeerror(self):
        for value in ([],None,{"sig":FIELD}):
            with self.subTest(value=value):
                with self.assertRaises(r450.Refused):
                    examine((value,"field"))

    def test_08_single_entry_lru_eviction(self):
        with patch.object(r450,"R462_MAX_CACHED_SIGNATURES",1):
            report,_=examine((FIELD,"field"),(ANOTHER,"field"),
                             (FIELD,"field"))
        self.assertEqual(report["R462_scoped_generic_signature_misses"],3)
        self.assertEqual(report["R462_generic_signature_cache_evictions"],2)
        self.assertEqual(report["R462_cached_signatures_at_exit"],1)

    def test_09_total_char_budget_eviction(self):
        with patch.object(r450,"R462_MAX_SIGNATURE_CHARS_TOTAL",len(FIELD)+1):
            report,_=examine((FIELD,"field"),(CLASS,"class"),
                             (FIELD,"field"))
        self.assertEqual(report["R462_generic_signature_cache_evictions"],2)

    def test_10_reference_name_budget_eviction(self):
        with patch.object(r450,"R462_MAX_CACHED_REFERENCE_NAMES",2):
            report,_=examine((FIELD,"field"),
                             ("Ljava/util/Set<Lrs/Thing;>;","field"),
                             (FIELD,"field"))
        self.assertEqual(report["R462_generic_signature_cache_evictions"],2)

    def test_11_oversize_signature_skips_but_still_fully_parses(self):
        with patch.object(r450,"R462_MAX_SIGNATURE_CHARS_PER_ENTRY",1):
            report,_=examine((FIELD,"field"),(FIELD,"field"))
        self.assertEqual(report["R462_uncacheable_signature_skips"],2)
        self.assertEqual(report["R462_cached_signatures_at_exit"],0)
        self.assertEqual(report["values"][0],
                         {"java/util/List.class","rs/Thing.class"})

    def test_12_zero_max_signature_entries_does_not_store(self):
        with patch.object(r450,"R462_MAX_CACHED_SIGNATURES",0):
            report,_=examine((FIELD,"field"),(FIELD,"field"))
        self.assertEqual(report["R462_scoped_generic_signature_hits"],0)
        self.assertEqual(report["R462_cached_signatures_at_exit"],0)
        self.assertEqual(report["R462_uncacheable_signature_skips"],2)

    def test_13_zero_reference_names_budget_skips(self):
        with patch.object(r450,"R462_MAX_CACHED_REFERENCE_NAMES",0):
            report,_=examine((CLASS,"class"),(CLASS,"class"))
        self.assertEqual(report["R462_uncacheable_signature_skips"],2)
        self.assertEqual(report["R462_scoped_generic_signature_hits"],0)

    def test_14_two_audits_do_not_reuse_cache(self):
        x,_=examine((FIELD,"field"),(FIELD,"field"))
        y,_=examine((FIELD,"field"))
        self.assertEqual(x["R462_scoped_generic_signature_hits"],1)
        self.assertEqual(y["R462_scoped_generic_signature_hits"],0)
        self.assertIsNone(r450._R461_ACTIVE_CACHE.get())

    def test_15_scope_restored_on_signature_exception(self):
        with self.assertRaises(r450.Refused):
            examine(("Lbad","field"))
        self.assertIsNone(r450._R461_ACTIVE_CACHE.get())

    def test_16_threads_do_not_share_generic_signature_cache(self):
        def worker(i):
            report,_=examine((FIELD,"field"),(FIELD,"field"))
            return report["R462_scoped_generic_signature_hits"]
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(worker,range(8))),[1]*8)

    def test_17_original_grammar_is_executed_once_per_unique_key(self):
        original=r450._generic_signature_refs_uncached
        with patch.object(r450,"_generic_signature_refs_uncached",
                          wraps=original) as spy:
            report,_=examine((FIELD,"field"),(FIELD,"field"),
                             (FIELD,"field"))
        self.assertEqual(spy.call_count,1)
        self.assertEqual(report["R462_scoped_generic_signature_hits"],2)

    def test_18_real_R450_synthetic_classfile_caches_signatures_across_reads(self):
        raw=r450_fixture.invented_classfile()
        @r450.scoped_instruction_cache
        def audit():
            a=r450.classfile_evidence(raw,lambda _:None)
            b=r450.classfile_evidence(raw,lambda _:None)
            return {"same":a==b},{}
        report,_=audit()
        self.assertTrue(report["same"])
        self.assertGreaterEqual(report["R462_scoped_generic_signature_hits"],3)

    def test_19_each_cache_is_bounded_by_entries(self):
        entries=[(f"Lrs/Synthetic{i};","field") for i in range(200)]
        report,_=examine(*entries)
        self.assertLessEqual(report["R462_cached_signatures_at_exit"],
                             r450.R462_MAX_CACHED_SIGNATURES)
        self.assertGreater(report["R462_generic_signature_cache_evictions"],0)

    def test_20_signature_cache_does_not_replace_bytecode_cache(self):
        report,_=examine((FIELD,"field"),(FIELD,"field"))
        self.assertEqual(report["R461_scoped_instruction_decode_hits"],0)
        self.assertEqual(report["R461_scoped_instruction_decode_misses"],0)
        self.assertTrue(report["R462_signature_cache_does_not_persist"])


class R462OwnerSyntheticParity(unittest.TestCase):
    def setUp(self):
        owner_fixture.R458OwnerInventedOffline.setUp(self)

    def test_21_new_scoped_signature_cache_keeps_exact_R459_private_parity(self):
        uncached, old_detail=r459.inspect.__wrapped__(self.original_jar)
        scoped, new_detail=r459.inspect(self.original_jar)
        profiler.require_parity(uncached,scoped,old_detail,new_detail)
        self.assertEqual(old_detail,new_detail)

    def test_22_SHA_and_compiled_read_pass_counts_unchanged(self):
        report,_=r459.inspect(self.original_jar)
        self.assertEqual(report["full_R446_inventory_observations"],2)
        self.assertEqual(report["classfile_evidence_pass_reads"],2)
        self.assertTrue(report["entire_current_inventory_consistent_after_evidence_pass"])
        self.assertFalse(report["historical_R421_full_inventory_independently_approved"])

    def test_23_scope_cache_stats_are_aggregate_only(self):
        report,_=r459.inspect(self.original_jar)
        text=json.dumps(report)
        for private in ("LootHistoryStore","images/logo.png",
                        str(self.temp),"rs/Bridge.class"):
            self.assertNotIn(private,text)
        self.assertIn("R462_scoped_generic_signature_misses",report)

    def test_24_original_pin_mutation_refuses_before_cache_evidence(self):
        self.original_jar.write_bytes(b"wrong original")
        with self.assertRaises(r459.r447.Refused):
            r459.inspect(self.original_jar)

    def test_25_report_never_claims_full_original_runtime_or_merge(self):
        report,_=r459.inspect(self.original_jar)
        for flag in ("client_executed",
                     "client_compilation_performed",
                     "complete_original_source_or_asset_parity_proven",
                     "jvm_linkage_verified",
                     "production_history_or_deletion_journal_accessed",
                     "release_authorized","merge_authorized"):
            self.assertFalse(report[flag])


if __name__=="__main__":
    unittest.main()
