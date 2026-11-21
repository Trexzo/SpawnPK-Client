"""R458 fully synthetic BootstrapMethods and invokedynamic regression suite.

No real SpawnPK JAR, private source, network requests, Java class execution,
player history, or persistence journals enter public GitHub CI.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r457_jvm_callsite_constraints as prior_fixture
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r458 import bootstrap_callsite_evidence as binary
from tools.r458 import audit_bootstrap_evidence as r458

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r458/audit_bootstrap_evidence.py"


def u2(i: int) -> bytes:
    return i.to_bytes(2, "big")


def u4(i: int) -> bytes:
    return i.to_bytes(4, "big")


class FabricatedJava11:
    """Invent JVM classfile with optional invokedynamic and condy entries."""
    def __init__(self):
        self.cp: list[bytes] = []
        self.ids: dict[str, int] = {}

    def add(self, label: str, value: bytes) -> int:
        self.cp.append(value)
        self.ids[label] = len(self.cp)
        return len(self.cp)

    def utf(self, label: str, value: str) -> int:
        raw = value.encode("ascii")
        return self.add(label, b"\x01"+u2(len(raw))+raw)

    def cls(self, label: str, name: str) -> int:
        ni = self.utf(label+"_name", name)
        return self.add(label, b"\x07"+u2(ni))

    def nat(self, label: str, name: str, desc: str) -> int:
        ni = self.utf(label+"_name", name)
        di = self.utf(label+"_desc", desc)
        return self.add(label, b"\x0c"+u2(ni)+u2(di))

    def methodref(self, label: str, owner: int, nat: int, tag=10) -> int:
        return self.add(label, bytes([tag])+u2(owner)+u2(nat))

    def handle(self, label: str, kind: int, referent: int) -> int:
        return self.add(label, b"\x0f"+bytes([kind])+u2(referent))

    def dynamic(self, label: str, tag: int, bsm: int, nat: int) -> int:
        return self.add(label, bytes([tag])+u2(bsm)+u2(nat))

    def fixture(self, *, opcode="indy", handle_kind=6,
                handle_target_kind=10, handle_name="metafactory",
                bsm_index=0, bootstrap_attrs=1, bootstrap_reference=None,
                corrupt_arg=False, extra_condy_arg=False,
                unused_call=False, explicit_code=None,
                dynamic_descriptor="Ljava/lang/String;",
                dynamictag_override=None, reserved_bytes=b"\x00\x00",
                old_major=55) -> bytes:
        own = self.cls("own", "rs/Synthetic")
        sup = self.cls("super", "java/lang/Object")
        bootstrap_class = self.cls("factory", "java/lang/invoke/LambdaMetafactory")
        impl_class = self.cls("impl", "rs/Implementation")
        name = self.utf("method_name", "load")
        mdesc = self.utf("method_desc", "()V")
        code_attr = self.utf("code_attr", "Code")
        bsm_attr = self.utf("bsm_attr", "BootstrapMethods")
        bsm_nat = self.nat(
            "bsm_nat", handle_name,
            "()V" if handle_name == "<init>"
            else "()Ljava/lang/invoke/CallSite;")
        bootstrap_target = self.methodref(
            "bsm_ref", bootstrap_class, bsm_nat, handle_target_kind)
        mh = self.handle("bsm_handle", handle_kind, bootstrap_target)
        self.ids["primary_handle"] = mh
        impl_nat = self.nat("impl_nat", "lambdaBody", "()V")
        impl_ref = self.methodref("impl_ref", impl_class, impl_nat)
        impl_handle = self.handle("impl_handle", 6, impl_ref)
        method_type_desc = self.utf("method_type_desc", "()V")
        method_type = self.add(
            "method_type", b"\x10"+u2(method_type_desc))
        dynamic_nat = self.nat("dynamic_nat", "DYNAMIC_VALUE",
                               dynamic_descriptor)
        self.dynamic("condy",17,bsm_index,dynamic_nat)
        call_nat = self.nat("call_nat","apply","()Ljava/lang/Runnable;")
        self.dynamic("indy",18,bsm_index,call_nat)
        bsm_index_id = (mh if bootstrap_reference is None
                        else bootstrap_reference)
        args = [method_type, impl_handle]
        if extra_condy_arg:
            args.append(self.ids["condy"])
        if corrupt_arg:
            args.append(self.ids["method_name"])  # CP Utf8 not loadable

        if explicit_code is not None:
            instructions = explicit_code
        elif unused_call or opcode == "unused":
            instructions = b"\xb1"
        elif opcode == "indy":
            instructions = b"\xba"+u2(self.ids["indy"])+reserved_bytes+b"\x57\xb1"
        elif opcode == "indy_badref":
            instructions = b"\xba"+u2(self.ids["condy"])+reserved_bytes+b"\x57\xb1"
        elif opcode == "condy":
            instructions = b"\x12"+bytes([self.ids["condy"]])+b"\x57\xb1"
        elif opcode == "condy_w":
            instructions = b"\x13"+u2(self.ids["condy"])+b"\x57\xb1"
        elif opcode == "condy2":
            instructions = b"\x14"+u2(self.ids["condy"])+b"\x58\xb1"
        else:
            raise ValueError("unknown synthetic opcode")

        # The invented Code attribute is structurally valid; no Java loads it.
        method_code = (u2(3)+u2(1)+u4(len(instructions))+instructions+
                       u2(0)+u2(0))
        method = (u2(0x0009)+u2(name)+u2(mdesc)+u2(1)+
                  u2(code_attr)+u4(len(method_code))+method_code)
        bsm_data = u2(1)+u2(bsm_index_id)+u2(len(args))+b"".join(
            u2(i) for i in args)
        raw = (b"\xca\xfe\xba\xbe\x00\x00"+u2(old_major)+
               u2(len(self.cp)+1)+b"".join(self.cp)+
               u2(0x0021)+u2(own)+u2(sup)+u2(0)+
               u2(0)+u2(1)+method+u2(bootstrap_attrs))
        for _ in range(bootstrap_attrs):
            raw += u2(bsm_attr)+u4(len(bsm_data))+bsm_data
        return raw


def sample(**kwargs):
    obj = FabricatedJava11()
    return obj.fixture(**kwargs)


class R458PureSynthetic(unittest.TestCase):
    def test_01_real_indy_opcode_follows_bootstrap_method_handle_and_lambda_arg(self):
        record = binary.scan_class(sample())
        self.assertEqual(record.class_name,"rs/Synthetic.class")
        self.assertEqual(len(record.invokedynamic_sites),1)
        call = record.invokedynamic_sites[0]
        self.assertEqual(call.source_method,"load()V")
        self.assertEqual(call.pc,0)
        self.assertEqual(call.nature,"invokedynamic")
        self.assertEqual(call.bootstrap.kind,6)
        self.assertEqual(call.bootstrap.name,"metafactory")
        self.assertEqual(call.bootstrap.owner,
                         "java/lang/invoke/LambdaMetafactory.class")
        self.assertEqual(call.argument_tags,(16,15))
        self.assertEqual(len(call.bootstrap_handle_arguments),1)
        self.assertEqual(call.bootstrap_handle_arguments[0].owner,
                         "rs/Implementation.class")
        self.assertEqual(call.bootstrap_handle_arguments[0].name,"lambdaBody")
        self.assertEqual(record.bootstrap_entries,1)
        self.assertEqual(record.method_type_entries,1)
        self.assertEqual(record.method_handle_entries,2)

    def test_02_unused_indy_cp_does_not_become_executed_bytecode_site(self):
        record=binary.scan_class(sample(unused_call=True))
        self.assertEqual(len(record.invokedynamic_sites),0)
        self.assertEqual(record.unused_invokedynamic_cp_entries,1)
        self.assertEqual(record.constant_pool_invokedynamic,1)
        self.assertEqual(record.unreferenced_bootstrap_entries,0)

    def test_03_condy_ldc_is_not_invokedynamic(self):
        record=binary.scan_class(sample(opcode="condy"))
        self.assertEqual(len(record.constant_dynamic_load_sites),1)
        self.assertEqual(len(record.invokedynamic_sites),0)
        self.assertEqual(record.constant_dynamic_load_sites[0].name,
                         "DYNAMIC_VALUE")
        self.assertEqual(record.constant_dynamic_load_sites[0].pc,0)

    def test_04_condy_ldc_w_is_one_slot_and_supported(self):
        record=binary.scan_class(sample(opcode="condy_w"))
        self.assertEqual(len(record.constant_dynamic_load_sites),1)

    def test_05_condy_long_uses_ldc2_w_not_ldc(self):
        record=binary.scan_class(sample(opcode="condy2",
                                         dynamic_descriptor="J"))
        self.assertEqual(len(record.constant_dynamic_load_sites),1)
        with self.assertRaisesRegex(binary.Refused,
                                    "R458_CONDY_LDC_SLOT_CATEGORY_MISMATCH"):
            binary.scan_class(sample(opcode="condy",dynamic_descriptor="J"))

    def test_06_ldc2_w_on_regular_condy_is_refused(self):
        with self.assertRaisesRegex(binary.Refused,
                                    "R458_CONDY_LDC_SLOT_CATEGORY_MISMATCH"):
            binary.scan_class(sample(opcode="condy2"))

    def test_07_condy_as_bootstrap_argument_tag17_not_recursively_executed(self):
        record=binary.scan_class(sample(extra_condy_arg=True))
        self.assertEqual(record.bootstrap_dynamic_arguments,1)
        self.assertEqual(record.invokedynamic_sites[0].argument_tags,
                         (16,15,17))

    def test_08_indy_reserved_operands_must_be_zero(self):
        with self.assertRaisesRegex(binary.Refused,
                                    "R458_BAD_INVOKEDYNAMIC_RESERVED_OPERANDS"):
            binary.scan_class(sample(reserved_bytes=b"\x00\x01"))

    def test_09_invokedynamic_opcode_needs_tag18(self):
        with self.assertRaisesRegex(binary.Refused,
                                    "R458_INVOKEDYNAMIC_NEEDS_TAG18"):
            binary.scan_class(sample(opcode="indy_badref"))

    def test_10_dynamic_cp_bootstrap_missing_refused(self):
        with self.assertRaisesRegex(binary.Refused,
                                    "R458_DYNAMIC_BOOTSTRAP_INDEX_MISSING"):
            binary.scan_class(sample(bsm_index=1))

    def test_11_missing_BootstrapMethods_attribute_refused(self):
        with self.assertRaisesRegex(binary.Refused,
                                    "R458_DYNAMIC_BOOTSTRAP_INDEX_MISSING"):
            binary.scan_class(sample(bootstrap_attrs=0))

    def test_12_duplicate_BootstrapMethods_attribute_refused(self):
        with self.assertRaisesRegex(
                binary.Refused,"R458_DUPLICATE_BOOTSTRAP_METHODS_ATTRIBUTE"):
            binary.scan_class(sample(bootstrap_attrs=2))

    def test_13_bootstrap_non_static_non_constructor_handle_refused(self):
        with self.assertRaisesRegex(
                binary.Refused,"R458_BOOTSTRAP_HANDLE_MUST_INVOKE_STATIC_OR_NEW"):
            binary.scan_class(sample(handle_kind=5))

    def test_14_invalid_handle_reference_tag_mismatch_refused(self):
        with self.assertRaisesRegex(
                binary.Refused,"R458_HANDLE_REFERENCE_KIND_TAG_MISMATCH"):
            binary.scan_class(sample(handle_kind=6,handle_target_kind=9))

    def test_15_handle_kind_8_requires_actual_constructor_name(self):
        with self.assertRaisesRegex(
                binary.Refused,"R458_NEW_INVOKE_SPECIAL_REQUIRES_INIT"):
            binary.scan_class(sample(handle_kind=8))

    def test_16_nonconstructor_handle_cannot_reference_init(self):
        with self.assertRaisesRegex(
                binary.Refused,"R458_NONCONSTRUCTOR_HANDLE_SPECIAL_NAME"):
            binary.scan_class(sample(handle_name="<init>",handle_kind=6))

    def test_17_invalid_bootstrap_argument_cp_tag_refused(self):
        with self.assertRaisesRegex(
                binary.Refused,"R458_BOOTSTRAP_ARG_NOT_LOADABLE_CP"):
            binary.scan_class(sample(corrupt_arg=True))

    def test_18_truncated_bootstrap_attribute_refused(self):
        raw=sample()
        with self.assertRaises(binary.Refused):
            binary.scan_class(raw[:-2])

    def test_19_class_magic_or_major_wrong_refused(self):
        raw=sample()
        for wrong in (raw[:6]+u2(56)+raw[8:],
                      b"\x00\x00\x00\x00"+raw[4:]):
            with self.subTest(wrong=wrong[:8]):
                with self.assertRaisesRegex(
                        binary.Refused,"R458_JAVA11_CLASS_REQUIRED"):
                    binary.scan_class(wrong)

    def test_20_bytecode_truncated_invokedynamic_refused(self):
        with self.assertRaisesRegex(
                binary.Refused,"R458_BAD_JVM_INSTRUCTION_BOUNDARY"):
            binary.scan_class(sample(explicit_code=b"\xba\x00"))

    def test_21_no_dynamic_cp_has_no_bootstrap_table_need(self):
        # R450's fabricated pre-existing Java11 class has ordinary invokes
        # but no invokedynamic/BootstrapMethods and must remain supported.
        raw=prior_fixture.r450_fixture.invented_classfile()
        record=binary.scan_class(raw)
        self.assertEqual(record.bootstrap_entries,0)
        self.assertEqual(len(record.invokedynamic_sites),0)
        self.assertEqual(len(record.constant_dynamic_load_sites),0)

    def test_22_member_handle_constructor_kind8_with_class_constructor(self):
        obj=FabricatedJava11()
        raw=obj.fixture(handle_kind=8,handle_name="<init>")
        record=binary.scan_class(raw)
        self.assertEqual(record.invokedynamic_sites[0].bootstrap.kind,8)

    def test_23_selected_code_dynamic_sites_budget_refuses(self):
        with patch.object(binary,"MAX_CODE_SITES",0):
            with self.assertRaisesRegex(
                    binary.Refused,"R458_CODE_DYNAMIC_SITE_BUDGET"):
                binary.scan_class(sample())

    def test_24_bootstrap_argument_budget_refuses(self):
        with patch.object(binary,"MAX_TOTAL_BOOTSTRAP_ARGUMENTS",1):
            with self.assertRaisesRegex(
                    binary.Refused,"R458_TOTAL_BOOTSTRAP_ARGS_LIMIT"):
                binary.scan_class(sample())

    def test_25_extra_attribute_bytes_are_refused(self):
        raw=sample()
        with self.assertRaisesRegex(binary.Refused,
                                    "R458_CLASSFILE_TRAILING_BYTES"):
            binary.scan_class(raw+b"x")


class R458Aggregate(unittest.TestCase):
    def test_26_owner_location_and_lambda_handle_counts_are_name_only(self):
        obj=binary.scan_class(sample())
        summary,detail=r458.aggregate(
            {"rs/Synthetic.class":obj},{"rs/Synthetic.class"},
            {"rs/Implementation.class"},set(),set())
        self.assertEqual(summary["invokedynamic_bytecode_sites"],1)
        self.assertEqual(summary["method_handle_cp_entries_sum"],2)
        self.assertEqual(summary["named_lambda_metafactory_bootstrap_sites"],1)
        self.assertEqual(summary["bootstrap_target_platform_name_only_sites"],1)
        self.assertEqual(summary[
            "bootstrap_method_handle_arguments_at_instruction_sites"],1)
        self.assertEqual(detail["owner_only_bootstrap_callsite_and_handle_worklist"]
                         [0]["argument_method_handles"][0]["owner_location"],
                         "preferred_dependency_class_name")
        self.assertFalse(summary["invokedynamic_callsite_resolution_proven"])

    def test_27_concatenation_name_is_weak_factory_hint(self):
        record=binary.scan_class(sample())
        from dataclasses import replace
        call=record.invokedynamic_sites[0]
        handle=replace(call.bootstrap,
                       owner="java/lang/invoke/StringConcatFactory.class")
        altered=replace(record, invokedynamic_sites=(
            replace(call,bootstrap=handle),))
        report,_=r458.aggregate({"rs/Synthetic.class":altered},
                                {"rs/Synthetic.class"},set(),set(),set())
        self.assertEqual(report["named_string_concat_factory_bootstrap_sites"],1)
        self.assertFalse(report["lambda_runtime_functionality_proven"])

    def test_28_no_private_classnames_in_public_aggregate(self):
        record=binary.scan_class(sample())
        report,private=r458.aggregate(
            {"rs/Synthetic.class":record},{"rs/Synthetic.class"},
            set(),set(),set())
        serialized=json.dumps(report)
        for secret in ("Synthetic.class","Implementation.class",
                       "LambdaMetafactory","metafactory",
                       "apply","lambdaBody"):
            self.assertNotIn(secret,serialized)
        self.assertFalse(private["release_authorized"])

    def test_29_current_compiled_class_key_drift_refused(self):
        record=binary.scan_class(sample())
        with self.assertRaisesRegex(
                r458.Refused,"R458_REBUILT_INVENTORY_CLASS_KEY_DRIFT"):
            r458.aggregate({"rs/Synthetic.class":record},set(),set(),
                           set(),set())

    def test_30_unused_CP_is_not_reported_as_instruction(self):
        record=binary.scan_class(sample(unused_call=True))
        report,_=r458.aggregate({"rs/Synthetic.class":record},
                                 {"rs/Synthetic.class"},set(),set(),set())
        self.assertEqual(report["invokedynamic_bytecode_sites"],0)
        self.assertEqual(report["unused_invokedynamic_cp_entries_sum"],1)


class R458OwnerInventedOffline(unittest.TestCase):
    def setUp(self):
        prior_fixture.R457OwnerOfflineSynthetic.setUp(self)

    def reports(self):
        return sorted(self.temp.glob(r458.PREFIX+"*"))

    def test_31_all_inherited_pinned_owner_inputs_required(self):
        result,private=r458.inspect(self.original_jar)
        self.assertEqual(result["status"],
                         "R458_STATIC_BOOTSTRAP_METHOD_HANDLE_EVIDENCE_UNAPPROVED")
        self.assertEqual(result["original_v309_class_count"],5)
        self.assertEqual(result["original_v309_resource_count"],2)
        self.assertEqual(result["isolated_r421_java_sources"],2)
        self.assertEqual(result["isolated_r421_compiled_classfiles"],2)
        self.assertEqual(result["invokedynamic_bytecode_sites"],0)
        self.assertEqual(result["constant_dynamic_ldc_bytecode_sites"],0)
        self.assertFalse(result["historical_R421_full_inventory_independently_approved"])
        self.assertEqual(private["schema"],r458.SCHEMA)

    def test_32_default_aggregate_only_no_private_output(self):
        output=r458.run(self.original_jar)
        self.assertFalse(output["private_report_created"])
        self.assertEqual(self.reports(),[])
        as_text=json.dumps(output)
        for secret in ("LootHistoryStore","textures/missing.png",
                       "images/logo.png","java/lang/Class",str(self.temp),
                       r425.PINNED_R421_STORE_SHA):
            self.assertNotIn(secret,as_text)

    def test_33_explicit_private_report_creates_new_only_and_no_overwrite(self):
        first=r458.run(self.original_jar,save=True)
        original=self.reports()[0]/r458.NAME
        before=original.read_bytes()
        second=r458.run(self.original_jar,save=True)
        self.assertEqual(len(self.reports()),2)
        self.assertNotEqual(first["private_quarantine_directory"],
                            second["private_quarantine_directory"])
        self.assertEqual(original.read_bytes(),before)
        self.assertEqual(
            json.loads(before)["schema"],r458.SCHEMA)

    def test_34_sha_mismatch_original_v309_refused(self):
        self.original_jar.write_bytes(b"modified original")
        with self.assertRaises(r458.r447.Refused):
            r458.inspect(self.original_jar)

    def test_35_one_compiled_class_changes_after_inventory_refused(self):
        snap,_=r458.r446.observe()
        (self.compiled/"rs/Bridge.class").write_bytes(b"tampered")
        with self.assertRaisesRegex(
                r458.Refused,"R458_REBUILT_CLASS_CHANGED_DURING_SCAN"):
            r458.observed_bootstrap(snap)

    def test_36_unrelated_source_changes_between_private_scans_refused(self):
        actual=r458.inspect
        count=[0]
        def changed(*args,**kwargs):
            output=actual(*args,**kwargs)
            count[0]+=1
            if count[0]==1:
                file=self.source/"rs/Bridge.java"
                file.write_bytes(file.read_bytes()+b" unrelated edit")
            return output
        with patch.object(r458,"inspect",side_effect=changed):
            with self.assertRaisesRegex(
                    r458.Refused,"R458_CURRENT_INPUTS_CHANGED_BEFORE_PRIVATE_SAVE"):
                r458.run(self.original_jar,save=True)
        self.assertEqual(self.reports(),[])

    def test_37_private_budget_refused_without_report(self):
        with patch.object(r458,"MAX_PRIVATE_BYTES",20):
            with self.assertRaisesRegex(
                    r458.Refused,"R458_PRIVATE_REPORT_TOO_LARGE"):
                r458.run(self.original_jar,save=True)
        self.assertEqual(self.reports(),[])

    def test_38_missing_original_CLI_path_redacted(self):
        absent=self.temp/"real-client-not-available.jar"
        result=subprocess.run(
            [sys.executable,"-B",str(CLI),"--original-v309-jar",str(absent)],
            capture_output=True,text=True,timeout=15,check=False)
        self.assertEqual(result.returncode,2,result.stderr)
        response=json.loads(result.stdout)
        self.assertEqual(response["status"],"R458_BOOTSTRAP_AUDIT_REFUSED")
        self.assertNotIn(str(absent),result.stdout)

    def test_39_no_runtime_history_merge_or_release_claims(self):
        result=r458.run(self.original_jar)
        for key in (
            "historical_R421_full_inventory_independently_approved",
            "client_started","private_classfiles_executed",
            "source_completeness_proven","asset_packaging_proven",
            "live_v312_compatibility_proven",
            "persistent_player_history_or_deletion_journal_accessed",
            "release_authorized","merge_authorized",
            "bootstrap_method_execution_proven",
            "invokedynamic_callsite_resolution_proven",
            "dynamic_constant_resolution_proven"):
            self.assertFalse(result[key])


if __name__=="__main__":
    unittest.main()
