"""R456 entirely fabricated JVM opcode/member declaration regressions.

Uses synthetic Java11 method bodies, bytecode and owner TEMP fixtures only.
Never reads or executes actual SpawnPK source/JAR/history.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r450_generic_resource_proximity as r450_fixture
import test_v309_r454_member_ancestry_evidence as ancestry_fixture
import test_v309_r455_dependency_member_access as owner_fixture
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r453 import classfile_member_reference as member
from tools.r456 import member_opcode_evidence as kinds
from tools.r456 import audit_member_opcode_staticness as r456

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r456/audit_member_opcode_staticness.py"


def cp(index: int):
    if index == 1:
        return ("rs/Target", "value", "I", "field")
    if index == 2:
        return ("rs/Target", "execute", "()V", "method")
    if index == 3:
        return ("rs/API", "run", "(I)V", "interface_method")
    if index == 4:
        return ("rs/Target", "construct", "()V", "method")
    raise kinds.Refused("R456_SYNTHETIC_CP_REFERENCE_MISSING")


def parse(code: bytes):
    return kinds.decoded_sites("rs/Caller.class","test()V",code,cp)


def field_target(name="value", flags=0x0008):
    return ancestry_fixture.make_record(
        "rs/Target.class", None,
        fields=((name,"I",flags),),
        methods=(("execute","()V",1),("construct","()V",8)))


def class_record(*refs):
    return ancestry_fixture.make_record(
        "rs/Caller.class", None, refs=tuple(refs))


def site(name, opcode, target, pc=0, static=None):
    op=dict(kinds.FIELD_OPS,**{}) if False else None
    table = {**kinds.FIELD_OPS, **kinds.METHOD_OPS}
    action, static_value = table[opcode]
    return kinds.Site("rs/Caller.class", "test()V",
                      pc, action,
                      static_value if static is None else static,
                      target)


class R456PureInstructions(unittest.TestCase):
    def test_01_exact_field_opcodes_are_distinguished_from_CP_only(self):
        events, dynamic=parse(b"\xb2\x00\x01\xb3\x00\x01"
                             b"\xb4\x00\x01\xb5\x00\x01\xb1")
        self.assertEqual(dynamic,0)
        self.assertEqual([s.operation for s in events],
                         ["getstatic","putstatic","getfield","putfield"])
        self.assertEqual([s.pc for s in events],[0,3,6,9])
        self.assertEqual([s.static_opcode for s in events],
                         [True,True,False,False])

    def test_02_invocation_opcodes_include_interface_and_static(self):
        events,dynamic=parse(
            b"\xb6\x00\x02\xb7\x00\x02\xb8\x00\x02"
            b"\xb9\x00\x03\x02\x00\xb1")
        self.assertEqual([s.operation for s in events],
                         ["invokevirtual","invokespecial",
                          "invokestatic","invokeinterface"])
        self.assertEqual([s.pc for s in events],[0,3,6,9])
        self.assertEqual(dynamic,0)

    def test_03_unused_CP_reference_not_an_observed_opcode(self):
        events,_=parse(b"\x00\xb1")
        self.assertEqual(events,())

    def test_04_valid_invokedynamic_counted_as_unknown_not_invented_member(self):
        events,dynamic=parse(b"\xba\x00\x08\x00\x00\xb1")
        self.assertEqual(dynamic,1)
        self.assertEqual(events,())

    def test_05_invokedynamic_nonzero_reserved_bytes_refused(self):
        with self.assertRaisesRegex(
                kinds.Refused,"R456_INVOKEDYNAMIC_ZERO_OPERANDS_REQUIRED"):
            parse(b"\xba\x00\x08\x00\x01\xb1")

    def test_06_wrong_field_CP_kind_refused(self):
        with self.assertRaisesRegex(
                kinds.Refused,"R456_FIELD_OR_METHOD_CP_TAG_MISMATCH"):
            parse(b"\xb2\x00\x02\xb1")

    def test_07_wrong_method_CP_kind_refused(self):
        with self.assertRaisesRegex(
                kinds.Refused,"R456_FIELD_OR_METHOD_CP_TAG_MISMATCH"):
            parse(b"\xb8\x00\x01\xb1")

    def test_08_wrong_invokevirtual_CP_kind_refused(self):
        with self.assertRaisesRegex(
                kinds.Refused,"R456_INVOKEVIRTUAL_NEEDS_METHODREF"):
            parse(b"\xb6\x00\x03\xb1")

    def test_09_wrong_invokeinterface_CP_kind_refused(self):
        with self.assertRaisesRegex(
                kinds.Refused,"R456_INVOKEINTERFACE_NEEDS_INTERFACE_METHODREF"):
            parse(b"\xb9\x00\x02\x02\x00\xb1")

    def test_10_invokeinterface_count_zero_or_reserved_nonzero_refused(self):
        for code in (b"\xb9\x00\x03\x00\x00\xb1",
                     b"\xb9\x00\x03\x02\x01\xb1"):
            with self.subTest(code=code):
                with self.assertRaisesRegex(
                        kinds.Refused,
                        "R456_INVOKEINTERFACE_COUNT_OR_ZERO_INVALID"):
                    parse(code)

    def test_11_invalid_instruction_boundary_refused(self):
        with self.assertRaisesRegex(
                kinds.Refused,"R456_UNSAFE_INSTRUCTION_BOUNDARY"):
            parse(b"\xb6\x00")

    def test_12_duplicate_offset_in_distinct_methods_permitted(self):
        a=kinds.Collector("rs/Caller.class")
        a("first()V",b"\xb8\x00\x02\xb1",cp)
        a("other()V",b"\xb8\x00\x02\xb1",cp)
        self.assertEqual(len(a.sites),2)
        self.assertEqual(a.methods_with_code,2)
        self.assertEqual({x.source_method for x in a.sites},
                         {"first()V","other()V"})

    def test_13_r450_real_code_callback_only_instruction_sites(self):
        collector=kinds.Collector(
            "rs/plugins/loottracker/LootHistoryStore.class")
        raw=r450_fixture.invented_classfile()
        r456.classfile.classfile_evidence(
            raw,r456.r449.resource_literal,member_observer=collector)
        self.assertEqual(len(collector.sites),2)
        self.assertEqual({s.operation for s in collector.sites},
                         {"invokevirtual"})
        self.assertEqual(collector.dynamic_sites,0)


class R456StaticInstanceClassification(unittest.TestCase):
    def test_14_getstatic_on_static_field_is_an_advisory_match(self):
        t=member.Member("rs/Target.class","value","I","field")
        summary,_=kinds.analyze(
            {"rs/Caller.class":class_record(t)},
            {"rs/Target.class":field_target()},
            [site("getstatic",0xb2,t)],0)
        self.assertEqual(summary["opcode_and_declaration_static_flags_agree"],1)
        self.assertFalse(summary["jvm_linkage_or_runtime_dispatch_verified"])

    def test_15_getfield_on_static_field_is_static_instance_conflict(self):
        t=member.Member("rs/Target.class","value","I","field")
        summary,private=kinds.analyze(
            {"rs/Caller.class":class_record(t)},
            {"rs/Target.class":field_target()},
            [site("getfield",0xb4,t)],0)
        self.assertEqual(summary["static_instance_opcode_declaration_conflicts"],1)
        self.assertEqual(private["private_bytecode_member_opcode_leads"][0][
            "advisory_classification"],
            "static_instance_opcode_declaration_conflict")
        self.assertFalse(summary["all_opcode_static_conflicts_proven_runtime_errors"])

    def test_16_putstatic_on_instance_field_is_static_instance_conflict(self):
        t=member.Member("rs/Target.class","value","I","field")
        summary,_=kinds.analyze(
            {"rs/Caller.class":class_record(t)},
            {"rs/Target.class":field_target(flags=1)},
            [site("putstatic",0xb3,t)],0)
        self.assertEqual(summary["static_instance_opcode_declaration_conflicts"],1)

    def test_17_invokevirtual_on_static_method_is_conflict(self):
        t=member.Member("rs/Target.class","construct","()V","method")
        summary,_=kinds.analyze(
            {"rs/Caller.class":class_record(t)},
            {"rs/Target.class":field_target()},
            [site("invokevirtual",0xb6,t)],0)
        self.assertEqual(summary["static_instance_opcode_declaration_conflicts"],1)

    def test_18_invokestatic_on_instance_method_is_conflict(self):
        t=member.Member("rs/Target.class","execute","()V","method")
        summary,_=kinds.analyze(
            {"rs/Caller.class":class_record(t)},
            {"rs/Target.class":field_target()},
            [site("invokestatic",0xb8,t)],0)
        self.assertEqual(summary["static_instance_opcode_declaration_conflicts"],1)

    def test_19_valid_instance_invokespecial_method_not_conflict(self):
        t=member.Member("rs/Target.class","execute","()V","method")
        summary,_=kinds.analyze(
            {"rs/Caller.class":class_record(t)},
            {"rs/Target.class":field_target()},
            [site("invokespecial",0xb7,t)],0)
        self.assertEqual(summary["opcode_and_declaration_static_flags_agree"],1)

    def test_20_missing_owner_not_reported_as_broken_link(self):
        t=member.Member("lib/Missing.class","go","()V","method")
        summary,_=kinds.analyze(
            {"rs/Caller.class":class_record(t)}, {},
            [site("invokevirtual",0xb6,t)],0)
        self.assertEqual(summary["method_or_field_owner_unavailable"],1)
        self.assertEqual(summary["static_instance_opcode_declaration_conflicts"],0)

    def test_21_inherited_parent_static_field_conflict_is_candidate_only(self):
        t=member.Member("rs/Target.class","value","I","field")
        child=ancestry_fixture.make_record(
            "rs/Target.class","lib/Parent.class")
        parent=ancestry_fixture.make_record(
            "lib/Parent.class",None,fields=(("value","I",8),))
        summary,_=kinds.analyze(
            {"rs/Caller.class":class_record(t),
             "rs/Target.class":child},
            {"lib/Parent.class":parent},
            [site("getfield",0xb4,t)],0)
        self.assertEqual(summary["static_instance_opcode_declaration_conflicts"],1)

    def test_22_inherited_multi_provider_ambiguity_not_falsely_confirmed(self):
        t=member.Member("rs/Target.class","go","()V","method")
        child=ancestry_fixture.make_record(
            "rs/Target.class",None,("rs/I1.class","rs/I2.class"))
        i1=ancestry_fixture.make_record(
            "rs/I1.class",None,methods=(("go","()V",1),))
        i2=ancestry_fixture.make_record(
            "rs/I2.class",None,methods=(("go","()V",1),))
        summary,_=kinds.analyze(
            {"rs/Caller.class":class_record(t),
             "rs/Target.class":child,
             "rs/I1.class":i1,
             "rs/I2.class":i2},
            {},[site("invokevirtual",0xb6,t)],0)
        self.assertEqual(summary["ambiguous_inherited_declarations"],1)
        self.assertEqual(summary["static_instance_opcode_declaration_conflicts"],0)

    def test_23_absent_signature_unknown_external_parent_not_claimed_error(self):
        t=member.Member("rs/Target.class","unknown","()V","method")
        child=ancestry_fixture.make_record(
            "rs/Target.class","lib/Unexamined.class")
        summary,_=kinds.analyze(
            {"rs/Caller.class":class_record(t),
             "rs/Target.class":child}, {},
            [site("invokevirtual",0xb6,t)],0)
        self.assertEqual(summary["incomplete_or_uncertain_ancestry"],1)

    def test_24_unknown_interface_owner_kind_still_not_JVM_proof(self):
        t=member.Member("rs/Target.class","execute","()V","method")
        target=replace(field_target(),access_flags=0x0201)
        summary,_=kinds.analyze(
            {"rs/Caller.class":class_record(t)},
            {"rs/Target.class":target},
            [site("invokevirtual",0xb6,t)],0)
        self.assertEqual(summary["interface_invoke_kind_uncertainties"],1)

    def test_25_clinit_direct_invocation_is_uncertain(self):
        t=member.Member("rs/Target.class","<clinit>","()V","method")
        record=ancestry_fixture.make_record(
            "rs/Target.class",None,methods=(("<clinit>","()V",0x0008),))
        summary,_=kinds.analyze(
            {"rs/Caller.class":class_record(t)},
            {"rs/Target.class":record},
            [site("invokestatic",0xb8,t)],0)
        # A static/instance match is not more authoritative than the
        # forbidden <clinit> bytecode invocation.
        self.assertEqual(summary["special_initializer_invocation_uncertainties"],1)

    def test_26_reject_duplicate_real_site_pc(self):
        t=member.Member("rs/Target.class","value","I","field")
        evidence=site("getstatic",0xb2,t)
        with self.assertRaisesRegex(
                kinds.Refused,"R456_DUPLICATE_BYTECODE_PC_SITE"):
            kinds.analyze(
                {"rs/Caller.class":class_record(t)},
                {"rs/Target.class":field_target()},
                [evidence,evidence],0)

    def test_27_class_and_dependency_shadowing_refused(self):
        record=field_target()
        with self.assertRaisesRegex(
                kinds.Refused,"R456_CLASS_PRECEDENCE_CONFLICT"):
            kinds.analyze(
                {"rs/Target.class":record},
                {"rs/Target.class":record},[],0)

    def test_28_unknown_bytecode_reachability_is_explicit(self):
        t=member.Member("rs/Target.class","execute","()V","method")
        summary,private=kinds.analyze(
            {"rs/Caller.class":class_record(t)},
            {"rs/Target.class":field_target()},
            [site("invokestatic",0xb8,t)],0)
        self.assertFalse(summary["unreachable_bytecode_excluded"])
        self.assertTrue(private["opcode_sites_are_static_not_proven_executed"])
        self.assertFalse(private["possible_linkage_error_requires_real_JVM_verification"] is False)

    def test_29_invokedynamic_count_never_fabricates_member(self):
        summary,_=kinds.analyze(
            {"rs/Caller.class":class_record()}, {},[],3)
        self.assertEqual(summary[
            "invokedynamic_sites_without_static_owner_resolution"],3)
        self.assertEqual(summary["field_and_method_bytecode_sites_inspected"],0)


class R456OwnerFakePipeline(unittest.TestCase):
    def setUp(self):
        owner_fixture.R455OwnerSafeSyntheticPipeline.setUp(self)

    def private_reports(self):
        return sorted(self.temp.glob(r456.PREFIX+"*"))

    def test_30_full_fake_original_and_compiled_input_admission(self):
        report, detail=r456.inspect(self.original_jar)
        self.assertEqual(report["status"],
                         "R456_JAVA11_OPCODE_MEMBER_STATICNESS_UNAPPROVED")
        self.assertEqual(report["original_v309_classes"],5)
        self.assertEqual(report["original_v309_resources"],2)
        self.assertEqual(report["isolated_r421_java_sources"],2)
        self.assertEqual(report["isolated_r421_compiled_classes"],2)
        self.assertEqual(report["invoke_method_site_count"],2)
        self.assertEqual(report["method_or_field_owner_unavailable"],2)
        self.assertEqual(report["get_put_field_site_count"],0)
        self.assertFalse(report["real_static_linkage_proven"])
        self.assertEqual(detail["schema"],r456.SCHEMA)

    def test_31_default_stdout_aggregate_only_no_private_files(self):
        summary=r456.run(self.original_jar)
        self.assertFalse(summary["private_worklist_created"])
        self.assertEqual(self.private_reports(),[])
        output=json.dumps(summary)
        for private in ("rs/plugins/loottracker/LootHistoryStore",
                        "images/logo.png","textures/missing.png",
                        "java/lang/Class",str(self.temp),
                        r425.PINNED_R421_STORE_SHA):
            self.assertNotIn(private,output)

    def test_32_explicit_private_no_overwrite_worklist(self):
        first=r456.run(self.original_jar,save=True)
        self.assertTrue(first["private_worklist_created"])
        target=self.private_reports()[0]/r456.NAME
        before=target.read_bytes()
        second=r456.run(self.original_jar,save=True)
        self.assertEqual(len(self.private_reports()),2)
        self.assertNotEqual(
            first["owner_private_quarantine_folder"],
            second["owner_private_quarantine_folder"])
        self.assertEqual(target.read_bytes(),before)

    def test_33_original_SHA_mismatch_refuses_no_output(self):
        self.original_jar.write_bytes(b"bad source")
        with self.assertRaises(r456.r447.Refused):
            r456.inspect(self.original_jar)
        self.assertEqual(self.private_reports(),[])

    def test_34_changed_compiled_class_from_snapshot_refused(self):
        observed,_=r456.r446.observe()
        (self.compiled/"rs/Bridge.class").write_bytes(b"tampered")
        with self.assertRaisesRegex(
                r456.Refused,"R456_COMPILED_INPUT_CHANGED_DURING_SCAN"):
            r456.code_sites(observed)

    def test_35_changed_unrelated_source_during_private_double_scan_refused(self):
        original=r456.inspect
        observed=[0]
        def change(*args,**kwargs):
            result=original(*args,**kwargs)
            observed[0]+=1
            if observed[0]==1:
                file=self.source/"rs/Bridge.java"
                file.write_bytes(file.read_bytes()+b" changed source")
            return result
        with patch.object(r456,"inspect",side_effect=change):
            with self.assertRaisesRegex(
                    r456.Refused,
                    "R456_FULL_INVENTORY_CHANGED_BETWEEN_PRIVATE_SCANS"):
                r456.run(self.original_jar,save=True)
        self.assertEqual(self.private_reports(),[])

    def test_36_tiny_private_report_budget_refused(self):
        with patch.object(r456,"MAX_PRIVATE_BYTES",20):
            with self.assertRaisesRegex(
                    r456.Refused,"R456_PRIVATE_WORKLIST_BYTE_BUDGET"):
                r456.run(self.original_jar,save=True)
        self.assertEqual(self.private_reports(),[])

    def test_37_missing_original_public_CLI_no_private_path_leak(self):
        missing=self.temp/"real-client-private-v309.jar"
        proc=subprocess.run(
            [sys.executable,"-B",str(CLI),"--original-v309-jar",str(missing)],
            capture_output=True,text=True,check=False,timeout=15)
        self.assertEqual(proc.returncode,2,proc.stderr)
        payload=json.loads(proc.stdout)
        self.assertEqual(payload["status"],"R456_MEMBER_OPCODE_AUDIT_REFUSED")
        self.assertNotIn(str(missing),proc.stdout)
        self.assertFalse(payload["release_authorized"])

    def test_38_no_runtime_history_release_or_custody_claims(self):
        report=r456.run(self.original_jar)
        for flag in (
            "historical_R421_full_inventory_independently_approved",
            "client_started","client_bytecode_executed",
            "real_static_linkage_proven",
            "original_functionality_recovered",
            "assets_packaged_in_runnable_client",
            "persistent_history_or_deletion_journals_accessed",
            "build_authorized","merge_authorized","release_authorized",
        ):
            self.assertFalse(report[flag])


if __name__ == "__main__":
    unittest.main()
