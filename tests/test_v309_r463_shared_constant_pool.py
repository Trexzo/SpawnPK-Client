"""R463 entirely fabricated Java11 constant-pool sharing and exact-evidence tests.

The three CP consumers R450/R453/R458 preserve their independent strict
semantic validation. No real recovered JAR, owner sources, player history,
runtime, credentials or external assets are used in public CI.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r450_generic_resource_proximity as r450_fixture
import test_v309_r453_member_reference_coverage as r453_fixture
import test_v309_r458_bootstrap_callsite as r458_fixture
from tools.r450 import classfile_signature_resource as r450
from tools.r453 import classfile_member_reference as r453
from tools.r458 import bootstrap_callsite_evidence as r458
from tools.r459 import audit_consolidated_inspection as r459
from tools.r463 import constant_pool_view as cpview

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r459/audit_consolidated_inspection.py"


def fixtures():
    return (
        r450_fixture.invented_classfile(),
        r453_fixture.fake_member_class(),
        r458_fixture.sample(),
        r458_fixture.sample(opcode="condy"),
        r458_fixture.sample(opcode="condy2",
                            dynamic_descriptor="J"),
    )


def no_resource(_):
    return None


def legacy_consumer_results(raw):
    return (
        r453.parse_class(raw),
        r458.scan_class(raw),
        r450.classfile_evidence(raw, no_resource),
    )


def shared_consumer_results(raw):
    view=cpview.parse(raw)
    return (
        r453.parse_class(raw,shared_pool=view),
        r458.scan_class(raw,shared_pool=view),
        r450.classfile_evidence(raw,no_resource,shared_pool=view),
    )


class R463SharedPoolPure(unittest.TestCase):
    def test_01_three_parsers_produce_equal_evidence_on_real_fabricated_classfiles(self):
        for i, raw in enumerate(fixtures()):
            with self.subTest(fixture=i):
                self.assertEqual(
                    legacy_consumer_results(raw),
                    shared_consumer_results(raw))

    def test_02_all_parsers_retained_without_optional_view(self):
        raw=r453_fixture.fake_member_class()
        self.assertEqual(r453.parse_class(raw).class_name,"rs/Widget.class")
        self.assertEqual(r458.scan_class(raw).bootstrap_entries,0)
        self.assertEqual(r450.classfile_evidence(raw,no_resource)[2],0)

    def test_03_view_matches_exact_raw_CP_token_layout(self):
        raw=r458_fixture.sample()
        view=cpview.parse(raw)
        self.assertIs(view.raw,raw)
        self.assertEqual(view.major,55)
        self.assertEqual(view.count,len(view.tags))
        self.assertEqual(view.count,len(view.entries))
        self.assertEqual(view.tags[0],0)
        self.assertGreater(view.end,10)
        self.assertLess(view.end,len(raw))
        self.assertIn(18,view.tags)
        self.assertIn(17,view.tags)
        self.assertIn(15,view.tags)
        self.assertIn(16,view.tags)

    def test_04_parsed_CP_tokens_immutable_in_view(self):
        view=cpview.parse(r453_fixture.fake_member_class())
        self.assertIsInstance(view.tags,tuple)
        self.assertIsInstance(view.entries,tuple)
        with self.assertRaises(FrozenInstanceError):
            view.count=2

    def test_05_different_but_equal_bytes_are_refused_in_every_adapter(self):
        raw=r458_fixture.sample()
        view=cpview.parse(raw)
        other=bytes(bytearray(raw))
        self.assertEqual(other,raw)
        self.assertIsNot(other,raw)
        for adapter in (
            lambda:r453.parse_class(other,shared_pool=view),
            lambda:r458.scan_class(other,shared_pool=view),
            lambda:r450.classfile_evidence(
                other,no_resource,shared_pool=view),
        ):
            with self.assertRaisesRegex(
                    (r450.Refused,r453.Refused,r458.Refused),
                    "R4[0-9][0-9]_R463_INPUT_MISMATCH"):
                adapter()

    def test_06_wrong_class_pool_cannot_be_substituted(self):
        data=r453_fixture.fake_member_class()
        view=cpview.parse(r458_fixture.sample())
        for adapter in (
            lambda:r453.parse_class(data,shared_pool=view),
            lambda:r458.scan_class(data,shared_pool=view),
            lambda:r450.classfile_evidence(
                data,no_resource,shared_pool=view),
        ):
            with self.assertRaises((
                    r450.Refused,r453.Refused,r458.Refused)):
                adapter()

    def test_07_untrusted_non_pool_instance_rejected(self):
        data=r453_fixture.fake_member_class()
        for adapter in (
            lambda:r453.parse_class(data,shared_pool=object()),
            lambda:r458.scan_class(data,shared_pool=object()),
            lambda:r450.classfile_evidence(
                data,no_resource,shared_pool=object()),
        ):
            with self.assertRaises((
                    r450.Refused,r453.Refused,r458.Refused)):
                adapter()

    def test_08_view_not_reused_between_classfiles(self):
        a,b=fixtures()[:2]
        pool=cpview.parse(a)
        with self.assertRaises(cpview.Refused):
            pool.validate_for(b)

    def test_09_magic_and_major_version_strict(self):
        raw=r453_fixture.fake_member_class()
        for altered in (
            b"FAKE"+raw[4:],
            raw[:6]+(56).to_bytes(2,"big")+raw[8:],
            raw[:6]+(52).to_bytes(2,"big")+raw[8:],
            b"",
            "not raw bytes",
        ):
            with self.subTest(altered_type=type(altered).__name__):
                with self.assertRaisesRegex(
                        cpview.Refused,"R463_EXACT_JAVA11_CLASS_BYTES_REQUIRED"):
                    cpview.parse(altered)

    def test_10_truncated_CP_payload_refused(self):
        raw=r453_fixture.fake_member_class()
        for blob in (raw[:8],raw[:10],raw[:11],raw[:13],
                     b"\xca\xfe\xba\xbe\x00\x00\x00\x37\x00\x02\x01\x00\x05x"):
            with self.subTest(n=len(blob)):
                with self.assertRaises(cpview.Refused):
                    cpview.parse(blob)

    def test_11_unknown_CP_tag_rejected(self):
        raw=r453_fixture.fake_member_class()
        blob=raw[:10]+b"\xff"+raw[11:]
        with self.assertRaisesRegex(
                cpview.Refused,"R463_UNSUPPORTED_CONSTANT_POOL_TAG"):
            cpview.parse(blob)

    def test_12_invalid_CP_count_zero_refused(self):
        raw=r453_fixture.fake_member_class()
        with self.assertRaisesRegex(
                cpview.Refused,"R463_BAD_CONSTANT_POOL_COUNT"):
            cpview.parse(raw[:8]+b"\x00\x00"+raw[10:])

    def test_13_double_slot_last_entry_refused(self):
        raw=b"\xca\xfe\xba\xbe\x00\x00\x00\x37\x00\x02"+b"\x05"+b"\x00"*8
        with self.assertRaisesRegex(
                cpview.Refused,"R463_DOUBLE_SLOT_CP_OVERFLOW"):
            cpview.parse(raw)

    def test_14_int_and_float_opaque_are_not_claimed_descriptor_evidence(self):
        raw=b"\xca\xfe\xba\xbe\x00\x00\x00\x37\x00\x03"+(
            b"\x03"+b"\x00"*4 + b"\x04"+b"\x00"*4)
        view=cpview.parse(raw)
        self.assertEqual(view.tags[1:],(3,4))
        self.assertIsNone(view.entries[1])
        self.assertIsNone(view.entries[2])

    def test_15_utf_malformed_byte_matches_legacy_replacement_semantics(self):
        head=b"\xca\xfe\xba\xbe\x00\x00\x00\x37\x00\x02"
        view=cpview.parse(head+b"\x01\x00\x01\xff")
        self.assertEqual(view.entries[1],"\ufffd")

    def test_16_invalid_method_handle_kind_refused_by_R458_after_shared_CP(self):
        raw=r458_fixture.sample(handle_kind=0)
        view=cpview.parse(raw)
        for shared in (None,view):
            with self.subTest(shared=shared is not None):
                with self.assertRaisesRegex(
                        r458.Refused,"R458_INVALID_METHOD_HANDLE_KIND"):
                    r458.scan_class(raw,shared_pool=shared)

    def test_17_wrong_handle_ref_tag_refused_by_R458_after_shared_CP(self):
        raw=r458_fixture.sample(handle_kind=6,handle_target_kind=9)
        view=cpview.parse(raw)
        for shared in (None,view):
            with self.assertRaisesRegex(
                    r458.Refused,"R458_HANDLE_REFERENCE_KIND_TAG_MISMATCH"):
                r458.scan_class(raw,shared_pool=shared)

    def test_18_bad_bootstrap_record_refused_by_R458_after_shared_CP(self):
        raw=r458_fixture.sample(bsm_index=1)
        view=cpview.parse(raw)
        for shared in (None,view):
            with self.assertRaisesRegex(
                    r458.Refused,"R458_DYNAMIC_BOOTSTRAP_INDEX_MISSING"):
                r458.scan_class(raw,shared_pool=shared)

    def test_19_bad_R450_signature_refused_even_with_valid_pool_view(self):
        raw=r450_fixture.invented_classfile(bad_class_signature="Lrs/Bad")
        view=cpview.parse(raw)
        for shared in (None,view):
            with self.assertRaises(r450.Refused):
                r450.classfile_evidence(raw,no_resource,shared_pool=shared)

    def test_20_truncated_class_structure_after_CP_refused_by_all_adapters(self):
        raw=r453_fixture.fake_member_class()
        truncated=raw[:cpview.parse(raw).end]+b"\x00"
        view=cpview.parse(truncated)
        for adapter in (
            lambda:r453.parse_class(truncated,shared_pool=view),
            lambda:r458.scan_class(truncated,shared_pool=view),
            lambda:r450.classfile_evidence(
                truncated,no_resource,shared_pool=view),
        ):
            with self.assertRaises((
                    r450.Refused,r453.Refused,r458.Refused)):
                adapter()

    def test_21_R450_resource_and_generic_evidence_exact_match(self):
        raw=r450_fixture.invented_classfile()
        view=cpview.parse(raw)
        self.assertEqual(
            r450.classfile_evidence(raw,r450_fixture.r450.r449.resource_literal),
            r450.classfile_evidence(
                raw,r450_fixture.r450.r449.resource_literal,
                shared_pool=view))

    def test_22_invokedynamic_and_condy_evidence_equal_with_shared_CP(self):
        for kind,extra in (
            ("indy",{}),("condy",{}),("condy_w",{}),
            ("condy2",{"dynamic_descriptor":"J"})):
            with self.subTest(kind=kind):
                raw=r458_fixture.sample(opcode=kind,**extra)
                pool=cpview.parse(raw)
                self.assertEqual(
                    r458.scan_class(raw),
                    r458.scan_class(raw,shared_pool=pool))

    def test_23_R453_legacy_java8_dependency_path_unchanged(self):
        raw=r453_fixture.fake_member_class()
        java8=raw[:6]+(52).to_bytes(2,"big")+raw[8:]
        result=r453.parse_class(java8,allowed_majors=tuple(range(45,56)))
        self.assertEqual(result.class_name,"rs/Widget.class")
        with self.assertRaises(cpview.Refused):
            cpview.parse(java8)


class R463InventedOwnerConsolidation(unittest.TestCase):
    def setUp(self):
        r458_fixture.R458OwnerInventedOffline.setUp(self)

    def test_24_R459_shared_CP_read_once_per_class_evidence_pass(self):
        original=cpview.parse
        with patch.object(cpview,"parse",wraps=original) as spy:
            report,_=r459.inspect(self.original_jar)
        self.assertEqual(spy.call_count,2)
        self.assertEqual(report["R463_shared_constant_pool_decodes"],2)
        self.assertEqual(report["R463_constant_pool_adapters_per_class"],3)
        self.assertEqual(report["classfile_evidence_pass_reads"],2)

    def test_25_full_R459_output_and_private_worklist_parity(self):
        normal,private=r459.inspect(self.original_jar)
        parse450=r450.classfile_evidence
        parse453=r453.parse_class
        parse458=r458.scan_class

        def old450(*args,**kwargs):
            kwargs.pop("shared_pool",None)
            return parse450(*args,**kwargs)

        def old453(*args,**kwargs):
            kwargs.pop("shared_pool",None)
            return parse453(*args,**kwargs)

        def old458(*args,**kwargs):
            kwargs.pop("shared_pool",None)
            return parse458(*args,**kwargs)

        with patch.object(r450,"classfile_evidence",side_effect=old450), \
             patch.object(r453,"parse_class",side_effect=old453), \
             patch.object(r458,"scan_class",side_effect=old458):
            legacy,legacy_private=r459.inspect(self.original_jar)
        self.assertEqual(normal,legacy)
        self.assertEqual(private,legacy_private)

    def test_26_aggregate_has_no_private_source_names(self):
        report,_=r459.inspect(self.original_jar)
        dumped=json.dumps(report,sort_keys=True)
        for secret in ("LootHistoryStore","rs/Bridge.class",
                       str(self.temp),"textures/missing.png",
                       "java/lang/Class"):
            self.assertNotIn(secret,dumped)

    def test_27_valid_fabricated_owner_sha_and_custody_still_checked(self):
        report,_=r459.inspect(self.original_jar)
        self.assertEqual(report["full_R446_inventory_observations"],2)
        self.assertTrue(report["pinned_original_archive_re_read_after_evidence_pass"])
        self.assertTrue(report["entire_current_inventory_consistent_after_evidence_pass"])
        self.assertFalse(report["historical_R421_full_inventory_independently_approved"])

    def test_28_owner_compiled_class_mutation_refused(self):
        original=r459.cpview.parse
        triggered=[False]
        def mutate(raw):
            if not triggered[0]:
                triggered[0]=True
                f=self.compiled/"rs/Bridge.class"
                f.write_bytes(b"not same original class")
            return original(raw)
        with patch.object(r459.cpview,"parse",side_effect=mutate):
            with self.assertRaises((
                    r459.Refused,r459.r446.Refused)):
                r459.inspect(self.original_jar)

    def test_29_shared_pool_view_does_not_cross_audits(self):
        old=cpview.parse
        seen=[]
        def record(raw):
            result=old(raw)
            seen.append(result)
            return result
        with patch.object(r459.cpview,"parse",side_effect=record):
            r459.inspect(self.original_jar)
            r459.inspect(self.original_jar)
        self.assertEqual(len(seen),4)
        self.assertEqual(len({id(x) for x in seen}),4)

    def test_30_no_client_runtime_or_history_work(self):
        report,_=r459.inspect(self.original_jar)
        for flag in ("client_executed","client_compilation_performed",
                     "production_history_or_deletion_journal_accessed",
                     "release_authorized","merge_authorized",
                     "complete_original_source_or_asset_parity_proven"):
            self.assertFalse(report[flag])


if __name__=="__main__":
    unittest.main()
