"""R457 fabricated JVMS invocation slot/count and special-method regressions.

Every classfile, JAR, current R421 owner root and temp directory in CI is
synthetic. No actual private source/assets, JVM execution or histories.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r454_member_ancestry_evidence as ancestry_fixture
import test_v309_r456_member_opcode_staticness as prior_fixture
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r453 import classfile_member_reference as member
from tools.r456 import member_opcode_evidence as decoder
from tools.r457 import jvm_callsite_constraints as slots
from tools.r457 import audit_jvm_callsite_constraints as r457

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r457/audit_jvm_callsite_constraints.py"


def target(name="run", desc="(I)V", kind="interface_method",
           owner="rs/API.class") -> member.Member:
    return member.Member(owner, name, desc, kind)


def invoke(op="invokeinterface", descriptor="(I)V", count=2,
           name="run", kind="interface_method", owner="rs/API.class"):
    table = dict(label for label in decoder.METHOD_OPS.values())
    return decoder.Site(
        "rs/Caller.class", "test()V", 0, op, table[op],
        target(name, descriptor, kind, owner),
        interface_encoded_count=(count if op == "invokeinterface" else None))


def records_for(t: member.Member, *, owner_flags=0x0201,
                method_flags=1):
    source = ancestry_fixture.make_record(
        "rs/Caller.class", None, refs=(t,))
    provider = ancestry_fixture.make_record(
        t.owner, None, methods=((t.name, t.descriptor, method_flags),))
    provider = replace(provider, access_flags=owner_flags)
    return {"rs/Caller.class": source}, {t.owner: provider}


class R457MethodDescriptorTests(unittest.TestCase):
    def test_01_empty_parameters_void_return(self):
        self.assertEqual(slots.method_shape("()V"),
                         slots.MethodShape(0, 0, 0, True))

    def test_02_primitives_one_slot_and_two_slot_values(self):
        shape = slots.method_shape("(BCFISZJD)V")
        self.assertEqual(shape.parameter_count, 8)
        self.assertEqual(shape.parameter_slots, 10)
        self.assertTrue(shape.void_return)

    def test_03_arrays_of_long_and_double_consume_one_slot(self):
        shape = slots.method_shape("([J[[DLrs/Packet;)Ljava/lang/String;")
        self.assertEqual(shape.parameter_count, 3)
        self.assertEqual(shape.parameter_slots, 3)
        self.assertEqual(shape.return_slots, 1)

    def test_04_primitive_long_return_is_two_slot_category(self):
        self.assertEqual(slots.method_shape("(I)J").return_slots, 2)

    def test_05_void_parameter_is_invalid(self):
        with self.assertRaises(slots.Refused):
            slots.method_shape("(V)V")

    def test_06_array_of_void_parameter_is_invalid(self):
        with self.assertRaises(slots.Refused):
            slots.method_shape("([V)V")

    def test_07_missing_closing_parenthesis_or_return_refused(self):
        for desc in ("(I", "(I)", "I)V", "()"):
            with self.subTest(desc=desc):
                with self.assertRaises(slots.Refused):
                    slots.method_shape(desc)

    def test_08_object_member_name_and_path_safety(self):
        for desc in ("(Lrs/../Danger;)V", "(Lrs\\Danger;)V",
                     "(L;)V", "(Lrs/Name)V", "(Lrs//Name;)V"):
            with self.subTest(desc=desc):
                with self.assertRaises(slots.Refused):
                    slots.method_shape(desc)

    def test_09_more_than_255_array_dimensions_refused(self):
        desc = "("+"["*256+"I)V"
        with self.assertRaisesRegex(slots.Refused,
                                    "R457_TOO_MANY_ARRAY_DIMENSIONS"):
            slots.method_shape(desc)

    def test_10_255_parameter_slots_permitted_and_256_refused(self):
        self.assertEqual(slots.method_shape("("+"I"*255+")V")
                         .parameter_slots, 255)
        with self.assertRaisesRegex(slots.Refused,
                                    "R457_ARGUMENT_SLOT_BUDGET"):
            slots.method_shape("("+"J"*128+")V")

    def test_11_non_ASCII_descriptor_refused(self):
        with self.assertRaisesRegex(slots.Refused, "R457_BAD_METHOD_DESCRIPTOR"):
            slots.method_shape("(Lrås/Foo;)V")

    def test_12_trailing_bytes_refused(self):
        with self.assertRaisesRegex(slots.Refused,
                                    "R457_DESCRIPTOR_TRAILING_DATA"):
            slots.method_shape("(I)Vextra")


class R457CallsiteIssueTests(unittest.TestCase):
    def test_13_correct_invokeinterface_slot_count_includes_receiver(self):
        site = invoke()
        owner = records_for(site.target)[1][site.target.owner]
        self.assertEqual(slots.site_issues(site, owner), ())

    def test_14_invokeinterface_count_mismatch_is_precise(self):
        site = invoke(count=1)
        owner = records_for(site.target)[1][site.target.owner]
        self.assertEqual(slots.site_issues(site, owner),
                         ("invokeinterface_encoded_count_mismatch",))

    def test_15_long_double_wide_values_exact_interface_count(self):
        site = invoke(descriptor="(JD[I)V", count=6)
        owner = records_for(site.target)[1][site.target.owner]
        self.assertEqual(slots.site_issues(site, owner), ())
        self.assertEqual(
            slots.site_issues(replace(site, interface_encoded_count=4), owner),
            ("invokeinterface_encoded_count_mismatch",))

    def test_16_array_of_long_counts_one_not_two(self):
        site = invoke(descriptor="([J)V", count=2)
        owner = records_for(site.target)[1][site.target.owner]
        self.assertEqual(slots.site_issues(site, owner), ())

    def test_17_missing_encoded_operand_is_unknown_not_valid(self):
        site = invoke(count=None)
        owner = records_for(site.target)[1][site.target.owner]
        self.assertEqual(slots.site_issues(site, owner),
                         ("invokeinterface_encoded_count_unavailable",))

    def test_18_invalid_encoded_count_is_refused(self):
        site = invoke(count=0)
        with self.assertRaisesRegex(slots.Refused,
                                    "R457_INTERFACE_ENCODED_COUNT_INVALID"):
            slots.site_issues(site, None)

    def test_19_interface_receiver_count_over_255_unencodable(self):
        site = invoke(descriptor="("+"I"*255+")V", count=255)
        self.assertEqual(
            slots.site_issues(site, None),
            ("invokeinterface_argument_slot_count_unencodable",))

    def test_20_valid_void_constructor_invokespecial_and_class_methodref(self):
        site = invoke(op="invokespecial", name="<init>", descriptor="()V",
                      kind="method", owner="rs/Target.class")
        owner = records_for(site.target,owner_flags=0x0001)[1][site.target.owner]
        self.assertEqual(slots.site_issues(site, owner), ())

    def test_21_constructor_cannot_be_called_via_invokevirtual(self):
        site = invoke(op="invokevirtual", name="<init>", descriptor="()V",
                      kind="method", owner="rs/Target.class")
        self.assertIn("constructor_requires_invokespecial",
                      slots.site_issues(site, None))

    def test_22_constructor_cannot_be_called_via_invokestatic(self):
        site = invoke(op="invokestatic", name="<init>", descriptor="()V",
                      kind="method", owner="rs/Target.class")
        self.assertIn("constructor_requires_invokespecial",
                      slots.site_issues(site, None))

    def test_23_constructor_cannot_have_nonvoid_descriptor(self):
        site = invoke(op="invokespecial", name="<init>", descriptor="()I",
                      kind="method", owner="rs/Target.class")
        self.assertIn("constructor_requires_void_return",
                      slots.site_issues(site, None))

    def test_24_constructor_cannot_use_interface_methodref(self):
        site = invoke(op="invokespecial", name="<init>", descriptor="()V",
                      kind="interface_method")
        self.assertIn("constructor_requires_class_methodref",
                      slots.site_issues(site, None))

    def test_25_explicit_clinit_any_invoke_rejected_as_signal(self):
        for op in ("invokespecial","invokestatic","invokevirtual"):
            with self.subTest(op=op):
                site=invoke(op=op, name="<clinit>", descriptor="()V",
                            kind="method", owner="rs/Target.class")
                self.assertIn("class_initializer_must_not_be_invoked",
                              slots.site_issues(site, None))

    def test_26_nonconstructor_invokespecial_not_falsely_flagged(self):
        site = invoke(op="invokespecial",name="superCall",
                      descriptor="()V",kind="method",owner="rs/Target.class")
        self.assertEqual(slots.site_issues(site, None), ())

    def test_27_interface_methodref_to_available_class_owner_flagged(self):
        site = invoke()
        owner = records_for(site.target,owner_flags=1)[1][site.target.owner]
        self.assertEqual(slots.site_issues(site, owner),
                         ("interface_methodref_owner_not_interface",))

    def test_28_class_methodref_to_available_interface_owner_flagged(self):
        site = invoke(op="invokestatic", kind="method", owner="rs/API.class")
        owner = records_for(site.target)[1][site.target.owner]
        self.assertEqual(slots.site_issues(site, owner),
                         ("class_methodref_owner_is_interface",))

    def test_29_interface_invokestatic_methodref_allowed(self):
        site = invoke(op="invokestatic", kind="interface_method")
        owner = records_for(site.target)[1][site.target.owner]
        self.assertEqual(slots.site_issues(site, owner), ())

    def test_30_unknown_owner_does_not_imply_wrong_CP_kind(self):
        site=invoke()
        self.assertEqual(slots.site_issues(site, None), ())

    def test_31_forged_static_opcode_flag_is_refused(self):
        site = replace(invoke(),static_opcode=True)
        with self.assertRaisesRegex(slots.Refused,
                                    "R457_OPCODE_STATIC_FLAG_FORGED"):
            slots.site_issues(site, None)

    def test_32_noninterface_count_field_refused(self):
        site=invoke(op="invokestatic",kind="method",
                    owner="rs/Target.class")
        site=replace(site,interface_encoded_count=2)
        with self.assertRaisesRegex(
                slots.Refused, "R457_NONINTERFACE_ENCODED_COUNT_UNEXPECTED"):
            slots.site_issues(site,None)

    def test_33_bad_owner_record_mismatch_refused(self):
        site=invoke()
        wrong=ancestry_fixture.make_record("rs/Wrong.class",None)
        with self.assertRaisesRegex(
                slots.Refused,"R457_REFERENCE_OWNER_RECORD_MISMATCH"):
            slots.site_issues(site,wrong)

    def test_34_real_r456_decoder_preserves_encoded_count(self):
        parsed,_=prior_fixture.parse(b"\xb9\x00\x03\x02\x00\xb1")
        self.assertEqual(len(parsed),1)
        self.assertEqual(parsed[0].interface_encoded_count,2)
        self.assertEqual(slots.site_issues(parsed[0],None),())

    def test_35_noninterface_bytecode_sites_have_no_count(self):
        parsed,_=prior_fixture.parse(b"\xb6\x00\x02\xb1")
        self.assertIsNone(parsed[0].interface_encoded_count)

    def test_36_counts_are_aggregated_without_private_callsite_names(self):
        a=invoke(count=1)
        rebuilt,preferred=records_for(a.target)
        summary,details=slots.analyze(rebuilt,preferred,[a],0)
        self.assertEqual(summary["sites_with_one_or_more_syntactic_findings"],1)
        self.assertEqual(summary["invokeinterface_argument_slot_count_mismatches"],1)
        self.assertEqual(summary["decoded_field_and_method_sites"],1)
        self.assertFalse(summary["JVM_runtime_or_linking_errors_proven"])
        self.assertEqual(
            details["private_violating_or_unresolved_JVM_callsite_candidates"][0]
            ["encoded_invokeinterface_count"],1)

    def test_37_multiple_independent_findings_are_counted_per_site(self):
        site=invoke(name="<init>",kind="interface_method",count=3,
                    descriptor="()I")
        rebuilt,dependencies=records_for(site.target,owner_flags=1)
        summary,private=slots.analyze(rebuilt,dependencies,[site],0)
        self.assertEqual(summary["sites_with_one_or_more_syntactic_findings"],1)
        self.assertEqual(summary["constructor_calls_using_non_invokespecial"],1)
        self.assertEqual(summary["constructor_calls_using_interface_methodref"],1)
        self.assertEqual(summary["constructor_descriptors_not_returning_void"],1)
        self.assertEqual(summary["invokeinterface_argument_slot_count_mismatches"],1)
        self.assertEqual(summary["interface_methodref_to_known_noninterface_owners"],1)
        self.assertEqual(len(private["private_violating_or_unresolved_JVM_callsite_candidates"]),1)

    def test_38_invokedynamic_separate_from_signature_proof(self):
        rebuilt={"rs/Caller.class":ancestry_fixture.make_record(
            "rs/Caller.class",None)}
        summary,_=slots.analyze(rebuilt,{},[],2)
        self.assertEqual(summary["invokedynamic_sites_not_resolved"],2)
        self.assertEqual(summary["decoded_field_and_method_sites"],0)

    def test_39_r456_legacy_site_without_count_remains_accepted_as_unknown(self):
        site=decoder.Site("rs/Caller.class","test()V",0,
                          "invokeinterface",False,target())
        self.assertEqual(slots.site_issues(site,None),
                         ("invokeinterface_encoded_count_unavailable",))


class R457OwnerOfflineSynthetic(unittest.TestCase):
    def setUp(self):
        prior_fixture.R456OwnerFakePipeline.setUp(self)

    def outputs(self):
        return sorted(self.temp.glob(r457.PREFIX+"*"))

    def test_40_complete_fake_original_and_R421_SHA_admission(self):
        result,worklist=r457.inspect(self.original_jar)
        self.assertEqual(result["status"],
                         "R457_STATIC_JVM_CALLSITE_CONSTRAINTS_UNAPPROVED")
        self.assertEqual(result["original_v309_classes"],5)
        self.assertEqual(result["original_v309_resources"],2)
        self.assertEqual(result["isolated_r421_sources"],2)
        self.assertEqual(result["isolated_r421_compiled_classes"],2)
        self.assertEqual(result["decoded_field_and_method_sites"],2)
        self.assertEqual(result["method_invocation_sites"],2)
        self.assertEqual(result["sites_with_one_or_more_syntactic_findings"],0)
        self.assertEqual(worklist["schema"],r457.SCHEMA)
        self.assertFalse(result["historical_R421_full_inventory_independently_approved"])

    def test_41_default_stdout_aggregate_only_and_readonly(self):
        report=r457.run(self.original_jar)
        self.assertFalse(report["private_worklist_created"])
        self.assertEqual(self.outputs(),[])
        serialized=json.dumps(report)
        for private in ("rs/plugins/loottracker/LootHistoryStore",
                        "textures/missing.png","images/logo.png",
                        "java/lang/Class",str(self.temp),
                        r425.PINNED_R421_STORE_SHA):
            self.assertNotIn(private,serialized)

    def test_42_explicit_private_quarantine_no_overwrite(self):
        first=r457.run(self.original_jar,save=True)
        self.assertTrue(first["private_worklist_created"])
        file=self.outputs()[0]/r457.NAME
        before=file.read_bytes()
        second=r457.run(self.original_jar,save=True)
        self.assertEqual(len(self.outputs()),2)
        self.assertNotEqual(first["private_quarantine_directory_name"],
                            second["private_quarantine_directory_name"])
        self.assertEqual(file.read_bytes(),before)

    def test_43_original_archive_sha_mismatch_refused(self):
        self.original_jar.write_bytes(b"changed original")
        with self.assertRaises(r457.r447.Refused):
            r457.inspect(self.original_jar)
        self.assertEqual(self.outputs(),[])

    def test_44_changed_compiled_class_since_snapshot_refused(self):
        snapshot,_=r457.r446.observe()
        (self.compiled/"rs/Bridge.class").write_bytes(b"altered")
        with self.assertRaisesRegex(
                r457.r456.Refused,"R456_COMPILED_INPUT_CHANGED_DURING_SCAN"):
            r457.r456.code_sites(snapshot)

    def test_45_unrelated_source_change_between_private_scans_refused(self):
        actual=r457.inspect
        n=[0]
        def change(*args,**kwargs):
            result=actual(*args,**kwargs)
            n[0]+=1
            if n[0]==1:
                f=self.source/"rs/Bridge.java"
                f.write_bytes(f.read_bytes()+b" unrelated edit")
            return result
        with patch.object(r457,"inspect",side_effect=change):
            with self.assertRaisesRegex(
                    r457.Refused,"R457_CURRENT_INVENTORY_CHANGED_BETWEEN_SCANS"):
                r457.run(self.original_jar,save=True)
        self.assertEqual(self.outputs(),[])

    def test_46_private_report_size_budget_refused_before_output(self):
        with patch.object(r457,"MAX_PRIVATE_BYTES",24):
            with self.assertRaisesRegex(
                    r457.Refused,"R457_PRIVATE_WORKLIST_SIZE_EXCEEDED"):
                r457.run(self.original_jar,save=True)
        self.assertEqual(self.outputs(),[])

    def test_47_missing_original_CLI_refuses_without_path_leak(self):
        missing=self.temp/"private-original-unavailable.jar"
        result=subprocess.run(
            [sys.executable,"-B",str(CLI),"--original-v309-jar",str(missing)],
            capture_output=True,text=True,timeout=15,check=False)
        self.assertEqual(result.returncode,2,result.stderr)
        response=json.loads(result.stdout)
        self.assertEqual(response["status"],"R457_JVM_CALLSITE_AUDIT_REFUSED")
        self.assertNotIn(str(missing),result.stdout)
        self.assertFalse(response["release_authorized"])

    def test_48_no_runtime_or_release_claims(self):
        result=r457.run(self.original_jar)
        for flag in ("client_executed",
                     "production_history_or_deletion_journals_accessed",
                     "historical_R421_full_inventory_independently_approved",
                     "full_client_source_deobfuscation_proven",
                     "assets_packaged_or_installed","compile_authorized",
                     "release_authorized","merge_authorized",
                     "complete_JVM_verification_performed",
                     "callsite_operand_stack_proven",
                     "constructor_initialization_state_proven",
                     "JVM_runtime_or_linking_errors_proven"):
            self.assertFalse(result[flag])


if __name__ == "__main__":
    unittest.main()
